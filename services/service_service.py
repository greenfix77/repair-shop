from typing import List, Dict, Optional

from core.storage.service_repository import ServiceRepository


class ServiceService:
    """Business logic layer for service catalog operations."""

    def __init__(self):
        self._repo = ServiceRepository()

    def create_service(self, data: Dict) -> Dict:
        """Create a new service with validation."""
        name = data.get('name', '').strip()
        if not name:
            raise ValueError("نام خدمت الزامی است.")
        data['name'] = name

        price = data.get('default_price', 0)
        try:
            price = int(price)
        except (TypeError, ValueError):
            raise ValueError("قیمت پیش‌فرض باید عدد باشد.")
        if price < 0:
            raise ValueError("قیمت پیش‌فرض نمی‌تواند منفی باشد.")
        data['default_price'] = price

        data['service_code'] = self._repo.generate_service_code()
        return self._repo.create(data)

    def update_service(self, service_id: int, data: Dict) -> Optional[Dict]:
        """Update an existing service with validation."""
        name = data.get('name', '').strip()
        if not name:
            raise ValueError("نام خدمت الزامی است.")
        data['name'] = name

        price = data.get('default_price', 0)
        try:
            price = int(price)
        except (TypeError, ValueError):
            raise ValueError("قیمت پیش‌فرض باید عدد باشد.")
        if price < 0:
            raise ValueError("قیمت پیش‌فرض نمی‌تواند منفی باشد.")
        data['default_price'] = price

        return self._repo.update(service_id, data)

    def delete_service(self, service_id: int) -> bool:
        """Delete a service by primary key."""
        return self._repo.delete(service_id)

    def get_service(self, service_id: int) -> Optional[Dict]:
        """Get a single service by primary key."""
        return self._repo.get(service_id)

    def list_all(self, active_only: bool = False) -> List[Dict]:
        """Return all services, optionally filtered to active only."""
        return self._repo.list_all(active_only)

    def search(self, query: str) -> List[Dict]:
        """Search services by name or code (contains, case-insensitive)."""
        if not query or len(query) < 1:
            return self._repo.list_all()
        return self._repo.search(query)
