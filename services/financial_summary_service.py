"""Single financial aggregation layer for a repair.

Phase 5F-1 introduces :class:`FinancialSummaryService` — the canonical
assembler of one repair's complete financial state. It composes the
existing :class:`ProfitService` and
:class:`PaymentReconciliationService` instead of duplicating any math.

Rules:

  * Pure composition only — no SQL, no repositories, no UI, no storage.
  * Accepts a ``repair_dict`` plus an optional repair id (the ledger
    service needs an id).
  * ``paid_amount`` always comes from the Payment Ledger via
    :class:`PaymentReconciliationService` — never from the stored
    ``Repair.paid_amount`` snapshot.
  * ``remaining_amount`` and ``payment_status`` are derived from
    ``gross_revenue`` and the ledger-derived ``paid_amount`` rather
    than from the stored snapshot.
"""
from typing import Any, Dict, Optional

from services.payment_reconciliation_service import PaymentReconciliationService
from services.profit_service import ProfitService


class FinancialSummaryService:
    """Compose ProfitService + PaymentReconciliationService into one dict."""

    def __init__(
        self,
        profit_service: Optional[ProfitService] = None,
        payment_service: Optional[PaymentReconciliationService] = None,
    ):
        self._profit_service = profit_service or ProfitService()
        self._payment_service = payment_service or PaymentReconciliationService()

    @staticmethod
    def _coerce_int(value: Any, default: int = 0) -> int:
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return default

    @classmethod
    def payment_status_for(cls, paid: Any, revenue: Any) -> str:
        """Single owner of the payment status rule.

        Used by consumers that already have a ``paid`` and ``revenue``
        pair computed (e.g. the InvoiceWidget, which tracks the
        post-discount/tax final amount) so they don't reimplement the
        unpaid / partial / settled ladder.
        """
        paid_amount = cls._coerce_int(paid)
        revenue_amount = cls._coerce_int(revenue)
        if paid_amount <= 0:
            return 'پرداخت نشده'
        if paid_amount < revenue_amount:
            return 'پرداخت جزئی'
        return 'تسویه شده'

    @classmethod
    def remaining_for(cls, paid: Any, revenue: Any) -> int:
        """Single owner of ``max(revenue - paid, 0)``."""
        paid_amount = cls._coerce_int(paid)
        revenue_amount = cls._coerce_int(revenue)
        return max(revenue_amount - paid_amount, 0)

    def calculate(self, repair: Optional[Dict], repair_id: Optional[int] = None) -> Dict[str, Any]:
        """Return the complete financial summary for one repair.

        The summary always includes every ProfitService field plus
        ledger-derived ``paid_amount``, ``remaining_amount`` and
        ``payment_status``. If ``repair_id`` is not supplied, the
        service falls back to ``repair.get('id')`` so callers don't
        need to pass both.
        """
        profit = self._profit_service.calculate_profit(repair)

        repair_id = repair_id if repair_id is not None else (
            (repair or {}).get('id') if isinstance(repair, dict) else None
        )
        try:
            paid_amount = (
                int(self._payment_service.net_paid_for_repair(int(repair_id)))
                if repair_id
                else 0
            )
        except Exception:
            paid_amount = 0

        gross_revenue = self._coerce_int(profit.get('gross_revenue', 0))
        remaining_amount = max(gross_revenue - paid_amount, 0)

        if paid_amount <= 0:
            payment_status = 'پرداخت نشده'
        elif paid_amount < gross_revenue:
            payment_status = 'پرداخت جزئی'
        else:
            payment_status = 'تسویه شده'

        return {
            'parts_cost': self._coerce_int(profit.get('parts_cost', 0)),
            'parts_revenue': self._coerce_int(profit.get('parts_revenue', 0)),
            'services_revenue': self._coerce_int(profit.get('services_revenue', 0)),
            'additional_charge_revenue': self._coerce_int(
                profit.get('additional_charge_revenue', 0)
            ),
            'gross_revenue': gross_revenue,
            'gross_profit': self._coerce_int(profit.get('gross_profit', 0)),
            'profit_margin': profit.get('profit_margin', 0) or 0,
            'paid_amount': paid_amount,
            'remaining_amount': remaining_amount,
            'payment_status': payment_status,
        }
