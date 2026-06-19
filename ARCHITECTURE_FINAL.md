# Architecture Final

## Project tree

```
app.py
controllers/
  __init__.py
  main_controller.py
core/
  __init__.py
  filters.py
  models.py
  status.py
  storage/
    __init__.py
    repairs_storage.py
services/
  calculations.py
  date_service.py
  invoice_calculator.py
  invoice_exporter.py
  invoice_generator.py
  notification_service.py
  repair_manager_service.py
  statistics.py
  table_service.py
ui/
  main_window.py
  status_styles.py
  table_renderer.py
  dialogs/
    invoice_dialog.py
    repair_dialog.py
    shop_settings_dialog.py
repair_manager/
  ui/
    components.py
```

## Module responsibilities

### app.py

Entry point. Contains `LaptopRepairManager(QMainWindow)` — the main window class that wires UI events to controllers and services. Also contains `NotificationDialog(QDialog)` for displaying notification history.

### controllers/

- **main_controller.py** — `MainController` with static methods `refresh_table`, `search_repairs`, `filter_repairs`. Bridges `app.py` events with `services/table_service.py`, `ui/table_renderer.py`, and `core/filters.py`.

### ui/

- **main_window.py** — Pure UI construction: `build_header`, `build_toolbar`, `build_table`, `build_status_bar`, `build_ui`. No business logic.
- **status_styles.py** — Maps status constants to CSS color strings (`get_status_color`).
- **table_renderer.py** — `QTableWidgetItem` factory: `create_table_item`, `set_status_styling`, `set_total_styling`, `create_action_buttons`, `render_single_row`, `render_table_rows`.

### ui/dialogs/

- **repair_dialog.py** — `RepairDialog(QDialog)`: add/edit repair form.
- **invoice_dialog.py** — `InvoicePreviewDialog(QDialog)`: invoice preview, print, save-as-PDF.
- **shop_settings_dialog.py** — `ShopSettingsDialog(QDialog)`: shop name, address, phone, logo management.

### services/

- **repair_manager_service.py** — CRUD operations on the in-memory repair list (`add_repair`, `delete_repair`, `get_repair_by_id`, `update_repair`). Uses `Repair` model internally.
- **table_service.py** — `build_table_rows`: extracts display data from repair dicts for table rendering.
- **calculations.py** — `calculate_invoice`: pure math (parts + labor, tax, discount).
- **invoice_calculator.py** — `calculate_invoice_totals`: computes full invoice breakdown from a repair dict.
- **invoice_generator.py** — `generate_print_invoice_html`, `generate_web_invoice_html`: produces HTML strings for invoices.
- **invoice_exporter.py** — `print_invoice_content`, `save_invoice_to_pdf`: Qt-based print/PDF output.
- **notification_service.py** — `show_info`, `show_warning`, `show_error`, `show_question`: thin wrappers over `QMessageBox`.
- **statistics.py** — `update_statistics`: computes aggregate counts from repair list.
- **date_service.py** — `today_persian`: returns current Jalali date string.

### core/

- **models.py** — `Repair` dataclass with `to_dict` / `from_dict`.
- **status.py** — Status string constants, status lists, and color maps.
- **filters.py** — `search_repairs`, `filter_repairs`: pure filtering functions.

### core/storage/

- **repairs_storage.py** — `RepairsStorage`: JSON file read/write (`load_all`, `save_all`).

## Layer overview

| Layer | Location | Responsibility |
|-------|----------|---------------|
| UI | `ui/`, `ui/dialogs/` | PyQt widgets, layout, visual rendering |
| Controller | `controllers/` | Orchestrates UI events, delegates to services |
| Service | `services/` | Business logic, data transformation, CRUD |
| Storage | `core/storage/` | File I/O, persistence |

## Main data flow

```
User action
    ↓
app.py (LaptopRepairManager event handler)
    ↓
controllers/main_controller.py
    ↓
services/ (business logic)
    ↓
core/storage/repairs_storage.py (JSON file)
```

## Existing dialogs

- **RepairDialog** — `ui/dialogs/repair_dialog.py`: form to add or edit a repair record.
- **InvoicePreviewDialog** — `ui/dialogs/invoice_dialog.py`: invoice preview with print and PDF export.
- **ShopSettingsDialog** — `ui/dialogs/shop_settings_dialog.py`: shop profile settings (name, address, contacts, logo).

## Existing services

| Service | File | Purpose |
|---------|------|---------|
| `repair_manager_service` | `services/repair_manager_service.py` | CRUD on repair list |
| `invoice_generator` | `services/invoice_generator.py` | HTML invoice generation |
| `invoice_calculator` | `services/invoice_calculator.py` | Invoice total computation |
| `invoice_exporter` | `services/invoice_exporter.py` | Print / PDF output |
| `statistics` | `services/statistics.py` | Aggregate repair statistics |
| `table_service` | `services/table_service.py` | Table row data preparation |
| `calculations` | `services/calculations.py` | Parts/labor/tax/discount math |
| `notification_service` | `services/notification_service.py` | QMessageBox wrappers |
| `date_service` | `services/date_service.py` | Jalali date formatting |

## Remaining technical debt

1. `invoice_generator.py` contains large HTML methods.
2. Notification logic can be extracted later.
3. `invoice_exporter` contains Qt dependencies.

## Future extension points

- Customer database
- Inventory management
- SMS notifications
- Reports and analytics
- Multi-user support

## Refactor history summary

- Duplicate code removal
- Dialogs extraction
- Services extraction
- Controller extraction
- Shop settings extraction
- Cleanup
