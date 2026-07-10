from core.storage.database import Base, engine
from core.storage.customer_model_db import CustomerDB  # noqa: F401
from core.storage.repair_model_db import RepairDB  # noqa: F401
from core.storage.service_model_db import ServiceDB  # noqa: F401


def init_database():
    Base.metadata.create_all(bind=engine)
