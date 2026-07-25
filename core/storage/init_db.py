from core.storage.database import Base, engine
from core.storage.customer_model_db import CustomerDB  # noqa: F401
from core.storage.repair_model_db import RepairDB  # noqa: F401
from core.storage.service_model_db import ServiceDB  # noqa: F401
from core.storage.part_model_db import PartDB  # noqa: F401
from core.storage.repair_service_model_db import RepairServiceDB  # noqa: F401
from core.storage.repair_part_model_db import RepairPartDB  # noqa: F401
from core.storage.todo_model_db import TodoDB  # noqa: F401
from core.storage.charge_model_db import ChargeDB  # noqa: F401
from core.storage.payment_transaction_model_db import PaymentTransactionDB  # noqa: F401


def init_database():
    Base.metadata.create_all(bind=engine)
    _migrate_repair_columns()
    _migrate_repair_part_columns()
    _migrate_part_columns()
    _migrate_repair_additional_charges()
    _migrate_legacy_payment_transactions()


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
        ('payment_method', "TEXT DEFAULT 'نقدی'"),
        ('payment_date', "TEXT DEFAULT ''"),
        ('financial_notes', 'TEXT DEFAULT ""'),
    ]
    with engine.connect() as conn:
        for col_name, col_def in new_columns:
            if col_name not in columns:
                conn.execute(text(f"ALTER TABLE repairs ADD COLUMN {col_name} {col_def}"))
        conn.commit()


def _migrate_repair_part_columns():
    """Add new columns to existing repair_part table if they don't exist."""
    from sqlalchemy import inspect, text
    inspector = inspect(engine)
    if 'repair_part' not in inspector.get_table_names():
        return
    columns = [c['name'] for c in inspector.get_columns('repair_part')]
    new_columns = [
        ('purchase_price_snapshot', 'INTEGER DEFAULT 0'),
    ]
    with engine.connect() as conn:
        for col_name, col_def in new_columns:
            if col_name not in columns:
                conn.execute(text(
                    f"ALTER TABLE repair_part ADD COLUMN {col_name} {col_def}"
                ))
        conn.commit()


def _migrate_part_columns():
    """Add new columns to existing part table if they don't exist."""
    from sqlalchemy import inspect, text
    inspector = inspect(engine)
    if 'part' not in inspector.get_table_names():
        return
    columns = [c['name'] for c in inspector.get_columns('part')]
    new_columns = [
        ('default_sale_price', 'INTEGER DEFAULT 0'),
    ]
    with engine.connect() as conn:
        for col_name, col_def in new_columns:
            if col_name not in columns:
                conn.execute(text(
                    f"ALTER TABLE part ADD COLUMN {col_name} {col_def}"
                ))
        conn.commit()


def _migrate_repair_additional_charges():
    """Add additional_charges_json column to existing repairs table if missing."""
    from sqlalchemy import inspect, text
    inspector = inspect(engine)
    if 'repairs' not in inspector.get_table_names():
        return
    columns = [c['name'] for c in inspector.get_columns('repairs')]
    if 'additional_charges_json' in columns:
        return
    with engine.connect() as conn:
        conn.execute(text(
            "ALTER TABLE repairs ADD COLUMN additional_charges_json TEXT DEFAULT '[]'"
        ))
        conn.execute(text(
            "UPDATE repairs SET additional_charges_json = '[]' "
            "WHERE additional_charges_json IS NULL OR additional_charges_json = ''"
        ))
        conn.commit()


def _migrate_legacy_payment_transactions():
    """Backfill one PAYMENT ledger row per existing repair with paid_amount > 0.

    Idempotent: each repair gets at most one legacy ledger row. Repair snapshot
    fields (paid_amount, payment_status, payment_method, payment_date) are never
    touched by this function.
    """
    from sqlalchemy import inspect
    inspector = inspect(engine)
    if 'repairs' not in inspector.get_table_names():
        return
    if 'payment_transaction' not in inspector.get_table_names():
        return

    from datetime import datetime
    from core.storage.database import SessionLocal
    from core.storage.repair_model_db import RepairDB
    from core.storage.payment_transaction_model_db import PaymentTransactionDB

    LEGACY_NOTE = "مهاجرت پرداخت قدیمی"
    LEGACY_TYPE = "PAYMENT"

    session = SessionLocal()
    try:
        try:
            repairs = session.query(RepairDB).all()
            for repair in repairs:
                paid = getattr(repair, 'paid_amount', 0) or 0
                if paid <= 0:
                    continue
                if repair.id is None:
                    continue
                existing = session.query(PaymentTransactionDB).filter_by(
                    repair_id=repair.id,
                    note=LEGACY_NOTE,
                ).first()
                if existing is not None:
                    continue
                session.add(PaymentTransactionDB(
                    repair_id=repair.id,
                    amount=paid,
                    payment_method=getattr(repair, 'payment_method', '') or '',
                    payment_date=getattr(repair, 'payment_date', '') or '',
                    transaction_type=LEGACY_TYPE,
                    created_at=datetime.now(),
                    note=LEGACY_NOTE,
                ))
            session.commit()
        except Exception:
            session.rollback()
            raise
    finally:
        session.close()
