import asyncio
from logging import getLogger, DEBUG, Formatter, FileHandler, StreamHandler
from pathlib import Path as OSPath

import config
from scraper import Scraper

logFormatter = Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
rootLogger = getLogger()
fileHandler = FileHandler("{0}/{1}.log".format("logs", "main.log"))
fileHandler.setFormatter(logFormatter)
rootLogger.addHandler(fileHandler)
consoleHandler = StreamHandler()
consoleHandler.setFormatter(logFormatter)
rootLogger.addHandler(consoleHandler)

# basicConfig(filename="main.log", format='[%(asctime)s.%(msecs)03d] %(message)s', datefmt='%m/%d/%Y %H:%M:%S') # filemode='a',
script = OSPath(__file__).stem
logger = getLogger(script)
logger.setLevel(DEBUG)

logger.info(f"{script} START")


async def main():
    scraper = Scraper(config.session_id)
    if not scraper.get_session_id(): await scraper.login(config.email, config.password)
    # scraper.clean_cache()
    folder = await scraper.scrape_dir("Users/Shadow", max_size_mb=50)
    # await scraper.scrape_disk()
    folder.tree()

    # await scraper.session.close()


if __name__ == '__main__':
    loop = None
    try:
        # asyncio.set_event_loop(asyncio.new_event_loop())
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
        loop.run_until_complete(asyncio.sleep(0.250))
        loop.close()
    except Exception as ex:
        if loop.is_running(): loop.close()
        raise (ex)

logger.info(f"{script} END")
