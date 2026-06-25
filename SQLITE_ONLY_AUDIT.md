# SQLite-Only Migration — Final Audit

## 1. Which storage is used for `load_all()`

`DualStorage.load_all()` (`core/storage/dual_storage.py:12-13`) delegates to **`self.json_storage.load_all()`**, which is `RepairsStorage.load_all()` (`core/storage/repairs_storage.py:10-25`) — reads from **`repairs.json`**.

`SQLiteStorage.load_all()` (`core/storage/sqlite_storage.py:12-37`) is **defined but never called** from `DualStorage`.

## 2. Which storage is used for `save_all()`

`DualStorage.save_all()` (`core/storage/dual_storage.py:15-16`) calls **both**:
- `self.json_storage.save_all(repairs)` → writes `repairs.json`
- `self.sqlite_storage.save_all(repairs)` → writes to `repair_manager.db`

Data flows to **both backends** on every save.

## 3. Whether JSON is still required

**Yes.** `load_all()` has no SQLite fallback — it relies entirely on `repairs.json`.
Without JSON, the application starts with an empty repair list.

## 4. Whether any code imports `RepairsStorage` directly

| File | Line | Reason |
|---|---|---|
| `core/storage/dual_storage.py` | 3, 9 | Instantiates `RepairsStorage` as `self.json_storage` |
| `core/storage/migrate_json_to_sqlite.py` | 2, 9 | One-shot migration script |

No other file in the application imports `RepairsStorage` directly.

## 5. Whether any code still depends on `repairs.json`

**Yes.** `RepairsStorage` (`core/storage/repairs_storage.py`) reads (`load_all`) and writes (`save_all`) `repairs.json` directly. All access is indirect through `DualStorage`, but the file is the **sole read source** and one of two write targets.

## Summary

| Concern | Status |
|---|---|
| `load_all()` uses JSON-only | 🛑 Blocking |
| `save_all()` writes both JSON + SQLite | 🟡 Dual write |
| JSON required for startup | 🛑 Yes |
| Direct `RepairsStorage` import (non-migration) | `dual_storage.py` only |
| `repairs.json` still actively used | 🛑 Yes |
