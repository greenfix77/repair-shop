# Customer Workflow Refactor

> Date: 2026-06-26
> Scope: Centralize all customer business logic into CustomerService

---

## Responsibilities Moved

### From RepairDialog → CustomerService

| Responsibility | Old Location | New Location |
|---|---|---|
| Phone lookup (save-time) | `validate_and_accept` → `find_by_phone()` | `resolve_customer()` line 54-57 |
| Name lookup (save-time) | `validate_and_accept` → `find_by_full_name()` | `resolve_customer()` line 59-71 |
| Duplicate detection | `validate_and_accept` inline (2 branches) | `resolve_customer()` line 54-71 |
| Customer creation | `validate_and_accept` inline `create_customer()` ×2 | `resolve_customer()` line 73-74 |
| Existing customer reuse decision | `validate_and_accept` inline (2 branches) | `resolve_customer()` line 63-71 |

### Removed from RepairDialog

| Removed Code | Lines (old) | Replacement |
|---|---|---|
| `phone = self.phone_input.text().strip()` | 312 | `_get_customer_data()` |
| `full_name = self.customer_name_input.text().strip()` | 313 | `_get_customer_data()` |
| `_sanitize_display_name(full_name)` | 314 | No longer needed |
| `if phone:` branch (lines 317-333) | 317-333 | `resolve_customer()` |
| `if full_name:` branch (lines 334-357) | 334-357 | `resolve_customer()` |
| `find_by_phone(phone)` call | 318 | internal to `resolve_customer` |
| `find_by_full_name(full_name)` call | 323, 342 | internal to `resolve_customer` |
| `create_customer(customer_data)` call ×2 | 331, 355 | internal to `resolve_customer` |
| Manual partial `setText` (name + phone only) | 326-327 | removed — now uses `populate_customer_fields` |

---

## Duplicated Logic Removed

### Duplicate A: Phone Lookup (3 → 1)

Before: `find_customer()` (phone auto-fill), `find_by_phone()` (save-time), inline in 2 branches.

After: Single `resolve_customer()` path via `_repo.get_by_phone()`.

### Duplicate B: Customer Creation (2 → 1)

Before: Two `create_customer()` call sites in `validate_and_accept`.

After: Single `_repo.create()` call inside `resolve_customer()`.

### Duplicate C: Phone Duplicate Detection (3 → 1)

Before: Phone auto-fill, Branch A, Branch B — each with slightly different lookup.

After: Single check in `resolve_customer()` at line 54-57.

### Duplicate D: Field Population (2 → 1)

Before: `populate_customer_fields()` (3 call sites) + manual partial `setText` (1 site).

After: `populate_customer_fields()` is the ONLY method that sets customer form fields.

---

## Final Workflow Diagram

```
RepairDialog
│
│  validate_and_accept()
│
├── Validate phone format
├── If edit mode → accept()
├── _get_customer_data() → dict
├── If no phone & no name → accept()
│
├── CustomerService.resolve_customer(data, confirm_cb)
│   │
│   ├── phone provided?
│   │   ├── YES → _repo.get_by_phone(phone)
│   │   │         └── found? → return existing
│   │   │
│   ├── full_name provided?
│   │   ├── YES → find_by_full_name(full_name)
│   │   │         └── found? → confirm? → return existing
│   │   │
│   ├── No match → generate_customer_code()
│   │             _repo.create(data)
│   │             → return new customer
│   │
│   └── → return customer dict (or None)
│
├── customer returned?
│   └── YES → populate_customer_fields(customer)
│
└── accept()


CustomerService public API (after refactor):

  resolve_customer(data, cb)    ← save-time orchestration (NEW)
  search_customers(query)       ← QCompleter search
  get_customer(id)              ← QCompleter PK lookup
  find_customer(phone)          ← phone auto-fill lookup
  find_by_phone(phone)          ← (kept for backward compat)
  find_by_full_name(name)       ← (kept for backward compat)
  create_customer(data)         ← (kept for backward compat)
  update_customer(id, data)     ← (kept for backward compat)
  get_all_customers()           ← (kept for backward compat)
  get_or_create_customer(data)  ← (kept for backward compat)
```

---

## Files Modified

- `services/customer_service.py` — added `resolve_customer()` method
- `ui/dialogs/repair_dialog.py` — `validate_and_accept()` now delegates to `resolve_customer()`

## Files Created

- `CUSTOMER_WORKFLOW_REFACTOR.md` — this document

