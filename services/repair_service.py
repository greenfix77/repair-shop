from typing import List, Dict

from core.status import (
    STATUS_PENDING,
    STATUS_IN_PROGRESS,
    STATUS_COMPLETED,
    STATUS_DELIVERED,
)
from services.date_service import today_persian


class RepairService:
    """Business logic layer for repair aggregate statistics.

    The repair table is the single source of truth, but it is loaded
    and persisted by ``SQLiteStorage`` (not a dedicated RepairsRepository
    yet). RepairService therefore accepts the repair list as input and
    provides *aggregate* helpers only.

    Architectural rules:
      - No persistence code lives here. The list is supplied by the
        orchestrator (DashboardService).
      - Service-level aggregation only. No business rule decisions
        (status transitions, lifecycle rules) belong here.
      - Domain status strings are imported from ``core.status`` so we
        don't redefine the canonical labels.
    """

    ACTIVE_STATUSES = (STATUS_PENDING, STATUS_IN_PROGRESS)
    READY_STATUSES = (STATUS_COMPLETED,)
    PAID_STATUSES = ('تسویه شده', 'پرداخت جزئی')

    @staticmethod
    def count_by_status(repairs: List[Dict], status: str) -> int:
        """Return number of repairs whose status matches ``status``."""
        return sum(1 for r in (repairs or []) if r.get('status') == status)

    @classmethod
    def count_active(cls, repairs: List[Dict]) -> int:
        """Return number of currently *active* repairs.

        Active = not yet delivered and not yet completed.
        Concretely: STATUS_PENDING and STATUS_IN_PROGRESS.
        """
        if not repairs:
            return 0
        active_set = set(cls.ACTIVE_STATUSES)
        return sum(1 for r in repairs if r.get('status') in active_set)

    @classmethod
    def count_ready_for_delivery(cls, repairs: List[Dict]) -> int:
        """Return number of repairs ready for delivery.

        Ready = STATUS_COMPLETED. STATUS_DELIVERED repairs are not
        counted because they have already left the shop.
        """
        if not repairs:
            return 0
        ready_set = set(cls.READY_STATUSES)
        return sum(1 for r in repairs if r.get('status') in ready_set)

    # ------------------------------------------------------------------
    # Financial aggregations
    # ------------------------------------------------------------------

    @classmethod
    def sum_paid_today(cls, repairs: List[Dict]) -> int:
        """Return total paid amount for repairs delivered today.

        Counts only repairs where payment_status is not 'پرداخت نشده'.
        Empty list returns 0.
        """
        if not repairs:
            return 0
        paid_set = set(cls.PAID_STATUSES)
        today = today_persian()
        return sum(
            r.get('paid_amount', 0) or 0
            for r in repairs
            if (r.get('delivery_date') or '').strip() == today
            and r.get('payment_status', '') in paid_set
        )

    @classmethod
    def sum_paid_this_month(cls, repairs: List[Dict]) -> int:
        """Return total paid amount for repairs delivered in the current month.

        Counts only repairs where payment_status is not 'پرداخت نشده'.
        Empty list returns 0.
        """
        if not repairs:
            return 0
        paid_set = set(cls.PAID_STATUSES)
        today = today_persian()
        current_month = today[:7]
        return sum(
            r.get('paid_amount', 0) or 0
            for r in repairs
            if (r.get('delivery_date') or '').strip().startswith(current_month)
            and r.get('payment_status', '') in paid_set
        )
