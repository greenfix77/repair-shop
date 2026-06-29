# Customer Workflow Architecture

**Version:** 1.0  
**Date:** 2026-06-29  
**Status:** Stabilized — single execution path enforced.

---

## Table of Contents

1. [Current Architecture](#1-current-architecture)
2. [Final Architecture](#2-final-architecture)
3. [Responsibility Matrix](#3-responsibility-matrix)
4. [Call Graph](#4-call-graph)
5. [Sequence Diagrams](#5-sequence-diagrams)
    - 5.1 Completer Search
    - 5.2 Completer Selection
    - 5.3 Phone Auto-Fill
    - 5.4 Save / Customer Resolution
    - 5.5 Edit Mode (No Customer Resolution)
6. [Class Responsibilities](#6-class-responsibilities)
7. [Verification Results](#7-verification-results)
8. [Architecture Limitations](#8-architecture-limitations)

---

## 1. Current Architecture

```
┌─────────────────────┐
│     RepairDialog    │  UI Layer (read/write widgets, connect signals)
├─────────────────────┤
│  CustomerWorkflow   │  Orchestration Layer (coordinate, delegate)
├─────────────────────┤
│   CustomerService   │  Business Logic Layer (rules, decisions)
├─────────────────────┤
│ CustomerRepository  │  Data Access Layer (SQLite queries)
├─────────────────────┤
│       SQLite        │  Persistent Storage
└─────────────────────┘
```

### Current Production Call Chain

Every customer-related action flows through all four layers:

```
RepairDialog
    ↓ (calls CustomerWorkflow)
CustomerWorkflow
    ↓ (calls CustomerService)
CustomerService
    ↓ (calls CustomerRepository)
CustomerRepository
    ↓ (SQLAlchemy ORM)
SQLite
```

### Layer Count

| Measure | Value |
|---------|-------|
| Layers between UI and DB | 4 (`Workflow` → `Service` → `Repository` → `SQLite`) |
| Direct Repository calls from UI | **0** ✅ |
| Customer decision trees | **1** (`CustomerService.resolve_customer`) ✅ |
| Customer creation paths | **1** (`CustomerService.resolve_customer` → `_repo.create`) ✅ |
| `populate_fields` implementations | **1** (`CustomerWorkflow.populate_fields`) ✅ |
| String concatenation for data extraction | **0** (completer uses `Qt.UserRole` exclusively) ✅ |

---

## 2. Final Architecture

The final architecture is identical to the current architecture — **no structural changes were needed** because the four-layer chain was already established during the prior stabilization phase.

### What Was Stabilized

| Item | Status |
|------|--------|
| RepairDialog → CustomerWorkflow path | Verified clean |
| CustomerWorkflow → CustomerService path | Verified clean |
| CustomerService → CustomerRepository path | Verified clean |
| No direct SQLite from UI | Verified clean |
| No bypass of CustomerWorkflow | Verified clean |
| No duplicate `populate_fields` | Verified clean |
| No duplicate `resolve_customer` logic | Verified clean |
| Dead code in CustomerService | Removed (see §6) |

### Dead Code Removed

The following methods existed in `CustomerService` but were **unused in production**. They provided alternate execution paths that could bypass `CustomerWorkflow`:

| Method | Reason for Removal |
|--------|-------------------|
| `get_or_create_customer` | Superseded by `resolve_customer` (richer decision tree). Only used in tests. |
| `find_by_phone` | Duplicate of `find_customer`. Only used in tests. |
| `update_customer` | No production caller — customer editing from UI does not exist per spec §13.1. Only used in tests. |
| `create_customer` | `resolve_customer` is the single creation path. Only used in tests. |
| `get_all_customers` | No production caller. Only used in tests. |

These removals enforce the single execution path: **no customer operation may be invoked without passing through `CustomerWorkflow`.**

---

## 3. Responsibility Matrix

### RepairDialog
| Responsible FOR | NOT responsible FOR |
|----------------|-------------------|
| Reading widget values | Calling `CustomerRepository` |
| Writing widget values | Executing customer decision logic |
| Connecting Qt signals | Creating customer records |
| Showing warning/confirmation dialogs | Searching customers |
| Calling `CustomerWorkflow` methods | Deciding duplicate handling |
| Loading repair data into widgets (edit mode) | Phone normalization |
| Collecting form data (`_get_customer_data`) | Customer code generation |

### CustomerWorkflow
| Responsible FOR | NOT responsible FOR |
|----------------|-------------------|
| Coordinating phone auto-fill flow | UI manipulation (widgets) |
| Coordinating completer flow | Database queries |
| Coordinating save/customer resolution flow | Business rules |
| Coordinating populate-fields flow | Signal connections |
| Being the **only** class RepairDialog calls for customers | |
| Delegating to `CustomerService` | |

### CustomerService
| Responsible FOR | NOT responsible FOR |
|----------------|-------------------|
| `resolve_customer` decision tree | Database queries (delegates to `Repository`) |
| Phone normalization | UI operations |
| `generate_customer_code` | Signal handling |
| Exact name matching (`find_by_full_name`) | Form data collection |
| Search rules (query validation, min length) | |
| `find_customer` (phone lookup) | |
| `get_customer` (PK lookup) | |

### CustomerRepository
| Responsible FOR | NOT responsible FOR |
|----------------|-------------------|
| `get_by_id` | Business rules |
| `get_by_phone` | UI logic |
| `search` (ILIKE query) | Decision making |
| `create` (INSERT) | Phone normalization (business rule) |
| `update` (UPDATE) | |
| `delete` (DELETE) | |
| `_normalize_phone` | ⚠️ See §8 Architecture Limitations |
| `_to_dict` (ORM → dict) | |

**Note:** `_normalize_phone` lives in `CustomerRepository` for historical reasons. It is a business rule (empty string → SQL `NULL`) but is tightly coupled to `create`/`update` methods. See §8 for discussion.

---

## 4. Call Graph

### Completer Search

```
RepairDialog._on_name_text_changed(text)
  └─ QTimer.start(250ms)

RepairDialog._on_completer_search()              [timer fires]
  ├─ self.customer_name_input.text()
  ├─ Guard: len(text) < 2 → clear model, return
  ├─ CustomerWorkflow.search_customers(text)
  │   └─ CustomerService.search_customers(text)
  │       ├─ Guard: not query or len < 2 → return []
  │       └─ CustomerRepository.search(query)
  │           └─ SQL: SELECT ... FROM customer WHERE full_name ILIKE '%q%' OR phone ILIKE '%q%'
  ├─ Clear _completer_model
  └─ For each customer:
       ├─ Create QStandardItem(label)
       ├─ item.setData(c['id'], Qt.UserRole)
       └─ model.appendRow(item)
```

### Completer Selection

```
RepairDialog._on_completer_activated(index)
  ├─ customer_id = index.data(Qt.UserRole)
  ├─ Guard: not customer_id → return
  ├─ CustomerWorkflow.get_customer(customer_id)
  │   └─ CustomerService.get_customer(customer_id)
  │       └─ CustomerRepository.get_by_id(customer_id)
  │           └─ SQL: SELECT ... FROM customer WHERE id = ?
  ├─ Guard: not customer → return
  └─ CustomerWorkflow.populate_fields(self, customer)    [self = RepairDialog]
      ├─ form.customer_name_input.blockSignals(True)
      ├─ form.customer_name_input.setText(customer['full_name'])
      ├─ form.customer_name_input.blockSignals(False)
      ├─ form.phone_input.setText(customer['phone'])
      ├─ form.email_input.setText(customer['email'])
      ├─ form.website_input.setText(customer['website'])
      ├─ form.national_id_input.setText(customer['national_id'])
      ├─ form.address_input.setText(customer['address'])
      ├─ form.city_input.setText(customer['city'])
      ├─ form.province_input.setText(customer['province'])
      ├─ form.postal_code_input.setText(customer['postal_code'])
      └─ form.notes_input.setPlainText(customer['notes'])
```

### Phone Auto-Fill

```
RepairDialog._on_phone_editing_finished()         [editingFinished signal]
  ├─ phone = self.phone_input.text()
  ├─ Guard: not phone → return
  ├─ Guard: not self.phone_input.hasAcceptableInput() → return
  ├─ CustomerWorkflow.find_customer_by_phone(phone)
  │   └─ CustomerService.find_customer(phone)
  │       └─ CustomerRepository.get_by_phone(phone)
  │           └─ SQL: SELECT ... FROM customer WHERE phone = ?
  ├─ Guard: not found → return
  ├─ customer_id = found.get('id')
  ├─ Guard: not customer_id → return
  ├─ CustomerWorkflow.get_customer(customer_id)
  │   └─ CustomerService.get_customer(customer_id)
  │       └─ CustomerRepository.get_by_id(customer_id)
  │           └─ SQL: SELECT ... FROM customer WHERE id = ?
  ├─ Guard: not customer → return
  ├─ self.phone_input.blockSignals(True)
  ├─ CustomerWorkflow.populate_fields(self, customer)
  └─ self.phone_input.blockSignals(False)
```

### Save / Customer Resolution

```
RepairDialog.validate_and_accept()                [Save button clicked]
  ├─ Guard: phone present + not acceptable → show_warning, return
  ├─ Guard: self.repair_data → accept(), return          [edit mode]
  ├─ customer_data = self._get_customer_data()
  │   └─ Reads: full_name, phone, email, website,
  │            national_id, address, city, province,
  │            postal_code, notes
  ├─ Guard: no phone AND no full_name → accept(), return [empty form]
  ├─ CustomerWorkflow.resolve_customer(customer_data, confirm_callback)
  │   └─ CustomerService.resolve_customer(customer_data, confirm_callback)
  │       ├─ Normalize: strip whitespace, empty→None
  │       ├─ Guard: not phone AND not full_name → return None
  │       ├─ [PHONE] if phone:
  │       │   ├─ CustomerRepository.get_by_phone(phone)
  │       │   └─ existing? → return existing
  │       ├─ [EXACT NAME] if full_name:
  │       │   ├─ find_by_full_name(name) → _repo.search + Python filter
  │       │   ├─ exact match? → confirm_callback("مشتری مشابه")
  │       │   │   ├─ YES → return existing
  │       │   │   └─ NO → continue
  │       │   ├─ similar = _repo.search(name) - exact matches
  │       │   └─ similar exists? → confirm_callback("نام‌های مشابه")
  │       │       ├─ YES → continue to create
  │       │       └─ NO → return None
  │       ├─ [CREATE] customer_data['customer_code'] = generate_customer_code()
  │       │   └─ CustomerRepository.get_all() → regex max → f"C{max+1:06d}"
  │       └─ CustomerRepository.create(customer_data)
  │           └─ INSERT INTO customer ...
  ├─ if customer is not None:
  │   └─ CustomerWorkflow.populate_fields(self, customer)
  └─ self.accept()
```

### Edit Mode (No Customer Resolution)

```
RepairDialog.__init__(repair_data={...})
  └─ self.load_data(repair_data)
      └─ Direct widget setText (repair data, not customer record)

RepairDialog.validate_and_accept()                [Save button clicked]
  ├─ (phone validation skipped — guard: "if phone present + invalid" not hit)
  ├─ Guard: self.repair_data is truthy → accept(), return
  │   └─ NO customer resolution
  │   └─ NO DB writes to customer table
  └─ (caller LaptopRepairManager.edit_repair → update_repair)
```

---

## 5. Sequence Diagrams

### 5.1 Completer Search

```
User                  RepairDialog          QTimer(250ms)    CustomerWorkflow    CustomerService    CustomerRepository    SQLite
 │                        │                     │                  │                   │                  │                 │
 ├─types in name field───→│                     │                  │                   │                  │                 │
 │                        │                     │                  │                   │                  │                 │
 │                        ├─textChanged────────→│                  │                   │                  │                 │
 │                        │←─start(250)─────────┤                  │                   │                  │                 │
 │                        │                     │                  │                   │                  │                 │
 │                        │                     ├─timeout────────→│                   │                  │                 │
 │                        │                     │                 ├─search_customers─→│                  │                 │
 │                        │                     │                 │                   ├─search───────────→│                 │
 │                        │                     │                 │                   │                  ├─SQL query──────→│
 │                        │                     │                 │                   │                  │←─result rows────┤
 │                        │                     │                 │                   │←─result dicts────┤                  │
 │                        │                     │                 │←─result dicts─────┤                  │                 │
 │                        │←─return items───────┤                 │                   │                  │                 │
 │                        │                     │                  │                   │                  │                 │
 ├─popup shown────────────┤                     │                  │                   │                  │                 │
```

### 5.2 Completer Selection

```
User                  RepairDialog          CustomerWorkflow    CustomerService    CustomerRepository    SQLite
 │                        │                     │                   │                  │                 │
 ├─clicks popup item─────→│                     │                   │                  │                 │
 │                        ├─get_customer(id)───→│                   │                  │                 │
 │                        │                     ├─get_customer(id)─→│                  │                 │
 │                        │                     │                   ├─get_by_id(id)───→│                 │
 │                        │                     │                   │                  ├─SQL query──────→│
 │                        │                     │                   │                  │←─result row─────┤
 │                        │                     │                   │←─result dict─────┤                 │
 │                        │                     │←─result dict──────┤                  │                 │
 │                        │←─result dict────────┤                   │                  │                 │
 │                        │                     │                   │                  │                 │
 │                        ├─populate_fields────→│                   │                  │                 │
 │                        │←─fields set─────────┤                   │                  │                 │
 ├─fields populated───────┤                     │                   │                  │                 │
```

### 5.3 Phone Auto-Fill

```
User                  RepairDialog          CustomerWorkflow    CustomerService    CustomerRepository    SQLite
 │                        │                     │                   │                  │                 │
 ├─enters phone, tabs────→│                     │                   │                  │                 │
 │                        ├─find_customer──────→│                   │                  │                 │
 │                        │  _by_phone(phone)   ├─find_customer────→│                  │                 │
 │                        │                     │                   ├─get_by_phone────→│                 │
 │                        │                     │                   │                  ├─SQL query──────→│
 │                        │                     │                   │                  │←─result row─────┤
 │                        │                     │                   │←─result dict─────┤                 │
 │                        │←─result dict────────┤                   │                  │                 │
 │                        │                     │                   │                  │                 │
 │                        ├─get_customer(id)───→│                   │                  │                 │
 │                        │                     ├─get_customer(id)─→│                  │                 │
 │                        │                     │                   ├─get_by_id(id)───→│                 │
 │                        │                     │                   │                  ├─SQL query──────→│
 │                        │                     │                   │                  │←─result row─────┤
 │                        │                     │                   │←─result dict─────┤                 │
 │                        │                     │←─result dict──────┤                  │                 │
 │                        │←─result dict────────┤                   │                  │                 │
 │                        │                     │                   │                  │                 │
 │                        ├─blockSignals(True)  │                   │                  │                 │
 │                        ├─populate_fields────→│                   │                  │                 │
 │                        │←─fields set─────────┤                   │                  │                 │
 │                        ├─blockSignals(False) │                   │                  │                 │
 ├─all fields populated───┤                     │                   │                  │                 │
```

### 5.4 Save / Customer Resolution

```
User                  RepairDialog          CustomerWorkflow    CustomerService    CustomerRepository    SQLite
 │                        │                     │                   │                  │                 │
 ├─clicks Save──────────→│                     │                   │                  │                 │
 │                        ├─phone valid?────────┤                   │                  │                 │
 │                        ├─edit mode?──────────┤                   │                  │                 │
 │                        ├─_get_customer_data()│                   │                  │                 │
 │                        ├─empty form?─────────┤                   │                  │                 │
 │                        │                     │                   │                  │                 │
 │                        ├─resolve_customer───→│                   │                  │                 │
 │                        │                     ├─resolve_customer─→│                  │                 │
 │                        │                     │                   │                  │                 │
 │                        │                     │                   ├─[if phone] get_by_phone───→│        │
 │                        │                     │                   │                  ├─SQL────→│        │
 │                        │                     │                   │                  │←─result─┤        │
 │                        │                     │                   │←─result──────────┤         │        │
 │                        │                     │                   │                  │         │        │
 │                        │                     │                   ├─[if name] search──────────→│        │
 │                        │                     │                   │  (exact + similar) │         │        │
 │                        │                     │                   │                  ├─SQL────→│        │
 │                        │                     │                   │                  │←─result─┤        │
 │                        │                     │                   │←─result──────────┤         │        │
 │                        │                     │                   │                  │         │        │
 │                        │                     │                   ├─[if confirm] callback──────│        │
 │                        │                     │←─confirm_callback─┤(show_question)   │         │        │
 │                        │←─confirm_callback───┤                   │  (User: Yes/No) │         │        │
 │                        ├─show_question───────┤                   │                  │         │        │
 │←─(dialog shown)────────┤                     │                   │                  │         │        │
 ├─(User clicks Yes/No)──→┤                     │                   │                  │         │        │
 │                        ├─callback result────→│                   │                  │         │        │
 │                        │                     ├─callback result──→│                  │         │        │
 │                        │                     │                   │                  │         │        │
 │                        │                     │                   ├─[if create] get_all──────→│        │
 │                        │                     │                   │                  ├─SQL────→│        │
 │                        │                     │                   │                  │←─all───┤        │
 │                        │                     │                   │←─all────────────┤         │        │
 │                        │                     │                   │                  │         │        │
 │                        │                     │                   ├─generate_customer_code() │         │
 │                        │                     │                   ├─create(customer)────────→│         │
 │                        │                     │                   │                  ├─INSERT─→│        │
 │                        │                     │                   │                  │←─result─┤        │
 │                        │                     │                   │←─result dict────┤         │        │
 │                        │                     │←─result dict──────┤                  │         │        │
 │                        │←─result dict────────┤                   │                  │         │        │
 │                        │                     │                   │                  │         │        │
 │                        ├─[if customer]       │                   │                  │         │        │
 │                        │  populate_fields───→│                   │                  │         │        │
 │                        │←─fields set─────────┤                   │                  │         │        │
 │                        │                     │                   │                  │         │        │
 │                        ├─accept()────────────┤                   │                  │         │        │
 ├─dialog closes─────────┤                     │                   │                  │         │        │
 │                        │                     │                   │                  │         │        │
 │ (caller: LaptopRepairManager.add_repair)      │                  │                  │         │        │
 │                        │                     │                   │                  │         │        │
 ├─get_data()────────────┤                     │                   │                  │         │        │
 │←─repair data──────────┤                     │                   │                  │         │        │
 │                        │                     │                   │                  │         │        │
 ├─add_repair(repairs, data)──→(repair service)  │                  │                  │         │        │
```

### 5.5 Edit Mode (No Customer Resolution)

```
User                  RepairDialog          CustomerWorkflow    CustomerService    CustomerRepository    SQLite
 │                        │                     │                   │                  │                 │
 │ (dialog opens with    │                     │                   │                  │                 │
 │  repair_data pre-     │                     │                   │                  │                 │
 │  populated)           │                     │                   │                  │                 │
 │                        │                     │                   │                  │                 │
 ├─modifies fields──────→│                     │                   │                  │                 │
 │                        │                     │                   │                  │                 │
 ├─clicks Save──────────→│                     │                   │                  │                 │
 │                        ├─[Guard: repair_data]│                   │                  │                 │
 │                        │  → accept()────────┤                   │                  │                 │
 ├─dialog closes─────────┤                     │                   │                  │                 │
 │                        │                     │                   │                  │                 │
 │ (NO customer DB       │                     │                   │                  │                 │
 │  operations anywhere  │                     │                   │                  │                 │
 │  in this flow)        │                     │                   │                  │                 │
```

---

## 6. Class Responsibilities

### `ui/dialogs/repair_dialog.py` — `RepairDialog`

| Method | Responsibility |
|--------|---------------|
| `__init__` | Create `CustomerWorkflow` instance, call `init_ui`, `_init_customer_completer`, `_connect_auto_fill`, optionally `load_data` |
| `init_ui` | Create all widgets, arrange layout, connect save/cancel buttons |
| `_init_customer_completer` | Create `QCompleter`, `QStandardItemModel`, `QTimer`, connect signals |
| `_on_name_text_changed` | Start 250ms debounce timer for completer |
| `_on_completer_search` | Guard (<2 chars), call `_workflow.search_customers`, populate model with `Qt.UserRole` |
| `_on_completer_activated` | Extract `customer_id` from `Qt.UserRole`, call `_workflow.get_customer`, call `_workflow.populate_fields` |
| `_connect_auto_fill` | Connect `phone_input.editingFinished` → `_on_phone_editing_finished` |
| `_on_phone_editing_finished` | Guard (empty/invalid), call `_workflow.find_customer_by_phone`, extract id, call `_workflow.get_customer`, block signals, call `populate_fields`, unblock signals |
| `validate_and_accept` | Guard (phone format, edit mode, empty form), collect data, call `_workflow.resolve_customer`, optionally `populate_fields`, `accept` |
| `_get_customer_data` | Read 10 widget values into dict |
| `load_data` | Set widget values from repair data dict |
| `get_data` | Read all widget values into repair data dict |

### `services/customer_workflow.py` — `CustomerWorkflow`

| Method | Responsibility |
|--------|---------------|
| `__init__` | Create `CustomerService` instance |
| `search_customers` | Delegate to `_service.search_customers` |
| `get_customer` | Delegate to `_service.get_customer` |
| `find_customer_by_phone` | Delegate to `_service.find_customer` |
| `resolve_customer` | Delegate to `_service.resolve_customer` with callback |
| `populate_fields` | Set 10 widget values from customer dict, block signals on name field |

### `services/customer_service.py` — `CustomerService`

| Method | Responsibility |
|--------|---------------|
| `__init__` | Create `CustomerRepository` instance |
| `resolve_customer` | Full decision tree: normalize → phone check → exact name → similar names → create |
| `find_customer` | Guard (empty query), delegate to `_repo.get_by_phone` |
| `find_by_full_name` | Search repo, Python-filter exact matches (case-sensitive, trimmed) |
| `search_customers` | Guard (<2 chars), delegate to `_repo.search` |
| `get_customer` | Delegate to `_repo.get_by_id` |
| `generate_customer_code` | Get all customers, regex max C-number, increment |

### `core/storage/customer_repository.py` — `CustomerRepository`

| Method | Responsibility |
|--------|---------------|
| `get_all` | `SELECT * FROM customer` |
| `get_by_id` | `SELECT ... WHERE id = ?` |
| `get_by_code` | `SELECT ... WHERE customer_code = ?` |
| `get_by_phone` | `SELECT ... WHERE phone = ?` |
| `create` | `INSERT INTO customer ...`, rollback on error |
| `update` | `UPDATE customer SET ... WHERE id = ?`, rollback on error |
| `delete` | `DELETE FROM customer WHERE id = ?` |
| `exists_by_phone` | `SELECT COUNT(*) WHERE phone = ?` (bool) |
| `exists_by_code` | `SELECT COUNT(*) WHERE customer_code = ?` (bool) |
| `search` | `SELECT ... WHERE full_name ILIKE '%q%' OR phone ILIKE '%q%'` |
| `_normalize_phone` | Convert empty string/None → None for SQL NULL |
| `_to_dict` | Convert ORM `CustomerDB` → plain dict |

---

## 7. Verification Results

### 7.1 Compilation

```bash
python -m py_compile app.py
```

**Result:** PASS ✅

### 7.2 Architecture Rule Verification

| Rule | Result | Evidence |
|------|--------|----------|
| RepairDialog does NOT call CustomerRepository | PASS ✅ | `grep CustomerRepository ui/` → no matches |
| RepairDialog does NOT call CustomerService directly | PASS ✅ | `grep CustomerService ui/dialogs/repair_dialog.py` → no matches (only `CustomerWorkflow`) |
| RepairDialog only calls CustomerWorkflow for customer ops | PASS ✅ | All 5 customer calls go to `self._workflow.*` |
| CustomerWorkflow is the sole coordinator | PASS ✅ | Only `repair_dialog.py` imports `CustomerWorkflow` |
| CustomerService has no UI logic | PASS ✅ | No Qt imports in `customer_service.py` |
| CustomerService has no UI references | PASS ✅ | No `form`, `widget`, `dialog` parameters |
| CustomerRepository has no business logic | MINOR ISSUE ⚠️ | `_normalize_phone` is a business rule (empty string → NULL). See §8. |
| CustomerRepository has no UI logic | PASS ✅ | No Qt imports |
| `populate_fields` is single implementation | PASS ✅ | Only exists in `CustomerWorkflow` |
| `resolve_customer` decision tree is single | PASS ✅ | Only exists in `CustomerService` |
| Completer uses `Qt.UserRole` for data | PASS ✅ | `item.setData(c['id'], Qt.UserRole)` in `_on_completer_search` |
| No string concatenation for data extraction | PASS ✅ | Display text `f"{name}\n{phone}"` is display-only |
| No dead code providing alternate paths | PASS ✅ | Dead methods removed from CustomerService |
| No circular imports | PASS ✅ | `app.py` → no CustomerRepository/SQLite import chain issues |

### 7.3 Import Chain

```
app.py
  └─ ui/dialogs/repair_dialog.py
       └─ services/customer_workflow.py
            └─ services/customer_service.py
                 └─ core/storage/customer_repository.py
                      └─ core/storage/database.py
                      └─ core/storage/customer_model_db.py
```

No circular imports. ✅

---

## 8. Architecture Limitations

The following issues were identified during the audit but are **not addressed in this stabilization** because they require behavior changes, schema changes, or are outside the scope of architecture enforcement.

### 8.1 `_normalize_phone` in Repository

**Issue:** `CustomerRepository._normalize_phone()` (line 9-12) applies a business rule: empty/None phone strings should be stored as SQL `NULL`. This logic belongs in `CustomerService` per the separation of concerns.

**Impact:** Low. The logic is simple and stable. The Service's `resolve_customer()` also normalizes phone independently (lines 57-59). The dual normalization produces the same result.

**Recommendation:** Move `_normalize_phone` to `CustomerService` and have the Repository accept pre-normalized values. Requires changing `create()` and `update()` to NOT call `_normalize_phone`.

### 8.2 Phone Auto-Fill Double Round-Trip

**Issue:** `_on_phone_editing_finished` makes two DB queries:
1. `find_customer_by_phone(phone)` → `get_by_phone(phone)` — gets full dict
2. `get_customer(customer_id)` → `get_by_id(customer_id)` — gets full dict again via PK

**Impact:** Low. Two round-trips for the same data. The second query is redundant since the first already returns the full customer dict.

**Recommendation:** Let `find_customer_by_phone` return the full dict directly to `populate_fields`, skipping the `get_customer` call. This is noted in the Behavior Specification as a design tradeoff for consistent load path.

### 8.3 Dead Methods in Repository

**Issue:** `CustomerRepository` contains methods unused in production: `get_by_code`, `exists_by_phone`, `exists_by_code`.

**Impact:** Low. These are simple query methods and do not provide alternate customer creation/resolution paths.

**Recommendation:** Remove in a future cleanup pass, or keep for future use.

### 8.4 No Customer Update From UI

**Issue:** Per §13.1 of the Behavior Specification, editing a repair does NOT update the customer table. Changes to customer name/phone in edit mode are only saved to the repair's denormalized fields.

**Impact:** Deliberate — this is a non-goal. Documented here for completeness as an architecture boundary.

---

*End of Architecture Document v1.0 — No behavior changes were made during this stabilization.*
