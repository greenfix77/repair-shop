from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime

from core.storage.database import Base


class PartDB(Base):
    __tablename__ = "part"

    id = Column(Integer, primary_key=True, autoincrement=True)
    part_code = Column(String, unique=True, default="")
    name = Column(String, nullable=False)
    purchase_price = Column(Integer, default=0)
    sale_price = Column(Integer, default=0)
    stock_quantity = Column(Integer, default=0)
    description = Column(Text, default="")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
