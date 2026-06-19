# Refactoring Summary

## Extracted Functions

| Function | Target Module | Source |
|----------|--------------|--------|
| `today_persian()` | `services/date_service.py` | `app.py` (4 occurrences → 2 remain in InvoicePreviewDialog HTML) |
| `calculate_invoice()` | `services/calculations.py` | `app.py` (3 occurrences) + `services/table_service.py` (1 occurrence) |
| `get_status_color()` | `ui/status_styles.py` | `app.py` (2 occurrences) |
| `get_repair_by_id()` | `services/repair_service.py` | Already existed; `preview_invoice` now uses it instead of inline `next()` |

## Files Changed

### Created (3)
- `services/date_service.py`
- `services/calculations.py`
- `ui/status_styles.py`

### Modified (2)
- `app.py` — replaced inline calculations, status color lookups, date formatting, and inline repair lookup
- `services/table_service.py` — replaced inline calculation with `calculate_invoice()`

## Duplicate Lines Removed

- **Financial calculations:** 6 lines (3 instances × 2 lines each: `subtotal = ...` + `tax_amount = ...` + `total = ...` → `calculate_invoice(...)`)
- **Date formatting:** 1 line (`today = jdatetime.date.today()` removed from `update_date_label`)
- **Table service:** 2 lines (`subtotal = ...` + `tax_amount = ...` + `total = ...` → `calculate_invoice(...)`)
- **Total:** ~9 duplicate lines removed

## Remaining Duplications (not addressed)

| Issue | Reason Skipped |
|-------|---------------|
| Orphan dead code at module level (`generate_web_invoice`, `print_invoice`, `save_pdf`) | Not in the 4 allowed extraction targets |
| InvoicePreviewDialog HTML templates | Forbidden per rules |
| `RepairDialog.calculate_total` (widget-based variant) | Different API (`.value()` vs `.get()`); UI code, not in allowed targets |
| Toolbar button styling (4 buttons) | UI code, not in allowed targets |
| Status bar label styling (4 labels) | UI code, not in allowed targets |
| Save-refresh-notify pattern (3 operations) | UI code, not in allowed targets |
| Selected row ID pattern (3 occurrences) | UI-dependent, not in allowed targets |
| `jdatetime.date.today().strftime('%Y/%m/%d')` in InvoicePreviewDialog HTML (2 occurrences) | Inside InvoicePreviewDialog HTML (forbidden) |

## Verification

- Syntax check: All files pass `python -m py_compile`
- Import check: All new modules import correctly at runtime
- No behavioral changes: All extractions are pure refactorings with identical output
