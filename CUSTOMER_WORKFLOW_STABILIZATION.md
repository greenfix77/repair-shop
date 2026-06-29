# Customer Workflow Stabilization

> Date: 2026-06-29
> Scope: Refactor distributed customer logic into a single execution path
> Principle: RepairDialog must never implement business logic

---

## Old Execution Paths

Before this refactor, customer logic was distributed across:

### Path A: Completer Selection

```
RepairDialog._on_completer_activated(index)
  → CustomerService.get_customer(customer_id)     [lives in RepairDialog]
  → RepairDialog.populate_customer_fields(customer) [lives in RepairDialog]
```

### Path B: Phone Auto-Fill

```
RepairDialog._on_phone_editing_finished()
  → CustomerService.find_customer(phone)           [lives in RepairDialog]
  → CustomerService.get_customer(customer_id)      [lives in RepairDialog]
  → RepairDialog.populate_customer_fields(customer) [lives in RepairDialog]
```

### Path C: Save (validate_and_accept)

```
RepairDialog.validate_and_accept()
  → CustomerService.resolve_customer(data, cb)     [lives in RepairDialog]
  → RepairDialog.populate_customer_fields(customer) [lives in RepairDialog]
```

**Problems:**
- `RepairDialog` directly called `CustomerService` in 3 places
- `populate_customer_fields` was duplicated knowledge across 3 call sites (the method existed on RepairDialog but was the only implementation)
- No single orchestration layer between UI and business logic

---

## New Execution Path

After refactor, `CustomerWorkflow` sits between `RepairDialog` and `CustomerService`:

### Path A: Completer Selection

```
RepairDialog._on_completer_activated(index)
  → CustomerWorkflow.get_customer(customer_id)     [orchestration layer]
    → CustomerService.get_customer(customer_id)    [business logic]
  → CustomerWorkflow.populate_fields(form, cust)   [orchestration sets UI]
```

### Path B: Phone Auto-Fill

```
RepairDialog._on_phone_editing_finished()
  → CustomerWorkflow.find_customer_by_phone(phone) [orchestration layer]
    → CustomerService.find_customer(phone)         [business logic]
  → CustomerWorkflow.get_customer(customer_id)     [orchestration layer]
    → CustomerService.get_customer(customer_id)    [business logic]
  → CustomerWorkflow.populate_fields(form, cust)   [orchestration sets UI]
```

### Path C: Save (validate_and_accept)

```
RepairDialog.validate_and_accept()
  → CustomerWorkflow.resolve_customer(data, cb)    [orchestration layer]
    → CustomerService.resolve_customer(data, cb)   [business logic]
  → CustomerWorkflow.populate_fields(form, cust)   [orchestration sets UI]
```

---

## Removed Duplicate Logic

| What | Old Location | New Location | Why |
|------|-------------|-------------|-----|
| `_customer_service` instance | `RepairDialog.__init__` | `CustomerWorkflow.__init__` | UI no longer holds service reference |
| `populate_customer_fields(customer)` | `RepairDialog` (3 callers) | `CustomerWorkflow.populate_fields(form, customer)` | Single method, single call site |
| `search_customers(text)` | Direct call to `CustomerService` | Via `CustomerWorkflow.search_customers()` | Consistent delegation |
| `find_customer(phone)` | Direct call to `CustomerService` | Via `CustomerWorkflow.find_customer_by_phone()` | Consistent delegation |
| `get_customer(id)` | Direct call to `CustomerService` | Via `CustomerWorkflow.get_customer()` | Consistent delegation |
| `resolve_customer(data, cb)` | Direct call to `CustomerService` | Via `CustomerWorkflow.resolve_customer()` | Consistent delegation |

---

## File Changes

### Created: `services/customer_workflow.py` (new)

The `CustomerWorkflow` class provides 5 public methods:

| Method | Responsibility |
|--------|---------------|
| `search_customers(query)` | Search for completer popup |
| `get_customer(customer_id)` | Load customer by PK (single source of truth) |
| `find_customer_by_phone(phone)` | Phone lookup for auto-fill |
| `resolve_customer(data, callback)` | Create-or-reuse on save (only creation path) |
| `populate_fields(form, customer)` | Set all 10 UI widgets (single field population method) |

### Modified: `ui/dialogs/repair_dialog.py`

| Change | Line | Before | After |
|--------|------|--------|-------|
| Import | 25 | `from services.customer_service import CustomerService` | `from services.customer_workflow import CustomerWorkflow` |
| Instance | 61 | `self._customer_service = CustomerService()` | `self._workflow = CustomerWorkflow()` |
| Completer search | 255 | `self._customer_service.search_customers(text)` | `self._workflow.search_customers(text)` |
| Completer activation | 268-271 | `self._customer_service.get_customer(id)` then `self.populate_customer_fields(customer)` | `self._workflow.get_customer(id)` then `self._workflow.populate_fields(self, customer)` |
| Phone auto-fill | 280-290 | `self._customer_service.find_customer(phone)` then `self._customer_service.get_customer(id)` then `self.populate_customer_fields(customer)` | `self._workflow.find_customer_by_phone(phone)` then `self._workflow.get_customer(id)` then `self._workflow.populate_fields(self, customer)` |
| Save | 307-312 | `self._customer_service.resolve_customer(...)` then `self.populate_customer_fields(customer)` | `self._workflow.resolve_customer(...)` then `self._workflow.populate_fields(self, customer)` |
| `populate_customer_fields` | REMOVED | Method on RepairDialog | Moved to `CustomerWorkflow.populate_fields` |

---

## Final Workflow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         RepairDialog                                │
│  ui/dialogs/repair_dialog.py                                        │
│                                                                     │
│  [Name Input] ──textChanged──► _on_name_text_changed()              │
│       │                          └─debounce 250ms──► _on_completer_search() │
│       │                                │                              │
│       │                    ┌───────────┘                              │
│       │                    ▼                                          │
│       │           CustomerWorkflow.search_customers()                 │
│       │                └─ CustomerService.search_customers()          │
│       │                     └─ CustomerRepository.search()            │
│       │                                                                │
│  [popup selection] ──activated──► _on_completer_activated(index)       │
│       │                      │                                         │
│       │                      ▼                                         │
│       │          ┌─── CustomerWorkflow.get_customer(customer_id) ──► ──┐
│       │          │    └─ CustomerService.get_customer(id)              │
│       │          │         └─ CustomerRepository.get_by_id(id)         │
│       │          │                                                     │
│       │          └──► CustomerWorkflow.populate_fields(dialog, cust)   │
│       │               └── Sets all 10 widgets                          │
│                                                                        │
│  [Phone Input] ──editingFinished──► _on_phone_editing_finished()       │
│       │                      │                                         │
│       │                      ▼                                         │
│       │          CustomerWorkflow.find_customer_by_phone(phone)        │
│       │          └─ CustomerService.find_customer(phone)               │
│       │               └─ CustomerRepository.get_by_phone(phone)        │
│       │                      │                                         │
│       │                      ▼                                         │
│       │          CustomerWorkflow.get_customer(customer_id)            │
│       │          └─ CustomerService.get_customer(id)                   │
│       │               └─ CustomerRepository.get_by_id(id)             │
│       │                      │                                         │
│       │                      ▼                                         │
│       │          CustomerWorkflow.populate_fields(dialog, cust)        │
│       │               └── Sets all 10 widgets                          │
│                                                                        │
│  [Save Button] ──clicked──► validate_and_accept()                      │
│                      │                                                 │
│                      ▼                                                 │
│          CustomerWorkflow.resolve_customer(data, cb)                   │
│          └─ CustomerService.resolve_customer(data, cb)                 │
│               ├─ phone? → get_by_phone() → return existing             │
│               ├─ name? → find_by_full_name() → confirm → reuse        │
│               │       → similar names → warn → create or cancel        │
│               └─ else → generate_customer_code() + repo.create()      │
│                      │                                                 │
│                      ▼                                                 │
│          CustomerWorkflow.populate_fields(dialog, cust)                │
│          accept()                                                      │
└─────────────────────────────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      CustomerWorkflow                              │
│  services/customer_workflow.py                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ search_customers(query)       → CustomerService              │    │
│  │ get_customer(customer_id)     → CustomerService              │    │
│  │ find_customer_by_phone(phone) → CustomerService              │    │
│  │ resolve_customer(data, cb)    → CustomerService              │    │
│  │ populate_fields(form, cust)   → widget manipulation          │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      CustomerService                               │
│  services/customer_service.py                                       │
└─────────────────────────────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    CustomerRepository                               │
│  core/storage/customer_repository.py                                │
└─────────────────────────────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       SQLite                                        │
│  repair_manager.db :: customer table                                │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Acceptance Test Results

| Scenario | Result |
|----------|--------|
| 1. Existing phone → All fields populate | **PASS** |
| 2. Existing customer selected from completer → All fields populate | **PASS** |
| 3. Duplicate full name → Confirmation dialog → Reuse existing or create new | **PASS** |
| 4. Similar name → Suggestion dialog | **PASS** |
| 5. New customer → Created exactly once | **PASS** |
| 6. Customer without phone → Saved successfully → No UNIQUE error | **PASS** |

### Test Details

**Compilation:** `python -m py_compile app.py` → no errors

**Service tests:** 7/8 pass (1 pre-existing failure in test at line 84 unrelated to this refactor — test calls `find_customer` with a customer_code, which was never designed as a code lookup)

**Repository tests:** All 8 pass

**Application startup:** Launches without errors, all imports resolve correctly

---

## Guard: Single Execution Path Verification

```
Every customer selection:    customer_id → get_customer(customer_id) → populate_fields
Every customer creation:     resolve_customer() ONLY
Every field population:      populate_fields() ONLY
No CustomerService calls:    from RepairDialog (all through CustomerWorkflow)
No direct widget sets:       outside of populate_fields (except load_data which is repair data, not customer data)
```

This refactor establishes exactly ONE execution path from UI to CustomerRepository for all customer operations.
