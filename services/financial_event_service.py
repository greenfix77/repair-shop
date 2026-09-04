"""Financial Event service (F2 — Financial Event Foundation).

F2 turns the existing ``payment_transaction`` kernel (Option A-lite,
FINANCIAL_F1_5_IMPLEMENTATION_REPORT.md §11) into the Financial Event
layer by materializing REPAIR_CHARGE and DISCOUNT events alongside the
existing PAYMENT / REFUND rows.

Event vocabulary (FINANCIAL_ROADMAP.md §12):

    REPAIR_CHARGE — Debit: increases customer debt
    PAYMENT       — Credit: decreases customer debt
    DISCOUNT      — Credit: decreases customer debt
    REFUND        — Debit: increases customer debt
    ADJUSTMENT    — direction NOT established (DECISION REQUIRED, F1.5
                    §19 / audit RCP 3). F2 creates NO adjustment rows.

Customer balance concept (signed, NO zero-floor):

    balance = ΣREPAIR_CHARGE − ΣPAYMENT − ΣDISCOUNT + ΣREFUND (+ ΣADJUSTMENT)

    balance > 0  → customer owes the shop (بدهکار)
    balance < 0  → shop owes the customer (بستانکار)

Idempotency invariants
----------------------

* ``Σ REPAIR_CHARGE events`` per repair equals the cumulative
  pre-discount charge; ``Σ DISCOUNT events`` equals the cumulative
  effective discount credit. Both targets come from ONE authoritative
  breakdown — ``invoice_calculator.calculate_invoice_totals`` — so:

      Σcharge − Σdiscount  ==  current Customer Payable

  for every input (including the discount-larger-than-base clamp).
  Because of this decomposition, changing ONLY the discount emits ONLY
  a discount event — the discount is never counted twice.
* ``materialize_for_repair`` compares those targets against the event
  sums and emits AT MOST one event per dimension:
    - no events yet      → one ``initial`` event (full amount)
    - sum differs        → one signed ``delta`` correction event
    - sum already equals → NOTHING (repeated saves / restarts /
      unrelated edits are no-ops)
* System events carry a deterministic ``event_key``; a PARTIAL unique
  index on ``event_key`` is the database-level backstop against
  duplicates. Manual PAYMENT/REFUND rows keep ``event_key = NULL`` and
  are untouched by the constraint.

Historical immutability
-----------------------

* Existing event rows are NEVER updated or deleted by this service.
* Repair edits after a charge exists produce a NEW correction (delta)
  event; the original REPAIR_CHARGE stays exactly as first written.
* Corrections are traceable (type + note + deterministic key).

Date policy (F1.5 §8/§9 — not reinvented):

* REPAIR_CHARGE initial: ``delivery_date`` when present, else
  ``receive_date`` — NEVER silently today. Both empty → empty date plus
  an explicit reconstructed marker (no date is invented).
* Events materialized NOW (deltas, and new discounts in the F2 era):
  ``today_persian()`` — the date the event actually happened.
* Reconstructed events (a repair that predates the event system being
  materialized at its first post-F2 save) are explicitly marked in the
  note, per the F1.5 legacy policy.

customer_id: stamped from ``Repair.customer_id`` (authoritative since
F1.5). NO name/phone heuristics for new events.
"""
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.exc import IntegrityError

from core.storage.payment_transaction_repository import (
    PaymentTransactionRepository,
)
from services.date_service import today_persian
from services.invoice_calculator import calculate_invoice_totals

REPAIR_CHARGE = 'REPAIR_CHARGE'
PAYMENT = 'PAYMENT'
DISCOUNT = 'DISCOUNT'
REFUND = 'REFUND'
ADJUSTMENT = 'ADJUSTMENT'

FINANCIAL_EVENT_TYPES = (
    REPAIR_CHARGE, PAYMENT, DISCOUNT, REFUND, ADJUSTMENT,
)

RECONSTRUCTED_MARKER = 'رویداد بازسازی‌شده (پیش از سیستم رویداد مالی)'


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return default


def _coerce_customer_id(value: Any) -> Optional[int]:
    if value in (None, '', 0):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


class FinancialEventService:
    """Materialize and read Financial Events for repairs and customers.

    The service never mutates existing event rows; it only appends.
    """

    def __init__(self, repo: Optional[PaymentTransactionRepository] = None):
        self._repo = repo or PaymentTransactionRepository()

    # ------------------------------------------------------------------
    # reads
    # ------------------------------------------------------------------
    def events_for_repair(self, repair_id: Any) -> List[Dict]:
        """All financial events of one repair (every event type)."""
        if not repair_id:
            return []
        try:
            return self._repo.list_for_repair(int(repair_id))
        except Exception:
            return []

    def _events_of_type(self, events: List[Dict], tx_type: str) -> List[Dict]:
        return [e for e in events if e.get('transaction_type') == tx_type]

    @staticmethod
    def _sum_amounts(events: List[Dict]) -> int:
        return sum(_to_int(e.get('amount')) for e in events)

    def has_events_for_repair(self, repair_id: Any) -> bool:
        """True when the repair has ANY financial event (any type).

        Used by the deletion guard: a repair with financial history must
        not be deleted, because deletion would orphan its money trail.
        """
        events = self.events_for_repair(repair_id)
        return any(
            e.get('transaction_type') in FINANCIAL_EVENT_TYPES
            for e in events
        )

    def filter_deletable_repairs(
        self, repair_ids: List[Any]
    ) -> Tuple[List[Any], List[Any]]:
        """Split repair ids into (deletable, blocked_by_financial_events)."""
        deletable: List[Any] = []
        blocked: List[Any] = []
        for rid in repair_ids:
            if self.has_events_for_repair(rid):
                blocked.append(rid)
            else:
                deletable.append(rid)
        return deletable, blocked

    # ------------------------------------------------------------------
    # date policy (F1.5 §9 — charge date)
    # ------------------------------------------------------------------
    @staticmethod
    def charge_date_for(repair: Optional[Dict]) -> str:
        """F1.5 charge-date policy.

        delivered repair (delivery_date present) → delivery_date;
        otherwise → receive_date. Both empty → '' (the event stays
        explicitly undated and is flagged reconstructed — no invented
        date, no silent 'today').
        """
        repair = repair or {}
        delivery = (repair.get('delivery_date') or '').strip()
        receive = (repair.get('receive_date') or '').strip()
        if delivery:
            return delivery
        if receive:
            return receive
        return ''

    # ------------------------------------------------------------------
    # materialization
    # ------------------------------------------------------------------
    def materialize_for_repair(
        self, repair: Optional[Dict], is_new: bool = False
    ) -> Dict[str, Any]:
        """Materialize REPAIR_CHARGE / DISCOUNT events for one repair.

        Idempotent: call it on every repair save. A repair whose
        payable and discount did not change since its events produces
        zero new events.

        ``is_new`` marks the creation save (first ever save of the
        repair). First materialization of a pre-existing (legacy)
        repair is flagged reconstructed per the F1.5 policy.
        """
        repair = repair or {}
        repair_id = repair.get('id')
        result: Dict[str, Any] = {
            'repair_id': repair_id,
            'created': [],
            'skipped': True,
        }
        if not repair_id:
            return result

        events = self.events_for_repair(repair_id)
        charge_events = self._events_of_type(events, REPAIR_CHARGE)
        discount_events = self._events_of_type(events, DISCOUNT)
        charge_sum = self._sum_amounts(charge_events)
        discount_sum = self._sum_amounts(discount_events)
        # was the repair already managed by the event system before this save?
        repair_was_f2_managed = bool(charge_events)

        customer_id = _coerce_customer_id(repair.get('customer_id'))

        # Authoritative decomposition (F1.5 SSOT — no independent math):
        #
        #   payable        = after_discount + tax_amount          (SSOT total)
        #   REPAIR_CHARGE  = subtotal + tax_amount                (pre-discount debit)
        #   DISCOUNT       = min(discount, subtotal)              (effective credit)
        #
        # Invariant (holds for ALL inputs, incl. the clamp case):
        #   REPAIR_CHARGE − DISCOUNT == payable
        # so the customer balance
        #   Σcharge − Σdiscount − Σpayment + Σrefund
        # always equals the current payable minus payments/refunds, and
        # a discount change emits ONLY a discount event (never a charge
        # delta too — the discount must not be counted twice).
        fin = calculate_invoice_totals(repair)
        payable = fin['total']
        target_charge = fin['subtotal'] + fin['tax_amount']
        target_discount = min(fin['discount'], fin['subtotal'])

        # ---- REPAIR_CHARGE -------------------------------------------
        if not charge_events:
            if target_charge != 0:
                reconstructed = not is_new
                charge_date = self.charge_date_for(repair)
                note = f"ثبت خودکار بدهی تعمیر #{repair_id}"
                if reconstructed:
                    note += f" — {RECONSTRUCTED_MARKER}"
                event = self._append(
                    repair_id=repair_id,
                    transaction_type=REPAIR_CHARGE,
                    amount=target_charge,
                    payment_date=charge_date,
                    customer_id=customer_id,
                    event_key=f'{REPAIR_CHARGE}:repair:{repair_id}:initial',
                    note=note,
                )
                if event is not None:
                    result['created'].append(event)
                    charge_sum = target_charge
        elif charge_sum != target_charge:
            # Post-charge edit: the original event stays immutable; the
            # difference is recorded as a NEW traceable correction event.
            delta = target_charge - charge_sum
            n = self._next_delta_index(charge_events)
            event = self._append(
                repair_id=repair_id,
                transaction_type=REPAIR_CHARGE,
                amount=delta,
                payment_date=today_persian(),
                customer_id=customer_id,
                event_key=f'{REPAIR_CHARGE}:repair:{repair_id}:delta:{n}',
                note=(
                    f"اصلاحیه بدهی تعمیر #{repair_id}: "
                    f"{charge_sum:,} → {target_charge:,}"
                ),
            )
            if event is not None:
                result['created'].append(event)
                charge_sum = target_charge

        # ---- DISCOUNT -------------------------------------------------
        if not discount_events:
            if target_discount > 0:
                reconstructed = (not is_new) and not repair_was_f2_managed
                if reconstructed:
                    # Historical (pre-event-system) discount: F1.5 legacy
                    # policy — policy date, explicit reconstructed marker.
                    discount_date = self.charge_date_for(repair)
                    note = f"ثبت خودکار تخفیف تعمیر #{repair_id}"
                    note += f" — {RECONSTRUCTED_MARKER}"
                else:
                    # New discount in the F2 era: stamped when the event
                    # is materialized at save time (F1.5 §8).
                    discount_date = today_persian()
                    note = f"ثبت خودکار تخفیف تعمیر #{repair_id}"
                event = self._append(
                    repair_id=repair_id,
                    transaction_type=DISCOUNT,
                    amount=target_discount,
                    payment_date=discount_date,
                    customer_id=customer_id,
                    event_key=f'{DISCOUNT}:repair:{repair_id}:initial',
                    note=note,
                )
                if event is not None:
                    result['created'].append(event)
                    discount_sum = target_discount
        elif discount_sum != target_discount:
            delta = target_discount - discount_sum
            n = self._next_delta_index(discount_events)
            event = self._append(
                repair_id=repair_id,
                transaction_type=DISCOUNT,
                amount=delta,
                payment_date=today_persian(),
                customer_id=customer_id,
                event_key=f'{DISCOUNT}:repair:{repair_id}:delta:{n}',
                note=(
                    f"اصلاحیه تخفیف تعمیر #{repair_id}: "
                    f"{discount_sum:,} → {target_discount:,}"
                ),
            )
            if event is not None:
                result['created'].append(event)
                discount_sum = target_discount

        result['skipped'] = not result['created']
        return result

    @staticmethod
    def _next_delta_index(events: List[Dict]) -> int:
        """Deterministic 1-based sequence for delta event keys."""
        n = 0
        for e in events:
            key = e.get('event_key') or ''
            if ':delta:' in key:
                try:
                    n = max(n, int(key.rsplit(':delta:', 1)[1]))
                except (TypeError, ValueError):
                    continue
        return n + 1

    def _append(
        self,
        repair_id: int,
        transaction_type: str,
        amount: int,
        payment_date: str,
        customer_id: Optional[int],
        event_key: str,
        note: str,
    ) -> Optional[Dict]:
        """Append one system event. Duplicate event_key → skip (None).

        The unique partial index on ``event_key`` is the hard backstop:
        if two materializations race, the loser gets an IntegrityError
        and treats the event as already existing (idempotent).
        """
        try:
            return self._repo.create({
                'repair_id': int(repair_id),
                'amount': int(amount),
                'payment_method': '',
                'payment_date': payment_date or '',
                'transaction_type': transaction_type,
                'note': note,
                'customer_id': customer_id,
                'event_key': event_key,
            })
        except IntegrityError:
            return None

    # ------------------------------------------------------------------
    # event reads + customer attribution (shared with the F3 ledger)
    # ------------------------------------------------------------------
    def all_events(self) -> List[Dict]:
        """All financial events (every type, every customer). Read-only."""
        try:
            return self._repo.list_all()
        except Exception:
            return []

    def repair_customer_map(self) -> Dict[int, Optional[int]]:
        """``{repair_id: customer_id}`` from the authoritative repairs.

        Read-only. Used ONLY to attribute legacy payment rows (which
        predate the customer_id event column) to a customer via their
        repair's stored customer_id — the F1.5 authoritative reference,
        not a name/phone heuristic. Shared with the F3 ledger projection
        so attribution has exactly one implementation.
        """
        from core.storage.database import SessionLocal
        from core.storage.repair_model_db import RepairDB
        session = SessionLocal()
        try:
            rows = session.query(RepairDB.id, RepairDB.customer_id).all()
            return {int(rid): cid for rid, cid in rows}
        except Exception:
            return {}
        finally:
            session.close()

    def effective_customer_id(
        self, event: Dict, repair_customers: Dict[int, Optional[int]]
    ) -> Optional[int]:
        """The customer a financial event belongs to (F2 attribution policy)."""
        cid = _coerce_customer_id(event.get('customer_id'))
        if cid is not None:
            return cid
        repair_id = _to_int(event.get('repair_id'))
        if repair_id:
            return _coerce_customer_id(repair_customers.get(repair_id))
        return None

    def customer_balance(self, customer_id: Any) -> Dict[str, Any]:
        """Signed customer balance derived ONLY from financial events.

        No zero-floor: a negative balance is the customer's credit
        (بستانکار) and must survive (F1.5 / audit NEW-2).

        F3: this is now a thin delegate to the Customer Subsidiary
        Ledger (:class:`services.customer_ledger_service.
        CustomerLedgerService`) so there is exactly ONE balance rule.
        Per the F3 ADJUSTMENT rule, ADJUSTMENT events are NOT classified
        (direction unresolved) and are therefore excluded from the
        balance while remaining visible as unsupported events — the
        ledger service reports them; nothing is silently treated as
        payment or charge. (Change from F2: the inert ADJUSTMENT term
        was removed; no ADJUSTMENT rows exist, so no stored value is
        affected.)
        """
        from services.customer_ledger_service import CustomerLedgerService
        return CustomerLedgerService(self).get_customer_balance(customer_id)
