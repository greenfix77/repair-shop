# resolve_customer() Decision Tree Audit

> Date: 2026-06-26
> Method: `CustomerService.resolve_customer()` at services/customer_service.py:31-74

---

## Entry

```
resolve_customer(customer_data: Dict, confirm_callback=None) -> Optional[Dict]
```

Initial extraction:

```
phone     = customer_data.get('phone', '').strip()
full_name = customer_data.get('full_name', '').strip()
```

---

## Exit Path 1 — No identifying data

```
Condition:
  not phone AND not full_name
  │
  ▼
Action:
  return None
  │
  ▼
Return:  None
```

Called when both `phone` and `full_name` are empty/falsy.

---

## Exit Path 2 — Phone match (existing customer)

```
Condition:
  phone is truthy
  │
  ▼
  _repo.get_by_phone(phone) returns a customer dict
  │
  ▼
Action:
  return existing
  │
  ▼
Return:  existing customer dict
```

Customer matched by exact phone. Silent reuse — no confirmation required.

---

## Exit Path 3 — Name match, confirmed

```
Condition:
  phone is falsy       OR   phone not in DB
  AND
  full_name is truthy
  AND
  find_by_full_name(full_name) returns non-empty list
  AND
  confirm_callback is provided
  AND
  confirm_callback() returns True
  │
  ▼
Action:
  return existing = exact[0]
  │
  ▼
Return:  first matching customer dict
```

Customer matched by exact `full_name`. User confirmed reuse. Phone was either empty or didn't match anything.

---

## Exit Path 4 — Name match, auto-confirmed (no callback)

```
Condition:
  phone is falsy       OR   phone not in DB
  AND
  full_name is truthy
  AND
  find_by_full_name(full_name) returns non-empty list
  AND
  confirm_callback is None
  │
  ▼
Action:
  return existing = exact[0]
  │
  ▼
Return:  first matching customer dict
```

Same as Path 3 but without a callback. Auto-confirms reuse. (Used internally or in tests.)

---

## Exit Path 5 — Name match, user declined

```
Condition:
  phone is falsy       OR   phone not in DB
  AND
  full_name is truthy
  AND
  find_by_full_name(full_name) returns non-empty list
  AND
  confirm_callback is provided
  AND
  confirm_callback() returns False
  │
  ▼
  (falls through to create)
  │
  ▼
Action:
  customer_data['customer_code'] = generate_customer_code()
  _repo.create(customer_data)
  │
  ▼
Return:  newly created customer dict
```

Name matched but user declined reuse. **A new customer is created** with whatever was in `customer_data`, which may include `phone=""`.

---

## Exit Path 6 — No match at all

```
Condition:
  phone is falsy       OR   phone not in DB
  AND
  full_name is falsy   OR   find_by_full_name(full_name) returns empty list
  │
  ▼
  (falls through to create)
  │
  ▼
Action:
  customer_data['customer_code'] = generate_customer_code()
  _repo.create(customer_data)
  │
  ▼
Return:  newly created customer dict
```

No existing customer matched. A new customer is created from `customer_data`.

---

## Combined Decision Flowchart

```
                  ┌──────────────────────┐
                  │  phone=""             │
                  │  full_name=""         │
                  └──────────┬───────────┘
                             │
                   ┌─────────▼─────────┐
                   │  any identifying  │
                   │  data?            │
                   │  phone OR name?   │
                   └────┬─────────┬────┘
                        NO        │
                        │        YES
                   ┌────▼───┐     │
                   │ return │     │
                   │  None  │     ▼
                   └────────┘  ┌──────────────┐
                               │  phone       │
                               │  truthy?     │
                               └──────┬───────┘
                                    NO │
                                  ┌────▼─────────┐
                                  │  YES         │
                                  │              ▼
                                  │  ┌──────────────────┐
                                  │  │ get_by_phone()    │
                                  │  │ found?            │
                                  │  └──┬───────────┬────┘
                                  │    YES          NO
                                  │     │            │
                                  │  ┌──▼──┐      (fall through)
                                  │  │ret. │         │
                                  │  │exist│         │
                                  │  └─────┘         │
                                  │                  │
                                  │      ┌───────────▼─────────┐
                                  │      │  full_name          │
                                  │      │  truthy?            │
                                  │      └───┬─────────────┬───┘
                                  │          NO             YES
                                  │           │              │
                                  │      (fall through)     ▼
                                  │           │     ┌────────────────┐
                                  │           │     │ find_by_       │
                                  │           │     │ full_name()    │
                                  │           │     │ found?         │
                                  │           │     └──┬─────────┬───┘
                                  │           │        YES        NO
                                  │           │         │          │
                                  │           │    ┌────▼──┐  (fall through)
                                  │           │    │confirm│      │
                                  │           │    │callback│      │
                                  │           │    │ exists?│      │
                                  │           │    └──┬──┬──┘      │
                                  │           │      NO  YES       │
                                  │           │       │    │        │
                                  │           │   ┌───▼┐ ┌▼─────┐  │
                                  │           │   │ret.│ │confirm│  │
                                  │           │   │auto│ │called │  │
                                  │           │   │────│ │  │    │  │
                                  │           │   │ret.│ │YES│ NO │  │
                                  │           │   │exist│ │ │  │  │  │
                                  │           │   └────┘ │ │  │  │  │
                                  │           │       ┌──▼─▼──▼──▼──┘
                                  │           │       │ (fall through)
                                  │           │       │  to CREATE
                                  │           │       └──────┬───────
                                  │           │              │
                                  │           └──────┐       │
                                  │                  │       │
                                  └──────────────────┘       │
                                                             │
                                              ┌──────────────▼────────┐
                                              │  customer_data['      │
                                              │  customer_code'] =    │
                                              │  generate_customer_   │
                                              │  code()               │
                                              │  _repo.create(        │
                                              │   customer_data)      │
                                              └──────────┬────────────┘
                                                         │
                                              ┌──────────▼──────────┐
                                              │  return new         │
                                              │  customer dict      │
                                              └─────────────────────┘
```

---

## Answers

### 1. What happens when phone == ""?

```
phone = ""  (after .strip())
```

- `not phone` → `True`
- `if not phone and not full_name:` → depends on `full_name`
  - If `full_name == ""` → **Exit Path 1** → return `None`
  - If `full_name != ""` → continue
- `if phone:` → **False** → **phone lookup entirely skipped**
- `if full_name:` → proceed to name match
  - Match found + confirmed → **Exit Path 3** → reuse existing
  - Match found + declined → **Exit Path 5** → **create with phone=""**
  - No match → **Exit Path 6** → **create with phone=""**

**Key fact:** `phone=""` means phone-based duplicate detection (lines 54-57) is NEVER executed. The first time an empty phone reaches the database is when `_repo.create()` is called.

---

### 2. Can resolve_customer() call create_customer() with an empty phone?

**YES.** In two distinct scenarios:

| Scenario | Phone provided? | Name provided? | Name match? | Confirm? | Creates with phone |
|----------|----------------|----------------|-------------|----------|-------------------|
| User has name, no phone, no match | No | Yes | No | N/A | `""` |
| User has name, no phone, match | No | Yes | Yes | Declined | `""` |

In both cases, `customer_data` is passed directly to `_repo.create()` without the `phone` field being set to any value. The resulting SQLite row has `phone=""`.

---

### 3. Under what exact conditions is Repository.create() executed?

`_repo.create()` is called at line 74. It is reached when ALL prior exit conditions are False:

1. `not phone and not full_name` — **False** (at least one has a value)
2. `phone` truthy AND `get_by_phone(phone)` returned truthy — **False** (either phone is empty OR phone not in DB)
3. `full_name` truthy AND `find_by_full_name(full_name)` returned non-empty AND (no callback OR callback returned True) — **False** (either name is empty OR name not found OR callback returned False)

In boolean logic:

```
phone != ""  →  get_by_phone(phone) must be None
full_name != ""  →  find_by_full_name must be empty
                     OR callback exists AND callback returned False
```

---

### 4. Why does SQLite receive phone="" instead of reusing an existing customer?

Because there is **no fallback phone lookup** when `phone=""`. The decision tree is:

```
phone=""  →  if phone:  →  False  →  skip get_by_phone()
```

Without a phone, the method jumps directly to name matching. If the name doesn't match exactly, or if the user declines the confirmation dialog for a name match, `_repo.create()` is called with the original `customer_data`, which has `phone=""`.

The method never attempts to:
- Look up any customer with a non-empty phone to suggest
- Search for customers with similar attributes other than exact name
- Prevent the creation of a customer with empty phone when a matching name exists but was declined

Essentially: **empty phone = free pass through duplicate detection.**

---

### 5. Is duplicate detection skipped when phone is empty?

**YES.** The phone-based duplicate detection (lines 54-57) is entirely inside `if phone:`, which is `False` when `phone=""`.

The only remaining guard against duplicates is the name-based check (lines 59-71), which has two gaps:

**Gap 1 — Exact match only.** `find_by_full_name()` does exact string comparison:
```python
if c.get('full_name', '').strip() == full_name.strip():
```
A customer named "علی احمدی" will NOT match input "علی" or "احمدی" or "علی  احمدی" (double space).

**Gap 2 — User can override.** Even when an exact name match IS found, the confirmation dialog allows the user to decline and create a new customer anyway.

In practice, the sequence that produces a duplicate with `phone=""` is:

```
User types name "علی احمدی" (no phone)
  → resolve_customer({phone: "", full_name: "علی احمدی", ...})
  → if phone:  → False  → SKIP phone lookup
  → if full_name: → True
  → find_by_full_name("علی احمدی") → [existing customer]
  → confirm_callback("مشتری مشابه", ...) → returns False (user clicks No)
  → Falls through to _repo.create(customer_data)
  → SQLite receives: phone="", full_name="علی احمدی", ...
  → DUPLICATE customer created
```

---

## Summary

| Weakness | Location | Impact |
|----------|----------|--------|
| Phone lookup guarded by `if phone:` | Line 54 | Empty phone = no phone duplicate check |
| Name match is exact only | `find_by_full_name` line 93 | Similar names bypass detection |
| Confirmation can be declined | Line 64-67 | User can create duplicate despite detection |
| No fallback search when phone is empty | Lines 48-74 | No attempt to find customers without phone |

All three paths that reach `_repo.create()` can produce a customer with `phone=""`:

```
Path A:  phone=""  +  full_name=""       → guard at line 51 → return None
         (won't create — but no customer at all)

Path B:  phone=""  +  name not found     → creates with phone=""
Path C:  phone=""  +  name found + declined → creates with phone=""
```
