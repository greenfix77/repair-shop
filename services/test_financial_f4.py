"""F4 targeted validation suite (FINANCIAL_F4_IMPLEMENTATION_REPORT.md).

Run:  python services/test_financial_f4.py

Every phase runs in a SEPARATE subprocess with a fresh temporary working
directory (the DB path is CWD-relative). The real ``repair_manager.db``
is NEVER touched.

Phases
  report     F4.1-F4.20 + F4.23 + realistic mixed sequence
  legacy     F4.21 / F4.22 (legacy attribution + orphans)
F4.24 (F3 regression) is the F3 suite run in the regression battery.
"""
import os
import subprocess
import sys
import tempfile

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THIS_FILE = os.path.abspath(__file__)


class Results:
    def __init__(self):
        self.passed = 0
        self.failed = 0

    def run(self, name, fn):
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            self.failed += 1
            print(f"[FAIL] {name}: {exc}")
            import traceback
            traceback.print_exc()
        else:
            self.passed += 1
            print(f"[PASS] {name}")

    def summary(self):
        print(f"\n=== phase result: {self.passed} passed, {self.failed} failed ===")
        return 1 if self.failed else 0


def fresh_dir():
    d = tempfile.mkdtemp(prefix='f4_')
    os.chdir(d)
    sys.path.insert(0, PROJECT_ROOT)
    return d


def run_phase(phase):
    proc = subprocess.run(
        [sys.executable, THIS_FILE, '--phase', phase],
        capture_output=True, text=True, encoding='utf-8',
        env=dict(os.environ, PYTHONIOENCODING='utf-8'),
        cwd=tempfile.gettempdir(), timeout=300,
    )
    print(proc.stdout)
    if proc.stderr.strip():
        print('--- stderr ---')
        print(proc.stderr)
    return proc.returncode


def make_repair(repair_id, customer_id=7, **over):
    base = {
        'id': repair_id, 'customer_id': customer_id,
        'customer_name': 'Sara', 'phone': '09123333333',
        'brand': 'hp', 'model': 'pavilion', 'issue': 'screen',
        'status': 'در حال تعمیر', 'receive_date': '1404/05/01',
        'delivery_date': '', 'parts_cost': 600000, 'labor_cost': 400000,
        'tax': 0.0, 'discount': 0, 'notes': '', 'warranty': '',
        'paid_amount': 0, 'payment_status': 'پرداخت نشده',
        'payment_method': 'نقدی', 'payment_date': '',
        'financial_notes': '',
        'service_lines': [{'service_id': None, 'service_name_snapshot': 's',
                           'quantity': 1, 'unit_price': 400000,
                           'total_price': 400000}],
        'part_lines': [{'part_id': 1, 'part_name_snapshot': 'RAM',
                        'quantity': 1, 'unit_price': 600000,
                        'total_price': 600000,
                        'purchase_price_snapshot': 350000}],
        'additional_charges': [],
    }
    base.update(over)
    return base


def seed_customers(session_factory, rows):
    from core.storage.customer_model_db import CustomerDB
    session = session_factory()
    try:
        for cid, name, phone in rows:
            session.add(CustomerDB(
                id=cid, customer_code=f'C{cid:06d}',
                full_name=name, phone=phone))
        session.commit()
    finally:
        session.close()


# ---------------------------------------------------------------- phase: report
def phase_report():
    fresh_dir()
    r = Results()

    from core.storage.init_db import init_database
    init_database()

    from core.storage.database import SessionLocal
    from core.storage.sqlite_storage import SQLiteStorage
    from core.storage.payment_transaction_repository import (
        PaymentTransactionRepository)
    from services.customer_report_service import (
        BALANCE_STATUS_CREDITOR, BALANCE_STATUS_DEBTOR,
        BALANCE_STATUS_SETTLED, CustomerReportService)
    from services.customer_ledger_service import CustomerLedgerService
    from services.financial_event_service import FinancialEventService

    seed_customers(SessionLocal, [(7, 'سارا محمدی', '09123333333'),
                                 (8, 'علی رضایی', '09111111111')])

    st = SQLiteStorage()
    repo = PaymentTransactionRepository()
    svc = CustomerReportService()
    ledger_svc = CustomerLedgerService()
    event_svc = FinancialEventService()

    # two repairs for customer 7 (one completed, one active)
    rep1 = make_repair(1, status='تحویل داده شده',
                       delivery_date='1404/05/10')
    rep2 = make_repair(2, receive_date='1404/06/01')
    rep3 = make_repair(3, receive_date='1404/06/05')  # used by F4.11/F4.19
    st.save_all([rep1, rep2])
    event_svc.materialize_for_repair(rep1, is_new=True)   # charge 1,000,000
    event_svc.materialize_for_repair(rep2, is_new=True)   # charge 1,000,000

    def f4_1_empty_report():
        report = svc.build_report(999)
        assert report.customer_found is False
        assert report.summary.repair_count == 0
        assert report.summary.current_balance == 0
        assert report.summary.balance_status == BALANCE_STATUS_SETTLED
        assert report.ledger.entries == [] and report.ledger.balance == 0
        assert report.payment_history.items == []
        assert report.repair_history == []

    def f4_2_summary():
        repo.create({'repair_id': 1, 'amount': 400000,
                     'payment_date': '1404/05/12',
                     'transaction_type': 'PAYMENT',
                     'payment_method': 'کارت‌خوان (POS)',
                     'customer_id': 7})
        report = svc.build_report(7)
        s = report.summary
        assert s.customer_id == 7
        assert report.customer_found is True
        assert s.customer_name == 'سارا محمدی'
        assert s.phone == '09123333333'
        assert s.total_repair_charge == 2000000
        assert s.total_payment == 400000
        assert s.total_discount == 0 and s.total_refund == 0
        assert s.current_balance == 1600000
        assert s.balance_status == BALANCE_STATUS_DEBTOR
        # identity: charge − payment − discount + refund == balance
        assert (s.total_repair_charge - s.total_payment
                - s.total_discount + s.total_refund) == s.current_balance

    def f4_3_repair_count():
        report = svc.build_report(7)
        assert report.summary.repair_count == 2

    def f4_4_completed_vs_active():
        report = svc.build_report(7)
        assert report.summary.completed_repair_count == 1  # delivered
        assert report.summary.active_repair_count == 1     # in progress

    def f4_5_6_7_8_ledger_passthrough():
        report = svc.build_report(7)
        f3 = ledger_svc.get_customer_ledger(7)
        # entries are the F3 entries, shape-transformed only
        assert report.ledger.entries == [e.as_dict() for e in f3['entries']]
        # order preserved
        f3_ids = [e.transaction_id for e in f3['entries']]
        assert [e['transaction_id'] for e in report.ledger.entries] == f3_ids
        # running balances preserved
        assert [e['running_balance'] for e in report.ledger.entries] == \
            [e.running_balance for e in f3['entries']]
        # totals preserved
        assert report.ledger.total_debit == f3['total_debit']
        assert report.ledger.total_credit == f3['total_credit']
        assert report.ledger.balance == f3['balance'] == \
            report.summary.current_balance

    def f4_9_payment_history():
        report = svc.build_report(7)
        items = report.payment_history.items
        assert len(items) == 1 and items[0]['event_type'] == 'PAYMENT'
        assert items[0]['credit'] == 400000 and items[0]['debit'] == 0
        assert items[0]['payment_method'] == 'کارت‌خوان (POS)'
        assert report.payment_history.total_paid == 400000
        assert report.payment_history.total_refunded == 0

    def f4_10_refund_history():
        repo.create({'repair_id': 1, 'amount': 100000,
                     'payment_date': '1404/05/20',
                     'transaction_type': 'REFUND', 'customer_id': 7})
        report = svc.build_report(7)
        items = report.payment_history.items
        refunds = [i for i in items if i['event_type'] == 'REFUND']
        assert len(refunds) == 1 and refunds[0]['debit'] == 100000
        assert report.payment_history.total_refunded == 100000
        assert report.summary.total_refund == 100000
        # refund remains a customer DEBIT: balance increased again
        assert report.summary.current_balance == 1600000 + 100000
        assert report.summary.balance_status == BALANCE_STATUS_DEBTOR

    def f4_11_discount_credit():
        st.save_all([rep1, rep2, rep3])
        event_svc.materialize_for_repair(rep3, is_new=True)
        repo.create({'repair_id': 3, 'amount': 50000,
                     'payment_date': '1404/06/06',
                     'transaction_type': 'DISCOUNT', 'customer_id': 7})
        report = svc.build_report(7)
        assert report.summary.total_discount == 50000  # positive = credit given
        disc = [e for e in report.ledger.entries
                if e['event_type'] == 'DISCOUNT']
        assert disc and disc[0]['credit'] == 50000 and disc[0]['debit'] == 0
        # discount reduces the balance exactly like F3 says
        assert report.summary.current_balance == ledger_svc\
            .get_customer_balance(7)['balance']

    def f4_12_credit_balance():
        repo.create({'repair_id': 3, 'amount': 5000000,
                     'payment_date': '1404/06/10',
                     'transaction_type': 'PAYMENT', 'customer_id': 7})
        report = svc.build_report(7)
        assert report.summary.current_balance < 0
        assert report.summary.balance_status == BALANCE_STATUS_CREDITOR
        assert report.summary.current_balance == \
            ledger_svc.get_customer_balance(7)['balance']

    def f4_13_14_15_date_filters():
        # events so far: charge1 (1404/05/01), pay (05/12), refund (05/20),
        # charge2 (1404/06/01), charge3 (06/05), disc (06/06), pay (06/10)
        from_date = '1404/06/01'
        report = svc.build_report(7, date_from=from_date)
        f3 = ledger_svc.get_customer_ledger(7, date_from=from_date)
        assert report.ledger.balance == f3['balance']
        assert [e['transaction_id'] for e in report.ledger.entries] == \
            [e.transaction_id for e in f3['entries']]
        assert all(e['event_date'] >= from_date
                   for e in report.ledger.entries)

        to_date = '1404/05/31'
        report = svc.build_report(7, date_to=to_date)
        f3 = ledger_svc.get_customer_ledger(7, date_to=to_date)
        assert report.ledger.balance == f3['balance']
        assert all(e['event_date'] <= to_date
                   for e in report.ledger.entries)

        report = svc.build_report(7, date_from='1404/05/12',
                                  date_to='1404/06/06')
        f3 = ledger_svc.get_customer_ledger(7, date_from='1404/05/12',
                                            date_to='1404/06/06')
        dates = [e['event_date'] for e in report.ledger.entries]
        assert dates == ['1404/05/12', '1404/05/20', '1404/06/01',
                         '1404/06/05', '1404/06/06'], dates
        # inclusive boundaries: both endpoint dates present
        assert '1404/05/12' in dates and '1404/06/06' in dates
        assert report.ledger.balance == f3['balance']

    def f4_16_unrelated_customer_excluded():
        repo.create({'repair_id': 9, 'amount': 777777,
                     'payment_date': '1404/06/11',
                     'transaction_type': 'PAYMENT', 'customer_id': 8})
        report = svc.build_report(7)
        assert all(e['customer_id'] == 7 for e in report.ledger.entries)
        assert all(i['customer_id'] == 7
                   for i in report.payment_history.items)
        other = svc.build_report(8)
        assert any(i['credit'] == 777777
                   for i in other.payment_history.items)

    def f4_17_unknown_event():
        repo.create({'repair_id': 1, 'amount': 100,
                     'payment_date': '1404/06/12',
                     'transaction_type': 'MYSTERY_TYPE', 'customer_id': 7})
        report = svc.build_report(7)
        assert report.ledger.entries[-1]['event_type'] != 'MYSTERY_TYPE'
        assert all(e['event_type'] != 'MYSTERY_TYPE'
                   for e in report.ledger.entries)
        reasons = {u['reason'] for u in report.ledger.unsupported_events}
        assert 'unknown_event_type' in reasons, report.ledger.unsupported_events

    def f4_18_adjustment_unresolved():
        repo.create({'repair_id': 1, 'amount': 300,
                     'payment_date': '1404/06/13',
                     'transaction_type': 'ADJUSTMENT', 'customer_id': 7})
        balance_before = ledger_svc.get_customer_balance(7)['balance']
        report = svc.build_report(7)
        reasons = {u['event_type']: u['reason']
                   for u in report.ledger.unsupported_events}
        assert reasons.get('ADJUSTMENT') == 'adjustment_direction_unresolved'
        # ADJUSTMENT never reaches the balance
        assert report.summary.current_balance == balance_before
        assert report.ledger.balance == balance_before

    def f4_19_repair_edit_no_rewrite():
        # the historical charge stays event-derived even when the repair
        # total changes WITHOUT materialization
        report = svc.build_report(7)
        rh1 = [x for x in report.repair_history if x.repair_id == 1][0]
        assert rh1.ledger_charge == 1000000
        edited = make_repair(1, status='تحویل داده شده',
                             delivery_date='1404/05/10',
                             parts_cost=1100000)  # payable now 1,500,000
        st.save_all([edited, rep2, rep3])
        report = svc.build_report(7)
        rh1 = [x for x in report.repair_history if x.repair_id == 1][0]
        assert rh1.ledger_charge == 1000000, rh1  # NOT the new repair total
        # after materialization the delta appears; the original entry is
        # untouched and the net follows the events
        event_svc.materialize_for_repair(edited, is_new=False)
        report = svc.build_report(7)
        rh1 = [x for x in report.repair_history if x.repair_id == 1][0]
        assert rh1.ledger_charge == 1500000  # 1,000,000 + 500,000 delta
        initial = [e for e in report.ledger.entries
                   if e['event_key'] == 'REPAIR_CHARGE:repair:1:initial'][0]
        assert initial['debit'] == 1000000  # historical row unchanged
        deltas = [e for e in report.ledger.entries
                  if e['event_key'] == 'REPAIR_CHARGE:repair:1:delta:1']
        assert deltas and deltas[0]['debit'] == 500000

    def f4_20_profit_separation():
        report = svc.build_report(7)
        se = report.shop_economics
        # shop economics exist and are non-trivial (parts cost snapshots)
        assert se.parts_cost > 0 and se.gross_profit > 0
        # they are NOT part of the balance
        assert report.summary.current_balance == \
            ledger_svc.get_customer_balance(7)['balance']
        assert (report.summary.total_repair_charge
                - report.summary.total_payment
                - report.summary.total_discount
                + report.summary.total_refund
                ) == report.summary.current_balance
        # and the report carries no profit key anywhere near the balance
        assert 'profit' not in report.summary.as_dict()
        assert 'balance' not in se.as_dict()

    def f4_23_determinism():
        a = svc.build_report(7).as_dict()
        b = svc.build_report(7).as_dict()
        assert a == b

    def realistic_mixed():
        # customer 42 (fresh): charge 10M, payment 3M, discount 0.5M,
        # refund 0.2M — untouched by the other scenarios
        rep8 = make_repair(42, customer_id=42, receive_date='1404/04/01',
                           parts_cost=0, labor_cost=0,
                           service_lines=[], part_lines=[])
        st.save_all([rep8])
        repo.create({'repair_id': 42, 'amount': 10000000,
                     'transaction_type': 'REPAIR_CHARGE', 'customer_id': 42,
                     'payment_date': '1404/04/01',
                     'event_key': 'REPAIR_CHARGE:repair:42:initial'})
        repo.create({'repair_id': 42, 'amount': 3000000,
                     'transaction_type': 'PAYMENT', 'customer_id': 42,
                     'payment_date': '1404/04/10'})
        repo.create({'repair_id': 42, 'amount': 500000,
                     'transaction_type': 'DISCOUNT', 'customer_id': 42,
                     'payment_date': '1404/04/12'})
        repo.create({'repair_id': 42, 'amount': 200000,
                     'transaction_type': 'REFUND', 'customer_id': 42,
                     'payment_date': '1404/04/15'})
        report = svc.build_report(42)
        assert report.summary.current_balance == 6700000, report.summary
        assert report.summary.balance_status == BALANCE_STATUS_DEBTOR
        assert report.summary.total_repair_charge == 10000000
        assert report.summary.total_payment == 3000000
        assert report.summary.total_discount == 500000
        assert report.summary.total_refund == 200000
        # exactly the same as F3
        assert report.summary.current_balance == \
            ledger_svc.get_customer_balance(42)['balance']
        assert report.ledger.balance == \
            ledger_svc.get_customer_ledger(42)['balance']

    r.run('F4.1 empty customer report', f4_1_empty_report)
    r.run('F4.2 customer summary fields', f4_2_summary)
    r.run('F4.3 repair count', f4_3_repair_count)
    r.run('F4.4 completed vs active repair counts', f4_4_completed_vs_active)
    r.run('F4.5 ledger passthrough (entries == F3)', f4_5_6_7_8_ledger_passthrough)
    r.run('F4.6 ledger order preserved', f4_5_6_7_8_ledger_passthrough)
    r.run('F4.7 running balance preserved', f4_5_6_7_8_ledger_passthrough)
    r.run('F4.8 debit/credit totals preserved', f4_5_6_7_8_ledger_passthrough)
    r.run('F4.9 payment history', f4_9_payment_history)
    r.run('F4.10 refund history', f4_10_refund_history)
    r.run('F4.11 discount remains a customer credit', f4_11_discount_credit)
    r.run('F4.12 customer credit / negative balance visible', f4_12_credit_balance)
    r.run('F4.13 inclusive date_from', f4_13_14_15_date_filters)
    r.run('F4.14 inclusive date_to', f4_13_14_15_date_filters)
    r.run('F4.15 date_from + date_to', f4_13_14_15_date_filters)
    r.run('F4.16 unrelated customer events excluded', f4_16_unrelated_customer_excluded)
    r.run('F4.17 unknown event handled safely', f4_17_unknown_event)
    r.run('F4.18 ADJUSTMENT remains unresolved', f4_18_adjustment_unresolved)
    r.run('F4.19 repair edit does not rewrite historical values', f4_19_repair_edit_no_rewrite)
    r.run('F4.20 profit does not affect customer balance', f4_20_profit_separation)
    r.run('F4.23 report determinism', f4_23_determinism)
    r.run('F4.R  realistic mixed sequence == F3 balance', realistic_mixed)

    return r.summary()


# ---------------------------------------------------------------- phase: legacy
def phase_legacy():
    fresh_dir()
    import sqlite3

    conn = sqlite3.connect('repair_manager.db')
    conn.executescript("""
    CREATE TABLE repairs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_name VARCHAR, phone VARCHAR, brand VARCHAR, model VARCHAR,
        issue VARCHAR, parts_cost INTEGER, labor_cost INTEGER, tax FLOAT,
        discount INTEGER, status VARCHAR, receive_date VARCHAR,
        delivery_date VARCHAR, notes VARCHAR, warranty VARCHAR
    );
    CREATE TABLE customer (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_code VARCHAR UNIQUE, full_name VARCHAR, phone VARCHAR UNIQUE,
        email VARCHAR, website VARCHAR, national_id VARCHAR, address VARCHAR,
        city VARCHAR, province VARCHAR, postal_code VARCHAR, notes VARCHAR,
        created_at VARCHAR, updated_at VARCHAR
    );
    CREATE TABLE payment_transaction (
        transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
        repair_id INTEGER NOT NULL DEFAULT 0,
        amount INTEGER NOT NULL DEFAULT 0,
        payment_method VARCHAR, payment_date VARCHAR,
        transaction_type VARCHAR NOT NULL DEFAULT 'PAYMENT',
        created_at DATETIME, note VARCHAR
    );
    """)
    conn.execute("INSERT INTO customer (id, customer_code, full_name, phone) "
                 "VALUES (1, 'C000001', 'علی رضایی', '09111111111')")
    conn.execute("INSERT INTO repairs (id, customer_name, phone, receive_date) "
                 "VALUES (1, 'علی رضایی', '09111111111', '1403/02/10')")
    conn.execute("INSERT INTO payment_transaction (repair_id, amount, "
                 "payment_method, payment_date, transaction_type, created_at, note) "
                 "VALUES (1, 500000, 'نقدی', '1403/02/15', 'PAYMENT', "
                 "'2025-05-05 10:00:00', 'مهاجرت پرداخت قدیمی')")
    # orphan payment (repair 77 does not exist)
    conn.execute("INSERT INTO payment_transaction (repair_id, amount, "
                 "payment_method, payment_date, transaction_type, created_at, note) "
                 "VALUES (77, 999999, 'نقدی', '1403/02/16', 'PAYMENT', "
                 "'2025-05-05 10:00:00', '')")
    conn.commit()
    conn.close()

    from core.storage.init_db import init_database
    init_database()

    from services.customer_report_service import CustomerReportService

    r = Results()
    svc = CustomerReportService()

    def f4_21_legacy_attribution():
        report = svc.build_report(1)
        assert report.customer_found is True
        assert report.summary.customer_name == 'علی رضایی'
        # the legacy payment is attributed via the repair's customer_id
        assert report.summary.total_payment == 500000
        assert len(report.payment_history.items) == 1
        assert report.payment_history.items[0]['payment_method'] == 'نقدی'
        assert report.ledger.balance == -500000  # customer credit visible
        # the legacy repair appears in the (operational) repair history
        assert [x.repair_id for x in report.repair_history] == [1]
        # no ledger events for it -> per-repair amounts stay None (no
        # reconstruction from the mutable repair)
        assert report.repair_history[0].ledger_charge is None

    def f4_22_orphan_unattributed():
        report = svc.build_report(1)
        # the orphan payment is visible as unattributed, never booked
        assert report.ledger.unattributed_events >= 1
        assert all(i['transaction_id'] != 2
                   for i in report.payment_history.items)
        # and it does not leak into any other customer's report either
        report2 = svc.build_report(2)
        assert all(e['customer_id'] != 1 for e in report2.ledger.entries)

    r.run('F4.21 legacy customer attribution (no heuristics)', f4_21_legacy_attribution)
    r.run('F4.22 orphaned/unattributed events preserved + visible', f4_22_orphan_unattributed)

    return r.summary()


RUNNERS = {
    'report': phase_report,
    'legacy': phase_legacy,
}


def main():
    if '--phase' in sys.argv:
        return RUNNERS[sys.argv[sys.argv.index('--phase') + 1]]()
    failures = 0
    for phase in ('report', 'legacy'):
        print(f"\n########## PHASE {phase} ##########")
        failures += run_phase(phase)
    print(f"\n=== F4 validation: "
          f"{'ALL PHASES PASSED' if failures == 0 else str(failures) + ' phase(s) failed'} ===")
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
