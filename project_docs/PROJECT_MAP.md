# Laptop Repair Manager

## Project Summary

Desktop application for managing laptop repair shop operations.

Technology Stack:

* Python
* PyQt5
* JSON Storage
* jdatetime

---

# Main Classes

## ShopSettingsDialog

Purpose:
Manage shop information and invoice settings.

Responsibilities:

* Save shop information
* Load shop settings
* Logo management

Dependencies:

* JSON settings file

---

## InvoicePreviewDialog

Purpose:
Display invoice preview and export/print invoice.

Responsibilities:

* Generate printable invoice
* Generate web invoice
* Export PDF
* Print invoice

Dependencies:

* ShopSettingsDialog
* Repair data

---

## NotificationDialog

Purpose:
Display reminders and notifications.

Responsibilities:

* Show pending repairs
* Show overdue repairs

---

## RepairDialog

Purpose:
Create/Edit repair records.

Responsibilities:

* Input validation
* Repair data editing

---

## LaptopRepairManager

Purpose:
Main application window.

Responsibilities:

* Table management
* Search
* Filtering
* Statistics
* Data loading
* Data saving

---

# Data Files

repairs.json
settings.json

---

# Known Critical Methods

load_repairs()

save_repairs()

refresh_table()

update_statistics()

preview_invoice()

generate_web_invoice()

generate_print_invoice()

---

# Application Startup Flow

main()
↓
LaptopRepairManager()
↓
load_repairs()
↓
refresh_table()
↓
show()
