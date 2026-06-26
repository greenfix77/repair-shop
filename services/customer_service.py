import re
from typing import List, Dict, Optional

from core.storage.customer_repository import CustomerRepository


class CustomerService:
    """Business logic layer for customer operations.

    All customer business rules live here. Repository handles data access only.
    """

    def __init__(self):
        self._repo = CustomerRepository()

    def get_or_create_customer(self, customer_data: Dict) -> Dict:
        """Return existing customer by phone, or create a new one.

        Validates phone presence, prevents duplicate phones,
        and auto-generates customer_code for new records.
        """
        phone = customer_data.get('phone', '')
        if not phone:
            raise ValueError("Phone number is required")
        existing = self._repo.get_by_phone(phone)
        if existing:
            return existing
        customer_data['customer_code'] = self.generate_customer_code()
        return self._repo.create(customer_data)

    def find_customer(self, query: str) -> Optional[Dict]:
        """Find a single customer by phone or customer_code.

        Designed for future extension: additional search fields
        (name, email, serial_number, repair_id, notes, etc.) can be
        added here without changing any caller.
        """
        result = self._repo.get_by_phone(query)
        if result:
            return result
        result = self._repo.get_by_code(query)
        if result:
            return result
        return None

    def find_by_phone(self, phone: str) -> Optional[Dict]:
        if not phone:
            return None
        return self._repo.get_by_phone(phone)

    def find_by_full_name(self, full_name: str) -> Optional[Dict]:
        if not full_name:
            return None
        customers = self._repo.search(full_name)
        for c in customers:
            if c.get('full_name', '').strip() == full_name.strip():
                return c
        return None

    def search_customers(self, query: str) -> List[Dict]:
        """Search customers by full_name or phone (contains, case-insensitive).

        Designed for future extension: additional fields (customer_code,
        email, serial_number, repair_id, notes) can be added here
        without changing callers.
        """
        if not query or len(query) < 2:
            return []
        return self._repo.search(query)

    def get_customer(self, customer_id: int) -> Optional[Dict]:
        """Get a single customer by primary key."""
        return self._repo.get_by_id(customer_id)

    def update_customer(self, customer_id: int, data: Dict) -> Optional[Dict]:
        """Update customer fields. Returns updated dict or None if not found."""
        return self._repo.update(customer_id, data)

    def create_customer(self, customer_data: Dict) -> Dict:
        customer_data['customer_code'] = self.generate_customer_code()
        return self._repo.create(customer_data)

    def get_all_customers(self) -> List[Dict]:
        """Return every customer as a list of dicts."""
        return self._repo.get_all()

    def generate_customer_code(self) -> str:
        """Return the next customer_code in C000001, C000002, … format."""
        customers = self._repo.get_all()
        max_num = 0
        for c in customers:
            code = c.get('customer_code', '')
            match = re.search(r'C(\d+)', code)
            if match:
                num = int(match.group(1))
                if num > max_num:
                    max_num = num
        return f"C{max_num + 1:06d}"
