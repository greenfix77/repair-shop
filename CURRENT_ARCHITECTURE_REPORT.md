# CURRENT ARCHITECTURE REPORT

## 1. Classes and Line Counts
- InvoicePreviewDialog (app.py:18-833) - 816 lines
- ShopSettingsDialog (app.py:656-801) - 146 lines
- NotificationDialog (app.py:1160-1195) - 36 lines
- RepairDialog (app.py:1196-1371) - 176 lines
- LaptopRepairManager (app.py:1372-1919) - 548 lines
- PersianCalendarWidget (components.py:17-39) - 23 lines
- PersianDateEdit (components.py:41-102) - 62 lines

## 2. Functions and Line Counts
- generate_print_invoice (app.py:86-310) - 225 lines
- generate_web_invoice (app.py:319-619) - 301 lines
- print_invoice (app.py:621-627) - 7 lines
- save_pdf (app.py:629-641) - 13 lines
- update_preview (app.py:643-652) - 10 lines
- select_logo (app.py:748-760) - 13 lines
- load_settings (app.py:761-781) - 21 lines
- save_settings (app.py:782-800) - 19 lines
- get_settings (app.py:802-823) - 22 lines
- calculate_total (app.py:1327-1333) - 7 lines
- load_data (app.py:1335-1350) - 16 lines
- get_data (app.py:1352-1369) - 18 lines
- init_ui (app.py:1377-1439) - 63 lines
- create_header (app.py:1440-1470) - 31 lines
- create_toolbar (app.py:1471-1524) - 54 lines
- create_table (app.py:1525-1560) - 36 lines
- create_status_bar (app.py:1561-1599) - 39 lines
- update_date_label (app.py:1600-1604) - 5 lines
- open_shop_settings (app.py:1606-1609) - 4 lines
- add_repair (app.py:1610-1627) - 18 lines
- edit_repair (app.py:1628-1663) - 36 lines
- delete_repair (app.py:1664-1690) - 27 lines
- preview_invoice (app.py:1691-1708) - 18 lines
- search_repairs (app.py:1709-1722) - 14 lines
- filter_repairs (app.py:1723-1731) - 9 lines
- refresh_table (app.py:1732-1801) - 70 lines
- view_repair (app.py:1802-1805) - 4 lines
- quick_invoice (app.py:1806-1809) - 4 lines
- update_statistics (app.py:1810-1820) - 11 lines
- check_notifications (app.py:1821-1852) - 32 lines
- load_data (app.py:1853-1867) - 15 lines
- save_data (app.py:1868-1873) - 6 lines
- closeEvent (app.py:1874-1883) - 10 lines
- main (app.py:1920-1937) - 18 lines

## 3. Dependency Map Between Classes
- InvoicePreviewDialog depends on ShopSettingsDialog (for getting shop settings)
- LaptopRepairManager uses PersianCalendarWidget and PersianDateEdit via import
- All UI classes inherit from PyQt5 widgets

## 4. Methods That Read/Write Files
- ShopSettingsDialog.load_settings (reads shop_settings.json)
- ShopSettingsDialog.save_settings (writes shop_settings.json)
- LaptopRepairManager.load_data (reads repairs.json)
- LaptopRepairManager.save_data (writes repairs.json)

## 5. Methods That Perform Calculations
- InvoicePreviewDialog.generate_print_invoice (financial calculations)
- InvoicePreviewDialog.generate_web_invoice (financial calculations)
- RepairDialog.calculate_total (financial calculations)
- LaptopRepairManager.refresh_table (financial calculations for display)

## 6. Methods That Generate Invoices
- InvoicePreviewDialog.generate_print_invoice
- InvoicePreviewDialog.generate_web_invoice
- InvoicePreviewDialog.print_invoice
- InvoicePreviewDialog.save_pdf
- InvoicePreviewDialog.update_preview

## 7. Methods That Handle Notifications
- NotificationDialog.__init__ (creates notification UI)
- LaptopRepairManager.check_notifications (checks for delivery date reminders)

## 8. UI-Only Methods
- InvoicePreviewDialog.init_ui
- ShopSettingsDialog.init_ui
- RepairDialog.init_ui
- LaptopRepairManager.init_ui
- LaptopRepairManager.create_header
- LaptopRepairManager.create_toolbar
- LaptopRepairManager.create_table
- LaptopRepairManager.create_status_bar
- PersianDateEdit.show_calendar
- PersianDateEdit.resizeEvent

## 9. Top 10 Largest Methods
1. InvoicePreviewDialog.generate_web_invoice (301 lines)
2. InvoicePreviewDialog.generate_print_invoice (225 lines)
3. LaptopRepairManager.refresh_table (70 lines)
4. InvoicePreviewDialog.__init__ (59 lines)
5. LaptopRepairManager.init_ui (63 lines)
6. ShopSettingsDialog.init_ui (62 lines)
7. RepairDialog.init_ui (75 lines)
8. LaptopRepairManager.create_toolbar (54 lines)
9. InvoicePreviewDialog.init_ui (33 lines)
10. ShopSettingsDialog.load_settings (21 lines)

## 10. Safe Extraction Order (Lowest Risk to Highest Risk)
1. PersianCalendarWidget (UI component, no dependencies)
2. PersianDateEdit (UI component, minimal dependencies)
3. NotificationDialog (simple UI component)
4. InvoicePreviewDialog (invoice generation, no core logic dependency)
5. ShopSettingsDialog (configuration, no core logic dependency)
6. RepairDialog (data entry, no core logic dependency)
7. calculations.py module (pure calculation functions)
8. storage.py module (file I/O operations)
9. notifications.py module (notification logic)
10. LaptopRepairManager (core application logic, highest complexity)