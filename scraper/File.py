from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from hashlib import md5
from logging import getLogger, DEBUG
from os import path
from pathlib import PurePosixPath, Path
from urllib.parse import quote

import aiofiles as aiofiles
from humanize import naturalsize
from yarl import URL

import config
import scraper

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

    def encoded_path(self) -> str:
        return quote(str(self.fullpath))

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
        url = url.update_query({'file': self.encoded_path()})  # .replace("%252F", "%2F")
        # logger.info(f"Download URL: {url}")
        return url

    async def download(self, skip_existing: bool = False) -> None:
        url = self.get_download_url()
        tmpfile = self.local_path()
        if skip_existing and tmpfile.exists(): return
        logger.info(f"Downloading to: {tmpfile}")
        async with self.scraper.get_session(config.session_id) as session:
            async with session.get(url, timeout=86400) as resp:  # self.scraper.session
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
                        logger.info(
                            f"wrote chunk of {chunk_size_str} to {tmpfile.name} ({naturalsize(tmpfile.stat().st_size)})")
                    # await f.write(await resp.read())
                    await f.close()
