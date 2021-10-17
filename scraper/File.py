from __future__ import annotations

import os
from copy import copy
from dataclasses import dataclass
from pathlib import PurePosixPath, Path
from typing import List
from urllib.parse import quote_plus, urlencode, quote

import aiofiles as aiofiles
import asyncio

import humanize
from bs4 import BeautifulSoup
from yarl import URL
from os import makedirs, path

import scraper
import config
import tempfile
from uuid import uuid4
from hashlib import md5
from shutil import unpack_archive
from humanize import naturalsize

from logging import getLogger, basicConfig, DEBUG
script = Path(__file__).stem
logger = getLogger(script)
logger.setLevel(DEBUG)

@dataclass
class File:
    scraper: scraper.Scraper
    fullpath: PurePosixPath

    def __init__(self, scraper, fullpath: PurePosixPath):
        self.scraper = scraper
        self.fullpath = fullpath

    def __str__(self):
        return f"File: \"{self.fullpath}\""

    def encoded_path(self) -> str: return quote(str(self.fullpath))

    def relative_path(self) -> PurePosixPath:
        return PurePosixPath(str(self.fullpath).replace(self.scraper.get_base_path(), ""))

    def relative_path_md5(self) -> str:
        return md5(str(self.relative_path()).encode('utf-8')).hexdigest()

    def local_path(self) -> Path:
        return Path(config.save_path + str(self.relative_path()))

    def create(self) -> None:
        local_path = self.local_path()
        if not path.exists(local_path.parent):
            logger.warning("not exists")
            os.makedirs(local_path.parent)
        if not local_path.exists():
            os.open(local_path, flags=os.O_CREAT)

    def get_download_url(self) -> URL:
        url = self.scraper.base_url / "file"
        url = url.update_query({'file': self.encoded_path()}) # .replace("%252F", "%2F")
        # logger.info(f"Download URL: {url}")
        return url

    async def download(self) -> None:
        url = self.get_download_url()
        tmpfile = self.local_path()
        logger.info(f"Downloading to: {tmpfile}")
        async with self.scraper.get_session(config.session_id) as session:
            async with session.get(url) as resp: # self.scraper.session
                if resp.status == 200:
                    self.create()
                    f = await aiofiles.open(str(tmpfile), mode='wb')
                    chunk_size = 81920
                    chunk_size_str = naturalsize(chunk_size)
                    while True:
                        chunk = await resp.content.read(chunk_size)
                        await asyncio.sleep(0)
                        if not chunk: break
                        await f.write(chunk)
                        logger.info(f"wrote chunk of {chunk_size_str} to {tmpfile.name} ({naturalsize(tmpfile.stat().st_size)})")
                    # await f.write(await resp.read())
                    await f.close()

@dataclass
class Folder(File):
    folders: List[Folder]
    files: List[File]

    def __init__(self, scraper, fullpath: PurePosixPath = None):
        super().__init__(scraper, fullpath)
        self.folders = []
        self.files = []

    async def update_folder_contents(self, endpoint: str = "dirlist", recursive: bool = False, create: bool = False) -> None:
        # print(f"folder.get_folder_contents(\"{self.fullpath}\")")
        response = None
        try:
            response = await self.scraper.post(endpoint, {"dir": str(self.fullpath)})
        except Exception as ex:
            logger.error(ex)
        xml = copy(response)
        if xml is None: return
        html = BeautifulSoup(xml, 'html.parser')
        # info("\tXML:",html)

        self.folders.clear()
        self.files.clear()
        for elem in html.find_all('li'):
            elempath = self.fullpath / elem.a.text
            # if elempath in self: continue
            if elem.get("class")[0] == 'directory':
                dir = Folder(self.scraper, elempath)
                if create: dir.create()
                if recursive: await dir.update_folder_contents(recursive=recursive,create=create)
                self.folders.append(dir)
            elif elem.get("class")[0] == 'file':
                file = File(self.scraper, elempath)
                if create: await file.create()
                self.files.append(file)
        # print("\t",self)

    def __contains__(self, fullpath) -> bool:
        for folder in self.folders:
            if folder.fullpath == fullpath: return True
        for file in self.files:
            if file.fullpath == fullpath: return True

    def __str__(self) -> str:
        try: return f"Folder: \"{self.fullpath}\" ({len(self.folders)} folders, {len(self.files)} files)"
        except: return f"Folder: \"{self.fullpath}\""

    def tree(self, _depth=1) -> None:
        print("=" * _depth + f"> \"{self.relative_path()}/\"")
        _depth += 1
        for file in self.files:
            print("=" * _depth + f"> \"{file.relative_path()}\"")
        for folder in self.folders:
            folder.tree(_depth)

    def get_download_url(self) -> URL:
        url = self.scraper.base_url / "zip"
        url = url.update_query({'dir': self.encoded_path()}) # .replace("%252F", "%2F")
        # logger.info(f"Download URL: {url}")
        return url

    def create(self) -> None:
        path = self.local_path()
        if not path.exists():
            makedirs(path, exist_ok=True)
            logger.info(f"created dir {path}")

    async def download(self) -> None:
        url = self.get_download_url()
        tmpfile = Path(tempfile.gettempdir()) / f"{self.relative_path_md5()}-{self.fullpath.name[:15]}.zip"
        logger.info(f"Downloading to: {tmpfile}")
        async with self.scraper.get_session(config.session_id) as session:
            async with session.get(url) as resp: # self.scraper.session
                if resp.status == 200:
                    # async with aiofiles.tempfile.TemporaryFile('wb') as f:
                    #     await f.write(b'Hello, World!')
                    f = await aiofiles.open(str(tmpfile), mode='wb')
                    chunk_size = 81920
                    chunk_size_str = naturalsize(chunk_size)
                    while True:
                        chunk = await resp.content.read(chunk_size)
                        await asyncio.sleep(0)
                        if not chunk: break
                        await f.write(chunk)
                        logger.info(f"wrote chunk of {chunk_size_str} to {tmpfile.name} ({naturalsize(tmpfile.stat().st_size)})")
                    # await f.write(await resp.read())
                    await f.close()
            if tmpfile.exists():
                extract_dir = self.local_path()
                self.create()
                logger.info(f"Extracting to: {extract_dir}")
                unpack_archive(str(tmpfile), extract_dir)
                tmpfile.unlink()