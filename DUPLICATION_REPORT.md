# Duplication Report

## Overview

Total source files analyzed: 10 Python files
Total lines of code: ~2,200 (excluding empty files)

---

## 1. Exact Duplicated Functions

### 1.1 `generate_web_invoice` — 100% duplicate, 3 occurrences

| Instance | File | Lines |
|----------|------|-------|
| A (original) | `app.py` | 325–631 (307 lines) |
| B (orphan copy) | `app.py` | 838–1144 (307 lines) |

- **Duplication percentage:** 100% (identical, copy-paste)
- **Extraction difficulty:** Easy — both are inside `InvoicePreviewDialog` scope (instance A) or floating at module level (instance B). The orphan copy (B) is dead code and should be removed.
- **Recommended target module:** `services/invoice_service.py` — extract to a dedicated invoice service.

### 1.2 `print_invoice` — 100% duplicate, 2 occurrences

| Instance | File | Lines |
|----------|------|-------|
| A (original) | `app.py` | 633–639 (7 lines) |
| B (orphan copy) | `app.py` | 1146–1152 (7 lines) |

- **Duplication percentage:** 100%
- **Extraction difficulty:** Trivial
- **Recommended target module:** `services/invoice_service.py`

### 1.3 `save_pdf` — 100% duplicate, 2 occurrences

| Instance | File | Lines |
|----------|------|-------|
| A (original) | `app.py` | 641–655 (15 lines) |
| B (orphan copy) | `app.py` | 1154–1168 (15 lines) |

- **Duplication percentage:** 100%
- **Extraction difficulty:** Trivial
- **Recommended target module:** `services/invoice_service.py`

---

## 2. Exact Duplicated Calculations

### 2.1 Invoice financial calculation — 3+ occurrences

The identical calculation block:

```python
parts_cost = data.get('parts_cost', 0)
labor_cost = data.get('labor_cost', 0)
subtotal = parts_cost + labor_cost
tax_rate = data.get('tax', 0)
tax_amount = subtotal * (tax_rate / 100)
discount = data.get('discount', 0)
total = subtotal + tax_amount - discount
```

| Instance | File | Lines |
|----------|------|-------|
| A | `app.py` | 103–109 (`generate_print_invoice`) |
| B | `app.py` | 330–337 (`generate_web_invoice`) |
| C | `app.py` | 843–850 (orphan `generate_web_invoice` copy) |
| D | `services/table_service.py` | 29–36 (`build_table_rows`) |

- **Duplication percentage:** 100% across all 4 instances
- **Extraction difficulty:** Easy — pure function, no UI dependencies
- **Recommended target module:** `repair_manager/core/calculations.py` (already intended but currently empty)

### 2.2 Total calculation in `RepairDialog` — partial duplicate

| Instance | File | Lines |
|----------|------|-------|
| RepairDialog | `app.py` | 1339–1344 (6 lines) |

This is a variant using widget `.value()` accessors instead of dict `.get()`. Core logic (`subtotal + tax - discount`) is structurally identical.

- **Duplication percentage:** ~70% (same formula, different data sources)
- **Extraction difficulty:** Easy — accept parameters
- **Recommended target module:** `repair_manager/core/calculations.py`

---

## 3. Exact Duplicated HTML Generation

### 3.1 Invoice HTML templates — 100% duplicate, 2 occurrences

| Template | File | Lines |
|----------|------|-------|
| Print invoice HTML | `app.py` | 111–322 (212 lines, unique) |
| Web invoice HTML (original) | `app.py` | 353–629 (277 lines) |
| Web invoice HTML (orphan copy) | `app.py` | 866–1142 (277 lines) |

- **Duplication percentage:** 100% for the web invoice template
- **Extraction difficulty:** Medium — templates are large, but they are self-contained f-strings
- **Recommended target module:** `services/invoice_service.py` as static methods or template strings

---

## 4. Exact Duplicated Styling Code

### 4.1 Web invoice CSS — 100% duplicate, 2 occurrences

The full CSS block (~170 lines of inline `<style>` inside the f-string) is duplicated in both instances of `generate_web_invoice`.

| Instance | File | Lines |
|----------|------|-------|
| Original | `app.py` | 358–531 |
| Orphan copy | `app.py` | 871–1044 |

- **Duplication percentage:** 100%
- **Extraction difficulty:** Easy — extract to a constant/string
- **Recommended target module:** `services/invoice_service.py` or a `templates/` module

### 4.2 Toolbar button styling — 70% duplicate

| Instance | File | Lines |
|----------|------|-------|
| add_btn | `app.py` | 1492 |
| edit_btn | `app.py` | 1498 |
| delete_btn | `app.py` | 1504 |
| invoice_btn | `app.py` | 1510 |

Each button has the same structure: `setStyleSheet("background-color: <color>; color: white;")` — only the color changes.

- **Duplication percentage:** ~70%
- **Extraction difficulty:** Trivial
- **Recommended target module:** `ui/table_renderer.py` (add a `create_styled_button` factory)

---

## 5. Exact Duplicated Status-Color Logic

### 5.1 Status-to-color mapping — 100% duplicate, 3 occurrences

| Instance | File | Lines | Implementation |
|----------|------|-------|----------------|
| A | `app.py` | 341–347 | Dict mapping Persian status → hex color string |
| B | `app.py` | 854–860 | Identical dict (orphan copy) |
| C | `ui/table_renderer.py` | 13–24 | if/elif chain with QColor (same mapping, different API) |

Status mapping:
```
'در انتظار'       → '#FF9800' / QColor("#FFF3E0","#FF9800")
'در حال تعمیر'    → '#2196F3' / QColor("#E3F2FD","#2196F3")
'تعمیر شده'       → '#4CAF50' / QColor("#E8F5E9","#4CAF50")
'تحویل داده شده'  → '#9E9E9E' / QColor("#F5F5F5","#9E9E9E")
```

- **Duplication percentage:** 100% (same data, different representation)
- **Extraction difficulty:** Easy
- **Recommended target module:** `core/status.py` — create a shared status constants module with color mappings

### 5.2 Status bar color mapping — 100% duplicate, 4 labels

| Label | File | Lines | Color |
|-------|------|-------|-------|
| `پending_label` | `app.py` | 1587 | `#FF9800` |
| `in_progress_label` | `app.py` | 1593 | `#2196F3` |
| `completed_label` | `app.py` | 1599 | `#4CAF50` |
| `delivered_label` | `app.py` | 1605 | `#9E9E9E` |

Same colors, hardcoded in 4 separate `setStyleSheet` calls.

---

## 6. Exact Duplicated Table Code

### 6.1 Table column header definition — 100% unique (not duplicated)

The table header is defined once at `app.py:1541–1545` — *well extracted*.

### 6.2 Row rendering logic — well extracted

`render_table_rows` and `render_single_row` in `ui/table_renderer.py` handle row rendering — *good separation*.

### 6.3 Table refresh pattern — 70% similar across operations

The 3 operations (add, edit, delete) follow the identical pattern:

```python
self.save_data()
self.refresh_table()
QMessageBox.information(self, "موفق", "...")
```

| Instance | File | Lines |
|----------|------|-------|
| add_repair | `app.py` | 1640–1643 |
| edit_repair | `app.py` | 1669–1672 |
| delete_repair | `app.py` | 1696–1699 |

- **Duplication percentage:** ~80%
- **Extraction difficulty:** Easy — create a helper `_refresh_and_notify(message)`
- **Recommended target module:** `LaptopRepairManager` class (keep as private method)

---

## 7. Exact Duplicated Repair Lookup Code

### 7.1 Get selected row ID pattern — 100% duplicate, 3 occurrences

```python
selected_row = self.table.currentRow()
if selected_row < 0:
    QMessageBox.warning(self, "هشدار", "لطفاً یک ردیف را انتخاب کنید.")
    return
repair_id = int(self.table.item(selected_row, 0).text())
```

| Instance | File | Lines |
|----------|------|-------|
| edit_repair | `app.py` | 1647–1653 |
| delete_repair | `app.py` | 1676–1682 |
| preview_invoice | `app.py` | 1703–1709 |

- **Duplication percentage:** ~90%
- **Extraction difficulty:** Easy
- **Recommended target module:** `LaptopRepairManager` — extract as `_get_selected_repair_id()`

### 7.2 Repair lookup by ID — 100% duplicate of service call, 3 occurrences

```python
get_repair_by_id(self.repairs, repair_id)
```

Occurrences at `app.py:1654`, `app.py:1694` (after deletion), `app.py:1710` (inline with `next()`).

The inline `next()` at line 1710 duplicates the logic of `get_repair_by_id` instead of using it.

---

## 8. Exact Duplicated Invoice Calculations

(Covered in section 2.1 — same calculation, same conclusion.)

Additional invoice presentation duplication:
- `generate_print_invoice` uses `<table>` HTML with `financial-summary` class
- `generate_web_invoice` uses `<div>`-based flex layout with `financial-card`/`financial-row` classes

These are structurally different layouts (same financial data, different rendering), so **not exact duplication** — but the data preparation logic is identical (section 2.1).

---

## 9. Exact Duplicated Date Formatting

### 9.1 Today's date formatting — 100% duplicate, 4 occurrences

```python
jdatetime.date.today().strftime('%Y/%m/%d')
```

| Instance | File | Line |
|----------|------|------|
| Print invoice footer | `app.py` | 317 |
| Web invoice footer (original) | `app.py` | 624 |
| Web invoice footer (orphan) | `app.py` | 1137 |
| Status bar date label | `app.py` | 1620 |

- **Duplication percentage:** 100%
- **Extraction difficulty:** Trivial
- **Recommended target module:** `repair_manager/core/calculations.py` as `today_persian()`

### 9.2 Date parsing for notification — structurally unique

Lines `app.py:1775–1776` parse `delivery_date_str.split('/')` to compute `days_diff` — this is the only date-arithmetic code and is **not duplicated**.

---

## 10. Refactoring Priority (Highest Impact First)

| Priority | Issue | Impact | Effort | Files Affected |
|----------|-------|--------|--------|----------------|
| **1** | Dead code: 3 orphan methods at module level (`generate_web_invoice`, `print_invoice`, `save_pdf`) | ❌ Causes `IndentationError`, app won't run | Trivial | `app.py:838–1168` |
| **2** | Invoice financial calculation duplicated in 4 places | 🔴 High (bug-prone) | Easy | `app.py`, `services/table_service.py` |
| **3** | Status-color mapping duplicated in 3 places | 🔴 High (inconsistent if changed) | Easy | `app.py`, `ui/table_renderer.py` |
| **4** | Selected-row / repair-ID lookup duplicated in 3 places | 🟡 Medium | Easy | `app.py` |
| **5** | Save-refresh-notify pattern duplicated in 3 places | 🟡 Medium | Easy | `app.py` |
| **6** | `today_persian()` formatting duplicated in 4 places | 🟡 Medium | Trivial | `app.py` |
| **7** | Web invoice CSS template duplicated (orphan dead code) | 🟢 Low (dead code) | Easy | `app.py` |
| **8** | Toolbar button styling pattern | 🟢 Low | Trivial | `app.py` |

### Recommended Module Structure

```
core/
  status.py          ← Status constants + color mappings
  calculations.py    ← calculate_invoice(), today_persian()
services/
  invoice_service.py ← generate_invoice_html() (print + web), print_invoice(), save_pdf()
  table_service.py   ← (keep as-is, already well-separated)
ui/
  table_renderer.py  ← (keep as-is, add create_styled_button())
```
