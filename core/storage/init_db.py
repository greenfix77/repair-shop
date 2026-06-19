from core.storage.database import Base, engine


def init_database():
    Base.metadata.create_all(bind=engine)
