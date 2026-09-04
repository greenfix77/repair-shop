"""F1.5 targeted validation suite (FINANCIAL_F1_5_IMPLEMENTATION_REPORT.md).

Run:  python services/test_financial_f1_5.py

The project database path is CWD-relative (core/storage/database.py),
so every phase runs in a SEPARATE subprocess with a fresh temporary
working directory. The real ``repair_manager.db`` is never touched;
phase ``realdb`` works on a COPY of it.

Phases
  core    A) customer_id round-trips (model / service / storage)
          B) authoritative Customer Payable formula (service level)
          C) historical snapshot integrity vs catalog price changes
          D) payments / refunds / net_paid_for_repair semantics
  ui      B) InvoiceWidget + invoice_generator parity with the SSOT
  legacy  E) legacy migration: schema upgrade + conservative backfill
  realdb  F) compatibility against a copy of the real database
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


# ---------------------------------------------------------------- utils
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
    d = tempfile.mkdtemp(prefix='f15_')
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


# ---------------------------------------------------------------- phase: core
def phase_core():
    fresh_dir()
    r = Results()

    # ---- A) customer_id on the model --------------------------------
    from core.models import Repair

    def a1_roundtrip():
        rep = Repair.from_dict({'id': 1, 'customer_id': 7, 'customer_name': 'x'})
        d = rep.to_dict()
        assert d['customer_id'] == 7, d
        rep2 = Repair.from_dict(d)
        assert rep2.customer_id == 7 and rep2.to_dict()['customer_id'] == 7

    def a2_coercion():
        assert Repair.from_dict({'customer_id': '9'}).customer_id == 9
        assert Repair.from_dict({'customer_id': 0}).customer_id is None
        assert Repair.from_dict({'customer_id': ''}).customer_id is None
        assert Repair.from_dict({'customer_id': None}).customer_id is None
        assert Repair.from_dict({'customer_id': 'abc'}).customer_id is None
        assert Repair.from_dict({}).customer_id is None

    def a3_add_repair_preserves():
        from services.repair_manager_service import add_repair
        out = add_repair([], {'customer_id': 5, 'customer_name': 'Ali',
                              'phone': '0911'})
        assert out[0]['customer_id'] == 5, out

    def a4_update_preserves():
        from services.repair_manager_service import update_repair
        existing = {'id': 1, 'customer_id': 5, 'customer_name': 'Ali'}
        # edit without a customer reference must not drop the stored link
        out = update_repair([dict(existing)], 1, {'brand': 'dell'})
        assert out[0]['customer_id'] == 5, out
        # explicit new customer wins
        out = update_repair([dict(existing)], 1, {'customer_id': 9})
        assert out[0]['customer_id'] == 9, out
        # explicit None keeps the stored one
        out = update_repair([dict(existing)], 1, {'customer_id': None})
        assert out[0]['customer_id'] == 5, out

    def a5_storage_roundtrip():
        from core.storage.sqlite_storage import SQLiteStorage
        st = SQLiteStorage()
        base = {
            'customer_name': 'Ali', 'phone': '09111111111', 'brand': 'dell',
            'model': 'xps', 'issue': 'np', 'parts_cost': 100, 'labor_cost': 200,
            'tax': 9.0, 'discount': 10, 'status': 'در انتظار',
            'receive_date': '1404/01/01', 'delivery_date': '',
            'notes': '', 'warranty': '', 'service_lines': [], 'part_lines': [],
            'additional_charges': [],
        }
        st.save_all([dict(base, id=1, customer_id=5),
                     dict(base, id=2, customer_id=None)])
        loaded = {x['id']: x for x in st.load_all()}
        assert loaded[1]['customer_id'] == 5, loaded[1]
        assert loaded[2]['customer_id'] is None, loaded[2]

    def a6_full_chain_no_data_loss():
        from services.repair_manager_service import add_repair
        from core.storage.sqlite_storage import SQLiteStorage
        dialog_dict = {
            'customer_id': 3, 'customer_name': 'Sara', 'phone': '09123333333',
            'brand': 'hp', 'model': 'pavilion', 'issue': 'screen',
            'status': 'در حال تعمیر', 'receive_date': '1404/05/01',
            'delivery_date': '', 'parts_cost': 150000, 'labor_cost': 250000,
            'tax': 9.0, 'discount': 50000, 'notes': 'n', 'warranty': '1 ماه',
            'paid_amount': 100000, 'payment_status': 'پرداخت جزئی',
            'payment_method': 'کارت‌خوان (POS)', 'payment_date': '1404/05/02',
            'financial_notes': 'fn',
            'service_lines': [{'service_id': None, 'service_name_snapshot': 's',
                               'quantity': 1, 'unit_price': 250000,
                               'total_price': 250000}],
            'part_lines': [{'part_id': 1, 'part_name_snapshot': 'RAM',
                            'quantity': 1, 'unit_price': 150000,
                            'total_price': 150000,
                            'purchase_price_snapshot': 90000}],
            'additional_charges': [{'charge_id': None,
                                    'charge_name_snapshot': 'شارژ',
                                    'quantity': 1, 'unit_price': 20000,
                                    'total_price': 20000}],
        }
        added = add_repair([], dict(dialog_dict))[0]
        st = SQLiteStorage()
        st.save_all([added])
        loaded = st.load_all()[0]
        assert loaded['customer_id'] == 3, loaded['customer_id']
        # strip the DB-generated primary keys on child lines before
        # comparing (storage assigns line ids on load — not data loss)
        saved = dict(added)
        loaded_norm = dict(loaded)
        for key in ('service_lines', 'part_lines', 'additional_charges'):
            loaded_norm[key] = [
                {k: v for k, v in line.items() if k != 'id'}
                for line in loaded_norm.get(key, [])
            ]
        for key, value in saved.items():
            assert loaded_norm.get(key) == value, (
                f'field {key!r} lost: saved={value!r} loaded={loaded_norm.get(key)!r}'
            )

    r.run('A1 Repair.from_dict/to_dict preserves customer_id', a1_roundtrip)
    r.run('A2 customer_id coercion (str ok / empty/0/invalid -> None)', a2_coercion)
    r.run('A3 add_repair preserves customer_id', a3_add_repair_preserves)
    r.run('A4 update_repair never drops stored customer_id', a4_update_preserves)
    r.run('A5 SQLiteStorage save/load customer_id round-trip', a5_storage_roundtrip)
    r.run('A6 full chain dialog->service->storage->load, no data loss',
          a6_full_chain_no_data_loss)

    # ---- B) authoritative payable (service level) --------------------
    from services.invoice_calculator import (
        calculate_invoice_totals, payable_total)

    def b1():
        fin = calculate_invoice_totals({'labor_cost': 100})
        assert fin['subtotal'] == 100 and fin['total'] == 100, fin

    def b2():
        fin = calculate_invoice_totals({'parts_cost': 200})
        assert fin['subtotal'] == 200 and fin['total'] == 200, fin

    def b3():
        fin = calculate_invoice_totals({'parts_cost': 200, 'labor_cost': 100})
        assert fin['subtotal'] == 300 and fin['total'] == 300, fin

    def b4():
        fin = calculate_invoice_totals({
            'parts_cost': 200, 'labor_cost': 100,
            'additional_charges': [{'total_price': 50}, {'total_price': 25}],
        })
        assert fin['additional_charges'] == 75, fin
        assert fin['subtotal'] == 375 and fin['total'] == 375, fin

    def b5():
        fin = calculate_invoice_totals({
            'labor_cost': 100, 'additional_charges': [{'amount': 40}],
        })
        assert fin['additional_charges'] == 40 and fin['total'] == 140, fin

    def b6():
        fin = calculate_invoice_totals(
            {'parts_cost': 100, 'labor_cost': 200, 'discount': 30, 'tax': 9.0})
        # prediscount 300 -> after_discount 270 -> tax int(24.3)=24 -> 294
        assert fin['after_discount'] == 270, fin
        assert fin['tax_amount'] == 24, fin
        assert fin['total'] == 294, fin

    def b7():
        fin = calculate_invoice_totals({'labor_cost': 33333, 'tax': 15.0})
        # int(4999.95) == 4999 (truncation, matching the widget)
        assert fin['tax_amount'] == 4999, fin
        assert fin['total'] == 38332, fin

    def b8():
        fin = calculate_invoice_totals(
            {'parts_cost': 100, 'discount': 500, 'tax': 9.0})
        assert fin['after_discount'] == 0, fin
        assert fin['tax_amount'] == 0 and fin['total'] == 0, fin

    def b9():
        fin = calculate_invoice_totals({
            'parts_cost': 100, 'labor_cost': 200,
            'additional_charges': [{'total_price': 50}],
            'discount': 80, 'tax': 10.0,
        })
        assert fin['subtotal'] == 350 and fin['after_discount'] == 270, fin
        assert fin['tax_amount'] == 27 and fin['total'] == 297, fin

    def b10():
        assert calculate_invoice_totals({})['total'] == 0
        assert calculate_invoice_totals(None)['total'] == 0
        fin = calculate_invoice_totals(
            {'parts_cost': '100', 'labor_cost': None, 'tax': 'abc',
             'discount': 'x', 'additional_charges': 'junk'})
        assert fin['parts_cost'] == 100 and fin['tax_rate'] == 0.0, fin
        assert fin['total'] == 100, fin

    def b11():
        fin = calculate_invoice_totals({
            'labor_cost': 100, 'additional_charges': [{'total_price': 0}],
        })
        assert fin['total'] == 100, fin

    def b12():
        from services.calculations import calculate_invoice
        sub, tax_amount, total = calculate_invoice(100, 200, 9.0, 30)
        fin = calculate_invoice_totals(
            {'parts_cost': 100, 'labor_cost': 200, 'tax': 9.0, 'discount': 30})
        assert (sub, tax_amount, total) == (
            fin['subtotal'], fin['tax_amount'], fin['total']), (sub, tax_amount, total)

    def b13():
        from services.table_service import build_table_rows
        repair = {
            'id': 1, 'customer_name': 'x', 'phone': '', 'brand': '', 'model': '',
            'issue': '', 'status': 'در انتظار', 'receive_date': '',
            'delivery_date': '', 'parts_cost': 200, 'labor_cost': 100,
            'tax': 9.0, 'discount': 30,
            'additional_charges': [{'total_price': 50}],
        }
        fin = calculate_invoice_totals(repair)
        row = build_table_rows([repair])[0]
        assert row['total_value'] == fin['total'], (row, fin)

    def b14():
        assert payable_total({'labor_cost': 7}) == 7

    r.run('B1  payable: services only', b1)
    r.run('B2  payable: parts only', b2)
    r.run('B3  payable: services + parts', b3)
    r.run('B4  payable: additional charges included', b4)
    r.run('B5  payable: legacy charge amount fallback', b5)
    r.run('B6  payable: discount applied BEFORE tax', b6)
    r.run('B7  payable: tax int truncation', b7)
    r.run('B8  payable: discount larger than base clamps to 0', b8)
    r.run('B9  payable: full combo', b9)
    r.run('B10 payable: malformed/empty inputs degrade to 0', b10)
    r.run('B11 payable: zero-total charge lines ignored', b11)
    r.run('B12 calculations.calculate_invoice delegates to SSOT', b12)
    r.run('B13 table_service rows use the SSOT total', b13)
    r.run('B14 payable_total helper', b14)

    # ---- C) historical snapshots ------------------------------------
    def c1():
        from core.storage.sqlite_storage import SQLiteStorage
        from core.storage.database import SessionLocal
        from core.storage.part_model_db import PartDB
        from core.storage.init_db import init_database
        init_database()
        session = SessionLocal()
        try:
            session.add(PartDB(id=1, name='RAM', purchase_price=1000,
                               sale_price=1500, default_sale_price=1500))
            session.commit()
        finally:
            session.close()

        repair = {
            'id': 1, 'customer_id': 3, 'customer_name': 'Ali',
            'phone': '09111111111', 'brand': 'd', 'model': 'm', 'issue': 'i',
            'parts_cost': 1500, 'labor_cost': 0, 'tax': 9.0, 'discount': 0,
            'status': 'در انتظار', 'receive_date': '1404/01/01',
            'delivery_date': '', 'notes': '', 'warranty': '',
            'service_lines': [],
            'part_lines': [{'id': 1, 'part_id': 1, 'part_name_snapshot': 'RAM',
                            'quantity': 1, 'unit_price': 1500,
                            'total_price': 1500,
                            'purchase_price_snapshot': 1000}],
            'additional_charges': [],
        }
        st = SQLiteStorage()
        st.save_all([repair])

        # change catalog prices AFTER the repair was saved
        session = SessionLocal()
        try:
            row = session.query(PartDB).filter_by(id=1).first()
            row.purchase_price = 5000
            row.sale_price = 9000
            row.default_sale_price = 9000
            session.commit()
        finally:
            session.close()

        loaded = st.load_all()[0]
        line = loaded['part_lines'][0]
        assert line['unit_price'] == 1500, line
        assert line['purchase_price_snapshot'] == 1000, line
        assert line['total_price'] == 1500, line
        assert loaded['parts_cost'] == 1500, loaded
        # payable still uses historical snapshots, not catalog prices
        # (1500 sale + int(1500 * 9%) tax = 1635)
        assert payable_total(loaded) == 1635, loaded

    r.run('C1  catalog price change never rewrites repair history', c1)

    # ---- D) payments --------------------------------------------------
    def clear_ledger():
        """Wipe payment_transaction rows (the suite's seeds with
        paid_amount > 0 trigger the app's own legacy back-fill on the
        next init — that behaviour is covered by the realdb phase)."""
        from core.storage.database import SessionLocal
        from core.storage.payment_transaction_model_db import (
            PaymentTransactionDB)
        s = SessionLocal()
        try:
            s.query(PaymentTransactionDB).delete()
            s.commit()
        finally:
            s.close()

    def make_repos():
        from core.storage.payment_transaction_repository import (
            PaymentTransactionRepository)
        from services.payment_reconciliation_service import (
            PaymentReconciliationService)
        return PaymentTransactionRepository(), PaymentReconciliationService()

    def seed_repair(st, repair_id, paid_snapshot):
        st.save_all([{
            'id': repair_id, 'customer_id': None,
            'customer_name': f'c{repair_id}', 'phone': '', 'brand': '',
            'model': '', 'issue': '', 'parts_cost': 100000, 'labor_cost': 0,
            'tax': 0.0, 'discount': 0, 'status': 'در انتظار',
            'receive_date': '1404/01/01', 'delivery_date': '', 'notes': '',
            'warranty': '', 'paid_amount': paid_snapshot,
            'payment_status': 'پرداخت جزئی', 'payment_method': 'نقدی',
            'payment_date': '', 'financial_notes': '', 'service_lines': [],
            'part_lines': [{'id': 1, 'part_id': None, 'part_name_snapshot': 'p',
                            'quantity': 1, 'unit_price': 100000,
                            'total_price': 100000,
                            'purchase_price_snapshot': 60000}],
            'additional_charges': [],
        }])

    def d1():
        from core.storage.sqlite_storage import SQLiteStorage
        st = SQLiteStorage()
        clear_ledger()
        seed_repair(st, 1, 120)
        repo, svc = make_repos()
        repo.create({'repair_id': 1, 'amount': 100,
                     'payment_date': '1404/01/01', 'transaction_type': 'PAYMENT'})
        repo.create({'repair_id': 1, 'amount': 50,
                     'payment_date': '1404/01/02', 'transaction_type': 'PAYMENT'})
        assert len(repo.list_for_repair(1)) == 2
        assert svc.net_paid_for_repair(1) == 150

    def d2():
        from core.storage.sqlite_storage import SQLiteStorage
        st = SQLiteStorage()
        clear_ledger()
        seed_repair(st, 2, 50)
        repo, svc = make_repos()
        repo.create({'repair_id': 2, 'amount': 50,
                     'payment_date': '1404/01/03', 'transaction_type': 'PAYMENT'})
        repo.create({'repair_id': 2, 'amount': 20,
                     'payment_date': '1404/01/04', 'transaction_type': 'REFUND'})
        assert svc.net_paid_for_repair(2) == 30

    def d3():
        from core.storage.sqlite_storage import SQLiteStorage
        st = SQLiteStorage()
        clear_ledger()
        seed_repair(st, 3, 120)
        repo, svc = make_repos()
        repo.create({'repair_id': 3, 'amount': 120,
                     'payment_date': '1404/01/05', 'transaction_type': 'PAYMENT'})
        res = svc.reconcile_repair(3)
        assert res['status'] == 'MATCH', res
        # snapshot drift is flagged (diagnostic only)
        rows = st.load_all()
        rows[0]['paid_amount'] = 999
        st.save_all(rows)
        res = svc.reconcile_repair(3)
        assert res['status'] == 'MISMATCH', res

    def d4():
        repo, svc = make_repos()
        repo.create({'repair_id': 3, 'amount': 40,
                     'payment_date': '1404/01/06',
                     'transaction_type': 'ADJUSTMENT'})
        # authoritative paid: PAYMENT - REFUND (ADJUSTMENT excluded)
        assert svc.net_paid_for_repair(3) == 120
        # reconciliation verdict still adds ADJUSTMENT (documented F1.5
        # divergence, pending the ADJUSTMENT direction decision)
        res = svc.reconcile_repair(3)
        assert res['net_ledger_amount'] == 160, res
        assert res['status'] == 'MISMATCH', res

    def d5():
        from core.storage.sqlite_storage import SQLiteStorage
        st = SQLiteStorage()
        clear_ledger()
        seed_repair(st, 4, 50)
        repo, svc = make_repos()
        repo.create({'repair_id': 4, 'amount': 50,
                     'payment_date': '1404/01/07', 'transaction_type': 'PAYMENT'})
        repo.create({'repair_id': 4, 'amount': 80,
                     'payment_date': '1404/01/08', 'transaction_type': 'REFUND'})
        assert svc.net_paid_for_repair(4) == 0  # zero-floor (NEW-2 kept)

    def d6():
        from core.storage.sqlite_storage import SQLiteStorage
        st = SQLiteStorage()
        clear_ledger()
        seed_repair(st, 5, 0)
        repo, svc = make_repos()
        assert svc.net_paid_for_repair(5) == 0
        assert svc.reconcile_repair(5)['status'] == 'NO_LEDGER'

    def d7():
        from services.financial_summary_service import FinancialSummaryService
        from core.storage.sqlite_storage import SQLiteStorage
        st = SQLiteStorage()
        clear_ledger()
        seed_repair(st, 6, 0)
        summary = FinancialSummaryService().calculate(st.load_all()[-1], 6)
        # paid comes from the ledger; remaining/status stay gross-based
        assert summary['paid_amount'] == 0
        assert summary['gross_revenue'] == 100000
        assert summary['remaining_amount'] == 100000
        assert summary['payment_status'] == 'پرداخت نشده'

    r.run('D1  single + multiple payments accumulate', d1)
    r.run('D2  refund reduces net paid', d2)
    r.run('D3  reconciliation MATCH / MISMATCH verdicts', d3)
    r.run('D4  ADJUSTMENT divergence pinned (paid excludes, verdict adds)', d4)
    r.run('D5  over-refund floors at 0 (NEW-2 behaviour kept)', d5)
    r.run('D6  repair without ledger -> NO_LEDGER', d6)
    r.run('D7  FinancialSummaryService keeps ledger-wins semantics', d7)

    return r.summary()


# ---------------------------------------------------------------- phase: ui
def phase_ui():
    fresh_dir()
    r = Results()
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'

    from core.storage.init_db import init_database
    init_database()

    from PyQt5.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from ui.widgets.invoice_widget import InvoiceWidget
    from services.invoice_calculator import calculate_invoice_totals

    def widget_parity():
        w = InvoiceWidget()
        repair = {
            'id': 1,
            'service_lines': [{'service_id': None, 'service_name_snapshot': 's',
                               'quantity': 1, 'unit_price': 200000,
                               'total_price': 200000}],
            'part_lines': [{'part_id': 1, 'part_name_snapshot': 'p',
                            'quantity': 1, 'unit_price': 100000,
                            'total_price': 100000,
                            'purchase_price_snapshot': 60000}],
            'additional_charges': [{'charge_id': None,
                                    'charge_name_snapshot': 'c',
                                    'quantity': 1, 'unit_price': 50000,
                                    'total_price': 50000}],
            'discount': 30000, 'tax': 9.0, 'paid_amount': 0,
        }
        w.load_data(repair)
        fin = calculate_invoice_totals({
            'parts_cost': 100000, 'labor_cost': 200000,
            'additional_charges': repair['additional_charges'],
            'tax': 9.0, 'discount': 30000,
        })
        # prediscount 350000 -> after_discount 320000 -> tax 28800 -> 348800
        assert fin['subtotal'] == 350000 and fin['total'] == 348800, fin
        # label-driven path
        w._recalculate()
        label_value = int(w._final_amount_label.text().replace(',', ''))
        assert label_value == fin['total'], (label_value, fin['total'])
        # quick-fill path
        assert w._final_amount() == fin['total']
        # get_data parity
        data = w.get_data()
        assert data['parts_cost'] == 100000 and data['labor_cost'] == 200000
        assert data['payment_status'] == 'پرداخت نشده'
        # paid == final -> settled
        w._paid_input.setValue(fin['total'])
        w._update_payment()
        assert w.get_data()['payment_status'] == 'تسویه شده'

    def generator_uses_ssot():
        from services.invoice_generator import generate_web_invoice_html
        repair = {
            'id': 1, 'customer_name': 'Ali', 'phone': '0911', 'brand': 'd',
            'model': 'm', 'issue': 'i', 'status': 'تعمیر شده',
            'receive_date': '1404/01/01', 'delivery_date': '',
            'parts_cost': 200, 'labor_cost': 100, 'tax': 9.0, 'discount': 30,
            'notes': '', 'warranty': '',
            'additional_charges': [{'total_price': 50}],
        }
        settings = {'shop_name': 'Test Shop', 'logo': '',
                    'invoice_logo_size': 96, 'address': '', 'phone': '',
                    'mobile': '', 'email': '', 'website': ''}
        fin = calculate_invoice_totals(repair)
        html = generate_web_invoice_html(repair, settings)
        assert f"{int(fin['total']):,}" in html, fin
        assert f"{int(fin['tax_amount']):,}" in html, fin

    r.run('B15 InvoiceWidget payable == SSOT (label/quick-fill/get_data)',
          widget_parity)
    r.run('B16 invoice_generator HTML shows SSOT payable', generator_uses_ssot)
    return r.summary()


# ---------------------------------------------------------------- phase: legacy
def phase_legacy():
    fresh_dir()

    # Simulate a PRE-customer_id database: legacy-shaped tables only.
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
        customer_code VARCHAR UNIQUE,
        full_name VARCHAR,
        phone VARCHAR UNIQUE,
        email VARCHAR, website VARCHAR, national_id VARCHAR, address VARCHAR,
        city VARCHAR, province VARCHAR, postal_code VARCHAR, notes VARCHAR,
        created_at VARCHAR, updated_at VARCHAR
    );
    """)
    conn.executemany(
        "INSERT INTO customer (id, customer_code, full_name, phone) "
        "VALUES (?,?,?,?)",
        [
            (1, 'C000001', 'علی رضایی', '09111111111'),
            (2, 'C000002', 'احمد خزایی', None),
            (3, 'C000003', 'سارا محمدی', '09133333333'),
            (4, 'C000004', 'سارا محمدی', '09144444444'),
        ])
    conn.executemany(
        "INSERT INTO repairs (id, customer_name, phone) VALUES (?,?,?)",
        [
            (1, 'علی رضایی', '09111111111'),   # R1 unique phone -> 1
            (2, 'احمد خزایی', ''),             # R2 unique name  -> 2
            (3, 'سارا محمدی', ''),             # ambiguous name  -> NULL
            (4, 'ناشناس', ''),                 # no match        -> NULL
            (5, 'علی رضایی', '09199999999'),   # phone unmatched -> name -> 1
            (6, 'سارا محمدی', ''),             # pre-set id kept
        ])
    # simulate a row that already carries a customer_id (never overwritten)
    conn.commit()
    conn.close()

    from core.storage.init_db import (
        init_database, _backfill_repair_customer_ids)
    init_database()

    # pre-set customer_id AFTER init for the never-overwrite check, then
    # prove idempotency by running the backfill again
    conn = sqlite3.connect('repair_manager.db')
    conn.execute("UPDATE repairs SET customer_id = 3 WHERE id = 6")
    conn.commit()
    conn.close()
    _backfill_repair_customer_ids()

    conn = sqlite3.connect('repair_manager.db')
    rows = {r[0]: r for r in conn.execute(
        'SELECT id, customer_id, customer_name, phone FROM repairs').fetchall()}
    cols = [c[1] for c in conn.execute('PRAGMA table_info(repairs)').fetchall()]
    conn.close()

    r = Results()

    def e1():
        assert 'customer_id' in cols, cols

    def e2():
        assert rows[1][1] == 1, rows[1]     # R1 unique phone
        assert rows[2][1] == 2, rows[2]     # R2 unique name
        assert rows[3][1] is None, rows[3]  # ambiguous -> unresolved
        assert rows[4][1] is None, rows[4]  # no match -> unresolved
        assert rows[5][1] == 1, rows[5]     # phone no-match, unique name
        assert rows[6][1] == 3, rows[6]     # pre-set never overwritten

    def e3():
        assert rows[1][2] == 'علی رضایی' and rows[1][3] == '09111111111'
        assert rows[2][2] == 'احمد خزایی' and rows[2][3] == ''
        assert rows[4][2] == 'ناشناس'

    def e4():
        _backfill_repair_customer_ids()
        conn = sqlite3.connect('repair_manager.db')
        rows2 = {x[0]: x[1] for x in conn.execute(
            'SELECT id, customer_id FROM repairs').fetchall()}
        conn.close()
        assert rows2 == {k: v[1] for k, v in rows.items()}, rows2

    def e5():
        from core.storage.sqlite_storage import SQLiteStorage
        from core.models import Repair
        loaded = SQLiteStorage().load_all()
        assert len(loaded) == 6
        by_id = {x['id']: x for x in loaded}
        assert by_id[3]['customer_id'] is None
        assert by_id[4]['customer_id'] is None
        assert by_id[1]['customer_id'] == 1
        # legacy dict without customer_id flows through the model safely
        legacy = dict(by_id[4])
        legacy.pop('customer_id', None)
        assert Repair.from_dict(legacy).customer_id is None
        # saving unresolved rows keeps them unresolved
        st = SQLiteStorage()
        st.save_all(list(by_id.values()))
        again = {x['id']: x['customer_id'] for x in st.load_all()}
        assert again[3] is None and again[4] is None and again[1] == 1, again

    r.run('E1  legacy DB gains customer_id column via migration', e1)
    r.run('E2  conservative backfill (R1/R2/ambiguous/none/preset)', e2)
    r.run('E3  customer_name/phone snapshots untouched', e3)
    r.run('E4  backfill is idempotent', e4)
    r.run('E5  legacy rows load/save safely; unresolved stay NULL', e5)
    return r.summary()


# ---------------------------------------------------------------- phase: realdb
def phase_realdb():
    work = tempfile.mkdtemp(prefix='f15_realdb_')
    shutil.copyfile(REAL_DB, os.path.join(work, 'repair_manager.db'))
    os.chdir(work)
    sys.path.insert(0, PROJECT_ROOT)

    r = Results()

    def snapshot():
        conn = sqlite3.connect('repair_manager.db')
        repairs = conn.execute('SELECT * FROM repairs ORDER BY id').fetchall()
        payments = conn.execute(
            'SELECT transaction_id, repair_id, amount, payment_method, '
            'payment_date, transaction_type, note '
            'FROM payment_transaction ORDER BY transaction_id').fetchall()
        conn.close()
        return repairs, payments

    pre_repairs, pre_payments = snapshot()

    pre_agg = {}
    conn = sqlite3.connect('repair_manager.db')
    for t, c, s in conn.execute(
            'SELECT transaction_type, COUNT(*), SUM(amount) '
            'FROM payment_transaction GROUP BY transaction_type'):
        pre_agg[t] = (c, s)
    conn.close()

    from core.storage.init_db import init_database
    init_database()

    post_repairs, post_payments = snapshot()

    conn = sqlite3.connect('repair_manager.db')
    cols = [c[1] for c in conn.execute('PRAGMA table_info(repairs)').fetchall()]
    mapping = {x[0]: x[1] for x in conn.execute(
        'SELECT id, customer_id FROM repairs ORDER BY id').fetchall()}
    agg = {}
    for t, c, s in conn.execute(
            'SELECT transaction_type, COUNT(*), SUM(amount) '
            'FROM payment_transaction GROUP BY transaction_type'):
        agg[t] = (c, s)
    conn.close()

    def f1():
        assert 'customer_id' in cols, cols

    def f2():
        # traced against the real data (unique phone/name matches only):
        # 1 'احمد خزایی'      (no phone)      -> customer 2 by unique name
        # 2 'امانویل سیمکشیان' 09110000000    -> customer 3 by unique phone
        # 3 'احمد دودانگه'     09133000000    -> customer 4 by unique phone
        # 4 'احمد دودانگه'     09133000000    -> customer 4 by unique phone
        # 5 'امانویل سیمکشیان' 09110000000    -> customer 3 by unique phone
        assert mapping == {1: 2, 2: 3, 3: 4, 4: 4, 5: 3}, mapping

    def f3():
        assert len(pre_repairs) == len(post_repairs) == 5, (
            len(pre_repairs), len(post_repairs))
        pre_cols = [c for c in cols if c != 'customer_id']
        idx = [cols.index(c) for c in pre_cols]
        for pre, post in zip(pre_repairs, post_repairs):
            for i, cname in zip(idx, pre_cols):
                assert pre[i] == post[i], (cname, pre[i], post[i])

    def f4():
        # every payment row identical (count, amounts, dates, notes)
        assert pre_payments == post_payments
        assert len(post_payments) == 9, len(post_payments)
        # 8 PAYMENT rows, 1 REFUND row; sums unchanged
        assert agg.get('PAYMENT') == pre_agg.get('PAYMENT'), (agg, pre_agg)
        assert agg.get('REFUND') == pre_agg.get('REFUND'), (agg, pre_agg)
        assert agg.get('PAYMENT', (0, 0))[0] == 8
        assert agg.get('REFUND', (0, 0))[0] == 1

    def f5():
        from core.storage.sqlite_storage import SQLiteStorage
        from core.models import Repair
        loaded = SQLiteStorage().load_all()
        assert len(loaded) == 5
        by_id = {x['id']: x for x in loaded}
        assert by_id[1]['customer_id'] == 2 and by_id[5]['customer_id'] == 3
        # model round-trip preserves the migrated ids
        for x in loaded:
            assert Repair.from_dict(x).to_dict()['customer_id'] == x['customer_id']

    r.run('F1  customer_id column added to existing repairs table', f1)
    r.run('F2  backfill assigns only unambiguous matches (expected map)', f2)
    r.run('F3  existing repair data unchanged (except customer_id)', f3)
    r.run('F4  existing payment transactions untouched (rows/counts/sums)', f4)
    r.run('F5  migrated copy loads via SQLiteStorage; ids survive model', f5)
    return r.summary()


# ---------------------------------------------------------------- main
RUNNERS = {
    'core': phase_core,
    'ui': phase_ui,
    'legacy': phase_legacy,
    'realdb': phase_realdb,
}


def main():
    if '--phase' in sys.argv:
        phase = sys.argv[sys.argv.index('--phase') + 1]
        return RUNNERS[phase]()
    failures = 0
    for phase in ('core', 'ui', 'legacy', 'realdb'):
        print(f"\n########## PHASE {phase} ##########")
        failures += run_phase(phase)
    print(f"\n=== F1.5 validation: "
          f"{'ALL PHASES PASSED' if failures == 0 else str(failures) + ' phase(s) failed'} ===")
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
