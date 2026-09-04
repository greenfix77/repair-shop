"""Customer Report Service (F4) — DTO/report layer over the F3 ledger.

F4 converts the F3 Customer Subsidiary Ledger (and only it) into a
stable, read-oriented customer financial report model that the future
F5 UI / PDF phases can consume directly.

    Financial Events (F2, authority)
        ↓
    CustomerLedgerService (F3, authoritative ledger projection)
        ↓
    CustomerReportService (F4 — THIS module: DTO assembly only)
        ↓
    future F5 UI / PDF

Hard rules implemented here:

* NO financial math of its own: ledger balances, running balances,
  totals, ordering, event classification and financial date filtering
  are reused 1:1 from :class:`services.customer_ledger_service.
  CustomerLedgerService` (F3). The report transforms DTO shapes only
  (per-type summary nets are signed sums of F3 entry effects).
* Customer accounting and shop economics are separate domains: the
  report's ``shop_economics`` block (parts cost / profit via
  ProfitService, the authoritative shop-economics service) is detached
  metadata that NEVER participates in the customer balance.
* Customer selection is by ``customer_id`` only — no name/phone
  heuristics. Repair history reads the F1.5-authoritative persisted
  ``repairs.customer_id`` link.
* Repair OPERATIONAL data is used for descriptive history only. No
  historical financial amount is ever reconstructed from a mutable
  Repair total; per-repair amounts come from ledger events or are None.
* ADJUSTMENT stays unresolved: such events appear only through F3's
  ``unsupported_events`` reporting (never classified, never balanced).
* No UI, no Qt, no persistence, no PDF — DTOs are derived on demand and
  fully deterministic (no timestamps), so the same data always produces
  the same report.

Date semantics (documented, intentionally different per section):

* ``ledger`` and ``payment_history``: financial EVENT date, inclusive
  ``date_from``/``date_to``, via F3 (identical to F3's filtering).
* ``summary``: always the customer's CURRENT (all-time) state — the
  roadmap §13 header KPIs (مانده فعلی حساب) are current-state values.
  With no date range, summary totals and ledger totals coincide.
* ``repair_history``: operational view (receive/delivery dates), not
  filtered by the financial range; per-repair amounts shown are
  cumulative ledger nets from all events.
* ``shop_economics``: all-time, over repairs attributable by the
  authoritative customer_id; different date semantics, no effect on any
  customer-accounting field.
"""
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from core.status import STATUS_COMPLETED, STATUS_DELIVERED
from services.customer_ledger_service import (
    DISCOUNT,
    PAYMENT,
    REPAIR_CHARGE,
    REFUND,
    CustomerLedgerService,
)
from services.customer_service import CustomerService
from services.profit_service import ProfitService

BALANCE_STATUS_SETTLED = 'تسویه'
BALANCE_STATUS_DEBTOR = 'بدهکار'
BALANCE_STATUS_CREDITOR = 'بستانکار'

_CHARGE_TYPES = (REPAIR_CHARGE, PAYMENT, DISCOUNT, REFUND)


def balance_status_for(balance: int) -> str:
    """Roadmap §8 account states from the F3 signed balance (no floor)."""
    if balance > 0:
        return BALANCE_STATUS_DEBTOR
    if balance < 0:
        return BALANCE_STATUS_CREDITOR
    return BALANCE_STATUS_SETTLED


# ----------------------------------------------------------------------
# DTOs
# ----------------------------------------------------------------------
@dataclass
class CustomerSummary:
    """Roadmap §13 header KPIs — the customer's CURRENT account state."""

    customer_id: int
    customer_name: str
    phone: str
    repair_count: int
    completed_repair_count: int
    active_repair_count: int
    total_repair_charge: int      # net REPAIR_CHARGE (debits − reversals)
    total_payment: int            # net PAYMENT (positive = amount paid)
    total_discount: int           # net DISCOUNT (positive = credit given)
    total_refund: int             # net REFUND (positive = refunded)
    current_balance: int          # F3 signed balance (no floor)
    balance_status: str           # تسویه / بدهکار / بستانکار

    def as_dict(self) -> Dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class LedgerReport:
    """F3 ledger passthrough — shape transformed, semantics untouched."""

    entries: List[Dict[str, Any]]   # CustomerLedgerEntry.as_dict(), F3 order
    total_debit: int
    total_credit: int
    balance: int
    unsupported_events: List[Dict[str, Any]]
    unattributed_events: int

    def as_dict(self) -> Dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class PaymentHistory:
    """Roadmap §16 payments tab source — ledger-consistent by construction.

    Items are the windowed ledger entries of type PAYMENT/REFUND (F3
    order preserved). PAYMENT stays a credit; REFUND stays a debit.
    """

    items: List[Dict[str, Any]]
    total_paid: int       # Σ PAYMENT credits within the window
    total_refunded: int   # Σ REFUND debits within the window

    def as_dict(self) -> Dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class RepairHistoryItem:
    """One attributable repair — descriptive fields + ledger-derived amounts.

    ``ledger_charge`` / ``ledger_discount`` are cumulative NETS of the
    customer's ledger events for this repair (None when the repair has
    no events). They are NEVER taken from the repair's mutable totals.
    """

    repair_id: int
    receive_date: str
    delivery_date: str
    status: str
    brand: str
    model: str
    description: str
    ledger_charge: Optional[int]
    ledger_discount: Optional[int]

    def as_dict(self) -> Dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class ShopEconomics:
    """Separate shop-economics block — detached from the customer ledger.

    Computed by ProfitService (the authoritative shop-economics service)
    over repairs attributable via the persisted customer_id. Legacy
    repairs without customer_id are excluded. These values NEVER affect
    the customer balance.
    """

    repair_count_included: int
    parts_cost: int          # Σ purchase-price snapshots (shop cost)
    gross_revenue: int       # Σ sale amounts (parts + services + charges)
    gross_profit: int        # gross_revenue − parts_cost
    excluded_legacy_repairs: int
    note: str = ('Shop economics only — never part of the customer '
                 'balance. Excludes legacy repairs without customer_id.')

    def as_dict(self) -> Dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class CustomerReport:
    """The stable F4 report model for one customer (F5/PDF consumer)."""

    customer_id: int
    date_from: Optional[str]      # inclusive, financial-event semantics
    date_to: Optional[str]        # inclusive, financial-event semantics
    customer_found: bool          # False when the customer id is unknown
    summary: CustomerSummary
    ledger: LedgerReport
    payment_history: PaymentHistory
    repair_history: List[RepairHistoryItem]
    shop_economics: ShopEconomics

    def as_dict(self) -> Dict[str, Any]:
        return {
            'customer_id': self.customer_id,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'customer_found': self.customer_found,
            'summary': self.summary.as_dict(),
            'ledger': self.ledger.as_dict(),
            'payment_history': self.payment_history.as_dict(),
            'repair_history': [r.as_dict() for r in self.repair_history],
            'shop_economics': self.shop_economics.as_dict(),
        }


# ----------------------------------------------------------------------
# service
# ----------------------------------------------------------------------
class CustomerReportService:
    """Assemble the F4 CustomerReport from authoritative services only.

    Composition (no recalculation of any financial semantic):
      * CustomerLedgerService (F3) — ledger, totals, balance, filtering
      * CustomerService           — customer identification (Workflow
        → Service → Repository authoritative path)
      * ProfitService             — shop-economics block only
    """

    def __init__(
        self,
        ledger_service: Optional[CustomerLedgerService] = None,
        customer_service: Optional[CustomerService] = None,
        profit_service: Optional[ProfitService] = None,
    ):
        self._ledger = ledger_service or CustomerLedgerService()
        self._customers = customer_service or CustomerService()
        self._profit = profit_service or ProfitService()

    # ------------------------------------------------------------------
    def build_report(
        self,
        customer_id: Any,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> CustomerReport:
        customer_id = self._coerce_id(customer_id)
        customer = self._customers.get_customer(customer_id) \
            if customer_id is not None else None

        repairs, excluded_legacy = self._read_repairs(customer_id)

        # --- F3 ledger: windowed (requested range) ---------------------
        windowed = self._ledger.get_customer_ledger(
            customer_id, date_from=date_from, date_to=date_to)
        ledger_report = LedgerReport(
            entries=[e.as_dict() for e in windowed['entries']],
            total_debit=windowed['total_debit'],
            total_credit=windowed['total_credit'],
            balance=windowed['balance'],
            unsupported_events=list(windowed['unsupported_events']),
            unattributed_events=windowed['unattributed_events'],
        )

        # --- F3 ledger: unbounded (current state for the header) -------
        current = self._ledger.get_customer_ledger(customer_id)

        return CustomerReport(
            customer_id=customer_id,
            date_from=date_from,
            date_to=date_to,
            customer_found=customer is not None,
            summary=self._build_summary(
                customer_id, customer, repairs, current),
            ledger=ledger_report,
            payment_history=self._build_payment_history(
                windowed['entries']),
            repair_history=self._build_repair_history(repairs, current),
            shop_economics=self._build_shop_economics(
                repairs, excluded_legacy),
        )

    # ------------------------------------------------------------------
    # section builders (DTO shaping only — no financial math)
    # ------------------------------------------------------------------
    @staticmethod
    def _build_summary(
        customer_id: Optional[int],
        customer: Optional[Dict[str, Any]],
        repairs: List[Dict[str, Any]],
        current: Dict[str, Any],
    ) -> CustomerSummary:
        completed = sum(
            1 for r in repairs
            if r.get('status') in (STATUS_DELIVERED, STATUS_COMPLETED)
        )
        # Net per-type amounts from F3 entry effects (no recalculation):
        # REPAIR_CHARGE / REFUND are debit-direction (positive signed
        # effect); PAYMENT / DISCOUNT are credit-direction (negative
        # signed effect) — normalised here to conventional positives.
        net = {REPAIR_CHARGE: 0, PAYMENT: 0, DISCOUNT: 0, REFUND: 0}
        for entry in current['entries']:
            if entry.event_type in net:
                net[entry.event_type] += entry.signed_effect
        balance = current['balance']
        return CustomerSummary(
            customer_id=customer_id or 0,
            customer_name=(customer or {}).get('full_name', '') or '',
            phone=(customer or {}).get('phone', '') or '',
            repair_count=len(repairs),
            completed_repair_count=completed,
            active_repair_count=len(repairs) - completed,
            total_repair_charge=net[REPAIR_CHARGE],
            total_payment=-net[PAYMENT],
            total_discount=-net[DISCOUNT],
            total_refund=net[REFUND],
            current_balance=balance,
            balance_status=balance_status_for(balance),
        )

    @staticmethod
    def _build_payment_history(entries: List[Any]) -> PaymentHistory:
        items = []
        total_paid = 0
        total_refunded = 0
        for entry in entries:
            if entry.event_type not in (PAYMENT, REFUND):
                continue
            items.append(entry.as_dict())
            if entry.event_type == PAYMENT:
                total_paid += entry.credit
            else:
                total_refunded += entry.debit
        return PaymentHistory(
            items=items,
            total_paid=total_paid,
            total_refunded=total_refunded,
        )

    @staticmethod
    def _build_repair_history(
        repairs: List[Dict[str, Any]],
        current: Dict[str, Any],
    ) -> List[RepairHistoryItem]:
        # cumulative per-repair nets from ledger events (never Repair totals)
        charge_nets: Dict[int, int] = {}
        discount_nets: Dict[int, int] = {}
        for entry in current['entries']:
            if entry.repair_id is None:
                continue
            if entry.event_type == REPAIR_CHARGE:
                charge_nets[entry.repair_id] = (
                    charge_nets.get(entry.repair_id, 0)
                    + entry.signed_effect)
            elif entry.event_type == DISCOUNT:
                discount_nets[entry.repair_id] = (
                    discount_nets.get(entry.repair_id, 0)
                    + entry.signed_effect)

        items = []
        for repair in repairs:
            repair_id = repair['id']
            items.append(RepairHistoryItem(
                repair_id=repair_id,
                receive_date=repair.get('receive_date') or '',
                delivery_date=repair.get('delivery_date') or '',
                status=repair.get('status') or '',
                brand=repair.get('brand') or '',
                model=repair.get('model') or '',
                description=repair.get('issue') or '',
                ledger_charge=charge_nets.get(repair_id),
                ledger_discount=discount_nets.get(repair_id),
            ))
        items.sort(key=lambda item: (item.receive_date or '',
                                     item.repair_id))
        return items

    def _build_shop_economics(
        self, repairs: List[Dict[str, Any]],
        excluded_legacy: int,
    ) -> ShopEconomics:
        parts_cost = 0
        gross_revenue = 0
        gross_profit = 0
        for repair in repairs:
            breakdown = self._profit.calculate_profit(repair)
            parts_cost += int(breakdown.get('parts_cost', 0) or 0)
            gross_revenue += int(breakdown.get('gross_revenue', 0) or 0)
            gross_profit += int(breakdown.get('gross_profit', 0) or 0)
        return ShopEconomics(
            repair_count_included=len(repairs),
            parts_cost=parts_cost,
            gross_revenue=gross_revenue,
            gross_profit=gross_profit,
            excluded_legacy_repairs=excluded_legacy,
        )

    # ------------------------------------------------------------------
    # reads (read-only, authoritative links only)
    # ------------------------------------------------------------------
    @staticmethod
    def _coerce_id(value: Any) -> Optional[int]:
        if value in (None, '', 0):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _read_repairs(
        self, customer_id: Optional[int]
    ) -> tuple:
        """Read-only repairs attributable by the authoritative customer_id.

        Uses the application's standard read-only repair aggregate load.
        Repairs without a persisted customer_id (legacy) cannot be
        reliably attributed: they are excluded from the report's repair
        sections and counted (``excluded_legacy_repairs``).
        """
        from core.storage.sqlite_storage import SQLiteStorage
        try:
            all_repairs = SQLiteStorage().load_all()
        except Exception:
            all_repairs = []

        if customer_id is None:
            excluded = sum(
                1 for r in all_repairs if r.get('customer_id') is None)
            return [], excluded

        attributable = [
            r for r in all_repairs
            if r.get('customer_id') == customer_id
        ]
        excluded = sum(
            1 for r in all_repairs if r.get('customer_id') is None)
        return attributable, excluded
