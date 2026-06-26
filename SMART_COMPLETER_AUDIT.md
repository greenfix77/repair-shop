# Smart Customer Completer — Import Audit

Audit date: 2026-06-26  
File: `ui/dialogs/repair_dialog.py`

---

## 1. PyQt5 Import Sources

### Lines 1–4 — `PyQt5.QtWidgets`
```python
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
                              QTabWidget, QWidget, QLineEdit, QTextEdit, QSpinBox,
                              QDoubleSpinBox, QComboBox, QLabel, QPushButton,
                              QCompleter, QStyledItemDelegate)
```
✅ All symbols (`QDialog`, `QVBoxLayout`, `QGridLayout`, `QTabWidget`, `QWidget`,
`QLineEdit`, `QTextEdit`, `QSpinBox`, `QDoubleSpinBox`, `QComboBox`, `QLabel`,
`QPushButton`, `QCompleter`, `QStyledItemDelegate`) belong to
`PyQt5.QtWidgets`.

### Line 5 — `PyQt5.QtCore`
```python
from PyQt5.QtCore import Qt, QTimer, QStringListModel, QRegularExpression
```
✅ All symbols (`Qt`, `QTimer`, `QStringListModel`, `QRegularExpression`)
belong to `PyQt5.QtCore`.

### Lines 6–10 — `PyQt5.QtGui`
```python
from PyQt5.QtGui import (
    QFont,
    QRegularExpressionValidator,
    QColor,
)
```
✅ All symbols (`QFont`, `QRegularExpressionValidator`, `QColor`) belong to
`PyQt5.QtGui`.

### Lines 12–17 — `PyQt5.QtWidgets` (second import)
```python
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QTabWidget, QWidget, QLineEdit, QTextEdit, QSpinBox,
    QDoubleSpinBox, QComboBox, QLabel, QPushButton,
    QCompleter, QStyledItemDelegate, QStyle
)
```
✅ `QStyle` is in `PyQt5.QtWidgets` — correct module.

---

## 2. Duplicate Imports (⚠️ Warning)

The same QtWidgets symbols are imported **twice** — once on lines 1–4 and
again on lines 12–17:

| Symbol | First import | Second import |
|---|---|---|
| `QDialog` | line 1 | line 13 |
| `QVBoxLayout` | line 1 | line 13 |
| `QHBoxLayout` | line 1 | line 13 |
| `QGridLayout` | line 2 | line 13 |
| `QTabWidget` | line 2 | line 14 |
| `QWidget` | line 2 | line 14 |
| `QLineEdit` | line 2 | line 14 |
| `QTextEdit` | line 2 | line 14 |
| `QSpinBox` | line 2 | line 14 |
| `QDoubleSpinBox` | line 3 | line 15 |
| `QComboBox` | line 3 | line 15 |
| `QLabel` | line 3 | line 15 |
| `QPushButton` | line 3 | line 15 |
| `QCompleter` | line 4 | line 16 |
| `QStyledItemDelegate` | line 4 | line 16 |
| `QStyle` | — | line 16 |

This is functionally harmless (Python ignores duplicate imports from the
same module) but is dead code and should be cleaned up.

---

## 3. QStyle — Correct Module

`QStyle` is imported from `PyQt5.QtWidgets` (line 16), not from
`PyQt5.QtCore` or `PyQt5.QtGui`. ✅

Used at line 30:
```python
if option.state & QStyle.State_Selected:
```

---

## 4. QCompleter Setup

### Lines 226–243 — `_init_customer_completer()`

| Call | Status |
|---|---|
| `QTimer()` | ✅ Correct — single-shot timer for debounce |
| `setSingleShot(True)` | ✅ Valid |
| `QStringListModel()` | ✅ Correct model class |
| `QCompleter()` | ✅ Correct widget class |
| `setCaseSensitivity(Qt.CaseInsensitive)` | ✅ Valid enum |
| `setFilterMode(Qt.MatchContains)` | ✅ Valid (Qt ≥ 5.2) |
| `setModel(self._completer_model)` | ✅ QStringListModel is a valid model |
| `setPopupMode(QCompleter.UnfilteredPopup)` | ✅ Valid enum |
| `popup().setItemDelegate(delegate)` | ✅ QCompleter.popup() returns a QAbstractItemView |
| `popup().setLayoutDirection(Qt.RightToLeft)` | ✅ Valid for RTL Persian text |
| `activated.connect(...)` | ✅ Signal exists on QCompleter |
| `setCompleter(self._completer)` | ✅ QLineEdit has setCompleter |
| `textChanged.connect(...)` | ✅ Signal exists on QLineEdit |

---

## 5. Delegate

### Lines 26–49 — `CompleterItemDelegate(QStyledItemDelegate)`

| Aspect | Status |
|---|---|
| Inherits `QStyledItemDelegate` | ✅ Correct base class |
| `paint()` signature | ✅ `(self, painter, option, index)` |
| `option.state & QStyle.State_Selected` | ✅ Valid pattern |
| `painter.fillRect()` / `drawText()` | ✅ Standard QPainter API |
| `QFont(font)` copy | ✅ Safe pattern |
| `QColor('#666666')` | ✅ Valid hex color string |
| `sizeHint()` returns int | ✅ Valid return type |

---

## 6. Circular Import Check

Import chain:

```
ui/dialogs/repair_dialog.py
  → services/customer_service.py
      → core/storage/customer_repository.py
          → core/storage/database.py
          → core/storage/customer_model_db.py
              → core/storage/database.py
  → services/notification_service.py
  → core/status.py
  → services/invoice_calculator.py
```

✅ **No circular imports detected.** Every dependency flows one direction
(ui → services → core/storage).

---

## 7. Runtime Import Error Check

| Import | Resolves | Notes |
|---|---|---|
| `PyQt5.QtWidgets.*` | ✅ | Standard PyQt5 package |
| `PyQt5.QtCore.Qt` | ✅ | Enum namespace |
| `PyQt5.QtCore.QTimer` | ✅ | Standard class |
| `PyQt5.QtCore.QStringListModel` | ✅ | Standard class |
| `PyQt5.QtCore.QRegularExpression` | ✅ | Standard class |
| `PyQt5.QtGui.QFont` | ✅ | Standard class |
| `PyQt5.QtGui.QRegularExpressionValidator` | ✅ | Standard class |
| `PyQt5.QtGui.QColor` | ✅ | Standard class |
| `PyQt5.QtWidgets.QStyle` | ✅ | Standard class |
| `services.customer_service` | ✅ | No circular deps |
| `services.notification_service` | ✅ | No circular deps |
| `core.status` | ✅ | No circular deps |
| `services.invoice_calculator` | ✅ | No circular deps |
| `repair_manager.ui.components` | ✅ | No circular deps |

✅ **No runtime import errors expected.**

---

## Summary

| Check | Result |
|---|---|
| PyQt5 imports from correct modules | ✅ Pass |
| QStyle imported from QtWidgets only | ✅ Pass |
| QCompleter setup valid | ✅ Pass |
| QStringListModel usage valid | ✅ Pass |
| Delegate usage valid | ✅ Pass |
| No circular imports | ✅ Pass |
| No runtime import errors expected | ✅ Pass |
| Duplicate imports present | ⚠️ Warning |
