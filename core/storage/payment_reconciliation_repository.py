"""Read-only repository for Payment Ledger reconciliation queries.

Phase 5E-2: this module only SELECTs from `repairs` and
`payment_transaction`. It never inserts, updates, or deletes rows.

The class is parameterised on a SQLAlchemy ``session_factory`` (defaults to
the project's ``SessionLocal``). Tests can therefore inject an isolated
in-memory session factory without touching ``repair_manager.db``.
"""
from typing import Callable, Dict, List, Optional

from sqlalchemy import func

from core.storage.database import SessionLocal
from core.storage.payment_transaction_model_db import PaymentTransactionDB
from core.storage.repair_model_db import RepairDB


class PaymentReconciliationRepository:
    """Read-only aggregation helpers for payment reconciliation."""

    def __init__(self, session_factory: Optional[Callable] = None):
        self._session_factory = session_factory or SessionLocal

    def get_repair_paid_amount(self, repair_id: int) -> Optional[int]:
        """Return ``repair.paid_amount`` for a given repair, or ``None`` if
        the repair does not exist."""
        session = self._session_factory()
        try:
            row = session.query(RepairDB).filter_by(id=repair_id).first()
            if row is None:
                return None
            paid = getattr(row, 'paid_amount', 0)
            try:
                return int(paid or 0)
            except (TypeError, ValueError):
                return 0
        finally:
            session.close()

    def list_all_repair_ids(self) -> List[int]:
        """Return every repair id present in the database."""
        session = self._session_factory()
        try:
            rows = session.query(RepairDB.id).all()
            return [int(r[0]) for r in rows if r[0] is not None]
        finally:
            session.close()

    def ledger_totals_for_repair(self, repair_id: int) -> Dict[str, int]:
        """Return ``{PAYMENT, REFUND, ADJUSTMENT, COUNT}`` totals for a
        single repair, summed from the ``payment_transaction`` table.

        Unknown transaction types are ignored on purpose — the reconciliation
        contract only knows the three documented types.

        F2: ``payment_transaction`` also stores REPAIR_CHARGE / DISCOUNT
        events. Those are NOT part of the payment reconciliation
        contract, so the query is scoped to the three reconciliation
        types. This keeps the historical verdict semantics unchanged:
        a repair whose only event is a REPAIR_CHARGE still reports
        ``NO_LEDGER`` (no payment rows), exactly as before F2.

        Missing or malformed amounts are coerced to ``0`` (safe default) but
        never silently mutated on disk: we only ``SELECT`` here.
        """
        session = self._session_factory()
        try:
            rows = (
                session.query(
                    PaymentTransactionDB.transaction_type,
                    func.coalesce(
                        func.sum(PaymentTransactionDB.amount), 0
                    ),
                    func.count(PaymentTransactionDB.transaction_id),
                )
                .filter(
                    PaymentTransactionDB.repair_id == repair_id,
                    PaymentTransactionDB.transaction_type.in_(
                        ('PAYMENT', 'REFUND', 'ADJUSTMENT')
                    ),
                )
                .group_by(PaymentTransactionDB.transaction_type)
                .all()
            )
        finally:
            session.close()

        totals = {'PAYMENT': 0, 'REFUND': 0, 'ADJUSTMENT': 0, 'COUNT': 0}
        for tx_type, amount_sum, count in rows:
            try:
                amount_sum = int(amount_sum or 0)
            except (TypeError, ValueError):
                amount_sum = 0
            try:
                count = int(count or 0)
            except (TypeError, ValueError):
                count = 0
            if tx_type in totals:
                totals[tx_type] = amount_sum
            totals['COUNT'] += count
        return totals

    def ledger_net_for_payment_date(self, payment_date: str) -> int:
        """Return ``SUM(PAYMENT) - SUM(REFUND)`` for a given ``payment_date``.

        Empty/missing date returns ``0`` (safe default).
        """
        date = (payment_date or '').strip()
        if not date:
            return 0
        session = self._session_factory()
        try:
            payment_sum = (
                session.query(func.coalesce(func.sum(PaymentTransactionDB.amount), 0))
                .filter(
                    PaymentTransactionDB.payment_date == date,
                    PaymentTransactionDB.transaction_type == 'PAYMENT',
                )
                .scalar()
            ) or 0
            refund_sum = (
                session.query(func.coalesce(func.sum(PaymentTransactionDB.amount), 0))
                .filter(
                    PaymentTransactionDB.payment_date == date,
                    PaymentTransactionDB.transaction_type == 'REFUND',
                )
                .scalar()
            ) or 0
        finally:
            session.close()
        try:
            payment_sum = int(payment_sum or 0)
        except (TypeError, ValueError):
            payment_sum = 0
        try:
            refund_sum = int(refund_sum or 0)
        except (TypeError, ValueError):
            refund_sum = 0
        return max(payment_sum - refund_sum, 0)

    def ledger_net_for_payment_month(self, year_month: str) -> int:
        """Return ``SUM(PAYMENT) - SUM(REFUND)`` for ``payment_date`` rows
        whose string prefix matches ``year_month`` (``YYYY/MM``).
        """
        prefix = (year_month or '').strip()
        if not prefix:
            return 0
        session = self._session_factory()
        try:
            payment_sum = (
                session.query(func.coalesce(func.sum(PaymentTransactionDB.amount), 0))
                .filter(
                    PaymentTransactionDB.payment_date.like(prefix + '%'),
                    PaymentTransactionDB.transaction_type == 'PAYMENT',
                )
                .scalar()
            ) or 0
            refund_sum = (
                session.query(func.coalesce(func.sum(PaymentTransactionDB.amount), 0))
                .filter(
                    PaymentTransactionDB.payment_date.like(prefix + '%'),
                    PaymentTransactionDB.transaction_type == 'REFUND',
                )
                .scalar()
            ) or 0
        finally:
            session.close()
        try:
            payment_sum = int(payment_sum or 0)
        except (TypeError, ValueError):
            payment_sum = 0
        try:
            refund_sum = int(refund_sum or 0)
        except (TypeError, ValueError):
            refund_sum = 0
        return max(payment_sum - refund_sum, 0)

    def net_paid_amount_for_repair(self, repair_id: int) -> int:
        """Return ``SUM(PAYMENT) - SUM(REFUND)`` for a single repair.

        This is the authoritative realized paid amount for the snapshot
        UI. Adjustment rows are intentionally excluded — the snapshot
        only tracks payments and refunds.
        """
        session = self._session_factory()
        try:
            payment_sum = (
                session.query(func.coalesce(func.sum(PaymentTransactionDB.amount), 0))
                .filter(
                    PaymentTransactionDB.repair_id == repair_id,
                    PaymentTransactionDB.transaction_type == 'PAYMENT',
                )
                .scalar()
            ) or 0
            refund_sum = (
                session.query(func.coalesce(func.sum(PaymentTransactionDB.amount), 0))
                .filter(
                    PaymentTransactionDB.repair_id == repair_id,
                    PaymentTransactionDB.transaction_type == 'REFUND',
                )
                .scalar()
            ) or 0
        finally:
            session.close()
        try:
            payment_sum = int(payment_sum or 0)
        except (TypeError, ValueError):
            payment_sum = 0
        try:
            refund_sum = int(refund_sum or 0)
        except (TypeError, ValueError):
            refund_sum = 0
        return max(payment_sum - refund_sum, 0)
