from datetime import datetime
from typing import List, Dict, Optional

from core.storage.todo_repository import TodoRepository

VALID_PRIORITIES = {"کم", "معمولی", "زیاد", "فوری"}


class TodoService:
    """Business logic layer for todo operations."""

    def __init__(self):
        self._repo = TodoRepository()

    def _validate(self, data: Dict):
        title = data.get('title', '').strip()
        if not title:
            raise ValueError("عنوان الزامی است.")
        data['title'] = title

        priority = data.get('priority', 'معمولی').strip()
        if priority not in VALID_PRIORITIES:
            raise ValueError("اولویت باید یکی از مقادیر: کم، معمولی، زیاد، فوری باشد.")
        data['priority'] = priority

    def _timestamps(self, data: Dict):
        now = datetime.now().isoformat()
        if 'created_at' not in data:
            data['created_at'] = now
        data['updated_at'] = now

    def create_todo(self, data: Dict) -> Dict:
        """Create a new todo with validation."""
        self._validate(data)
        self._timestamps(data)
        return self._repo.create(data)

    def update_todo(self, todo_id: int, data: Dict) -> Optional[Dict]:
        """Update an existing todo with validation."""
        self._validate(data)
        self._timestamps(data)
        return self._repo.update(todo_id, data)

    def delete_todo(self, todo_id: int) -> bool:
        """Delete a todo by primary key."""
        return self._repo.delete(todo_id)

    def get_todo(self, todo_id: int) -> Optional[Dict]:
        """Get a single todo by primary key."""
        return self._repo.get(todo_id)

    def list_all(self, done_only: Optional[bool] = None) -> List[Dict]:
        """Return all todos, optionally filtered by completion status."""
        return self._repo.list_all(done_only)

    def search(self, query: str) -> List[Dict]:
        """Search todos by title or description (contains, case-insensitive)."""
        if not query or len(query) < 1:
            return self._repo.list_all()
        return self._repo.search(query)

    def get_due_today(self, today: str) -> List[Dict]:
        """Return pending todos due on a specific date string.

        Compare with normalized whitespace-trimmed equality so legacy records
        with stray leading/trailing spaces still match today's date.
        """
        target = (today or '').strip()
        return [
            t for t in self._repo.list_all(done_only=False)
            if (t.get('due_date', '') or '').strip() == target
        ]

    def count_due_today(self, today: str) -> int:
        """Return number of pending todos due on the given date string.

        Thin aggregate over :meth:`get_due_today`. Used by
        DashboardService — no business rules duplicated.
        """
        return len(self.get_due_today(today))

    def get_pending(self) -> List[Dict]:
        """Return all pending (not done) todos."""
        return self._repo.get_pending()

    def get_completed(self) -> List[Dict]:
        """Return all completed (done) todos."""
        return self._repo.get_completed()

    def mark_done(self, todo_id: int) -> Optional[Dict]:
        """Mark a todo as done."""
        return self._repo.update(todo_id, {'is_done': True})

    def mark_pending(self, todo_id: int) -> Optional[Dict]:
        """Mark a todo as pending (not done)."""
        return self._repo.update(todo_id, {'is_done': False})