from core.storage.database import Base, engine
from core.storage.customer_model_db import CustomerDB  # noqa: F401
from core.storage.repair_model_db import RepairDB  # noqa: F401
from core.storage.service_model_db import ServiceDB  # noqa: F401
from core.storage.part_model_db import PartDB  # noqa: F401
from core.storage.repair_service_model_db import RepairServiceDB  # noqa: F401
from core.storage.repair_part_model_db import RepairPartDB  # noqa: F401
from core.storage.todo_model_db import TodoDB  # noqa: F401


def init_database():
    Base.metadata.create_all(bind=engine)
    _migrate_repair_columns()


def _migrate_repair_columns():
    """Add new columns to existing repairs table if they don't exist."""
    from sqlalchemy import inspect, text
    inspector = inspect(engine)
    if 'repairs' not in inspector.get_table_names():
        return
    columns = [c['name'] for c in inspector.get_columns('repairs')]
    new_columns = [
        ('paid_amount', 'INTEGER DEFAULT 0'),
        ('payment_status', "TEXT DEFAULT 'پرداخت نشده'"),
        ('financial_notes', 'TEXT DEFAULT ""'),
    ]
    with engine.connect() as conn:
        for col_name, col_def in new_columns:
            if col_name not in columns:
                conn.execute(text(f"ALTER TABLE repairs ADD COLUMN {col_name} {col_def}"))
        conn.commit()
