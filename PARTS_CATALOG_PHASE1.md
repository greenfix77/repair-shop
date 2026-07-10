# Parts Catalog — Phase 1

> Date: 2026-07-10
> Scope: Standalone Parts Catalog (مدیریت قطعات) infrastructure and management UI.
> Phase: 1 (infrastructure + management only; no Financial tab integration yet).

## 1. Overview

Phase 1 introduces a standalone **Parts Catalog** that allows the shop to
define reusable parts (e.g. "LCD Screen 14-inch", "Battery HP-15") with
purchase price, sale price, stock quantity, and an active/inactive flag.
This catalog will later be used to populate Repair invoice line-items and
track inventory.

Phase 1 does **not** modify the Financial tab, inventory movements, or
repair logic. It only creates the table, repository, service layer, and
management UI, mirroring the Services Catalog pattern.

## 2. Database — `part` table

New SQLAlchemy model at `core/storage/part_model_db.py`:

| Field            | Type     | Constraints                  |
|------------------|----------|------------------------------|
| id               | Integer  | PK, autoincrement            |
| part_code        | String   | UNIQUE                       |
| name             | String   | NOT NULL                     |
| purchase_price   | Integer  | DEFAULT 0                    |
| sale_price       | Integer  | DEFAULT 0                    |
| stock_quantity   | Integer  | DEFAULT 0                    |
| description      | Text     | DEFAULT ""                   |
| is_active        | Boolean  | DEFAULT True                 |
| created_at       | DateTime | set on create                |
| updated_at       | DateTime | set on create + update       |

Registered in `core/storage/init_db.py` so `Base.metadata.create_all()` creates
the table automatically. Uses the same `Base`, `engine`, and `SessionLocal`
already used by `CustomerDB`, `RepairDB`, and `ServiceDB`.

No existing tables were modified. No schema migrations.

## 3. Repository — `PartRepository`

`core/storage/part_repository.py` mirrors the `ServiceRepository` pattern:

| Method                              | Description                              |
|-------------------------------------|------------------------------------------|
| `create(data)`                      | Insert a new part row                    |
| `update(part_id, data)`             | Update an existing part, set updated_at  |
| `delete(part_id)`                   | Delete by primary key                    |
| `get(part_id)`                      | Get by primary key                       |
| `list_all(active_only=False)`       | List all (or only active)                |
| `search(query)`                     | ILIKE search on name + part_code         |
| `generate_part_code()`              | Next code in `P000001`, `P000002`, ...   |

`_to_dict` serializes rows to plain dicts (consistent with other repositories).

## 4. Service Layer — `PartService`

`services/part_service.py` provides business validation:

| Method                              | Validation                               |
|-------------------------------------|------------------------------------------|
| `create_part(data)`                 | name required, prices >= 0, stock >= 0, auto-generate code |
| `update_part(part_id, data)`        | name required, prices >= 0, stock >= 0  |
| `delete_part(part_id)`              | passthrough                              |
| `get_part(part_id)`                 | passthrough                              |
| `list_all(active_only)`             | passthrough                               |
| `search(query)`                    | empty query -> list_all                  |
| `get_active_for_invoice()`          | returns active parts (future invoice use) |
| `find_by_code(part_code)`           | exact match by code (future invoice use)  |

Friendly Persian error messages are raised as `ValueError`:
- `نام قطعه الزامی است.`
- `قیمت یا موجودی نمی‌تواند منفی باشد.`

## 5. Management UI

### Navigation
A new `قطعات` button was added to the nav bar in `ui/main_window.py`,
alongside `تعمیرات`, `مشتریان`, and `خدمات`. The `QStackedWidget` now has 4 pages:
- Page 0: Repairs
- Page 1: Customers
- Page 2: Services
- Page 3: Parts

### Parts View (`ui/part_view.py`)
Mirrors the Services view structure:

- **Toolbar**: "➕ افزودن قطعه", "🗑️ حذف انتخاب‌شده‌ها", search box
- **Table columns**: ☑ | کد قطعه | نام قطعه | قیمت خرید | قیمت فروش | موجودی | تاریخ ایجاد | ویرایش
- Sorted alphabetically by name on render
- Header checkbox for Select All / Deselect All
- Per-row checkboxes for bulk selection
- "ویرایش" button (minWidth 75) in the last column
- Search box filters via `PartService.search()`
- Stock quantity shown in red when <= 0

### Add/Edit Dialog (`ui/dialogs/part_edit_dialog.py`)
- **Create mode** (`part_id=None`): title "افزودن قطعه", auto-generates code
- **Edit mode**: title "ویرایش قطعه", loads existing fields
- Fields: کد قطعه (read-only label), نام قطعه * (required), قیمت خرید (QSpinBox), قیمت فروش (QSpinBox), موجودی (QSpinBox), توضیحات (QTextEdit), فعال (QCheckBox)
- Validation: name required, prices >= 0, stock >= 0
- Stores `_created_part` for potential auto-select by callers

### App Integration (`app.py`)
- `PartService` instance in `__init__`
- `show_parts_view()`: switches to page 3, refreshes table
- `refresh_part_table()`: loads all parts, renders sorted rows
- `search_parts(text)`: filters table via search
- `add_part()`: opens create dialog, refreshes on accept
- `edit_part(part_id)`: opens edit dialog, refreshes on accept
- `delete_selected_parts()`: bulk delete with confirmation

## 6. Verification

- `python -m py_compile app.py` passes
- Application launches normally with 4 views
- Parts tab opens successfully (page 3)
- Creating a part works (code auto-generated as P000001)
- Editing a part works
- Bulk delete works (with confirmation)
- Search works (filters by name or code)
- Part codes are sequential (P000001, P000002, ...)
- Services, Customers, and Repairs tabs still work

## 7. Planned Future Integration

Phase 2 (not yet implemented) will integrate the Parts Catalog with
Repair invoices:

1. **Repair Financial tab**: Add a parts line-item table where each line
   references a `part_id` from this catalog.
2. **Invoice calculation**: Sum parts line-item prices (from `sale_price` or
   override) into the invoice total.
3. **Stock deduction**: When a repair is saved with parts, deduct quantities
   from `stock_quantity`.
4. **Low-stock warnings**: Alert when `stock_quantity` falls below a threshold.
5. **Active-only filtering**: In the invoice line-item picker, only show
   parts where `is_active = True`.
6. **Reporting**: Parts usage and profit margin reporting (sale_price vs
   purchase_price).

No changes to the Financial tab or invoice calculation are made in Phase 1.

## 8. Helper Methods for Future Invoice Integration

`PartService` includes two helper methods prepared for Phase 2:

- `get_active_for_invoice()`: Returns only active parts, suitable for
  populating an invoice line-item picker dropdown.
- `find_by_code(part_code)`: Finds a part by exact code match, for
  barcode-scanner or quick-code-entry integration.

These methods are not yet called by any UI code.

## 9. Files Created/Modified

```
created files:
- core/storage/part_model_db.py
- core/storage/part_repository.py
- services/part_service.py
- ui/dialogs/part_edit_dialog.py
- ui/part_view.py
- PARTS_CATALOG_PHASE1.md

modified files:
- core/storage/init_db.py       (register PartDB)
- ui/main_window.py            (nav button + parts page)
- app.py                        (PartService, view switching, CRUD)
```
