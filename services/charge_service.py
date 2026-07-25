from typing import List, Dict, Optional

from core.storage.charge_repository import ChargeRepository


class ChargeService:
    """Business logic layer for the Charges Catalog."""

    def __init__(self):
        self._repo = ChargeRepository()

    def _validate(self, data: Dict):
        name = data.get('name', '').strip()
        if not name:
            raise ValueError("نام هزینه الزامی است.")
        data['name'] = name

        value = data.get('default_amount', 0)
        try:
            value = int(value)
        except (TypeError, ValueError):
            raise ValueError("مبلغ پیش‌فرض باید عدد باشد.")
        if value < 0:
            raise ValueError("مبلغ نمی‌تواند منفی باشد.")
        data['default_amount'] = value

    def create_charge(self, data: Dict) -> Dict:
        """Create a new charge with validation."""
        self._validate(data)
        return self._repo.create(data)

    def update_charge(self, charge_id: int, data: Dict) -> Optional[Dict]:
        """Update an existing charge with validation."""
        self._validate(data)
        return self._repo.update(charge_id, data)

    def delete_charge(self, charge_id: int) -> bool:
        return self._repo.delete(charge_id)

    def get_charge(self, charge_id: int) -> Optional[Dict]:
        return self._repo.get(charge_id)

    def list_all(self, active_only: bool = False) -> List[Dict]:
        return self._repo.list_all(active_only)

    def search(self, query: str) -> List[Dict]:
        if not query or len(query) < 1:
            return self._repo.list_all()
        return self._repo.search(query)
