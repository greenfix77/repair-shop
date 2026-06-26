from sqlalchemy import Column, Integer, String

from core.storage.database import Base


class CustomerDB(Base):
    __tablename__ = "customer"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_code = Column(String, unique=True, default="")
    full_name = Column(String, default="")
    phone = Column(String, unique=True)
    email = Column(String, default="")
    website = Column(String, default="")
    national_id = Column(String, default="")
    address = Column(String, default="")
    city = Column(String, default="")
    province = Column(String, default="")
    postal_code = Column(String, default="")
    notes = Column(String, default="")
    created_at = Column(String, default="")
    updated_at = Column(String, default="")
