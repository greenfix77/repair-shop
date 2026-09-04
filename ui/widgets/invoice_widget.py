from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                               QLabel, QLineEdit, QPushButton, QSpinBox,
                               QDoubleSpinBox, QTextEdit, QTableWidget,
                               QTableWidgetItem, QHeaderView, QAbstractItemView,
                               QCompleter, QFrame, QStyledItemDelegate,
                               QScrollArea, QComboBox)
from PyQt5.QtCore import Qt, QTimer, QModelIndex, QSize
from typing import Dict
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QFont, QColor

from services.service_service import ServiceService
from services.part_service import PartService
from services.charge_service import ChargeService
from services.notification_service import show_warning
from services.date_service import today_persian
from services.payment_reconciliation_service import PaymentReconciliationService
from services.financial_summary_service import FinancialSummaryService
from services.invoice_calculator import calculate_invoice_totals
from core.storage.payment_transaction_repository import PaymentTransactionRepository
from repair_manager.ui.components import PersianDateEdit
from ui.dialogs.service_edit_dialog import ServiceEditDialog
from ui.dialogs.part_edit_dialog import PartEditDialog
from ui.dialogs.item_picker_dialog import ItemPickerDialog


class _CompleterDelegate(QStyledItemDelegate):
    def sizeHint(self, option, index):
        h = option.widget.fontMetrics().height() + 6
        return QSize(super().sizeHint(option, index).width(), h)


class _AutoGrowTable(QTableWidget):
    """جدولی که ارتفاع مطابق تعداد سطرها تنظیم می‌کند؛ بدون اسکرول داخلی."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

    def sizeHint(self):
        hint = super().sizeHint()
        n = self.rowCount()
        h = self.frameWidth() * 2
        vh = self.verticalHeader()
        if vh is not None and vh.isVisible():
            h += vh.length()
        else:
            h += self.horizontalHeader().sizeHint().height() if self.columnCount() > 0 else 0
            for r in range(n):
                h += self.rowHeight(r)
        if n == 0:
            h += self.horizontalHeader().sizeHint().height() + 4
        hint.setHeight(h)
        return hint

    def minimumSizeHint(self):
        return self.sizeHint()


class InvoiceWidget(QWidget):
    """ویجت فاکتور تعمیر: خدمات، قطعات، خلاصه، پرداخت، یادداشت‌های مالی"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._service_svc = ServiceService()
        self._part_svc = PartService()
        self._charge_svc = ChargeService()
        self._payment_tx_repo = PaymentTransactionRepository()
        self._reconciliation_svc = PaymentReconciliationService()
        self._financial_summary_svc = FinancialSummaryService(
            payment_service=self._reconciliation_svc,
        )
        self._service_lines = []
        self._part_lines = []
        self._additional_charges = []
        self._payment_transactions = []
        self._current_repair_id = None

        self._init_ui()
        self._init_completers()
        self._render_payment_history_table()
        self._refresh_financial_summary()

    # --- UI Setup ---

    def _init_ui(self):
        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)

        # بخش خدمات
        svc_frame = QFrame()
        svc_frame.setStyleSheet("background-color: white; border-radius: 5px; padding: 5px;")
        svc_layout = QVBoxLayout(svc_frame)

        svc_header = QHBoxLayout()
        svc_title = QLabel("خدمات انجام‌شده")
        svc_title.setStyleSheet("font-weight: bold; font-size: 11pt;")
        svc_header.addWidget(svc_title)
        svc_header.addStretch()

        self._svc_search = QLineEdit()
        self._svc_search.setPlaceholderText("جستجوی خدمت...")
        self._svc_search.setMaximumWidth(200)
        svc_header.addWidget(self._svc_search)

        add_svc_btn = QPushButton("➕ افزودن خدمت")
        add_svc_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        add_svc_btn.clicked.connect(self._add_service_from_search)
        svc_header.addWidget(add_svc_btn)

        create_svc_btn = QPushButton("✨ ایجاد خدمت جدید")
        create_svc_btn.setStyleSheet("background-color: #2196F3; color: white;")
        create_svc_btn.clicked.connect(self._create_new_service)
        svc_header.addWidget(create_svc_btn)
        svc_layout.addLayout(svc_header)

        self._svc_table = _AutoGrowTable()
        self._svc_table.setColumnCount(5)
        self._svc_table.setHorizontalHeaderLabels(["خدمت", "تعداد", "قیمت واحد", "جمع", "عملیات"])
        self._svc_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._svc_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._svc_table.setAlternatingRowColors(True)
        self._svc_table.verticalHeader().setVisible(False)
        hdr = self._svc_table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        svc_layout.addWidget(self._svc_table)

        self._svc_subtotal_label = QLabel("جمع خدمات: 0")
        self._svc_subtotal_label.setStyleSheet("font-weight: bold; color: #333;")
        svc_layout.addWidget(self._svc_subtotal_label)

        layout.addWidget(svc_frame)

        # بخش قطعات
        part_frame = QFrame()
        part_frame.setStyleSheet("background-color: white; border-radius: 5px; padding: 5px;")
        part_layout = QVBoxLayout(part_frame)

        part_header = QHBoxLayout()
        part_title = QLabel("قطعات مصرف‌شده")
        part_title.setStyleSheet("font-weight: bold; font-size: 11pt;")
        part_header.addWidget(part_title)
        part_header.addStretch()

        self._part_search = QLineEdit()
        self._part_search.setPlaceholderText("جستجوی قطعه...")
        self._part_search.setMaximumWidth(200)
        part_header.addWidget(self._part_search)

        add_part_btn = QPushButton("➕ افزودن قطعه")
        add_part_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        add_part_btn.clicked.connect(self._add_part_from_search)
        part_header.addWidget(add_part_btn)

        create_part_btn = QPushButton("✨ ایجاد قطعه جدید")
        create_part_btn.setStyleSheet("background-color: #2196F3; color: white;")
        create_part_btn.clicked.connect(self._create_new_part)
        part_header.addWidget(create_part_btn)
        part_layout.addLayout(part_header)

        self._part_table = _AutoGrowTable()
        self._part_table.setColumnCount(6)
        self._part_table.setHorizontalHeaderLabels(
            ["قطعه", "تعداد", "قیمت خرید", "قیمت واحد", "جمع", "عملیات"]
        )
        self._part_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._part_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._part_table.setAlternatingRowColors(True)
        self._part_table.verticalHeader().setVisible(False)
        phdr = self._part_table.horizontalHeader()
        phdr.setSectionResizeMode(0, QHeaderView.Stretch)
        phdr.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        phdr.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        phdr.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        phdr.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        phdr.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        part_layout.addWidget(self._part_table)

        self._part_subtotal_label = QLabel("جمع قطعات: 0")
        self._part_subtotal_label.setStyleSheet("font-weight: bold; color: #333;")
        part_layout.addWidget(self._part_subtotal_label)

        layout.addWidget(part_frame)

        # بخش هزینه‌های جانبی
        charge_frame = QFrame()
        charge_frame.setStyleSheet("background-color: white; border-radius: 5px; padding: 5px;")
        charge_layout = QVBoxLayout(charge_frame)

        charge_header = QHBoxLayout()
        charge_title = QLabel("هزینه‌های جانبی")
        charge_title.setStyleSheet("font-weight: bold; font-size: 11pt;")
        charge_header.addWidget(charge_title)
        charge_header.addStretch()

        add_charge_btn = QPushButton("➕ افزودن هزینه")
        add_charge_btn.setFixedHeight(36)
        add_charge_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        add_charge_btn.clicked.connect(self._on_add_charge_clicked)
        charge_header.addWidget(add_charge_btn)

        del_charge_btn = QPushButton("🗑️ حذف هزینه")
        del_charge_btn.setFixedHeight(36)
        del_charge_btn.setStyleSheet("background-color: #f44336; color: white;")
        del_charge_btn.clicked.connect(self._remove_last_charge)
        charge_header.addWidget(del_charge_btn)

        charge_layout.addLayout(charge_header)

        self._charges_table = _AutoGrowTable()
        self._charges_table.setColumnCount(5)
        self._charges_table.setHorizontalHeaderLabels(
            ["هزینه", "تعداد", "مبلغ واحد", "جمع", "عملیات"]
        )
        self._charges_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._charges_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._charges_table.setAlternatingRowColors(True)
        self._charges_table.verticalHeader().setVisible(False)
        chdr = self._charges_table.horizontalHeader()
        chdr.setSectionResizeMode(0, QHeaderView.Stretch)
        chdr.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        chdr.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        chdr.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        chdr.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        charge_layout.addWidget(self._charges_table)

        self._charges_subtotal_label = QLabel("جمع هزینه‌های جانبی: ۰ تومان")
        self._charges_subtotal_label.setStyleSheet("font-weight: bold; color: #333;")
        charge_layout.addWidget(self._charges_subtotal_label)

        layout.addWidget(charge_frame)

        # بخش خلاصه فاکتور + پرداخت
        bottom_layout = QVBoxLayout()

        # خلاصه
        summary_frame = QFrame()
        summary_frame.setStyleSheet("background-color: #f0f0f0; border-radius: 5px; padding: 10px;")
        summary_layout = QGridLayout(summary_frame)

        summary_layout.addWidget(QLabel("جمع خدمات:"), 0, 0)
        self._sum_services_label = QLabel("0")
        summary_layout.addWidget(self._sum_services_label, 0, 1)

        summary_layout.addWidget(QLabel("جمع قطعات:"), 1, 0)
        self._sum_parts_label = QLabel("0")
        summary_layout.addWidget(self._sum_parts_label, 1, 1)

        summary_layout.addWidget(QLabel("جمع قبل از تخفیف:"), 2, 0)
        self._sum_prediscount_label = QLabel("0")
        self._sum_prediscount_label.setStyleSheet("font-weight: bold;")
        summary_layout.addWidget(self._sum_prediscount_label, 2, 1)

        summary_layout.addWidget(QLabel("تخفیف:"), 3, 0)
        self._discount_input = QSpinBox()
        self._discount_input.setMaximum(999999999)
        self._discount_input.valueChanged.connect(self._recalculate)
        summary_layout.addWidget(self._discount_input, 3, 1)

        summary_layout.addWidget(QLabel("مالیات (%):"), 4, 0)
        self._tax_input = QDoubleSpinBox()
        self._tax_input.setMaximum(100)
        self._tax_input.valueChanged.connect(self._recalculate)
        summary_layout.addWidget(self._tax_input, 4, 1)

        summary_layout.addWidget(QLabel("مبلغ نهایی:"), 5, 0)
        self._final_amount_label = QLabel("0")
        self._final_amount_label.setStyleSheet("font-weight: bold; color: green; font-size: 12pt;")
        summary_layout.addWidget(self._final_amount_label, 5, 1)

        bottom_layout.addWidget(summary_frame)

        # پرداخت
        payment_frame = QFrame()
        payment_frame.setStyleSheet("background-color: #f0f0f0; border-radius: 5px; padding: 10px;")
        payment_layout = QGridLayout(payment_frame)

        payment_layout.addWidget(QLabel("مبلغ پرداخت‌شده:"), 0, 0)
        self._paid_input = QSpinBox()
        self._paid_input.setMaximum(999999999)
        self._paid_input.valueChanged.connect(self._update_payment)
        payment_layout.addWidget(self._paid_input, 0, 1)

        self._full_pay_btn = QPushButton("کل مبلغ")
        self._full_pay_btn.setStyleSheet(
            "background-color: #4CAF50; color: white; padding: 4px 10px;"
            " border: none; border-radius: 4px; font-size: 9pt;"
        )
        self._full_pay_btn.clicked.connect(self._fill_paid_with_total)
        payment_layout.addWidget(self._full_pay_btn, 0, 2)

        payment_layout.addWidget(QLabel("روش پرداخت:"), 1, 0)
        self._payment_method_combo = QComboBox()
        self._payment_method_combo.addItems([
            "نقدی",
            "کارت‌خوان (POS)",
            "کارت به کارت",
            "انتقال بانکی",
            "چک",
            "سایر",
        ])
        payment_layout.addWidget(self._payment_method_combo, 1, 1)

        payment_layout.addWidget(QLabel("تاریخ پرداخت:"), 2, 0)
        date_row = QWidget()
        date_row_layout = QHBoxLayout(date_row)
        date_row_layout.setContentsMargins(0, 0, 0, 0)
        date_row_layout.setSpacing(6)
        self._payment_date_today_btn = QPushButton("امروز")
        self._payment_date_today_btn.setStyleSheet(
            "background-color: #607D8B; color: white; padding: 4px 10px;"
            " border: none; border-radius: 4px; font-size: 9pt;"
        )
        self._payment_date_today_btn.clicked.connect(self._set_payment_date_today)
        self._payment_date_input = PersianDateEdit()
        date_row_layout.addWidget(self._payment_date_today_btn)
        date_row_layout.addWidget(self._payment_date_input, 1)
        payment_layout.addWidget(date_row, 2, 1)

        payment_layout.addWidget(QLabel("مانده:"), 3, 0)
        self._remaining_label = QLabel("0")
        payment_layout.addWidget(self._remaining_label, 3, 1)

        payment_layout.addWidget(QLabel("وضعیت پرداخت:"), 4, 0)
        self._payment_status_label = QLabel("پرداخت نشده")
        self._payment_status_label.setStyleSheet("font-weight: bold; color: #f44336;")
        payment_layout.addWidget(self._payment_status_label, 4, 1)

        bottom_layout.addWidget(payment_frame)

        # تاریخچه پرداخت‌ها (فقط نمایش)
        payment_history_frame = QFrame()
        payment_history_frame.setStyleSheet(
            "background-color: white; border-radius: 5px; padding: 5px;"
        )
        payment_history_layout = QVBoxLayout(payment_history_frame)
        payment_history_title = QLabel("تاریخچه پرداخت‌ها")
        payment_history_title.setStyleSheet("font-weight: bold; font-size: 11pt;")
        payment_history_layout.addWidget(payment_history_title)

        self._payment_history_table = _AutoGrowTable()
        self._payment_history_table.setColumnCount(5)
        self._payment_history_table.setHorizontalHeaderLabels(
            ["تاریخ", "مبلغ", "روش پرداخت", "نوع", "توضیحات"]
        )
        self._payment_history_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._payment_history_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._payment_history_table.setAlternatingRowColors(True)
        self._payment_history_table.verticalHeader().setVisible(False)
        phhdr = self._payment_history_table.horizontalHeader()
        phhdr.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        phhdr.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        phhdr.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        phhdr.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        phhdr.setSectionResizeMode(4, QHeaderView.Stretch)
        payment_history_layout.addWidget(self._payment_history_table)

        self._add_payment_btn = QPushButton("ثبت پرداخت")
        self._add_payment_btn.setFixedHeight(36)
        self._add_payment_btn.setLayoutDirection(Qt.RightToLeft)
        self._add_payment_btn.setStyleSheet(
            "background-color: #4CAF50; color: white; padding: 4px 10px;"
            " border: none; border-radius: 4px; font-size: 10pt;"
        )
        self._add_payment_btn.clicked.connect(self._on_add_payment_clicked)
        payment_history_layout.addWidget(self._add_payment_btn)

        self._add_refund_btn = QPushButton("ثبت استرداد")
        self._add_refund_btn.setFixedHeight(36)
        self._add_refund_btn.setLayoutDirection(Qt.RightToLeft)
        self._add_refund_btn.setStyleSheet(
            "background-color: #f44336; color: white; padding: 4px 10px;"
            " border: none; border-radius: 4px; font-size: 10pt;"
        )
        self._add_refund_btn.clicked.connect(self._on_add_refund_clicked)
        payment_history_layout.addWidget(self._add_refund_btn)

        bottom_layout.addWidget(payment_history_frame)

        bottom_layout.addWidget(self._build_financial_summary_section())

        layout.addLayout(bottom_layout)

        # یادداشت‌های مالی
        notes_frame = QFrame()
        notes_frame.setStyleSheet("background-color: white; border-radius: 5px; padding: 5px;")
        notes_layout = QVBoxLayout(notes_frame)
        notes_title = QLabel("توضیحات مالی")
        notes_title.setStyleSheet("font-weight: bold;")
        notes_layout.addWidget(notes_title)
        self._financial_notes_input = QTextEdit()
        self._financial_notes_input.setMaximumHeight(60)
        notes_layout.addWidget(self._financial_notes_input)
        layout.addWidget(notes_frame)

        scroll.setWidget(content)
        outer_layout.addWidget(scroll)
        self.setLayout(outer_layout)

    def _init_completers(self):
        self._svc_completer_model = QStandardItemModel()
        self._svc_completer = QCompleter()
        self._svc_completer.setCaseSensitivity(Qt.CaseInsensitive)
        self._svc_completer.setFilterMode(Qt.MatchContains)
        self._svc_completer.setModel(self._svc_completer_model)
        self._svc_completer.setCompletionMode(QCompleter.PopupCompletion)
        self._svc_completer.popup().setItemDelegate(_CompleterDelegate())
        self._svc_completer.popup().setLayoutDirection(Qt.RightToLeft)
        self._svc_completer.activated[QModelIndex].connect(self._on_svc_completer_activated)
        self._svc_search.setCompleter(self._svc_completer)
        self._svc_search.textChanged.connect(self._on_svc_search_changed)

        self._part_completer_model = QStandardItemModel()
        self._part_completer = QCompleter()
        self._part_completer.setCaseSensitivity(Qt.CaseInsensitive)
        self._part_completer.setFilterMode(Qt.MatchContains)
        self._part_completer.setModel(self._part_completer_model)
        self._part_completer.setCompletionMode(QCompleter.PopupCompletion)
        self._part_completer.popup().setItemDelegate(_CompleterDelegate())
        self._part_completer.popup().setLayoutDirection(Qt.RightToLeft)
        self._part_completer.activated[QModelIndex].connect(self._on_part_completer_activated)
        self._part_search.setCompleter(self._part_completer)
        self._part_search.textChanged.connect(self._on_part_search_changed)

    # --- Completer Search ---

    def _on_svc_search_changed(self, text):
        if len(text.strip()) < 1:
            self._svc_completer_model.clear()
            return
        services = self._service_svc.search(text)
        self._svc_completer_model.clear()
        for s in services:
            label = f"{s['name']} - {s.get('default_price', 0):,}"
            item = QStandardItem(label)
            item.setData(s['id'], Qt.UserRole)
            item.setData(s.get('default_price', 0), Qt.UserRole + 1)
            self._svc_completer_model.appendRow(item)
        if services:
            self._svc_completer.setCompletionPrefix(text)
            self._svc_completer.complete()
        else:
            empty = QStandardItem("نتیجه‌ای یافت نشد")
            empty.setEnabled(False)
            self._svc_completer_model.appendRow(empty)
            self._svc_completer.setCompletionPrefix('')
            self._svc_completer.complete()
        self._svc_completer.popup().setMinimumWidth(self._svc_search.width())

    def _on_svc_completer_activated(self, index):
        sid = index.data(Qt.UserRole)
        if not sid:
            return
        price = index.data(Qt.UserRole + 1) or 0
        label = index.data(Qt.DisplayRole) or ''
        name = label.split(' - ')[0] if ' - ' in label else label
        self._add_service_line(sid, name, price)
        self._svc_search.clear()

    def _on_part_search_changed(self, text):
        if len(text.strip()) < 1:
            self._part_completer_model.clear()
            return
        parts = self._part_svc.search(text)
        self._part_completer_model.clear()
        for p in parts:
            label = f"{p['name']} - {p.get('sale_price', 0):,}"
            item = QStandardItem(label)
            item.setData(p['id'], Qt.UserRole)
            item.setData(p.get('sale_price', 0), Qt.UserRole + 1)
            self._part_completer_model.appendRow(item)
        if parts:
            self._part_completer.setCompletionPrefix(text)
            self._part_completer.complete()
        else:
            empty = QStandardItem("نتیجه‌ای یافت نشد")
            empty.setEnabled(False)
            self._part_completer_model.appendRow(empty)
            self._part_completer.setCompletionPrefix('')
            self._part_completer.complete()
        self._part_completer.popup().setMinimumWidth(self._part_search.width())

    def _on_part_completer_activated(self, index):
        pid = index.data(Qt.UserRole)
        if not pid:
            return
        price = index.data(Qt.UserRole + 1) or 0
        label = index.data(Qt.DisplayRole) or ''
        name = label.split(' - ')[0] if ' - ' in label else label
        self._add_part_line(pid, name, price)
        self._part_search.clear()

    # --- Add from search button ---

    def _add_service_from_search(self):
        services = self._service_svc.list_all(active_only=True)
        if not services:
            show_warning(self, "هیچ خدمتی", "هیچ خدمت فعالی در کاتالوگ یافت نشد.")
            return
        dialog = ItemPickerDialog("انتخاب خدمت", services, 'name', 'default_price', parent=self)
        if dialog.exec_() == dialog.Accepted and dialog.selected_item:
            s = dialog.selected_item
            self._add_service_line(s['id'], s['name'], s.get('default_price', 0))
            self._svc_search.clear()

    def _add_part_from_search(self):
        parts = self._part_svc.list_all(active_only=True)
        if not parts:
            show_warning(self, "هیچ قطعه‌ای", "هیچ قطعه فعالی در کاتالوگ یافت نشد.")
            return
        dialog = ItemPickerDialog("انتخاب قطعه", parts, 'name', 'sale_price', parent=self)
        if dialog.exec_() == dialog.Accepted and dialog.selected_item:
            p = dialog.selected_item
            self._add_part_line(p['id'], p['name'], p.get('sale_price', 0))
            self._part_search.clear()

    # --- Create new items ---

    def _create_new_service(self):
        dialog = ServiceEditDialog(service_id=None, parent=self)
        if dialog.exec_() == dialog.Accepted:
            created = getattr(dialog, '_created_service', None)
            if created:
                self._add_service_line(
                    created['id'], created['name'], created.get('default_price', 0)
                )
                self._svc_search.clear()

    def _create_new_part(self):
        dialog = PartEditDialog(part_id=None, parent=self)
        if dialog.exec_() == dialog.Accepted:
            created = getattr(dialog, '_created_part', None)
            if created:
                self._add_part_line(
                    created['id'], created['name'], created.get('sale_price', 0)
                )
                self._part_search.clear()

    # --- Line management ---

    def _add_service_line(self, service_id, name, unit_price):
        line = {
            'service_id': service_id,
            'service_name_snapshot': name,
            'quantity': 1,
            'unit_price': unit_price,
            'total_price': unit_price,
        }
        self._service_lines.append(line)
        self._render_service_table()

    def _add_part_line(self, part_id, name, unit_price):
        purchase_price_snapshot = 0
        default_sale_price = 0
        if part_id is not None:
            try:
                part = self._part_svc.get_part(part_id)
                if part:
                    purchase_price_snapshot = part.get('purchase_price', 0) or 0
                    default_sale_price = part.get('default_sale_price', 0) or 0
            except Exception:
                purchase_price_snapshot = 0
                default_sale_price = 0
        if default_sale_price <= 0:
            default_sale_price = purchase_price_snapshot
        initial_unit_price = default_sale_price
        line = {
            'part_id': part_id,
            'part_name_snapshot': name,
            'quantity': 1,
            'unit_price': initial_unit_price,
            'total_price': initial_unit_price,
            'purchase_price_snapshot': purchase_price_snapshot,
        }
        self._part_lines.append(line)
        self._render_part_table()

    def _remove_service_line(self, row):
        if 0 <= row < len(self._service_lines):
            del self._service_lines[row]
            self._render_service_table()

    def _remove_part_line(self, row):
        if 0 <= row < len(self._part_lines):
            del self._part_lines[row]
            self._render_part_table()

    # --- Rendering ---

    def _render_service_table(self):
        self._svc_table.setRowCount(0)
        for i, line in enumerate(self._service_lines):
            row = self._svc_table.rowCount()
            self._svc_table.insertRow(row)

            self._svc_table.setItem(row, 0, QTableWidgetItem(line['service_name_snapshot']))

            qty = QSpinBox()
            qty.setMaximum(999999)
            qty.setValue(line['quantity'])
            qty.valueChanged.connect(lambda v, r=i: self._update_svc_qty(r, v))
            self._svc_table.setCellWidget(row, 1, qty)

            price = QSpinBox()
            price.setMaximum(999999999)
            price.setValue(line['unit_price'])
            price.valueChanged.connect(lambda v, r=i: self._update_svc_price(r, v))
            self._svc_table.setCellWidget(row, 2, price)

            self._svc_table.setItem(row, 3, QTableWidgetItem(f"{line['total_price']:,}"))

            rm_btn = QPushButton("🗑️")
            rm_btn.setFixedSize(35, 25)
            rm_btn.setStyleSheet("background-color: #f44336; color: white;")
            rm_btn.clicked.connect(lambda checked, r=i: self._remove_service_line(r))
            self._svc_table.setCellWidget(row, 4, rm_btn)

        if self._svc_table.rowCount() == 0:
            self._svc_table.setRowCount(1)
            placeholder = QTableWidgetItem("هیچ خدمتی اضافه نشده است")
            placeholder.setForeground(QColor('#999'))
            self._svc_table.setItem(0, 0, placeholder)
            self._svc_table.setSpan(0, 0, 1, 5)

        self._svc_table.updateGeometry()
        self._recalculate()

    def _render_part_table(self):
        self._part_table.setRowCount(0)
        for i, line in enumerate(self._part_lines):
            row = self._part_table.rowCount()
            self._part_table.insertRow(row)

            self._part_table.setItem(row, 0, QTableWidgetItem(line['part_name_snapshot']))

            qty = QSpinBox()
            qty.setMaximum(999999)
            qty.setValue(line['quantity'])
            qty.valueChanged.connect(lambda v, r=i: self._update_part_qty(r, v))
            self._part_table.setCellWidget(row, 1, qty)

            purchase_price_snapshot = line.get('purchase_price_snapshot', 0) or 0
            purchase_item = QTableWidgetItem(f"{purchase_price_snapshot:,}")
            purchase_item.setFlags(purchase_item.flags() & ~Qt.ItemIsEditable)
            self._part_table.setItem(row, 2, purchase_item)

            price = QSpinBox()
            price.setMaximum(999999999)
            price.setValue(line['unit_price'])
            price.valueChanged.connect(lambda v, r=i: self._update_part_price(r, v))
            self._part_table.setCellWidget(row, 3, price)

            self._part_table.setItem(row, 4, QTableWidgetItem(f"{line['total_price']:,}"))

            rm_btn = QPushButton("🗑️")
            rm_btn.setFixedSize(35, 25)
            rm_btn.setStyleSheet("background-color: #f44336; color: white;")
            rm_btn.clicked.connect(lambda checked, r=i: self._remove_part_line(r))
            self._part_table.setCellWidget(row, 5, rm_btn)

        if self._part_table.rowCount() == 0:
            self._part_table.setRowCount(1)
            placeholder = QTableWidgetItem("هیچ قطعه‌ای اضافه نشده است")
            placeholder.setForeground(QColor('#999'))
            self._part_table.setItem(0, 0, placeholder)
            self._part_table.setSpan(0, 0, 1, 6)

        self._part_table.updateGeometry()
        self._recalculate()

    # --- Quantity / Price updates ---

    def _update_svc_qty(self, row, value):
        if 0 <= row < len(self._service_lines):
            if value < 1:
                show_warning(self, "خطا", "تعداد باید بیشتر از صفر باشد.")
                self.sender().setValue(1)
                return
            self._service_lines[row]['quantity'] = value
            self._service_lines[row]['total_price'] = value * self._service_lines[row]['unit_price']
            self._svc_table.item(row, 3).setText(f"{self._service_lines[row]['total_price']:,}")
            self._recalculate()

    def _update_svc_price(self, row, value):
        if 0 <= row < len(self._service_lines):
            if value < 0:
                show_warning(self, "خطا", "قیمت نمی‌تواند منفی باشد.")
                self.sender().setValue(0)
                return
            self._service_lines[row]['unit_price'] = value
            self._service_lines[row]['total_price'] = value * self._service_lines[row]['quantity']
            self._svc_table.item(row, 3).setText(f"{self._service_lines[row]['total_price']:,}")
            self._recalculate()

    def _update_part_qty(self, row, value):
        if 0 <= row < len(self._part_lines):
            if value < 1:
                show_warning(self, "خطا", "تعداد باید بیشتر از صفر باشد.")
                self.sender().setValue(1)
                return
            self._part_lines[row]['quantity'] = value
            self._part_lines[row]['total_price'] = value * self._part_lines[row]['unit_price']
            self._part_table.item(row, 4).setText(f"{self._part_lines[row]['total_price']:,}")
            self._recalculate()

    def _update_part_price(self, row, value):
        if 0 <= row < len(self._part_lines):
            if value < 0:
                show_warning(self, "خطا", "قیمت نمی‌تواند منفی باشد.")
                self.sender().setValue(0)
                return
            self._part_lines[row]['unit_price'] = value
            self._part_lines[row]['total_price'] = value * self._part_lines[row]['quantity']
            self._part_table.item(row, 4).setText(f"{self._part_lines[row]['total_price']:,}")
            self._recalculate()

    def _update_charge_qty(self, row, value):
        if 0 <= row < len(self._additional_charges):
            if value < 1:
                show_warning(self, "خطا", "تعداد باید بیشتر از صفر باشد.")
                self.sender().setValue(1)
                return
            self._additional_charges[row]['quantity'] = value
            self._additional_charges[row]['total_price'] = (
                value * self._additional_charges[row]['unit_price']
            )
            self._charges_table.item(row, 3).setText(
                f"{self._additional_charges[row]['total_price']:,}"
            )
            self._recalculate()

    def _update_charge_price(self, row, value):
        if 0 <= row < len(self._additional_charges):
            if value < 0:
                show_warning(self, "خطا", "قیمت نمی‌تواند منفی باشد.")
                self.sender().setValue(0)
                return
            self._additional_charges[row]['unit_price'] = value
            self._additional_charges[row]['total_price'] = (
                value * self._additional_charges[row]['quantity']
            )
            self._charges_table.item(row, 3).setText(
                f"{self._additional_charges[row]['total_price']:,}"
            )
            self._recalculate()

    # --- Additional Charges ---

    def _build_additional_charges_section(self) -> QFrame:
        """هزینه‌های جانبی -----------------------------------------------------"""
        frame = QFrame()
        frame.setStyleSheet(
            "background-color: white; border-radius: 5px; padding: 5px;"
        )
        v = QVBoxLayout(frame)

        title = QLabel("هزینه‌های جانبی")
        title.setStyleSheet("font-weight: bold;")
        v.addWidget(title)

        add_btn = QPushButton("افزودن هزینه")
        add_btn.setFixedHeight(36)
        add_btn.setStyleSheet(
            "background-color: #4CAF50; color: white; padding: 4px 10px;"
            " border: none; border-radius: 4px; font-size: 10pt;"
        )
        add_btn.clicked.connect(self._on_add_charge_clicked)
        v.addWidget(add_btn)

        self._charges_table = _AutoGrowTable()
        self._charges_table.setColumnCount(5)
        self._charges_table.setHorizontalHeaderLabels(
            ["عنوان", "نوع", "مبلغ", "توضیح", "حذف"]
        )
        self._charges_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._charges_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._charges_table.verticalHeader().setVisible(False)
        chdr = self._charges_table.horizontalHeader()
        chdr.setSectionResizeMode(0, QHeaderView.Stretch)
        chdr.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        chdr.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        chdr.setSectionResizeMode(3, QHeaderView.Stretch)
        chdr.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        v.addWidget(self._charges_table)

        return frame

    def _on_add_charge_clicked(self):
        self._add_charge_from_search()

    def _add_charge_from_search(self):
        charges = self._charge_svc.list_all(active_only=True)
        if not charges:
            show_warning(self, "هیچ هزینه‌ای", "هیچ هزینه فعالی در کاتالوگ یافت نشد.")
            return
        dialog = ItemPickerDialog(
            "انتخاب هزینه", charges, 'name', 'default_amount', parent=self
        )
        if dialog.exec_() == dialog.Accepted and dialog.selected_item:
            c = dialog.selected_item
            self._add_charge_line(
                c['id'], c['name'], c.get('default_amount', 0)
            )

    def _add_charge_line(self, charge_id, name, unit_price):
        line = {
            'charge_id': charge_id,
            'charge_name_snapshot': name,
            'quantity': 1,
            'unit_price': unit_price,
            'total_price': unit_price,
        }
        self._additional_charges.append(line)
        self._render_additional_charges_table()
        self._recalculate()

    def _remove_last_charge(self):
        """حذف آخرین هزینه اضافه‌شده (دکمه ابزار سرصفحه)."""
        if not self._additional_charges:
            return
        self._additional_charges.pop()
        self._render_additional_charges_table()
        self._recalculate()

    def _remove_additional_charge(self, row):
        if 0 <= row < len(self._additional_charges):
            del self._additional_charges[row]
        self._render_additional_charges_table()
        self._recalculate()

    def _on_charge_field_changed(self, row, field, value):
        if 0 <= row < len(self._additional_charges):
            self._additional_charges[row][field] = value

    def _render_additional_charges_table(self):
        self._charges_table.setRowCount(0)
        for i, line in enumerate(self._additional_charges):
            row = self._charges_table.rowCount()
            self._charges_table.insertRow(row)

            self._charges_table.setItem(
                row, 0, QTableWidgetItem(line.get('charge_name_snapshot', '') or '')
            )

            qty = QSpinBox()
            qty.setMaximum(999999)
            qty.setValue(line.get('quantity', 1) or 1)
            qty.valueChanged.connect(lambda v, r=i: self._update_charge_qty(r, v))
            self._charges_table.setCellWidget(row, 1, qty)

            price = QSpinBox()
            price.setMaximum(999999999)
            price.setValue(line.get('unit_price', 0) or 0)
            price.valueChanged.connect(lambda v, r=i: self._update_charge_price(r, v))
            self._charges_table.setCellWidget(row, 2, price)

            self._charges_table.setItem(
                row, 3, QTableWidgetItem(f"{line.get('total_price', 0) or 0:,}")
            )

            rm_btn = QPushButton("🗑️")
            rm_btn.setFixedSize(35, 25)
            rm_btn.setStyleSheet("background-color: #f44336; color: white;")
            rm_btn.clicked.connect(lambda checked, r=i: self._remove_additional_charge(r))
            self._charges_table.setCellWidget(row, 4, rm_btn)

        if self._charges_table.rowCount() == 0:
            self._charges_table.setRowCount(1)
            placeholder = QTableWidgetItem("هیچ هزینه‌ای اضافه نشده است")
            placeholder.setForeground(QColor('#999'))
            self._charges_table.setItem(0, 0, placeholder)
            self._charges_table.setSpan(0, 0, 1, 5)

        self._charges_table.updateGeometry()

    # --- Payment history (read-only) ---

    def _render_payment_history_table(self):
        """Render the read-only payment history rows.

        Reads exclusively from ``PaymentTransactionRepository``. Safe to
        call with an empty list — shows a placeholder row.
        """
        if not hasattr(self, '_payment_history_table'):
            return
        self._payment_history_table.setRowCount(0)
        transactions = self._payment_transactions or []
        for tx in transactions:
            row = self._payment_history_table.rowCount()
            self._payment_history_table.insertRow(row)
            payment_date = tx.get('payment_date', '') or ''
            amount = tx.get('amount', 0) or 0
            method = tx.get('payment_method', '') or ''
            tx_type = tx.get('transaction_type', '') or ''
            note = tx.get('note', '') or ''

            self._payment_history_table.setItem(
                row, 0, QTableWidgetItem(payment_date)
            )
            self._payment_history_table.setItem(
                row, 1, QTableWidgetItem(f"{int(amount):,}")
            )
            self._payment_history_table.setItem(
                row, 2, QTableWidgetItem(method)
            )
            self._payment_history_table.setItem(
                row, 3, QTableWidgetItem(tx_type)
            )
            self._payment_history_table.setItem(
                row, 4, QTableWidgetItem(note)
            )

        if self._payment_history_table.rowCount() == 0:
            self._payment_history_table.setRowCount(1)
            placeholder = QTableWidgetItem("هیچ تراکنش پرداختی ثبت نشده است")
            placeholder.setForeground(QColor('#999'))
            self._payment_history_table.setItem(0, 0, placeholder)
            self._payment_history_table.setSpan(0, 0, 1, 5)

        self._payment_history_table.updateGeometry()

    def _load_payment_history(self, repair_id):
        """Fetch ledger transactions for the repair via the repository.

        F2: reads the PAYMENT/REFUND payment history only — the Financial
        tab's history table keeps showing exactly what it showed before
        the financial-event foundation. The full event stream (including
        REPAIR_CHARGE / DISCOUNT) stays available through the
        repository/service for the future customer ledger.
        """
        if not repair_id:
            self._payment_transactions = []
            self._render_payment_history_table()
            return
        try:
            transactions = self._payment_tx_repo.list_payment_history_for_repair(
                int(repair_id)
            )
        except Exception:
            transactions = []
        self._payment_transactions = transactions
        self._render_payment_history_table()
        self._sync_paid_from_ledger(repair_id)

    def _sync_paid_from_ledger(self, repair_id):
        """Drive snapshot UI from the ledger via PaymentReconciliationService.

        Updates only the existing UI controls (``پرداخت شده``,
        ``مانده``, ``وضعیت پرداخت``). Does not touch calculations,
        Repair persistence, or any other field.
        """
        if not repair_id:
            return
        try:
            paid = int(self._reconciliation_svc.net_paid_for_repair(int(repair_id)) or 0)
        except Exception:
            return

        self._paid_input.blockSignals(True)
        try:
            self._paid_input.setValue(paid)
        finally:
            self._paid_input.blockSignals(False)
        self._update_payment()
        self._refresh_financial_summary()

    def _on_add_payment_clicked(self):
        self._create_ledger_transaction('PAYMENT', 'ثبت پرداخت ناموفق بود:')

    def _on_add_refund_clicked(self):
        self._create_ledger_transaction('REFUND', 'ثبت استرداد ناموفق بود:')

    def _create_ledger_transaction(self, transaction_type, error_prefix):
        """Create one ledger transaction from the current payment controls.

        Both PAYMENT and REFUND share this pipeline. Amount must be > 0.
        After successful insert the history table reloads and the
        snapshot sync runs through ``PaymentReconciliationService`` so
        refunds automatically reduce the customer's net paid amount.
        """
        repair_id = self._current_repair_id
        if not repair_id:
            show_warning(self, "خطا", "ابتدا تعمیر را ذخیره کنید.")
            return

        amount = int(self._paid_input.value() or 0)
        if amount <= 0:
            show_warning(self, "خطا", "مبلغ باید بیشتر از صفر باشد.")
            return

        payment_method = self._payment_method_combo.currentText() or ''
        payment_date = self._payment_date_input.get_date() or ''
        note = self._financial_notes_input.toPlainText() or ''

        try:
            self._payment_tx_repo.create({
                'repair_id': int(repair_id),
                'amount': amount,
                'payment_method': payment_method,
                'payment_date': payment_date,
                'transaction_type': transaction_type,
                'note': note,
            })
        except Exception as exc:
            show_warning(self, "خطا", f"{error_prefix} {exc}")
            return

        self._load_payment_history(repair_id)
        self._sync_paid_from_ledger(repair_id)

    # --- Calculation ---

    def _authoritative_totals(self) -> Dict:
        """Compute the payable breakdown via the single source of truth.

        F1.5: the widget owns no total formula anymore. Services, parts
        and additional-charge subtotals plus the final payable all come
        from ``invoice_calculator.calculate_invoice_totals`` so the
        widget, the repairs table and the invoice PDF always agree.
        """
        return calculate_invoice_totals({
            'parts_cost': sum(l['total_price'] for l in self._part_lines),
            'labor_cost': sum(l['total_price'] for l in self._service_lines),
            'additional_charges': self._additional_charges,
            'tax': self._tax_input.value(),
            'discount': self._discount_input.value(),
        })

    def _recalculate(self):
        fin = self._authoritative_totals()
        svc_subtotal = fin['labor_cost']
        part_subtotal = fin['parts_cost']
        charge_subtotal = fin['additional_charges']
        prediscount = fin['subtotal']
        final = fin['total']

        self._svc_subtotal_label.setText(f"جمع خدمات: {svc_subtotal:,}")
        self._part_subtotal_label.setText(f"جمع قطعات: {part_subtotal:,}")
        self._charges_subtotal_label.setText(
            f"جمع هزینه‌های جانبی: {charge_subtotal:,}"
        )
        self._sum_services_label.setText(f"{svc_subtotal:,}")
        self._sum_parts_label.setText(f"{part_subtotal:,}")
        self._sum_prediscount_label.setText(f"{prediscount:,}")
        self._final_amount_label.setText(f"{final:,}")

        self._update_payment()
        self._refresh_financial_summary()

    def _final_amount(self) -> int:
        """Reuse the existing recalculation chain and return the final total.

        Avoids duplicating business logic: the same formula used for
        ``مبلغ نهایی`` powers the 'کل مبلغ' quick-fill.
        """
        self._recalculate()
        text = self._final_amount_label.text().replace(',', '').strip()
        try:
            return int(text or 0)
        except ValueError:
            return 0

    def _fill_paid_with_total(self):
        """Fill paid amount with the current invoice final total.

        Triggers the same UI pipeline as a manual edit so the remaining
        label and payment status reflect the new value immediately.
        """
        self._paid_input.blockSignals(True)
        self._paid_input.setValue(self._final_amount())
        self._paid_input.blockSignals(False)
        self._update_payment()

    def _set_payment_date_today(self):
        """Fill payment_date with the authoritative today's Persian date."""
        self._payment_date_input.setText(today_persian())

    # --- Financial Summary Panel (read-only) ---

    def _build_financial_summary_section(self) -> QFrame:
        """Read-only panel fed exclusively by FinancialSummaryService."""
        frame = QFrame()
        frame.setStyleSheet(
            "background-color: white; border-radius: 5px; padding: 5px;"
        )
        layout = QVBoxLayout(frame)

        title = QLabel("خلاصه مالی")
        title.setStyleSheet("font-weight: bold; font-size: 11pt;")
        layout.addWidget(title)

        self._summary_rows = {}
        rows = [
            ("درآمد خدمات", "services_revenue"),
            ("درآمد قطعات", "parts_revenue"),
            ("درآمد هزینه‌های جانبی", "additional_charge_revenue"),
            ("درآمد کل", "gross_revenue"),
            ("بهای تمام‌شده قطعات", "parts_cost"),
            ("سود ناخالص", "gross_profit"),
            ("حاشیه سود", "profit_margin"),
            ("مبلغ پرداخت‌شده", "paid_amount"),
            ("مانده", "remaining_amount"),
            ("وضعیت پرداخت", "payment_status"),
        ]
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(4)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 0)
        for i, (label_text, key) in enumerate(rows):
            name = QLabel(label_text)
            name.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            value = QLabel("--")
            value.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            value.setStyleSheet("font-weight: bold;")
            grid.addWidget(name, i, 0)
            grid.addWidget(value, i, 1)
            self._summary_rows[key] = value
        layout.addLayout(grid)

        return frame

    def _refresh_financial_summary(self):
        """Recompute summary rows via FinancialSummaryService.

        All values are formatted — no math happens here. ProfitService
        and PaymentReconciliationService remain the only owners of
        calculations.
        """
        summary = self._financial_summary_svc.calculate(
            self._build_summary_repair_dict(),
            self._current_repair_id,
        )
        money_keys = (
            'services_revenue',
            'parts_revenue',
            'additional_charge_revenue',
            'gross_revenue',
            'parts_cost',
            'gross_profit',
            'paid_amount',
            'remaining_amount',
        )
        for key in money_keys:
            value_label = self._summary_rows.get(key)
            if value_label is None:
                continue
            try:
                amount = int(summary.get(key, 0) or 0)
            except (TypeError, ValueError):
                amount = 0
            value_label.setText(f"{amount:,} تومان")

        margin_label = self._summary_rows.get('profit_margin')
        if margin_label is not None:
            try:
                margin = float(summary.get('profit_margin', 0) or 0)
            except (TypeError, ValueError):
                margin = 0.0
            margin_label.setText(f"{margin * 100:.1f} %")

        status_label = self._summary_rows.get('payment_status')
        if status_label is not None:
            status_label.setText(str(summary.get('payment_status', '') or '--'))

    def _build_summary_repair_dict(self) -> Dict:
        """Project the current widget state into a repair-shaped dict.

        No math — just structural mapping so FinancialSummaryService can
        read the same shape it expects from a real Repair dict.
        """
        repair = {
            'service_lines': list(self._service_lines),
            'part_lines': list(self._part_lines),
            'additional_charges': list(self._additional_charges),
        }
        if self._current_repair_id is not None:
            repair['id'] = self._current_repair_id
        return repair

    def _update_payment(self):
        final = self._authoritative_totals()['total']

        paid = self._paid_input.value()
        if paid < 0:
            paid = 0
        remaining = FinancialSummaryService.remaining_for(paid, final)
        if remaining == 0 and paid > final:
            paid = final
            self._paid_input.blockSignals(True)
            self._paid_input.setValue(paid)
            self._paid_input.blockSignals(False)

        self._remaining_label.setText(f"{remaining:,}")

        payment_status = FinancialSummaryService.payment_status_for(paid, final)
        status_styles = {
            'تسویه شده': "font-weight: bold; color: #4CAF50;",
            'پرداخت جزئی': "font-weight: bold; color: #FF9800;",
            'پرداخت نشده': "font-weight: bold; color: #f44336;",
        }
        self._payment_status_label.setText(payment_status)
        self._payment_status_label.setStyleSheet(
            status_styles.get(payment_status, status_styles['پرداخت نشده'])
        )

    # --- Public API: load / get data ---

    def load_data(self, data):
        """Load invoice data from a repair dict, with migration for old repairs."""
        self._service_lines = list(data.get('service_lines', []))
        self._part_lines = list(data.get('part_lines', []))

        # Migration: old repairs without invoice lines
        if not self._service_lines and not self._part_lines:
            labor = data.get('labor_cost', 0) or 0
            parts = data.get('parts_cost', 0) or 0
            if labor > 0:
                self._service_lines.append({
                    'service_id': None,
                    'service_name_snapshot': 'هزینه تعمیر',
                    'quantity': 1,
                    'unit_price': labor,
                    'total_price': labor,
                })
            if parts > 0:
                self._part_lines.append({
                    'part_id': None,
                    'part_name_snapshot': 'قطعات',
                    'quantity': 1,
                    'unit_price': parts,
                    'total_price': parts,
                })

        self._discount_input.setValue(data.get('discount', 0))
        self._tax_input.setValue(data.get('tax', 0))
        self._paid_input.setValue(data.get('paid_amount', 0))
        legacy_method_map = {
            '': 'نقدی',
            'کارت‌خوان': 'کارت‌خوان (POS)',
        }
        saved_method = legacy_method_map.get(
            data.get('payment_method', '') or '',
            data.get('payment_method', '') or 'نقدی',
        )
        idx = self._payment_method_combo.findText(saved_method)
        self._payment_method_combo.setCurrentIndex(idx if idx >= 0 else 0)
        payment_date = data.get('payment_date', '') or ''
        self._payment_date_input.setText(payment_date)
        self._financial_notes_input.setPlainText(data.get('financial_notes', ''))

        raw_charges = data.get('additional_charges', []) or []
        migrated = []
        for c in raw_charges:
            if not isinstance(c, dict):
                continue
            line = dict(c)
            if 'charge_name_snapshot' not in line:
                line['charge_name_snapshot'] = (
                    line.get('title', '') or line.get('name', '') or ''
                )
            if 'charge_id' not in line:
                line['charge_id'] = line.get('id') or None
            try:
                unit_price = int(line.get('unit_price', 0) or 0)
            except (TypeError, ValueError):
                unit_price = 0
            if unit_price == 0:
                try:
                    unit_price = int(line.get('amount', 0) or 0)
                except (TypeError, ValueError):
                    unit_price = 0
            try:
                quantity = int(line.get('quantity', 1) or 1)
            except (TypeError, ValueError):
                quantity = 1
            if quantity < 1:
                quantity = 1
            line['unit_price'] = unit_price
            line['quantity'] = quantity
            line['total_price'] = unit_price * quantity
            migrated.append(line)
        self._additional_charges = migrated

        self._render_service_table()
        self._render_part_table()
        self._render_additional_charges_table()
        self._recalculate()
        self._current_repair_id = data.get('id')
        self._load_payment_history(data.get('id'))

    def get_data(self):
        """Return invoice data as a dict."""
        fin = self._authoritative_totals()
        final = fin['total']
        paid = self._paid_input.value()

        payment_status = FinancialSummaryService.payment_status_for(paid, final)

        return {
            'service_lines': list(self._service_lines),
            'part_lines': list(self._part_lines),
            'additional_charges': list(self._additional_charges),
            'tax': self._tax_input.value(),
            'discount': self._discount_input.value(),
            'paid_amount': paid,
            'payment_status': payment_status,
            'payment_method': self._payment_method_combo.currentText(),
            'payment_date': self._payment_date_input.get_date(),
            'financial_notes': self._financial_notes_input.toPlainText(),
            'parts_cost': fin['parts_cost'],
            'labor_cost': fin['labor_cost'],
        }
