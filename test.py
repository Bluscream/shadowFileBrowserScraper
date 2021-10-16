from requests import post
from json import dumps
import config

url = 'https://filebrowser.ams1.shadow.tech:2447/shadowftp/dirlist'
cookies = {'beaker.session.id': config.session_id}
data = {"dir": f"%2Fvar%2Flog%2Ffilebrowser%2Fuserdisks%2F{config.disk_id}%2F"}

# ===============================

print("REQUESTS")
r = post(url, cookies=cookies, data=data)
print(r.text)

# ===============================

print("AIOHTTP")
import aiohttp, asyncio

async def main():
    async with aiohttp.ClientSession(cookies=cookies) as session:
        async with session.post(url, data=data) as response:
            print("Status:", response.status)
            print("Content-type:", response.headers['content-type'])
            html = await response.text()
            print("Body:", html[:15], "...")

loop = asyncio.get_event_loop()
loop.run_until_complete(main())

# ===============================
