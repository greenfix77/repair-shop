# Phone Normalization Audit

## Why empty string caused UNIQUE failure

The `CustomerDB.phone` column is defined with `unique=True`. In SQLite (and most SQL databases), a UNIQUE constraint treats each empty string `""` as a distinct non-NULL value. This means:

- Two rows with `phone=""` violate the UNIQUE constraint
- No two customers can be created without a phone number

The root cause was in `customer_repository.py` `create()`:
```python
phone=customer_data.get('phone', ''),  # always stores ""
```

And the `CustomerDB` model enforced this with:
```python
phone = Column(String, unique=True, default="")
```
The `default=""` caused SQLAlchemy to convert any explicit `None` value back to `""` during INSERT.

## Why NULL solves it

SQLite handles NULL uniquely in UNIQUE constraints: **NULL != NULL**. Multiple rows can have `phone=NULL` without violating the UNIQUE constraint because each NULL is considered distinct from every other NULL.

This is standard SQL behavior:
- `""` is a value → UNIQUE sees it as equal to another `""`
- `NULL` is unknown/missing → UNIQUE never considers two NULLs as equal

## Where normalization is implemented

### `core/storage/customer_repository.py`

**`_normalize_phone()` static method** (line 8-12):
```python
@staticmethod
def _normalize_phone(phone):
    if phone is None or (isinstance(phone, str) and not phone.strip()):
        return None
    return phone
```
Converts `""`, whitespace-only strings, and `None` to Python `None` (which SQLAlchemy maps to SQL `NULL`).

**Applied in `create()`** at line 53:
```python
phone=self._normalize_phone(customer_data.get('phone', '')),
```

**Applied in `update()`** at lines 85-87:
```python
if key == 'phone':
    value = self._normalize_phone(value)
```

### `core/storage/customer_model_db.py`

**Removed `default=""`** from the `phone` column (line 12):
```python
phone = Column(String, unique=True)
```
This was necessary because SQLAlchemy's Python-side `default=""` was overriding the explicit `None` value during INSERT, converting `None` back to `""`.

### What was NOT changed (as required)
- `CustomerService` decision logic — untouched
- `resolve_customer()` — untouched
- Duplicate detection (`exists_by_phone`, `get_by_phone`) — untouched
- Database schema — no ALTER TABLE, no constraint changes
- UNIQUE constraint — preserved
- Other columns — untouched
