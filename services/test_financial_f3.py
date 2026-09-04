"""F3 targeted validation suite (FINANCIAL_F3_IMPLEMENTATION_REPORT.md).

Run:  python services/test_financial_f3.py

Every phase runs in a SEPARATE subprocess with a fresh temporary working
directory (the DB path is CWD-relative). The real ``repair_manager.db``
is NEVER touched; phase ``realdb`` works on a COPY of it.

Phases
  ledger       pure projection + repo-backed ledger scenarios (1-21, 25)
  integration  realistic sequence, materialization-driven events,
               repair-edit/event immutability, F2 delegation, profit
               separation
  legacy       pre-F2 database: attribution, orphan exclusion
  realdb       production copy: no schema change, deterministic ledger
"""
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THIS_FILE = os.path.abspath(__file__)
REAL_DB = os.path.join(PROJECT_ROOT, 'repair_manager.db')


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
    d = tempfile.mkdtemp(prefix='f3_')
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


def ev(transaction_id, tx_type, amount, date='1404/01/01',
       customer_id=7, repair_id=1, created='2026-09-03T10:00:00',
       note='', event_key=None):
    """Build a raw financial-event dict (ledger projection input)."""
    return {
        'transaction_id': transaction_id,
        'repair_id': repair_id,
        'amount': amount,
        'payment_method': '',
        'payment_date': date,
        'transaction_type': tx_type,
        'created_at': created,
        'note': note,
        'customer_id': customer_id,
        'event_key': event_key,
    }


# ---------------------------------------------------------------- phase: ledger
def phase_ledger():
    fresh_dir()
    r = Results()

    from core.storage.init_db import init_database
    init_database()

    from services.customer_ledger_service import (
        CustomerLedgerEntry, CustomerLedgerService, build_ledger_entries,
        classify_event, apply_running_balances)
    from services.financial_event_service import FinancialEventService

    svc = CustomerLedgerService()

    def t1_empty():
        ledger = svc.get_customer_ledger(7)
        assert ledger['entries'] == [] and ledger['balance'] == 0
        assert ledger['total_debit'] == 0 and ledger['total_credit'] == 0
        assert ledger['entry_count'] == 0

    def t2_charge():
        p = build_ledger_entries([ev(1, 'REPAIR_CHARGE', 1000)], 7)
        e = p['entries'][0]
        assert e.direction == 'DEBIT' and e.debit == 1000 and e.credit == 0
        assert e.signed_effect == 1000 and e.running_balance == 1000

    def t3_payment():
        p = build_ledger_entries([ev(2, 'PAYMENT', 300)], 7)
        e = p['entries'][0]
        assert e.direction == 'CREDIT' and e.credit == 300 and e.debit == 0
        assert e.signed_effect == -300 and e.running_balance == -300

    def t4_discount():
        p = build_ledger_entries([ev(3, 'DISCOUNT', 100)], 7)
        e = p['entries'][0]
        assert e.direction == 'CREDIT' and e.credit == 100
        assert e.signed_effect == -100 and e.running_balance == -100

    def t5_refund():
        p = build_ledger_entries([ev(4, 'REFUND', 50)], 7)
        e = p['entries'][0]
        assert e.direction == 'DEBIT' and e.debit == 50
        assert e.signed_effect == 50 and e.running_balance == 50

    def t6_9_multiple_events():
        events = [
            ev(1, 'REPAIR_CHARGE', 1000, '1404/01/01'),
            ev(2, 'PAYMENT', 300, '1404/01/02'),
            ev(3, 'DISCOUNT', 100, '1404/01/03'),
            ev(4, 'REFUND', 50, '1404/01/04'),
        ]
        p = build_ledger_entries(events, 7)
        balances = [e.running_balance for e in p['entries']]
        assert balances == [1000, 700, 600, 650], balances
        # correct classification + signed effects
        assert [(e.debit, e.credit, e.signed_effect) for e in p['entries']] == [
            (1000, 0, 1000), (0, 300, -300), (0, 100, -100), (50, 0, 50)]
        assert p['unsupported_events'] == [] and p['unattributed_events'] == 0

    def t10_11_final_balance_and_credit():
        events = [
            ev(1, 'REPAIR_CHARGE', 1000, '1404/01/01'),
            ev(2, 'PAYMENT', 1500, '1404/01/02'),
        ]
        p = build_ledger_entries(events, 7)
        assert p['entries'][-1].running_balance == -500  # customer credit
        # no zero-floor anywhere in the projection
        assert sum(e.signed_effect for e in p['entries']) == -500

    def t12_13_same_date_deterministic():
        events = [
            ev(11, 'PAYMENT', 100, '1404/02/01', created='2026-09-03T10:05:00'),
            ev(10, 'REPAIR_CHARGE', 500, '1404/02/01', created='2026-09-03T10:00:00'),
            ev(12, 'PAYMENT', 200, '1404/02/01', created='2026-09-03T10:05:00'),
        ]
        p1 = build_ledger_entries(list(events), 7)
        p2 = build_ledger_entries(list(reversed(events)), 7)
        ids1 = [e.transaction_id for e in p1['entries']]
        ids2 = [e.transaction_id for e in p2['entries']]
        # same input -> same order regardless of input order
        assert ids1 == ids2 == [10, 11, 12], (ids1, ids2)
        # same date: record timestamp then id decide the order
        assert [e.running_balance for e in p1['entries']] == [500, 400, 200]

    def t14_17_date_filters():
        events = [
            ev(1, 'REPAIR_CHARGE', 1000, '1404/01/01'),
            ev(2, 'PAYMENT', 300, '1404/02/15'),
            ev(3, 'REFUND', 50, '1404/03/10'),
        ]
        repair_customers = {}
        from services.customer_ledger_service import _in_range
        # from-date (inclusive)
        p = build_ledger_entries(events, 7)
        entries = [e for e in p['entries'] if _in_range(e.event_date, '1404/02/01', None)]
        assert [e.transaction_id for e in entries] == [2, 3]
        # to-date (inclusive)
        entries = [e for e in p['entries'] if _in_range(e.event_date, None, '1404/02/28')]
        assert [e.transaction_id for e in entries] == [1, 2]
        # inclusive boundaries: exact dates match
        assert _in_range('1404/02/15', '1404/02/15', None)
        assert _in_range('1404/02/15', None, '1404/02/15')
        # from + to
        entries = [e for e in p['entries'] if _in_range(e.event_date, '1404/02/01', '1404/02/28')]
        assert [e.transaction_id for e in entries] == [2]
        # running balance recomputed over the filtered window
        apply_running_balances(entries)
        assert entries[0].running_balance == -300

    def t14b_undated_events():
        p = build_ledger_entries([ev(1, 'REPAIR_CHARGE', 1000, date='')], 7)
        assert len(p['entries']) == 1  # visible without a range
        from services.customer_ledger_service import _in_range
        assert not _in_range('', '1404/01/01', None)   # excluded from bounded views
        assert not _in_range('', None, '1404/12/29')

    def t18_unattributed_excluded():
        events = [
            ev(1, 'REPAIR_CHARGE', 1000, customer_id=None, repair_id=None),
            ev(2, 'PAYMENT', 300, customer_id=7),
        ]
        p = build_ledger_entries(events, 7)
        assert [e.transaction_id for e in p['entries']] == [2]
        assert p['unattributed_events'] == 1

    def t18b_orphan_repair_reference():
        events = [ev(1, 'REPAIR_CHARGE', 1000, customer_id=None, repair_id=999)]
        p = build_ledger_entries(events, 7, {1: 7, 999: None})
        assert p['entries'] == [] and p['unattributed_events'] == 1

    def t19_unknown_type():
        status, reason, _ = classify_event(ev(1, 'MYSTERY_TYPE', 100))
        assert status == 'unsupported' and reason == 'unknown_event_type'
        p = build_ledger_entries([ev(1, 'MYSTERY_TYPE', 100, customer_id=7)], 7)
        assert p['entries'] == []
        assert p['unsupported_events'] == [
            {'transaction_id': 1, 'event_type': 'MYSTERY_TYPE',
             'reason': 'unknown_event_type'}]

    def t20_invalid_amounts():
        assert classify_event(ev(1, 'PAYMENT', 'abc'))[0] == 'unsupported'
        assert classify_event(ev(1, 'PAYMENT', None))[0] == 'unsupported'
        p = build_ledger_entries(
            [ev(1, 'PAYMENT', None, customer_id=7),
             ev(2, 'REPAIR_CHARGE', 100, customer_id=7)], 7)
        assert [e.transaction_id for e in p['entries']] == [2]
        assert p['unsupported_events'][0]['reason'] == 'invalid_amount'

    def t21_adjustment_unresolved():
        status, reason, _ = classify_event(ev(1, 'ADJUSTMENT', 100))
        assert status == 'unsupported'
        assert reason == 'adjustment_direction_unresolved'
        p = build_ledger_entries(
            [ev(1, 'ADJUSTMENT', 100, customer_id=7),
             ev(2, 'REPAIR_CHARGE', 500, customer_id=7)], 7)
        assert [e.transaction_id for e in p['entries']] == [2]
        assert p['unsupported_events'] == [
            {'transaction_id': 1, 'event_type': 'ADJUSTMENT',
             'reason': 'adjustment_direction_unresolved'}]
        # ADJUSTMENT never reaches the balance
        assert p['entries'][0].running_balance == 500

    def t21b_negative_delta_reversal_books_as_debit():
        # F2 signed correction delta: discount reversal of -100 must
        # INCREASE debt by 100 in the ledger (traceable to DISCOUNT)
        p = build_ledger_entries([
            ev(1, 'REPAIR_CHARGE', 500, '1404/01/01'),
            ev(2, 'DISCOUNT', -100, '1404/01/02'),
        ], 7)
        reversal = p['entries'][1]
        assert reversal.debit == 100 and reversal.credit == 0
        assert reversal.signed_effect == 100
        assert reversal.running_balance == 600
        assert reversal.event_type == 'DISCOUNT'  # traceable to its event

    def t_entry_metadata():
        p = build_ledger_entries([
            ev(9, 'REPAIR_CHARGE', 1000, date='1404/01/01', repair_id=4,
               note='ثبت خودکار بدهی تعمیر #4 — رویداد بازسازی‌شده '
                    '(پیش از سیستم رویداد مالی)',
               event_key='REPAIR_CHARGE:repair:4:initial'),
        ], 7)
        e = p['entries'][0]
        assert e.transaction_id == 9 and e.repair_id == 4
        assert e.event_date == '1404/01/01' and e.customer_id == 7
        assert e.event_key == 'REPAIR_CHARGE:repair:4:initial'
        assert e.reconstructed is True
        assert isinstance(e, CustomerLedgerEntry)
        assert set(e.as_dict()) >= {
            'customer_id', 'transaction_id', 'repair_id', 'event_type',
            'event_date', 'description', 'debit', 'credit',
            'signed_effect', 'running_balance', 'reconstructed'}

    r.run('T1  empty customer ledger', t1_empty)
    r.run('T2  one REPAIR_CHARGE -> DEBIT +1000', t2_charge)
    r.run('T3  one PAYMENT -> CREDIT -300', t3_payment)
    r.run('T4  one DISCOUNT -> CREDIT -100', t4_discount)
    r.run('T5  one REFUND -> DEBIT +50', t5_refund)
    r.run('T6-9 multiple events: classification, effects, running balance', t6_9_multiple_events)
    r.run('T10/11 final balance + customer credit (no zero-floor)', t10_11_final_balance_and_credit)
    r.run('T12/13 same-date events: deterministic ordering', t12_13_same_date_deterministic)
    r.run('T14-17 date filtering (from/to/inclusive/both)', t14_17_date_filters)
    r.run('T14b undated events: visible unbounded, excluded from ranges', t14b_undated_events)
    r.run('T18 unattributed events excluded + counted', t18_unattributed_excluded)
    r.run('T18b orphaned repair reference never guessed', t18b_orphan_repair_reference)
    r.run('T19 unknown event type handled safely + visibly', t19_unknown_type)
    r.run('T20 missing/invalid amounts handled safely', t20_invalid_amounts)
    r.run('T21 ADJUSTMENT remains unresolved, never classified', t21_adjustment_unresolved)
    r.run('T21b negative correction delta books as debit (reversal)', t21b_negative_delta_reversal_books_as_debit)
    r.run('T22b entry metadata (ids, reference, reconstructed flag)', t_entry_metadata)

    return r.summary()


# ---------------------------------------------------------------- phase: integration
def phase_integration():
    fresh_dir()
    r = Results()

    from core.storage.init_db import init_database
    init_database()

    from core.storage.sqlite_storage import SQLiteStorage
    from core.storage.payment_transaction_repository import (
        PaymentTransactionRepository)
    from services.customer_ledger_service import CustomerLedgerService
    from services.financial_event_service import FinancialEventService
    from services.invoice_calculator import calculate_invoice_totals

    st = SQLiteStorage()
    repo = PaymentTransactionRepository()
    ledger_svc = CustomerLedgerService()
    event_svc = FinancialEventService()
    rep = None  # set by i3; reused by i4

    # --- realistic sequence (repo-written events, explicit dates) -----
    repo.create({'repair_id': 1, 'amount': 10000000,
                 'transaction_type': 'REPAIR_CHARGE', 'customer_id': 7,
                 'payment_date': '1404/05/01',
                 'event_key': 'REPAIR_CHARGE:repair:1:initial'})
    repo.create({'repair_id': 1, 'amount': 3000000,
                 'transaction_type': 'PAYMENT', 'customer_id': 7,
                 'payment_date': '1404/05/10'})
    repo.create({'repair_id': 1, 'amount': 500000,
                 'transaction_type': 'DISCOUNT', 'customer_id': 7,
                 'payment_date': '1404/05/12',
                 'event_key': 'DISCOUNT:repair:1:initial'})
    repo.create({'repair_id': 1, 'amount': 200000,
                 'transaction_type': 'REFUND', 'customer_id': 7,
                 'payment_date': '1404/05/15'})

    def i1_realistic_sequence():
        ledger = ledger_svc.get_customer_ledger(7)
        balances = [e.running_balance for e in ledger['entries']]
        assert balances == [10000000, 7000000, 6500000, 6700000], balances
        assert ledger['total_debit'] == 10200000, ledger
        assert ledger['total_credit'] == 3500000, ledger
        assert ledger['balance'] == 6700000, ledger
        assert ledger['entry_count'] == 4

    def i2_event_immutability():
        before = repo.list_for_repair(1)
        ledger_svc.get_customer_ledger(7)
        ledger_svc.get_customer_balance(7)
        event_svc.customer_balance(7)
        after = repo.list_for_repair(1)
        assert before == after  # ledger projection never mutates events

    def i3_materialization_driven():
        nonlocal rep
        # charge + discount via the F2 materialization path
        rep = {
            'id': 2, 'customer_id': 8, 'customer_name': 'Ali',
            'phone': '09120000000', 'brand': '', 'model': '', 'issue': '',
            'status': 'در انتظار', 'receive_date': '1404/06/01',
            'delivery_date': '', 'parts_cost': 600000, 'labor_cost': 400000,
            'tax': 0.0, 'discount': 100000, 'notes': '', 'warranty': '',
            'paid_amount': 0, 'payment_status': 'پرداخت نشده',
            'payment_method': 'نقدی', 'payment_date': '',
            'financial_notes': '', 'service_lines': [],
            'part_lines': [{'part_id': 1, 'part_name_snapshot': 'p',
                            'quantity': 1, 'unit_price': 600000,
                            'total_price': 600000,
                            'purchase_price_snapshot': 300000}],
            'additional_charges': [],
        }
        st.save_all([rep])
        out = FinancialEventService().materialize_for_repair(rep, is_new=True)
        assert [e['transaction_type'] for e in out['created']] == [
            'REPAIR_CHARGE', 'DISCOUNT'], out
        ledger = ledger_svc.get_customer_ledger(8)
        entries = ledger['entries']
        assert [(e.event_type, e.debit, e.credit) for e in entries] == [
            ('REPAIR_CHARGE', 1000000, 0), ('DISCOUNT', 0, 100000)]
        assert ledger['balance'] == 900000
        # charge − discount == payable (F2 invariant visible in the ledger)
        assert ledger['total_debit'] - ledger['total_credit'] == \
            calculate_invoice_totals(rep)['total']

    def i4_repair_edit_ledger_stability():
        # historical charge entry stays identical after the repair changes
        ledger_before = ledger_svc.get_customer_ledger(8)
        snap = {e.transaction_id: e.as_dict() for e in ledger_before['entries']}
        edited = dict(rep, parts_cost=1100000)  # payable 1,500,000 now
        st.save_all([edited])
        FinancialEventService().materialize_for_repair(edited, is_new=False)
        ledger_after = ledger_svc.get_customer_ledger(8)
        entries = ledger_after['entries']
        # original entries untouched
        for e in entries:
            if e.transaction_id in snap:
                assert snap[e.transaction_id] == e.as_dict(), e
        # one new delta entry (+500,000 debit), running balance follows
        new = [e for e in entries if e.transaction_id not in snap]
        assert len(new) == 1 and new[0].debit == 500000, new
        assert entries[-1].running_balance == 1400000
        # the historical charge row itself still shows 1,000,000
        charge = [e for e in entries
                  if e.event_key == 'REPAIR_CHARGE:repair:2:initial'][0]
        assert charge.debit == 1000000 and charge.running_balance == 1000000

    def i5_f2_delegation_single_rule():
        via_f2 = event_svc.customer_balance(7)
        via_ledger = ledger_svc.get_customer_balance(7)
        assert via_f2 == via_ledger
        assert via_ledger['balance'] == 6700000

    def i6_profit_separation():
        import sys
        assert 'services.profit_service' not in sys.modules, (
            'ledger layer must not touch ProfitService')
        # and the ledger result carries no profit/cost concepts
        ledger = ledger_svc.get_customer_ledger(7)
        assert not any('profit' in k or 'cost' in k
                       for k in ledger.keys())

    def i7_payment_refund_compatibility():
        from services.payment_reconciliation_service import (
            PaymentReconciliationService)
        net = PaymentReconciliationService().net_paid_for_repair(1)
        assert net == 3000000 - 200000  # PAYMENT - REFUND semantics untouched
        history = repo.list_payment_history_for_repair(1)
        assert all(t['transaction_type'] in ('PAYMENT', 'REFUND')
                   for t in history)

    r.run('I1  realistic sequence: 10M/3M/0.5M/0.2M -> balance 6,700,000', i1_realistic_sequence)
    r.run('I2  ledger projection never mutates financial events', i2_event_immutability)
    r.run('I3  materialization-driven events project correctly', i3_materialization_driven)
    r.run('I4  repair edits leave historical ledger entries unchanged', i4_repair_edit_ledger_stability)
    r.run('I5  F2 customer_balance delegates to the ledger (one rule)', i5_f2_delegation_single_rule)
    r.run('I6  ProfitService never imported by the ledger layer', i6_profit_separation)
    r.run('I7  PAYMENT/REFUND compatibility intact', i7_payment_refund_compatibility)

    return r.summary()


# ---------------------------------------------------------------- phase: legacy
def phase_legacy():
    fresh_dir()

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
    conn.execute("INSERT INTO repairs (id, customer_name, phone) "
                 "VALUES (1, 'علی رضایی', '09111111111')")
    # legacy payment + refund rows without customer_id/event_key
    conn.execute("INSERT INTO payment_transaction (repair_id, amount, "
                 "payment_date, transaction_type, created_at, note) VALUES "
                 "(1, 500000, '1403/02/15', 'PAYMENT', '2025-05-05 10:00:00', "
                 "'مهاجرت پرداخت قدیمی')")
    conn.execute("INSERT INTO payment_transaction (repair_id, amount, "
                 "payment_date, transaction_type, created_at, note) VALUES "
                 "(1, 50000, '1403/02/16', 'REFUND', '2025-05-05 10:00:00', '')")
    # orphan payment referencing a non-existent repair
    conn.execute("INSERT INTO payment_transaction (repair_id, amount, "
                 "payment_date, transaction_type, created_at, note) VALUES "
                 "(77, 999999, '1403/02/17', 'PAYMENT', '2025-05-05 10:00:00', '')")
    conn.commit()
    conn.close()

    from core.storage.init_db import init_database
    init_database()

    from services.customer_ledger_service import CustomerLedgerService

    r = Results()
    svc = CustomerLedgerService()

    def l1_legacy_attribution():
        ledger = svc.get_customer_ledger(1)
        # legacy rows attributed via the repair's F1.5 customer_id
        types = [(e.event_type, e.debit, e.credit) for e in ledger['entries']]
        assert types == [('PAYMENT', 0, 500000), ('REFUND', 50000, 0)], types
        assert ledger['balance'] == -450000  # customer credit, survives
        assert ledger['unattributed_events'] == 1  # the orphan, visible

    def l2_deterministic_repeat():
        a = [e.as_dict() for e in svc.get_customer_ledger(1)['entries']]
        b = [e.as_dict() for e in svc.get_customer_ledger(1)['entries']]
        assert a == b

    def l3_no_writes_to_legacy_rows():
        conn = sqlite3.connect('repair_manager.db')
        rows = conn.execute(
            'SELECT transaction_id, amount, transaction_type, note '
            'FROM payment_transaction ORDER BY transaction_id').fetchall()
        conn.close()
        assert rows[0][:3] == (1, 500000, 'PAYMENT')
        assert rows[0][3] == 'مهاجرت پرداخت قدیمی'  # note untouched
        assert rows[2][:3] == (3, 999999, 'PAYMENT')  # orphan preserved

    r.run('L1  legacy events attributed via repair.customer_id; orphan excluded', l1_legacy_attribution)
    r.run('L2  ledger deterministic across repeated builds', l2_deterministic_repeat)
    r.run('L3  legacy rows never modified by the ledger layer', l3_no_writes_to_legacy_rows)

    return r.summary()


# ---------------------------------------------------------------- phase: realdb
def phase_realdb():
    work = tempfile.mkdtemp(prefix='f3_realdb_')
    shutil.copyfile(REAL_DB, os.path.join(work, 'repair_manager.db'))
    os.chdir(work)
    sys.path.insert(0, PROJECT_ROOT)

    r = Results()

    from core.storage.init_db import init_database
    init_database()  # F2-era migration only — F3 adds NO schema change

    conn = sqlite3.connect('repair_manager.db')
    pay_cols = [c[1] for c in conn.execute(
        'PRAGMA table_info(payment_transaction)').fetchall()]
    tables = [t[0] for t in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    conn.close()

    from services.customer_ledger_service import CustomerLedgerService
    svc = CustomerLedgerService()

    def f1_no_schema_change():
        # F3 adds no columns and no tables
        assert 'customer_id' in pay_cols and 'event_key' in pay_cols
        assert not any('ledger' in t.lower() for t in tables), tables

    def f2_ledger_from_real_data():
        # The production copy's legacy PAYMENT rows carry no customer_id
        # but DO resolve through the F2 repair-attribution policy, so the
        # ledger legitimately shows them as customer credits.
        ledger = svc.get_customer_ledger(2)
        for e in ledger['entries']:
            assert e.customer_id == 2
            assert e.event_type in ('PAYMENT', 'REFUND')  # no events yet
            assert e.reconstructed is False  # legacy rows carry no marker
        assert ledger['balance'] == (ledger['total_debit']
                                     - ledger['total_credit'])
        assert isinstance(ledger['unattributed_events'], int)
        assert ledger['unattributed_events'] >= 0

    def f3_deterministic():
        a = [e.as_dict() for e in svc.get_customer_ledger(3)['entries']]
        b = [e.as_dict() for e in svc.get_customer_ledger(3)['entries']]
        assert a == b

    def f4_save_flow_integration():
        # simulate one app save of a legacy repair -> ledger reflects it
        from core.storage.sqlite_storage import SQLiteStorage
        from services.financial_event_service import FinancialEventService
        st = SQLiteStorage()
        loaded = {x['id']: x for x in st.load_all()}
        rep = loaded[2]  # 'امانویل سیمکشیان' -> customer 3
        ledger_before = svc.get_customer_ledger(3)
        before_ids = {e.transaction_id for e in ledger_before['entries']}
        FinancialEventService().materialize_for_repair(rep, is_new=False)
        ledger = svc.get_customer_ledger(3)
        # a reconstructed REPAIR_CHARGE was added for this customer
        charges = [e for e in ledger['entries']
                   if e.event_type == 'REPAIR_CHARGE']
        assert len(charges) == 1, charges
        charge = charges[0]
        assert charge.reconstructed is True
        assert charge.debit == charge.signed_effect > 0
        assert charge.transaction_id not in before_ids
        # legacy payment entries are untouched and still present
        assert before_ids.issubset(
            {e.transaction_id for e in ledger['entries']})
        assert ledger['balance'] == (ledger['total_debit']
                                     - ledger['total_credit'])
        # repeat save -> ledger unchanged (idempotent)
        FinancialEventService().materialize_for_repair(rep, is_new=False)
        again = [e.as_dict() for e in svc.get_customer_ledger(3)['entries']]
        assert [e.as_dict() for e in ledger['entries']] == again

    r.run('F3.1 F3 introduces NO schema change / NO ledger table', f1_no_schema_change)
    r.run('F3.2 ledger builds on the production copy', f2_ledger_from_real_data)
    r.run('F3.3 ledger deterministic on real data', f3_deterministic)
    r.run('F3.4 save-flow integration on real data (reconstructed, idempotent)', f4_save_flow_integration)

    return r.summary()


RUNNERS = {
    'ledger': phase_ledger,
    'integration': phase_integration,
    'legacy': phase_legacy,
    'realdb': phase_realdb,
}


def main():
    if '--phase' in sys.argv:
        return RUNNERS[sys.argv[sys.argv.index('--phase') + 1]]()
    failures = 0
    for phase in ('ledger', 'integration', 'legacy', 'realdb'):
        print(f"\n########## PHASE {phase} ##########")
        failures += run_phase(phase)
    print(f"\n=== F3 validation: "
          f"{'ALL PHASES PASSED' if failures == 0 else str(failures) + ' phase(s) failed'} ===")
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
