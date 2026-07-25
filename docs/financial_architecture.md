# Financial Architecture

This document describes the financial architecture as it exists after the current phase. It documents only what is implemented.

## Invoice Immutability Rules

- Invoices own their own immutable snapshots.
- Once a `repair_part` or `repair_service` line is created, its `unit_price`, `total_price`, and `purchase_price_snapshot` are frozen on the line.
- Catalog changes never modify existing invoices.
- The invoice widget captures the catalog `purchase_price` and `default_sale_price` at the moment a part line is inserted; later catalog edits do not retroactively update the line.
- The Services Catalog behaves identically: `default_price` is snapshotted into `unit_price` at insert time.

## Pricing Rules

- **Purchase Price** belongs to the Parts Catalog. It represents inventory cost.
- **Suggested Sale Price** (`default_sale_price`) belongs to the Parts Catalog. It represents the recommended selling price for new invoice lines.
- **Purchase Price Snapshot** (`purchase_price_snapshot`) belongs to invoice part line items. It is captured at insert time.
- **Sale Price Snapshot** (`unit_price` on a `repair_part` line) belongs to invoice line items. It is captured at insert time using `default_sale_price` from the catalog, falling back to `purchase_price` only when `default_sale_price` is missing or zero.
- Users may freely edit the snapshot values on an active invoice line. Those edits affect only that repair.
- Old Parts Catalog rows that do not contain `default_sale_price` behave as `default_sale_price = purchase_price`. There is no migration that resets data.

## Additional Charges Rules

- **Charges belong to a Repair.** Each repair owns an `additional_charges` collection.
- Each charge item is a dict with the shape:
  - `type` (string; type values are not restricted in this phase)
  - `title` (string)
  - `amount` (integer)
  - `note` (string)
- Charges are stored as **immutable snapshots** inside the repair.
- The Repair dataclass (`core/models.py`) carries `additional_charges` as a `List[Dict]` defaulting to `[]`.
- SQLite persistence stores the list as a JSON-encoded `additional_charges_json` column on the `repairs` table. The column default is `'[]'`.
- Existing repairs from prior versions are migrated additively: the column is added if missing, and any null/empty value is initialized to `'[]'`. No data is rewritten.
- JSON file persistence (`repairs.json` via `RepairsStorage`) round-trips the dict transparently because the field is simply part of the repair dict.
- **Reports must always read repair snapshots.** A charge is read from the repair dict, never recomputed from an external source.
- No calculation, total, or aggregation is performed on `additional_charges` in this phase. That work belongs to a later phase.

## Charges Catalog

- The Charges Catalog is **independent** from repairs and invoices. It is its own first-class entity, modeled the same way as the Parts and Services catalogs.
- A Catalog `Charge` owns:
  - `id`
  - `name`
  - `category` (free-form string; users may select from predefined categories or type their own)
  - `default_amount`
  - `description`
  - `is_active`
- The Catalog is stored in its own `charge` SQL table via `ChargeDB` / `ChargeRepository` / `ChargeService`. No table is shared with Parts, Services, or repairs.
- Editing the Charges Catalog **never modifies existing repairs.** Repairs still own their own `additional_charges` snapshots, captured at the time the repair was authored.
- Additional Charges **inside repairs remain immutable snapshots.** A repair's charges are read from the repair dict, never recomputed or refreshed from the Catalog.
- Future invoice integration will snapshot Catalog data at the moment a charge is added to a repair, exactly like Parts (`default_sale_price`) and Services (`default_price`) already do. Until that integration exists, repairs continue using only their own `additional_charges` list.
