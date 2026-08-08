"""Read-only reconciliation service for the Payment Ledger.

Phase 5E-2: this service compares each ``Repair``'s ``paid_amount``
(snapshot) against the totals derived from the
``payment_transaction`` ledger.

Diagnostic only — it never mutates either table.

Public API:
  - ``reconcile_repair(repair_id) -> dict | None``
  - ``reconcile_all_repairs() -> list[dict]``
  - ``summarize(results) -> dict`` (small helper)
"""
from typing import Dict, List, Optional

from core.storage.payment_reconciliation_repository import (
    PaymentReconciliationRepository,
)


class PaymentReconciliationService:
    """Business layer that turns ledger totals into MATCH / MISMATCH /
    NO_LEDGER verdicts.

    The service holds no state. The repository is read-only.
    """

    STATUS_MATCH = "MATCH"
    STATUS_MISMATCH = "MISMATCH"
    STATUS_NO_LEDGER = "NO_LEDGER"

    PAYMENT_TYPE = "PAYMENT"
    REFUND_TYPE = "REFUND"

    def __init__(self, repository: Optional[PaymentReconciliationRepository] = None):
        self._repo = repository or PaymentReconciliationRepository()

    def net_income_for_payment_date(self, payment_date: str) -> int:
        """Return net income realized on a given ``payment_date``.

        net = SUM(PAYMENT) - SUM(REFUND). Empty/missing date returns 0.
        Used by the Dashboard for today's income.
        """
        return self._repo.ledger_net_for_payment_date(payment_date)

    def net_income_for_payment_month(self, year_month: str) -> int:
        """Return net income realized within a payment month (``YYYY/MM``).

        net = SUM(PAYMENT) - SUM(REFUND) over rows whose ``payment_date``
        starts with the given prefix. Empty/missing prefix returns 0.
        Used by the Dashboard for the monthly income KPI.
        """
        return self._repo.ledger_net_for_payment_month(year_month)

    def net_paid_for_repair(self, repair_id: int) -> int:
        """Return the authoritative paid amount derived from the ledger.

        Single owner of ``net_paid`` for consumers:
            net_paid = SUM(PAYMENT) - SUM(REFUND)

        REFUND rows reduce the realized paid amount. ADJUSTMENT is
        intentionally excluded from the snapshot formula.

        Returns ``0`` when the repair has no ledger rows or doesn't
        exist. When no ``REFUND`` rows exist the result is identical to
        ``SUM(PAYMENT)`` — preserving prior PAYMENT-only behavior.
        """
        return self._repo.net_paid_amount_for_repair(int(repair_id))

    def reconcile_repair(self, repair_id: int) -> Optional[Dict]:
        """Reconcile a single repair.

        Returns ``None`` when the repair id does not exist (so the caller
        can distinguish "unknown repair" from "real but unmatched").
        """
        paid_amount = self._repo.get_repair_paid_amount(repair_id)
        if paid_amount is None:
            return None

        totals = self._repo.ledger_totals_for_repair(repair_id)
        return self._build_result(
            repair_id=repair_id,
            paid_amount=paid_amount,
            totals=totals,
        )

    def reconcile_all_repairs(self) -> List[Dict]:
        """Reconcile every repair present in the database.

        The list is ordered by ``repair_id`` for deterministic output.
        """
        results: List[Dict] = []
        for repair_id in self._repo.list_all_repair_ids():
            res = self.reconcile_repair(repair_id)
            if res is not None:
                results.append(res)
        return results

    @classmethod
    def summarize(cls, results: List[Dict]) -> Dict[str, int]:
        """Count results by status. Useful for CLI / reporting.

        This helper takes an already-computed list of reconciliation dicts
        and does not touch the database itself.
        """
        summary = {cls.STATUS_MATCH: 0, cls.STATUS_MISMATCH: 0, cls.STATUS_NO_LEDGER: 0}
        for r in results:
            status = r.get("status")
            if status in summary:
                summary[status] += 1
        return summary

    def _build_result(
        self, repair_id: int, paid_amount: int, totals: Dict[str, int]
    ) -> Dict:
        """Apply the reconciliation formula and status rules.

        Formula (verified against Phase 5E-2 test cases 1–5):
            net_ledger_amount = payment_total + adjustment_total - refund_total

        ADJUSTMENT adds to the realized net (e.g. manual write-ups).
        REFUND subtracts from the realized net (e.g. partial returns).
        PAYMENT is always positive in the current legacy migration.

        Status rules:
            NO_LEDGER  — repair has zero ledger rows.
            MATCH      — net_ledger_amount == repair.paid_amount.
            MISMATCH   — net_ledger_amount != repair.paid_amount.
        """
        payment_total = int(totals.get("PAYMENT", 0) or 0)
        refund_total = int(totals.get("REFUND", 0) or 0)
        adjustment_total = int(totals.get("ADJUSTMENT", 0) or 0)
        ledger_count = int(totals.get("COUNT", 0) or 0)

        if ledger_count == 0:
            net = 0
            status = self.STATUS_NO_LEDGER
            difference = int(paid_amount or 0) - net
        else:
            net = payment_total + adjustment_total - refund_total
            difference = int(paid_amount or 0) - net
            status = (
                self.STATUS_MATCH if difference == 0 else self.STATUS_MISMATCH
            )

        return {
            "repair_id": int(repair_id),
            "paid_amount": int(paid_amount or 0),
            "payment_total": payment_total,
            "refund_total": refund_total,
            "adjustment_total": adjustment_total,
            "net_ledger_amount": net,
            "difference": difference,
            "status": status,
        }
