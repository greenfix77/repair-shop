from typing import List, Dict, Optional

from core.storage.database import SessionLocal
from core.storage.customer_model_db import CustomerDB


class CustomerRepository:
    def get_all(self) -> List[Dict]:
        session = SessionLocal()
        try:
            rows = session.query(CustomerDB).all()
            return [self._to_dict(row) for row in rows]
        finally:
            session.close()

    def get_by_id(self, customer_id: int) -> Optional[Dict]:
        session = SessionLocal()
        try:
            row = session.query(CustomerDB).filter_by(id=customer_id).first()
            return self._to_dict(row) if row else None
        finally:
            session.close()

    def get_by_code(self, customer_code: str) -> Optional[Dict]:
        session = SessionLocal()
        try:
            row = session.query(CustomerDB).filter_by(customer_code=customer_code).first()
            return self._to_dict(row) if row else None
        finally:
            session.close()

    def get_by_phone(self, phone: str) -> Optional[Dict]:
        session = SessionLocal()
        try:
            row = session.query(CustomerDB).filter_by(phone=phone).first()
            return self._to_dict(row) if row else None
        finally:
            session.close()

    def create(self, customer_data: Dict) -> Dict:
        session = SessionLocal()
        try:
            row = CustomerDB(
                customer_code=customer_data.get('customer_code', ''),
                full_name=customer_data.get('full_name', ''),
                phone=customer_data.get('phone', ''),
                email=customer_data.get('email', ''),
                website=customer_data.get('website', ''),
                national_id=customer_data.get('national_id', ''),
                address=customer_data.get('address', ''),
                city=customer_data.get('city', ''),
                province=customer_data.get('province', ''),
                postal_code=customer_data.get('postal_code', ''),
                notes=customer_data.get('notes', ''),
                created_at=customer_data.get('created_at', ''),
                updated_at=customer_data.get('updated_at', ''),
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

    def update(self, customer_id: int, customer_data: Dict) -> Optional[Dict]:
        session = SessionLocal()
        try:
            row = session.query(CustomerDB).filter_by(id=customer_id).first()
            if not row:
                return None
            for key in ('customer_code', 'full_name', 'phone', 'email', 'website',
                        'national_id', 'address', 'city', 'province', 'postal_code',
                        'notes', 'created_at', 'updated_at'):
                if key in customer_data:
                    setattr(row, key, customer_data[key])
            session.commit()
            session.refresh(row)
            return self._to_dict(row)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def delete(self, customer_id: int) -> bool:
        session = SessionLocal()
        try:
            row = session.query(CustomerDB).filter_by(id=customer_id).first()
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

    def exists_by_phone(self, phone: str) -> bool:
        session = SessionLocal()
        try:
            return session.query(CustomerDB).filter_by(phone=phone).first() is not None
        finally:
            session.close()

    def exists_by_code(self, customer_code: str) -> bool:
        session = SessionLocal()
        try:
            return session.query(CustomerDB).filter_by(customer_code=customer_code).first() is not None
        finally:
            session.close()

    @staticmethod
    def _to_dict(row: CustomerDB) -> Dict:
        return {
            'id': row.id,
            'customer_code': row.customer_code or '',
            'full_name': row.full_name or '',
            'phone': row.phone or '',
            'email': row.email or '',
            'website': row.website or '',
            'national_id': row.national_id or '',
            'address': row.address or '',
            'city': row.city or '',
            'province': row.province or '',
            'postal_code': row.postal_code or '',
            'notes': row.notes or '',
            'created_at': row.created_at or '',
            'updated_at': row.updated_at or '',
        }
