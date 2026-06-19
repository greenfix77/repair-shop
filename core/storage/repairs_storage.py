import json
from pathlib import Path
from typing import List, Dict


class RepairsStorage:
    def __init__(self, filepath: str = "repairs.json"):
        self.filepath = Path(filepath)
    
    def load_all(self) -> List[Dict]:
        """Load all repairs from file"""
        try:
            if self.filepath.exists():
                with open(self.filepath, "r", encoding="utf-8") as f:
                    repairs = json.load(f)
                for i, repair in enumerate(repairs):
                    if 'id' not in repair:
                        repair['id'] = i + 1
                return repairs
            else:
                return []
        except Exception as e:
            # In the original implementation, this would show a QMessageBox
            # We'll re-raise to let the caller handle it
            raise e

    def save_all(self, repairs: List[Dict]) -> None:
        """Save all repairs to file"""
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(repairs, f, ensure_ascii=False, indent=4)
        except Exception as e:
            # In the original implementation, this would show a QMessageBox
            # We'll re-raise to let the caller handle it
            raise e