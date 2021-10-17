import asyncio
from logging import getLogger, basicConfig, DEBUG
from pathlib import Path as OSPath

import config
from scraper import Scraper, Folder

basicConfig(format='[%(asctime)s.%(msecs)03d] %(message)s', datefmt='%m/%d/%Y %H:%M:%S')
script = OSPath(__file__).stem
logger = getLogger(script)
logger.setLevel(DEBUG)

logger.info(f"{script} START")


async def main():
    scraper = Scraper(config.session_id)
    if not scraper.get_session_id(): await scraper.login(config.email, config.password)
    folder = Folder(scraper, scraper.get_path("ProgramData"))  # ProgramData/Animation Labs
    await folder.update_folder_contents(recursive=False)
    for subdir in folder.folders:
        logger.info(f"DIR: {subdir.fullpath}")
        logger.info(f"URL: {subdir.get_download_url()}")
        await subdir.download()
    for file in folder.files:
        logger.info(f"FILE: {file.fullpath}")
        logger.info(f"URL: {file.get_download_url()}")
        await file.download()
    # folder.tree()

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
