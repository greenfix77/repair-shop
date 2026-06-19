# Invoice Generator Extraction Report

## 1. Files Modified

| File | Change | Lines |
|---|---|---|
| `services/invoice_generator.py` | **Created** — contains extracted HTML generation functions | +538 |
| `app.py` | **Modified** — removed old methods, added import, updated `update_preview` | -858 net |

## 2. Lines Moved

| Function | Source (app.py) | Destination | Lines |
|---|---|---|---|
| `generate_print_invoice_html` | `InvoicePreviewDialog.generate_print_invoice` | `services/invoice_generator.py` | 230 |
| `generate_web_invoice_html` | `InvoicePreviewDialog.generate_web_invoice` | `services/invoice_generator.py` | 302 |

**Total extracted: 532 lines of HTML generation logic.**

### Changes to app.py (`InvoicePreviewDialog`)

- **Added import** (line 32):  
  `from services.invoice_generator import generate_print_invoice_html, generate_web_invoice_html`
- **Removed method**: `generate_print_invoice` (was 228 lines)
- **Removed method**: `generate_web_invoice` (was 302 lines)
- **Updated method**: `update_preview` — now calls `generate_print_invoice_html()` and `generate_web_invoice_html()` from the new module
- **Removed dead code**: Orphaned duplicate methods at end of `ShopSettingsDialog` class (329 lines) that were never callable

## 3. Remaining Invoice Logic in Dialog

The following methods remain in `InvoicePreviewDialog` (total ~75 lines):

| Method | Role |
|---|---|
| `__init__` | Collects `repair_data`, loads `shop_settings`, calls `init_ui` |
| `init_ui` | Builds all UI widgets (radio buttons, preview QTextEdit, action buttons) |
| `print_invoice` | QPrinter/QPrintDialog workflow |
| `save_pdf` | QFileDialog + QPrinter PDF export |
| `update_preview` | Calls generator functions, sets HTML on `self.preview` |

**No HTML template, no CSS, no Persian string, no `jdatetime` usage remains in the dialog.** The dialog only orchestrates data collection, display, and print/save actions.

## 4. Risk Assessment

| Risk | Level | Mitigation |
|---|---|---|
| HTML output differs | **Low** | All f-string templates copied verbatim. Indentation within f-strings preserved exactly. |
| CSS/formatting differs | **Low** | CSS blocks copied as raw strings without any modification. |
| Persian text corruption | **Low** | Strings preserved in original f-string context; no encoding transformation applied. |
| Broken import | **Low** | `generate_print_invoice_html` / `generate_web_invoice_html` correctly imported and called in `update_preview`. |
| Dead code remnants | **None** | Dead duplicate methods verified removed; AST check passes. |
| Circular imports | **None** | `invoice_generator.py` imports only `jdatetime`, `Path`, `calculate_invoice_totals`, `get_status_color`, `STATUS_PENDING` — no backward import to `app.py`. |

## 5. Validation Checklist

- [x] Both files pass `py_compile` (syntax check)
- [x] Both files pass `ast.parse` (structure check)
- [x] No references to old `self.generate_print_invoice()` / `self.generate_web_invoice()` remain
- [x] All five UI/print/save methods remain in `InvoicePreviewDialog`
- [x] No UI widget code was touched
- [x] No CSS was altered
- [x] No Persian strings were altered
- [x] `jdatetime.date.today()` usage preserved in both functions
- [x] `calculate_invoice_totals` usage preserved in both functions
- [x] HTML f-string indentation matches original output exactly
- [x] Dead code (duplicate methods orphaned after `ShopSettingsDialog`) removed
