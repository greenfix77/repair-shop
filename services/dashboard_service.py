from dataclasses import dataclass, field
from typing import List, Optional, Any, Dict

from services.date_service import today_persian


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
    ):
        """Initialize with optional collaborators.

        Phase 4B wires ``customer_service``, ``todo_service`` and
        ``repair_service``. ``repair_source`` is the owner of the live
        repairs list (typically :class:`LaptopRepairManager`); it must
        expose a ``repairs`` attribute (list[dict]). The DashboardService
        never reaches into the storage layer itself — it asks the source.
        """
        self._todo_service = todo_service
        self._customer_service = customer_service
        self._repair_source = repair_source
        self._repair_service = repair_service

    # ------------------------------------------------------------------
    # KPI Cards
    # ------------------------------------------------------------------

    def today_income(self):
        """Return today's income amount.

        Returns ``None`` in Phase 3 (the value will be populated by a
        future financial phase). Once the financial pipeline is in
        place, this method must aggregate paid invoices received today
        via the existing ``SQLiteStorage`` and ``services.invoice_*``
        modules — NOT duplicate their queries.
        """
        return None

    def monthly_income(self):
        """Return this month's income amount.

        See :meth:`today_income` for the placeholder contract.
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
          - monthly_income  → RepairService.sum_paid_this_month(repair_list)

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

        return snapshot

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

    def income_trend(self) -> List[Any]:
        """Return income series points for the 'Income Trend' chart slot.

        Empty in Phase 3.
        """
        return []

    def repair_status_breakdown(self) -> List[Any]:
        """Return status→count pairs for the 'Repair Status' chart slot.

        Empty in Phase 3.
        """
        return []

    def monthly_activity(self) -> List[Any]:
        """Return monthly activity series for the 'Monthly Activity' chart.

        Empty in Phase 3.
        """
        return []
