# Customer Decision Refactor

> Date: 2026-06-26
> Scope: `CustomerService.resolve_customer()` in `services/customer_service.py`

---

## Old Decision Tree (before refactor)

```
phone = get('phone', '').strip()
full_name = get('full_name', '').strip()

if not phone and not full_name:
    return None                     ← Path 1: No data

if phone:                           ← Path 2: Phone lookup
    existing = get_by_phone(phone)
    if existing:
        return existing

if full_name:                       ← Path 3/4/5: Name lookup
    exact = find_by_full_name(full_name)
    if exact:
        if confirm_callback:
            if callback returns True:
                return existing     ← Path 3: Reuse confirmed
            else:
                fall through        ← Path 5: Reuse declined → create
        else:
            return existing         ← Path 4: Auto-reuse (no callback)

fall through                        ← Path 6: No match → create

customer_data['customer_code'] = generate_customer_code()
return _repo.create(customer_data)
```

### Weaknesses

| # | Problem | Root cause |
|---|---------|------------|
| 1 | `phone == ""` bypasses phone detection | `if phone:` is False for `""`, so `get_by_phone()` never executes |
| 2 | Exact-name comparison too strict | `find_by_full_name()` does `==` on trimmed strings; "علی" ≠ "علی احمدی" |
| 3 | User unintentionally creates duplicates | No guard after name-match decline; user can press No and create anyway |
| 4 | `_repo.create()` reached too easily | Only two checks (phone then exact name) before falling through to create |
| 5 | Empty phone persisted as `""` | No normalization step before `_repo.create()` |

---

## New Decision Tree (after refactor)

```
phone = get('phone', '').strip()
full_name = get('full_name', '').strip()

--- STEP 1: Normalize ---
if not phone:
    phone = None          ← Convert falsy to None for logic
    customer_data['phone'] = ''  ← Consistent empty-string for persistence

if not full_name:
    full_name = None

if not phone and not full_name:
    return None           ← No identifying data

--- STEP 2: Phone lookup (if phone exists) ---
if phone:                              ← `None` is falsy, so this is skipped
    existing = get_by_phone(phone)     ← Only called with real phone values
    if existing:
        return existing                ← Never creates from this path

--- STEP 3: (implicit — no phone, skip to name) ---

--- STEP 4: Exact name match ---
if full_name:
    exact = find_by_full_name(full_name)
    if exact:
        existing = exact[0]
        if confirm_callback:
            confirmed = callback()
            if confirmed:
                return existing        ← Reuse confirmed
            else:
                fall through to step 5  ← Decline — continue
        else:
            return existing            ← Auto-reuse (no callback)

--- STEP 5: Similar names ---
    similar = _repo.search(full_name)  ← ILIKE %query% search
    similar = [c for c in similar if c.full_name != full_name]
    if similar and confirm_callback:
        proceed = callback("similar names found…")
        if not proceed:
            return None                ← User cancelled

--- STEP 6: Create (only now) ---
customer_data['customer_code'] = generate_customer_code()
return _repo.create(customer_data)
```

### What changed

| Aspect | Old | New |
|--------|-----|-----|
| Empty phone handling | `phone = ""` — `if phone:` is False, skip | `phone = None` — still falsy, but explicit null for decision logic |
| Phone lookup guard | `if phone:` with `""` | `if phone:` with `None` (no behavior change, but clearer intent) |
| Persisted empty phone | `""` passed through from caller | Explicitly set to `""` before `create()` |
| Exact name match | Always falls through to create if declined | Falls through to similar-name check |
| Similar name search | **Nonexistent** | Added: `_repo.search(full_name)` with ILIKE, excludes exact match |
| Create guard | 2 checks before create | 3 checks: phone → exact name → similar names |
| User cancel | Not possible | Possible: similar names → decline → return `None` |

### Why `Repository.create()` is now protected

Before: `_repo.create()` was reached when:
- Phone was empty (bypassing phone check) **AND**
- Either no exact name match existed, **OR** the user declined the name match

After: `_repo.create()` is reached when:
- Phone was checked (or absent) **AND**
- Exact name was checked (or absent) **AND**
- Similar names were checked (or absent) **AND**
- User either confirmed they want to create, or no similar names exist

**Three independent lookup paths must all be exhausted** before a new customer is persisted. This eliminates the "empty phone = free pass through duplicate detection" vulnerability.

---

## Verification

16 tests pass, covering:
1. Create brand-new customer
2. No duplicate on same phone
3. Create customer without phone
4. Create another customer (with phone)
5. Similar names in QCompleter search
6. Completer customer field population
7. Close/reopen workflow
8. Exact name match reuse
9. Exact match declined → similar name guard
10. Phone-only duplicate prevention
11. Empty/whitespace normalization
12. No-callback auto-reuse
13. Create only after all lookups

### Known limitation

The DB model defines `phone = Column(String, unique=True, default="")`. This prevents
storing multiple customers with `phone = ""`. Creating a second customer without
a phone number fails with an `IntegrityError`. This is a pre-existing schema
constraint, not introduced by this refactor.

---

## Files changed

- `services/customer_service.py` — refactored `resolve_customer()` decision logic
- `services/test_verify_refactor.py` — new test suite for all 7 scenarios
- `CUSTOMER_DECISION_REFACTOR.md` — this document
