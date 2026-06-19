from typing import List, Dict

from core.storage.database import SessionLocal
from core.storage.repair_model_db import RepairDB
from core.storage.init_db import init_database


class SQLiteStorage:
    def __init__(self):
        init_database()

    def load_all(self) -> List[Dict]:
        session = SessionLocal()
        try:
            rows = session.query(RepairDB).all()
            result = []
            for row in rows:
                result.append({
                    'id': row.id,
                    'customer_name': row.customer_name or '',
                    'phone': row.phone or '',
                    'brand': row.brand or '',
                    'model': row.model or '',
                    'issue': row.issue or '',
                    'parts_cost': row.parts_cost or 0,
                    'labor_cost': row.labor_cost or 0,
                    'tax': row.tax or 0.0,
                    'discount': row.discount or 0,
                    'status': row.status or '',
                    'receive_date': row.receive_date or '',
                    'delivery_date': row.delivery_date or '',
                    'notes': row.notes or '',
                    'warranty': row.warranty or '',
                })
            return result
        finally:
            session.close()

    def save_all(self, repairs: List[Dict]) -> None:
        session = SessionLocal()
        try:
            session.query(RepairDB).delete()
            for item in repairs:
                row = RepairDB(
                    id=item.get('id', 0),
                    customer_name=item.get('customer_name', ''),
                    phone=item.get('phone', ''),
                    brand=item.get('brand', ''),
                    model=item.get('model', ''),
                    issue=item.get('issue', ''),
                    parts_cost=item.get('parts_cost', 0),
                    labor_cost=item.get('labor_cost', 0),
                    tax=float(item.get('tax', 0)),
                    discount=item.get('discount', 0),
                    status=item.get('status', ''),
                    receive_date=item.get('receive_date', ''),
                    delivery_date=item.get('delivery_date', ''),
                    notes=item.get('notes', ''),
                    warranty=item.get('warranty', ''),
                )
                session.add(row)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
