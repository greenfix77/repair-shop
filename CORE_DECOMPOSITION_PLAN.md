# CORE DECOMPOSITION PLAN

## LaptopRepairManager Responsibility Analysis

### 1. UI Responsibilities
- **Methods**: init_ui, create_header, create_toolbar, create_table, create_status_bar
- **Future Module**: ui/main_window.py
- **Difficulty**: Easy
- **Dependencies**: PyQt5 widgets, PersianDateEdit
- **Order**: Extract first after storage

### 2. Business Logic Responsibilities
- **Methods**: add_repair, edit_repair, delete_repair, preview_invoice
- **Future Module**: core/business_logic.py
- **Difficulty**: Medium
- **Dependencies**: RepairDialog, InvoicePreviewDialog, storage layer
- **Order**: Extract after UI and storage

### 3. Data Transformation Logic
- **Methods**: calculate_total (in RepairDialog - not in manager)
- **Future Module**: services/calculations.py
- **Difficulty**: N/A (already in RepairDialog)
- **Dependencies**: N/A
- **Order**: N/A

### 4. Table Rendering Logic
- **Methods**: refresh_table
- **Future Module**: ui/table_renderer.py
- **Difficulty**: Medium
- **Dependencies**: repair data structure, UI components
- **Order**: Extract after UI base

### 5. Filtering/Search Logic
- **Methods**: search_repairs, filter_repairs
- **Future Module**: core/filters.py
- **Difficulty**: Easy
- **Dependencies**: table widget, repair data
- **Order**: Extract after table renderer

### 6. Statistics Calculation Logic
- **Methods**: update_statistics
- **Future Module**: services/statistics.py
- **Difficulty**: Easy
- **Dependencies**: repair data
- **Order**: Extract after filters

### 7. Invoice-Related Logic
- **Methods**: preview_invoice (currently in main manager)
- **Future Module**: services/invoice_service.py
- **Difficulty**: Hard
- **Dependencies**: InvoicePreviewDialog, repair data
- **Order**: Extract last

## Suggested Extraction Order

1. UI components (create_header, create_toolbar, create_table, create_status_bar)
2. Table rendering (refresh_table)
3. Filters (search_repairs, filter_repairs)
4. Statistics (update_statistics)
5. Business logic (add_repair, edit_repair, delete_repair)
6. Invoice service (preview_invoice)

## Dependencies Map

- UI components ← PyQt5, PersianDateEdit
- Table renderer ← UI components, repair data
- Filters ← Table renderer
- Statistics ← repair data
- Business logic ← Dialogs, Storage, UI
- Invoice service ← Business logic, InvoicePreviewDialog