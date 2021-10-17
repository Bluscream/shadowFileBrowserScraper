from __future__ import annotations

import asyncio
import os.path
from logging import getLogger, DEBUG
from pathlib import Path, PurePosixPath

from aiohttp import ClientSession
from yarl import URL

import config
from scraper.File import File, Folder

script = Path(__file__).stem
logger = getLogger(script)
logger.setLevel(DEBUG)


class Scraper():
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
    }

    def get_session_id(self) -> str:
        for key, cookie in self.session.cookie_jar.filter_cookies('/').items():
            if key == "beaker.session.id": return cookie.value

    def __init__(self, session_id="") -> None:
        # config.save_path = eval('f' + repr(config.save_path))
        self.session = self.get_session(session_id)
        os.makedirs(config.save_path, exist_ok=True)

    def get_session(self, session_id="") -> ClientSession:
        if session_id: return ClientSession(cookies={"beaker.session.id": session_id})
        return ClientSession()

    async def post(self, endpoint, data) -> str:
        # if not self.get_session_id(): raise AttributeError("Not logged in!")
        url = self.base_url / endpoint
        # print("NEW POST REQUEST to", url)
        # print(endpoint+":", dumps(data["dir"]))

        # print("\tHeaders:", dumps(self.session.headers))

        # if response.status != 200: await asyncio.sleep(99999)
        # print(f"\t{response.method} ({response.status} {response.reason})", "RESPONSE from", response.url)
        # print(f"\t\tType: {response.content_type} ({response.content_length}B)")
        # print("\t\tCookies:", dumps(response.cookies))
        # print("\t\tHeaders:", response.headers)
        await asyncio.sleep(.5)
        # async with self.session as session:
        async with self.get_session(config.session_id) as session:
            async with session.post(url, data=data, headers=self.headers) as response:
                return await response.text()

    async def login(self, email, password):
        async with await self.post("auth", {"username": email, "password": password}) as response:
            html = await response.text()
            logger.info(html)
            self.session = self.get_session(html)

    def get_root_folder(self):
        return Folder(self, self.get_path())

    def get_base_path(self) -> str:
        return f"{self.base_path}{config.disk_id}"

    def get_path(self, path: str = "") -> PurePosixPath:
        return PurePosixPath(f"{self.get_base_path()}/{path}".replace("//", "/"))
