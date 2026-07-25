from typing import List, Dict, Optional

from core.storage.part_repository import PartRepository


class PartService:
    """Business logic layer for parts catalog operations."""

    def __init__(self):
        self._repo = PartRepository()

    def _validate(self, data: Dict):
        name = data.get('name', '').strip()
        if not name:
            raise ValueError("نام قطعه الزامی است.")
        data['name'] = name

        for field in ('purchase_price', 'sale_price', 'default_sale_price',
                      'stock_quantity'):
            value = data.get(field, 0)
            try:
                value = int(value)
            except (TypeError, ValueError):
                raise ValueError(f"{field} باید عدد باشد.")
            if value < 0:
                raise ValueError("قیمت یا موجودی نمی‌تواند منفی باشد.")
            data[field] = value

    def create_part(self, data: Dict) -> Dict:
        """Create a new part with validation."""
        self._validate(data)
        data['part_code'] = self._repo.generate_part_code()
        return self._repo.create(data)

    def update_part(self, part_id: int, data: Dict) -> Optional[Dict]:
        """Update an existing part with validation."""
        self._validate(data)
        return self._repo.update(part_id, data)

    def delete_part(self, part_id: int) -> bool:
        """Delete a part by primary key."""
        return self._repo.delete(part_id)

    def get_part(self, part_id: int) -> Optional[Dict]:
        """Get a single part by primary key."""
        return self._repo.get(part_id)

    def list_all(self, active_only: bool = False) -> List[Dict]:
        """Return all parts, optionally filtered to active only."""
        return self._repo.list_all(active_only)

    def search(self, query: str) -> List[Dict]:
        """Search parts by name or code (contains, case-insensitive)."""
        if not query or len(query) < 1:
            return self._repo.list_all()
        return self._repo.search(query)

    def get_active_for_invoice(self) -> List[Dict]:
        """Return active parts for future invoice line-item selection."""
        return self._repo.list_all(active_only=True)

    def find_by_code(self, part_code: str) -> Optional[Dict]:
        """Find a part by its code (for future invoice integration)."""
        parts = self._repo.search(part_code)
        for p in parts:
            if p.get('part_code', '').strip() == part_code.strip():
                return p
        return None
