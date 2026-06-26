from core.storage.init_db import init_database
from core.storage.customer_repository import CustomerRepository


def test_customer_repository():
    init_database()
    repo = CustomerRepository()

    # Create
    customer = repo.create({
        'customer_code': 'C001',
        'full_name': 'John Doe',
        'phone': '1234567890',
        'email': 'john@example.com',
        'website': '',
        'national_id': 'ID001',
        'address': '123 Main St',
        'city': 'Springfield',
        'province': 'IL',
        'postal_code': '62701',
        'notes': 'Test customer',
        'created_at': '2025-01-01',
        'updated_at': '2025-01-01',
    })
    assert customer['id'] > 0, "create: should return customer with id"
    assert customer['full_name'] == 'John Doe', "create: full_name mismatch"
    print(f"[PASS] create -> id={customer['id']}, name={customer['full_name']}")

    # Find by phone
    found = repo.get_by_phone('1234567890')
    assert found is not None, "get_by_phone: should find customer"
    assert found['id'] == customer['id'], "get_by_phone: id mismatch"
    print(f"[PASS] get_by_phone -> found {found['full_name']}")

    # Find by code
    found = repo.get_by_code('C001')
    assert found is not None, "get_by_code: should find customer"
    assert found['id'] == customer['id'], "get_by_code: id mismatch"
    print(f"[PASS] get_by_code -> found {found['full_name']}")

    # Find by id
    found = repo.get_by_id(customer['id'])
    assert found is not None, "get_by_id: should find customer"
    assert found['id'] == customer['id'], "get_by_id: id mismatch"
    print(f"[PASS] get_by_id -> found {found['full_name']}")

    # Exists checks
    assert repo.exists_by_phone('1234567890') is True, "exists_by_phone: should be True"
    assert repo.exists_by_phone('0000000000') is False, "exists_by_phone: should be False"
    assert repo.exists_by_code('C001') is True, "exists_by_code: should be True"
    assert repo.exists_by_code('X999') is False, "exists_by_code: should be False"
    print("[PASS] exists_by_phone / exists_by_code")

    # Update
    updated = repo.update(customer['id'], {'full_name': 'John Updated'})
    assert updated is not None, "update: should return customer"
    assert updated['full_name'] == 'John Updated', "update: name should be updated"
    print(f"[PASS] update -> name={updated['full_name']}")

    # List all
    all_customers = repo.get_all()
    assert len(all_customers) >= 1, "get_all: should have at least 1 customer"
    print(f"[PASS] get_all -> {len(all_customers)} customer(s)")

    # Delete
    deleted = repo.delete(customer['id'])
    assert deleted is True, "delete: should return True"
    assert repo.get_by_id(customer['id']) is None, "delete: should no longer exist"
    print(f"[PASS] delete -> removed id={customer['id']}")

    print("\nAll tests passed!")


if __name__ == '__main__':
    test_customer_repository()
