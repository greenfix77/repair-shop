from typing import List, Dict, Optional

from services.customer_service import CustomerService


class CustomerWorkflow:
    """Single execution path for all customer UI workflows.

    RepairDialog calls only this class for customer operations.
    No business logic lives in RepairDialog.
    No UI references live in CustomerService.

    Responsibilities:
    - Lookup by customer id (single source of truth for customer data)
    - Lookup by phone (auto-fill trigger)
    - Resolve customer on save (create-or-reuse with duplicate detection)
    - Populate all UI fields (single method, no duplicated widget manipulation)
    - Search customers (completer popup)
    """

    def __init__(self):
        self._service = CustomerService()

    def search_customers(self, query: str) -> List[Dict]:
        """Search customers for completer popup.

        Returns list of customer dicts with id set in Qt.UserRole by caller.
        """
        return self._service.search_customers(query)

    def get_customer(self, customer_id: int) -> Optional[Dict]:
        """Get a single customer by primary key.

        This is the SINGLE source of truth for loading customer data.
        Every customer selection path must go through this method.
        Never parse displayed text. Never split strings.
        """
        return self._service.get_customer(customer_id)

    def find_customer_by_phone(self, phone: str) -> Optional[Dict]:
        """Find customer by phone number (exact match).

        Returns the full customer dict. The caller extracts customer_id
        and calls get_customer() for a consistent load path.
        """
        return self._service.find_customer(phone)

    def resolve_customer(
        self, customer_data: Dict, confirm_callback=None
    ) -> Optional[Dict]:
        """Resolve customer on save: create-or-reuse with duplicate detection.

        This is the ONLY method that creates customers.
        No other code path may create customers directly.

        Args:
            customer_data: Form data dict with customer fields.
            confirm_callback: Callable(title, message) -> bool.

        Returns:
            Customer dict (existing or newly created), or None if
            no identifying data was provided or user cancelled.
        """
        return self._service.resolve_customer(customer_data, confirm_callback)

    def populate_fields(self, form, customer: Dict) -> None:
        """Populate all customer UI fields from a customer dict.

        This is the ONLY method that sets customer form fields.
        No other code may manipulate customer widgets directly.

        Args:
            form: The RepairDialog instance (provides widget references).
            customer: Customer dict with all fields.
        """
        form.customer_name_input.blockSignals(True)
        form.customer_name_input.setText(customer.get('full_name', ''))
        form.customer_name_input.blockSignals(False)
        form.phone_input.setText(customer.get('phone', ''))
        form.email_input.setText(customer.get('email', ''))
        form.website_input.setText(customer.get('website', ''))
        form.national_id_input.setText(customer.get('national_id', ''))
        form.address_input.setText(customer.get('address', ''))
        form.city_input.setText(customer.get('city', ''))
        form.province_input.setText(customer.get('province', ''))
        form.postal_code_input.setText(customer.get('postal_code', ''))
        form.notes_input.setPlainText(customer.get('notes', ''))
