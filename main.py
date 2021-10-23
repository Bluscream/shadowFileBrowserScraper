import asyncio
import sys
from logging import getLogger, DEBUG, Formatter, FileHandler, StreamHandler
from pathlib import Path as OSPath, PurePosixPath, Path, PosixPath
from typing import List

import config
from scraper import Scraper, Folder
from errors import errors
from argparse import ArgumentParser, Namespace, BooleanOptionalAction

logFormatter = Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
rootLogger = getLogger()
fileHandler = FileHandler("{0}/{1}.log".format("logs", "main"))
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
global running
running = False

async def main(args: Namespace, running=None):
    if running: return
    running = True
    if args.email: config.email = args.email
    if args.password: config.password = args.password
    if args.backup_dir: config.save_path = args.backup_dir
    if args.disk_id: config.disk_id = args.disk_id
    if args.ignored_dir_names: config.ignored_dir_names = args.ignored_dir_names.split(",")
    if args.session_id: config.session_id = args.session_id

    scraper = Scraper(config.session_id)
    if args.login or not scraper.get_session_id(): await scraper.login(config.email, config.password)
    path = str(args.path)
    path = path.replace("\\", "/").replace("C:/", "")
    path = scraper.get_path(path)
    folder = Folder(scraper, path)
    local_path = folder.local_path()
    if args.clean_cache: scraper.clean_cache(local_path)
    if args.update: await folder.update_folder_contents(recursive=args.recursive, create=args.create)
    if args.scrape: await folder.scrape(args.max_size, args.skip_not_empty_dirs, args.skip_existing_files)
    if args.scrape_disk: await scraper.scrape_disk(args.max_size, args.skip_not_empty_dirs, args.skip_existing_files)
    if args.download: await folder.download(args.skip_not_empty_dirs)
    # await scraper.scrape_disk()
    if args.tree: folder.tree()

    # await scraper.session.close()


if __name__ == '__main__':
    parser = ArgumentParser(description='Shadow File Browser Scraper')
    parser.add_argument('path', type=PurePosixPath, help='The path to scrape')
    parser.add_argument('-sd', '--scrape-disk', type=bool, help='Wether to scrape the full disk', default=False, action=BooleanOptionalAction)
    parser.add_argument('-s', '--scrape', type=bool, help='Wether to scrape the path', default=False, action=BooleanOptionalAction)
    parser.add_argument('-d', '--download', type=bool, help='Wether to download the path', default=False, action=BooleanOptionalAction)
    parser.add_argument('-t', '--tree', type=bool, help='Wether to print a tree of the path', default=False, action=BooleanOptionalAction)
    parser.add_argument('-l', '--login', type=bool, help='Force login', default=False, action=BooleanOptionalAction)
    parser.add_argument('--skip-not-empty-dirs', type=bool, help='Skips directories that already exist and are not empty', default=True, action=BooleanOptionalAction)
    parser.add_argument('--skip-existing-files', type=bool, help='Skips files that already exist', default=True, action=BooleanOptionalAction)
    parser.add_argument('--clean-cache', type=bool, help='Cleans corrupt downloads', default=False, action=BooleanOptionalAction)
    parser.add_argument('-u', '--update', type=bool, help='Update path contents', default=False, action=BooleanOptionalAction)
    parser.add_argument('-r', '--recursive', type=bool, help='Recurses operation', default=False, action=BooleanOptionalAction)
    parser.add_argument('-c', '--create', type=bool, help='Creates folder/file structure', default=False, action=BooleanOptionalAction)
    parser.add_argument('--max-size', type=int, help='Max size for directory archives in MB', default=999)
    parser.add_argument('-e', '--email', type=str, help='Email used for login', default="")
    parser.add_argument('-p', '--password', type=str, help='Password used for login', default="")
    parser.add_argument('--disk-id', type=str, help='Userdisk ID', default="")
    parser.add_argument('--ignored-dir-names', type=str, help='Comma seperated lowercase list of directory names to ignore', default="")
    parser.add_argument('--session-id', type=str, help='Session ID to use, don\'t use with --login', default="")
    parser.add_argument('--backup-dir', type=Path, help='The local backup mirror path', default=Path("backups/"))
    loop = None
    # try:
    # asyncio.set_event_loop(asyncio.new_event_loop())
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(parser.parse_args(), running))
    loop.run_until_complete(asyncio.sleep(0.250))
    loop.close()
    # except Exception as ex:
        # if loop.is_running(): loop.close()
        # errors.append(str(ex))

i = 0;l = len(errors)
for error in errors:
    i += 1
    logger.error(f"Error #{i}/{l}: {error}")

logger.info(f"{script} END")
