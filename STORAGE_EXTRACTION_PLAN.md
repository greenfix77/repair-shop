# STORAGE EXTRACTION PLAN

## 1. File I/O Operations Inventory

From app.py:
- `LaptopRepairManager.load_data()` - reads repairs.json
- `LaptopRepairManager.save_data()` - writes repairs.json
- `ShopSettingsDialog.load_settings()` - reads shop_settings.json
- `ShopSettingsDialog.save_settings()` - writes shop_settings.json
- `ShopSettingsDialog.get_settings()` - static method, reads shop_settings.json

## 2. Logical Storage Units

### Repairs Storage Unit
- File: repairs.json
- Operations: load_all, save_all, get_by_id, add, update, delete
- Data: repair records with all fields

### Settings Storage Unit
- File: shop_settings.json
- Operations: load, save, get_default
- Data: shop configuration (name, address, contact info, logo)

## 3. Storage API Interface

```python
class RepairsStorage:
    def load_all() -> List[dict]
    def save_all(repairs: List[dict]) -> None
    def get_by_id(repair_id: int) -> dict
    def add(repair: dict) -> None
    def update(repair: dict) -> None
    def delete(repair_id: int) -> None

class SettingsStorage:
    def load() -> dict
    def save(settings: dict) -> None
    def get_default() -> dict
```

## 4. BEFORE → AFTER Structure

BEFORE:
```
app.py (monolithic)
├── LaptopRepairManager.load_data/save_data
├── ShopSettingsDialog.load_settings/save_settings/get_settings
└── Direct file operations scattered
```

AFTER:
```
core/
├── storage.py
│   ├── RepairsStorage
│   └── SettingsStorage
├── models.py (data structures)
app.py
├── LaptopRepairManager (uses RepairsStorage)
└── ShopSettingsDialog (uses SettingsStorage)
```

## 5. Migration Steps

Step 1: Create core/storage.py with new classes
Step 2: Copy existing file operations to new classes
Step 3: Add backward compatibility wrapper functions
Step 4: Update LaptopRepairManager to use new storage
Step 5: Update ShopSettingsDialog to use new storage
Step 6: Remove old methods from app.py
Step 7: Final cleanup

## 6. Risk Analysis

Medium risk - File I/O is critical for data persistence. However, the operations are simple and well-tested in current implementation. Risk mitigated through backward compatibility.

## 7. Backward Compatibility Strategy

Maintain original method signatures in old classes during transition:
- Keep old methods as wrappers calling new storage
- Add deprecation warnings
- Allow both systems to operate simultaneously
- Remove old methods only after verification

## 8. Exact Functions to Move

From LaptopRepairManager:
- `load_data()` → `RepairsStorage.load_all()`
- `save_data()` → `RepairsStorage.save_all()`

From ShopSettingsDialog:
- `load_settings()` → `SettingsStorage.load()`
- `save_settings()` → `SettingsStorage.save()`
- `get_settings()` → `SettingsStorage.get_default()`

## 9. Suggested core/storage.py Structure

```python
# core/storage.py
import json
from pathlib import Path
from typing import List, Dict, Optional

class RepairsStorage:
    def __init__(self, filepath: str = "repairs.json"):
        self.filepath = Path(filepath)
    
    def load_all(self) -> List[Dict]:
        # Implementation from old load_data
    
    def save_all(self, repairs: List[Dict]) -> None:
        # Implementation from old save_data

class SettingsStorage:
    def __init__(self, filepath: str = "shop_settings.json"):
        self.filepath = Path(filepath)
    
    def load(self) -> Dict:
        # Implementation from old load_settings
    
    def save(self, settings: Dict) -> None:
        # Implementation from old save_settings
    
    @staticmethod
    def get_default() -> Dict:
        # Implementation from old get_settings
```

## 10. First Safe Commit Plan

Commit 1: Create core/storage.py with empty classes
Commit 2: Add actual implementations (copy from app.py)
Commit 3: Add backward compatibility wrappers in original classes
Commit 4: Update one consumer (LaptopRepairManager) to use new storage
Commit 5: Test and verify repairs functionality
Commit 6: Update other consumer (ShopSettingsDialog) to use new storage
Commit 7: Remove old methods after verification