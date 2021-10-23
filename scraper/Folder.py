from __future__ import annotations

import asyncio
import os
import shutil
from copy import copy
from dataclasses import dataclass
from logging import getLogger, DEBUG
from os import makedirs
from pathlib import PurePosixPath, Path
from shutil import unpack_archive
from typing import List

import aiofiles as aiofiles
from bs4 import BeautifulSoup
from humanize import naturalsize
from yarl import URL

import config
from scraper import File

script = Path(__file__).stem
logger = getLogger(script)
logger.setLevel(DEBUG)


@dataclass
class Folder(File):
    folders: List[Folder]
    files: List[File]

    def __init__(self, scraper, fullpath: PurePosixPath = None):
        super().__init__(scraper, fullpath)
        self.folders = []
        self.files = []

    async def update_folder_contents(self, endpoint: str = "dirlist", recursive: bool = False,
                                     create: bool = False) -> None:
        # print(f"folder.get_folder_contents(\"{self.fullpath}\")")
        response = None
        try:
            response = await self.scraper.post(endpoint, data={"dir": str(self.fullpath)}, headers=self.scraper.headers)
        except Exception as ex:
            logger.error(ex)
        xml = copy(response)
        if xml is None: return
        html = BeautifulSoup(xml, 'html.parser')
        # info("\tXML:",html)

        self.folders.clear()
        self.files.clear()
        for elem in html.find_all('li'):
            if elem.a.text in config.ignored_dir_names:
                logger.warning(f"DIR IGNORE: \"{elem.a.text}\" in config.ignored_dir_names")
                continue
            if elem.a.text.endswith(".sys"):
                logger.warning(f"DIR IGNORE: \"{elem.a.text}\".endswith('.sys')")
                continue
            if elem.a.text == self.fullpath.name:
                logger.warning(f"DIR IGNORE: \"{elem.a.text}\" == \"{self.fullpath.name}\" (PROBABLY RECURSIVE LOOP)")
                continue
            elempath = self.fullpath / elem.a.text
            # if elempath in self: continue
            if elem.get("class")[0] == 'directory':
                dir = Folder(self.scraper, elempath)
                if create: dir.create()
                if recursive: await dir.update_folder_contents(recursive=recursive, create=create)
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
        try:
            return f"Folder: \"{self.fullpath}\" ({len(self.folders)} folders, {len(self.files)} files)"
        except:
            return f"Folder: \"{self.fullpath}\""

    def tree(self, _depth=1) -> None:
        print("=" * _depth + f"> \"{self.relative_path()}/\"")
        _depth += 1
        for file in self.files:
            print("=" * _depth + f"> \"{file.relative_path()}\"")
        for folder in self.folders:
            folder.tree(_depth)

    def get_download_url(self) -> URL:
        url = self.scraper.base_url / "zip"
        url = url.update_query({'dir': self.encoded_path()})  # .replace("%252F", "%2F")
        # logger.info(f"Download URL: {url}")
        return url

    def create(self) -> None:
        path = self.local_path()
        if not path.exists():
            makedirs(path, exist_ok=True)
            logger.info(f"created dir {path}")

    async def download(self, max_size_b: int = None, skip_not_empty: bool = False) -> None:
        url = self.get_download_url()
        lp = self.local_path()
        if skip_not_empty and lp.exists() and os.listdir(lp): return
        tmpfile = self.local_path().parent / f"{self.relative_path_md5()}-{self.fullpath.name[:15]}.zip"
        logger.info(f"Downloading to: {tmpfile}")
        async with self.scraper.get_session(config.session_id) as session:
            async with session.get(url, timeout=86400) as resp:  # self.scraper.session
                t = copy(resp)
                if t.status == 200:
                    # async with aiofiles.tempfile.TemporaryFile('wb') as f:
                    #     await f.write(b'Hello, World!')
                    self.create()
                    f = await aiofiles.open(str(tmpfile), mode='wb')
                    c = 0
                    try:
                        while True:
                            flsz = tmpfile.stat().st_size
                            chunk = await t.content.read(81920)
                            await asyncio.sleep(0)
                            if not chunk: break
                            await f.write(chunk)
                            # scraper.cls()
                            c += 1
                            if c > 100:
                                logger.info(f"Wrote 100 chunks to \"{tmpfile.name}\" ({naturalsize(flsz)} [{flsz}])")
                                c = 0
                            if flsz > max_size_b:  # 601970376, 999879829
                                logger.warning(f"zip is too large, downloading childs instead...")
                                await f.close()
                                tmpfile.unlink()
                                await self.update_folder_contents()  # this
                                for subdir in self.folders:
                                    await subdir.download(max_size_b)
                                return
                    except Exception as ex:
                        logger.error(f"Failed to download {url}: ({ex}), skipping...")
                        await f.close()
                        tmpfile.unlink()
                        pass
                    # await f.write(await resp.read())
                    await f.close()
            if tmpfile.exists():
                extract_dir = self.local_path()
                logger.info(f"Extracting to: {extract_dir}")
                try:
                    unpack_archive(str(tmpfile), extract_dir)
                except shutil.ReadError as ex:
                    logger.error(ex)
                    self.local_path().rmdir()
                tmpfile.unlink()
