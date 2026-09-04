"""F2 targeted validation suite (FINANCIAL_F2_IMPLEMENTATION_REPORT.md).

Run:  python services/test_financial_f2.py

Every phase runs in a SEPARATE subprocess with a fresh temporary working
directory (the DB path is CWD-relative). The real ``repair_manager.db``
is NEVER touched; phase ``realdb`` works on a COPY of it.

Phases
  events    materialization, idempotency, discount lifecycle A-F,
            historical immutability, customer balance (signed, no floor)
  compat    PAYMENT/REFUND + reconciliation/summary/table/profit/UI
            regression safety with financial events present
  deletion  financial deletion guard (service logic used by app.py)
  legacy    pre-F2 database: migration, first-touch materialization,
            reconstructed flags, legacy payment attribution
  realdb    copy of the production DB: migration, no auto-backfill,
            repeated startup idempotency
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
    d = tempfile.mkdtemp(prefix='f2_')
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


def make_repair(repair_id, customer_id=3, **over):
    base = {
        'id': repair_id, 'customer_id': customer_id,
        'customer_name': 'Sara', 'phone': '09123333333',
        'brand': 'hp', 'model': 'pavilion', 'issue': 'screen',
        'status': 'در حال تعمیر', 'receive_date': '1404/05/10',
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


# ---------------------------------------------------------------- phase: events
def phase_events():
    fresh_dir()
    r = Results()

    from core.storage.init_db import init_database
    init_database()

    from core.storage.sqlite_storage import SQLiteStorage
    from core.storage.payment_transaction_repository import (
        PaymentTransactionRepository)
    from services.financial_event_service import (
        FinancialEventService, REPAIR_CHARGE, PAYMENT, DISCOUNT, REFUND)
    from services.invoice_calculator import payable_total
    from services.date_service import today_persian
    from sqlalchemy.exc import IntegrityError

    st = SQLiteStorage()
    repo = PaymentTransactionRepository()
    svc = FinancialEventService()

    # 1-4: new repair with customer_id -> REPAIR_CHARGE materialized
    repair = make_repair(1, customer_id=3)  # payable = 1,000,000
    st.save_all([repair])
    out = svc.materialize_for_repair(repair, is_new=True)

    def t1_new_repair():
        assert out['created'], out
        types = [e['transaction_type'] for e in out['created']]
        assert types == ['REPAIR_CHARGE'], types  # discount=0 -> no discount event

    def t2_charge_amount():
        ev = repo.list_for_repair(1)
        charge = [e for e in ev if e['transaction_type'] == 'REPAIR_CHARGE']
        assert len(charge) == 1, charge
        assert charge[0]['amount'] == payable_total(repair) == 1000000, charge

    def t3_event_metadata():
        ev = repo.list_for_repair(1)[0]
        assert ev['customer_id'] == 3, ev
        assert ev['repair_id'] == 1
        assert ev['event_key'] == 'REPAIR_CHARGE:repair:1:initial', ev
        assert ev['payment_date'] == '1404/05/10', ev  # receive_date policy
        assert ev['transaction_id'] > 0

    def t4_charge_date_delivered():
        delivered = make_repair(2, customer_id=4, status='تحویل داده شده',
                                delivery_date='1404/05/20')
        st.save_all([repair, delivered])
        svc.materialize_for_repair(delivered, is_new=True)
        ev = [e for e in repo.list_for_repair(2)
              if e['transaction_type'] == 'REPAIR_CHARGE'][0]
        assert ev['payment_date'] == '1404/05/20', ev  # delivery_date policy

    r.run('T1  new repair materializes REPAIR_CHARGE only (discount=0)', t1_new_repair)
    r.run('T2  charge amount == authoritative Customer Payable', t2_charge_amount)
    r.run('T3  event metadata (customer_id, event_key, date, id)', t3_event_metadata)
    r.run('T4  delivered repair charged at delivery_date (F1.5 policy)', t4_charge_date_delivered)

    # 5 / 9-13: discount lifecycle on repair 1
    def set_and_materialize(rid, **over):
        rep = make_repair(rid, **over)
        st.save_all([rep, make_repair(2, customer_id=4, status='تحویل داده شده',
                                      delivery_date='1404/05/20')])
        svc.materialize_for_repair(rep, is_new=False)
        return rep

    def t5_discount_materializes():
        before = len(repo.list_for_repair(1))
        set_and_materialize(1, discount=100)
        d = [e for e in repo.list_for_repair(1) if e['transaction_type'] == 'DISCOUNT']
        assert len(d) == 1 and d[0]['amount'] == 100, d
        assert d[0]['event_key'] == 'DISCOUNT:repair:1:initial', d
        assert d[0]['payment_date'] == today_persian(), d  # new discount: save-time stamp
        # ONLY a discount event: the discount is part of the payable, so
        # no charge correction may be emitted for the same change
        c = [e for e in repo.list_for_repair(1)
             if e['transaction_type'] == 'REPAIR_CHARGE']
        assert len(c) == 1, c
        assert len(repo.list_for_repair(1)) == before + 1

    def t6_repeat_save_no_duplicates():
        before = len(repo.list_for_repair(1))
        set_and_materialize(1, discount=100)   # same repair, same values
        set_and_materialize(1, discount=100)   # again
        after = repo.list_for_repair(1)
        assert len(after) == before, (before, len(after))

    def t7_restart_no_duplicates():
        # "startup" = init_database() again + materialize again
        init_database()
        rep = make_repair(1, discount=100)
        svc.materialize_for_repair(rep, is_new=False)
        ev = repo.list_for_repair(1)
        assert len([e for e in ev if e['transaction_type'] == 'REPAIR_CHARGE']) == 1
        assert len([e for e in ev if e['transaction_type'] == 'DISCOUNT']) == 1

    def t8_unrelated_edit_no_events():
        before = len(repo.list_for_repair(1))
        set_and_materialize(1, discount=100, notes='تعمیر صفحه', warranty='3 ماه')
        after = repo.list_for_repair(1)
        assert len(after) == before, (before, len(after))

    def t11_discount_increase_delta():
        rows_before = {e['transaction_id']: dict(e) for e in repo.list_for_repair(1)}
        set_and_materialize(1, discount=150)
        d = [e for e in repo.list_for_repair(1) if e['transaction_type'] == 'DISCOUNT']
        assert len(d) == 2, d
        assert sum(e['amount'] for e in d) == 150, d
        delta = [e for e in d if e['event_key'] == 'DISCOUNT:repair:1:delta:1']
        assert delta and delta[0]['amount'] == 50, d
        # every pre-existing row byte-identical (originals immutable)
        for e in repo.list_for_repair(1):
            if e['transaction_id'] in rows_before:
                assert rows_before[e['transaction_id']] == e, e

    def t12_discount_decrease_delta():
        set_and_materialize(1, discount=50)
        d = [e for e in repo.list_for_repair(1) if e['transaction_type'] == 'DISCOUNT']
        assert len(d) == 3, d
        assert sum(e['amount'] for e in d) == 50, d
        last = [e for e in d if e['event_key'] == 'DISCOUNT:repair:1:delta:2']
        assert last and last[0]['amount'] == -100, d  # signed reversal delta

    def t13_discount_removed():
        set_and_materialize(1, discount=0)
        d = [e for e in repo.list_for_repair(1) if e['transaction_type'] == 'DISCOUNT']
        assert len(d) == 4, d
        assert sum(e['amount'] for e in d) == 0, d
        last = [e for e in d if e['event_key'] == 'DISCOUNT:repair:1:delta:3']
        assert last and last[0]['amount'] == -50, d

    r.run('T5  discount materialization (case B)', t5_discount_materializes)
    r.run('T6  repeated saves create NO duplicates (cases C)', t6_repeat_save_no_duplicates)
    r.run('T7  restart (init + materialize) creates NO duplicates', t7_restart_no_duplicates)
    r.run('T8  unrelated field edits create NO events', t8_unrelated_edit_no_events)
    r.run('T11 discount increase -> +delta, originals immutable (case D)', t11_discount_increase_delta)
    r.run('T12 discount decrease -> signed reversal delta (case E)', t12_discount_decrease_delta)
    r.run('T13 discount removed -> reversal to zero (case F)', t13_discount_removed)

    # 16/17: historical stability under repair edits
    def t16_17_edit_does_not_mutate_history():
        # charge exists at 1,000,000; now raise the payable to 1,800,000
        rows_before = {e['transaction_id']: dict(e) for e in repo.list_for_repair(1)}
        set_and_materialize(1, discount=0, parts_cost=1400000)
        ev = repo.list_for_repair(1)
        # every pre-existing row is byte-identical
        for e in ev:
            before = rows_before.get(e['transaction_id'])
            if before is not None:
                assert before == e, (before, e)
        # exactly one correction event was appended (charge +delta 800000)
        new = [e for e in ev if e['transaction_id'] not in rows_before]
        assert len(new) == 1, new
        assert new[0]['transaction_type'] == 'REPAIR_CHARGE'
        assert new[0]['amount'] == 800000, new
        assert sum(e['amount'] for e in ev
                   if e['transaction_type'] == 'REPAIR_CHARGE') == 1800000
        # original charge row value unchanged
        orig = [e for e in ev if e['event_key'] == 'REPAIR_CHARGE:repair:1:initial'][0]
        assert orig['amount'] == 1000000, orig

    r.run('T16/17 repair edits never mutate historical events; delta appended', t16_17_edit_does_not_mutate_history)

    # 13/14/15/21: payments, refunds, balance
    def t13_14_payment_refund_functional():
        repo.create({'repair_id': 1, 'amount': 400000,
                     'payment_date': '1404/05/21', 'transaction_type': 'PAYMENT'})
        repo.create({'repair_id': 1, 'amount': 100000,
                     'payment_date': '1404/05/22', 'transaction_type': 'REFUND'})
        from services.payment_reconciliation_service import (
            PaymentReconciliationService)
        net = PaymentReconciliationService().net_paid_for_repair(1)
        assert net == 300000, net  # PAYMENT - REFUND semantics unchanged

    def t21_customer_balance():
        # F3: customer_balance delegates to the Customer Subsidiary
        # Ledger. The ledger books each row into exactly ONE column
        # (roadmap §15 footer convention), so the discount reversal
        # deltas (+100, +50 from the T11-T13 lifecycle) appear as
        # DEBITS. The balance contract is unchanged: signed, no floor.
        bal = svc.customer_balance(3)
        # repair 1: charge 1,000,000 + delta 800,000, refund 100,000,
        # discount reversal deltas 100 + 50  -> total_debit
        # payment 400,000 + discount initial/delta (100 + 50) -> total_credit
        assert bal['total_debit'] == 1000000 + 800000 + 100000 + 150, bal
        assert bal['total_credit'] == 400000 + 150, bal
        assert bal['balance'] == 1500000, bal      # signed, no floor
        assert bal['unattributed_events'] == 0, bal

    def t21b_credit_balance_no_floor():
        # customer 4: charge 1,000,000 then overpay 1,200,000
        repo.create({'repair_id': 2, 'amount': 1200000,
                     'payment_date': '1404/05/21', 'transaction_type': 'PAYMENT'})
        bal = svc.customer_balance(4)
        assert bal['balance'] == 1000000 - 1200000 == -200000, bal  # بستانکار

    def t21c_legacy_attribution_via_repair():
        # a payment row without customer_id (legacy shape) is attributed
        # via the repair's authoritative customer_id
        repo.create({'repair_id': 1, 'amount': 50000,
                     'payment_date': '1404/05/23', 'transaction_type': 'PAYMENT'})
        bal = svc.customer_balance(3)
        assert bal['balance'] == 1500000 - 50000, bal

    def t21d_unique_index_backstop():
        try:
            repo.create({'repair_id': 1, 'amount': 999,
                         'transaction_type': 'REPAIR_CHARGE',
                         'event_key': 'REPAIR_CHARGE:repair:1:initial'})
        except IntegrityError:
            return
        raise AssertionError('duplicate event_key insert was not rejected')

    r.run('T13/14 PAYMENT/REFUND behavior unchanged (net_paid)', t13_14_payment_refund_functional)
    r.run('T21  customer balance from events (signed, no floor)', t21_customer_balance)
    r.run('T21b overpayment -> negative balance (credit) preserved', t21b_credit_balance_no_floor)
    r.run('T21c legacy payment attributed via repair.customer_id', t21c_legacy_attribution_via_repair)
    r.run('T21d unique event_key index rejects duplicates', t21d_unique_index_backstop)

    # reconstruction markers
    def t_reconstructed_markers():
        legacy_like = make_repair(3, customer_id=None, receive_date='1403/01/01')
        st.save_all([repair, make_repair(2, customer_id=4, status='تحویل داده شده',
                                         delivery_date='1404/05/20'), legacy_like])
        out = svc.materialize_for_repair(legacy_like, is_new=False)
        charge = [e for e in out['created'] if e['transaction_type'] == 'REPAIR_CHARGE'][0]
        assert charge['payment_date'] == '1403/01/01', charge
        assert 'بازسازی‌شده' in charge['note'], charge

    def t_undated_reconstructed():
        ghost = make_repair(4, customer_id=None, receive_date='',
                            delivery_date='')
        st.save_all([repair, make_repair(2, customer_id=4, status='تحویل داده شده',
                                         delivery_date='1404/05/20'), ghost])
        out = svc.materialize_for_repair(ghost, is_new=False)
        charge = [e for e in out['created'] if e['transaction_type'] == 'REPAIR_CHARGE'][0]
        assert charge['payment_date'] == '', charge  # no date invented
        assert 'بازسازی‌شده' in charge['note'], charge

    r.run('T9   legacy first-touch -> policy date + reconstructed marker', t_reconstructed_markers)
    r.run('T9b  both dates empty -> undated + reconstructed (no invented date)', t_undated_reconstructed)

    # charge - discount == payable invariant, incl. the clamp case
    def t_invariant_no_clamp():
        rep = make_repair(5, customer_id=3, discount=250000)  # subtotal 1,000,000
        st.save_all([rep])
        svc.materialize_for_repair(rep, is_new=True)
        ev = repo.list_for_repair(5)
        charge = sum(e['amount'] for e in ev if e['transaction_type'] == 'REPAIR_CHARGE')
        disc = sum(e['amount'] for e in ev if e['transaction_type'] == 'DISCOUNT')
        assert charge == 1000000 and disc == 250000, ev
        assert charge - disc == payable_total(rep), (charge, disc, rep)

    def t_invariant_clamp():
        # discount (500,000) larger than the base (200,000): payable 0
        rep = make_repair(6, customer_id=3, parts_cost=200000,
                          labor_cost=0, discount=500000)
        st.save_all([rep])
        svc.materialize_for_repair(rep, is_new=True)
        ev = repo.list_for_repair(6)
        charge = sum(e['amount'] for e in ev if e['transaction_type'] == 'REPAIR_CHARGE')
        disc = sum(e['amount'] for e in ev if e['transaction_type'] == 'DISCOUNT')
        assert charge == 200000 and disc == 200000, ev  # effective discount capped
        assert charge - disc == 0 == payable_total(rep), (charge, disc)

    r.run('T18  invariant charge - discount == payable (no clamp)', t_invariant_no_clamp)
    r.run('T19  invariant holds with clamped discount (payable 0)', t_invariant_clamp)

    return r.summary()


# ---------------------------------------------------------------- phase: compat
def phase_compat():
    fresh_dir()
    r = Results()

    from core.storage.init_db import init_database
    init_database()

    from core.storage.sqlite_storage import SQLiteStorage
    from core.storage.payment_transaction_repository import (
        PaymentTransactionRepository)
    from services.financial_event_service import FinancialEventService
    from services.payment_reconciliation_service import (
        PaymentReconciliationService)
    from services.financial_summary_service import FinancialSummaryService
    from services.profit_service import ProfitService
    from services.table_service import build_table_rows
    from services.invoice_calculator import calculate_invoice_totals

    st = SQLiteStorage()
    repo = PaymentTransactionRepository()
    svc = FinancialEventService()

    repair = make_repair(1, customer_id=3, discount=0)
    st.save_all([repair])
    svc.materialize_for_repair(repair, is_new=True)
    repo.create({'repair_id': 1, 'amount': 300000,
                 'payment_date': '1404/05/21', 'transaction_type': 'PAYMENT'})

    def c1_no_ledger_semantics_kept():
        # repair 2 has ONLY a REPAIR_CHARGE event -> still NO_LEDGER
        rep2 = make_repair(2, customer_id=4)
        st.save_all([repair, rep2])
        svc.materialize_for_repair(rep2, is_new=True)
        res = PaymentReconciliationService().reconcile_repair(2)
        assert res['status'] == 'NO_LEDGER', res

    def c2_reconciliation_payment_semantics():
        res = PaymentReconciliationService().reconcile_repair(1)
        # paid snapshot 0 vs ledger 300,000 -> MISMATCH (unchanged rule)
        assert res['status'] == 'MISMATCH', res
        assert res['payment_total'] == 300000, res

    def c3_summary_service_unchanged():
        loaded = {x['id']: x for x in st.load_all()}
        summary = FinancialSummaryService().calculate(loaded[1], 1)
        assert summary['paid_amount'] == 300000, summary
        assert summary['gross_revenue'] == 1000000, summary  # gross, no tax/discount
        assert summary['remaining_amount'] == 700000, summary

    def c4_profit_service_untouched():
        loaded = {x['id']: x for x in st.load_all()}
        p = ProfitService.calculate_profit(loaded[1])
        assert p['gross_revenue'] == 1000000, p
        assert p['parts_cost'] == 350000, p          # purchase snapshot
        assert p['gross_profit'] == 650000, p        # no tax/discount influence

    def c5_history_filter_preserves_ui():
        all_events = repo.list_for_repair(1)
        history = repo.list_payment_history_for_repair(1)
        assert any(e['transaction_type'] == 'REPAIR_CHARGE' for e in all_events)
        assert all(e['transaction_type'] in ('PAYMENT', 'REFUND')
                   for e in history), history
        assert len(history) == 1, history

    def c6_table_report_regression():
        loaded = {x['id']: x for x in st.load_all()}
        fin = calculate_invoice_totals(loaded[1])
        row = build_table_rows([loaded[1]])[0]
        assert row['total_value'] == fin['total'] == 1000000, (row, fin)

    def c7_widget_history_and_status():
        os.environ['QT_QPA_PLATFORM'] = 'offscreen'
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance() or QApplication([])
        from ui.widgets.invoice_widget import InvoiceWidget
        w = InvoiceWidget()
        w.load_data(make_repair(1, customer_id=3, discount=0, paid_amount=300000))
        rows = w._payment_transactions
        assert all(t['transaction_type'] in ('PAYMENT', 'REFUND') for t in rows), rows
        assert len(rows) == 1, rows
        # payable display still the SSOT, status from final vs paid
        assert w._final_amount() == 1000000
        assert w.get_data()['payment_status'] == 'پرداخت جزئی'

    r.run('C1  REPAIR_CHARGE-only repair still reports NO_LEDGER', c1_no_ledger_semantics_kept)
    r.run('C2  reconciliation verdicts keep payment semantics', c2_reconciliation_payment_semantics)
    r.run('C3  FinancialSummaryService unchanged (ledger-wins, gross)', c3_summary_service_unchanged)
    r.run('C4  ProfitService untouched (shop economics intact)', c4_profit_service_untouched)
    r.run('C5  payment-history read returns PAYMENT/REFUND only', c5_history_filter_preserves_ui)
    r.run('C6  table/report totals unaffected by financial events', c6_table_report_regression)
    r.run('C7  InvoiceWidget history + status unchanged with events present', c7_widget_history_and_status)

    return r.summary()


# ---------------------------------------------------------------- phase: deletion
def phase_deletion():
    fresh_dir()
    r = Results()

    from core.storage.init_db import init_database
    init_database()

    from core.storage.sqlite_storage import SQLiteStorage
    from core.storage.payment_transaction_repository import (
        PaymentTransactionRepository)
    from services.financial_event_service import FinancialEventService

    st = SQLiteStorage()
    repo = PaymentTransactionRepository()
    svc = FinancialEventService()

    charged = make_repair(1, customer_id=3)
    payment_only = make_repair(2, customer_id=3)  # legacy-style: payments, no charge
    clean = make_repair(3, customer_id=4)
    st.save_all([charged, payment_only, clean])
    svc.materialize_for_repair(charged, is_new=True)
    repo.create({'repair_id': 2, 'amount': 250000,
                 'payment_date': '1404/05/21', 'transaction_type': 'PAYMENT'})

    def d1_charged_repair_blocked():
        assert svc.has_events_for_repair(1) is True

    def d2_payment_only_repair_blocked():
        # legacy payment rows also block deletion (NEW-1 orphan risk)
        assert svc.has_events_for_repair(2) is True

    def d3_eventless_repair_deletable():
        assert svc.has_events_for_repair(3) is False

    def d4_batch_split():
        deletable, blocked = svc.filter_deletable_repairs([1, 2, 3, 99])
        assert deletable == [3, 99], deletable
        assert blocked == [1, 2], blocked

    def d5_deletion_leaves_events_intact():
        # simulating the app flow: only deletable ids are removed
        deletable, blocked = svc.filter_deletable_repairs([1, 2, 3])
        assert deletable == [3] and blocked == [1, 2]
        st.save_all([charged, payment_only])  # repair 3 removed
        # events of kept repairs are untouched
        assert svc.has_events_for_repair(1) and svc.has_events_for_repair(2)
        assert len(repo.list_for_repair(1)) == 1
        assert len(repo.list_for_repair(2)) == 1

    r.run('D1  repair with REPAIR_CHARGE is deletion-blocked', d1_charged_repair_blocked)
    r.run('D2  repair with PAYMENT history is deletion-blocked', d2_payment_only_repair_blocked)
    r.run('D3  repair without events stays deletable', d3_eventless_repair_deletable)
    r.run('D4  batch deletion splits deletable vs blocked', d4_batch_split)
    r.run('D5  guarded deletion leaves financial history intact', d5_deletion_leaves_events_intact)

    return r.summary()


# ---------------------------------------------------------------- phase: legacy
def phase_legacy():
    fresh_dir()

    # Pre-F2 database: payment_transaction WITHOUT customer_id/event_key
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
    conn.execute(
        "INSERT INTO customer (id, customer_code, full_name, phone) "
        "VALUES (1, 'C000001', 'علی رضایی', '09111111111')")
    # legacy repair with discount and paid_amount, old dates
    conn.execute(
        "INSERT INTO repairs (id, customer_name, phone, parts_cost, labor_cost, "
        "tax, discount, status, receive_date, delivery_date) "
        "VALUES (1, 'علی رضایی', '09111111111', 600000, 400000, 0, 100000, "
        "'تحویل داده شده', '1403/02/10', '1403/02/20')")
    conn.execute(
        "INSERT INTO payment_transaction (repair_id, amount, payment_method, "
        "payment_date, transaction_type, created_at, note) "
        "VALUES (1, 500000, 'نقدی', '1403/02/15', 'PAYMENT', '2025-05-05 10:00:00', "
        "'مهاجرت پرداخت قدیمی')")
    conn.commit()
    conn.close()

    from core.storage.init_db import init_database
    init_database()

    from core.storage.sqlite_storage import SQLiteStorage
    from core.storage.payment_transaction_repository import (
        PaymentTransactionRepository)
    from services.financial_event_service import FinancialEventService

    r = Results()
    repo = PaymentTransactionRepository()
    svc = FinancialEventService()

    def l1_migration_non_destructive():
        legacy = repo.list_for_repair(1)
        assert len(legacy) == 1, legacy
        row = legacy[0]
        assert row['amount'] == 500000 and row['transaction_type'] == 'PAYMENT'
        assert row['customer_id'] is None and row['event_key'] is None, row

    def l2_first_touch_materializes_reconstructed():
        loaded = {x['id']: x for x in SQLiteStorage().load_all()}
        rep = loaded[1]
        assert rep['customer_id'] == 1  # F1.5 backfill
        out = svc.materialize_for_repair(rep, is_new=False)
        types = sorted(e['transaction_type'] for e in out['created'])
        assert types == ['DISCOUNT', 'REPAIR_CHARGE'], out
        charge = [e for e in out['created']
                  if e['transaction_type'] == 'REPAIR_CHARGE'][0]
        # delivered -> delivery_date policy (F1.5), reconstructed marker
        assert charge['payment_date'] == '1403/02/20', charge
        assert 'بازسازی‌شده' in charge['note'], charge
        assert charge['amount'] == 1000000, charge  # 600k + 400k, tax 0
        disc = [e for e in out['created'] if e['transaction_type'] == 'DISCOUNT'][0]
        assert disc['amount'] == 100000 and 'بازسازی‌شده' in disc['note'], disc

    def l3_second_touch_no_duplicates():
        loaded = {x['id']: x for x in SQLiteStorage().load_all()}
        out = svc.materialize_for_repair(loaded[1], is_new=False)
        assert out['skipped'], out

    def l4_balance_attributed():
        bal = svc.customer_balance(1)
        # debit 1,000,000; credit 100,000 discount + 500,000 legacy payment
        assert bal['total_debit'] == 1000000, bal
        assert bal['total_credit'] == 600000, bal
        assert bal['balance'] == 400000, bal
        assert bal['unattributed_events'] == 0, bal

    r.run('L1  legacy payment rows migrate non-destructively (NULLs kept)', l1_migration_non_destructive)
    r.run('L2  first post-F2 save materializes reconstructed events', l2_first_touch_materializes_reconstructed)
    r.run('L3  second save of legacy repair creates NO duplicates', l3_second_touch_no_duplicates)
    r.run('L4  legacy payment attributed via repair.customer_id for balance', l4_balance_attributed)

    return r.summary()


# ---------------------------------------------------------------- phase: realdb
def phase_realdb():
    work = tempfile.mkdtemp(prefix='f2_realdb_')
    shutil.copyfile(REAL_DB, os.path.join(work, 'repair_manager.db'))
    os.chdir(work)
    sys.path.insert(0, PROJECT_ROOT)

    r = Results()

    ORIGINAL_COLUMNS = (
        'transaction_id, repair_id, amount, payment_method, '
        'payment_date, transaction_type, note'
    )

    def pay_snapshot():
        conn = sqlite3.connect('repair_manager.db')
        rows = conn.execute(
            f'SELECT {ORIGINAL_COLUMNS} FROM payment_transaction '
            'ORDER BY transaction_id').fetchall()
        conn.close()
        return rows

    def event_counts():
        conn = sqlite3.connect('repair_manager.db')
        counts = dict(conn.execute(
            'SELECT transaction_type, COUNT(*) FROM payment_transaction '
            'GROUP BY transaction_type').fetchall())
        conn.close()
        return counts

    pre_pay = pay_snapshot()

    from core.storage.init_db import init_database
    init_database()          # startup #1 (migration)
    init_database()          # startup #2 (idempotency)

    post_pay = pay_snapshot()

    conn = sqlite3.connect('repair_manager.db')
    cols = [c[1] for c in conn.execute(
        'PRAGMA table_info(payment_transaction)').fetchall()]
    idx = [
        x[0] for x in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND "
            "tbl_name='payment_transaction'").fetchall()
    ]
    ext = conn.execute(
        'SELECT customer_id, event_key FROM payment_transaction '
        'ORDER BY transaction_id').fetchall()
    rep_map = dict(conn.execute(
        'SELECT id, customer_id FROM repairs ORDER BY id').fetchall())
    conn.close()

    def f1_schema():
        assert 'customer_id' in cols and 'event_key' in cols, cols
        assert 'ux_payment_transaction_event_key' in idx, idx

    def f2_rows_untouched():
        assert pre_pay == post_pay
        assert all(x[0] is None and x[1] is None for x in ext)
        assert len(post_pay) == 9

    def f3_no_auto_backfill():
        counts = event_counts()
        assert counts.get('REPAIR_CHARGE', 0) == 0, counts
        assert counts.get('DISCOUNT', 0) == 0, counts
        assert counts.get('PAYMENT') == 8 and counts.get('REFUND') == 1, counts

    def f4_first_save_then_repeat():
        from core.storage.sqlite_storage import SQLiteStorage
        from services.financial_event_service import FinancialEventService
        from core.storage.payment_transaction_repository import (
            PaymentTransactionRepository)
        st = SQLiteStorage()
        svc = FinancialEventService()
        repo = PaymentTransactionRepository()
        loaded = {x['id']: x for x in st.load_all()}
        rep = loaded[1]  # legacy repair, customer backfilled by F1.5
        out1 = svc.materialize_for_repair(rep, is_new=False)
        assert [e['transaction_type'] for e in out1['created']] == ['REPAIR_CHARGE'], out1
        out2 = svc.materialize_for_repair(rep, is_new=False)
        assert out2['skipped'], out2
        charges = [e for e in repo.list_for_repair(1)
                   if e['transaction_type'] == 'REPAIR_CHARGE']
        assert len(charges) == 1, charges
        # F1.5 mapping intact and stamped on the event
        assert charges[0]['customer_id'] == rep_map[1] == 2, (charges, rep_map)

    def f5_f15_customer_backfill_intact():
        assert rep_map == {1: 2, 2: 3, 3: 4, 4: 4, 5: 3}, rep_map

    r.run('F2.1 event columns + unique index added to existing DB', f1_schema)
    r.run('F2.2 existing payment rows untouched (values + NULL extensions)', f2_rows_untouched)
    r.run('F2.3 NO automatic event backfill on startup (twice)', f3_no_auto_backfill)
    r.run('F2.4 first save materializes once; repeat save is a no-op', f4_first_save_then_repeat)
    r.run('F2.5 F1.5 customer_id backfill mapping intact', f5_f15_customer_backfill_intact)

    return r.summary()


RUNNERS = {
    'events': phase_events,
    'compat': phase_compat,
    'deletion': phase_deletion,
    'legacy': phase_legacy,
    'realdb': phase_realdb,
}


def main():
    if '--phase' in sys.argv:
        return RUNNERS[sys.argv[sys.argv.index('--phase') + 1]]()
    failures = 0
    for phase in ('events', 'compat', 'deletion', 'legacy', 'realdb'):
        print(f"\n########## PHASE {phase} ##########")
        failures += run_phase(phase)
    print(f"\n=== F2 validation: "
          f"{'ALL PHASES PASSED' if failures == 0 else str(failures) + ' phase(s) failed'} ===")
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
