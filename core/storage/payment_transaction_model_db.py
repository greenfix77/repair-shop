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

    __table_args__ = (
        Index("ix_payment_transaction_repair_id", "repair_id"),
        Index("ix_payment_transaction_payment_date", "payment_date"),
    )
