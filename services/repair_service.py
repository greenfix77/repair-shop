from typing import List, Dict, Optional

from core.status import (
    STATUS_PENDING,
    STATUS_IN_PROGRESS,
    STATUS_COMPLETED,
    STATUS_DELIVERED,
)
from services.date_service import today_persian
from services.payment_reconciliation_service import PaymentReconciliationService


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

    _reconciliation_svc: Optional[PaymentReconciliationService] = None

    @classmethod
    def _reconciliation(cls) -> PaymentReconciliationService:
        if cls._reconciliation_svc is None:
            cls._reconciliation_svc = PaymentReconciliationService()
        return cls._reconciliation_svc

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
        """Return net income realized on today's ``payment_date``.

        Source of truth is the Payment Ledger via
        :class:`PaymentReconciliationService`. The legacy
        ``delivery_date``/``paid_amount``/``payment_status`` snapshot is
        no longer consulted for Dashboard KPIs. The ``repairs`` argument
        is accepted for backward compatibility with prior callers but
        is intentionally ignored.
        """
        return cls._reconciliation().net_income_for_payment_date(today_persian())

    @classmethod
    def sum_paid_this_month(cls, repairs: List[Dict]) -> int:
        """Return net income realized within the current payment month.

        Source of truth is the Payment Ledger via
        :class:`PaymentReconciliationService`. The ``repairs`` argument
        is accepted for backward compatibility with prior callers but
        is intentionally ignored.
        """
        current_month = today_persian()[:7]
        return cls._reconciliation().net_income_for_payment_month(current_month)
