import datetime
import config
from scraper import Scraper
import asyncio
from typing import Optional


async def main():
    scraper = Scraper(config.session_id)
    # if not scraper.get_session_id(): await scraper.login(config.email, config.password)
    await scraper.scrape_disk(config.disk_id)
    print("Disk ID:", scraper.disk_id)
    # scraper.download(eval('f' + repr(config.save_path)))
    folders = await scraper.get_folder_contents("/")
    for folder in folders:
        print(str(folder))

    # await scraper.session.close()


if __name__ == '__main__':
    loop = None
    try:
        # asyncio.set_event_loop(asyncio.new_event_loop())
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
        loop.run_until_complete(asyncio.sleep(0.250))
        loop.close()
    except: pass