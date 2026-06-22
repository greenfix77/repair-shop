# SQLite Migration Audit

## DualStorage Architecture (Current State)

```
                    LaptopRepairManager
                            |
                      DualStorage
                     /            \
            RepairsStorage     SQLiteStorage
           (repairs.json)    (repair_manager.db)
```

## 1. Every Location Reading Repairs

### From persistent storage (file/DB):

| # | File | Line | Code | Source |
|---|------|------|------|--------|
| 1 | `core/storage/dual_storage.py` | 13 | `return self.json_storage.load_all()` | JSON |
| 2 | `core/storage/repairs_storage.py` | 10-19 | `json.load(f)` from `repairs.json` | JSON |
| 3 | `core/storage/sqlite_storage.py` | 11-31 | `session.query(RepairDB).all()` | SQLite |
| 4 | `core/storage/migrate_json_to_sqlite.py` | 10 | `json_storage.load_all()` | JSON |

### From in-memory list (`self.repairs` / `repairs` parameter):

| # | File | Line | Context |
|---|------|------|---------|
| 5 | `app.py` | 257 | `self.repairs = self.storage.load_all()` - entry point |
| 6 | `app.py` | 109 | `add_repair(self.repairs, data)` |
| 7 | `app.py` | 125 | `get_repair_by_id(self.repairs, repair_id)` |
| 8 | `app.py` | 138 | `update_repair(self.repairs, repair_id, updated_data)` |
| 9 | `app.py` | 158 | `delete_repair(self.repairs, repair_id)` |
| 10 | `app.py` | 174 | `get_repair_by_id(self.repairs, repair_id)` |
| 11 | `app.py` | 185 | `self.controller.search_repairs(self.table, self.repairs, text)` |
| 12 | `app.py` | 189 | `self.controller.filter_repairs(self.table, self.repairs, status)` |
| 13 | `app.py` | 211 | `update_statistics(self.repairs)` |
| 14 | `app.py` | 224 | `for repair in self.repairs` (notifications) |
| 15 | `services/repair_manager_service.py` | 7-49 | `add_repair`, `delete_repair`, `get_repair_by_id`, `update_repair` |
| 16 | `core/filters.py` | 2-26 | `search_repairs`, `filter_repairs` |
| 17 | `services/table_service.py` | 4-25 | `build_table_rows` |
| 18 | `services/statistics.py` | 5-12 | `update_statistics` |

**Key finding: Only 4 locations read from persistent storage. The rest read from an in-memory list.**

---

## 2. Every Location Writing Repairs

### To persistent storage (file/DB):

| # | File | Line | Code | Destination |
|---|------|------|------|-------------|
| 1 | `core/storage/dual_storage.py` | 16-17 | `json_storage.save_all(repairs)` + `sqlite_storage.save_all(repairs)` | Both |
| 2 | `core/storage/repairs_storage.py` | 24-31 | `json.dump(repairs, f)` | JSON |
| 3 | `core/storage/sqlite_storage.py` | 33-64 | `session.add(row)` + `session.commit()` | SQLite |
| 4 | `core/storage/migrate_json_to_sqlite.py` | 13 | `sqlite_storage.save_all(repairs)` | SQLite |

### Triggers for write:

| # | File | Line | Event |
|---|------|------|-------|
| 5 | `app.py` | 111 | After add_repair |
| 6 | `app.py` | 140 | After edit_repair |
| 7 | `app.py` | 160 | After delete_repair |
| 8 | `app.py` | 272 | closeEvent (app shutdown) |

---

## 3. & 4. Every Location Saving/Loading Data

All save/load for repairs goes through `app.py` → `DualStorage`:

```
load_data():
  app.py:257 → self.storage.load_all()
  → DualStorage.load_all() → RepairsStorage.load_all() → repairs.json

save_data():
  app.py:265 → self.storage.save_all(self.repairs)
  → DualStorage.save_all() → RepairsStorage.save_all() (JSON)
                          → SQLiteStorage.save_all() (SQLite)
```

**Shop settings** (separate from repairs) are persisted directly to `shop_settings.json`:

```
Load: ui/main_window.py:17-23, ui/dialogs/shop_settings_dialog.py:123-142, :177-196
Save: ui/dialogs/shop_settings_dialog.py:168-170
```

---

## 5. Current Storage Implementation

### `DualStorage` (`core/storage/dual_storage.py`)

```python
class DualStorage:
    def __init__(self):
        self.json_storage = RepairsStorage()
        self.sqlite_storage = SQLiteStorage()

    def load_all(self) -> List[Dict]:
        return self.json_storage.load_all()  # <-- JSON ONLY!

    def save_all(self, repairs: List[Dict]) -> None:
        self.json_storage.save_all(repairs)   # writes to JSON
        self.sqlite_storage.save_all(repairs) # writes to SQLite
```

**Critical asymmetry:** `load_all()` reads **only from JSON**. `save_all()` writes to **both**.

### `SQLiteStorage` (`core/storage/sqlite_storage.py`)

- `load_all()`: Queries all `RepairDB` rows, returns `List[Dict]`
- `save_all()`: Deletes all rows, inserts full list in one transaction
- Covers all 15 fields (id, customer_name, phone, brand, model, issue, parts_cost, labor_cost, tax, discount, status, receive_date, delivery_date, notes, warranty)

### `RepairsStorage` (`core/storage/repairs_storage.py`)

- `load_all()`: Reads `repairs.json`, assigns sequential IDs if missing
- `save_all()`: Dumps entire list to `repairs.json` with `ensure_ascii=False, indent=4`

### Migration script (`core/storage/migrate_json_to_sqlite.py`)

- Reads from JSON via `RepairsStorage`
- Writes to SQLite via `SQLiteStorage`

---

## 6. DualStorage Usage Map

Only referenced in **2 files**:

| # | File | Line | Usage |
|---|------|------|-------|
| 1 | `app.py` | 17 | `from core.storage.dual_storage import DualStorage` |
| 2 | `app.py` | 77 | `self.storage = DualStorage()` |
| 3 | `app.py` | 257 | `self.storage.load_all()` (via load_data) |
| 4 | `app.py` | 265 | `self.storage.save_all(self.repairs)` (via save_data) |

**The entire DualStorage → RepairsStorage dependency is confined to app.py.**

---

## 7. Remaining Direct JSON Dependencies

### For repairs data:

| # | File | Lines | Dependency | Risk |
|---|------|-------|------------|------|
| 1 | `core/storage/repairs_storage.py` | 1, 7, 15, 31 | `import json`, reads/writes `repairs.json` | HIGH - primary repair persistence |
| 2 | `core/storage/dual_storage.py` | 3, 9, 13, 16 | imports + uses `RepairsStorage` | HIGH - bridges JSON to app |
| 3 | `core/storage/migrate_json_to_sqlite.py` | 2, 9-10 | imports + uses `RepairsStorage` | LOW - migration script only |

### For shop settings (separate concern, not repairs):

| # | File | Lines | Dependency | Risk |
|---|------|-------|------------|------|
| 4 | `ui/main_window.py` | 1, 19-20 | `import json`, reads `shop_settings.json` | N/A - shop settings, not repairs |
| 5 | `ui/dialogs/shop_settings_dialog.py` | 1, 127-128, 169-170, 192-193 | `import json`, reads/writes `shop_settings.json` | N/A - shop settings, not repairs |

### Dead import:

| # | File | Line | Dependency | Risk |
|---|------|------|------------|------|
| 6 | `repair_manager/ui/components.py` | 2 | `import json` - **never used** | NONE - dead import, safe to remove |

---

## 8. Risk Assessment for Removing RepairsStorage

### Question: Can the application safely run on SQLite only?

**YES.** No blockers exist.

### Evidence:

1. **`SQLiteStorage` is fully implemented** with both `load_all()` and `save_all()`
2. **All writes already go to SQLite** through `DualStorage.save_all()`
3. **The SQLite schema is identical** to the JSON structure (same 15 fields)
4. **`SQLiteStorage.load_all()` returns the exact same `List[Dict]` format**
5. **No code in the application reads `repairs.json` directly** - all reads go through `DualStorage`
6. **No code depends on `RepairsStorage` except** `DualStorage` and `migrate_json_to_sqlite.py`
7. **All business logic** (services, filters, controllers) operates on in-memory `List[Dict]` and is storage-agnostic
8. **Shop settings** (`shop_settings.json`) is a separate persistence concern unrelated to repair storage

### Blocker list:

**None.** Zero blocking issues identified.

### Exact files to modify for SQLite-only migration:

| Step | File | Change |
|------|------|--------|
| 1 | `core/storage/dual_storage.py:13` | Change `return self.json_storage.load_all()` → `return self.sqlite_storage.load_all()` | 
| 2 | `app.py:17` | Change import `DualStorage` → `SQLiteStorage` |
| 3 | `app.py:77` | Change `DualStorage()` → `SQLiteStorage()` |
| 4 | Option A: Update `DualStorage` to read from SQLite (minimal change) | |
| 5 | Option B: Replace `DualStorage` entirely with `SQLiteStorage` (cleaner) | |

### Cleanup (safe to do after validation):

| # | File | Action | Reason |
|---|------|--------|--------|
| 1 | `core/storage/dual_storage.py` | Delete | No longer needed |
| 2 | `core/storage/repairs_storage.py` | Delete | No longer needed |
| 3 | `core/storage/migrate_json_to_sqlite.py` | Keep or delete | Migration script, useful for reference |
| 4 | `repairs.json` | Delete | Confirm SQLite data first |
| 5 | `repair_manager/ui/components.py:2` | Remove `import json` | Dead import |

### Recommended approach (smallest change):

```
Step 1: swap DualStorage.load_all() to read from SQLite
Step 2: change app.py import to SQLiteStorage directly
Step 3: verify application works
Step 4: cleanup dead files
```

### Risk level: **LOW**

- Migration requires modifying exactly **1 logic line** (`dual_storage.py:13`)
- Plus **2 import/instantiation lines** in `app.py`
- All changes are reversible
- SQLite has been receiving all writes since DualStorage was introduced
- Data integrity can be verified by comparing JSON and SQLite content before cutover

---

## Audit Metadata

- **Audit date:** 2026-06-22
- **Codebase state:** Commit `7b853d2` (clean working tree)
- **Files analyzed:** 32 Python files across `app.py`, `core/`, `services/`, `controllers/`, `ui/`, `repair_manager/`
- **Total grep patterns searched:** 14
