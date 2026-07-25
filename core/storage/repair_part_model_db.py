from sqlalchemy import Column, Integer, String

from core.storage.database import Base


class RepairPartDB(Base):
    __tablename__ = "repair_part"

    id = Column(Integer, primary_key=True, autoincrement=True)
    repair_id = Column(Integer, nullable=False)
    part_id = Column(Integer, nullable=True)
    part_name_snapshot = Column(String, default="")
    quantity = Column(Integer, default=1)
    unit_price = Column(Integer, default=0)
    total_price = Column(Integer, default=0)
    purchase_price_snapshot = Column(Integer, default=0)
