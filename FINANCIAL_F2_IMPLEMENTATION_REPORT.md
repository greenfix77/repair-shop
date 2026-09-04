# FINANCIAL F2 — Implementation Report

**Project:** Laptop Repair Manager
**Phase:** F2 — Financial Event Foundation
**Baseline documents:** `FINANCIAL_ROADMAP.md` v1.0 · `FINANCIAL_F1_DATA_DOMAIN_AUDIT.md` · `FINANCIAL_F1_5_IMPLEMENTATION_REPORT.md`
**Date:** 2026-09-03
**Status:** **COMPLETE** (ADJUSTMENT direction remains DECISION REQUIRED — carried from F1.5; F2 creates no ADJUSTMENT events and implements the rest of the foundation without it)

---

## 1. F2 Objective

Implement the Financial Event Foundation on top of the existing `payment_transaction` kernel (F1.5 Option A-lite):

- materialize `REPAIR_CHARGE` and `DISCOUNT` as real, dated, traceable, idempotent financial events at repair save;
- keep `PAYMENT`/`REFUND` fully backward compatible;
- provide the signed customer-balance foundation from events (no UI, no zero-floor);
- protect historical financial integrity (immutability, deletion guard, no silent migration).

F2 is NOT double-entry accounting, a customer ledger UI, or a report phase.

## 2. References Inspected

- `FINANCIAL_ROADMAP.md` (§3–§12 debit/credit rules, §24 phases, §25 non-goals)
- `FINANCIAL_F1_DATA_DOMAIN_AUDIT.md` (incl. Independent Senior Accounting Architecture Review §6–§12, NEW-1, RCP 3/4)
- `FINANCIAL_F1_5_IMPLEMENTATION_REPORT.md` (all decisions; especially §6 SSOT, §8 discount semantics, §9 charge date policy, §10 net_paid, §11 Option A-lite, §12 post-charge edit policy)

## 3. Baseline Architecture (verified before any change)

```
Operational Domain (Customer, Repair, Part, Service)   ← unchanged
        ↓
Financial Events  ← F2 builds HERE, inside payment_transaction
        ↓
Customer Subsidiary Ledger (F3)                        ← only balance foundation laid
        ↓
Accounting Layer (Stage 5+)                            ← NOT touched
```

`Financial Event ≠ Journal Entry` — no account columns, no postings, no journal concepts were added.

## 4. Actual Code Paths Inspected (STEP 2–5)

| Path | Finding |
|---|---|
| `app.add_repair` / `app.edit_repair` (app.py:310/326) | only repair-creation/update surfaces; end with `save_data()` → materialization hooks placed here |
| `app.delete_repair` / `app.delete_selected_repairs` (app.py:356/377) | uncontrolled deletion (F1.5 NEW-1 orphan risk) → guard placed here |
| `app.save_data` callers | add / edit / delete / batch-delete / closeEvent only — no other repair writers exist (`controllers/main_controller.py` is table rendering/search only) |
| `PaymentTransactionRepository` | append-only (create/read), one all-types consumer (`invoice_widget._load_payment_history`) |
| `PaymentReconciliationRepository.ledger_totals_for_repair` | COUNT included ALL row types → would have flipped `NO_LEDGER` to `MATCH` once charges exist → scoped (see §10) |
| `invoice_calculator.calculate_invoice_totals` | F1.5 SSOT confirmed intact (charges in, discount-before-tax, int truncation, clamp) |
| ADJUSTMENT producer/consumer sweep | still **no producer/UI anywhere**; real DB has 0 ADJUSTMENT rows; only latent consumer = reconciliation verdict formula |
| `PersianDateEdit` default | receive_date defaults to **today** for new repairs → F1.5 charge-date policy yields the save date for new repairs, no shortcut needed |

## 5. Existing payment_transaction Architecture

Schema (before F2): `transaction_id` PK · `repair_id` · `amount` (int) · `payment_method` · `payment_date` · `transaction_type` (PAYMENT/REFUND) · `created_at` · `note` + 2 indexes. Append-only repository. Consumers: widget payment history, `_sync_paid_from_ledger` (via `net_paid_for_repair`), reconciliation verdicts, dashboard income (type-filtered), F1.5 legacy back-fill migration.

## 6. Financial Event Model Decision

**Extend `payment_transaction` in place (Option A-lite, per F1.5 §11).** No second table, no rename. Two nullable columns + one partial unique index added; everything else reused. The `payment_date` column is the **event date** for all event types (it already served that role for payments); `transaction_type` carries the event vocabulary `REPAIR_CHARGE / PAYMENT / DISCOUNT / REFUND / ADJUSTMENT`.

**Sign convention (documented):**

| Type | Amount sign | Ledger direction |
|---|---|---|
| REPAIR_CHARGE | positive = charge; negative = correction delta reducing the charge | Debit |
| PAYMENT | positive | Credit |
| DISCOUNT | positive = discount credit; negative = reversal of prior discount | Credit |
| REFUND | positive | Debit |
| ADJUSTMENT | **undefined — DECISION REQUIRED**; no producer, no rows | — |

## 7. Schema Changes (migration impact explained before implementation — STEP 7)

`init_db._migrate_payment_transaction_columns()` (idempotent, wired into `init_database()`):

1. `ALTER TABLE payment_transaction ADD COLUMN customer_id INTEGER` — event attribution; NULL for all legacy/manual rows.
2. `ALTER TABLE payment_transaction ADD COLUMN event_key TEXT` — deterministic identity of system-generated events.
3. `CREATE UNIQUE INDEX IF NOT EXISTS ux_payment_transaction_event_key ON payment_transaction(event_key) WHERE event_key IS NOT NULL` — partial unique index: the hard backstop against duplicate system events while leaving legacy/manual rows (NULL key) completely untouched.

**Impact:** additive only; no row is rewritten; no existing column changes; existing queries unaffected (verified: 8 PAYMENT + 1 REFUND rows byte-identical after migration on a production copy; all original columns NULL-safe). No destructive migration of any kind. No data backfill at startup.

## 8. REPAIR_CHARGE Implementation

`FinancialEventService.materialize_for_repair(repair, is_new)` (called from `app.add_repair` with `is_new=True` and `app.edit_repair` with `is_new=False`, **after** `save_data()` succeeds; failures are reported and never roll back the save — the next save self-heals):

- **Amount** — decomposed from the F1.5 SSOT breakdown only (`calculate_invoice_totals`), no independent math:

  ```
  REPAIR_CHARGE (debit) = fin.subtotal + fin.tax_amount      (pre-discount payable)
  DISCOUNT (credit)     = min(fin.discount, fin.subtotal)    (effective discount)
  invariant: REPAIR_CHARGE − DISCOUNT == fin.total (Customer Payable) — holds for ALL inputs incl. the clamp
  ```

  Rationale: roadmap §9 books the charge as the pre-discount debit and the discount as a separate credit; the prompt's balance formula (`REPAIR_CHARGE − PAYMENT − DISCOUNT + REFUND + ADJUSTMENT`) then always equals the current payable minus payments/refunds. This decomposition also prevents double-counting: a discount-only change emits ONLY a discount event (caught by test T7 during development).
- **Date (F1.5 §9 policy, unchanged):** `delivery_date` when present, else `receive_date`; **never silently today**; both empty → empty date + explicit reconstructed marker (no date invented).
- **customer_id:** stamped from `Repair.customer_id` (authoritative). No heuristics.
- **Immutability:** once a charge event exists it is never updated or deleted. A later payable change appends a signed REPAIR_CHARGE **delta** event (`…:delta:N`, dated today, note `اصلاحیه بدهی تعمیر #id: old → new`) — the sanctioned "delta event" mechanism; `Σ REPAIR_CHARGE events` always equals the cumulative pre-discount charge.
- `is_new=False` first materialization of a pre-F2 repair → reconstructed marker in the note (F1.5 policy).
- A repair whose charge target is 0 produces no charge event (nothing to book); a later charged edit then produces the initial event.

## 9. DISCOUNT Implementation

Discount lifecycle (the prompt's mandatory cases A–F), driven by the same compare-and-delta mechanism:

| Case | Repair action | Event result |
|---|---|---|
| A | saved with discount = 0 | no DISCOUNT event |
| B | first save with discount = 100 | one `DISCOUNT:repair:N:initial` event, amount 100 |
| C | saved again, discount unchanged | **nothing** (idempotent) |
| D | discount 100 → 150 | one delta `+50` (original rows untouched) |
| E | discount 150 → 50 | one signed delta `−100` (reversal) |
| F | discount removed 50 → 0 | one signed delta `−50`; `Σ DISCOUNT = 0` |

- Discount event dates: new discounts in the F2 era are stamped `today_persian()` at the materializing save (F1.5 §8); a pre-F2 (reconstructed) discount gets the F1.5 policy date (`delivery_date`/`receive_date`) + explicit reconstructed marker; deltas are stamped `today_persian()` (they happen now).
- Effective discount = `min(discount, prediscount)` — with the SSOT clamp, the recorded credit never exceeds the base, keeping `Σcharge − Σdiscount == payable` exact even when a discount exceeds the repair total (test T19).
- Discounts remain non-negative as a repair-header value; negative AMOUNTS appear only as signed correction deltas of the DISCOUNT event stream.

## 10. PAYMENT / REFUND Compatibility

- `payment_transaction` rows for PAYMENT/REFUND are untouched: same write path (`InvoiceWidget._create_ledger_transaction`), same repository, same schema semantics. `net_paid_for_repair` = `ΣPAYMENT − ΣREFUND` (zero-floored) is unchanged; `net_paid_amount_for_repair` still excludes ADJUSTMENT; reconciliation verdicts keep `PAYMENT + ADJUSTMENT − REFUND` (divergence pinned, DECISION REQUIRED unchanged).
- **One surgical consumer fix:** `ledger_totals_for_repair` now scopes its query to `PAYMENT/REFUND/ADJUSTMENT` so that new event types cannot flip a charge-only repair from `NO_LEDGER` to `MATCH` (the F1.5 report §11 explicitly required rechecking this query). Verdict semantics are bit-identical to pre-F2 for payment data (tests C1/C2 + the F1.5 D-suite).
- **UI preservation:** the Financial tab's payment history now reads the new `list_payment_history_for_repair` (PAYMENT/REFUND only) instead of `list_for_repair` — the table keeps showing exactly what it showed before F2 (test C7). The full event stream remains available via the repository/service for F3.
- `list_for_repair` (all types) is now used by the FinancialEventService; dashboard income remains type-filtered and unaffected.

## 11. customer_id Handling

- Every system event stamps `customer_id` from `Repair.customer_id` (F1.5 authoritative path: Dialog → Repair → RepairDB → SQLiteStorage → DB). No name/phone heuristics for new events.
- Legacy payment rows keep `customer_id = NULL`; for **read-only** balance attribution they resolve through their repair's stored `customer_id` (the F1.5 authoritative reference — not a heuristic). Events that cannot be attributed (repair deleted or customer unresolved) are counted as `unattributed_events` and never silently dropped.
- F1.5's repair backfill mapping verified intact on the production copy (`{1:2, 2:3, 3:4, 4:4, 5:3}` — test F2.5).

## 12. Event Dates

| Event | Date |
|---|---|
| REPAIR_CHARGE initial | `delivery_date` (delivered) else `receive_date`; both empty → `''` + reconstructed marker |
| REPAIR_CHARGE delta | `today_persian()` (materialization date) |
| DISCOUNT initial (F2-era discount) | `today_persian()` (save-time stamp, F1.5 §8) |
| DISCOUNT initial (reconstructed legacy) | `delivery_date`/`receive_date` policy + reconstructed marker |
| DISCOUNT delta | `today_persian()` |
| PAYMENT / REFUND | unchanged (user-entered `payment_date`) |

No invented dates anywhere; undated events are explicit and flagged.

## 13. Idempotency Strategy

Deterministic event identity + sum-based comparison + DB backstop:

1. **Deterministic keys:** `REPAIR_CHARGE:repair:{id}:initial|delta:{n}`, `DISCOUNT:repair:{id}:initial|delta:{n}` (n = 1-based sequence of existing deltas — deterministic per DB state).
2. **Compare-and-skip:** materialization computes the SSOT targets and compares against `Σ` existing events; equal → zero events. Repeated saves, app restarts (`init_database()` re-runs), UI refreshes and unrelated-field edits therefore produce nothing (tests T6/T7/T8).
3. **Uniqueness backstop:** partial unique index on `event_key`; a racing duplicate insert raises `IntegrityError` and is treated as "already exists" (test T21d).
4. **No startup backfill:** starting the app never creates events; materialization happens only on repair save (test F2.3 — twice-run startup leaves 0 system events on the production copy).

## 14. Duplicate-Prevention Strategy

Same mechanism as §13 — the state invariant `Σ REPAIR_CHARGE == cumulative charge` and `Σ DISCOUNT == cumulative discount` makes duplication mathematically detectable, the compare-and-skip makes it unreachable in normal flow, and the unique index makes it impossible at the storage layer.

## 15. Historical Immutability Strategy

- The service only **appends**; there is no update/delete path for events (repository stays append-only).
- Original `initial` events are byte-stable for the lifetime of the repair; every correction is a new delta row referencing old→new values in its note (tests T11, T16/17).
- Deletion of repairs carrying events is blocked (§17), so events cannot be orphaned by user action.
- No startup migration rewrites event or payment data.

## 16. Repair-Edit Behavior

- Payable unchanged (e.g. notes/warranty edits) → no events.
- Payable changed (parts/labor/charges/tax) → signed REPAIR_CHARGE delta; original charge immutable.
- Discount changed → DISCOUNT delta only (never a charge delta too — the decomposition prevents double-counting).
- customer_id changes → stamped on future events; historical events keep their original attribution (no rewrite).
- The old "widget clamp of ledger-paid" (audit NEW-4) and overpayment ladder (RCP 2) remain untouched.

## 17. Repair-Deletion Behavior

Smallest safe guard, implemented in `app.delete_repair` and `app.delete_selected_repairs` using the testable service logic (`has_events_for_repair`, `filter_deletable_repairs`):

- Repair with ANY financial event (PAYMENT/REFUND/REPAIR_CHARGE/DISCOUNT/ADJUSTMENT) → deletion **blocked** with a Persian message explaining that financial events must be corrected/voided first (controlled workflow = F3+).
- Batch deletion → event-ful repairs are kept, the rest are deleted, and the result message reports both counts.
- Event-less repairs remain deletable exactly as before; no cascade deletion of financial history exists anywhere (tests D1–D5). This closes F1.5 NEW-1's active orphan path.

## 18. Legacy-Data Behavior

- **No automatic event reconstruction.** Startup only migrates schema; `Σ REPAIR_CHARGE/DISCOUNT == 0` on the production copy after two startups (test F2.3).
- First post-F2 **save** of a legacy repair materializes its charge (and discount, if any) as reconstructed events: policy date + explicit `رویداد بازسازی‌شده` marker (tests L2, T9).
- Pre-F2 `payment_transaction` rows migrate non-destructively (new columns NULL, values byte-identical — tests L1, F2.2).
- Legacy payments without customer_id are balance-attributed via their repair's F1.5-authoritative `customer_id`; unattributable rows are counted, never guessed (tests L4, T21c).
- Production-DB note: between the F1.5 and F2 sessions the application was started and the **F1.5 migration ran against the real DB** (repairs.customer_id added + backfilled with exactly the tested mapping `{1:2, 2:3, 3:4, 4:4, 5:3}`); this is the designed deployment path. The F2 migration has not yet run there and will apply the same tested additive change on next app start.

## 19. Customer-Balance Behavior (foundation implemented, no UI)

`FinancialEventService.customer_balance(customer_id)` — derived **only** from financial events:

```
balance = ΣREPAIR_CHARGE − ΣPAYMENT − ΣDISCOUNT + ΣREFUND (+ ΣADJUSTMENT, signed)
```

- **Signed, no zero-floor**: overpayment yields a negative balance (customer credit / بستانکار) — test T21b.
- Returns `total_debit`, `total_credit`, `balance`, `event_count`, `unattributed_events`.
- ADJUSTMENT is included with its signed amount per the F2 target formula but is inert (no rows, no producer; direction = DECISION REQUIRED).
- Repair totals and ProfitService are not consulted; shop profit stays fully separate.
- No ledger UI, statement, or running-balance report — that is F3/F4.

## 20. Files Changed

| File | Change |
|---|---|
| `app.py` | lazy `FinancialEventService`; `_materialize_financial_events` hook after add/edit save; deletion guards in `delete_repair` + `delete_selected_repairs` |
| `core/storage/payment_transaction_model_db.py` | `customer_id`, `event_key` columns (nullable) |
| `core/storage/init_db.py` | `_migrate_payment_transaction_columns()` (columns + partial unique index) wired into `init_database()` |
| `core/storage/payment_transaction_repository.py` | create/_to_dict carry new fields; new `list_payment_history_for_repair` (PAYMENT/REFUND only) |
| `core/storage/payment_reconciliation_repository.py` | `ledger_totals_for_repair` scoped to reconciliation types (verdict semantics preserved) |
| `ui/widgets/invoice_widget.py` | `_load_payment_history` uses the filtered read (UI behavior unchanged) |

## 21. Files Created

| File | Purpose |
|---|---|
| `services/financial_event_service.py` | Financial Event service: materialization, idempotency, date policy, deletion-guard logic, signed customer balance |
| `services/test_financial_f2.py` | F2 validation suite (5 phases, 42 checks) |
| `FINANCIAL_F2_IMPLEMENTATION_REPORT.md` | this report |

## 22. Migrations

One idempotent, additive migration (`_migrate_payment_transaction_columns`): two nullable columns + one partial unique index. Verified on a production-DB copy: existing rows/values untouched, new columns NULL, index created, double-startup safe. No data migration, no event backfill.

## 23. Tests Performed

`python services/test_financial_f2.py` (isolated subprocess phases; real DB never written):

- **events (21)** — T1 new repair w/ customer_id; T2 charge == SSOT payable; T3 event metadata (id/type/customer/repair/amount/date/key); T4 delivery-date policy; T5 discount materialization + no charge delta; T6 repeated saves; T7 restart; T8 unrelated edits; T11 discount +Δ; T12 discount −Δ; T13 discount removed; T16/17 edit immutability + delta; T13/14 PAYMENT/REFUND net semantics; T21 balance (signed); T21b credit balance (no floor); T21c legacy attribution; T21d unique-index rejection; T9/T9b reconstructed markers (dated/undated); T18/T19 `charge − discount == payable` invariant incl. clamp.
- **compat (7)** — NO_LEDGER semantics with charge-only repairs; reconciliation verdicts; FinancialSummaryService; ProfitService; payment-history filter; table/report totals; InvoiceWidget history+status with events present.
- **deletion (5)** — charged/payment-history/clean repairs; batch split; guarded deletion leaves history intact.
- **legacy (4)** — pre-F2 DB migration; first-touch reconstructed materialization; second-save no-op; legacy payment attribution.
- **realdb (5)** — production copy: columns+index; 9 payment rows untouched; no auto-backfill on double startup; first save materializes once then no-op; F1.5 backfill mapping intact.
- **Regression:** full F1.5 suite re-run (40/40 PASS); existing `test_verify_refactor.py`, `test_customer_repository.py`, `test_sqlite_storage.py` (all exit 0, isolated CWDs); `compileall` over core/services/ui/controllers/app.py — OK; per-step `py_compile` — OK.
- Real-DB write-safety experiment: full F2+F1.5 suites + compileall re-run leaves the production file byte-for-byte untouched (UTC mtime identical before/after).

## 24. Test Results

**F2 targeted validation: 42/42 PASS** (events 21, compat 7, deletion 5, legacy 4, realdb 5). **F1.5 regression: 40/40 PASS.** Existing suites: 3/3 PASS. Compilation: OK. No test claimed without execution.

## 25. Regression Results

- Payable SSOT, table column, invoice PDF: unchanged (F1.5 suite + C6).
- `net_paid_for_repair`, reconciliation verdicts, dashboard income inputs: unchanged (C1/C2, F1.5 D-suite).
- ProfitService: zero modifications; profit math verified (C4).
- Payment registration/refund/history UI: unchanged (C5/C7).
- customer_id path: unchanged and re-verified end-to-end (F1.5 A-suite + F2.5).
- Known pre-existing failure (unchanged): stale `services/test_customer_service.py` references a removed API (`get_or_create_customer`) — documented in F1.5, out of scope.

## 26. Unresolved Issues

1. **ADJUSTMENT direction** — DECISION REQUIRED (below). No producer exists; the divergence between the reconciliation verdict and `net_paid_for_repair` is pinned by the F1.5 D4 test.
2. **Void/rollback workflow for charged repairs** — deletion of a charged repair is blocked until F3 provides a controlled void/reversal flow (intended F2 behavior).
3. Charge/discount events do not yet appear in any UI (by design; F3/F5 will surface them).
4. `paid_amount` snapshot clamp (audit NEW-4) and zero-floored dashboard income (NEW-2) remain as documented F3 items.

## 27. DECISION REQUIRED

**ADJUSTMENT direction/sign** (carried from F1.5 §19 / audit RCP 3). The only directional evidence in the code (`payment_reconciliation_service._build_result`: `net = PAYMENT + ADJUSTMENT − REFUND`) treats a positive ADJUSTMENT as payment-like (debt-reducing), while the F2 target formula treats positive ADJUSTMENT as debt-increasing. With zero ADJUSTMENT rows and no producer, F2 cannot safely pick a side: **no ADJUSTMENT events are created, and the balance function's ADJUSTMENT term is currently inert.** Decision needed before any ADJUSTMENT producer ships: signed amount (positive = debt increase, per the F2 target formula) or ADJUSTMENT_IN/ADJUSTMENT_OUT, plus declaring ONE net formula authoritative.

## 28. ROADMAP CHANGE PROPOSAL

**None.** All F2 work implements the roadmap as written (§6/§9 ledger semantics, §11 audit-friendly corrections, §12 event types, §24 F2 phase). The audit's existing RCP 3 (ADJUSTMENT) and RCP 4 (event dates) were adopted rather than re-proposed. One documentation-level note for the future roadmap custodian: roadmap §6's single-row example (charge shown net of discount) and §9's separate-credit example are both satisfiable by the F2 event decomposition (charge = pre-discount debit, discount = separate credit; a ledger renderer may show either view) — no roadmap text change required.

## 29. Explicit Scope Verification

Implemented: financial-event kernel extension (2 columns + index), REPAIR_CHARGE/DISCOUNT materialization at save, deterministic idempotency, delta corrections, signed customer-balance foundation, deletion guard, PAYMENT/REFUND compatibility fixes (reconciliation COUNT scope, history filter), additive migration, tests, report.

NOT implemented (per F2 scope): double-entry / journal entries / chart of accounts / trial balance / statements / period closing / bank reconciliation / expense or inventory or COGS accounting / accounting UI / customer report UI / PDF / dashboard changes / payment_transaction rename / second event table / roadmap edits / commits / Git configuration changes. `FINANCIAL_ROADMAP.md` untouched; line endings untouched; the pre-existing `FINANCIAL_F1_DATA_DOMAIN_AUDIT.md` working-tree modification left as found; no commits, branches, stashes or resets.

---

*F2 boundary: the financial-event foundation only. Operational → Financial Event is now real and traceable; Financial Event → Customer Subsidiary Ledger is F3; Ledger → Accounting Entries is Stage 5+.*
