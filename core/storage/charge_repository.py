from datetime import datetime
from typing import List, Dict, Optional

from core.storage.database import SessionLocal
from core.storage.charge_model_db import ChargeDB


class ChargeRepository:
    def create(self, data: Dict) -> Dict:
        session = SessionLocal()
        try:
            now = datetime.now()
            row = ChargeDB(
                name=data.get('name', ''),
                category=data.get('category', ''),
                default_amount=data.get('default_amount', 0),
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

    def update(self, charge_id: int, data: Dict) -> Optional[Dict]:
        session = SessionLocal()
        try:
            row = session.query(ChargeDB).filter_by(id=charge_id).first()
            if not row:
                return None
            for key in ('name', 'category', 'default_amount',
                        'description', 'is_active'):
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

    def delete(self, charge_id: int) -> bool:
        session = SessionLocal()
        try:
            row = session.query(ChargeDB).filter_by(id=charge_id).first()
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

    def get(self, charge_id: int) -> Optional[Dict]:
        session = SessionLocal()
        try:
            row = session.query(ChargeDB).filter_by(id=charge_id).first()
            return self._to_dict(row) if row else None
        finally:
            session.close()

    def list_all(self, active_only: bool = False) -> List[Dict]:
        session = SessionLocal()
        try:
            query = session.query(ChargeDB)
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
            rows = session.query(ChargeDB).filter(
                ChargeDB.name.ilike(pattern) |
                ChargeDB.category.ilike(pattern)
            ).all()
            return [self._to_dict(row) for row in rows]
        finally:
            session.close()

    @staticmethod
    def _to_dict(row: ChargeDB) -> Dict:
        return {
            'id': row.id,
            'name': row.name or '',
            'category': row.category or '',
            'default_amount': row.default_amount or 0,
            'description': row.description or '',
            'is_active': row.is_active if row.is_active is not None else True,
            'created_at': row.created_at.isoformat() if row.created_at else '',
            'updated_at': row.updated_at.isoformat() if row.updated_at else '',
        }
