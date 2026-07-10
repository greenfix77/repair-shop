import re
from datetime import datetime
from typing import List, Dict, Optional

from core.storage.database import SessionLocal
from core.storage.part_model_db import PartDB


class PartRepository:
    def create(self, data: Dict) -> Dict:
        session = SessionLocal()
        try:
            now = datetime.now()
            row = PartDB(
                part_code=data.get('part_code', ''),
                name=data.get('name', ''),
                purchase_price=data.get('purchase_price', 0),
                sale_price=data.get('sale_price', 0),
                stock_quantity=data.get('stock_quantity', 0),
                description=data.get('description', ''),
                is_active=data.get('is_active', True),
                created_at=now,
                updated_at=now,
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            return self._to_dict(row)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def update(self, part_id: int, data: Dict) -> Optional[Dict]:
        session = SessionLocal()
        try:
            row = session.query(PartDB).filter_by(id=part_id).first()
            if not row:
                return None
            for key in ('part_code', 'name', 'purchase_price', 'sale_price',
                        'stock_quantity', 'description', 'is_active'):
                if key in data:
                    setattr(row, key, data[key])
            row.updated_at = datetime.now()
            session.commit()
            session.refresh(row)
            return self._to_dict(row)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def delete(self, part_id: int) -> bool:
        session = SessionLocal()
        try:
            row = session.query(PartDB).filter_by(id=part_id).first()
            if not row:
                return False
            session.delete(row)
            session.commit()
            return True
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get(self, part_id: int) -> Optional[Dict]:
        session = SessionLocal()
        try:
            row = session.query(PartDB).filter_by(id=part_id).first()
            return self._to_dict(row) if row else None
        finally:
            session.close()

    def list_all(self, active_only: bool = False) -> List[Dict]:
        session = SessionLocal()
        try:
            query = session.query(PartDB)
            if active_only:
                query = query.filter_by(is_active=True)
            rows = query.all()
            return [self._to_dict(row) for row in rows]
        finally:
            session.close()

    def search(self, query: str) -> List[Dict]:
        session = SessionLocal()
        try:
            pattern = f'%{query}%'
            rows = session.query(PartDB).filter(
                PartDB.name.ilike(pattern) |
                PartDB.part_code.ilike(pattern)
            ).all()
            return [self._to_dict(row) for row in rows]
        finally:
            session.close()

    def generate_part_code(self) -> str:
        parts = self.list_all()
        max_num = 0
        for p in parts:
            code = p.get('part_code', '')
            match = re.search(r'P(\d+)', code)
            if match:
                num = int(match.group(1))
                if num > max_num:
                    max_num = num
        return f"P{max_num + 1:06d}"

    @staticmethod
    def _to_dict(row: PartDB) -> Dict:
        return {
            'id': row.id,
            'part_code': row.part_code or '',
            'name': row.name or '',
            'purchase_price': row.purchase_price or 0,
            'sale_price': row.sale_price or 0,
            'stock_quantity': row.stock_quantity or 0,
            'description': row.description or '',
            'is_active': row.is_active if row.is_active is not None else True,
            'created_at': row.created_at.isoformat() if row.created_at else '',
            'updated_at': row.updated_at.isoformat() if row.updated_at else '',
        }
