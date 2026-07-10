from typing import List, Dict

from core.storage.database import SessionLocal
from core.storage.repair_model_db import RepairDB
from core.storage.repair_service_model_db import RepairServiceDB
from core.storage.repair_part_model_db import RepairPartDB
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
                repair_dict = {
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
                    'paid_amount': getattr(row, 'paid_amount', 0) or 0,
                    'payment_status': getattr(row, 'payment_status', '') or 'پرداخت نشده',
                    'financial_notes': getattr(row, 'financial_notes', '') or '',
                    'service_lines': [],
                    'part_lines': [],
                }

                svc_rows = session.query(RepairServiceDB).filter_by(
                    repair_id=row.id
                ).all()
                for s in svc_rows:
                    repair_dict['service_lines'].append({
                        'id': s.id,
                        'service_id': s.service_id,
                        'service_name_snapshot': s.service_name_snapshot or '',
                        'quantity': s.quantity or 1,
                        'unit_price': s.unit_price or 0,
                        'total_price': s.total_price or 0,
                    })

                part_rows = session.query(RepairPartDB).filter_by(
                    repair_id=row.id
                ).all()
                for p in part_rows:
                    repair_dict['part_lines'].append({
                        'id': p.id,
                        'part_id': p.part_id,
                        'part_name_snapshot': p.part_name_snapshot or '',
                        'quantity': p.quantity or 1,
                        'unit_price': p.unit_price or 0,
                        'total_price': p.total_price or 0,
                    })

                result.append(repair_dict)
            return result
        finally:
            session.close()

    def save_all(self, repairs: List[Dict]) -> None:
        session = SessionLocal()
        try:
            session.query(RepairServiceDB).delete()
            session.query(RepairPartDB).delete()
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
                    paid_amount=item.get('paid_amount', 0),
                    payment_status=item.get('payment_status', 'پرداخت نشده'),
                    financial_notes=item.get('financial_notes', ''),
                )
                session.add(row)

                for svc in item.get('service_lines', []):
                    svc_row = RepairServiceDB(
                        repair_id=item.get('id', 0),
                        service_id=svc.get('service_id'),
                        service_name_snapshot=svc.get('service_name_snapshot', ''),
                        quantity=svc.get('quantity', 1),
                        unit_price=svc.get('unit_price', 0),
                        total_price=svc.get('total_price', 0),
                    )
                    session.add(svc_row)

                for prt in item.get('part_lines', []):
                    part_row = RepairPartDB(
                        repair_id=item.get('id', 0),
                        part_id=prt.get('part_id'),
                        part_name_snapshot=prt.get('part_name_snapshot', ''),
                        quantity=prt.get('quantity', 1),
                        unit_price=prt.get('unit_price', 0),
                        total_price=prt.get('total_price', 0),
                    )
                    session.add(part_row)

            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
