from sqlalchemy import Column, Integer, String, Boolean, Text

from core.storage.database import Base


class TodoDB(Base):
    __tablename__ = "todo"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False)
    description = Column(Text, default="")
    due_date = Column(String, default="")
    priority = Column(String, default="معمولی")
    is_done = Column(Boolean, default=False)
    created_at = Column(String, default="")
    updated_at = Column(String, default="")
