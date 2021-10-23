from __future__ import annotations

import asyncio
import datetime
import json
import os.path
import re
from copy import copy
from logging import getLogger, DEBUG
from os import fdopen, remove
from pathlib import Path, PurePosixPath
from pickle import dumps
from shutil import copymode, move
from tempfile import mkstemp
from typing import List

import humanize
from aiohttp import ClientSession, ClientResponse
from aiohttp.web_response import Response
from humanize import naturalsize
from yarl import URL

import config
from scraper.File import File
from scraper.Folder import Folder
from fileinput import input
from sys import stdout

script = Path(__file__).stem
logger = getLogger(script)
logger.setLevel(DEBUG)


def cls(): os.system('cls' if os.name == 'nt' else 'clear')

class Scraper():
    session: ClientSession = ClientSession()
    base_url = URL("https://filebrowser.ams1.shadow.tech:2447/shadowftp/")
    base_path = "/var/log/filebrowser/userdisks/"
    headers = {
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "cache-control": "no-cache",
        # "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
        # "content-length": "126",
        "pragma": "no-cache",
        "sec-ch-ua": "\"Chromium\";v=\"94\", \"Google Chrome\";v=\"94\", \";Not A Brand\";v=\"99\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\"",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "x-requested-with": "XMLHttpRequest",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.61 Safari/537.36 OPR/80.0.4170.48"
    }
    cookies = {
        "has_visited": "true",
        "gdpr_preferences": "{%22necessary%22:true%2C%22preferences%22:false%2C%22statistics%22:false%2C%22marketing%22:false}",
        "cookie_scan_date": "2021-10-08T18:08:37.882Z",
        "is-user-exist": "false",
        "is-user": "true",
        "s_sq": "bladeshadowtechprod%3D%2526c.%2526a.%2526activitymap.%2526page%253Dhttps%25253A%25252F%25252Faccount.shadow.tech%25252Fhome%25252Fapplications%2526link%253DShadow%252520Anwendungen%2526region%253Droot%2526.activitymap%2526.a%2526.c",
    }

    def get_session_id(self, session = None) -> str:
        for key, cookie in (session if session else self.session).cookie_jar.filter_cookies('/').items():
            if key == "beaker.session.id": return cookie.value

    def __init__(self, session_id:str="") -> None:
        # config.save_path = eval('f' + repr(config.save_path))
        self.session = self.get_session(session_id)
        os.makedirs(config.save_path, exist_ok=True)
        logger.info(f"Created Scraper for {session_id}")

    def get_session(self, session_id:str="", filepath="config.py") -> ClientSession:
        session = self.session
        if session_id and session_id != "":
            if config.session_id != session_id:
                fd, abspath = mkstemp()
                with fdopen(fd, 'w') as file1:
                    with open(filepath, 'r') as file0:
                        for line in file0:
                            if line.startswith("session_id"):
                                file1.writelines([f"session_id = \"{session_id}\" # updated {datetime.datetime.now()}"])
                            else: file1.write(line)
                copymode(filepath, abspath)
                remove(filepath)
                move(abspath, filepath)
            config.session_id = session_id
            session = ClientSession(cookies={"beaker.session.id": session_id})
            logger.info(f"Created new Session with beaker id: {self.get_session_id(session)}")
        else:
            session = ClientSession()
            logger.info(f"Created new empty Session")
        return session

    async def post(self, endpoint:str, data:dict=None, _json:dict=None, headers:dict=None) -> str:
        # if not self.get_session_id(): raise AttributeError("Not logged in!")
        url = self.base_url / endpoint
        logger.info(f"NEW POST REQUEST to {url}")
        if data:
            t = ""
            for k, v in data.items(): t += f'{k}={v.replace("/", "%2F")}\n'
            t = t.strip()
            logger.info(f"\tData: {t} ({len(t.encode('utf-8'))})")
        if _json:
            t = ""
            for k, v in _json.items(): t += f'{k}={v.replace("/", "%2F")}\n'
            t = t.strip()
            logger.info(f"\tJSON: {t} ({len(t.encode('utf-8'))})")

        # print("\tHeaders:", dumps(self.session.headers))

        # if response.status != 200: await asyncio.sleep(99999)
        # print(f"\t{response.method} ({response.status} {response.reason})", "RESPONSE from", response.url)
        # print(f"\t\tType: {response.content_type} ({response.content_length}B)")
        # print("\t\tCookies:", dumps(response.cookies))
        # print("\t\tHeaders:", response.headers)
        await asyncio.sleep(0)
        async with self.get_session(config.session_id) as session:
            async with session.post(url, data=data, headers=headers, json=_json) as response:
                return await response.text()

    async def login(self, email, password):
        data = {"username": email, "password": password}
        url = self.base_url / "auth"
        await asyncio.sleep(0)
        async with self.get_session() as session:
            async with session.post(url, json=data) as resp:
                json = await resp.json()
                session_id = resp.cookies["beaker.session.id"].value
        self.session = self.get_session(session_id)
        logger.info(f"Logged in as \"{json['login']}\" (Session ID: {session_id})")

    def get_root_folder(self):
        return Folder(self, self.get_path())

    def get_base_path(self) -> str:
        return f"{self.base_path}{config.disk_id}"

    def get_path(self, path: str = "") -> PurePosixPath:
        return PurePosixPath(f"{self.get_base_path()}/{path}".replace("//", "/"))

    async def scrape_disk(self) -> List[Folder]:
        folders = [
            Folder(self, self.get_path("Program Files")),
            Folder(self, self.get_path("Program Files (x86)")),
            Folder(self, self.get_path("Users"))
        ]
        for folder in folders: await self.scrape_dir(str(folder))
        return folders

    async def scrape_dir(self, path: str, max_size_mb: int = 999) -> Folder:
        max_size = max_size_mb * 1048576
        folder = Folder(self, self.get_path(path))
        logger.info(f"Scraping Directory: \"{folder}\" (Max Size: {naturalsize(max_size)})")
        await folder.update_folder_contents(recursive=False)
        for subdir in folder.folders:
            logger.info(f"DIR: {subdir.fullpath}")
            logger.info(f"URL: {subdir.get_download_url()}")
            await subdir.download(max_size, skip_not_empty=True)
        for file in folder.files:
            logger.info(f"FILE: {file.fullpath}")
            logger.info(f"URL: {file.get_download_url()}")
            await file.download(skip_existing=True)
        return folder

    def clean_cache(self, root:Folder=None, regex:re.Pattern=r"\w{32}-(?:.*){1,15}\.zip") -> None:
        if not root: root = self.get_root_folder().local_path()
        logger.info(f"Cleaning {root} from files matching {regex}")
        freed_bytes = 0; free_files = 0
        for root, subdirs, files in os.walk(root):
            for filename in files:
                if re.match(regex, filename): # filename.endswith(".zip"):
                    f = os.path.join(root, filename)
                    try:
                        free_files += 1
                        s = os.path.getsize(f)
                        logger.info(f"#{free_files} Deleted incomplete download: \"{f}\" ({humanize.naturalsize(s)})")
                        os.unlink(f)
                        freed_bytes += s
                    except Exception as ex:
                        logger.warning(f"Failed to delete \"{f}\"!")
        logger.info(f"Deleted {free_files} incomplete downloads (Total Size: {humanize.naturalsize(freed_bytes)})")
