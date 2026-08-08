from dataclasses import dataclass, field
from typing import List, Optional, Any, Dict

from core.status import STATUS_COMPLETED, ALL_STATUSES
from services.date_service import today_persian
from services.profit_service import ProfitService


@dataclass
class DashboardSnapshot:
    """Lightweight, immutable-by-convention Dashboard state.

    Holds *aggregated* KPI values produced by the domain services. The
    snapshot is created by :meth:`DashboardService.get_snapshot` and
    consumed by :class:`DashboardDialog` in a **single** call.

    Field set for Phase 4B (non-financial):

      - customer_count
      - today_todos
      - active_repairs
      - ready_repairs

    Financial / future fields are intentionally absent so a later phase
    can extend this dataclass without touching DashboardDialog's request
    surface (the dialog still asks for *one* snapshot).

    ``None`` means "not yet provided". The dialog interprets ``None``
    the same as the original "--" placeholder to keep cards meaningful
    when a value is unavailable (defensive default).
    """

    customer_count: Optional[int] = None
    today_todos: Optional[int] = None
    active_repairs: Optional[int] = None
    ready_repairs: Optional[int] = None

    today_income: Optional[int] = None
    monthly_income: Optional[int] = None

    today_revenue: Optional[int] = None
    monthly_revenue: Optional[int] = None
    today_profit: Optional[int] = None
    monthly_profit: Optional[int] = None
    average_profit_margin: Optional[float] = None

    future: Dict[str, Any] = field(default_factory=dict)


class DashboardService:
    """Centralized service for all Dashboard statistics.

    This service is the SINGLE source of Dashboard data. DashboardDialog
    must communicate ONLY with this service; it must NEVER query
    repositories directly.

    Architectural rules:
      - No UI code lives here.
      - No chart drawing lives here (the chart placeholders are unchanged).
      - No SQL or raw data access lives here in Phase 3; method bodies will
        delegate to existing services (TodoService, CustomerService, …) in
        future phases without duplicating their queries.
      - Future phases can extend this class with additional methods
        (financial reports, inventory, profit, expenses, trends, …).
        Adding methods must NOT require modifications to DashboardDialog
        widget structure or layout.

    Construction keeps all dependencies optional so the service can be
    instantiated without injecting anything (handy for tests and for the
    Phase 3 UI-only milestone). When real backing services are wired
    later, they can be supplied via the constructor or via the
    ``service`` attribute without breaking callers.
    """

    def __init__(
        self,
        todo_service: Optional[Any] = None,
        customer_service: Optional[Any] = None,
        repair_source: Optional[Any] = None,
        repair_service: Optional[Any] = None,
        profit_service: Optional[ProfitService] = None,
    ):
        """Initialize with optional collaborators.

        Phase 4B wires ``customer_service``, ``todo_service`` and
        ``repair_service``. ``repair_source`` is the owner of the live
        repairs list (typically :class:`LaptopRepairManager`); it must
        expose a ``repairs`` attribute (list[dict]). The DashboardService
        never reaches into the storage layer itself — it asks the source.

        Phase 5F-2 adds ``profit_service`` (defaults to a fresh
        :class:`ProfitService` instance). All profit math goes through
        this collaborator.
        """
        self._todo_service = todo_service
        self._customer_service = customer_service
        self._repair_source = repair_source
        self._repair_service = repair_service
        self._profit_service = profit_service or ProfitService()

    # ------------------------------------------------------------------
    # KPI Cards
    # ------------------------------------------------------------------

    def today_income(self):
        """Return today's income amount from the Payment Ledger.

        Delegates to :class:`RepairService` which in turn asks
        :class:`PaymentReconciliationService` for ``SUM(PAYMENT) -
        SUM(REFUND)`` filtered by today's ``payment_date``.
        """
        return None

    def monthly_income(self):
        """Return this month's income amount from the Payment Ledger.

        Delegates to :class:`RepairService` which asks
        :class:`PaymentReconciliationService` for ``SUM(PAYMENT) -
        SUM(REFUND)`` filtered by the current month prefix.
        """
        return None

    def active_repairs(self):
        """Return the count of currently active repairs.

        See :meth:`today_income` for the placeholder contract.
        """
        return None

    def ready_repairs(self):
        """Return the count of repairs ready for delivery.

        See :meth:`today_income` for the placeholder contract.
        """
        return None

    def today_todos(self):
        """Return the count of todos due today.

        See :meth:`today_income` for the placeholder contract.
        """
        return None

    def customer_count(self):
        """Return the total customer count.

        See :meth:`today_income` for the placeholder contract.
        """
        return None

    # ------------------------------------------------------------------
    # Snapshot – one-shot load for DashboardDialog
    # ------------------------------------------------------------------

    def get_snapshot(self) -> DashboardSnapshot:
        """Return a single DashboardSnapshot aggregating all Dashboard KPIs.

        DashboardDialog calls this **once** at open time. The snapshot
        bundles all KPI values so the dialog never makes multiple
        round-trips to the service.

        Aggregation rules (no business logic duplication):
          - customer_count  → CustomerService.count_customers()
          - today_todos     → TodoService.count_due_today(today_persian())
          - active_repairs   → RepairService.count_active(repair_list)
          - ready_repairs   → RepairService.count_ready_for_delivery(repair_list)
          - today_income    → RepairService.sum_paid_today(repair_list)
                               — now reads the Payment Ledger via
                                 PaymentReconciliationService
                                 (SUM(PAYMENT) - SUM(REFUND) by today)
          - monthly_income  → RepairService.sum_paid_this_month(repair_list)
                               — now reads the Payment Ledger via
                                 PaymentReconciliationService
                                 (SUM(PAYMENT) - SUM(REFUND) by month)

        Financial values are aggregated via RepairService so the
        DashboardService never duplicates financial calculations.
        ``None`` is returned when a value cannot be computed.
        """
        snapshot = DashboardSnapshot()

        if self._customer_service is not None:
            try:
                snapshot.customer_count = self._customer_service.count_customers()
            except Exception:
                snapshot.customer_count = None

        if self._todo_service is not None:
            try:
                snapshot.today_todos = self._todo_service.count_due_today(
                    today_persian()
                )
            except Exception:
                snapshot.today_todos = None

        if self._repair_service is not None and self._repair_source is not None:
            try:
                repairs = self._repair_source.repairs
            except Exception:
                repairs = []
            try:
                snapshot.active_repairs = self._repair_service.count_active(repairs)
                snapshot.ready_repairs = self._repair_service.count_ready_for_delivery(
                    repairs
                )
                snapshot.today_income = self._repair_service.sum_paid_today(repairs)
                snapshot.monthly_income = self._repair_service.sum_paid_this_month(
                    repairs
                )
            except Exception:
                snapshot.active_repairs = None
                snapshot.ready_repairs = None
                snapshot.today_income = None
                snapshot.monthly_income = None

        snapshot.today_revenue, snapshot.today_profit = self._profit_for_window(
            repairs or [], 'today'
        )
        snapshot.monthly_revenue, snapshot.monthly_profit = self._profit_for_window(
            repairs or [], 'month'
        )
        snapshot.average_profit_margin = self._average_profit_margin(repairs or [])

        return snapshot

    # ------------------------------------------------------------------
    # Profit helpers (Phase 5F-2)
    # ------------------------------------------------------------------

    def _completed_repairs(self, repairs: List[Any]) -> List[Dict]:
        result = []
        for r in repairs or []:
            if isinstance(r, dict) and r.get('status') == STATUS_COMPLETED:
                result.append(r)
        return result

    def _profit_for_window(
        self, repairs: List[Any], window: str
    ) -> (Optional[int], Optional[int]):
        """Sum revenue and gross profit across completed repairs in window.

        ``window`` is ``'today'`` or ``'month'``. Date key on the repair
        dict is ``delivery_date`` (Persian string). Returns ``(None,
        None)`` when the profit service or repair list is missing.
        """
        if not repairs:
            return 0, 0
        today = today_persian()
        if window == 'today':
            target = today
            match = lambda d: (d or '').strip() == target  # noqa: E731
        elif window == 'month':
            prefix = today[:7]
            match = lambda d: (d or '').strip().startswith(prefix)  # noqa: E731
        else:
            return 0, 0
        revenue = 0
        profit = 0
        for r in self._completed_repairs(repairs):
            if not match(r.get('delivery_date', '')):
                continue
            breakdown = self._profit_service.calculate_profit(r)
            revenue += int(breakdown.get('gross_revenue', 0) or 0)
            profit += int(breakdown.get('gross_profit', 0) or 0)
        return revenue, profit

    def _average_profit_margin(self, repairs: List[Any]) -> Optional[float]:
        completed = self._completed_repairs(repairs)
        if not completed:
            return 0.0
        margins = []
        for r in completed:
            breakdown = self._profit_service.calculate_profit(r)
            margins.append(float(breakdown.get('profit_margin', 0) or 0))
        if not margins:
            return 0.0
        return sum(margins) / len(margins)

    # ------------------------------------------------------------------
    # Information Panels
    # ------------------------------------------------------------------

    def recent_activities(self) -> List[Any]:
        """Return a list of recent activity records for the dashboard panel.

        Returns an empty list in Phase 3. A future phase may populate this
        from a feed of repair / invoice / todo recent events.
        """
        return []

    def alerts(self) -> List[Any]:
        """Return a list of alert items for the dashboard panel.

        Returns an empty list in Phase 3. A future phase may populate this
        from overdue repairs, overdue invoices, overdue todos, etc.
        """
        return []

    # ------------------------------------------------------------------
    # Charts placeholder API
    # ------------------------------------------------------------------
    # The chart placeholders in DashboardDialog remain purely visual until
    # a Charts phase kicks off. The methods below are added so future
    # phases can extend this class incrementally (financial reports,
    # inventory, profit, expenses, monthly reports, employee statistics,
    # repair trends) without re-touching the Dashboard UI architecture.

    def income_trend(self, days: int = 7) -> List[Any]:
        """Return recent revenue trend points for the 'Income Trend' chart.

        Each point is ``(label, revenue)`` where ``label`` is the delivery
        date rendered as ``MM/DD`` and ``revenue`` is the gross revenue of
        completed repairs delivered that day. Revenue is aggregated by
        delegating each repair to :class:`ProfitService` (the sole owner of
        profit math); this method never recomputes financial formulas.
        Points are ordered oldest → newest, limited to the ``days`` most
        recent days that actually contain deliveries.
        """
        repairs = []
        try:
            repairs = self._repair_source.repairs or []
        except Exception:
            repairs = []
        per_day: Dict[str, int] = {}
        for r in self._completed_repairs(repairs):
            delivery = (r.get('delivery_date') or '').strip()
            if not delivery:
                continue
            try:
                breakdown = self._profit_service.calculate_profit(r)
                revenue = int(breakdown.get('gross_revenue', 0) or 0)
            except Exception:
                continue
            parts = delivery.split('/')
            label = parts[1] + '/' + parts[2] if len(parts) == 3 else delivery
            per_day[label] = per_day.get(label, 0) + revenue
        ordered = sorted(per_day.items())
        return ordered[-days:]

    def repair_status_breakdown(self) -> List[Any]:
        """Return ``(status, count)`` pairs for the 'Repair Status' chart.

        Counts every repair by its current status, ordered by the canonical
        status list from :mod:`core.status`. Zero-count statuses are omitted.
        Pure counting of existing data — no financial logic involved.
        """
        repairs = []
        try:
            repairs = self._repair_source.repairs or []
        except Exception:
            repairs = []
        counts: Dict[str, int] = {}
        for r in repairs:
            status = r.get('status') if isinstance(r, dict) else None
            if status:
                counts[status] = counts.get(status, 0) + 1
        return [(s, counts.get(s, 0)) for s in ALL_STATUSES if counts.get(s, 0) > 0]

    def monthly_activity(self, months: int = 6) -> List[Any]:
        """Return monthly activity points for the 'Monthly Activity' chart.

        Each point is ``(label, count)`` where ``label`` is the Persian
        ``YYYY/MM`` prefix of a completed repair's delivery date and
        ``count`` is the number of completed repairs that month. Ordered
        oldest → newest, limited to the ``months`` most recent months that
        are present in the data. Pure counting — no financial logic.
        """
        repairs = []
        try:
            repairs = self._repair_source.repairs or []
        except Exception:
            repairs = []
        per_month: Dict[str, int] = {}
        for r in self._completed_repairs(repairs):
            delivery = (r.get('delivery_date') or '').strip()
            if not delivery:
                continue
            month = delivery[:7]
            per_month[month] = per_month.get(month, 0) + 1
        ordered = sorted(per_month.items())
        return ordered[-months:]
