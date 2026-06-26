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
        customer_data['customer_code'] = self.generate_customer_code()
        return self._repo.create(customer_data)

    def find_customer(self, query: str) -> Optional[Dict]:
        result = self._repo.get_by_phone(query)
        if result:
            return result
        return self._repo.get_by_code(query)

    def update_customer(self, customer_id: int, data: Dict) -> Optional[Dict]:
        return self._repo.update(customer_id, data)

    def get_all_customers(self) -> List[Dict]:
        return self._repo.get_all()

    def generate_customer_code(self) -> str:
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
