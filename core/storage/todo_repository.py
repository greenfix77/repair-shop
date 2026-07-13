from typing import List, Dict, Optional

from core.storage.database import SessionLocal
from core.storage.todo_model_db import TodoDB


class TodoRepository:
    _FIELDS = ('title', 'description', 'due_date', 'priority', 'is_done',
               'created_at', 'updated_at')

    def create(self, data: Dict) -> Dict:
        session = SessionLocal()
        try:
            row = TodoDB(
                title=data.get('title', ''),
                description=data.get('description', ''),
                due_date=data.get('due_date', ''),
                priority=data.get('priority', 'معمولی'),
                is_done=data.get('is_done', False),
                created_at=data.get('created_at', ''),
                updated_at=data.get('updated_at', ''),
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

    def update(self, todo_id: int, data: Dict) -> Optional[Dict]:
        session = SessionLocal()
        try:
            row = session.query(TodoDB).filter_by(id=todo_id).first()
            if not row:
                return None
            for key in self._FIELDS:
                if key in data:
                    setattr(row, key, data[key])
            session.commit()
            session.refresh(row)
            return self._to_dict(row)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def delete(self, todo_id: int) -> bool:
        session = SessionLocal()
        try:
            row = session.query(TodoDB).filter_by(id=todo_id).first()
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

    def get(self, todo_id: int) -> Optional[Dict]:
        session = SessionLocal()
        try:
            row = session.query(TodoDB).filter_by(id=todo_id).first()
            return self._to_dict(row) if row else None
        finally:
            session.close()

    def list_all(self, done_only: Optional[bool] = None) -> List[Dict]:
        session = SessionLocal()
        try:
            query = session.query(TodoDB)
            if done_only is True:
                query = query.filter_by(is_done=True)
            elif done_only is False:
                query = query.filter_by(is_done=False)
            rows = query.all()
            return [self._to_dict(row) for row in rows]
        finally:
            session.close()

    def search(self, query: str) -> List[Dict]:
        session = SessionLocal()
        try:
            pattern = f'%{query}%'
            rows = session.query(TodoDB).filter(
                TodoDB.title.ilike(pattern) |
                TodoDB.description.ilike(pattern)
            ).all()
            return [self._to_dict(row) for row in rows]
        finally:
            session.close()

    def get_due_today(self, today: str) -> List[Dict]:
        session = SessionLocal()
        try:
            rows = session.query(TodoDB).filter_by(due_date=today, is_done=False).all()
            return [self._to_dict(row) for row in rows]
        finally:
            session.close()

    def get_pending(self) -> List[Dict]:
        return self.list_all(done_only=False)

    def get_completed(self) -> List[Dict]:
        return self.list_all(done_only=True)

    @staticmethod
    def _to_dict(row: TodoDB) -> Dict:
        return {
            'id': row.id,
            'title': row.title or '',
            'description': row.description or '',
            'due_date': row.due_date or '',
            'priority': row.priority or 'معمولی',
            'is_done': row.is_done if row.is_done is not None else False,
            'created_at': row.created_at or '',
            'updated_at': row.updated_at or '',
        }
