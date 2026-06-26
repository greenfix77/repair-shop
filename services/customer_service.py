import re
from typing import List, Dict, Optional

from core.storage.customer_repository import CustomerRepository


class CustomerService:
    def __init__(self):
        self._repo = CustomerRepository()

    def get_or_create_customer(self, customer_data: Dict) -> Dict:
        phone = customer_data.get('phone', '')
        if phone:
            existing = self._repo.get_by_phone(phone)
            if existing:
                return existing
        customer_code = self._generate_code()
        customer_data['customer_code'] = customer_code
        return self._repo.create(customer_data)

    def find_by_phone(self, phone: str) -> Optional[Dict]:
        return self._repo.get_by_phone(phone)

    def find_by_code(self, code: str) -> Optional[Dict]:
        return self._repo.get_by_code(code)

    def update_customer(self, customer_id: int, customer_data: Dict) -> Optional[Dict]:
        return self._repo.update(customer_id, customer_data)

    def get_all_customers(self) -> List[Dict]:
        return self._repo.get_all()

    def _generate_code(self) -> str:
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
