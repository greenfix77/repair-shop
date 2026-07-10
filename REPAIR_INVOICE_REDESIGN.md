# Repair Invoice Redesign

> Date: 2026-07-10
> Scope: Replace the simple financial fields in the Repair dialog with a full
> invoice system integrated with the Services and Parts catalogs.

## 1. Overview

The Financial tab in `RepairDialog` has been replaced with an `InvoiceWidget`
that provides a complete repair invoice with:

- **Services section**: Add services from the catalog, edit quantity/price, remove rows
- **Parts section**: Add parts from the catalog, edit quantity/price, remove rows
- **Invoice summary**: Auto-calculated totals with editable tax and discount
- **Payment section**: Paid amount, remaining balance, payment status
- **Financial notes**: Free-text notes field

## 2. New Tables

### `repair_service`

| Field                  | Type    | Constraints       |
|------------------------|---------|-------------------|
| id                     | Integer | PK, autoincrement |
| repair_id              | Integer | NOT NULL (FK)     |
| service_id             | Integer | nullable          |
| service_name_snapshot  | String  | default ""        |
| quantity               | Integer | default 1         |
| unit_price             | Integer | default 0         |
| total_price            | Integer | default 0         |

### `repair_part`

| Field                | Type    | Constraints       |
|----------------------|---------|-------------------|
| id                   | Integer | PK, autoincrement |
| repair_id            | Integer | NOT NULL (FK)     |
| part_id              | Integer | nullable          |
| part_name_snapshot   | String  | default ""        |
| quantity             | Integer | default 1         |
| unit_price           | Integer | default 0         |
| total_price          | Integer | default 0         |

### New columns on `repairs` table

| Column            | Type    | Default             |
|-------------------|---------|---------------------|
| paid_amount       | Integer | 0                   |
| payment_status    | String  | 'پرداخت نشده'       |
| financial_notes   | String  | ''                  |

These columns are added via `ALTER TABLE` migration in `init_db.py` when they
don't already exist, preserving the existing table and data.

## 3. Why Snapshots?

The `service_name_snapshot` and `part_name_snapshot` fields preserve the
original name and price at the time the invoice was created. This ensures
that invoices remain accurate even if catalog items are renamed, repriced, or
deleted later.

## 4. Calculation Rules

```
service_subtotal = Σ(service_line.quantity × service_line.unit_price)
part_subtotal    = Σ(part_line.quantity × part_line.unit_price)
pre_discount     = service_subtotal + part_subtotal
after_discount   = max(0, pre_discount - discount)
tax_amount       = int(after_discount × tax_percent / 100)
final_amount     = after_discount + tax_amount
remaining        = max(0, final_amount - paid_amount)
```

- Tax and discount are editable.
- All other values are calculated automatically.
- Numbers are formatted with thousand separators.
- Negative remaining is not allowed (paid amount is clamped to final_amount).

## 5. Payment Status Logic

| Condition                    | Status          | Color   |
|------------------------------|-----------------|---------|
| remaining = 0, final > 0     | تسویه شده       | Green   |
| paid > 0, remaining > 0      | پرداخت جزئی     | Orange  |
| paid = 0                     | پرداخت نشده     | Red     |

## 6. Migration Behavior

When opening an old repair that has no `service_lines` or `part_lines`:

- `labor_cost` → migrated to a service line named "هزینه تعمیر"
- `parts_cost` → migrated to a part line named "قطعات"
- `tax` and `discount` → preserved on the repair
- Historical data is never lost

The migration happens in `InvoiceWidget.load_data()` and is purely a UI
display migration. The original `parts_cost` and `labor_cost` fields remain
on the `repairs` table for backward compatibility. When saving,
`get_data()` returns both the invoice lines AND the computed `parts_cost`/
`labor_cost` totals (derived from the invoice lines), keeping the old
fields in sync.

## 7. Architecture

### Data Flow

```
SQLiteStorage.load_all()
  → loads repairs + service_lines + part_lines from DB
  → returns list of dicts with embedded line lists

app.py
  → passes repair dict to RepairDialog(repair_data=...)
  → RepairDialog.load_data() calls InvoiceWidget.load_data()
  → InvoiceWidget renders tables + summary

RepairDialog.get_data()
  → calls InvoiceWidget.get_data()
  → returns dict with service_lines, part_lines, payment fields

app.py
  → add_repair() / update_repair() merge data into in-memory list
  → save_data() calls SQLiteStorage.save_all()
  → SQLiteStorage saves repairs + invoice lines to DB
```

### Files

| File | Role |
|------|------|
| `core/storage/repair_service_model_db.py` | RepairServiceDB SQLAlchemy model |
| `core/storage/repair_part_model_db.py` | RepairPartDB SQLAlchemy model |
| `core/storage/repair_model_db.py` | Extended with payment columns |
| `core/storage/init_db.py` | Registers new models + runs column migration |
| `core/models.py` | Repair dataclass extended with new fields |
| `core/storage/sqlite_storage.py` | Loads/saves invoice lines + payment fields |
| `ui/widgets/invoice_widget.py` | Full invoice UI (services, parts, summary, payment) |
| `ui/dialogs/repair_dialog.py` | Financial tab replaced with InvoiceWidget |

### Reuse

- `ServiceService` — for service search and creation
- `PartService` — for part search and creation
- `ServiceEditDialog` — for creating new services from the invoice
- `PartEditDialog` — for creating new parts from the invoice
- `CustomerWorkflow` — unchanged, customer selection is separate

## 8. UX Features

- Full RTL support
- Search with QCompleter (partial match, keyboard navigation, Enter selects)
- "ایجاد خدمت جدید" and "ایجاد قطعه جدید" buttons open the catalog dialogs
- Newly created items are immediately available in the completer
- Quantity and price are editable via QSpinBox cell widgets
- Row totals update instantly when quantity or price changes
- Summary recalculates instantly
- Payment status updates automatically
- Placeholder text when tables are empty ("هیچ خدمتی/قطعه‌ای اضافه نشده است")
- Tab navigation works throughout

## 9. Validation

- Quantity must be greater than zero (reset to 1 if set to 0)
- Prices cannot be negative (reset to 0 if negative)
- Paid amount cannot be negative (QSpinBox minimum is 0)
- Friendly Persian validation messages

## 10. Future Inventory Integration

Phase 2 (not yet implemented):

1. **Stock deduction**: When a repair is saved with parts, deduct quantities
   from `PartDB.stock_quantity`.
2. **Low-stock warnings**: Alert when stock falls below a threshold.
3. **Stock return**: When a repair is cancelled or a part is removed,
   return quantities to stock.
4. **Service cost reporting**: Revenue analysis by service type.
5. **Parts profit margin**: Track profit per part (sale_price - purchase_price).

No inventory movements are implemented in this phase.

## 11. Verification

- `python -m py_compile app.py` passes
- Application launches normally
- Add multiple services and parts via completer search
- Create new service/part from the invoice → immediately available
- Edit quantities and prices → totals update instantly
- Save and reopen → all invoice lines persist
- Payment status updates correctly (پرداخت نشده / پرداخت جزئی / تسویه شده)
- Old repairs display historical values via migration
- Services, Customers, Parts, and Repairs tabs still work
