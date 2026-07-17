from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                               QLabel, QLineEdit, QPushButton, QSpinBox,
                               QDoubleSpinBox, QTextEdit, QTableWidget,
                               QTableWidgetItem, QHeaderView, QAbstractItemView,
                               QCompleter, QFrame, QStyledItemDelegate,
                               QScrollArea, QComboBox)
from PyQt5.QtCore import Qt, QTimer, QModelIndex, QSize
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QFont, QColor

from services.service_service import ServiceService
from services.part_service import PartService
from services.notification_service import show_warning
from services.date_service import today_persian
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
        self._service_lines = []
        self._part_lines = []

        self._init_ui()
        self._init_completers()

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
        self._part_table.setColumnCount(5)
        self._part_table.setHorizontalHeaderLabels(["قطعه", "تعداد", "قیمت واحد", "جمع", "عملیات"])
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
        part_layout.addWidget(self._part_table)

        self._part_subtotal_label = QLabel("جمع قطعات: 0")
        self._part_subtotal_label.setStyleSheet("font-weight: bold; color: #333;")
        part_layout.addWidget(self._part_subtotal_label)

        layout.addWidget(part_frame)

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
        line = {
            'part_id': part_id,
            'part_name_snapshot': name,
            'quantity': 1,
            'unit_price': unit_price,
            'total_price': unit_price,
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

            price = QSpinBox()
            price.setMaximum(999999999)
            price.setValue(line['unit_price'])
            price.valueChanged.connect(lambda v, r=i: self._update_part_price(r, v))
            self._part_table.setCellWidget(row, 2, price)

            self._part_table.setItem(row, 3, QTableWidgetItem(f"{line['total_price']:,}"))

            rm_btn = QPushButton("🗑️")
            rm_btn.setFixedSize(35, 25)
            rm_btn.setStyleSheet("background-color: #f44336; color: white;")
            rm_btn.clicked.connect(lambda checked, r=i: self._remove_part_line(r))
            self._part_table.setCellWidget(row, 4, rm_btn)

        if self._part_table.rowCount() == 0:
            self._part_table.setRowCount(1)
            placeholder = QTableWidgetItem("هیچ قطعه‌ای اضافه نشده است")
            placeholder.setForeground(QColor('#999'))
            self._part_table.setItem(0, 0, placeholder)
            self._part_table.setSpan(0, 0, 1, 5)

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
            self._part_table.item(row, 3).setText(f"{self._part_lines[row]['total_price']:,}")
            self._recalculate()

    def _update_part_price(self, row, value):
        if 0 <= row < len(self._part_lines):
            if value < 0:
                show_warning(self, "خطا", "قیمت نمی‌تواند منفی باشد.")
                self.sender().setValue(0)
                return
            self._part_lines[row]['unit_price'] = value
            self._part_lines[row]['total_price'] = value * self._part_lines[row]['quantity']
            self._part_table.item(row, 3).setText(f"{self._part_lines[row]['total_price']:,}")
            self._recalculate()

    # --- Calculation ---

    def _recalculate(self):
        svc_subtotal = sum(l['total_price'] for l in self._service_lines)
        part_subtotal = sum(l['total_price'] for l in self._part_lines)
        prediscount = svc_subtotal + part_subtotal
        discount = self._discount_input.value()
        after_discount = max(0, prediscount - discount)
        tax = self._tax_input.value()
        tax_amount = int(after_discount * tax / 100)
        final = after_discount + tax_amount

        self._svc_subtotal_label.setText(f"جمع خدمات: {svc_subtotal:,}")
        self._part_subtotal_label.setText(f"جمع قطعات: {part_subtotal:,}")
        self._sum_services_label.setText(f"{svc_subtotal:,}")
        self._sum_parts_label.setText(f"{part_subtotal:,}")
        self._sum_prediscount_label.setText(f"{prediscount:,}")
        self._final_amount_label.setText(f"{final:,}")

        self._update_payment()

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

    def _update_payment(self):
        svc_subtotal = sum(l['total_price'] for l in self._service_lines)
        part_subtotal = sum(l['total_price'] for l in self._part_lines)
        prediscount = svc_subtotal + part_subtotal
        discount = self._discount_input.value()
        after_discount = max(0, prediscount - discount)
        tax = self._tax_input.value()
        tax_amount = int(after_discount * tax / 100)
        final = after_discount + tax_amount

        paid = self._paid_input.value()
        if paid < 0:
            paid = 0
        remaining = final - paid
        if remaining < 0:
            remaining = 0
            paid = final
            self._paid_input.blockSignals(True)
            self._paid_input.setValue(paid)
            self._paid_input.blockSignals(False)

        self._remaining_label.setText(f"{remaining:,}")

        if remaining <= 0 and final > 0:
            self._payment_status_label.setText("تسویه شده")
            self._payment_status_label.setStyleSheet("font-weight: bold; color: #4CAF50;")
        elif paid > 0:
            self._payment_status_label.setText("پرداخت جزئی")
            self._payment_status_label.setStyleSheet("font-weight: bold; color: #FF9800;")
        else:
            self._payment_status_label.setText("پرداخت نشده")
            self._payment_status_label.setStyleSheet("font-weight: bold; color: #f44336;")

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

        self._render_service_table()
        self._render_part_table()

    def get_data(self):
        """Return invoice data as a dict."""
        svc_subtotal = sum(l['total_price'] for l in self._service_lines)
        part_subtotal = sum(l['total_price'] for l in self._part_lines)
        prediscount = svc_subtotal + part_subtotal
        discount = self._discount_input.value()
        after_discount = max(0, prediscount - discount)
        tax = self._tax_input.value()
        tax_amount = int(after_discount * tax / 100)
        final = after_discount + tax_amount
        paid = self._paid_input.value()

        remaining = max(0, final - paid)
        if remaining <= 0 and final > 0:
            payment_status = 'تسویه شده'
        elif paid > 0:
            payment_status = 'پرداخت جزئی'
        else:
            payment_status = 'پرداخت نشده'

        return {
            'service_lines': list(self._service_lines),
            'part_lines': list(self._part_lines),
            'tax': self._tax_input.value(),
            'discount': self._discount_input.value(),
            'paid_amount': paid,
            'payment_status': payment_status,
            'payment_method': self._payment_method_combo.currentText(),
            'payment_date': self._payment_date_input.get_date(),
            'financial_notes': self._financial_notes_input.toPlainText(),
            'parts_cost': part_subtotal,
            'labor_cost': svc_subtotal,
        }
