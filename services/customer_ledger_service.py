"""Customer Subsidiary Ledger service (F3).

F3 projects the Financial Events created by F2 (the ``payment_transaction``
kernel — Option A-lite) into a deterministic, chronological,
customer-level subsidiary ledger.

    Financial Event  (historical source — F2, append-only)
        ↓  deterministic projection (this module)
    Customer Ledger Entry  (derived domain representation — NOT persisted)
        ↓
    Customer balance / totals (signed, no zero-floor)
        ↓
    future: General Ledger / Journal Entries (Stage 5+)

Architectural rules (F3 task, FINANCIAL_ROADMAP.md §2.1/§3):

* Financial Event ≠ Ledger Entry. The event records WHAT happened; the
  ledger entry records HOW it affects one customer's account.
* The ledger is READ/PROJECTION only. It never creates, updates or
  deletes Financial Events and never reads mutable Repair totals or
  ProfitService. Dependency direction:

      Financial Event → Ledger projection   (never the reverse)

* No persistence: ledger entries are derived on demand. There is exactly
  ONE financial source of truth (the events); a second persisted ledger
  copy would duplicate it. (Documented persistence decision — see
  FINANCIAL_F3_IMPLEMENTATION_REPORT.md §16.)

Event → Ledger mapping (single central table — do not scatter these
checks anywhere else):

    REPAIR_CHARGE → DEBIT,  signed_effect = +amount
    PAYMENT       → CREDIT, signed_effect = −amount
    DISCOUNT      → CREDIT, signed_effect = −amount
    REFUND        → DEBIT,  signed_effect = +amount
    ADJUSTMENT    → UNSUPPORTED (direction unresolved — DECISION REQUIRED,
                    F1.5 §19 / audit RCP 3; never silently classified)
    anything else → UNSUPPORTED (unknown type)

Signed conventions:

* ``signed_effect``: debit effect is positive, credit effect is negative.
  For F2's signed correction deltas this formula is applied to the stored
  amount as-is (e.g. a DISCOUNT delta of −100 yields signed_effect +100,
  i.e. the reversal books as a debit — economically correct and traceable
  back to the DISCOUNT event).
* ``debit``  = max(0, signed_effect); ``credit`` = max(0, −signed_effect).
* Running balance = previous balance + signed_effect. A positive balance
  means the customer owes the shop (بدهکار); a negative balance means the
  customer has credit (بستانکار). NO zero-floor — credits survive.

Ordering (deterministic, never DB row order):

    1. event date (``payment_date``, Persian YYYY/MM/DD — ascending
       string order equals chronological order; empty/undated events
       sort FIRST, treated as oldest-unknown)
    2. ``created_at`` (ISO record timestamp, ascending)
    3. ``transaction_id`` (final, unique tiebreaker)

Filtering is by ``customer_id`` only (never name/phone). Date ranges are
INCLUSIVE on both boundaries and use the financial event date; undated
events are excluded from any bounded range (they cannot be placed in
time) and remain visible in the unbounded ledger.
"""
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from services.financial_event_service import (
    ADJUSTMENT,
    DISCOUNT,
    PAYMENT,
    RECONSTRUCTED_MARKER,
    REFUND,
    REPAIR_CHARGE,
    FinancialEventService,
    _coerce_customer_id,
)
# The single central Event→Ledger mapping. Deliberately does NOT contain
# ADJUSTMENT (unresolved direction) or any unknown type — those must be
# surfaced as unsupported, never silently classified.
EVENT_LEDGER_MAP: Dict[str, Tuple[str, int]] = {
    REPAIR_CHARGE: ('DEBIT', +1),
    PAYMENT: ('CREDIT', -1),
    DISCOUNT: ('CREDIT', -1),
    REFUND: ('DEBIT', +1),
}

DIRECTION_DEBIT = 'DEBIT'
DIRECTION_CREDIT = 'CREDIT'


@dataclass
class CustomerLedgerEntry:
    """Derived projection of one Financial Event for one customer.

    The financial event remains the historical authority; this object is
    a read-only view used for balances and (future) reporting/UI.
    """

    customer_id: int
    transaction_id: int          # the Financial Event id (authority link)
    repair_id: Optional[int]
    event_type: str
    event_date: str              # the financial event date (payment_date)
    created_at: str              # event record timestamp (ordering only)
    description: str             # event note
    direction: str               # natural direction of the event type
    debit: int                   # >0 when the effect increases customer debt
    credit: int                  # >0 when the effect decreases customer debt
    signed_effect: int           # +debit / −credit (balance arithmetic)
    running_balance: int         # balance AFTER this entry
    event_key: Optional[str]     # deterministic event identity (reference)
    reconstructed: bool          # derived from the F2 reconstruction marker
    # F4: passthrough metadata from the financial event (payment history
    # reporting). Additive only — no ledger semantics depend on it.
    payment_method: str = ''

    def as_dict(self) -> Dict[str, Any]:
        return dict(self.__dict__)


def classify_event(event: Dict[str, Any]) -> Tuple[str, str, Optional[int]]:
    """Classify one financial event for the ledger.

    Returns ``(status, direction, signed_effect)``:

      ('ok', 'DEBIT'|'CREDIT', signed_effect)
      ('unsupported', reason, None)

    Unknown event types, ADJUSTMENT (unresolved) and non-integer amounts
    are explicitly unsupported — never silently classified and never
    silently zero-filled.
    """
    tx_type = event.get('transaction_type') or ''
    if tx_type not in EVENT_LEDGER_MAP:
        if tx_type == ADJUSTMENT:
            return ('unsupported', 'adjustment_direction_unresolved', None)
        return ('unsupported', 'unknown_event_type', None)

    raw_amount = event.get('amount')
    try:
        amount = int(raw_amount)
    except (TypeError, ValueError):
        return ('unsupported', 'invalid_amount', None)

    direction, sign = EVENT_LEDGER_MAP[tx_type]
    return ('ok', direction, sign * amount)


def _order_key(entry: CustomerLedgerEntry) -> Tuple[str, str, int]:
    """Deterministic ordering key (documented in the module docstring)."""
    return (entry.event_date or '', entry.created_at or '',
            entry.transaction_id)


def build_ledger_entries(
    events: List[Dict[str, Any]],
    customer_id: Any,
    repair_customers: Optional[Dict[int, Optional[int]]] = None,
) -> Dict[str, Any]:
    """Pure projection: financial events → ordered ledger for one customer.

    ``events`` are raw financial-event dicts (as returned by the
    repository). Attribution follows the F2 policy: the event's own
    ``customer_id`` when present, otherwise the ``customer_id`` of the
    referenced repair (the F1.5 authoritative reference — never a
    name/phone heuristic). Events that cannot be attributed are EXCLUDED
    from every customer ledger and reported as unattributed; they are
    never guessed.

    ADJUSTMENT and unknown-type events are excluded from the ledger and
    reported under ``unsupported_events`` (visible, not classified).
    """
    target = _coerce_customer_id(customer_id)
    repair_customers = repair_customers or {}

    customer_events: List[Dict[str, Any]] = []
    unattributed = 0
    unsupported: List[Dict[str, Any]] = []

    for event in events:
        cid = _coerce_customer_id(event.get('customer_id'))
        if cid is None:
            repair_id = event.get('repair_id')
            try:
                repair_id_int = int(repair_id) if repair_id else 0
            except (TypeError, ValueError):
                repair_id_int = 0
            if repair_id_int:
                cid = _coerce_customer_id(repair_customers.get(repair_id_int))
        if cid is None:
            unattributed += 1
            continue
        if cid != target:
            continue

        status, direction, signed_effect = classify_event(event)
        if status != 'ok':
            unsupported.append({
                'transaction_id': event.get('transaction_id'),
                'event_type': event.get('transaction_type'),
                'reason': direction,
            })
            continue

        note = event.get('note') or ''
        entry = CustomerLedgerEntry(
            customer_id=cid,
            transaction_id=event.get('transaction_id'),
            repair_id=(int(event['repair_id'])
                       if event.get('repair_id') else None),
            event_type=event.get('transaction_type') or '',
            event_date=(event.get('payment_date') or '').strip(),
            created_at=event.get('created_at') or '',
            description=note,
            direction=direction,
            debit=max(signed_effect, 0),
            credit=max(-signed_effect, 0),
            signed_effect=signed_effect,
            running_balance=0,  # filled by apply_running_balances
            event_key=event.get('event_key'),
            reconstructed=RECONSTRUCTED_MARKER in note,
            payment_method=event.get('payment_method') or '',
        )
        customer_events.append(entry)

    customer_events.sort(key=_order_key)
    apply_running_balances(customer_events)

    return {
        'entries': customer_events,
        'unsupported_events': unsupported,
        'unattributed_events': unattributed,
    }


def apply_running_balances(entries: List[CustomerLedgerEntry]) -> int:
    """Fill ``running_balance`` in order; return the final balance.

    ``balance = previous balance + signed_effect`` — signed, NO
    zero-floor: customer credit (negative balance) survives.
    """
    balance = 0
    for entry in entries:
        balance += entry.signed_effect
        entry.running_balance = balance
    return balance


def _in_range(event_date: str, date_from: Optional[str],
              date_to: Optional[str]) -> bool:
    """Inclusive event-date range filter.

    Undated events (``''``) cannot be placed in time: they are excluded
    from any bounded range and remain visible only in the unbounded
    ledger (documented policy — no date is invented for them).
    """
    date = (event_date or '').strip()
    if not date:
        return False
    if date_from and date < date_from:
        return False
    if date_to and date > date_to:
        return False
    return True


class CustomerLedgerService:
    """Read-only Customer Subsidiary Ledger over the Financial Events.

    Composition: wraps :class:`FinancialEventService` for event reads and
    attribution (single owner of the F2 attribution policy). This service
    performs NO writes of any kind.
    """

    def __init__(self, event_service: Optional[FinancialEventService] = None):
        self._events = event_service or FinancialEventService()

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------
    def get_customer_ledger(
        self,
        customer_id: Any,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Build the subsidiary ledger for one customer.

        Returns entries (ordered, with running balances), totals and
        diagnostics. ``date_from`` / ``date_to`` are inclusive on the
        financial event date; undated events appear only without a
        range. ADJUSTMENT/unknown events are reported, never classified.
        """
        target = _coerce_customer_id(customer_id)
        events = self._events.all_events()
        repair_customers = self._events.repair_customer_map()

        projection = build_ledger_entries(
            events, target, repair_customers
        )
        entries: List[CustomerLedgerEntry] = projection['entries']

        if date_from or date_to:
            entries = [
                e for e in entries
                if _in_range(e.event_date, date_from, date_to)
            ]

        total_debit = sum(e.debit for e in entries)
        total_credit = sum(e.credit for e in entries)
        balance = apply_running_balances(entries)

        return {
            'customer_id': target,
            'entries': entries,
            'total_debit': total_debit,
            'total_credit': total_credit,
            'balance': balance,
            'entry_count': len(entries),
            'unsupported_events': projection['unsupported_events'],
            'unattributed_events': projection['unattributed_events'],
        }

    def get_customer_balance(self, customer_id: Any) -> Dict[str, Any]:
        """Authoritative signed customer balance (ledger-derived)."""
        ledger = self.get_customer_ledger(customer_id)
        return {
            'customer_id': ledger['customer_id'],
            'total_debit': ledger['total_debit'],
            'total_credit': ledger['total_credit'],
            'balance': ledger['balance'],
            'event_count': ledger['entry_count'],
            'unattributed_events': ledger['unattributed_events'],
        }

    def get_totals(self, customer_id: Any,
                   date_from: Optional[str] = None,
                   date_to: Optional[str] = None) -> Dict[str, int]:
        """Total debits / total credits / resulting balance (signed)."""
        ledger = self.get_customer_ledger(customer_id, date_from, date_to)
        return {
            'total_debit': ledger['total_debit'],
            'total_credit': ledger['total_credit'],
            'balance': ledger['balance'],
        }
