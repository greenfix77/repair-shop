# FINANCIAL F1 — Data / Domain Audit

**Project:** Laptop Repair Manager
**Phase:** F1 (Data/Domain Audit) — READ-ONLY
**Baseline:** `FINANCIAL_ROADMAP.md` v1.0
**Date:** audit performed against current working tree (uncommitted state after R12-FIX)
**Legend:** VERIFIED = traced in code · INFERRED = drawn from surrounding evidence · NOT FOUND = absent

---

## # 1. Executive Summary

**Overall status: PARTIAL → Partially blocked for a reliable customer ledger.**

The project already has more financial infrastructure than the domain model suggests:

- A **real payment ledger** (`payment_transaction` table) with per-event amount, date, method, transaction type (PAYMENT/REFUND) and a working write path in the Financial tab.
- A **profit service** built on per-repair part lines that **snapshot purchase price** and **sale price** per line.
- A **payment reconciliation service** and a **financial summary service** that already treat the ledger as the source of truth for `paid_amount`.

However the domain model is **not yet ready to produce a complete customer account**:

- `Repair` has **no persisted `customer_id`** (dropped at the model layer, despite being produced by the Repair dialog).
- There are **three inconsistent "total" formulas** (invoice calculator, Financial-tab widget, ProfitService gross) — there is currently **no single source of truth for the customer-payable amount**.
- **Discount exists only as a repair field, not as a ledger event** → it cannot become a ledger Credit without a decision.
- Direct payment history is reconstructable **only for data written after the ledger migration**; **legacy history was collapsed** into a single PAYMENT row.

Repository → Service layering is clean for catalogs; **financial logic still partly lives in the UI** (InvoiceWidget inline totals). This must not be replicated.

---

## # 2. Current Financial Data Model

| Domain | Current Source | Financial Fields | Status | Notes |
|---|---|---|---|---|
| Customer | SQLite `customer` (CustomerRepository) | none (no financial fields) | OK | PK `id`; `full_name`, `phone`, `email`, `national_id`, `city`, … |
| Repair header | `repairs` table (RepairDB) + `core/models.Repair` | `parts_cost`, `labor_cost`, `tax`, `discount`, `paid_amount`, `payment_status`, `payment_method`, `payment_date`, `financial_notes` | PARTIAL | No `customer_id` persisted; `parts_cost`=Σ part line sale totals, `labor_cost`=Σ service line totals (snapshots) |
| Repair service lines | `repair_service` (RepairServiceDB) | `unit_price`, `total_price`, `quantity` | OK | No cost/expense snapshot → service margin implicitly 100% |
| Repair part lines | `repair_part` (RepairPartDB) | `unit_price` (sale), `purchase_price_snapshot`, `total_price`, `quantity` | OK | Sale & purchase snapshotted per line on save |
| Additional charges | JSON column `additional_charges_json` | `unit_price`, `total_price`, `quantity` | OK | Line-level; referenced by ProfitService |
| Part catalog | `part` table (PartRepository) | `purchase_price`, `sale_price`, `default_sale_price`, `stock_quantity` | OK | Purchase vs sale explicitly separated |
| Service catalog | `service` table | `default_price` | OK | Used as initial sale price on lines |
| Payment ledger | `payment_transaction` (PaymentTransactionRepository) | `amount`, `payment_method`, `payment_date`, `transaction_type` (PAYMENT/REFUND/ADJUSTMENT), `repair_id`, `note`, `created_at` | OK (VERIFIED as write path) | Real multi-event history; `repair_id` FK-like (no SQL FK) |
| Invoice / totals | `invoice_calculator.calculate_invoice_totals` | parts, labor, tax, discount → subtotal/tax/total | WARNING | Formula duplicated; order conflicts with InvoiceWidget |
| Dashboard income | `PaymentReconciliationService` (ledger `payment_date` net) | SUM(PAYMENT)−SUM(REFUND) by date/month | OK | Cash-collection date semantics |
| Dashboard profit | `ProfitService` | parts_cost/revenue, service revenue, gross profit/margin, `delivery_date` window | OK | Analytical profit only |
| Customer stats | `customer_stats_service` | repair COUNTS only (total/delivered/in_progress) | PARTIAL | No financial aggregation per customer |

---

## # 3. Customer Domain

- **Representation:** SQLite row (`core/storage/customer_model_db.py`) + dict via `CustomerRepository._to_dict` (fields: id, customer_code, full_name, phone, email, website, national_id, address, city, province, postal_code, notes, created_at …).
- **Primary key:** `id` (int, autoincrement). `customer_code` unique human code (C######). VERIFIED.
- **How Repair references Customer:** ⚠️ **Not by FK.** `Repair`/`RepairDB` store only denormalized `customer_name` + `phone`. The Repair dialog resolves a `_selected_customer_id` at runtime and emits `customer_id` in `get_data()` (repair_dialog.py:393), but **`Repair.from_dict`/`to_dict` (core/models.py) drop it**, `RepairDB` has no `customer_id` column, and `SQLiteStorage.save_all` never writes it. **The id is available at the UI boundary and is lost at the model boundary** → CRITICAL GAP.
- **Reliable association:** NO for historical/general data — current linking is heuristic (phone match preferred, name fallback) in `customer_stats_service._match_key` and `LaptopRepairManager._has_related_repairs`. Ambiguous when two customers share phone/name. WARNING.
- **Historical missing references:** possible; heuristic fallback silently attributes a repair to *all* matching customers (`compute_customer_repair_stats` iterates `matched_ids`). INFERRED: this can over-count.
- **Authoritative customer access path:** `CustomerWorkflow → CustomerService → CustomerRepository` (single path, VERIFIED). No other code may create customers.
- **Search/filter:** exists — repository search on `full_name`/`phone`; Customers-tab live search wired. VERIFIED.
- **Customer statistics:** exist — repair counts per customer (`customer_stats_service`, used by Customers table). Financial aggregation per customer: **NOT IMPLEMENTED**.
- **Customer financial aggregation:** NOT FOUND.

| Item | Verdict |
|---|---|
| customer_id on Repair persisted | **GAP / CRITICAL** |
| Repair↔Customer reliable FK | **GAP / CRITICAL** |
| heuristic fallback | exists, WARNING |
| customer search/filter | PASS |
| customer stats (counts) | PASS |
| customer financial aggregation | GAP |

---

## # 4. Repair Financial Domain

Per-field audit (VERIFIED against `core/models.py`, `RepairDB`, `SQLiteStorage`):

| Field | Type | Persisted | Source | Meaning in code | Used by | Financial relevance | Potential issue |
|---|---|---|---|---|---|---|---|
| `id` | int | yes (PK) | add_repair assigns max+1 | repair key | everything, ledger `repair_id` | ledger linking | legacy JSON ids vs DB id |
| `customer_id` | – | **NO** | repair_dialog `get_data` emits | intended FK | **nowhere persisted** | critical for per-customer ledger | dropped by Repair.from_dict / RepairDB |
| `customer_name` | str | yes | dialog snapshot | display + heuristic link | table, stats, invoice | customer identification | no FK; name collisions |
| `phone` | str | yes | dialog snapshot | display + heuristic link | stats match | customer identification | no FK; format drift |
| `status` | str | yes | combo (4 values) | workflow stage | stats, dashboard, invoices | gate for delivered/revenue windows | no cancelled state |
| `receive_date` | str | yes | Persian picker | intake date | table | operational | not a cash date |
| `delivery_date` | str | yes | Persian picker | completion/delivery date | ProfitService windows | revenue/profit time window | empty on older records |
| `parts_cost` | int | yes | InvoiceWidget `get_data` = **Σ part line `total_price`** | snapshot of sold parts | invoice_calculator, table total | customer payable (sale) | **is SALE sum, not purchase cost** |
| `labor_cost` | int | yes | InvoiceWidget = **Σ service line `total_price`** | snapshot of charged services | invoice_calculator, table total | customer payable | empty lines → legacy migration in widget |
| `tax` | float | yes | widget `%` input | tax rate (%) | invoice_calculator/widget | increases payable | applied at inconsistent step |
| `discount` | int | yes | widget input | flat amounts OFF | invoice_calculator/widget | reduces payable (→ ledger Credit) | **not in ledger** |
| `paid_amount` | int | yes | widget (synced from ledger on load) | snapshot of amount paid | reconciliation vs ledger | balance | can drift from ledger; legacy snapshots |
| `payment_status` | str | yes | `financial_summary_service.payment_status_for` | unpaid/partial/settled | table, widget | balance state | derived, can disagree with ledger |
| `payment_method` | str | yes | combo | method text | widget | cash-flow detail | free text; legacy map ('کارتخوان'→POS) |
| `payment_date` | str | yes | Persian picker | date of the payment snapshot | dashboard (legacy? no — dashboard uses ledger now) | cash date | missing on legacy; dashboard ignores snapshot |
| `financial_notes` | str | yes | notes text | free-form | none | audit notes | informal |
| `service_lines` | list | yes (child table) | widget | per-line service: qty/unit/total, `service_id` | ProfitService | revenue | no labor cost snapshot |
| `part_lines` | list | yes (child table) | widget | per-line part: qty/`unit_price`/`total_price`/`purchase_price_snapshot`, `part_id` | ProfitService, widget | revenue + cost + profit | legacy lines lack purchase snapshot & part_id |
| `additional_charges` | list | yes (JSON) | widget | extra charge lines | ProfitService | revenue | no cost attached |

**Overall repair financials:** partial. Real, snapshotted lines exist; the header-level snapshot fields (`parts_cost`, `labor_cost`) duplicate line sums; no FK to customer.

---

## # 5. Invoice Calculation

**Authoritative formula** (`services/invoice_calculator.py`, VERIFIED):

```
subtotal   = parts_cost + labor_cost
tax_amount = subtotal * (tax/100)
total      = subtotal + tax_amount − discount
```
Identical copy in `services/calculations.calculate_invoice` (used by `table_service.build_table_rows` for the table's `هزینه کل` column).

**InvoiceWidget live formula** (`invoice_widget._recalculate` / `_update_payment` / `get_data`, VERIFIED — **this is financial logic in UI**):

```
prediscount   = services + parts + additional_charges
after_discount= max(0, prediscount − discount)
tax_amount    = int(after_discount * tax / 100)
final         = after_discount + tax_amount
```
Differences from the calculator: discount is applied **before** tax; **additional charges are included**; then `final` drives the widget's payment-status and remaining.

**ProfitService gross revenue** (`profit_service.py`, VERIFIED): `gross_revenue = parts_revenue + services_revenue + additional_charges` — **no tax, no discount, no charges in `پرداخت` classification**.

**Confirmed:** `Invoice Total == calculate_invoice_totals(repair_data)["total"]` **only** when the repair was persisted from the widget with **no additional charges and either no discount or no tax**. Otherwise the three "totals" differ:

- Calculator total: `(parts+labor)*(1+tax) − discount`
- Widget final: `(parts+labor+charges − discount)*(1+tax)`
- Gross (profit/summary): `parts+labor+charges`

Follow-through: invoice preview/PDF (`invoice_generator.py:15`, `:254`) and the table column use the calculator; the live Financial tab shows the widget value, and FinancialSummaryService/`payment_status` uses gross. **No single authoritative "customer payable" exists.** → HIGH/CRITICAL consistency gap. No formula change made or proposed here.

---

## # 6. Parts / Cost / Profit

Trace: `PartDB → RepairPartDB → InvoiceWidget._add_part_line → Repair.part_lines → ProfitService`.

- **Catalog purchase price:** `PartDB.purchase_price`. VERIFIED.
- **Catalog sale price:** `PartDB.sale_price` and `PartDB.default_sale_price`. `_add_part_line` sets `unit_price = default_sale_price` (fallback to purchase_price when sale ≤ 0). VERIFIED.
- **Per-repair sale price:** `RepairPartDB.unit_price` (editable per line in the Financial tab). VERIFIED.
- **Persisted per-line totals:** `unit_price`, `total_price = unit_price*qty`, `quantity`, `purchase_price_snapshot`. VERIFIED.
- **`repair_part.part_id`:** stored (nullable); VERIFIED.
- **Purchase price snapshotted per line:** YES for lines created via the Financial tab (`purchase_price_snapshot` written by InvoiceWidget + `SQLiteStorage`). VERIFIED.
- **Historical stability vs catalog price change:** GOOD — cost and sale are frozen per line (`purchase_price_snapshot`, `unit_price`), so later catalog edits do not alter history. VERIFIED by schema.
- **Link back to a catalog Part:** `part_id` stored, but **not a SQL FK and nullable**; legacy lines (created via repair_dialog migration, `part_id=None`) cannot be traced to a catalog Part. PARTIAL.
- **PURCHASE COST vs CUSTOMER SALE PRICE:** cleanly separated in both schema and formulas. VERIFIED.

**Sufficiency assessment:**

1. Customer outstanding balance → **BLOCKED by total-formula inconsistency** + no per-customer FK.
2. Customer ledger → **PARTIAL** — ledger has PAYMENT/REFUND; REPAIR_CHARGE/DISCOUNT not yet materializable cleanly.
3. Revenue → **READY** via ProfitService parts/service/charges revenue (choice of gross vs net-with-tax unresolved).
4. Parts cost → **READY** for new lines (`purchase_price_snapshot`); legacy lines default to 0 → overstated profit for legacy repairs unless data fixed.
5. Profit per repair → **READY** (ProfitService), qualifier: no tax/discount impact, services margin=100%.
6. Profit per customer → **PARTIAL** — possible only after per-repair customer attribution (FK) exists.
7. Historical profit reporting → **PARTIAL** — possible for line-based repairs; **legacy lines have no purchase snapshot and can be unattributed**.

---

## # 7. Payment Model

- **`paid_amount` semantics:** a **snapshot** on the Repair row (int). On the Financial tab it is **driven from the ledger** when loading (`_sync_paid_from_ledger` → `PaymentReconciliationService.net_paid_for_repair`), so today it semantically means *net paid per ledger (ΣPAYMENT−ΣREFUND)* once a repair has been opened in the tab. **It is not one payment, not necessarily "the latest" — it is the running net.** VERIFIED.
- **Multiple payment events:** **YES, real.** `payment_transaction` rows (one per PAYMENT/REFUND), each with `amount`, `payment_method`, `payment_date`, `transaction_type`, `note`, `created_at`, `repair_id`. Write path: InvoiceWidget `_create_ledger_transaction` (payment/refund buttons). VERIFIED.
- **Payment history per event:** stored (amount, date, method, type, note) and rendered in the Financial tab (`_render_payment_history_table` reads the repository). VERIFIED.
- **ADJUSTMENT type:** recognized by reconciliation (adds to net) but **no write path / no UI**. NOT FOUND in write paths.
- **Conceptual reconstruction test — Repair total 10M, Day1 3M, Day2 7M:**
  - New/system-ledger data: **YES — fully reconstructable** from two PAYMENT rows (amounts, dates, methods). VERIFIED.
  - **Legacy data** (repairs saved before the ledger migration): **NO — PAYMENT HISTORY GAP.** `init_db._migrate_legacy_payment_transactions` back-fills a **single** PAYMENT row (amount = stored `paid_amount`), collapsing any prior multi-payment history; the original day/amount/method split is unrecoverable without the historical database backup.
- Conclusion: schema *can* hold a true ledger; the gap is **legacy collapse**, not architecture.

---

## # 8. Date Semantics

| Date | Semantic (VERIFIED) |
|---|---|
| `receive_date` | intake date (Persian), repair-level; operational, not cash |
| `delivery_date` | completion/delivery date; used by **ProfitService as the revenue/profit time window** (dashboard revenue/profit by today/month prefix) |
| `payment_date` | **cash event date** on ledger rows; used by **dashboard income KPIs** (`SUM(PAYMENT)−SUM(REFUND)` for today / current `YYYY/MM`) via `PaymentReconciliationService` |
| DB `created_at` | transaction insert time (absolute), separate from Persian `payment_date` |
| `updated_at`/`created_at` on catalogs | record timestamps, not financial |

- Date used for **income (cash collection)**: ledger `payment_date`. Matches FINANCIAL_ROADMAP concept of cash collection. VERIFIED.
- Leftover header `payment_date` on Repair is legacy snapshot, **no longer consulted for dashboard income**.
- **Legacy records with missing `payment_date`:** likely (field defaults to `""`); the dashboard returns `0` for empty dates (safe), and no fallback exists — reported, unchanged.
- Profit-by-delivery vs income-by-payment deliberately differ (one is shop economics, one is cash). INFERRED from code split.

---

## # 9. Discount

- **Stored:** single integer `repair.discount` (header-level). VERIFIED.
- **Level:** repair-level only. No service-level or part-level discount fields exist. VERIFIED.
- **Entry into calculation:** `invoice_calculator.calculate_invoice_totals` (after tax) and InvoiceWidget (before tax, non-negative). VERIFIED.
- **Customer payable impact:** reduces payable in both formula branches. VERIFIED.
- **Discount as future ledger CREDIT:** **possible in principle (roadmap §9) but NOT today** — discount is a repair field with no ledger row and no date; historical credit reconstruction would use... no date. PARTIAL/BLOCKED until a DISCOUNT transaction + date semantics are decided.

---

## # 10. Refund / Cancellation

- **Refund:** **PARTIALLY IMPLEMENTED.** A `REFUND` ledger transaction can be recorded per repair from the Financial tab (`_on_add_refund_clicked`); it reduces net paid (`ΣPAYMENT − ΣREFUND`) and reconciliation/flags treat it accordingly. VERIFIED.
  - No UI to reverse a refund (would be another REFUND/debit) — partial.
- **Cancellation:** **NOT IMPLEMENTED.** `core.status` has exactly four statuses (`در انتظار`, `در حال تعمیر`, `تعمیر شده`, `تحویل داده شده`) — *no cancelled status*. `compute_customer_repair_stats` even notes "there is no cancelled status". Repair money remains chargeable. ROADMAP report tab lists "لغو شده" as a status → **architecture cannot currently represent cancellation; adding a status is a small schema/status addition (decision for F2/F3)**.
- **Reversing a payment / repair charge:** not modeled as reversal events (only REFUND). PARTIAL.

**Distinction:** cancellation = *not implemented* (would work after adding a status + logic); legacy multi-payment history reconstruction = *architecture cannot support* (collapsed at migration).

---

## # 11. Existing Financial Services

| Service | Owns (VERIFIED) | Status |
|---|---|---|
| `invoice_calculator.calculate_invoice_totals` | invoice total formula (parts+labor, tax, discount) | should stay authoritative for **printed/table invoice** |
| `calculations.calculate_invoice` | identical duplicate of the above (used by table column) | duplication — LOW |
| `profit_service.ProfitService` | profit/`gross_revenue`/margin from lines (purchase snapshot) | authoritative for **profit/economics** |
| `payment_reconciliation_service` | net paid from ledger, reconcile vs snapshot, today/month income | authoritative for **paid amount & cash income** |
| `financial_summary_service` | composes profit + ledger → paid/remaining/status | attempts single source; blocked by total inconsistency |
| `repair_service` | counts + delegate income to reconciliation | fine |
| `statistics` / `customer_stats_service` | status counts / per-customer repair counts | fine, not financial |
| `table_service` | display row build (calls calculations) | display |
| `customer_service` / `customer_workflow` | customer CRUD + search; no financials | as-is |
| `part_service` / `service_service` | catalog CRUD + default prices | as-is |

**Where financial logic lives in UI (do not replicate):** `invoice_widget` computes `final`/paid/remaining/status inline (`_recalculate`, `_update_payment`, `get_data`) — a second owner of the total formula, diverging from the calculator.

**Duplication map:** total formula ×2 (services) + ×1 (UI, diverging); paid/status already centralized in `FinancialSummaryService` (good — keep it).

**Future `financial_report_service.py`:** appropriate (report DTO assembly per roadmap §22). **Not created.**

---

## # 12. Customer Report Readiness

Requirement (per `FINANCIAL_ROADMAP.md` §13–17): | Classification |

| # | Requirement | Status | Reason |
|---|---|---|---|
| 1 | Customer information | **READY** | CustomerRepository full fields; CustomerWorkflow single path |
| 2 | Repair history | **PARTIAL** | Repairs listable, but repair→customer linkage is heuristic (phone/name), no FK |
| 3 | Repair status | **READY** | 4 statuses stored + status styling exists |
| 4 | Repair amount | **PARTIAL** | `total_cost`/calculator available, but 3 competing "totals"; line rows exist but header amount is a snapshot |
| 5 | Customer ledger | **PARTIAL** | Ledger rows exist (payment/refund) but REPAIR_CHARGE and DISCOUNT rows are not materialized; totals inconsistent |
| 6 | Payment history | **READY (new data) / BLOCKED (legacy)** | Repository + UI history table exist; legacy collapsed to single row |
| 7 | Current balance | **PARTIAL** | Formula `gross − net_paid` exists in FinancialSummaryService but `gross` excludes tax/discount → balance ≠ what customer actually owes per the invoice formula |
| 8 | Date-range filtering | **PARTIAL** | Dates exist on repairs and ledger; no reusable date-range filter service yet |
| 9 | Financial summary | **PARTIAL** | counts (statistics) ready; financial summary ready for gross/paid but not for taxed/discounted payable |
| 10 | Profit by customer | **BLOCKED** | requires per-repair customer attribution (FK) → currently blocked by #2 |
| 11 | Link from ledger entry to Repair | **READY** | ledger rows carry `repair_id`; repairs keyed by id (repair_id → repair dict) — a `{}` won't be needed |
| 12 | Future PDF/Print | **PARTIAL** | Invoice HTML/PDF pipeline exists (invoice_generator/exporter) as template; report HTML not built |

Overall: **customer report is BLOCKED mainly by (a) missing persisted customer_id and (b) the unresolved "total" / balance formula.**

---

## # 13. Ledger Readiness

| Type | Reconstruct from current data? | Amount | Date | Repair ref | Historical reliability | Verdict |
|---|---|---|---|---|---|---|
| `REPAIR_CHARGE` | conceptually from repair totals | yes but 3 competing totals | `receive`/`delivery`/now — no dedicated charge date | repair id | **NO ledger row exists** — must be generated retrospectively; totals may differ from then-current invoice | **PARTIAL/BLOCKED** |
| `PAYMENT` | yes (ledger rows) | `amount` per row | `payment_date` | `repair_id` | **NEW data YES; legacy collapsed to one row** | **READY (new) / GAP (legacy)** |
| `DISCOUNT` | no (discount only on repair) | amount known | no date stored | repair id | no event, no date | **PARTIAL/BLOCKED** |
| `REFUND` | yes (ledger rows, type REFUND) | `amount` | `payment_date` | `repair_id` | new data yes; legacy: refunds were not recorded | **READY (new)** |
| `ADJUSTMENT` | recognized by reconciliation, **no write path** | n/a | n/a | `repair_id` in repo reads | n/a | **BLOCKED (no producer)** |

**Key verdict:** the schema *can* host a ledger; **the missing pieces are the producers (charge/discount/adjustment rows + dates) and the customer link, not the storage table.** Do not create the table now.

---

## # 14. Data Integrity Findings

- **`customer_id` missing everywhere in persistence** (model, `RepairDB`, storage) despite being produced by the dialog → CRITICAL.
- **Legacy payment history collapsed** to a single PAYMENT back-fill row. HIGH.
- **Legacy part/service lines:** created by widget migration with `part_id=None` and **no `purchase_price_snapshot`** → ProfitService treats purchase cost as 0 → legacy profit overstated and lines untraceable to catalog. MEDIUM/HIGH.
- **`payment_date` missing on many legacy repairs** (field default `""`); dashboard degrades gracefully to 0; no fallback. MEDIUM.
- **`paid_amount` snapshot vs ledger drift:** reconciliation (`PaymentReconciliationService`) exists specifically to detect MATCH/MISMATCH/NO_LEDGER but nothing enforces sync; FinancialSummaryService prefers ledger. MEDIUM.
- **`paid_amount > total`:** widget clamps in `_update_payment` (paid forced down to final when remaining==0); no DB-level guard; legacy overpayments theoretically possible. LOW/MEDIUM.
- **Negative values:** `after_discount` is clamped via `max(0,…)` in widget; `calculate_invoice_totals` does **not** clamp (negative total possible if discount > subtotal+tax). LOW.
- **Legacy JSON vs SQLite/dict discrepancies:** repair load migrates lines in the widget; `Repair.from_dict` normalizes to typed fields; old records lacking keys default safely. LOW.
- **Nullable financial fields:** `part_id`, `service_id` nullable with snapshots as name text — acceptable but weakens linking. LOW.
- **Old records that cannot participate safely:** any legacy repair with neither phone nor name will never be attributed to a customer; legacy overpaid/underpaid rows flagged only via reconciliation. INFERRED.

---

## # 15. Architecture Findings

**Recommended future architecture (per roadmap §22):**
```
Repository (existing) → Service/Domain Logic → Report DTO/ViewModel → Report UI → PDF/Print
```
Reusable components: `PaymentTransactionRepository`, `PaymentReconciliationService`, `ProfitService`, `FinancialSummaryService`, `CustomerRepository`/`CustomerWorkflow`, statistics services, `invoice_generator` (as PDF/HTML pattern), `date_service`.

**Where financial logic currently lives in UI (do NOT refactor, just avoid re-implementing):**
- `ui/widgets/invoice_widget.py` — inline total/paid/remaining/status formulas (`_recalculate`, `_update_payment`, `get_data`). This is the diverging second source of the total formula.
- `ui/dialogs/repair_dialog.py` — merges invoice data into the repair dict (structural, not formulaic).

**Positive boundaries:** catalogs already satisfy Repository→Service→UI cleanly; the ledger, profit and reconciliation services already centralize the *advanced* financial math. The weak boundary is the **repair aggregate** (no dedicated RepairsRepository yet; `SQLiteStorage` owns whole-table read/write with no FK enforcement) and the **heuristic customer linkage**.

---

## # 16. Gaps

**CRITICAL GAP**
1. **No persisted `customer_id` on Repair** — dropped by `Repair.from_dict/to_dict`, absent from `RepairDB` and `SQLiteStorage`. Blocks profit-per-customer and reliable ledger reporting.
2. **No single authoritative "customer payable" total** — three inconsistent formulas (invoice_calculator, InvoiceWidget inline, ProfitService gross). Blocks balance/ledger correctness.

**HIGH GAP**
3. **Financial total formula duplicated and diverging in UI** (InvoiceWidget) — violates roadmap §22.
4. **Legacy multi-payment history collapsed** to one back-filled row — historical payment reconstruction impossible.
5. **Discount never materialized as a ledger event (no date/row)** — cannot become ledger Credit historically.
6. **Legacy repair lines lack `purchase_price_snapshot`** (and `part_id`) — profit overstated, untraceable cost.
7. **No cancelled status / cancellation support** — roadmap currency "لغو شده" unrepresentable.

**MEDIUM GAP**
8. **Heuristic repair→customer linkage** (phone/name) with ambiguous over-attribution; no FK.
9. **`paid_amount` snapshot can drift from ledger** — reconciliation is diagnostic only.
10. **Service cost not modeled** — services always 100% margin; cannot compute true shop cost of labor.
11. **ADJUSTMENT has no producer/UI.**

**LOW GAP**
12. `calculations.calculate_invoice` duplicates `invoice_calculator` formula.
13. Missing/empty `payment_date` fallbacks on legacy rows; negative-total not clamped in calculator branch.
14. Header `parts_cost`/`labor_cost` snapshots duplicate line sums (drift risk when only lines edited).

---

## # 17. Existing Capabilities That MUST NOT Be Reimplemented

Future F2–F7 phases must **reuse** (not recreate):
- `ProfitService.calculate_profit` — profit/cost/margin.
- `PaymentReconciliationService` — net paid per repair, today/month income (ledger `payment_date`), reconciliation.
- `FinancialSummaryService.payment_status_for` / `remaining_for` / `calculate` — single ladder + composition.
- `PaymentTransactionRepository` — ledger create/read (PAYMENT/REFUND).
- `CustomerWorkflow → CustomerService → CustomerRepository` — customer data, search, `count_customers`, `get_customer` (Single source of truth).
- `invoice_calculator.calculate_invoice_totals` — the drifted-toward-total formula (after alignment decision) for printed/table invoice.
- `invoice_generator` / `invoice_exporter` — HTML/PDF pipeline patterns.
- `customer_stats_service` — count-based customer statistics.
- `SQLiteStorage` (repair aggregate persistence) and `status.py`/`date_service.today_persian`.

Do **not** re-derive paid amounts from stored `paid_amount` snapshots (ledger wins per FinancialSummaryService). Do **not** recompute profits outside ProfitService.

---

## # 18. F2 Prerequisites

Only the decisions/fixes that MUST precede the ledger model phase (F2). **Not started here.**

1. **Decide the authoritative "customer payable / total" formula.** Choose one (recommend: align InvoiceWidget & table with `invoice_calculator`, extend it to *include additional charges* and pin tax/discount ordering) and make it the single source of truth that also drives a future REPAIR_CHARGE.
2. **Persist `customer_id` on Repair** (dataclass + `RepairDB` column + `SQLiteStorage` + migration for existing rows via heuristic with a confidence rule). Required so ledger entries and reports are attributed to the right customer.
3. **Define DISCOUNT ledger event semantics** (as ledger Credit) — including its **date** (payment_date of the discount event; historical repairs get a back-fill policy decision) and interaction with balance.
4. **Define REPAIR_CHARGE generation policy** — materialize at repair save, or derive lazily; which total; which date (decision depends on #1).
5. **Decide legacy migration policy** — keep collapsed payment history (document as "prior to migration"), and decide whether to back-fill purchase-price snapshots for legacy lines or exclude them from profit reports.
6. **Decide cancellation representation** (add a cancelled status) — only if F2 ledger must account for voided repairs.
7. **Explicitly separate "customer account" vs "shop economics"** per roadmap in every F2 decision; profit must never enter the ledger.

---

## # 19. Regression Rules

Financial invariants future implementations must preserve (baseline = roadmap + traced code):

1. **Purchase price ≠ sale price.** Customer account uses **sale** (`unit_price`); shop cost uses `purchase_price_snapshot`. Never swap.
2. **Customer account ≠ shop profit.** Ledger Debits/Credits affect the customer balance only; profit is computed separately (ProfitService) and never debits/credits the account.
3. **PAYMENT is always Credit; DISCOUNT is Credit; REFUND is Debit** (roadmap §3, §7–§10); over-payment must produce a visible "بستانکار" state, not a bare negative.
4. **Ledger-derived `net_paid_for_repair` remains the source of truth for paid** (FinancialSummaryService) — never replace with the stored snapshot.
5. **Dashboard income = ledger net by `payment_date`** (today + `YYYY/MM`); do not revert to delivery-date income.
6. **Historical repair lines are immutable snapshots** (`unit_price`, `purchase_price_snapshot`, `total_price`); catalog price changes must never rewrite history.
7. **The invoice total formula stays single-sourced** once decided; no new inline formula copies in UI.
8. **Repair `id` remains the ledger/`repair_id` reference**; ledger links must survive deletion policies (currently ledger is not FK-constrained).
9. **Empty/missing dates degrade to 0 (or are explicitly excluded), never crash or invent dates.**
10. **No wholesale rewrite of `SQLiteStorage`/`RepairDB`** without F2 decision review (backward compatibility of existing DB).

---

*End of F1 audit. Source files untouched; database untouched; no service/model created.*