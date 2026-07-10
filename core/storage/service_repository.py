import re
from datetime import datetime
from typing import List, Dict, Optional

from core.storage.database import SessionLocal
from core.storage.service_model_db import ServiceDB


class ServiceRepository:
    def create(self, data: Dict) -> Dict:
        session = SessionLocal()
        try:
            now = datetime.now()
            row = ServiceDB(
                service_code=data.get('service_code', ''),
                name=data.get('name', ''),
                default_price=data.get('default_price', 0),
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

    def update(self, service_id: int, data: Dict) -> Optional[Dict]:
        session = SessionLocal()
        try:
            row = session.query(ServiceDB).filter_by(id=service_id).first()
            if not row:
                return None
            for key in ('service_code', 'name', 'default_price', 'description',
                        'is_active'):
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

    def delete(self, service_id: int) -> bool:
        session = SessionLocal()
        try:
            row = session.query(ServiceDB).filter_by(id=service_id).first()
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

    def get(self, service_id: int) -> Optional[Dict]:
        session = SessionLocal()
        try:
            row = session.query(ServiceDB).filter_by(id=service_id).first()
            return self._to_dict(row) if row else None
        finally:
            session.close()

    def list_all(self, active_only: bool = False) -> List[Dict]:
        session = SessionLocal()
        try:
            query = session.query(ServiceDB)
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
            rows = session.query(ServiceDB).filter(
                ServiceDB.name.ilike(pattern) |
                ServiceDB.service_code.ilike(pattern)
            ).all()
            return [self._to_dict(row) for row in rows]
        finally:
            session.close()

    def generate_service_code(self) -> str:
        services = self.list_all()
        max_num = 0
        for s in services:
            code = s.get('service_code', '')
            match = re.search(r'S(\d+)', code)
            if match:
                num = int(match.group(1))
                if num > max_num:
                    max_num = num
        return f"S{max_num + 1:06d}"

    @staticmethod
    def _to_dict(row: ServiceDB) -> Dict:
        return {
            'id': row.id,
            'service_code': row.service_code or '',
            'name': row.name or '',
            'default_price': row.default_price or 0,
            'description': row.description or '',
            'is_active': row.is_active if row.is_active is not None else True,
            'created_at': row.created_at.isoformat() if row.created_at else '',
            'updated_at': row.updated_at.isoformat() if row.updated_at else '',
        }
