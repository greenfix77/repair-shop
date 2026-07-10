# Services Catalog — Phase 1

> Date: 2026-07-10
> Scope: Standalone Services Catalog (مدیریت خدمات) infrastructure and management UI.
> Phase: 1 (infrastructure + management only; no Financial tab integration yet).

## 1. Overview

Phase 1 introduces a standalone **Services Catalog** that allows the shop to
define reusable services (e.g. "Screen Replacement", "Battery Test") with a
default price and an active/inactive flag. This catalog will later be used to
populate Repair invoices line-items.

Phase 1 does **not** modify the Financial tab, inventory, or parts. It only
creates the table, repository, service layer, and management UI.

## 2. Database — `service` table

New SQLAlchemy model at `core/storage/service_model_db.py`:

| Field            | Type     | Constraints                  |
|------------------|----------|------------------------------|
| id               | Integer  | PK, autoincrement            |
| service_code     | String   | UNIQUE                       |
| name             | String   | NOT NULL                     |
| default_price    | Integer  | NOT NULL, DEFAULT 0          |
| description      | Text     | DEFAULT ""                   |
| is_active        | Boolean  | DEFAULT True                 |
| created_at       | DateTime | set on create                |
| updated_at       | DateTime | set on create + update       |

Registered in `core/storage/init_db.py` so `Base.metadata.create_all()` creates
the table automatically. Uses the same `Base`, `engine`, and `SessionLocal`
already used by `CustomerDB` and `RepairDB`.

No existing tables were modified. No schema migrations.

## 3. Repository — `ServiceRepository`

`core/storage/service_repository.py` mirrors the `CustomerRepository` pattern:

| Method                              | Description                              |
|-------------------------------------|------------------------------------------|
| `create(data)`                      | Insert a new service row                 |
| `update(service_id, data)`          | Update an existing service, set updated_at |
| `delete(service_id)`               | Delete by primary key                    |
| `get(service_id)`                   | Get by primary key                       |
| `list_all(active_only=False)`       | List all (or only active)                |
| `search(query)`                     | ILIKE search on name + service_code      |
| `generate_service_code()`           | Next code in `S000001`, `S000002`, ...   |

`_to_dict` serializes rows to plain dicts (consistent with CustomerRepository).

## 4. Service Layer — `ServiceService`

`services/service_service.py` provides business validation:

| Method                              | Validation                               |
|-------------------------------------|------------------------------------------|
| `create_service(data)`              | name required, price >= 0, auto-generate code |
| `update_service(service_id, data)`  | name required, price >= 0                |
| `delete_service(service_id)`        | passthrough                              |
| `get_service(service_id)`           | passthrough                              |
| `list_all(active_only)`             | passthrough                               |
| `search(query)`                     | empty query -> list_all                  |

Friendly Persian error messages are raised as `ValueError`:
- `نام خدمت الزامی است.`
- `قیمت پیش‌فرض نمی‌تواند منفی باشد.`

## 5. Management UI

### Navigation
A new `خدمات` button was added to the nav bar in `ui/main_window.py`,
alongside `تعمیرات` and `مشتریان`. The `QStackedWidget` now has 3 pages:
- Page 0: Repairs
- Page 1: Customers
- Page 2: Services

### Services View (`ui/service_view.py`)
Mirrors the Customers view structure:

- **Toolbar**: "➕ افزودن خدمت", "🗑️ حذف انتخاب‌شده‌ها", search box
- **Table columns**: ☑ | کد خدمت | نام خدمت | قیمت پیش‌فرض | توضیحات | فعال | ویرایش
- Sorted alphabetically by name on render
- Header checkbox for Select All / Deselect All
- Per-row checkboxes for bulk selection
- "ویرایش" button (minWidth 75) in the last column
- Search box filters via `ServiceService.search()`

### Add/Edit Dialog (`ui/dialogs/service_edit_dialog.py`)
- **Create mode** (`service_id=None`): title "افزودن خدمت", auto-generates code
- **Edit mode**: title "ویرایش خدمت", loads existing fields
- Fields: کد خدمت (read-only label), نام خدمت * (required), قیمت پیش‌فرض (QSpinBox), توضیحات (QTextEdit), فعال (QCheckBox)
- Validation: name required, price >= 0
- Stores `_created_service` for potential auto-select by callers

### App Integration (`app.py`)
- `ServiceService` instance in `__init__`
- `show_services_view()`: switches to page 2, refreshes table
- `refresh_service_table()`: loads all services, renders sorted rows
- `search_services(text)`: filters table via search
- `add_service()`: opens create dialog, refreshes on accept
- `edit_service(service_id)`: opens edit dialog, refreshes on accept
- `delete_selected_services()`: bulk delete with confirmation

## 6. Verification

- `python -m py_compile app.py` passes
- Application launches normally
- Services tab opens successfully (page 2)
- Creating a service works (code auto-generated as S000001)
- Editing a service works
- Bulk delete works (with confirmation)
- Search works (filters by name or code)
- Service codes are sequential (S000001, S000002, ...)
- Repairs and Customers views remain functional

## 7. Planned Future Integration

Phase 2 (not yet implemented) will integrate the Services Catalog with
Repair invoices:

1. **Repair Financial tab**: Replace flat cost fields with a line-item table
   where each line references a `service_id` from this catalog.
2. **Invoice calculation**: Sum line-item prices (from `default_price` or
   override) to compute parts/labor totals.
3. **Service price defaults**: When selecting a service, pre-fill the price
   from `default_price`, allow per-repair override.
4. **Active-only filtering**: In the invoice line-item picker, only show
   services where `is_active = True`.
5. **Reporting**: Service-level revenue reporting.

No changes to the Financial tab or invoice calculation are made in Phase 1.

## 8. Files Created/Modified

```
created files:
- core/storage/service_model_db.py
- core/storage/service_repository.py
- services/service_service.py
- ui/dialogs/service_edit_dialog.py
- ui/service_view.py
- SERVICES_CATALOG_PHASE1.md

modified files:
- core/storage/init_db.py       (register ServiceDB)
- ui/main_window.py            (nav button + services page)
- app.py                        (ServiceService, view switching, CRUD)
```
