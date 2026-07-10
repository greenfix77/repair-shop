from sqlalchemy import Column, Integer, String, Float

from core.storage.database import Base


class RepairDB(Base):
    __tablename__ = "repairs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_name = Column(String, default="")
    phone = Column(String, default="")
    brand = Column(String, default="")
    model = Column(String, default="")
    issue = Column(String, default="")
    parts_cost = Column(Integer, default=0)
    labor_cost = Column(Integer, default=0)
    tax = Column(Float, default=0.0)
    discount = Column(Integer, default=0)
    status = Column(String, default="")
    receive_date = Column(String, default="")
    delivery_date = Column(String, default="")
    notes = Column(String, default="")
    warranty = Column(String, default="")
    paid_amount = Column(Integer, default=0)
    payment_status = Column(String, default="پرداخت نشده")
    financial_notes = Column(String, default="")
