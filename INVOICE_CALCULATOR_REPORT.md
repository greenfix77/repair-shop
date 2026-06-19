# Invoice Calculator Refactoring Report

## Extracted Function

`calculate_invoice_totals(repair_data: dict) -> dict` in `services/invoice_calculator.py`

Returns dict with keys: `parts_cost`, `labor_cost`, `subtotal`, `tax_rate`, `tax_amount`, `discount`, `total`.

## Files Modified

| File | Lines Changed |
|------|--------------|
| `app.py` | Import added + 3 calculation blocks replaced |
| `services/invoice_calculator.py` | Created (new file) |

## Duplicated Calculations Removed

| Location | Old Lines | New Lines | Lines Saved |
|----------|-----------|-----------|-------------|
| `InvoicePreviewDialog.generate_print_invoice` | 6 (data.get ×4 + calculate_invoice) | 8 (fin destructure) | −2* |
| `InvoicePreviewDialog.generate_web_invoice` | 6 | 8 | −2* |
| `RepairDialog.calculate_total` | 3 (widget math) | 5 (dict build + fin) | −2* |

*Net increase in lines but calculation logic is centralized and no longer duplicated.

**Important:** The three call sites are now identical in their calculation — they all delegate to `calculate_invoice_totals()`. The logic exists in exactly one place.

## Remaining Duplicated Calculations

| Location | Description | Why Not Changed |
|----------|-------------|-----------------|
| `services/table_service.py` `build_table_rows()` | Same formula (parts+labor → subtotal → tax → total) | Uses `services/calculations.calculate_invoice()`, which is a different extraction |
| `app.py` orphan `generate_web_invoice` (module-level dead code) | Identical to InvoicePreviewDialog version | Dead code; not in scope |
| `app.py` InvoicePreviewDialog HTML templates (×2) | Financial values rendered as HTML | HTML not to be changed |

## Risk Level

**Low.** All replacements are pure refactorings:
- `calculate_invoice_totals()` has no side effects, no I/O, no UI dependencies
- Input dict keys match existing repair data structure
- Output dict preserves all existing variable names used in HTML templates
- Output values use identical arithmetic (`dict.get()` defaults, formulas, types)

## Static Verification

- `python -m py_compile services/invoice_calculator.py` — OK
- `python -m py_compile app.py` — OK
- Runtime unit test with 3 scenarios (dict style, widget style, empty dict) — all assertions passed
