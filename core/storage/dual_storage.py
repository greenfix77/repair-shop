from typing import List, Dict

from core.storage.repairs_storage import RepairsStorage
from core.storage.sqlite_storage import SQLiteStorage


class DualStorage:
    def __init__(self):
        self.json_storage = RepairsStorage()
        self.sqlite_storage = SQLiteStorage()

    def load_all(self) -> List[Dict]:
        return self.json_storage.load_all()

    def save_all(self, repairs: List[Dict]) -> None:
        self.json_storage.save_all(repairs)
        self.sqlite_storage.save_all(repairs)
