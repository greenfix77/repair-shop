from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DB_FILE = "repair_manager.db"

engine = create_engine(
    f"sqlite:///{DB_FILE}",
    echo=False
)

SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()
