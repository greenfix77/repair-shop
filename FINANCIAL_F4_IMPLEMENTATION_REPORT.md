# FINANCIAL F4 — Implementation Report

**Project:** Laptop Repair Manager
**Phase:** F4 — Customer Report Service / DTO Layer
**Baseline documents:** `FINANCIAL_ROADMAP.md` v1.0 · `FINANCIAL_F1_DATA_DOMAIN_AUDIT.md` · `FINANCIAL_F1_5_IMPLEMENTATION_REPORT.md` · `FINANCIAL_F2_IMPLEMENTATION_REPORT.md` · `FINANCIAL_F3_IMPLEMENTATION_REPORT.md`
**Date:** 2026-09-03
**Status:** **COMPLETE** (ADJUSTMENT remains DECISION REQUIRED, carried from F1.5/F2/F3; two report requirements are explicitly DEFERRED — see §Risks)

---

## Objective

Implement the Customer Report Service / DTO layer on top of the F3 `CustomerLedgerService`: one stable, deterministic, read-oriented `CustomerReport` model that the future F5 UI / PDF phases consume directly — with **zero financial math of its own**, zero UI, zero persistence, zero schema changes.

## F3 Baseline Verified

Before implementation, the F3 layer was re-verified in code: `CustomerLedgerService.get_customer_ledger / get_customer_balance / get_totals`, `CustomerLedgerEntry` (order, running balance, debit/credit/signed_effect, `unsupported_events`, `unattributed_events`), the central `EVENT_LEDGER_MAP`, and the F2 attribution policy. The report performs **no recalculation** of any financial semantic — it transforms DTO shapes and adds per-type signed nets derived from F3 entry effects only.

## Report Architecture

```
FinancialEventService (F2, authority — untouched)
        ↓
CustomerLedgerService (F3, authoritative ledger — untouched*)
        ↓
CustomerReportService (F4 — DTO assembly only)
        ↓
CustomerReport DTOs  →  future F5 UI / PDF
```

\* one additive, semantics-free F3 extension, documented in §Ledger integration: `payment_method` passthrough on `CustomerLedgerEntry`.

## DTO / Model Structure

`services/customer_report_service.py` — lightweight dataclasses (project style), `as_dict()` for F5/PDF serialization, fully deterministic (no timestamps):

| DTO | Content |
|---|---|
| `CustomerReport` | customer_id · date_from · date_to · customer_found · summary · ledger · payment_history · repair_history · shop_economics |
| `CustomerSummary` | customer_id, customer_name, phone, repair_count, completed_repair_count, active_repair_count, total_repair_charge, total_payment, total_discount, total_refund, current_balance, balance_status |
| `LedgerReport` | entries (F3 `CustomerLedgerEntry.as_dict()` in F3 order) · total_debit · total_credit · balance · unsupported_events · unattributed_events |
| `PaymentHistory` | items (windowed PAYMENT/REFUND ledger entries incl. payment_method) · total_paid · total_refunded |
| `RepairHistoryItem` | repair_id, receive_date, delivery_date, status, brand, model, description, ledger_charge (net from events, or None), ledger_discount (net from events, or None) |
| `ShopEconomics` | repair_count_included, parts_cost, gross_revenue, gross_profit, excluded_legacy_repairs, note |

Balance status uses the roadmap §8 account states from the F3 signed balance: **`تسویه`** (zero) / **`بدهکار`** (balance > 0, customer owes) / **`بستانکار`** (balance < 0, customer credit). No zero-floor — credit balances survive (F4.12).

## Customer Summary Fields

- **Totals are signed sums of F3 entry effects per event type** (no independent formula): `total_repair_charge = Σ signed(REPAIR_CHARGE)`, `total_payment = −Σ signed(PAYMENT)`, `total_discount = −Σ signed(DISCOUNT)`, `total_refund = Σ signed(REFUND)`. Invariant (tested): `total_repair_charge − total_payment − total_discount + total_refund == current_balance`.
- Summary reflects the customer's **CURRENT (all-time)** state — the roadmap §13 header KPIs (مانده فعلی حساب) are current-state values. With no date range, summary and ledger totals coincide (verified).
- Repair counts mirror the existing `customer_stats_service` convention (completed = `تحویل داده شده`/`تعمیر شده`; active = the rest — there is no cancelled status in `core.status`). Repairs are attributed **only** by the persisted `customer_id` (no heuristics); legacy repairs without customer_id are excluded from counts.

## Ledger Integration

`report.ledger` is the F3 result for the requested range, entries shape-transformed to dicts:
- entries identical to `[e.as_dict() for e in F3 entries]` (F4.5),
- order preserved (F4.6), running balances preserved (F4.7),
- debit/credit totals and balance preserved (F4.8),
- `unsupported_events` / `unattributed_events` passthrough (F4.17/F4.18/F4.22).

**F3 extension (additive, semantics-free):** `CustomerLedgerEntry.payment_method` — passthrough metadata from the event so payment history can show the method without a second event query. No F3 test required changes (its key assertions are supersets).

## Payment / Refund History

Derived from the **windowed F3 ledger entries** filtered to `PAYMENT`/`REFUND` — ledger-consistent by construction (same rows, same order, same running arithmetic). PAYMENT remains a credit; REFUND remains a debit; `total_paid` / `total_refunded` are column sums of those entries. No new payment calculation exists.

## Repair History Strategy

- Read-only load of repairs attributable by the authoritative persisted `customer_id` (the application's standard `SQLiteStorage.load_all` read, filtered — no new repository, no heuristics).
- Descriptive fields only (dates, status, brand/model, issue) plus **ledger-derived** per-repair nets: `ledger_charge` = Σ signed REPAIR_CHARGE effects, `ledger_discount` = Σ signed DISCOUNT effects; **None** when the repair has no events (never reconstructed from mutable repair totals — F4.19 proves the report shows the event-derived 1,000,000 even after the repair total is edited to 1,500,000 without materialization, and shows 1,500,000 only after the F2 delta event exists, with the original entry row unchanged).
- Repair history is an operational view (receive/delivery dates) and is **not** filtered by the financial event-date range — different date semantics, documented here and in the DTO docstrings.

## Date Filtering

Financial sections (`ledger`, `payment_history`) reuse F3's financial-event date semantics verbatim: `date_from` / `date_to` **inclusive** (F4.13–F4.15 verify exact endpoint inclusion and equality with `CustomerLedgerService.get_customer_ledger(customer_id, date_from, date_to)`). No current-date, repair-date or row-order substitutes. Summary (current state), repair history (operational) and shop economics (all-time) intentionally use their own documented semantics.

## Customer Filtering

`customer_id` only. Customer identification via the authoritative path `CustomerService → CustomerRepository` (Workflow path); unknown ids produce an empty, well-formed report with `customer_found = False` (F4.1). No name/phone matching anywhere in F4; legacy attribution remains F2/F3's responsibility.

## Profit / Cost Separation

`shop_economics` is computed by **ProfitService** (unchanged) over customer_id-attributable repairs: `parts_cost` (purchase snapshots), `gross_revenue`, `gross_profit`, plus `excluded_legacy_repairs` (legacy repairs without customer_id are excluded). The block is detached metadata: it never enters `current_balance`, the ledger rows, or any customer-accounting field (F4.20: balance equals the F3 balance exactly and the summary carries no profit keys). No `balance = revenue − cost − payments` style error exists.

## ADJUSTMENT Handling

Unresolved (DECISION REQUIRED, carried from F1.5/F2/F3). F4 assigns no direction, includes nothing in any balance, and creates no producer. ADJUSTMENT rows surface only through F3's `unsupported_events` (reason `adjustment_direction_unresolved`) and leave the balance untouched (F4.18).

## Legacy Handling

Legacy PAYMENT/REFUND rows (no `customer_id`) attribute through their repair's F1.5-authoritative `customer_id` and appear correctly in the attributed customer's report, including payment history (F4.21). Orphaned events (missing repair) remain unattributed: visible via `unattributed_events`, never booked into any customer's report (F4.22). Legacy repairs without `customer_id` are excluded from repair history/counts/shop economics and counted in `shop_economics.excluded_legacy_repairs`.

## Files Changed

| File | Change |
|---|---|
| `services/customer_ledger_service.py` | additive `payment_method` passthrough field on `CustomerLedgerEntry` (+ population in `build_ledger_entries`); no semantic change (F4.19 note) |

## Files Created

| File | Purpose |
|---|---|
| `services/customer_report_service.py` | F4 report DTOs + `CustomerReportService` |
| `services/test_financial_f4.py` | F4 validation suite (2 phases, 24 checks) |
| `FINANCIAL_F4_IMPLEMENTATION_REPORT.md` | this report |

## Tests Added

`python services/test_financial_f4.py` (isolated subprocess phases; production DB never written):

- **report (22):** F4.1 empty report; F4.2 summary fields (name/phone/totals/balance/status + the identity `charge − payment − discount + refund == balance`); F4.3 repair count; F4.4 completed vs active; F4.5–F4.8 ledger passthrough (entries/order/running balances/totals identical to F3); F4.9 payment history (method, total_paid); F4.10 refund history (debit, balance increases); F4.11 discount stays a credit; F4.12 overpayment → negative balance + `بستانکار`; F4.13–F4.15 inclusive from/to/from+to (windowed ledger + payment history equal F3's window); F4.16 unrelated customer excluded; F4.17 unknown event → unsupported, never booked; F4.18 ADJUSTMENT unresolved, balance untouched; F4.19 repair edits never rewrite event-derived values (discriminating test: edit without materialization → report still shows the event amount); F4.20 profit separate from balance; F4.23 determinism (`as_dict()` equality); F4.R realistic mixed sequence (charge 10,000,000 / payment 3,000,000 / discount 500,000 / refund 200,000 → balance **6,700,000**, status بدهکار, identical to F3).
- **legacy (2):** F4.21 legacy attribution via the repair link (payment history + credit balance −500,000 visible, `ledger_charge` None — no reconstruction); F4.22 orphaned/unattributed events preserved + excluded.

## Test Results

**F4 targeted validation: 24/24 PASS** (report 22, legacy 2). All results from actual executions.

## Regression Results

- **F3 suite: 31/31 PASS** (F4.24).
- **F2 suite: 42/42 PASS.**
- **F1.5 suite: 40/40 PASS.**
- Existing suites: `test_verify_refactor.py`, `test_customer_repository.py`, `test_sqlite_storage.py` — all exit 0 (isolated CWDs).
- `compileall` over core/services/ui/controllers/app.py — OK; per-step `py_compile` — OK.
- Known pre-existing failure unchanged: stale `services/test_customer_service.py` (removed API; documented since F1.5). No old test was modified for F4.

## Database Safety

Zero migrations, zero new tables, zero new columns, zero startup backfills. The full F4 suite leaves the production `repair_manager.db` byte-identical (UTC mtime compared before/after — unchanged; state: 5 repairs, 9 payment rows, 0 system events). All suite phases run in isolated temporary CWDs (the DB path is CWD-relative). No commits, branches, stashes, resets, or Git configuration changes; no line-ending changes.

## Scope Verification

Implemented: `CustomerReport`/`CustomerSummary`/`LedgerReport`/`PaymentHistory`/`RepairHistoryItem`/`ShopEconomics` DTOs; `CustomerReportService` (customer info, ledger passthrough, payment/refund history, repair history, financial summary, shop-economics block, date-range support); deterministic `as_dict()` structures ready for F5/PDF.

NOT implemented: customer report UI, tabs, buttons, dashboard changes, PDF, printing, chart of accounts, general ledger, journal entries, double-entry, trial balance, financial statements, cash/bank accounting, expense accounting, inventory accounting, COGS, period closing, ADJUSTMENT semantics, `payment_transaction` rename, second event table, ledger persistence, startup backfill, refactors. `FINANCIAL_ROADMAP.md` untouched; the pre-existing working-tree modifications (`FINANCIAL_F1_DATA_DOMAIN_AUDIT.md`, app-driven `repair_manager.db` state) left as found.

## Risks / Deferred Items

1. **Per-repair shop economics in repair history** — DEFERRED: only the aggregate `shop_economics` block is provided; attaching profit per repair row is possible but was kept out to minimize contamination risk in the F5 UI.
2. **Repair-history date filtering** — DEFERRED by design: repair history uses operational dates with different semantics than the financial range; if F5 wants a repair-history window, it must be a separate, explicitly-labeled filter (decision belongs to F5 design).
3. **Shop-economics date windowing** — DEFERRED: ProfitService has no window semantics; the block is all-time. Wiring `delivery_date` windows would duplicate dashboard logic and was not invented here.
4. `repair_count` in the summary counts only customer_id-attributable repairs; legacy repairs (no customer_id) remain unattributed by design (F1.5 policy) and are counted in `excluded_legacy_repairs`.
5. Known pre-existing stale test (`services/test_customer_service.py`) — unrelated, documented since F1.5.

## DECISION REQUIRED

None new. **ADJUSTMENT direction/sign** remains the single carried decision (F1.5 §19 / audit RCP 3); when decided, the ledger mapping and the report propagate automatically — no F4 code change is needed to honor it (unknown/ADJUSTMENT events stay unsupported and visible).

## ROADMAP CHANGE PROPOSAL

**None.** F4 implements roadmap §24 phase F4 ("تولید View Model/DTO برای Customer Header, Repair History, Ledger, Payments, Financial Summary") exactly, reusing the services the roadmap §22 mandates (ledger/profit/reconciliation not duplicated). The roadmap file is untouched.
