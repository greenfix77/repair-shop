# PROJECT_DEPENDENCY MAP

## 1. Function Call Graph (app.py)

```
main() → QApplication → LaptopRepairManager.__init__
  ↓
LaptopRepairManager.__init__ → load_data() → refresh_table() → update_statistics()
  ↓
LaptopRepairManager.create_toolbar() → connect: search_repairs(), filter_repairs()
  ↓
LaptopRepairManager.add_repair() → RepairDialog.get_data() → save_data() → refresh_table()
  ↓
LaptopRepairManager.edit_repair() → RepairDialog(repair_data) → get_data() → save_data() → refresh_table()
  ↓
LaptopRepairManager.delete_repair() → save_data() → refresh_table()
  ↓
LaptopRepairManager.preview_invoice() → InvoicePreviewDialog(repair_data)
  ↓
InvoicePreviewDialog.__init__ → ShopSettingsDialog.get_settings() → generate_print_invoice() | generate_web_invoice()
  ↓
InvoicePreviewDialog.update_preview() → generate_print_invoice() | generate_web_invoice()
  ↓
InvoicePreviewDialog.print_invoice() → QPrinter
  ↓
InvoicePreviewDialog.save_pdf() → QPrinter.PdfFormat
  ↓
LaptopRepairManager.check_notifications() → NotificationDialog(notifications)
  ↓
LaptopRepairManager.closeEvent() → save_data()
```

## 2. Class-to-Class Dependencies (Actual Usage)

- LaptopRepairManager → RepairDialog (via add_repair(), edit_repair())
- LaptopRepairManager → InvoicePreviewDialog (via preview_invoice())
- LaptopRepairManager → NotificationDialog (via check_notifications())
- LaptopRepairManager → ShopSettingsDialog (via open_shop_settings())
- InvoicePreviewDialog → ShopSettingsDialog (via get_settings())
- RepairDialog → PersianDateEdit (via receive_date_input, delivery_date_input)
- InvoicePreviewDialog → QTextEdit (via preview widget)
- InvoicePreviewDialog → QPrinter (via print_invoice(), save_pdf())

## 3. Data Flow Mapping

UI Layer:
- LaptopRepairManager → QTableWidget (display repairs)
- RepairDialog → QLineEdit/QTextEdit (input validation)
- InvoicePreviewDialog → QTextEdit (HTML display)

Business Logic:
- LaptopRepairManager.load_data() ↔ repairs.json
- LaptopRepairManager.save_data() ↔ repairs.json
- RepairDialog.calculate_total() → financial calculations
- InvoicePreviewDialog.generate_*_invoice() → HTML generation

Storage:
- load_data()/save_data() → repairs.json
- ShopSettingsDialog.load_settings()/save_settings() → shop_settings.json

## 4. Hard vs Soft Dependencies Classification

Hard Dependencies:
- PyQt5 imports (all UI classes)
- json module (load/save operations)
- jdatetime (Persian date handling)
- Path from pathlib (file operations)

Soft Dependencies:
- ShopSettingsDialog.get_settings() (static method call from InvoicePreviewDialog)
- QMessageBox (UI notifications, could be abstracted)
- QPrinter (printing functionality, could be abstracted)

## 5. Circular Dependency Detection

None detected. All dependencies flow in one direction:
UI → Business Logic → Storage

## 6. Extraction Anchors (Safe Refactor Starting Points)

1. PersianCalendarWidget (no internal dependencies)
2. PersianDateEdit (depends only on PersianCalendarWidget)
3. ShopSettingsDialog (no business logic dependencies)
4. NotificationDialog (no business logic dependencies)
5. InvoicePreviewDialog (only depends on ShopSettingsDialog.get_settings())

## 7. Danger Zones (High Risk Refactor Areas)

1. LaptopRepairManager.refresh_table() - Complex UI updates with financial calculations
2. InvoicePreviewDialog.generate_web_invoice() - Large HTML template with embedded CSS
3. LaptopRepairManager.__init__ - Core initialization with multiple operations
4. LaptopRepairManager.save_data()/load_data() - Critical data persistence

## 8. Coupling Score (1–10) Per Class

- PersianCalendarWidget: 1 (standalone UI component)
- PersianDateEdit: 2 (uses PersianCalendarWidget)
- NotificationDialog: 1 (standalone UI component)
- ShopSettingsDialog: 2 (file I/O operations)
- RepairDialog: 4 (financial calculations, UI components)
- InvoicePreviewDialog: 5 (depends on ShopSettingsDialog, complex HTML generation)
- LaptopRepairManager: 9 (many responsibilities: UI, business logic, data persistence)

## 9. Suggested First Extraction Step

Extract PersianCalendarWidget and PersianDateEdit into a separate UI components module. Justification:
- No dependencies on business logic
- Standalone functionality
- Reusable components
- Minimal impact on main application flow
- Clear interface boundaries