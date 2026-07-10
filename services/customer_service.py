import re
from typing import List, Dict, Optional

from core.storage.customer_repository import CustomerRepository


class CustomerService:
    """Business logic layer for customer operations.

    All customer business rules live here. Repository handles data access only.
    """

    def __init__(self):
        self._repo = CustomerRepository()

    def resolve_customer(self, customer_data: Dict, confirm_callback=None) -> Optional[Dict]:
        """Single entry point for all customer resolution.

        Decision order:
          1. Normalize input (trim whitespace, convert empty to None).
          2. Phone lookup — if phone present, search by phone and return
             existing immediately. Never create from this path.
          3. No phone — skip phone lookup. Continue with name resolution.
          4. Exact name match — if found, ask user to reuse. If yes,
             return existing. If no, continue.
          5. Similar names — search with LIKE. If similar names exist,
             show confirmation. User may continue or cancel.
          6. Only then — create a new customer.

        Args:
            customer_data: Form data dict with customer fields.
            confirm_callback: Optional callable(title, message) -> bool.
                              Return True to confirm/reuse, False to decline.

        Returns:
            Customer dict (existing or newly created), or None if no
            identifying data was provided or user cancelled.
        """
        phone = customer_data.get('phone', '').strip()
        full_name = customer_data.get('full_name', '').strip()

        if not phone:
            phone = None
            customer_data['phone'] = ''

        if not full_name:
            full_name = None

        if not phone and not full_name:
            return None

        if phone:
            existing = self._repo.get_by_phone(phone)
            if existing:
                return existing

        if full_name:
            exact = self.find_by_full_name(full_name)
            if exact:
                existing = exact[0]
                if confirm_callback:
                    confirmed = confirm_callback(
                        "مشتری مشابه",
                        "مشتری مشابهی وجود دارد.\nاز همان مشتری استفاده شود؟"
                    )
                    if confirmed:
                        return existing
                else:
                    return existing

            similar = self._repo.search(full_name)
            similar = [
                c for c in similar
                if c.get('full_name', '').strip() != full_name
            ]
            if similar:
                if confirm_callback:
                    names = '\n'.join(
                        c.get('full_name', '') for c in similar[:5]
                    )
                    proceed = confirm_callback(
                        "نام‌های مشابه",
                        f"نام‌های مشابهی یافت شد:\n{names}\n\nآیا ادامه می‌دهید؟"
                    )
                    if not proceed:
                        return None

        customer_data['customer_code'] = self.generate_customer_code()
        return self._repo.create(customer_data)

    def find_customer(self, query: str) -> Optional[Dict]:
        """Find a single customer by phone."""
        if not query:
            return None
        return self._repo.get_by_phone(query)

    def find_by_full_name(self, full_name: str) -> List[Dict]:
        if not full_name:
            return []
        customers = self._repo.search(full_name)
        result = []
        for c in customers:
            if c.get('full_name', '').strip() == full_name.strip():
                result.append(c)
        return result

    def check_create_duplicate(self, customer_data: Dict) -> Optional[str]:
        """Check for duplicates when creating a customer from management UI.

        Business rules:
          - Find existing customers with the same normalized full_name.
          - If none exist, allow creation.
          - If same-name customers exist:
              If entered phone (non-empty) matches any same-name customer's phone
              (normalized via repository logic), block with phone message.
              Else if entered national_id (non-empty) matches any same-name
              customer's national_id, block with national_id message.
              Else allow (different person, same name).

        Returns:
          Error message string if creation should be blocked, or None if allowed.
        """
        full_name = customer_data.get('full_name', '').strip()
        if not full_name:
            return None

        same_name = self.find_by_full_name(full_name)
        if not same_name:
            return None

        phone = customer_data.get('phone', '').strip()
        national_id = customer_data.get('national_id', '').strip()

        if phone:
            entered_phone = self._repo._normalize_phone(phone)
            for c in same_name:
                existing_raw = (c.get('phone') or '').strip()
                existing_phone = self._repo._normalize_phone(existing_raw)
                if entered_phone is not None and entered_phone == existing_phone:
                    return "مشتری با همین نام و شماره تلفن قبلاً ثبت شده است."

        if national_id:
            for c in same_name:
                existing_nid = (c.get('national_id') or '').strip()
                if existing_nid and existing_nid == national_id:
                    return "مشتری با همین نام و کد ملی قبلاً ثبت شده است."

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

    def update_customer(self, customer_id: int, customer_data: Dict) -> Optional[Dict]:
        """Update an existing customer's data."""
        return self._repo.update(customer_id, customer_data)

    def create_customer(self, customer_data: Dict) -> Dict:
        """Create a new customer without duplicate detection (conscious clone path)."""
        customer_data['customer_code'] = self.generate_customer_code()
        return self._repo.create(customer_data)

    def get_all_customers(self) -> List[Dict]:
        """Return all customers (for management views)."""
        return self._repo.get_all()

    def delete_customer(self, customer_id: int) -> bool:
        """Delete a customer by primary key."""
        return self._repo.delete(customer_id)

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
