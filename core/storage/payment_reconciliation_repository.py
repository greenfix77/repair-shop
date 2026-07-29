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
                .filter(PaymentTransactionDB.repair_id == repair_id)
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
