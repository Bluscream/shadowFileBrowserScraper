import asyncio
import dataclasses
from pathlib import Path, PosixPath
from dataclasses import dataclass
from typing import List
from json import dumps

from bs4 import BeautifulSoup
from yarl import URL
from urllib.parse import urlencode, quote_plus
from aiohttp import ClientSession, ClientConnectionError, ClientError
import os.path
from scraper.File import File, Folder

class Scraper():
    email = ""
    password = ""
    disk_id = ""

    session: ClientSession
    base_url = URL("https://filebrowser.ams1.shadow.tech:2447/shadowftp/")
    base_path = "/var/log/filebrowser/userdisks/"
    headers = {
        "accept": "*/*",
        "accept-language": "en,en-US;q=0.9,de;q=0.8",
        "cache-control": "no-cache",
        "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
        "pragma": "no-cache",
        "sec-ch-ua": "\"Chromium\";v=\"94\", \"Google Chrome\";v=\"94\", \";Not A Brand\";v=\"99\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\"",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "x-requested-with": "XMLHttpRequest"
    }
    cookies = {
        "has_visited": "true",
        "gdpr_preferences": "{%22necessary%22:true%2C%22preferences%22:false%2C%22statistics%22:false%2C%22marketing%22:false}",
        "cookie_scan_date": "2021-10-08T18:08:37.882Z",
        "is-user-exist": "false",
        "is-user": "true",
        "s_sq": "bladeshadowtechprod%3D%2526c.%2526a.%2526activitymap.%2526page%253Dhttps%25253A%25252F%25252Faccount.shadow.tech%25252Fhome%25252Fapplications%2526link%253DShadow%252520Anwendungen%2526region%253Droot%2526.activitymap%2526.a%2526.c",
        "beaker.session.id": ""
    }

    def get_session_id(self):
        for key, cookie in self.session.cookie_jar.filter_cookies('/').items():
            if key == "beaker.session.id": return cookie.value

    def __init__(self, session_id=""):
        if session_id:
            self.cookies["beaker.session.id"] = session_id
            self.session = ClientSession(cookies=self.cookies)
            print("Session:", self.get_session_id())
        else:
            self.session = ClientSession()

    async def post(self, endpoint, data):
        if not self.get_session_id(): raise AttributeError("Not logged in!")
        url = self.base_url / endpoint
        print("NEW POST REQUEST to", url)
        print("\tData:", dumps(data))

        # print("\tHeaders:", dumps(self.session.headers))

        async with self.session as session:
            async with session.post(url, data=data) as response:
                # if response.status != 200: await asyncio.sleep(99999)
                # print(f"\t{response.method} ({response.status} {response.reason})", "RESPONSE from", response.url)
                # print(f"\t\tType: {response.content_type} ({response.content_length}B)")
                # print("\t\tCookies:", dumps(response.cookies))
                # print("\t\tHeaders:", response.headers)
                html = await response.text()
                return [response, html]

    async def login(self, email, password):
        self.email = email
        self.password = password
        async with await self.post("auth", {"username": email, "password": password}) as response:
            print("Content-type:", response.headers['content-type'])
            html = await response.text()
            print("Body:", html[:15], "...")

    def get_path(self, path):
        return f"{self.base_path}/{self.disk_id}/{path}".replace("//", "/")

    async def get_folder_contents(self, path):
        _path = self.get_path(path)
        print(f"get_files({_path})")
        folder = Folder(PosixPath(_path))
        # folder.files = await self._get_files(folder.path)
        await self._get_folders(folder.path, folder)
        return folder

    async def _get_files(self, path):
        return self._get_folders(path, files=True)

    async def _get_folders(self, path, folder: Folder = None, files: bool = False):
        if not folder: folder = Folder(path)
        folder.path = Path(path)
        response = await self.post("filelist" if files else "dirlist", {"dir": path})
        xml = response[1]
        html = BeautifulSoup(xml, 'html.parser')
        print(html)

        for elem in html.find_all('li'):
            if elem.get("class")[0] == 'directory': folder.folders.append(Folder(folder.path / elem.a.text))
            elif elem.get("class")[0] == 'file': folder.files.append(File(folder.path / elem.a.text))
        print("lol")
        return folder


    async def scrape_disk(self, disk_id):
        self.disk_id = disk_id
        pass

    async def download(self, path, recursive=False):
        pass