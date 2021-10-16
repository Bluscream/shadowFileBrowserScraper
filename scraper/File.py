from pathlib import PosixPath
from typing import List
from urllib.parse import quote_plus
from bs4 import BeautifulSoup

class File:
    path: PosixPath
    def __init__(self, path: PosixPath = None):
        self.path = path

class Folder:
    path: PosixPath
    folders: List = []
    files: List[File] = []
    def __init__(self, path: PosixPath = None):
        self.path = path

    def fromResponse(self, path : PosixPath): pass

    def encoded_path(self): return quote_plus(str(self.path))

    def get_content(self): pass