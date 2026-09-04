# FINANCIAL F1.5 — Implementation Report

**Project:** Laptop Repair Manager
**Phase:** F1.5 — Financial Foundation Alignment (prerequisite for F2)
**Baseline documents:** `FINANCIAL_ROADMAP.md` v1.0 · `FINANCIAL_F1_DATA_DOMAIN_AUDIT.md` (incl. "Independent Senior Accounting Architecture Review")
**Date:** 2026-09-03
**Status:** **COMPLETE** (one item carried as DECISION REQUIRED; it does not block F1.5 because no ADJUSTMENT producer exists and no code was changed for it)

---

## 1. F1.5 Objective

Stabilize and verify the financial foundation before F2 (Customer Ledger Model):

1. Persist `customer_id` on Repair end-to-end.
2. Define ONE authoritative Customer Payable formula and enforce it as the single source of truth (SSOT).
3. Define discount semantics, Repair-Charge date policy, `net_paid_for_repair` semantics.
4. Decide the PaymentTransaction / Financial-Event architecture for F2.
5. Preserve all historical-integrity invariants; no F2 implementation; no unrelated changes.

## 2. Baseline Architecture (unchanged by F1.5)

```
Operational Domain (Customer, Repair, Part, Service)
        ↓
Financial Events (payment_transaction today: PAYMENT/REFUND; F2 adds REPAIR_CHARGE/DISCOUNT)
        ↓
Customer Subsidiary Ledger (F2/F3 — NOT built in F1.5)
        ↓
Accounting Layer (Stage 5+ — NOT built)
```

Layering respected in F1.5: `Repository → Service → UI`; `Repair` remains an operational document; `ProfitService` remains shop-economics-only; `Financial Event ≠ Journal Entry`; `Customer Ledger ≠ Shop Profit`.

## 3. Problems Found (verified in code)

| # | Problem | Severity | Resolution |
|---|---|---|---|
| 1 | `customer_id` produced by RepairDialog (`ui/dialogs/repair_dialog.py:393`) but dropped by `Repair.from_dict/to_dict`, absent from `RepairDB` and `SQLiteStorage` | CRITICAL | FIXED end-to-end (§4) |
| 2 | Three competing "totals": `invoice_calculator` (tax-then-discount, no charges), `InvoiceWidget` inline ×3 (discount-then-tax, with charges), `ProfitService` gross | CRITICAL | FIXED — SSOT established (§6) |
| 3 | `calculations.calculate_invoice` duplicate formula | LOW | Delegated to SSOT (§6) |
| 4 | `table_service` payable excluded additional charges | HIGH | Fixed — passes charges to SSOT (§6) |
| 5 | ADJUSTMENT direction undefined; `net_paid_for_repair` (PAYMENT−REFUND) vs reconciliation verdict (PAYMENT+ADJUSTMENT−REFUND) | P2 (latent — no producer) | Documented; **DECISION REQUIRED** (§10) |
| 6 | Legacy repairs have no `customer_id` | CRITICAL for ledger attribution | Conservative backfill migration (§5) |
| 7 | Zero-floor on net paid / income (`max(net,0)`) hides customer-credit states | P2 | Left as-is (F3 decision; audit NEW-2) — documented, unchanged |
| 8 | Widget clamps ledger-derived paid down to `final` | P2 | Left as-is (audit NEW-4); no UI redesign in F1.5 |

## 4. customer_id Persistence Path (end-to-end)

Full data flow after F1.5:

```
RepairDialog.get_data()          — already emitted customer_id (unchanged)
  → app.add_repair / app.edit_repair (unchanged)
    → repair_manager_service.add_repair / update_repair
        → Repair.from_dict   — now ACCEPTS customer_id (int / numeric str; missing/empty/0/invalid → None)
        → Repair.to_dict     — now EMITS customer_id
    → update_repair merge guard — an edit that carries no customer_id can never drop a stored one
      → SQLiteStorage.save_all  — writes repairs.customer_id (None-safe)
      → SQLiteStorage.load_all  — reads repairs.customer_id (legacy rows → None)
        → SQLite: new nullable column `repairs.customer_id INTEGER` (no FK, no unique — operational reference)
```

- **Model** (`core/models.py`): `customer_id: Optional[int] = None` added to the `Repair` dataclass; included in `to_dict`/`from_dict` with safe coercion. Every relevant `Repair` construction path was checked — `Repair.from_dict` is used only by `repair_manager_service.add_repair/update_repair`; `migrate_json_to_sqlite` and `SQLiteStorage` handle raw dicts and now pass `customer_id` through transparently.
- **Dialog edit path** (unchanged, verified): `RepairDialog.load_data` re-selects the customer (by `customer_id`, else phone, else unique exact name) and `get_data` re-emits the id — so editing a legacy repair re-attaches the id; the service-layer guard covers any caller that doesn't.
- **Authoritative reference rule:** for NEW records `customer_id` is the sole customer reference. The dialog's phone/name lookup in `load_data` is used only to *restore* the selection for legacy records that have no stored id yet; once stored, `customer_id` wins. No new name/phone heuristics were introduced into the persistence path.

**Database column migration** (`core/storage/init_db.py`): `customer_id INTEGER` added to `_migrate_repair_columns` (idempotent `ALTER TABLE ... ADD COLUMN`), consistent with the existing column-migration mechanism. No destructive migration; existing databases gain the column on next startup.

## 5. Legacy Migration Policy (customer_id)

Implemented in `init_db._backfill_repair_customer_ids()` (runs inside `init_database()`, idempotent):

- **R1 (phone):** repair `phone` non-empty AND exactly one customer has that phone (stripped comparison) → assign that customer id. (Note: `customer.phone` is UNIQUE at the DB level, so a phone match is unique by construction.)
- **R2 (name):** otherwise repair `customer_name` non-empty AND exactly one customer has that exact `full_name` → assign.
- **Ambiguous / no match → `customer_id` stays NULL** and remains identifiable (`customer_id IS NULL`). Historical rows are never overwritten, never guessed, and `customer_name`/`phone` snapshots are never modified. Rows that already carry a `customer_id` are skipped.
- Re-runs only touch rows with `customer_id IS NULL` — safe on every startup.

**Real database result (verified on a copy, phase F):** 5/5 repairs resolved unambiguously (4 by unique phone, 1 by unique name). The production DB itself is untouched by this task; the migration runs automatically (and identically) on next app start — same deployment mechanism as previous column migrations.

**Sufficiency of the policy:** sufficient for automatic migration. Repairs that match no customer, or match several (e.g. duplicate names with different phones), remain unlinked and identifiable — per the task's rule that weak heuristics must not attach repairs to the wrong customer.

## 6. Authoritative Customer Payable Formula (SSOT)

Owner: **`services/invoice_calculator.calculate_invoice_totals`** (+ convenience `payable_total`).

```
prediscount    = parts_cost + labor_cost + additional_charges
after_discount = max(0, prediscount − discount)
tax_amount     = int(after_discount × tax_rate / 100)
Customer Payable (total) = after_discount + tax_amount
```

- **Semantics pinned from the InvoiceWidget** (the amount the shop actually quotes on the Financial tab), exactly as recommended by the audit's Independent Senior Accounting Architecture Review (§7 and §12): additional charges ARE part of the payable; discount (flat amount) is applied BEFORE tax; tax amount truncates to int; discount larger than the base clamps to 0 (no negative payable). All monetary values are integer currency units; only the tax rate is a float percentage.
- **Enforced everywhere:**
  - `InvoiceWidget._recalculate / _update_payment / get_data` — the three inline copies were removed; all call the SSOT via `_authoritative_totals()` (UI owns display only).
  - `table_service.build_table_rows` — now passes `additional_charges` through `calculations.calculate_invoice` (delegation shim) so the repairs-table «هزینه کل» column uses the SSOT.
  - `invoice_generator` (print + web invoice HTML/PDF) — already called `calculate_invoice_totals`; keys preserved (`subtotal` is now the prediscount base, `total` the payable), so PDF totals converge automatically.
  - `calculations.calculate_invoice` — duplicate formula body deleted; delegates to the SSOT (signature kept).
- **User-visible convergence (signed off by the audit, §12.2):** for repairs with additional charges and/or both discount+tax, the repairs-table column and the invoice PDF now show the same payable the Financial tab always showed. Example: parts 200,000 + labor 100,000 + charges 50,000 − discount 30,000, tax 9% → table/PDF previously showed 288,700; they now show **348,800**, matching the widget.
- **ProfitService was NOT modified.** `gross_revenue = parts + services + charges` remains the shop-economics (gross revenue) definition; it is deliberately NOT the Customer Payable (no tax, no discount). Customer sale price (`unit_price`) and shop purchase cost (`purchase_price_snapshot`) are never substituted.

## 7. Tax Semantics

- Tax rate is a **percentage** stored on the repair (float, e.g. 9.0).
- Tax base = **post-discount** subtotal (prediscount − discount) — pinned to the widget's behavior per the audit review (§7: "pin discount-before-tax and the existing int truncation so the currently displayed مبلغ نهایی is preserved").
- `tax_amount = int(after_discount × rate / 100)` — integer currency, truncation toward zero, identical to the widget's historical math.
- The invoice PDF's arithmetic (جمع − تخفیف + مالیات = مبلغ قابل پرداخت) stays coherent under the new formula.

## 8. Discount Semantics (for F2 — implemented only as documented policy)

- **DISCOUNT = CREDIT** on the customer account (roadmap §9) — confirmed, not modified.
- **Level/amount:** repair-header, flat integer amount (currency units), never negative (widget input is a non-negative QSpinBox; SSOT clamps the post-discount base at 0).
- **When applied:** when the Repair is **saved** with `discount > 0` — the save is the atomic commit point at which the payable is reduced. There is no separate "apply discount" action in the code.
- **Changeable later:** yes, via the Financial tab + save. Under F2, once a DISCOUNT event exists, changing the discount must follow the Post-Charge Edit policy (§12) — a correction event, never a silent rewrite.
- **Date:** no discount date exists anywhere in the model today. F1.5 decision:
  - **New discounts (F2 onward):** the DISCOUNT event date is stamped when the event is materialized at repair save (the save that carries the discount) — no separate field is needed for that case.
  - **Historical discounts (pre-F2):** the true application date is **not recoverable**. Adopted (from the audit review §8, not invented): backfill the event date from `delivery_date` when the repair is delivered, else `receive_date`, and flag the row as *reconstructed*. No date is ever invented; repairs with neither date are left undated/flagged for F2 handling.
- **`discount_date` field:** NOT required. F2's "materialize at save" captures the application date at the moment of application; ambiguous historical cases are covered by the reconstruction policy. Adding the column now would be dead schema (documented for F2: if F2 later needs to distinguish "discount edited" from "discount untouched" on the same save, it compares the previous repair value and emits a correction event).

## 9. Repair Charge Date Policy (for F2)

Adopted from the audit review (§8: "recommend delivery_date when delivered, else receive_date — never 'today'", RCP 4):

- **REPAIR_CHARGE event date = `delivery_date` when the repair is delivered, else `receive_date`.**
- Rationale from the domain: `receive_date` = intake (operational), `delivery_date` = completion and the existing revenue window used by ProfitService; there is no invoice-date concept in the codebase.
- For repairs saved in F2+, the charge is materialized at save using this policy date (typically `receive_date` = save day for new repairs).
- Edge case (both dates empty — possible on legacy rows): no reliable date exists; such events must be flagged reconstructed and dated by explicit F2 policy. **Not invented here** — listed as an F2 edge case.
- Not implemented in F1.5 (no event materialization).

## 10. net_paid_for_repair Semantics

- **Authoritative:** `PaymentReconciliationService.net_paid_for_repair` → `PaymentReconciliationRepository.net_paid_amount_for_repair` =
  **`ΣPAYMENT − ΣREFUND`, zero-floored** — this is the number `FinancialSummaryService` and the InvoiceWidget ledger-sync consume; it is unchanged.
- **The divergence:** `PaymentReconciliationService._build_result` (reconciliation verdict) uses `PAYMENT + ADJUSTMENT − REFUND`, while `net_paid_amount_for_repair` excludes ADJUSTMENT. Latent today (ADJUSTMENT has **no producer/UI anywhere**), but the moment an ADJUSTMENT row is written the two disagree — pinned by test D4.
- **Role of ADJUSTMENT:** roadmap §12 lists it as a transaction type but never defines its **direction/sign**; the audit already raised ROADMAP CHANGE PROPOSAL 3 for exactly this. Because the direction cannot be determined from code or documents, F1.5 makes **no change** and reports:
  - **DECISION REQUIRED — ADJUSTMENT direction.** Options: (a) signed amount column, or (b) split types ADJUSTMENT_IN / ADJUSTMENT_OUT, with ONE net formula declared authoritative (recommend adopting RCP 3, then unify `_build_result` and `net_paid_amount_for_repair`).
  - Nothing was silently changed; existing `payment_transaction` data is untouched (verified bit-identical in phase F).
- **Zero-floor** (`max(net, 0)`) is existing behavior and was preserved; signed balances remain an F3 decision (audit NEW-2, review §13). Over-refund currently reads as 0 — documented, not changed.

## 11. PaymentTransaction / Financial Event Architecture (decision for F2)

**Decision: Option A-lite — `payment_transaction` IS the kernel of the future Financial-Event layer; it is extended in place, not renamed, and no second table is created.**

Basis (traced, not assumed):
- Schema already carries everything an event needs: `transaction_id` PK, `repair_id`, `amount` (int), `payment_method`, `payment_date`, `transaction_type` (PAYMENT/REFUND today), `note`, `created_at`, plus two indexes.
- The repository is **append-only by design** (create/read only) — exactly the immutability profile the future event store needs.
- The audit verdict: "the schema can host a ledger; the missing pieces are the producers (charge/discount/adjustment rows + dates) and the customer link, not the storage table. Do not create the table now."
- The review's explicit non-goal: "No renaming of `payment_transaction`; no second financial system alongside the existing one."

**F2 plan recorded (not implemented):** add `REPAIR_CHARGE` / `DISCOUNT` as new `transaction_type` values written at repair save; existing PAYMENT/REFUND rows and all consumers (reconciliation, dashboard income, payment-history UI) continue unchanged. Backward compatibility: new type values are ignored by current aggregates by design (`ledger_totals_for_repair` counts only known types for totals but counts all rows for COUNT — F2 must recheck that query when new types appear).

## 12. Post-Charge Repair Edit Policy (documented for F2, not implemented)

- Once a REPAIR_CHARGE (or DISCOUNT) event exists, **editing the Repair must NOT silently rewrite the historical financial event.**
- F2 must materialize events as immutable rows and route corrections through controlled mechanisms — **Adjustment / Reversal / Correction events** referencing the original — consistent with roadmap §11 ("silent deletion of financial events is forbidden; corrections must be traceable Adjustment events").
- Operational edits remain free (Repair stays an operational document); only the *event layer* is frozen. F1.5 changes no edit behavior today.

## 13. Historical Integrity Rules (preserved and now test-enforced)

1. Catalog price changes never rewrite repair line history (`unit_price`, `purchase_price_snapshot`, `total_price` are per-line snapshots) — test C1.
2. `unit_price` = historical customer sale price; `purchase_price_snapshot` = historical shop cost — never swapped (SSOT doc + ProfitService untouched).
3. Customer Ledger must never use ProfitService as its accounting source — untouched and documented.
4. Repair remains operational; **no accounting fields** (`debit_account`, `credit_account`, `journal_entry_id`) added — only `customer_id`, an operational reference.
5. Future Financial Events will be materialized and independently traceable (§11).
6. Historical financial events to become immutable (append-only repo already; §12).
7. Editing a Repair must not silently rewrite historical accounting (§12).

## 14. Files Changed

| File | Change |
|---|---|
| `core/models.py` | `Repair.customer_id` field; emitted in `to_dict`; parsed with safe coercion in `from_dict` |
| `core/storage/repair_model_db.py` | `customer_id` column (nullable) |
| `core/storage/sqlite_storage.py` | write/read `customer_id` in `save_all`/`load_all` |
| `core/storage/init_db.py` | `customer_id` added to `_migrate_repair_columns`; new `_backfill_repair_customer_ids()` wired into `init_database()` |
| `services/repair_manager_service.py` | `update_repair` preserves a stored `customer_id` when the edit carries none |
| `services/invoice_calculator.py` | rewritten as the single source of truth (charges included, discount-before-tax, int truncation, clamp; superset of the historical result keys) |
| `services/calculations.py` | duplicate formula removed; delegates to the SSOT |
| `services/table_service.py` | passes `additional_charges` to the SSOT |
| `ui/widgets/invoice_widget.py` | 3 inline formula copies replaced by `_authoritative_totals()` → SSOT |

## 15. Files Created

| File | Purpose |
|---|---|
| `services/test_financial_f1_5.py` | F1.5 targeted validation suite (4 isolated phases, 40 checks) |
| `FINANCIAL_F1_5_IMPLEMENTATION_REPORT.md` | this report |

## 16. Tests Executed

`python services/test_financial_f1_5.py` (all phases in isolated subprocesses; the real `repair_manager.db` is never touched — phase F works on a copy):

- **Phase core — 28/28 PASS**
  - A) customer_id: model round-trip; coercion (str/empty/0/invalid→None); `add_repair`; `update_repair` preservation guard; `SQLiteStorage` save/load; full dialog→service→storage→load chain with no data loss.
  - B) payable: services only / parts only / both / +charges / legacy amount fallback / discount-before-tax / tax truncation / discount clamp / full combo / malformed inputs / zero-charge lines / `calculations` delegation / `table_service` parity / helper.
  - C) historical snapshots: catalog price change after save leaves line snapshots, header `parts_cost` and SSOT payable untouched.
  - D) payments: single + multiple accumulate; refund reduces; MATCH/MISMATCH verdicts; ADJUSTMENT divergence pinned (paid excludes it, verdict adds it); over-refund zero-floor kept; NO_LEDGER; `FinancialSummaryService` ledger-wins semantics.
- **Phase ui — 2/2 PASS** — InvoiceWidget label / quick-fill / `get_data` / payment-status all equal the SSOT; invoice HTML shows the SSOT payable + tax.
- **Phase legacy — 5/5 PASS** — legacy-shaped DB gains the column; conservative backfill (unique phone → assign; unique name → assign; ambiguous → NULL; no match → NULL; pre-set id never overwritten); snapshots untouched; idempotent re-run; legacy rows load/save safely; unresolved stay NULL.
- **Phase realdb — 5/5 PASS** (on a COPY of `repair_manager.db`): column added; expected mapping `{1:2, 2:3, 3:4, 4:4, 5:3}`; every other repair field unchanged; all 9 payment rows byte-identical (8 PAYMENT + 1 REFUND, sums unchanged); migrated copy loads and ids survive the model.
- **Existing suite (isolated CWD):** `core/storage/test_customer_repository.py` PASS (exit 0) · `core/storage/test_sqlite_storage.py` PASS (exit 0) · `services/test_verify_refactor.py` PASS ("ALL TESTS PASSED", exit 0).
- **Compilation:** `python -m compileall core services ui controllers app.py` — OK; `py_compile` on every changed file after each step — OK.
- Real `repair_manager.db` verified untouched (size/mtime unchanged, still opens read-only, 5 repairs / 9 payments).

## 17. Test Results

- **F1.5 targeted validation: 40/40 PASS** (core 28, ui 2, legacy 5, realdb 5).
- **Existing tests:** 3 of 4 runnable suites PASS. `services/test_customer_service.py` fails with `AttributeError: 'CustomerService' object has no attribute 'get_or_create_customer'` — **pre-existing stale test** (file unmodified in git; the API was renamed to `resolve_customer` in an earlier refactor — see `services/test_verify_refactor.py`). Unrelated to F1.5; reported, not fixed (out of scope).
- No test claimed passed without execution; all results above are from actual runs.

## 18. Remaining Risks

1. **PDF/table subtotal display:** with additional charges, the invoice PDF's «جمع» now includes charges that the itemized table does not list line-by-line (the PDF never itemized charges). Arithmetically consistent with the payable; F2/F5 may add a charges row to the printed table (UI/print change — out of F1.5 scope).
2. **Zero-floor nets** (`max(net,0)`) still mask customer-credit states (audit NEW-2) — F3 decision, preserved as-is.
3. **Widget clamp** of ledger-derived paid (audit NEW-4) — unchanged; overpayment ladder (audit RCP 2 / NEW-8) untouched.
4. **Repair deletion still orphans payment rows** (audit NEW-1) — F2 deletion guard, untouched.
5. **ADJUSTMENT divergence** — pinned by test; must be resolved before any ADJUSTMENT producer ships (§10).
6. **Stale `test_customer_service.py`** references a removed API (pre-existing).
7. **Both-dates-empty legacy repairs** cannot get a reliable REPAIR_CHARGE date — F2 edge case (flag as reconstructed).

## 19. DECISION REQUIRED

1. **ADJUSTMENT direction/sign** (roadmap §12 undefined; code diverges: reconciliation verdict adds it, `net_paid_for_repair` excludes it). Required before any ADJUSTMENT producer exists. Recommendation: adopt audit RCP 3 (signed adjustment or ADJUSTMENT_IN/ADJUSTMENT_OUT) and declare ONE net formula authoritative. **No F1.5 code change was made.**

## 20. ROADMAP CHANGE PROPOSAL

**None added.** The audit's four ROADMAP CHANGE PROPOSALS (1–4) already cover everything F1.5 surfaced; none of F1.5's findings contradict the roadmap. F1.5 *implements the prerequisites* named in RCP 1 (persist customer_id; unify the payable formula) — both were explicitly recommended by the audit review (§12.2), so no new proposal is required. The ADJUSTMENT gap is covered by the existing RCP 3 (restated in §19 above rather than duplicated).

---

*F1.5 boundary respected: no Customer Ledger, no Financial-Event table, no REPAIR_CHARGE/DISCOUNT materialization, no journal entries, no chart of accounts, no new UI, no PDF reports, no schema changes beyond the `customer_id` column, no roadmap file edits, no commits, no Git configuration changes. `FINANCIAL_ROADMAP.md` untouched; the pre-existing working-tree modification to `FINANCIAL_F1_DATA_DOMAIN_AUDIT.md` was left as found; the real `repair_manager.db` was never written.*