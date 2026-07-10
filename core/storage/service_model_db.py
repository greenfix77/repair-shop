from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime

from core.storage.database import Base


class ServiceDB(Base):
    __tablename__ = "service"

    id = Column(Integer, primary_key=True, autoincrement=True)
    service_code = Column(String, unique=True, default="")
    name = Column(String, nullable=False)
    default_price = Column(Integer, nullable=False, default=0)
    description = Column(Text, default="")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
