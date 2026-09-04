from datetime import datetime
from typing import List, Dict, Optional

from core.storage.database import SessionLocal
from core.storage.payment_transaction_model_db import PaymentTransactionDB


class PaymentTransactionRepository:
    def create(self, data: Dict) -> Dict:
        session = SessionLocal()
        try:
            row = PaymentTransactionDB(
                repair_id=data.get('repair_id', 0) or 0,
                amount=data.get('amount', 0) or 0,
                payment_method=data.get('payment_method', '') or '',
                payment_date=data.get('payment_date', '') or '',
                transaction_type=data.get('transaction_type', 'PAYMENT') or 'PAYMENT',
                created_at=data.get('created_at') or datetime.now(),
                note=data.get('note', '') or '',
                customer_id=data.get('customer_id'),
                event_key=data.get('event_key'),
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            return self._to_dict(row)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_by_id(self, transaction_id: int) -> Optional[Dict]:
        session = SessionLocal()
        try:
            row = session.query(PaymentTransactionDB).filter_by(
                transaction_id=transaction_id,
            ).first()
            return self._to_dict(row) if row else None
        finally:
            session.close()

    def list_for_repair(self, repair_id: int) -> List[Dict]:
        session = SessionLocal()
        try:
            rows = session.query(PaymentTransactionDB).filter_by(
                repair_id=repair_id,
            ).order_by(PaymentTransactionDB.created_at).all()
            return [self._to_dict(row) for row in rows]
        finally:
            session.close()

    def list_payment_history_for_repair(self, repair_id: int) -> List[Dict]:
        """Return only the payment history rows (PAYMENT / REFUND).

        F2: ``payment_transaction`` now also stores system-generated
        REPAIR_CHARGE / DISCOUNT events. The Financial tab's payment
        history keeps showing exactly what it showed before F2 — the
        customer's payments and refunds — so the UI behavior is
        unchanged. The full event stream (all types) is read via
        :meth:`list_for_repair` / :meth:`list_all`.
        """
        session = SessionLocal()
        try:
            rows = (
                session.query(PaymentTransactionDB)
                .filter(
                    PaymentTransactionDB.repair_id == repair_id,
                    PaymentTransactionDB.transaction_type.in_(
                        ('PAYMENT', 'REFUND')
                    ),
                )
                .order_by(PaymentTransactionDB.created_at)
                .all()
            )
            return [self._to_dict(row) for row in rows]
        finally:
            session.close()

    def list_by_payment_date(self, payment_date: str) -> List[Dict]:
        session = SessionLocal()
        try:
            rows = session.query(PaymentTransactionDB).filter_by(
                payment_date=payment_date,
            ).order_by(PaymentTransactionDB.created_at).all()
            return [self._to_dict(row) for row in rows]
        finally:
            session.close()

    def list_all(self) -> List[Dict]:
        session = SessionLocal()
        try:
            rows = session.query(PaymentTransactionDB).order_by(
                PaymentTransactionDB.created_at,
            ).all()
            return [self._to_dict(row) for row in rows]
        finally:
            session.close()

    @staticmethod
    def _to_dict(row: PaymentTransactionDB) -> Dict:
        return {
            'transaction_id': row.transaction_id,
            'repair_id': row.repair_id or 0,
            'amount': row.amount or 0,
            'payment_method': row.payment_method or '',
            'payment_date': row.payment_date or '',
            'transaction_type': row.transaction_type or 'PAYMENT',
            'created_at': row.created_at.isoformat() if row.created_at else '',
            'note': row.note or '',
            'customer_id': getattr(row, 'customer_id', None),
            'event_key': getattr(row, 'event_key', None),
        }
