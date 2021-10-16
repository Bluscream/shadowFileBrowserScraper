import asyncio
from pathlib import PurePosixPath

import config
from scraper import Scraper, Folder


async def main():
    scraper = Scraper(config.session_id)
    # if not scraper.get_session_id(): await scraper.login(config.email, config.password)
    # scraper.download()
    folder = Folder(scraper, PurePosixPath("/var/log/filebrowser/userdisks"
                                           "/25ee0b378593bccc8523a69d90a24b2c647ba7c4b3c768f63ff1070872938188"
                                           "/ProgramData/Adguard/"))
    i = 0
    await folder.update_folder_contents(recursive=True, iteration=i)
    folder.tree()
    # folders = await scraper.post("dirlist", {"dir": scraper.get_path("")})

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
