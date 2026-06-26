# Customer Workflow Architecture Audit

> Date: 2026-06-26
> Scope: UI → Service → Repository → SQLite → UI
> Principle: DO NOT MODIFY CODE. Only observe and document.

---

## 1. Layered Architecture Overview

```
┌─────────────────────────────────────────────────┐
│                  RepairDialog                    │  UI Layer (PyQt5)
│  ui/dialogs/repair_dialog.py                     │
├─────────────────────────────────────────────────┤
│                 CustomerService                  │  Service Layer
│  services/customer_service.py                    │
├─────────────────────────────────────────────────┤
│               CustomerRepository                 │  Repository Layer
│  core/storage/customer_repository.py             │
├─────────────────────────────────────────────────┤
│              CustomerDB (SQLAlchemy)             │  ORM / SQLite
│  core/storage/customer_model_db.py               │
└─────────────────────────────────────────────────┘
```

---

## 2. Complete Call Graph

### 2.1 All methods and their callers

```
┌────────────────────────────────────────────────────────────────────┐
│  repair_dialog.py                                                  │
│                                                                    │
│  __init__()                                                        │
│    ├── init_ui()                          [builds widgets+signals] │
│    ├── _init_customer_completer()         [builds QCompleter]      │
│    └── _connect_auto_fill()               [phone signal]           │
│                                                                    │
│  _on_name_text_changed(text)                                       │
│    └── _completer_timer.start(250)                                 │
│                                                                    │
│  _on_completer_search() ← QTimer.timeout                           │
│    └── CustomerService.search_customers(text)                      │
│         └── CustomerRepository.search(query)                       │
│              └── SQL: ilike(full_name) OR ilike(phone)             │
│                                                                    │
│  _on_completer_activated(index) ← QCompleter.activated[QModelIndex]│
│    ├── proxy.mapToSource(index)                                    │
│    ├── item.data(Qt.UserRole) → customer_id                        │
│    ├── CustomerService.get_customer(customer_id)                   │
│    │    └── CustomerRepository.get_by_id(id)                       │
│    └── populate_customer_fields(customer)                          │
│                                                                    │
│  _on_phone_editing_finished() ← phone_input.editingFinished        │
│    ├── CustomerService.find_customer(phone)                        │
│    │    ├── CustomerRepository.get_by_phone(phone)                 │
│    │    └── CustomerRepository.get_by_code(phone)  [fallback]      │
│    └── populate_customer_fields(customer)                          │
│                                                                    │
│  validate_and_accept() ← save_btn.clicked                          │
│    ├── CustomerService.find_by_phone(phone)                        │
│    │    └── CustomerRepository.get_by_phone(phone)                 │
│    ├── CustomerService.find_by_full_name(full_name)                │
│    │    └── CustomerRepository.search(full_name)  [exact filter]   │
│    ├── CustomerService.create_customer(data)    [2 call sites]     │
│    │    ├── generate_customer_code()                               │
│    │    └── CustomerRepository.create(data)                        │
│    └── populate_customer_fields(existing)     [2 call sites]       │
│                                                                    │
│  populate_customer_fields(customer)                                │
│    └── Sets all 10 widgets: name, phone, email, website,           │
│        national_id, address, city, province, postal_code, notes    │
│                                                                    │
│  _get_customer_data()                                              │
│    └── Reads all 10 widgets → Dict                                 │
│                                                                    │
│  _sanitize_display_name(name)                                      │
│    └── Strips emoji prefix from display string                     │
└────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────┐
│  customer_service.py                                               │
│                                                                    │
│  search_customers(query: str) → List[Dict]        [USED]          │
│    └── CustomerRepository.search(query)                           │
│                                                                    │
│  find_customer(query: str) → Optional[Dict]       [USED]          │
│    ├── CustomerRepository.get_by_phone(query)                     │
│    └── CustomerRepository.get_by_code(query)  [fallback]          │
│                                                                    │
│  find_by_phone(phone: str) → Optional[Dict]      [USED]          │
│    └── CustomerRepository.get_by_phone(phone)                     │
│                                                                    │
│  find_by_full_name(full_name: str) → List[Dict]   [USED]          │
│    └── CustomerRepository.search(full_name) + exact filter        │
│                                                                    │
│  get_customer(customer_id: int) → Optional[Dict]  [USED]          │
│    └── CustomerRepository.get_by_id(customer_id)                  │
│                                                                    │
│  create_customer(data: Dict) → Dict               [USED]          │
│    ├── generate_customer_code()                                   │
│    └── CustomerRepository.create(data)                            │
│                                                                    │
│  ──────────────────── UNUSED BY UI ────────────────────           │
│  get_or_create_customer(data) → Dict              [UNUSED]        │
│    (has duplicate-phone detection built in)                        │
│  update_customer(id, data) → Optional[Dict]       [UNUSED]        │
│  get_all_customers() → List[Dict]                 [UNUSED]        │
│  generate_customer_code() → str                   [only via        │
│                                                     create_cust]  │
└────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────┐
│  customer_repository.py                                            │
│                                                                    │
│  get_by_phone(phone) → Optional[Dict]             [USED]          │
│  get_by_id(id) → Optional[Dict]                   [USED]          │
│  get_by_code(code) → Optional[Dict]               [USED]          │
│  search(query) → List[Dict]                       [USED]          │
│  create(data) → Dict                              [USED]          │
│                                                                    │
│  ──────────────────── UNUSED BY UI ────────────────────           │
│  get_all() → List[Dict]                           [UNUSED]        │
│  update(id, data) → Optional[Dict]                [UNUSED]        │
│  delete(id) → bool                                [UNUSED]        │
│  exists_by_phone(phone) → bool                    [UNUSED]        │
│  exists_by_code(code) → bool                      [UNUSED]        │
└────────────────────────────────────────────────────────────────────┘
```

---

## 3. Workflow Trace: A — Phone Auto-fill

```
User types phone "09123456789" and tabs away
│
▼
phone_input.editingFinished SIGNAL
│
▼
RepairDialog._on_phone_editing_finished()          [line 294]
│
├── Guard: phone empty OR invalid → return
│
├── CustomerService.find_customer("09123456789")   [line 298]
│   │
│   ├── CustomerRepository.get_by_phone("09123456789")
│   │   └── SQL: SELECT * FROM customer WHERE phone = ?
│   │   └── Returns Dict OR None
│   │
│   └── FALLBACK: CustomerRepository.get_by_code("09123456789")
│       └── Only if get_by_phone returned None
│       └── Unnecessary: phone number is never a customer code
│
├── Guard: customer is None → return (no auto-fill)
│
├── phone_input.blockSignals(True)
│
└── populate_customer_fields(customer)             [line 302]
    │
    ├── customer_name_input.setText(full_name)
    ├── phone_input.setText(phone)
    ├── email_input.setText(email)
    ├── website_input.setText(website)
    ├── national_id_input.setText(national_id)
    ├── address_input.setText(address)
    ├── city_input.setText(city)
    ├── province_input.setText(province)
    ├── postal_code_input.setText(postal_code)
    └── notes_input.setPlainText(notes)

└── phone_input.blockSignals(False)

=== OBSERVATIONS ===

1. find_customer() has an UNNECESSARY fallback to get_by_code().
   Phone numbers will never match customer_code format "C000001".
   This fallback serves no purpose for phone auto-fill.

2. phone_input.blockSignals() prevents recursive editingFinished.
   This is correct — it was also in the original code.

3. populate_customer_fields() is called correctly with full data.

4. PROBLEM: _on_phone_editing_finished and validate_and_accept
   are INDEPENDENT signal handlers. If phone editing finishes and
   auto-fill fires, BUT the user clicks Save before the event
   loop processes editingFinished, validate_and_accept runs
   WITHOUT the auto-fill having populated the fields.
```

---

## 4. Workflow Trace: B — Customer Completer

```
User types "عل" in customer_name_input
│
▼
QLineEdit.textChanged SIGNAL
│
▼
RepairDialog._on_name_text_changed("عل")           [line 246]
│
├── QCompleter.setCompletionPrefix("عل")
│
└── _completer_timer.start(250)

250ms passes (debounce)
│
▼
QTimer.timeout SIGNAL
│
▼
RepairDialog._on_completer_search()                [line 250]
│
├── Guard: text < 2 chars → clear model → return
│
├── CustomerService.search_customers("عل")         [line 255]
│   │
│   └── CustomerRepository.search("عل")
│       └── SQL: WHERE full_name ILIKE '%عل%'
│       │          OR phone ILIKE '%عل%'
│       └── Returns List[Dict] (all matching)
│
├── _completer_model.clear()
│
├── For each customer c:
│   │
│   ├── label = f"👤 {c[full_name]}\n📞 {c[phone]}"
│   ├── item = QStandardItem(label)
│   ├── item.setData(c[id], Qt.UserRole)     ← customer_id stored here
│   └── _completer_model.appendRow(item)
│
└── QCompleter popup shows items (filtered by prefix)

User clicks on a suggestion
│
▼
QCompleter.activated[QModelIndex] SIGNAL           [line 241]
│
▼
RepairDialog._on_completer_activated(index)        [line 263]
│
├── proxy = _completer.completionModel()
│   └── Returns QSortFilterProxyModel (internal to QCompleter)
│
├── source_index = proxy.mapToSource(index)
│   └── Maps proxy index → source model (_completer_model)
│
├── item = _completer_model.itemFromIndex(source_index)
│
├── Guard: item is None → return
│
├── customer_id = item.data(Qt.UserRole)           [line 269]
│   └── Retrieves customer_id from stored data
│
├── Guard: customer_id is None → return
│
├── CustomerService.get_customer(customer_id)      [line 272]
│   │
│   └── CustomerRepository.get_by_id(customer_id)
│       └── SQL: SELECT * FROM customer WHERE id = ?
│       └── Returns FULL customer Dict
│
├── Guard: customer is None → return
│
└── populate_customer_fields(customer)             [line 275]
    └── Fills ALL 10 widgets

=== OBSERVATIONS ===

1. QStandardItemModel is the SOURCE model (contains items + Qt.UserRole).

2. QCompleter wraps it in an internal QSortFilterProxyModel (PROXY).

3. The activated signal passes a PROXY index, which is mapped back to
   the SOURCE model via proxy.mapToSource().

4. Customer ID travels through Qt.UserRole — DISPLAY TEXT is NEVER
   used for identity. This is correct.

5. get_customer(id) makes a SECOND database round-trip to fetch the
   full customer dict. The data was already available in
   _on_completer_search() but not cached. This is an N+1 query.

6. After selection, the name input shows the customer's clean name
   (no emoji prefix), because populate_customer_fields sets it.

7. _on_name_text_changed fires during typing. After population,
   blockSignals prevents re-triggering the search.
```

---

## 5. Workflow Trace: C — Save (validate_and_accept)

```
User clicks Save button
│
▼
save_btn.clicked SIGNAL
│
▼
RepairDialog.validate_and_accept()                 [line 305]
│
├── ELIF: phone invalid → show_warning → return
├── ELIF: repair_data → accept() → return (edit mode)
│
├── phone = phone_input.text().strip()
├── full_name = customer_name_input.text().strip()
├── full_name = _sanitize_display_name(full_name)  ← strips emoji
│
├── IF phone != sanitized name:
│   └── customer_name_input.setText(full_name)
│
├── BRANCH A: phone is truthy ────────────────── [line 317]
│   │
│   ├── CustomerService.find_by_phone(phone)     [line 318]
│   │   └── CustomerRepository.get_by_phone(phone)
│   │
│   ├── IF customer exists:
│   │   ├── populate_customer_fields(existing)
│   │   └── accept() → RETURN
│   │
│   ├── CustomerService.find_by_full_name(full_name) [line 323]
│   │   └── CustomerRepository.search(full_name) + exact filter
│   │
│   ├── IF list non-empty:
│   │   ├── existing = list[0]
│   │   ├── customer_name_input.setText(name)    [PARTIAL populate]
│   │   ├── phone_input.setText(phone)            [PARTIAL populate]
│   │   └── accept() → RETURN
│   │
│   ├── **_get_customer_data()**                  [reads form fields]
│   ├── **CustomerService.create_customer(data)** [line 331]
│   │   ├── generate_customer_code()
│   │   └── CustomerRepository.create(data)
│   └── accept() → RETURN
│
├── BRANCH B: full_name is truthy ───────────── [line 334]
│   │
│   ├── current_phone = phone_input.text().strip()
│   │
│   ├── IF current_phone:                        [defensive check]
│   │   ├── CustomerService.find_by_phone(current_phone)
│   │   │   └── CustomerRepository.get_by_phone(current_phone)
│   │   ├── IF exists:
│   │   │   ├── populate_customer_fields(existing)
│   │   │   └── accept() → RETURN
│   │
│   ├── CustomerService.find_by_full_name(full_name) [line 342]
│   │   └── CustomerRepository.search(full_name) + exact filter
│   │
│   ├── IF list non-empty:
│   │   ├── existing = list[0]
│   │   ├── show_question("مشتری مشابه...")
│   │   ├── IF confirmed:
│   │   │   ├── populate_customer_fields(existing)
│   │   │   └── accept() → RETURN
│   │
│   ├── **_get_customer_data()**                  [reads form fields]
│   ├── **CustomerService.create_customer(data)** [line 355]
│   │   ├── generate_customer_code()
│   │   └── CustomerRepository.create(data)
│   └── accept() → RETURN
│
└── ELSE (no phone, no name): accept() → return

=== OBSERVATIONS ===

1. TWO separate create_customer() call sites [lines 331, 355].
   Both bypass CustomerService.get_or_create_customer() which has
   built-in duplicate detection. The UI reimplements its OWN
   duplicate detection with subtle differences in each branch.

2. BRANCH A has a PARTIALLY populated path (lines 326-327):
   After find_by_full_name succeeds, only name and phone are set.
   Email, website, address, etc. are NOT populated from the DB.
   This is INCONSISTENT with populate_customer_fields().

3. BRANCH B has a DEFENSIVE phone check (lines 335-341) that
   duplicates the logic from BRANCH A (lines 318-322). This was
   added to fix a regression but demonstrates duplicated logic.

4. _sanitize_display_name() [line 314] strips emoji prefix.
   This method EXISTS because at one point the raw display text
   (with emoji) was used for customer identity lookup. With
   QStandardItemModel + Qt.UserRole, this is now a dead fallback.

5. After BRANCH B's confirm-dialog, populate_customer_fields IS
   called (line 351). But after BRANCH A's find_by_full_name match,
   it is NOT (line 326-327 does manual partial setText).
```

---

## 6. All Connected Qt Signals

| # | Signal | Connected Slot | File:Line | Purpose |
|---|--------|---------------|-----------|---------|
| 1 | `parts_cost_input.valueChanged` | `self.calculate_total` | `repair_dialog.py:129` | Recalculate financial totals |
| 2 | `labor_cost_input.valueChanged` | `self.calculate_total` | `repair_dialog.py:135` | Recalculate financial totals |
| 3 | `tax_input.valueChanged` | `self.calculate_total` | `repair_dialog.py:141` | Recalculate financial totals |
| 4 | `discount_input.valueChanged` | `self.calculate_total` | `repair_dialog.py:147` | Recalculate financial totals |
| 5 | `save_btn.clicked` | `self.validate_and_accept` | `repair_dialog.py:218` | Save repair |
| 6 | `cancel_btn.clicked` | `self.reject` | `repair_dialog.py:219` | Close dialog |
| 7 | `_completer_timer.timeout` | `self._on_completer_search` | `repair_dialog.py:230` | Debounced completer search |
| 8 | `_completer.activated[QModelIndex]` | `self._on_completer_activated` | `repair_dialog.py:241` | User selects completer item |
| 9 | `customer_name_input.textChanged` | `self._on_name_text_changed` | `repair_dialog.py:244` | Start debounce timer |
| 10 | `phone_input.editingFinished` | `self._on_phone_editing_finished` | `repair_dialog.py:292` | Phone auto-fill trigger |

All 10 connections are present and accounted for.

---

## 7. QCompleter Architecture

```
Source Model
  QStandardItemModel (self._completer_model)
  ├── Row 0: QStandardItem("👤 علی احمدی\n📞 09121234567")
  │           └── Qt.UserRole → customer_id = 1
  ├── Row 1: QStandardItem("👤 علی رضایی\n📞 09127654321")
  │           └── Qt.UserRole → customer_id = 2
  └── Row 2: QStandardItem("👤 علی حسینی\n📞 09135555555")
              └── Qt.UserRole → customer_id = 3

Proxy Model (internal to QCompleter)
  QCompleterFilterProxyModel (subclass of QSortFilterProxyModel)
  ├── Wraps _completer_model
  ├── Filters by: setCompletionPrefix + setFilterMode(MatchContains)
  └── Forwards Qt.UserRole from source items

Display
  CompleterItemDelegate (custom QStyledItemDelegate)
  ├── paint(): draws two lines, right-aligned, Persian
  └── sizeHint(): height = 2 * font_height + 12

Activation
  QCompleter.activated[QModelIndex] signal
  ├── Emitted with proxy model index
  ├── Slot: _on_completer_activated(proxy_index)
  └── Maps: proxy.mapToSource(proxy_index) → source QModelIndex
      Then: _completer_model.itemFromIndex(source_index)
      Then: item.data(Qt.UserRole) → customer_id

Customer ID travel path:
  User types → search → repo returns customers
  → each customer.id stored in QStandardItem(Qt.UserRole)
  → user clicks → proxy.mapToSource → itemFromIndex
  → data(Qt.UserRole) → get_customer(id) → populate_customer_fields()
```

---

## 8. CustomerService Method Usage

### USED (called from UI)

| Method | Caller | Purpose |
|--------|--------|---------|
| `search_customers(query)` | `_on_completer_search` | Find matching customers for completer |
| `find_customer(query)` | `_on_phone_editing_finished` | Phone auto-fill lookup |
| `find_by_phone(phone)` | `validate_and_accept` (×2) | Save-time duplicate detection |
| `find_by_full_name(name)` | `validate_and_accept` (×2) | Save-time name-based match |
| `get_customer(id)` | `_on_completer_activated` | Get full customer by ID |
| `create_customer(data)` | `validate_and_accept` (×2) | Create new customer on save |
| `generate_customer_code()` | via `create_customer` | Auto-generate code |

### UNUSED (never called from UI, only from tests)

| Method | Notes |
|--------|-------|
| `get_or_create_customer(data)` | **CRITICAL**: Has built-in duplicate detection. UI bypasses it entirely. |
| `update_customer(id, data)` | Would allow editing customer from form |
| `get_all_customers()` | Returns all customers |

---

## 9. CustomerRepository Method Usage

### USED (called from UI via service)

| Method | Purpose |
|--------|---------|
| `get_by_phone(phone)` | Lookup by phone (exact match, unique) |
| `get_by_id(id)` | Lookup by primary key |
| `get_by_code(code)` | Fallback in `find_customer` |
| `search(query)` | Partial match on name or phone |
| `create(data)` | Insert new customer |

### UNUSED (never called from UI)

| Method | Notes |
|--------|-------|
| `get_all()` | Only called from `generate_customer_code()` (indirect usage) |
| `update(id, data)` | Not wired to any UI path |
| `delete(id)` | No customer deletion UI |
| `exists_by_phone(phone)` | Should exist — used only in tests |
| `exists_by_code(code)` | Completely orphaned |

---

## 10. RepairDialog — Customer-Related Methods Grouped by Responsibility

### Search & Lookup Group
| Method | Lines | Responsibility |
|--------|-------|---------------|
| `_on_name_text_changed` | 246-248 | React to typing, start debounce timer |
| `_on_completer_search` | 250-261 | Execute search, populate QStandardItemModel |
| `_on_completer_activated` | 263-275 | Handle selection, retrieve customer, populate fields |
| `_on_phone_editing_finished` | 294-303 | Handle phone entry, find customer, populate fields |

### Field Population Group
| Method | Lines | Responsibility |
|--------|-------|---------------|
| `populate_customer_fields` | 277-289 | Set all 10 customer widgets from dict |
| `_get_customer_data` | 368-380 | Read all 10 widgets into dict |

### Save & Validation Group
| Method | Lines | Responsibility |
|--------|-------|---------------|
| `validate_and_accept` | 305-358 | Full validation, duplicate detection, create-or-reuse |
| `_sanitize_display_name` | 360-366 | Strip emoji prefix from display text |

### UI Setup Group
| Method | Lines | Responsibility |
|--------|-------|---------------|
| `_init_customer_completer` | 227-244 | Build QCompleter, connect signals |
| `_connect_auto_fill` | 291-292 | Connect phone editingFinished signal |

---

## 11. Duplicated Logic Inventory

### Duplicate A: Phone Lookup — Two methods, same repository call

```
CustomerService.find_customer(phone)        [line 31]
  → get_by_phone(phone) + get_by_code(phone) fallback

CustomerService.find_by_phone(phone)        [line 46]
  → get_by_phone(phone) ONLY

Same core operation: get_by_phone(phone).
find_customer adds an unnecessary get_by_code fallback.
```

### Duplicate B: Customer Creation — Two paths, bypassing get_or_create

```
validate_and_accept [line 330-331]  create_customer(data) via BRANCH A
validate_and_accept [line 354-355]  create_customer(data) via BRANCH B

CustomerService.get_or_create_customer(data) [line 16] — THE method that
  has proper duplicate detection — COMPLETELY UNUSED by UI.
```

### Duplicate C: Phone duplicate detection — Three implementations

```
1. _on_phone_editing_finished: find_customer(phone) → populate
2. validate_and_accept BRANCH A: find_by_phone(phone) → populate → accept
3. validate_and_accept BRANCH B: find_by_phone(current_phone) → populate → accept

Each uses a slightly different lookup method (find_customer vs find_by_phone).
```

### Duplicate D: Field population — Two patterns

```
1. populate_customer_fields(customer) — sets ALL 10 fields [correct path]
2. validate_and_accept BRANCH A name-match:
     customer_name_input.setText(full_name)  [line 326]
     phone_input.setText(phone)               [line 327]
     — Only 2 fields, bypasses populate_customer_fields entirely
```

---

## 12. Answers to the Six Questions

### Q1: What is the SINGLE source of truth for customer lookup?

**There is none.** Three different lookup methods are used depending on the code path:

| Context | Method Used | Repository Call |
|---------|------------|-----------------|
| Phone auto-fill | `CustomerService.find_customer(phone)` | `get_by_phone` + `get_by_code` fallback |
| Save validation | `CustomerService.find_by_phone(phone)` | `get_by_phone` only |
| Completer selection | `CustomerService.get_customer(id)` | `get_by_id` — PK lookup |

Each path calls a different service method, though they all resolve to the same `CustomerRepository.get_by_phone()` (except the completer which uses PK).

### Q2: What is the SINGLE source of truth for customer creation?

**There is none.** `CustomerService` has two methods:

| Method | Duplicate Detection | Used By UI? |
|--------|-------------------|-------------|
| `get_or_create_customer(data)` | YES — checks phone before create | **NO** (only tests) |
| `create_customer(data)` | **NO** — blindly inserts | **YES** (×2 in validate_and_accept) |

The method designed as the single source of truth (`get_or_create_customer`) is completely unused by the UI. The UI calls the unsafe `create_customer()` directly, reimplementing duplicate detection inline with slightly different logic in each branch.

### Q3: What is the SINGLE source of truth for field population?

**Nearly there, but not quite.** `populate_customer_fields(customer)` is the designated method and is called from 3 of the 4 population sites:

| Context | Calls populate_customer_fields? | 
|---------|-------------------------------|
| Phone auto-fill | YES |
| Completer selection | YES |
| Save — find_by_phone match | YES |
| Save — find_by_full_name match (BRANCH A) | **NO** — partial setText only |

One path bypasses the method and does manual partial population.

### Q4: Which responsibilities are duplicated?

1. **Phone lookup** — `find_customer` vs `find_by_phone` (same repo call, different fallback)
2. **Customer creation** — `get_or_create_customer` (unused) vs inline `find_by_phone` + `create_customer` in two branches
3. **Phone duplicate detection** — implemented in 3 places with slight differences
4. **Field population** — `populate_customer_fields` vs manual 2-field setText
5. **Save validation logic** — BRANCH A and BRANCH B are structurally similar but handle the phone differently

### Q5: Why do regressions keep happening?

**Root cause: Every fix changes behavior in one code path without the fixer knowing about the other paths.**

Each fix is targeted at a specific symptom (completer not working, phone auto-fill broken, duplicates created). The fixer changes the relevant code path (completer `activated` signal, `validate_and_accept` branch, etc.) but the same logic exists in MULTIPLE places with DIFFERENT implementations. A fix that works for one path may:

1. Break another path that had a different implementation
2. Not address the same issue in the other path
3. Introduce a different bug because the fix only accounts for one variant

The signal overload issue (QCompleter.activated resolving to QString instead of QModelIndex) is a classic example — a PyQt binding detail that's invisible in a diff review but breaks the entire completer workflow.

### Q6: What architectural change would permanently solve the problem?

**Centralize all customer operations through ONE service method per operation type.**

```
Current:                        Proposed:
─────────                       ─────────
search_customers()              search_customers()  ← stays (read-only)
find_customer()                 ← REMOVE
find_by_phone()                 ← REMOVE
find_by_full_name()             ← REMOVE  
get_customer()                  get_customer()      ← stays (by PK)
create_customer()               ← REMOVE
                                get_or_create_customer() ← ONLY creation method
get_or_create_customer()        ← MAKE THIS THE ONLY PATH

validate_and_accept():
  BRANCH A (phone)              validate_and_accept():
  BRANCH B (no phone)             SINGLE PATH:
                                    1. get_or_create_customer(data)
                                       → checks phone internally
                                       → returns existing OR creates
                                    2. populate_customer_fields(result)
                                    3. accept()
```

**Specific changes:**

1. **Remove `find_customer()` and `find_by_phone()` from service.** Replace all callers with a single `find_customer_by_phone()` that does exactly one thing: `get_by_phone(phone)`.

2. **Make `get_or_create_customer()` the ONLY creation method.** Remove `create_customer()` from the service's public API. All creation goes through `get_or_create_customer()`, which has built-in phone-based duplicate detection.

3. **Always call `populate_customer_fields()` for ANY customer match.** Remove the manual 2-field setText at line 326-327.

4. **Simplify `validate_and_accept` to a single path.** Instead of two branches (phone vs no-phone), use one path:
   - Collect form data via `_get_customer_data()`
   - Call `get_or_create_customer(data)` — this handles phone check internally
   - Call `populate_customer_fields(result)` with whatever it returns
   - Accept

This eliminates every duplication listed in Q4 and removes the root cause of regressions. No more "fix this branch, break that branch."
