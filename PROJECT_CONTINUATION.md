
---

# Repair Manager Project Continuation Summary

## Project

Persian Laptop Repair Shop Management Software

Stack:

* Python 3.12
* PyQt5
* SQLite
* SQLAlchemy
* QWebEngineView (new invoice preview)
* RTL UI
* UTF-8 Persian text

---

# Current Architecture Status

Architecture Refactor:

✅ Complete

Document:

* ARCHITECTURE_FINAL.md

Layers:

```text
UI
Controllers
Services
Core
Storage
```

Current architecture is considered STABLE.

No further architecture refactor unless explicitly requested.

---

# Storage Status

Current mode:

```text
DualStorage
├── repairs.json
└── repair_manager.db
```

Behavior:

```text
Load  -> JSON
Save  -> JSON + SQLite
```

SQLite migration:

✅ Completed

JSON migration:

✅ Completed

Audit:

SQLITE_MIGRATION_AUDIT.md

Current status:

```text
SQLite validation phase
```

Rules:

* keep repairs.json
* keep repair_manager.db
* continue real-world testing
* do not switch to SQLite-only yet

---

# Git Status

Stable tag exists:

```text
stable-json-version
```

Workflow:

```text
compile
test
commit
push
```

Every feature:

```text
one feature = one commit
```

---

# OpenCode Rules

Main file:

```text
opencode_rules.md
```

Important policies:

* clean git status required
* UTF-8 protection
* Persian text protection
* compile before commit
* manual test before commit
* push after commit
* no force push
* no history rewrite

---

# Invoice Preview Status

Old renderer:

```text
QTextEdit
```

New renderer:

```text
QWebEngineView
```

Migration status:

```text
COMPLETE
```

Current:

```python
USE_WEB_PREVIEW = True
```

Results:

✅ RTL works

✅ Logo works

✅ Printing works

✅ PDF export works

---

# Invoice Logo System

Implemented:

```text
services/logo_service.py
```

Features:

* logo loading
* header logo
* invoice logo
* app icon support
* base64 invoice embedding

Bug fixed:

Large logo caused blank preview.

Solution:

* scale image before base64
* size guard added

Status:

✅ Stable

---

# Shop Settings Features

Implemented:

```text
Shop name
Address
Phone
Email
Website
Logo
Invoice logo size
Header logo size
Use logo as app icon
```

Validation:

✅ Phone

11 digits

QRegularExpressionValidator

✅ Email

Email format validation

✅ Website

URL validation

---

# UI Improvements Already Implemented

Implemented:

✅ Dynamic application title

Example:

```text
سیستم مدیریت تعمیرگاه گرین فیکس
```

based on shop name.

---

Implemented:

✅ Dynamic window title

---

Implemented:

✅ Dynamic header logo

---

Implemented:

✅ Dynamic application icon

---

Implemented:

✅ Logo background removed

---

Implemented:

✅ Configurable logo sizes

Header:

16–512 px

Invoice:

16–256 px

---

# Current Next UI Tasks

Priority 1

Customizable title appearance

Planned settings:

```text
header_title_size
header_title_color
header_gradient_start
header_gradient_end
header_border_radius
header_height
```

Goal:

Professional gradient title bar.

---

Priority 2

Repair summary card near header

Show:

```text
فوری
عادی
در حال تعمیر
آماده تحویل
```

with:

* icon
* count
* color

---

Priority 3

Move:

```text
تنظیمات کلی
```

beside:

```text
پیش نمایش فاکتور
```

---

# Future Invoice Improvements

Planned:

✅ Professional centered header

✅ Better A4 layout

✅ Larger invoice number

✅ QR code

✅ Customer signature

✅ Delivery signature

✅ Better tables

✅ Better spacing

Not started yet.

---

# Future Roadmap

Current order:

```text
1. SQLite validation
2. SQLite-only migration
3. Customer database
4. Repair history
5. Reports
6. Dashboard
7. Inventory
8. SMS notifications
9. Multi-user support
10. PyQt6 migration
```

---

# PyQt6 Status

Not started.

Decision:

SQLite first.

PyQt6 later.

Reason:

Lower risk.

---

# Current Health Status

Architecture:

✅ Stable

SQLite:

✅ Working

Invoice Preview:

✅ Working

Printing:

✅ Working

PDF:

✅ Working

Logo System:

✅ Working

Application:

✅ Production usable

---

ا