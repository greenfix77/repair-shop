# Customer Root Cause Analysis

> Date: 2026-07-09
> Scope: RepairDialog -> CustomerWorkflow -> CustomerService -> CustomerRepository -> SQLite
> Mode: ANALYSIS ONLY. No code modified. No migrations. No commits. No push.
> Source of truth: CUSTOMER_BEHAVIOR_SPECIFICATION.md, CUSTOMER_WORKFLOW_STABILIZATION.md,
> CUSTOMER_WORKFLOW_REGRESSION_AUDIT.md, plus current code in the 5 target files.

## Note on audit currency

`CUSTOMER_WORKFLOW_REGRESSION_AUDIT.md` documents the PRE-refactor state
(`self._customer_service`, `RepairDialog.populate_customer_fields`, direct
`CustomerService` calls from the dialog). The CURRENT code is POST-refactor and
matches `CUSTOMER_WORKFLOW_STABILIZATION.md` (`self._workflow`,
`CustomerWorkflow.populate_fields`). Conformance below is judged against the
SPEC, using the CURRENT code as the implementation under analysis.

---

## 1. Actual Execution Graph (verified against current code)

### 1.1 Phone Auto-Fill
```
repair_dialog._on_phone_editing_finished            [repair_dialog.py:276]
  guard: empty / !hasAcceptableInput -> return
  -> CustomerWorkflow.find_customer_by_phone         [customer_workflow.py:40]
       -> CustomerService.find_customer              [customer_service.py:91]
            -> CustomerRepository.get_by_phone        [customer_repository.py:39]
  -> customer_id = found['id']  (guard)
  -> CustomerWorkflow.get_customer                  [customer_workflow.py:31]
       -> CustomerService.get_customer               [customer_service.py:118]
            -> CustomerRepository.get_by_id           [customer_repository.py:23]
  -> phone_input.blockSignals(True)
  -> CustomerWorkflow.populate_fields               [customer_workflow.py:66]  (10 widgets)
  -> phone_input.blockSignals(False)
```

### 1.2 Completer popup
```
repair_dialog._on_name_text_changed                 [repair_dialog.py:246]
  -> setCompletionPrefix(text) ; timer.start(250)
(250ms) _on_completer_search                       [repair_dialog.py:250]
  guard: len(text) < 2 -> clear model, return
  -> CustomerWorkflow.search_customers              [customer_workflow.py:24]
       -> CustomerService.search_customers           [customer_service.py:107] (len<2 guard)
            -> CustomerRepository.search             [customer_repository.py:127] (ILIKE %q%)
  -> model.clear + appendRow(label="{name}\n{phone}", Qt.UserRole = c['id'])
```

### 1.3 Completer selection
```
repair_dialog._on_completer_activated              [repair_dialog.py:264]  (activated[QModelIndex])
  -> customer_id = index.data(Qt.UserRole)         (NO display-text parsing)
  -> CustomerWorkflow.get_customer                  [customer_workflow.py:31]
       -> CustomerService.get_customer               [customer_service.py:118]
            -> CustomerRepository.get_by_id           [customer_repository.py:23]
  -> CustomerWorkflow.populate_fields               [customer_workflow.py:66]
  NOTE: phone_input signals are NOT blocked here (only customer_name_input is).
```

### 1.4 Duplicate detection (exact name)
```
CustomerService.resolve_customer                    [customer_service.py:16]
  normalize phone/full_name ; guard no phone & no name -> None
  phone? -> repo.get_by_phone -> return existing (no dialog)
  full_name? -> find_by_full_name (repo.search + Python exact-strip filter)
    exact found -> confirm_callback("مشتری مشابه", "...")
       Yes -> return existing ; No -> continue (do NOT create)
```

### 1.5 Similar-name detection
```
CustomerService.resolve_customer                    [customer_service.py:71]
  similar = repo.search(full_name)
  filter out c['full_name'].strip() == full_name   (excludes exact match)
  similar? -> confirm_callback("نام‌های مشابه", "{names}\n\nآیا ادامه می‌دهید؟")
    not proceed -> return None ; proceed -> continue
```

### 1.6 Customer creation
```
CustomerService.resolve_customer                    [customer_service.py:88]
  -> generate_customer_code                         [customer_service.py:122]
       repo.get_all() -> regex C(\d+) -> max+1 -> "C00000N"  (full-table scan)
  -> CustomerRepository.create                      [customer_repository.py:47]
       _normalize_phone(empty/whitespace -> None) -> INSERT ; phone NULL allowed
       session.rollback() + raise on UNIQUE violation
```

### 1.7 Customer reuse
```
Phone present  -> get_by_phone hit -> return existing (silent, priority 1)
Exact name     -> confirm Yes       -> return existing (priority 2)
```

### 1.8 Save entry
```
repair_dialog.validate_and_accept                  [repair_dialog.py:293]
  guard: phone present + invalid -> warning, STAY
  guard: self.repair_data (edit mode) -> accept() + return  (NO customer resolution)
  _get_customer_data() (10 fields)
  guard: no phone AND no full_name -> accept()
  CustomerWorkflow.resolve_customer(data, show_question callback)
  if customer -> populate_fields
  accept()  <-- ALWAYS, even if resolve returned None
```

---

## 2. Specification Conformance

| # | Scenario (spec) | Status | Evidence |
|---|-----------------|:------:|----------|
| 1 | Phone Auto-Fill | PASS | Guards + 2-step lookup + signal block + 10-field populate (repair_dialog:276-291) |
| 2 | Completer popup | PASS | 250ms debounce, len<2 guard, ILIKE, id in Qt.UserRole, no emojis (250-262) |
| 3 | Completer selection | PASS | activated[QModelIndex], id from UserRole, get_customer, populate_fields (264-271) |
| 4 | Duplicate name save | PASS | Decision tree matches spec section 8 (customer_service:57-86) |
| 5 | Similar names (completer) | PASS | repo.search minus exact; warn callback; cancel->None (71-86) |
| 6 | Customer without phone | PASS | empty->None->SQL NULL; UNIQUE allows multiple NULLs (repo:9-12,53) |
| 7 | Phone-edited refresh | PASS | populate_fields sets all 10 widgets (workflow:66-87) |
| 8 | New customer save | PASS | generate_customer_code + repo.create + normalize_phone (88-89, repo:47-73) |
| 9 | Customer reuse (phone/name) | PASS | phone->existing (52-55); exact+Yes->existing (66-67) |

### Gaps / partial conformance (not scenario failures)

| Item | Status | Note |
|------|:------:|------|
| Lookup by customer_code | PARTIAL | `repo.get_by_code` exists (repo:31) but workflow/service do not expose it; pre-existing failing service test (line 84) hits this. Not required by the 7 spec scenarios. |
| created_at / updated_at on create | PARTIAL | Columns default "" (model:21-22); `repo.create` takes them from form (defaults "") so new rows never get real timestamps. Data-quality gap, not a UI behavior issue. |
| Edit-mode customer update | N/A | Spec section 13 (Non-Goals #1/#4) explicitly out of scope; not a conformance failure. |

---

## 3. Root-Cause Grouping

No active scenario failures exist (all 9 PASS). The latent risks documented in
the audit cluster into the following independent root causes:

| Group | Root cause | Symptoms it produces | Files / methods |
|-------|-----------|----------------------|-----------------|
| R1 | Save flow conflates "repair save" with "customer resolved" | (a) `accept()` runs even when resolve returns None -> repair saved w/o customer on cancel; (b) edit-mode early `accept()` -> customer table never updated on repair edit | repair_dialog.py `validate_and_accept` (293-313) |
| R2 | No customer<->repair linkage in schema | Repairs hold denormalized name/phone only; stale-customer risk; underpins edit-mode gap; no customer history | repair_model_db.py / app layer (outside the 5 target files) |
| R3 | Phone auto-fill does 2 DB round-trips for one row | `find_customer_by_phone` then `get_customer` = redundant query (intentional per spec for single-load-path consistency) | repair_dialog.py `_on_phone_editing_finished` (280-288) |
| R4 | Inconsistent signal blocking | Completer path does not block `phone_input` while phone path does; harmless today (no `textChanged` slot) but fragile | repair_dialog.py `_on_completer_activated` (264-271) |
| R5 | Code-lookup path unexposed | `get_by_code` unused; failing service test line 84 | customer_service.py / customer_workflow.py |

**Independent root-cause estimate:** 5 total, but only **R1 and R2 are
behaviorally significant**. Effective independent root causes that actually
matter: ~2 (R1 save semantics, R2 data linkage). R3-R5 are low-impact /
defensive. R2 is a schema/roadmap item, not a stabilization defect.

---

## 4. Architecture Assessment

- **Is CustomerWorkflow the single source of truth?** YES. Verified: RepairDialog
  imports only CustomerWorkflow (repair_dialog.py:25), instantiates only
  CustomerWorkflow (61), and all four entry points (completer search, completer
  activate, phone auto-fill, save) call workflow methods only. `populate_fields`
  (workflow:66-87) is the sole customer-field setter; the only exception is
  `load_data` (repair data, exempted by spec rule 5). No CustomerService or
  CustomerRepository import leaks into the dialog. Conforms to spec section 1.

- **Is another major refactor necessary?** NO. The layered chain
  RepairDialog -> CustomerWorkflow -> CustomerService -> CustomerRepository ->
  SQLite is intact and conforms to the spec. Per `opencode_rules.md`:
  "Architecture refactor is COMPLETE. Do not perform additional architecture
  refactors unless explicitly requested."

- **Would targeted fixes be safer?** YES. Remaining issues are localized
  behavioral/semantic gaps, not structural. Targeted atomic fixes satisfy
  `opencode_rules.md` (smallest possible change, one fix per commit, no
  schema changes without approval) and avoid destabilizing a working chain.

---

## 5. Highest-Risk Regression Points

| Rank | File | Method | Why highest risk |
|:----:|------|--------|------------------|
| 1 | ui/dialogs/repair_dialog.py | `validate_and_accept` (293-313) | Single save entry point; unconditional `accept()` + edit-mode bypass; a regression here breaks the entire save flow and all three customer paths simultaneously. |
| 2 | services/customer_service.py | `resolve_customer` (16-89) | Decision tree with two user callbacks; reordering returns risks duplicate creation or lost reuse. |
| 3 | services/customer_workflow.py | `populate_fields` (66-87) | Sole field setter shared by completer, phone, and save paths; one bug breaks all three. |
| 4 | core/storage/customer_repository.py | `create` (47-73) | Phone normalization + UNIQUE handling; an error here causes constraint violations or NULL mishandling across all creation/reuse. |

---

## 6. Recommended Next Steps (priority order)

1. **Do NOT start a major refactor. Proceed with targeted fixes only.**
   Aligns with `opencode_rules.md` (architecture refactor complete; small atomic
   changes; no schema changes without approval).

2. **Confirm intended "cancel duplicate detection" behavior (R1a).**
   If cancel should abort the save (not silently accept), change
   `validate_and_accept` to `return` instead of `accept()` when
   `resolve_customer` returns None. This is a BEHAVIOR change -> requires
   explicit user approval before implementing. Do NOT auto-apply.

3. **Populate created_at / updated_at in `repo.create`** (PARTIAL gap).
   Low risk, data-quality only, no UI behavior change. One small commit.

4. **Add `phone_input` signal blocking in completer path** (R4) only if a future
   `textChanged`/`editingFinished` slot is planned; otherwise leave as-is to
   avoid an unnecessary change (spec does not require it for the completer path).

5. **Defer R3 (collapse phone round-trip) and R5 (code lookup).** Both extend or
   contradict the spec's single-load-path design; not stabilization work.

6. **R2 (customer<->repair FK) is a roadmap item** ("Customer database" phase),
   not a stabilization fix. Do not touch the schema now.

### Decision
**Proceed with targeted fixes. A major refactor is not necessary and is
explicitly discouraged by `opencode_rules.md`.** The architecture already
satisfies the single-source-of-truth requirement; only localized, individually
committable behavioral fixes remain, and even those marked "behavior change"
(step 2) must wait for explicit approval.

---

*End of root-cause analysis. No source files were modified.*
