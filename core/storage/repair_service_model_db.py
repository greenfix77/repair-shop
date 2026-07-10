from sqlalchemy import Column, Integer, String

from core.storage.database import Base


class RepairServiceDB(Base):
    __tablename__ = "repair_service"

    id = Column(Integer, primary_key=True, autoincrement=True)
    repair_id = Column(Integer, nullable=False)
    service_id = Column(Integer, nullable=True)
    service_name_snapshot = Column(String, default="")
    quantity = Column(Integer, default=1)
    unit_price = Column(Integer, default=0)
    total_price = Column(Integer, default=0)
