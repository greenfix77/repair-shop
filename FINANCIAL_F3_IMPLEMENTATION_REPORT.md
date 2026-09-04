# FINANCIAL F3 — Implementation Report

**Project:** Laptop Repair Manager
**Phase:** F3 — Customer Subsidiary Ledger (domain layer)
**Baseline documents:** `FINANCIAL_ROADMAP.md` v1.0 · `FINANCIAL_F1_DATA_DOMAIN_AUDIT.md` · `FINANCIAL_F1_5_IMPLEMENTATION_REPORT.md` · `FINANCIAL_F2_IMPLEMENTATION_REPORT.md`
**Date:** 2026-09-03
**Status:** **COMPLETE** (ADJUSTMENT direction remains DECISION REQUIRED, carried from F1.5/F2; the ledger explicitly refuses to classify it)

---

## 1. F3 Objective

Build the Customer Subsidiary Ledger domain layer on top of the F2 Financial Event foundation: a deterministic, chronological, per-customer projection of Financial Events with debit/credit classification, signed running balance, totals, customer filtering and inclusive date-range filtering.

Not implemented (per scope): general-ledger accounting, journal entries, chart of accounts, any UI, any new persistence.

## 2. References Inspected

- `FINANCIAL_ROADMAP.md` — §2.1 customer account, §3/§4 debit/credit golden rule, §7 payments, §9 discount, §10 refund, §15 ledger table (DATE | شرح | مرجع | بدهکار | بستانکار | مانده + footer جمع بدهکار/جمع بستانکار/مانده), §24 F3 phase definition.
- `FINANCIAL_F1_DATA_DOMAIN_AUDIT.md` — §19 regression rules (ledger-wins, no profit in ledger), NEW-2 (zero-floor masking), RCP 3 (ADJUSTMENT).
- `FINANCIAL_F1_5_IMPLEMENTATION_REPORT.md` — §10 net_paid semantics, §19 DECISION REQUIRED.
- `FINANCIAL_F2_IMPLEMENTATION_REPORT.md` — §6 event model/sign convention, §8/§9 charge & discount events, §19 customer balance foundation.

## 3. Current F2 Architecture (verified before any change)

`payment_transaction` kernel with `customer_id` + `event_key` (partial unique index), append-only repository, `FinancialEventService` (materialization, idempotency, deletion-guard logic, `customer_balance`), event vocabulary `REPAIR_CHARGE / PAYMENT / DISCOUNT / REFUND / ADJUSTMENT` (no ADJUSTMENT producer, 0 rows in production), no startup backfill. All preserved unchanged except the one documented change in §11/§12 below.

## 4. Financial Event → Ledger Architecture

```
FinancialEventService (F2, append-only authority)
        ↓  reads events + attribution (composition, one implementation)
CustomerLedgerService (F3, read-only projection)
        ↓
CustomerLedgerEntry (derived dataclass — NOT persisted)
        ↓
running balance / totals / customer balance (signed, no floor)
```

- Dependency direction is strictly Event → Ledger. The ledger performs **no writes of any kind** (verified by test I2: event rows are byte-identical after ledger builds).
- The ledger never reads Repair totals, `ProfitService`, catalog prices, or `paid_amount` snapshots. Historical entries come only from immutable Financial Events (verified by test I4: after a repair edit raises the payable, the historical charge entry still shows the original amount until a new delta event exists).

## 5. Ledger Entry Domain Model

`CustomerLedgerEntry` dataclass (`services/customer_ledger_service.py`) — a projection, not a persisted row:

`customer_id` · `transaction_id` (the Financial Event id — authority link) · `repair_id` (nullable) · `event_type` · `event_date` (the financial event date) · `created_at` (ordering only) · `description` (event note) · `direction` (natural direction of the event type) · `debit` · `credit` · `signed_effect` · `running_balance` · `event_key` (deterministic event reference) · `reconstructed` (derived from the F2 reconstruction marker in the note) · `as_dict()` for future UI/reporting.

**Persistence decision:** ledger entries are **derived, not persisted** (see §16).

## 6. Event-to-Ledger Mapping

One central, explicit, testable table — `EVENT_LEDGER_MAP` — the only place event types are classified (no scattered type checks):

| Financial Event | Direction | signed_effect |
|---|---|---|
| REPAIR_CHARGE | DEBIT | `+amount` |
| PAYMENT | CREDIT | `−amount` |
| DISCOUNT | CREDIT | `−amount` |
| REFUND | DEBIT | `+amount` |
| ADJUSTMENT | **UNSUPPORTED** (`adjustment_direction_unresolved`) | — |
| anything else | **UNSUPPORTED** (`unknown_event_type`) | — |

- `debit = max(0, signed_effect)`, `credit = max(0, −signed_effect)` — every row books into exactly one column (roadmap §15 footer convention: جمع بدهکار / جمع بستانکار − مانده).
- F2's signed correction deltas flow through the same formula: a DISCOUNT reversal delta of −100 yields `signed_effect = +100` → books as a DEBIT row, still traceable to its DISCOUNT event (test T21b). No negative financial-event amount is used to *encode* direction; direction comes from the mapping, the sign of the stored amount expresses corrections.
- ADJUSTMENT and unknown types are never silently classified: they are excluded from entries/totals/balance and reported under `unsupported_events` with an explicit reason (tests T19, T21).

## 7. Debit/Credit Semantics

Roadmap §3/§4 golden rule, unchanged: debit increases what the customer owes; credit decreases it. REPAIR_CHARGE→Debit, PAYMENT→Credit, DISCOUNT→Credit (roadmap §9), REFUND→Debit (roadmap §10). The customer account contains no purchase prices, shop cost, profit, margin or COGS (test I6 proves `ProfitService` is never even imported by the ledger layer).

## 8. Signed Balance Convention

`signed_effect`: DEBIT → `+amount`, CREDIT → `−amount`. Running balance accumulates signed effects. **Positive balance = customer owes the shop (بدهکار); negative = customer credit (بستانکار). No zero-floor anywhere** — overpayment yields a visible negative balance (tests T10/11, L1, and F2 T21b).

## 9. Ordering Strategy

Deterministic and documented; never database row order:

1. **event date** (`payment_date`, Persian `YYYY/MM/DD` — ascending string order is chronological; empty/undated events sort **first**, treated as oldest-unknown);
2. **`created_at`** (event record timestamp, ascending);
3. **`transaction_id`** (unique final tiebreaker).

Same input events always produce the same ledger order regardless of input order (test T12/13; determinism on real data test F3.3, L2).

## 10. Running Balance Strategy

`balance = previous balance + signed_effect`, computed in order over the projected entries (`apply_running_balances`). Never read from Repair, never from ProfitService, never from stored snapshots. Date-filtered windows recompute the running balance within the window (test T14-17).

## 11. Customer Balance Strategy

**One domain-level rule.** F2's `FinancialEventService.customer_balance` is now a thin delegate to `CustomerLedgerService.get_customer_balance` (lazy import; return shape preserved: `customer_id, total_debit, total_credit, balance, event_count, unattributed_events`). There is no second balance algorithm anywhere.

**Smallest justified change to F2 (documented per the F3 task):**
1. `customer_balance` previously summed signed amounts into debit/credit *buckets* (a negative discount delta reduced `total_credit`) and included ADJUSTMENT as an inert debit term. The ledger books each row into exactly one column, so reversal deltas now appear as debits and ADJUSTMENT is excluded (unresolved) and reported as unsupported. **The balance value and its signed/no-floor contract are unchanged** — only the debit/credit presentation split differs, and only for signed correction deltas (F2 test T21 updated accordingly; balance assertions unchanged).
2. Attribution helpers renamed public (`repair_customer_map`, `effective_customer_id`) + new read-only `all_events()` — so F3 reuses F2's attribution instead of duplicating it.

F2 suite re-run: **42/42 PASS** after this change.

## 12. Date Filtering

Domain-level, on the **financial event date**: `date_from` / `date_to`, **both boundaries inclusive** (test T14-17). Undated events cannot be placed in time: they are visible in the unbounded ledger and excluded from any bounded range (documented policy; no date invented — test T14b). No Repair dates or current date are consulted.

## 13. Legacy-Data Handling

- No startup backfill, no reconstruction, no new migration — F3 adds **zero schema changes** (verified on the production copy: no new columns, no ledger table).
- Legacy PAYMENT/REFUND rows (no `customer_id`) attribute through their repair's F1.5-authoritative `customer_id` — the F2 policy, reused via one shared implementation (tests L1, F3.2).
- Orphaned references (repair missing) are never guessed: excluded from customer ledgers, counted as `unattributed_events`, and left untouched on disk (tests L1, T18b, L3).
- Legacy rows are never modified by the ledger layer (test L3).

## 14. Invalid/Unknown Event Handling

| Situation | Behavior |
|---|---|
| Unknown event type | excluded, reported `unsupported_events[{reason: unknown_event_type}]` |
| ADJUSTMENT | excluded, reported `adjustment_direction_unresolved` |
| Missing/non-integer amount | excluded, reported `invalid_amount` (never silently zero-filled) |
| Missing `customer_id` (no resolvable repair) | unattributed — excluded from every customer ledger, counted, preserved on disk |
| Orphaned repair reference | same as unattributed (no guess) |
| Empty event date | visible unbounded; excluded from bounded ranges |

## 15. ADJUSTMENT Handling

Remains **DECISION REQUIRED** (F1.5 §19 / audit RCP 3 — the only directional code evidence conflicts with the target formula). F3 does not classify ADJUSTMENT as debit or credit, does not include it in any balance, and does not create any ADJUSTMENT events. If an ADJUSTMENT row appears, the ledger surfaces it under `unsupported_events` (visible, unclassified) — never silently treated as payment or charge (test T21).

## 16. Persistence Decision

**Derived ledger — no new table.** The roadmap's F3 phase ("Service مستقل برای دریافت گردش حساب...") requires a service, not storage; the F1.5/F2 architecture already has exactly one financial source of truth (`payment_transaction`). A second persisted ledger copy would duplicate that truth and re-create the drift class of problems F2 eliminated. Nothing in the current architecture demonstrates a persistence requirement, so per the F3 task rules no `DECISION REQUIRED` is raised — the derived design is the documented decision. If F4/F5 reporting ever demands pre-aggregated storage, that will be a new DECISION REQUIRED with migration analysis.

## 17. Service/Module Structure

- `services/customer_ledger_service.py` (new, focused):
  - `EVENT_LEDGER_MAP` — the single Event→Ledger mapping;
  - `classify_event` — explicit classification / refusal;
  - `CustomerLedgerEntry` — domain dataclass;
  - `build_ledger_entries` — pure projection (filter → classify → order);
  - `apply_running_balances` — signed running balance;
  - `CustomerLedgerService` — read-only I/O wrapper (`get_customer_ledger`, `get_customer_balance`, `get_totals`) composing `FinancialEventService` for reads/attribution.
- `services/financial_event_service.py` (minimal change, §11): public attribution helpers, `all_events()`, `customer_balance` delegation.
- No ledger logic in UI, Dashboard, InvoiceWidget, RepairDialog or the main window. No God Object: the module has one responsibility.

## 18. Files Changed

| File | Change |
|---|---|
| `services/financial_event_service.py` | attribution helpers made public (`repair_customer_map`, `effective_customer_id`), new `all_events()` read, `customer_balance` delegates to the ledger (one balance rule); docstrings updated |
| `services/test_financial_f2.py` | T21 debit/credit expectations updated to the ledger column convention (balance assertions unchanged) — documented in §11 |

## 19. Files Created

| File | Purpose |
|---|---|
| `services/customer_ledger_service.py` | Customer Subsidiary Ledger domain layer (projection, mapping, balances, filtering) |
| `services/test_financial_f3.py` | F3 validation suite (4 phases, 31 checks) |
| `FINANCIAL_F3_IMPLEMENTATION_REPORT.md` | this report |

## 20. Tests Added

`python services/test_financial_f3.py` (isolated subprocess phases; production DB never written):

- **ledger (17):** T1 empty ledger; T2–T5 single charge/payment/discount/refund classification; T6–9 multiple events (classification, effects, running balance 1000→700→600→650); T10/11 final balance + customer credit (no floor); T12/13 same-date determinism; T14–17 from/to/inclusive/from+to filtering; T14b undated events; T18 unattributed exclusion; T18b orphaned reference; T19 unknown type; T20 invalid/missing amounts; T21 ADJUSTMENT unresolved; T21b negative correction delta books as debit; T22b entry metadata (ids, reference, reconstructed flag).
- **integration (7):** I1 realistic sequence — charge 10,000,000, payment 3,000,000, discount 500,000, refund 200,000 → running balances 10M→7M→6.5M→**6,700,000**, total debit **10,200,000**, total credit **3,500,000**; I2 event immutability under ledger reads; I3 materialization-driven events project correctly (charge−discount==payable visible in the ledger); I4 repair edits leave historical entries unchanged (delta appended, original charge still 1,000,000); I5 F2 delegation (one rule); I6 ProfitService never imported; I7 PAYMENT/REFUND compatibility (`net_paid` = 2,800,000 on the sequence).
- **legacy (3):** L1 legacy attribution + orphan excluded + credit balance −450,000 visible; L2 determinism; L3 legacy rows never modified.
- **realdb (4):** F3.1 no schema change/no ledger table; F3.2 production-copy ledger (legacy payments legitimately visible as credits via the F2 attribution policy); F3.3 determinism; F3.4 save-flow integration (reconstructed charge, idempotent repeat).

## 21. Test Results

**F3 targeted validation: 31/31 PASS** (ledger 17, integration 7, legacy 3, realdb 4). All results from actual executions.

## 22. Regression Results

- **F2 suite: 42/42 PASS** (after the documented T21 presentation update; balance contract unchanged).
- **F1.5 suite: 40/40 PASS.**
- Existing suites: `test_verify_refactor.py`, `test_customer_repository.py`, `test_sqlite_storage.py` — all exit 0 (isolated CWDs).
- `compileall` over core/services/ui/controllers/app.py — OK; per-step `py_compile` — OK.
- Known pre-existing failure unchanged: stale `services/test_customer_service.py` (removed API; documented since F1.5).

## 23. Database Safety

- F3 introduces **no migration, no columns, no tables** (verified on a production-DB copy, F3.1).
- Full F3 suite run leaves the production `repair_manager.db` byte-identical (UTC mtime compared before/after — unchanged); state verified: 5 repairs, 9 payment rows, 0 system events.
- All destructive-prone experiments ran on copies in temporary directories; the suite's phases each use an isolated CWD (DB path is CWD-relative).
- No commits, branches, stashes, resets, or Git configuration changes; no line-ending changes; `FINANCIAL_ROADMAP.md` untouched; the pre-existing working-tree modification to `FINANCIAL_F1_DATA_DOMAIN_AUDIT.md` (and the app-driven `repair_manager.db` state from the F1.5 migration deployment) left as found.

## 24. Unresolved Decisions

1. **ADJUSTMENT direction/sign** — unchanged since F1.5/F2; the ledger refuses classification and reports such rows as unsupported. Must be decided before any ADJUSTMENT producer ships (recommendation: adopt audit RCP 3, then extend `EVENT_LEDGER_MAP` — a one-line mapping change by design).
2. **Ledger persistence** — deliberately derived (§16); revisit only if a demonstrated requirement appears (would be DECISION REQUIRED).
3. Ledger UI/reporting — F4/F5 scope.

## 25. ROADMAP CHANGE PROPOSAL

**None.** F3 implements roadmap §24 phase F3 exactly (independent ledger service: statement assembly, running balance, debit/credit totals, date/type filtering — type filtering here takes the form of the explicit classification map; per-type statement filtering belongs to the F4 report DTOs). No roadmap rule was contradicted; the roadmap file is untouched.

## 26. Explicit F3 Scope Verification

Implemented: Event→Ledger central mapping; ledger entry domain model (derived); deterministic ordering; signed running balance; customer balance (single delegated rule); customer_id filtering; inclusive date-range filtering; totals; unattributed/unknown/invalid/ADJUSTMENT safe handling; legacy attribution reuse; focused tests; report.

NOT implemented: persistence of ledger rows, journal entries, chart of accounts, general ledger, double-entry, trial balance, financial statements, COGS/inventory/expense accounting, period closing, any UI (no report window, no tabs, no buttons, no PDF/print, no dashboard widgets), payment_transaction renames or second event tables, startup backfills, roadmap edits, commits, Git configuration changes.

---

*F3 boundary: the Customer Subsidiary Ledger is now a deterministic, read-only projection of immutable Financial Events. Next: F4 (Customer Report Service DTOs) consumes this layer; the Accounting Layer remains future work.*
