from core.storage.init_db import init_database
from core.storage.customer_repository import CustomerRepository
from services.customer_service import CustomerService


def clean_customers():
    repo = CustomerRepository()
    for c in repo.get_all():
        repo.delete(c['id'])


def test_customer_service():
    init_database()
    clean_customers()

    service = CustomerService()
    now = '2025-01-01'

    # generate_customer_code before any customers
    assert service.generate_customer_code() == 'C000001'
    print("[PASS] generate_customer_code -> C000001")

    # Create first customer
    c1 = service.get_or_create_customer({
        'full_name': 'Alice',
        'phone': '1111111111',
        'email': 'alice@example.com',
        'created_at': now,
        'updated_at': now,
    })
    assert c1['customer_code'] == 'C000001', f"expected C000001, got {c1['customer_code']}"
    assert c1['full_name'] == 'Alice'
    print(f"[PASS] create first -> {c1['customer_code']} {c1['full_name']}")

    # Create second customer
    c2 = service.get_or_create_customer({
        'full_name': 'Bob',
        'phone': '2222222222',
        'email': 'bob@example.com',
        'created_at': now,
        'updated_at': now,
    })
    assert c2['customer_code'] == 'C000002', f"expected C000002, got {c2['customer_code']}"
    assert c2['full_name'] == 'Bob'
    print(f"[PASS] create second -> {c2['customer_code']} {c2['full_name']}")

    # Duplicate phone returns existing customer
    c3 = service.get_or_create_customer({
        'full_name': 'Alice Dup',
        'phone': '1111111111',
        'email': 'alice@example.com',
        'created_at': now,
        'updated_at': now,
    })
    assert c3['customer_code'] == 'C000001', f"expected C000001, got {c3['customer_code']}"
    assert c3['full_name'] == 'Alice', "should return original, not overwrite"
    print(f"[PASS] duplicate phone -> returns existing {c3['customer_code']} {c3['full_name']}")

    # customer_code increments correctly
    c4 = service.get_or_create_customer({
        'full_name': 'Charlie',
        'phone': '3333333333',
        'email': 'charlie@example.com',
        'created_at': now,
        'updated_at': now,
    })
    assert c4['customer_code'] == 'C000003', f"expected C000003, got {c4['customer_code']}"
    print(f"[PASS] increment code -> {c4['customer_code']} {c4['full_name']}")

    # find_customer by phone
    found = service.find_customer('2222222222')
    assert found is not None and found['full_name'] == 'Bob'
    print(f"[PASS] find_customer (phone) -> {found['full_name']}")

    # find_customer by customer_code
    found = service.find_customer('C000003')
    assert found is not None and found['full_name'] == 'Charlie'
    print(f"[PASS] find_customer (code) -> {found['full_name']}")

    # find_customer returns None for unknown query
    found = service.find_customer('NONEXISTENT')
    assert found is None
    print("[PASS] find_customer (unknown) -> None")

    # update_customer
    updated = service.update_customer(c1['id'], {'full_name': 'Alice Smith'})
    assert updated is not None and updated['full_name'] == 'Alice Smith'
    print(f"[PASS] update_customer -> {updated['full_name']}")

    # get_all_customers
    all_c = service.get_all_customers()
    assert len(all_c) == 3
    print(f"[PASS] get_all_customers -> {len(all_c)} customers")

    print("\nAll tests passed!")


if __name__ == '__main__':
    test_customer_service()
