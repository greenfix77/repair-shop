from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime

from core.storage.database import Base


class ChargeDB(Base):
    __tablename__ = "charge"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    category = Column(String, default="")
    default_amount = Column(Integer, default=0)
    description = Column(Text, default="")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
