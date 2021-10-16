from __future__ import annotations

import os
from copy import copy
from dataclasses import dataclass
from pathlib import PurePosixPath, Path
from typing import List
from urllib.parse import quote_plus
from bs4 import BeautifulSoup
from yarl import URL
from os import makedirs, path

import scraper
import config


@dataclass
class File:
    scraper: scraper.Scraper
    fullpath: PurePosixPath

    def __init__(self, scraper, fullpath: PurePosixPath):
        self.scraper = scraper
        self.fullpath = fullpath

    def __str__(self):
        return f"File: \"{self.fullpath}\""

    def encoded_path(self) -> str: return quote_plus(str(self.fullpath))

    def relative_path(self) -> PurePosixPath:
        return PurePosixPath(str(self.fullpath).replace(self.scraper.get_base_path(), ""))

    def local_path(self) -> Path:
        return Path(config.save_path + str(self.relative_path()))

    async def create(self) -> None:
        local_path = self.local_path()
        print(self.fullpath.parent)
        if not path.exists(self.fullpath.parent):
            print("not exists")
            os.makedirs(self.fullpath.parent)
        if not local_path.exists():
            os.open(local_path, flags=os.O_CREAT)



@dataclass
class Folder(File):
    folders: List[Folder]
    files: List[File]

    def __init__(self, scraper, fullpath: PurePosixPath = None):
        super().__init__(scraper, fullpath)
        self.folders = []
        self.files = []

    async def update_folder_contents(self, endpoint: str = "dirlist", recursive: bool = False,
                                     iteration: int = 0) -> None:
        iteration += 1
        print(f"#{iteration} folder.get_folder_contents(\"{self.fullpath}\")")
        response = None
        try:
            response = await self.scraper.post(endpoint, {"dir": str(self.fullpath)})
        except Exception as ex:
            print(ex)
        xml = copy(response)
        if xml is None: return
        html = BeautifulSoup(xml, 'html.parser')
        print(html)

        self.folders.clear()
        self.files.clear()
        for elem in html.find_all('li'):
            elempath = self.fullpath / elem.a.text
            # if elempath in self: continue
            if elem.get("class")[0] == 'directory':
                dir = Folder(self.scraper, elempath)
                dir.create()
                if recursive: await dir.update_folder_contents(recursive=True, iteration=iteration)
                self.folders.append(dir)
            elif elem.get("class")[0] == 'file':
                file = File(self.scraper, elempath)
                await file.create()
                self.files.append(file)

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
        url.query.add("dir", self.fullpath)
        print(url)
        return url

    def create(self) -> None:
        path = self.local_path()
        if not path.exists():
            makedirs(path, exist_ok=True)
