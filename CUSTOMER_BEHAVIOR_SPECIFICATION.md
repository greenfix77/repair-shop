# Customer Workflow Behavior Specification

> Date: 2026-06-29
> Version: 1.0
> Status: Specification (no code changes)
> Principle: This document is the single source of truth for all future customer workflow implementation.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Layer Responsibilities](#2-layer-responsibilities)
3. [Event Flow Diagram](#3-event-flow-diagram)
4. [Scenario Specifications](#4-scenario-specifications)
5. [Field Mapping](#5-field-mapping)
6. [Completer Specification](#6-completer-specification)
7. [Phone Auto-Fill Specification](#7-phone-auto-fill-specification)
8. [Duplicate Detection Decision Tree](#8-duplicate-detection-decision-tree)
9. [Save Workflow Specification](#9-save-workflow-specification)
10. [State Transitions](#10-state-transitions)
11. [Error Handling](#11-error-handling)
12. [SQLite Interaction Map](#12-sqlite-interaction-map)
13. [Non-Goals](#13-non-goals)

---

## 1. Architecture Overview

### Layered Architecture

```
┌──────────────────────────────────────────────────┐
│  Layer 1: UI (RepairDialog)                       │
│  File: ui/dialogs/repair_dialog.py                │
│  Responsibility: Widgets, signals, user events    │
│  Must NOT: Implement business logic               │
│  Must NOT: Call CustomerService directly          │
│  Must NOT: Parse displayed text                   │
├──────────────────────────────────────────────────┤
│  Layer 2: Orchestration (CustomerWorkflow)        │
│  File: services/customer_workflow.py              │
│  Responsibility: Workflow routing, field pop.     │
│  Single source of truth for:                      │
│    - Loading customer by ID                       │
│    - Setting form fields                          │
│    - Delegating to CustomerService                │
├──────────────────────────────────────────────────┤
│  Layer 3: Business Logic (CustomerService)        │
│  File: services/customer_service.py               │
│  Responsibility: Rules, validation, resolution    │
│  Allowed to: Decide create vs reuse               │
│  Allowed to: Generate customer codes              │
├──────────────────────────────────────────────────┤
│  Layer 4: Data Access (CustomerRepository)        │
│  File: core/storage/customer_repository.py        │
│  Responsibility: SQL queries, normalization       │
│  Allowed to: CRUD operations only                 │
├──────────────────────────────────────────────────┤
│  Layer 5: Persistence (SQLite)                    │
│  File: repair_manager.db :: customer table        │
│  Responsibility: Data storage, UNIQUE constraints │
└──────────────────────────────────────────────────┘
```

### Layer Communication Contract

| Caller | Callee | Allowed Methods |
|--------|--------|-----------------|
| `RepairDialog` | `CustomerWorkflow` | `search_customers`, `get_customer`, `find_customer_by_phone`, `resolve_customer`, `populate_fields` |
| `CustomerWorkflow` | `CustomerService` | `search_customers`, `find_customer`, `get_customer`, `resolve_customer` |
| `CustomerService` | `CustomerRepository` | `search`, `get_by_phone`, `get_by_id`, `get_by_code`, `create`, `update`, `get_all` |
| `CustomerRepository` | SQLite | SQL via SQLAlchemy ORM |

### Prohibited Patterns

- `RepairDialog` must NEVER call `CustomerService` directly
- `RepairDialog` must NEVER call `CustomerRepository` directly
- `CustomerService` must NEVER import `CustomerWorkflow`
- `CustomerService` must NEVER access UI types (QWidget, QLineEdit, etc.)
- `CustomerRepository` must NEVER contain business logic or validation rules

---

## 2. Layer Responsibilities

### 2.1 RepairDialog (UI Layer)

**Owns:**
- Widget creation and layout
- Qt signal connections
- User event handlers (keyboard, focus, clicks)
- Dialog acceptance/rejection
- Loading repair data into form fields (edit mode)
- Reading form data for repair saving (`get_data`, `_get_customer_data`)

**Signal connections (exactly these):**

| Signal | Slot | Trigger |
|--------|------|---------|
| `customer_name_input.textChanged` | `_on_name_text_changed` | Every keystroke in name field |
| `_completer_timer.timeout` | `_on_completer_search` | 250ms after last keystroke |
| `_completer.activated[QModelIndex]` | `_on_completer_activated` | User clicks completer suggestion |
| `phone_input.editingFinished` | `_on_phone_editing_finished` | Phone field loses focus with valid input |
| `save_btn.clicked` | `validate_and_accept` | Save button clicked |
| `cancel_btn.clicked` | `reject` | Cancel button clicked |

**Must NOT do:**
- Implement duplicate detection logic
- Implement customer creation logic
- Directly query CustomerRepository
- Parse or split completer display text
- Concatenate customer field values
- Call `setText` on customer widgets directly (except `load_data` for repair data)

### 2.2 CustomerWorkflow (Orchestration Layer)

**Owns:**
- Single method for loading customer by ID: `get_customer(customer_id)`
- Single method for setting customer form fields: `populate_fields(form, customer)`
- Routing phone auto-fill through `get_customer` for consistent load path
- Delegating all business logic to `CustomerService`

**Public methods (exactly these):**

| Method | Input | Output | Purpose |
|--------|-------|--------|---------|
| `search_customers(query)` | `str` (≥2 chars) | `List[Dict]` | Populate completer model |
| `get_customer(customer_id)` | `int` | `Optional[Dict]` | Load by PK — single source of truth |
| `find_customer_by_phone(phone)` | `str` | `Optional[Dict]` | Phone lookup for auto-fill |
| `resolve_customer(data, callback)` | `Dict, Callable` | `Optional[Dict]` | Create-or-reuse on save |
| `populate_fields(form, customer)` | `RepairDialog, Dict` | `None` | Set all 10 form widgets |

**`populate_fields` contract:**
- Accepts any object with the expected widget attribute names
- Blocks `customer_name_input` signals during `setText`
- Sets each widget from the corresponding customer dict key
- Must be the ONLY code that sets customer widget values
- Never concatenates values
- Never parses strings

### 2.3 CustomerService (Business Logic Layer)

**Owns:**
- Customer resolution decision tree (phone → name → similar → create)
- Duplicate detection rules
- Customer code generation
- Find-by-full-name exact matching

**Public methods used by CustomerWorkflow:**

| Method | Input | Output | Purpose |
|--------|-------|--------|---------|
| `search_customers(query)` | `str` | `List[Dict]` | ILIKE search on name and phone |
| `find_customer(phone)` | `str` | `Optional[Dict]` | Exact phone lookup |
| `get_customer(customer_id)` | `int` | `Optional[Dict]` | PK lookup |
| `resolve_customer(data, callback)` | `Dict, Callable` | `Optional[Dict]` | Create-or-reuse decision tree |

**`resolve_customer` decision order (exact, sequential):**

```
1. Normalize: strip whitespace, empty → None
2. If no phone AND no full_name → return None
3. If phone exists → get_by_phone(phone) → if found → return existing
4. If full_name exists:
   a. find_by_full_name(full_name) → exact match (ILIKE search + Python exact filter)
   b. If exact match found → confirm_callback("مشتری مشابه", ...)
      - If confirmed → return existing
      - If declined → continue (do NOT create yet)
   c. search(full_name) → filter out exact match → remaining are "similar"
   d. If similar names exist → confirm_callback("نام‌های مشابه", ...)
      - If not proceed → return None (user cancelled)
      - If proceed → continue
5. Generate customer_code
6. _repo.create(data) → return new customer
```

### 2.4 CustomerRepository (Data Access Layer)

**Owns:**
- All SQL queries (parameterized via SQLAlchemy)
- Phone normalization (empty → NULL)
- Dict serialization from ORM rows

**Methods:**

| Method | SQL | Returns |
|--------|-----|---------|
| `get_all()` | `SELECT * FROM customer` | `List[Dict]` |
| `get_by_id(id)` | `SELECT * FROM customer WHERE id = ?` | `Optional[Dict]` |
| `get_by_code(code)` | `SELECT * FROM customer WHERE customer_code = ?` | `Optional[Dict]` |
| `get_by_phone(phone)` | `SELECT * FROM customer WHERE phone = ?` | `Optional[Dict]` |
| `search(query)` | `SELECT * FROM customer WHERE full_name ILIKE ? OR phone ILIKE ?` | `List[Dict]` |
| `create(data)` | `INSERT INTO customer (...) VALUES (...)` | `Dict` (with generated id) |
| `update(id, data)` | `UPDATE customer SET ... WHERE id = ?` | `Optional[Dict]` |
| `delete(id)` | `DELETE FROM customer WHERE id = ?` | `bool` |
| `exists_by_phone(phone)` | `SELECT 1 FROM customer WHERE phone = ? LIMIT 1` | `bool` |
| `exists_by_code(code)` | `SELECT 1 FROM customer WHERE customer_code = ? LIMIT 1` | `bool` |

**Phone normalization rule:**
- Input: `None` → stored as SQL `NULL`
- Input: `""` (empty string) → stored as SQL `NULL`
- Input: `"  "` (whitespace) → stored as SQL `NULL`
- Input: `"09121234567"` → stored as `"09121234567"`

This ensures multiple customers without a phone can coexist despite the `UNIQUE` constraint on `phone`.

### 2.5 CustomerDB (ORM Model)

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | `Integer` | PK, autoincrement |
| `customer_code` | `String` | UNIQUE, default `""` |
| `full_name` | `String` | default `""` |
| `phone` | `String` | UNIQUE, no default (NULL allowed) |
| `email` | `String` | default `""` |
| `website` | `String` | default `""` |
| `national_id` | `String` | default `""` |
| `address` | `String` | default `""` |
| `city` | `String` | default `""` |
| `province` | `String` | default `""` |
| `postal_code` | `String` | default `""` |
| `notes` | `String` | default `""` |
| `created_at` | `String` | default `""` |
| `updated_at` | `String` | default `""` |

---

## 3. Event Flow Diagram

### Complete Signal-Flow Map

```
                          ┌───────────────────────┐
                          │    RepairDialog        │
                          │    (User Actions)      │
                          └───────┬───────────────┘
                                  │
          ┌───────────────────────┼───────────────────────┐
          ▼                       ▼                       ▼
   ┌──────────────┐      ┌───────────────┐      ┌──────────────┐
   │ Name Input   │      │ Phone Input   │      │ Save Button  │
   │ textChanged  │      │editingFinished│      │ clicked      │
   └───────┬──────┘      └───────┬───────┘      └───────┬──────┘
           │                     │                      │
           ▼                     ▼                      ▼
   ┌──────────────┐      ┌───────────────┐      ┌──────────────┐
   │_on_name_text_│      │_on_phone_     │      │validate_and_ │
   │_changed()    │      │editing_finished│      │accept()      │
   └───────┬──────┘      └───────┬───────┘      └───────┬──────┘
           │                     │                      │
           ▼                     ▼                      │
   ┌──────────────┐      ┌───────────────┐              │
   │Timer.start   │      │workflow.      │              │
   │(250ms)       │      │find_customer_ │              │
   └───────┬──────┘      │by_phone(phone)│              │
           │             └───────┬───────┘              │
           ▼                     │                      │
   ┌──────────────┐              ▼                      │
   │timer.timeout │      ┌───────────────┐              │
   └───────┬──────┘      │ service.      │              │
           │             │ find_customer │              │
           ▼             └───────┬───────┘              │
   ┌────────────────┐           │                      │
   │_on_completer_  │           ▼                      │
   │search()        │    ┌───────────────┐              │
   └───────┬────────┘    │ repo.         │              │
           │             │ get_by_phone  │              │
           ▼             └───────┬───────┘              │
   ┌────────────────┐           │                      │
   │ workflow.      │           ▼                      │
   │ search_customers│    ┌───────────────┐              │
   └───────┬────────┘    │ customer_id   │              │
           │             │ extracted     │              │
           ▼             └───────┬───────┘              │
   ┌────────────────┐           │                      │
   │ _completer_    │           ▼                      │
   │ model populated│    ┌───────────────┐              │
   └───────┬────────┘    │ workflow.     │              │
           │             │ get_customer  │              │
           ▼             └───────┬───────┘              │
   ┌────────────────┐           │                      │
   │User clicks     │           ▼                      │
   │suggestion      │    ┌───────────────┐              │
   └───────┬────────┘    │ workflow.     │              │
           │             │ populate_fields│              │
           ▼             └───────┬───────┘              │
   ┌────────────────┐           │                      │
   │_on_completer_  │           ▼                      │
   │activated(index)│    ┌───────────────┐              │
   └───────┬────────┘    │ ALL 10        │              │
           │             │ fields set    │              │
           ▼             └───────────────┘              │
   ┌────────────────┐                                   │
   │ workflow.      │                                   │
   │ get_customer   │                                   │
   │ (customer_id)  │                                   │
   └───────┬────────┘                                   │
           │                                            │
           ▼                                            │
   ┌────────────────┐                                   │
   │ workflow.      │                                   │
   │ populate_fields│                                   │
   └────────────────┘                                   │
                                                        │
           ┌────────────────────────────────────────────┘
           ▼
   ┌──────────────────────────────────┐
   │ workflow.resolve_customer(data,cb)│
   └───────────────┬──────────────────┘
                   │
                   ▼
          ┌────────────────┐
          │ service.        │
          │ resolve_customer│
          └───────┬────────┘
                   │
         ┌─────────┼──────────┐
         ▼         ▼          ▼
   ┌────────┐ ┌────────┐ ┌────────┐
   │get_by_ │ │find_by_ │ │create  │
   │phone   │ │full_name│ │(new)   │
   └────────┘ └────────┘ └────────┘
                   │
                   ▼
   ┌──────────────────────────────────┐
   │ workflow.populate_fields(form,   │
   │  customer)                       │
   └──────────────────────────────────┘
                   │
                   ▼
             ┌──────────┐
             │ accept() │
             └──────────┘
```

---

## 4. Scenario Specifications

### Scenario 1: Phone Auto-Fill

```
Trigger: User types phone "09123456789" and tabs away / clicks elsewhere
──────────────────────────────────────────────────────────────────────

Step 1: QLineEdit.editingFinished fires
  Widget: phone_input
  Guard: phone_input.text() is empty? → STOP
  Guard: phone_input.hasAcceptableInput() is false? → STOP
  (Validator: ^0\d{10}$ — 11 digits starting with 0)

Step 2: CustomerWorkflow.find_customer_by_phone(phone)
  → CustomerService.find_customer(phone)
    → CustomerRepository.get_by_phone(phone)
      → SQL: SELECT * FROM customer WHERE phone = '09123456789'
  Result: Optional[Dict] — customer record or None
  Guard: None? → STOP (silently — no notification)

Step 3: Extract customer_id from found record
  customer_id = found['id']
  Guard: None or 0? → STOP

Step 4: CustomerWorkflow.get_customer(customer_id)
  → CustomerService.get_customer(customer_id)
    → CustomerRepository.get_by_id(customer_id)
      → SQL: SELECT * FROM customer WHERE id = <customer_id>
  Result: Optional[Dict] — full customer record or None
  Guard: None? → STOP

Step 5: Block phone_input signals
  phone_input.blockSignals(True) — prevent recursive editingFinished

Step 6: CustomerWorkflow.populate_fields(dialog, customer)
  → Sets all 10 widgets from customer dict

Step 7: Unblock phone_input signals
  phone_input.blockSignals(False)

Result: ALL 10 customer fields populated from database.
──────────────────────────────────────────────────────────────────────

Expected state after completion:
  customer_name_input = customer.full_name
  phone_input = customer.phone
  email_input = customer.email
  website_input = customer.website
  national_id_input = customer.national_id
  address_input = customer.address
  city_input = customer.city
  province_input = customer.province
  postal_code_input = customer.postal_code
  notes_input = customer.notes

NO dialog appears.
NO error shown.
NO field contains data from another field.
NO field contains concatenated text.
```

### Scenario 2: Completer Selection

```
Trigger: User types ≥2 characters in name field, popup appears, user clicks item
────────────────────────────────────────────────────────────────────────────────

Phase A — Debounce:
  Step 1: textChanged fires on every keystroke
  Step 2: _on_name_text_changed(text):
    - _completer.setCompletionPrefix(text) — updates filter
    - _completer_timer.start(250) — restarts 250ms debounce
  Repeat for each keystroke (timer keeps resetting)

Phase B — Search (fires once, 250ms after last keystroke):
  Step 3: _completer_timer.timeout fires
  Step 4: _on_completer_search():
    - Guard: len(text.strip()) < 2? → clear model, STOP
    - CustomerWorkflow.search_customers(text)
      → CustomerService.search_customers(text)
        → CustomerRepository.search(text)
          → SQL: WHERE full_name ILIKE '%text%' OR phone ILIKE '%text%'
    - Clear _completer_model
    - For each customer c in results:
      * label = f"{c['full_name']}\n{phone_or_empty}"
      * item = QStandardItem(label)
      * item.setData(c['id'], Qt.UserRole)  ← customer_id stored here
      * _completer_model.appendRow(item)
    - QCompleter popup displays (filtered by prefix internally)

Phase C — Selection (user clicks):
  Step 5: QCompleter.activated[QModelIndex] fires
    - Index is a proxy model index (internal QCompleter QSortFilterProxyModel)
  Step 6: _on_completer_activated(index):
    - customer_id = index.data(Qt.UserRole)
      ← Directly from stored data. NO display text parsing.
    - Guard: no customer_id? → STOP (silently)
    - CustomerWorkflow.get_customer(customer_id)
      → CustomerService.get_customer(customer_id)
        → CustomerRepository.get_by_id(customer_id)
          → SQL: SELECT * FROM customer WHERE id = <id>
    - Guard: customer is None? → STOP (silently)
    - CustomerWorkflow.populate_fields(dialog, customer)
      → Sets ALL 10 widgets

Result: ALL 10 customer fields populated from database.
────────────────────────────────────────────────────────────────────────────────

Expected state after completion:
  customer_name_input = customer.full_name (clean, no emoji, no newline, no phone)
  phone_input = customer.phone
  email_input = customer.email
  website_input = customer.website
  national_id_input = customer.national_id
  address_input = customer.address
  city_input = customer.city
  province_input = customer.province
  postal_code_input = customer.postal_code
  notes_input = customer.notes

The displayed popup text "{full_name}\n{phone}" is NEVER used as data source.
The popup is display-only. All data comes from DB via customer_id.
```

### Scenario 3: New Customer Save

```
Trigger: User fills form with new customer data, clicks Save
────────────────────────────────────────────────────────────────

Step 1: save_btn.clicked fires
Step 2: validate_and_accept():
  Guard: phone present but invalid format? → show_warning, STOP
  Guard: self.repair_data (edit mode)? → accept() immediately, STOP
  (Edit mode skips ALL customer resolution — no customer table writes)

Step 3: _get_customer_data() → reads all 10 widget values into dict

Step 4: Guard: no phone AND no full_name → accept() directly (empty repair)

Step 5: CustomerWorkflow.resolve_customer(data, callback)
  → CustomerService.resolve_customer(data, callback)

Step 5a: Normalize
  - phone = data['phone'].strip()
  - full_name = data['full_name'].strip()
  - If no phone → phone = None; data['phone'] = ''
  - If no full_name → full_name = None

Step 5b: No phone AND no full_name → return None
  Not reached (Step 4 guard already caught this)

Step 5c: Phone present → get_by_phone(phone)
  - Not found (new customer) → continue

Step 5d: Full_name present → find_by_full_name(full_name)
  - Search: ILIKE + Python exact filter
  - Not found → continue

Step 5e: No similar names → continue

Step 5f: Create customer
  - customer_code = generate_customer_code() → "C000001" style
  - _repo.create(data)
    → SQL: INSERT INTO customer (...) VALUES (...)
  - Returns new customer dict with auto-generated id

Step 6: Customer returned (non-None)
  → CustomerWorkflow.populate_fields(dialog, customer)
    → Sets all 10 widgets (refreshed from DB, has id and customer_code)

Step 7: accept() → dialog closes with QDialog.Accepted

Result: Exactly one customer created in SQLite.
────────────────────────────────────────────────────────────────

Expected outcomes:
  - New row in customer table
  - customer_code auto-generated (C followed by 6-digit zero-padded number)
  - phone stored as NULL if empty (via _normalize_phone)
  - No SQLite UNIQUE constraint violation
  - Dialog returns Accepted
  - app.py receives accepted → calls get_data() → saves repair
```

### Scenario 4: Duplicate Customer Name Save

```
Trigger: User types existing customer name "علی احمدی", clicks Save
─────────────────────────────────────────────────────────────────────

Step 1-4: Same as Scenario 3

Step 5a: Normalize
Step 5b: Phone absent → skip phone lookup

Step 5c: Full_name present → find_by_full_name("علی احمدی")
  → CustomerRepository.search("علی احمدی")
    → SQL: WHERE full_name ILIKE '%علی احمدی%' OR phone ILIKE '%علی احمدی%'
  → Python filter: exact match on full_name
  → Returns [existing_customer]  (list with 1 item)

Step 5d: confirm_callback("مشتری مشابه", "مشتری مشابهی وجود دارد.\nاز همان مشتری استفاده شود؟")
  → show_question dialog appears (Yes/No)

  BRANCH A: User clicks Yes
    → Return existing_customer  ← REUSE, no new customer
    → Skip to Step 6

  BRANCH B: User clicks No
    → Continue to Step 5e  ← User explicitly wants new customer

Step 5e (if user clicked No):
  → search("علی احمدی") → filter out exact match
  → If similar names exist:
    → confirm_callback("نام‌های مشابه", "...")
      BRANCH A: User clicks Yes (ادامه) → proceed to create
      BRANCH B: User clicks No (انصراف) → return None → skip populate → accept

Step 5f (if user proceeded):
  → generate_customer_code()
  → _repo.create(data)
  → Returns new customer (DUPLICATE name, different customer_code)

Step 6: If customer returned → populate_fields
Step 7: accept()

Result: 
  BRANCH A: Existing customer reused. NO new customer created.
  BRANCH B (proceed): New customer created. Duplicate name, different codes.
  BRANCH B (cancel): Dialog still accepts. Repair saved without customer data.
─────────────────────────────────────────────────────────────────────────────────

CRITICAL BEHAVIOR NOTE:
  When user clicks "No" on exact match and "Cancel" on similar names warning,
  resolve_customer returns None, populate_fields is skipped, but
  validate_and_accept still calls accept(). The repair is saved WITHOUT
  customer resolution. This is existing behavior.
```

### Scenario 5: Similar Names (Completer)

```
Trigger: Multiple customers with similar names exist
  Customer A: "علی احمدی", phone "09121234567"
  Customer B: "علی رضایی", phone "09127654321"
────────────────────────────────────────────────────────────────

Phase A — Type "علی":
  - textChanged fires for each character
  - 250ms debounce
  - search_customers("علی") → ILIKE '%علی%' on full_name and phone
  - Both Customer A and Customer B match
  - _completer_model gets 2 rows:
    Row 0: label = "علی احمدی\n09121234567", Qt.UserRole = A.id
    Row 1: label = "علی رضایی\n09127654321", Qt.UserRole = B.id
  - QCompleter popup shows both with two-line display

Phase B — User selects "علی رضایی":
  - activated[QModelIndex] fires
  - customer_id = B.id  ← from Qt.UserRole, NOT from display text
  - get_customer(B.id)
  - populate_fields(dialog, customer_B)
  - Result: All fields populated with Customer B's data

Result: No ambiguity. exact customer selected via customer_id.
────────────────────────────────────────────────────────────────

KEY BEHAVIOR:
  The completer popup shows all matching customers regardless of sorting
  order (results are in DB return order). The user distinguishes by
  looking at the phone number on the second line.
  The customer_id in Qt.UserRole is the ONLY data carrier.
  The display text is NEVER used for data extraction.
```

### Scenario 6: Customer Without Phone

```
Trigger: User creates customer with no phone number
────────────────────────────────────────────────────────

Step 1: User fills name "رضا بدون تلفن", leaves phone empty
Step 2: User clicks Save
Step 3: validate_and_accept():
  - phone empty → skip phone format validation
  - _get_customer_data() → phone = ""
  - Guard: full_name present → continue

Step 4: resolve_customer(data, callback):
  - phone = "".strip() → ""
  - phone = None (normalized)
  - data['phone'] = ''  (set to empty string for storage)

Step 5: No phone → skip get_by_phone()
Step 6: find_by_full_name("رضا بدون تلفن") → not found → continue
Step 7: No similar → continue
Step 8: generate_customer_code() → "C00000N"
Step 9: _repo.create(data):
  - phone = _normalize_phone('') → None
  - SQL: INSERT INTO customer (...) VALUES (..., NULL, ...)
  - No UNIQUE constraint violation because phone is NULL
    (SQLite UNIQUE allows multiple NULLs)
Step 10: Returns new customer dict

Result: Customer created successfully.
────────────────────────────────────────────────────────

Expected outcomes:
  - phone stored as SQL NULL
  - No UNIQUE constraint violation
  - Multiple customers can have empty phone
  - Customer is fully functional in all workflows
```

### Scenario 7: Phone Edited — Refreshed Fields

```
Trigger: Customer fields already populated (from completer or previous auto-fill)
         User changes phone to a different existing customer's phone
────────────────────────────────────────────────────────────────────────────────

Initial state:
  customer_name_input = "علی احمدی"
  phone_input = "09121234567"
  All other fields populated with علی احمدی's data

Step 1: User changes phone_input to "09127654321"
Step 2: User tabs away (editingFinished fires)

Step 3: _on_phone_editing_finished():
  - phone = "09127654321"
  - hasAcceptableInput() → True (valid 11-digit format)

Step 4: find_customer_by_phone("09127654321")
  → Found: customer for "علی رضایی"

Step 5: customer_id = found['id'] (B.id, not A.id)

Step 6: get_customer(customer_id) → returns Customer B's full record

Step 7: populate_fields(dialog, customer_B):
  - customer_name_input.setText("علی رضایی") ← UPDATED
  - phone_input.setText("09127654321")
  - email, website, national_id, address, city, province, postal_code, notes
    ← ALL UPDATED to Customer B's values

Result: ALL fields refreshed with new customer's data.
────────────────────────────────────────────────────────────────────────────────

Expected outcomes:
  - Every field reflects the new customer (not just name and phone)
  - Signal blocking prevents recursive auto-fill trigger
  - No partial population (all 10 fields updated)
  - Previous customer's data completely replaced
```

---

## 5. Field Mapping

### Widget-to-Field Map

| Customer Entity Field | UI Widget | Widget Type | Tab Location |
|-----------------------|-----------|-------------|--------------|
| `full_name` | `customer_name_input` | `QLineEdit` | Main tab (row 0) |
| `phone` | `phone_input` | `QLineEdit` | Main tab (row 1) |
| `email` | `email_input` | `QLineEdit` | Customer info tab (row 0) |
| `website` | `website_input` | `QLineEdit` | Customer info tab (row 1) |
| `national_id` | `national_id_input` | `QLineEdit` | Customer info tab (row 2) |
| `address` | `address_input` | `QLineEdit` | Customer info tab (row 3) |
| `city` | `city_input` | `QLineEdit` | Customer info tab (row 4) |
| `province` | `province_input` | `QLineEdit` | Customer info tab (row 5) |
| `postal_code` | `postal_code_input` | `QLineEdit` | Customer info tab (row 6) |
| `notes` | `notes_input` | `QTextEdit` | Notes tab (row 0) |

### Widget Constraints

| Widget | Validator | Max Length | Format |
|--------|-----------|------------|--------|
| `phone_input` | `QRegularExpressionValidator(r'^0\d{10}$')` | 11 | `09123456789` |

All other inputs are plain `QLineEdit` or `QTextEdit` with no validators.

### Reading Widgets (`_get_customer_data`)

```python
{
    'full_name': customer_name_input.text().strip(),
    'phone': phone_input.text().strip(),
    'email': email_input.text().strip(),
    'website': website_input.text().strip(),
    'national_id': national_id_input.text().strip(),
    'address': address_input.text().strip(),
    'city': city_input.text().strip(),
    'province': province_input.text().strip(),
    'postal_code': postal_code_input.text().strip(),
    'notes': notes_input.toPlainText().strip(),
}
```

### Writing Widgets (`populate_fields`)

Each widget receives exactly one value from the customer dict:
- No concatenation of multiple fields into one widget
- No splitting of values across multiple widgets
- No parsing of display text
- `customer_name_input` signals are blocked during write to prevent recursive completer search
- `notes_input` uses `setPlainText` (QTextEdit API)

### Rules

1. Every field must be written individually by its key
2. No two fields may share the same value source
3. No value may be transformed/parsed before being written
4. The customer dict is the SINGLE source of truth for field values
5. Repair data loading (`load_data`) is exempt — it loads repair-specific fields (customer_name, phone) which are denormalized copies, not customer entity data

---

## 6. Completer Specification

### 6.1 Trigger Conditions

| Condition | Behavior |
|-----------|----------|
| Text length < 2 | Popup hidden, model cleared |
| Text length ≥ 2 | Debounce 250ms, then search |
| Backspace to < 2 | Popup hidden, model cleared |
| No matches | Empty popup (no items) |
| Matches found | Popup appears (filtered by prefix) |

### 6.2 Timing

- Debounce interval: **250ms** (single-shot QTimer)
- Timer restarts on every keystroke
- Search executes exactly once per debounce period

### 6.3 Search Algorithm

```
search_customers(query):
  Guard: query is None or len(query) < 2 → return []
  → CustomerRepository.search(query)
    → SQL: WHERE full_name ILIKE '%query%' OR phone ILIKE '%query%'
  → Returns List[Dict] — ALL matches (no limit)

Matching:
  - Case-insensitive (ILIKE)
  - Contains match (wildcards on both sides)
  - Searches BOTH full_name and phone
  - If query matches only phone, the customer still appears
```

### 6.4 Sorting

- Results returned in database order (no explicit ORDER BY)
- Current behavior: insertion order (SQLite default)

### 6.5 Popup Display

**Display format:**
```
Line 1: {full_name}          (larger font, right-aligned)
Line 2: {phone}              (smaller font, gray #666666, right-aligned)
```

**Rules:**
- NO emojis (`👤`, `📞`, or any other)
- NO formatting characters except `\n` as line separator
- Line 2 is empty string if phone is unavailable (no phone placeholder text)
- Display is handled by custom `CompleterItemDelegate` (QStyledItemDelegate)

**Layout:**
- Direction: `RightToLeft`
- Delegate padding: 8px horizontal, 4px vertical
- Row height: 2 × font height + 12px
- First line font: pointSize + 1
- Second line font: pointSize - 1, color #666666

### 6.6 Data Storage Per Item

Each `QStandardItem` stores:
- `Qt.DisplayRole` → `"{full_name}\n{phone_or_empty}"` (display only)
- `Qt.UserRole` → `customer_id` (integer, the SINGLE source of truth)

### 6.7 Selection Behavior

When user selects an item:
1. `activated[QModelIndex]` signal fires
2. The index is from the **proxy model** (QCompleter's internal `QSortFilterProxyModel`)
3. `index.data(Qt.UserRole)` → directly returns `customer_id`
4. The `customer_id` is then used to load the full customer via `get_customer(customer_id)`
5. Display text is NEVER accessed for data extraction

### 6.8 Duplicate Handling

If the same customer matches both name and phone, they appear once (it's a single DB row).

If two customers have the same name but different phones, both appear (two rows).

If the exact same customer_id appears twice (impossible — PK is unique), the model handles it at the Qt level.

### 6.9 QCompleter Configuration

```
caseSensitivity:     Qt.CaseInsensitive
filterMode:         Qt.MatchContains
completionMode:     QCompleter.PopupCompletion
model:              QStandardItemModel (self._completer_model)
                    Items carry customer_id in Qt.UserRole
popup delegate:     CompleterItemDelegate (custom two-line rendering)
popup direction:    Qt.RightToLeft
```

---

## 7. Phone Auto-Fill Specification

### 7.1 Trigger

| Event | Widget | Signal |
|-------|--------|--------|
| User finishes editing phone field | `phone_input` | `editingFinished` |

`editingFinished` fires when:
- Widget loses focus (tab, click elsewhere)
- User presses Enter/Return

It does NOT fire on every keystroke (unlike `textChanged`).

### 7.2 Guards

```
Guard 1: phone_input.text() is empty? → STOP (silent)
Guard 2: phone_input.hasAcceptableInput() is False? → STOP (silent)
```

The validator `^0\d{10}$` ensures only valid 11-digit Iranian phone numbers starting with 0 pass the guard.

### 7.3 Lookup Flow

```
1. find_customer_by_phone(phone)
   → get_by_phone(phone) → exact match on phone column
   Guard: None? → STOP (silent — no notification for unknown phone)

2. Extract customer_id = found['id']
   Guard: None or 0? → STOP

3. get_customer(customer_id)
   → get_by_id(customer_id) → PK lookup
   Guard: None? → STOP

4. populate_fields(dialog, customer)
```

### 7.4 Signal Safety

- `phone_input.blockSignals(True)` BEFORE `populate_fields`
- `phone_input.blockSignals(False)` AFTER `populate_fields`
- This prevents the `setText` call inside `populate_fields` from triggering another `editingFinished` event

### 7.5 Silent Failure

When the phone is not found in the database, the method returns silently. No warning, no error, no dialog. The user simply continues typing, and the phone field retains whatever the user typed.

---

## 8. Duplicate Detection Decision Tree

### resolve_customer Full Decision Tree

```
resolve_customer(customer_data, confirm_callback)
│
├── [NORMALIZE]
│   phone    = customer_data.get('phone', '').strip()
│   name     = customer_data.get('full_name', '').strip()
│   if not phone:    phone = None;  data['phone'] = ''
│   if not name:     name = None
│
├── [GUARD] not phone AND not name?
│   └── return None
│
├── [PHONE CHECK] phone exists?
│   ├── existing = _repo.get_by_phone(phone)
│   └── existing? ──► return existing   ← DUPLICATE PHONE, IMMEDIATE RETURN
│
├── [EXACT NAME] name exists?
│   ├── exact = find_by_full_name(name)
│   │   ├── _repo.search(name)
│   │   └── Python filter: c['full_name'].strip() == name
│   │
│   ├── exact match found?
│   │   ├── confirm_callback("مشتری مشابه", "مشتری مشابهی وجود دارد.\nاز همان مشتری استفاده شود؟")
│   │   │
│   │   ├── User clicks YES (مشتری مشابه)
│   │   │   └── return existing   ← REUSE EXISTING
│   │   │
│   │   └── User clicks NO (مشتری جدید)
│   │       └── continue to similar check
│   │
│   └── no exact match?
│       └── continue to similar check
│
├── [SIMILAR NAMES] search(name)
│   ├── similar = _repo.search(name)
│   ├── filter: remove exact name match from results
│   │
│   └── similar names exist?
│       ├── confirm_callback("نام‌های مشابه", "نام‌های مشابهی یافت شد:\n{names}\n\nآیا ادامه می‌دهید؟")
│       │
│       ├── User clicks YES (ادامه)
│       │   └── continue to create
│       │
│       └── User clicks NO (انصراف)
│           └── return None   ← USER CANCELLED
│
└── [CREATE NEW]
    ├── customer_data['customer_code'] = generate_customer_code()
    │   └── repo.get_all() → find max C-number → increment → "C00000N"
    └── return _repo.create(customer_data)
```

### Priority Summary

```
Priority 1: Phone match     → return EXISTING (no dialog)
Priority 2: Exact name      → dialog: reuse or continue
Priority 3: Similar name    → dialog: continue or cancel
Priority 4: No match        → CREATE NEW
```

### Key Behavioral Rules

1. **Phone takes priority** over name. If phone matches, the customer is returned immediately. No name check.
2. **Exact name match** requires user confirmation to reuse. If user declines, the system falls through to similar name check, NOT to immediate creation.
3. **Similar name warning** gives the user a final chance to cancel. If cancelled, `None` is returned.
4. **Creation only happens** after all checks pass and user has confirmed continuation past warnings.
5. **No phone + no name** → `None` (caught by guard, caller accepts empty form).

---

## 9. Save Workflow Specification

### 9.1 Complete Save Sequence

```
validate_and_accept()
│
├── [1] Phone format validation
│     phone present + invalid format → show_warning → return (stay on dialog)
│
├── [2] Edit mode check
│     self.repair_data exists → accept() → return (NO customer resolution)
│     (Edit mode saves repair data but NEVER touches customer table)
│
├── [3] Collect form data
│     customer_data = _get_customer_data()
│     Reads all 10 widget values into dict
│
├── [4] Empty form guard
│     no phone AND no full_name → accept() (save empty repair)
│
├── [5] Resolve customer
│     result = CustomerWorkflow.resolve_customer(data, confirm_callback)
│     → Full decision tree (Section 8)
│
├── [6] Populate fields (if customer returned)
│     if result is not None:
│         CustomerWorkflow.populate_fields(dialog, result)
│     (If None: user cancelled → skip population)
│
└── [7] Accept dialog
      accept()
      (ALWAYS called, even if resolve_customer returned None)
```

### 9.2 Edit Mode Behavior

When `self.repair_data` is set (edit mode):
- `validate_and_accept` calls `accept()` immediately at Step 2
- NO customer resolution occurs
- NO customer lookup occurs
- NO customer creation occurs
- The customer table is NEVER updated
- Only the repair data (from `get_data()`) is saved

This means:
- Editing a repair's customer name does NOT update the customer table
- Editing a repair's phone does NOT update the customer table
- There is NO mechanism in the current UI to update customer data

### 9.3 Save Outcomes Summary

| Input | DB Outcome | Dialog Result |
|-------|-----------|---------------|
| New customer (phone + name) | New customer created + repair saved | Accepted |
| New customer (name only) | New customer created (phone=NULL) + repair saved | Accepted |
| New customer (phone only) | New customer created + repair saved | Accepted |
| Existing phone | Existing customer reused + repair saved | Accepted |
| Existing exact name (Yes) | Existing customer reused + repair saved | Accepted |
| Existing exact name (No, then cancel) | No customer, repair saved without resolution | Accepted |
| Empty form | No customer, empty repair saved | Accepted |
| Edit mode (any data) | No customer table write, repair updated | Accepted |

---

## 10. State Transitions

### Dialog State Machine

```
                  ┌─────────────┐
                  │   CREATED   │
                  │  (__init__) │
                  └──────┬──────┘
                         │
                         ▼
                  ┌─────────────┐
                  │   OPENED    │
                  │ (exec_ call)│
                  └──────┬──────┘
                         │
           ┌─────────────┼────────────────┐
           ▼             ▼                ▼
    ┌──────────┐  ┌──────────┐    ┌──────────┐
    │  EDITING │  │  EDITING │    │  EDITING │
    │  NAME    │  │  PHONE   │    │  OTHER   │
    └────┬─────┘  └────┬─────┘    └────┬─────┘
         │             │               │
         ▼             ▼               │
    ┌──────────┐  ┌──────────┐         │
    │COMPLETER │  │ AUTO-    │         │
    │ POPUP    │  │ FILL     │         │
    │ SHOWN    │  │ TRIGGERED│         │
    └────┬─────┘  └────┬─────┘         │
         │             │               │
         ▼             ▼               │
    ┌──────────┐  ┌──────────┐         │
    │SELECTED  │  │ FIELDS   │         │
    │ → FIELDS │  │POPULATED │         │
    │POPULATED │  │          │         │
    └──────────┘  └──────────┘         │
         │             │               │
         └─────────────┼───────────────┘
                       │
                       ▼
                ┌──────────────┐
                │ SAVE CLICKED │
                │ (validating) │
                └──────┬───────┘
                       │
           ┌───────────┼───────────────┐
           ▼           ▼               ▼
    ┌──────────┐ ┌──────────┐   ┌──────────┐
    │ VALID    │ │ INVALID  │   │ EDIT     │
    │→ RESOLVE │ │ PHONE    │   │ MODE     │
    │ CUSTOMER │ │→ WARNING │   │→ ACCEPT  │
    └────┬─────┘ └──────────┘   └──────────┘
         │
         ▼
    ┌──────────┐
    │ CUSTOMER │
    │ RESOLVED │
    └────┬─────┘
         │
    ┌────┴────┐
    ▼         ▼
  [HAS CUST] [NO CUST]
    │         │
    ▼         ▼
  POPULATE   SKIP
  FIELDS     POPULATE
    │         │
    └────┬────┘
         ▼
    ┌──────────┐
    │ ACCEPTED │
    │ (dialog  │
    │ closes)  │
    └──────────┘
         │
         ▼
    ┌──────────┐
    │ SAVED IN │
    │ app.py   │
    └──────────┘
```

### State Transition Triggers

| From State | To State | Trigger |
|------------|----------|---------|
| CREATED | OPENED | `dialog.exec_()` called from `app.py` |
| OPENED | EDITING NAME | User clicks name input |
| OPENED | EDITING PHONE | User clicks phone input |
| EDITING NAME | COMPLETER POPUP SHOWN | User types ≥2 chars, 250ms debounce, search returns results |
| EDITING NAME | (stay in EDITING NAME) | User types <2 chars or debounce timeout with no results |
| COMPLETER POPUP SHOWN | SELECTED → FIELDS POPULATED | User clicks popup item |
| COMPLETER POPUP SHOWN | EDITING NAME | User clicks outside popup or continues typing |
| EDITING PHONE | AUTO-FILL TRIGGERED | User tabs away with valid 11-digit phone |
| EDITING PHONE → AUTO-FILL TRIGGERED | FIELDS POPULATED | Phone found in DB |
| EDITING PHONE | (stay in EDITING PHONE) | User tabs away with empty/invalid phone or phone not found |
| Any EDITING state | SAVE CLICKED | User clicks Save button |
| SAVE CLICKED | VALID → RESOLVE CUSTOMER | Phone valid (or empty), not edit mode |
| SAVE CLICKED | INVALID PHONE → WARNING | Phone present but invalid format |
| SAVE CLICKED | EDIT MODE → ACCEPT | `self.repair_data` is set |
| VALID → RESOLVE CUSTOMER | CUSTOMER RESOLVED | `resolve_customer` completes |
| CUSTOMER RESOLVED (has customer) | POPULATE FIELDS | Customer dict returned |
| CUSTOMER RESOLVED (no customer) | SKIP POPULATE | `None` returned (user cancelled) |
| POPULATE FIELDS or SKIP POPULATE | ACCEPTED | `accept()` called |
| INVALID PHONE → WARNING | Back to current EDITING state | User dismisses warning dialog |
| ACCEPTED | SAVED IN app.py | `dialog.exec_()` returns `QDialog.Accepted` |
| User clicks Cancel | REJECTED | `dialog.reject()` called via cancel button or window close |

---

## 11. Error Handling

### 11.1 Empty Phone

| Context | Behavior |
|---------|----------|
| Auto-fill trigger | Silent return — no lookup attempted |
| Save (create mode) | Phone normalized to `None` → stored as SQL NULL |
| Save (phone in form) | Not treated as error; customer can exist without phone |
| UNIQUE constraint | Not triggered (SQLite allows multiple NULLs in UNIQUE columns) |

### 11.2 Duplicate Phone

| Context | Behavior |
|---------|----------|
| Auto-fill trigger | Returns existing customer (desired behavior — user is trying to find them) |
| Save (resolve_customer) | Phone checked first: existing found → returned immediately (no dialog) |
| Save (manual insert) | Not possible — `resolve_customer` is the only creation path |
| DB level | `phone` column has UNIQUE constraint → SQLite rejects duplicate non-NULL phones |

### 11.3 Duplicate Name

| Context | Behavior |
|---------|----------|
| Completer display | Both customers shown in popup (different rows, different phone numbers) |
| Save (resolve_customer) | Exact name match → confirmation dialog → user decides |
| Save (after decline) | Similar names check → warning dialog → user decides |
| After all declines | `resolve_customer` returns `None` → dialog still accepts |

### 11.4 Cancelled Dialog

| Context | Behavior |
|---------|----------|
| User clicks Cancel button | `reject()` called — dialog closes with `QDialog.Rejected` |
| `app.py` handles | `if dialog.exec_() == QDialog.Accepted:` → branch not taken → no save |
| Customer changes | Discarded — no DB writes of any kind |
| Window close (X button) | Same as Cancel — dialog closes with `QDialog.Rejected` |

### 11.5 Deleted Customer

| Context | Behavior |
|---------|----------|
| Customer deleted from DB but still in completer search results | Not possible — completer queries live DB |
| Customer deleted between search and selection | `get_customer(customer_id)` returns `None` → silent return |
| Customer deleted between population and save | `resolve_customer` with phone creates NEW customer (phone not UNIQUE conflicted since old was deleted) |
| Repair references deleted customer | Repair stores denormalized `customer_name` and `phone` only — no FK constraint to break |

### 11.6 Invalid customer_id

| Context | Behavior |
|---------|----------|
| `Qt.UserRole` returns None/0 | Guard in `_on_completer_activated`: silent return |
| `get_customer(invalid_id)` | Repository returns `None` → guard in caller: silent return |
| `get_by_id(999999)` returns None | Silent — no error thrown |
| Non-integer in Qt.UserRole | Not possible — code stores `c['id']` which is always int |

### 11.7 No Phone + No Name Save

```
validate_and_accept guard:
  if not phone and not full_name → accept()
  
This creates a repair with empty customer_name and empty phone.
This is intentional — the repair may be started without customer info.
```

### 11.8 Database Error

| Error | Repository Behavior | UI Behavior |
|-------|--------------------|-------------|
| UNIQUE constraint violation | `session.rollback()` → exception re-raised | Unhandled — propagates up through service → workflow → dialog |
| Connection error | Exception from SQLAlchemy | Unhandled — crash at dialog level |
| Threading issue | Not applicable — all DB operations are synchronous | N/A |

---

## 12. SQLite Interaction Map

### Read Operations

```
Search for completer:
  SQL: SELECT * FROM customer
       WHERE full_name ILIKE '%query%'
          OR phone ILIKE '%query%'
  Called: Every 250ms debounce while typing in name field
  Layer: CustomerRepository.search()

Lookup by phone:
  SQL: SELECT * FROM customer WHERE phone = '09123456789'
  Called: On phone_input.editingFinished
  Layer: CustomerRepository.get_by_phone()

Lookup by ID:
  SQL: SELECT * FROM customer WHERE id = 42
  Called: On completer selection, phone auto-fill data load
  Layer: CustomerRepository.get_by_id()

Lookup by name (exact match):
  SQL: SELECT * FROM customer
       WHERE full_name ILIKE '%name%'
          OR phone ILIKE '%name%'
  + Python: filter c['full_name'].strip() == name
  Called: On save, during resolve_customer
  Layer: CustomerService.find_by_full_name() → CustomerRepository.search()

Similar name search:
  SQL: Same as search (above)
  + Python: filter excludes exact match
  Called: On save, after exact match declined
  Layer: CustomerService.resolve_customer() → CustomerRepository.search()

Generate customer code:
  SQL: SELECT * FROM customer  (entire table)
  Called: On save, when creating new customer
  Layer: CustomerRepository.get_all()
```

### Write Operations

```
Create customer:
  SQL: INSERT INTO customer (customer_code, full_name, phone, email, ...)
       VALUES ('C000001', 'علی احمدی', '09123456789', ...)
  Called: On save, only after all duplicate checks pass
  Layer: CustomerRepository.create()
```

### Write Frequency

| Operation | Frequency | Notes |
|-----------|-----------|-------|
| Search | High (every 250ms while typing) | Read-only |
| Phone lookup | Low (on tab-away from phone) | Read-only |
| ID lookup | Medium (completer selection + auto-fill) | Read-only |
| Create customer | Low (only on save of new customers) | Write |
| Generate code | Low (same as create) | Read: full table scan |

---

## 13. Non-Goals

The following are explicitly NOT covered by this specification:

1. **Customer editing in repair dialog** — Currently, edit mode bypasses customer resolution entirely. No customer update mechanism exists.
2. **Customer delete from UI** — No customer deletion UI exists. Only repository method available.
3. **Linking repairs to customer by FK** — Repairs store denormalized `customer_name` and `phone`. No `customer_id` in repairs table.
4. **Customer data update** — No mechanism in UI to update existing customer data.
5. **Invoice integration with customer data** — Invoice generation is separate from customer workflow.
6. **Multiple phone numbers per customer** — Phone column is UNIQUE, single value only.
7. **Customer search by email/code/address** — Search is limited to `full_name` and `phone`.
8. **Pagination/sorting in completer** — All results returned, no explicit ordering.
9. **International phone formats** — Validator enforces Iranian format (`^0\d{10}$`).
10. **Customer history/repair history** — No display of customer's past repairs in dialog.

---

## Appendix: Code Reference

| File | Line Range | Relevant Methods |
|------|-----------|-----------------|
| `ui/dialogs/repair_dialog.py` | 227-244 | `_init_customer_completer`, signal setup |
| `ui/dialogs/repair_dialog.py` | 246-248 | `_on_name_text_changed` |
| `ui/dialogs/repair_dialog.py` | 250-262 | `_on_completer_search` |
| `ui/dialogs/repair_dialog.py` | 264-271 | `_on_completer_activated` |
| `ui/dialogs/repair_dialog.py` | 273-274 | `_connect_auto_fill` |
| `ui/dialogs/repair_dialog.py` | 276-291 | `_on_phone_editing_finished` |
| `ui/dialogs/repair_dialog.py` | 293-313 | `validate_and_accept` |
| `ui/dialogs/repair_dialog.py` | 315-327 | `_get_customer_data` |
| `services/customer_workflow.py` | 1-87 | `CustomerWorkflow` (all methods) |
| `services/customer_service.py` | 31-104 | `resolve_customer` |
| `services/customer_service.py` | 106-110 | `find_customer` |
| `services/customer_service.py` | 127-136 | `search_customers` |
| `services/customer_service.py` | 138-140 | `get_customer` |
| `services/customer_service.py` | 117-125 | `find_by_full_name` |
| `services/customer_service.py` | 154-165 | `generate_customer_code` |
| `core/storage/customer_repository.py` | 23-29 | `get_by_id` |
| `core/storage/customer_repository.py` | 39-45 | `get_by_phone` |
| `core/storage/customer_repository.py` | 47-73 | `create` |
| `core/storage/customer_repository.py` | 127-137 | `search` |
| `core/storage/customer_repository.py` | 139-156 | `_to_dict` |
| `core/storage/customer_model_db.py` | 1-22 | CustomerDB ORM model |
| `app.py` | 147-160 | `add_repair` (dialog invocation) |
| `app.py` | 162-189 | `edit_repair` (dialog invocation) |

---

*End of Behavior Specification v1.0 — No code was modified during the creation of this document.*
