from sqlalchemy import Column, Integer, String, DateTime, Index

from core.storage.database import Base


class PaymentTransactionDB(Base):
    __tablename__ = "payment_transaction"

    transaction_id = Column(Integer, primary_key=True, autoincrement=True)
    repair_id = Column(Integer, nullable=False, default=0)
    amount = Column(Integer, nullable=False, default=0)
    payment_method = Column(String, default="")
    payment_date = Column(String, default="")
    transaction_type = Column(String, nullable=False, default="PAYMENT")
    created_at = Column(DateTime)
    note = Column(String, default="")
    # F2 Financial-Event extensions (Option A-lite, FINANCIAL_F1_5 report §11):
    # customer_id  — authoritative customer attribution, stamped from
    #                Repair.customer_id at event creation (legacy rows NULL).
    # event_key    — deterministic identity of system-generated events
    #                (idempotency). NULL for manual PAYMENT/REFUND rows.
    #                Uniqueness is enforced by a PARTIAL unique index so
    #                legacy NULL rows are never affected.
    customer_id = Column(Integer, nullable=True)
    event_key = Column(String, nullable=True)

    __table_args__ = (
        Index("ix_payment_transaction_repair_id", "repair_id"),
        Index("ix_payment_transaction_payment_date", "payment_date"),
    )
