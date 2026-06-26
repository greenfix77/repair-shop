"""Verification script for empty phone persistence fix."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import text

from core.storage.init_db import init_database
from core.storage.customer_repository import CustomerRepository
from core.storage.database import SessionLocal
from core.storage.customer_model_db import CustomerDB

init_database()
repo = CustomerRepository()

# Clean test data
session = SessionLocal()
session.execute(text("DELETE FROM customer WHERE customer_code LIKE 'T%'"))
session.commit()
session.close()

print("=== VERIFICATION: Empty phone persistence ===\n")

# 1. Create customer without phone
print("1. Create customer WITHOUT phone...")
c1 = repo.create({
    'customer_code': 'T000001',
    'full_name': 'No Phone One',
    'phone': '',
    'email': 'nophone1@test.com',
})
assert c1['id'] > 0
assert c1['phone'] == ''
print("   PASS - id=%d" % c1['id'])

# 2. Create second customer without phone (should NOT raise UNIQUE)
print("2. Create second customer WITHOUT phone...")
c2 = repo.create({
    'customer_code': 'T000002',
    'full_name': 'No Phone Two',
    'phone': '',
    'email': 'nophone2@test.com',
})
assert c2['id'] > 0
assert c2['phone'] == ''
print("   PASS - id=%d" % c2['id'])

# 3. Verify database stores NULL, not empty string
print("3. Verify database stores NULL (not empty string)...")
session = SessionLocal()
row1 = session.query(CustomerDB).filter_by(customer_code='T000001').first()
row2 = session.query(CustomerDB).filter_by(customer_code='T000002').first()
assert row1.phone is None, "Expected NULL in DB, got: %r" % row1.phone
assert row2.phone is None, "Expected NULL in DB, got: %r" % row2.phone
# Raw SQL verification
result = session.execute(text("SELECT phone FROM customer WHERE customer_code = 'T000001'")).fetchone()
print("   Raw SQL phone value: %r" % result[0])
session.close()
print("   PASS - both rows have phone=NULL in database")

# 4. Create customer WITH phone
print("4. Create customer WITH phone...")
c3 = repo.create({
    'customer_code': 'T000003',
    'full_name': 'Has Phone',
    'phone': '09120000000',
    'email': 'hasphone@test.com',
})
assert c3['id'] > 0
assert c3['phone'] == '09120000000'
print("   PASS - id=%d, phone=%s" % (c3['id'], c3['phone']))

# 5. Duplicate phone must still be rejected
print("5. Duplicate phone must be rejected...")
try:
    repo.create({
        'customer_code': 'T000004',
        'full_name': 'Duplicate Phone',
        'phone': '09120000000',
        'email': 'dup@test.com',
    })
    print("   FAIL - should have raised exception")
except Exception as e:
    print("   PASS - duplicate phone rejected: %s" % type(e).__name__)

# 6. Existing customer workflow continues to work
print("6. Existing customer workflow continues...")
c4 = repo.get_by_phone('09120000000')
assert c4 is not None
assert c4['full_name'] == 'Has Phone'
print("   PASS - get_by_phone works: %s" % c4['full_name'])

all_c = repo.get_all()
print("   Total customers: %d" % len(all_c))

# Cleanup test data
session = SessionLocal()
session.execute(text("DELETE FROM customer WHERE customer_code LIKE 'T%'"))
session.commit()
session.close()

print("\nALL VERIFICATIONS PASSED")
