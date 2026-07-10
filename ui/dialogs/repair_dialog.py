from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
                              QTabWidget, QWidget, QLineEdit, QTextEdit, QSpinBox,
                              QDoubleSpinBox, QComboBox, QLabel, QPushButton,
                              QCompleter, QStyledItemDelegate, QStyle, QMessageBox)
from PyQt5.QtCore import Qt, QTimer, QRegularExpression, QSize, QModelIndex
from PyQt5.QtGui import (
    QFont,
    QRegularExpressionValidator,
    QColor,
    QStandardItemModel,
    QStandardItem,
)

from services.notification_service import show_warning, show_question
from core.status import ALL_STATUSES, STATUS_PENDING
from repair_manager.ui.components import PersianDateEdit
from services.invoice_calculator import calculate_invoice_totals
from services.customer_workflow import CustomerWorkflow
from ui.dialogs.customer_edit_dialog import CustomerEditDialog
from ui.dialogs.customer_selection_dialog import CustomerSelectionDialog


class CompleterItemDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        text = index.data(Qt.DisplayRole) or ''
        painter.save()
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
        rect = option.rect.adjusted(8, 4, -8, -4)
        lines = text.split('\n')
        font = painter.font()
        if lines:
            f = QFont(font)
            f.setPointSize(font.pointSize() + 1)
            painter.setFont(f)
            painter.drawText(rect, Qt.AlignRight | Qt.AlignBottom, lines[0])
        if len(lines) > 1:
            f = QFont(font)
            f.setPointSize(font.pointSize() - 1)
            painter.setFont(f)
            painter.setPen(QColor('#666666'))
            painter.drawText(rect, Qt.AlignRight | Qt.AlignTop, lines[1])
        painter.restore()

    def sizeHint(self, option, index):
        h = option.widget.fontMetrics().height() * 2 + 12
        return QSize(super().sizeHint(option, index).width(), h)


class RepairDialog(QDialog):
    """دیالوگ افزودن/ویرایش تعمیر"""

    def __init__(self, repair_data=None, parent=None):
        super().__init__(parent)
        self.repair_data = repair_data
        self._workflow = CustomerWorkflow()
        self._selected_customer_id = None

        self.setWindowTitle("ثبت/ویرایش تعمیر")
        self.setModal(True)
        self.setMinimumSize(700, 600)

        self.init_ui()
        self._init_customer_completer()

        if repair_data:
            self.load_data(repair_data)
        else:
            self.calculate_total(0)

    def init_ui(self):
        layout = QVBoxLayout()

        tabs = QTabWidget()

        # تب اطلاعات اصلی (تعمیر + انتخاب مشتری)
        main_tab = QWidget()
        main_layout = QGridLayout()

        # بخش انتخاب مشتری
        main_layout.addWidget(QLabel("مشتری:"), 0, 0)
        selector_layout = QHBoxLayout()
        self.customer_selector_input = QLineEdit()
        self.customer_selector_input.setPlaceholderText("نام مشتری را جستجو کنید...")
        selector_layout.addWidget(self.customer_selector_input)

        browse_btn = QPushButton("📋 انتخاب از لیست")
        browse_btn.setStyleSheet("background-color: #607D8B; color: white;")
        browse_btn.clicked.connect(self._open_customer_selection)
        selector_layout.addWidget(browse_btn)

        create_btn = QPushButton("➕ افزودن مشتری")
        create_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        create_btn.clicked.connect(self._open_customer_creation)
        selector_layout.addWidget(create_btn)

        main_layout.addLayout(selector_layout, 0, 1)

        main_layout.addWidget(QLabel("برند:"), 1, 0)
        self.brand_input = QLineEdit()
        main_layout.addWidget(self.brand_input, 1, 1)

        main_layout.addWidget(QLabel("مدل:"), 2, 0)
        self.model_input = QLineEdit()
        main_layout.addWidget(self.model_input, 2, 1)

        main_layout.addWidget(QLabel("ایراد:"), 3, 0)
        self.issue_input = QTextEdit()
        self.issue_input.setMaximumHeight(80)
        main_layout.addWidget(self.issue_input, 3, 1)

        main_layout.addWidget(QLabel("وضعیت:"), 4, 0)
        self.status_input = QComboBox()
        self.status_input.addItems(ALL_STATUSES)
        main_layout.addWidget(self.status_input, 4, 1)

        main_layout.addWidget(QLabel("تاریخ دریافت:"), 5, 0)
        self.receive_date_input = PersianDateEdit()
        main_layout.addWidget(self.receive_date_input, 5, 1)

        main_layout.addWidget(QLabel("تاریخ تحویل:"), 6, 0)
        self.delivery_date_input = PersianDateEdit()
        main_layout.addWidget(self.delivery_date_input, 6, 1)

        main_layout.addWidget(QLabel("یادداشت‌ها:"), 7, 0)
        self.repair_notes_input = QTextEdit()
        self.repair_notes_input.setMaximumHeight(80)
        main_layout.addWidget(self.repair_notes_input, 7, 1)

        main_tab.setLayout(main_layout)

        # تب اطلاعات مشتری (فقط خواندنی)
        customer_tab = QWidget()
        customer_layout = QGridLayout()

        customer_layout.addWidget(QLabel("کد مشتری:"), 0, 0)
        self.customer_code_label = QLabel("-")
        customer_layout.addWidget(self.customer_code_label, 0, 1)

        customer_layout.addWidget(QLabel("نام:"), 1, 0)
        self.customer_full_name_label = QLabel("-")
        customer_layout.addWidget(self.customer_full_name_label, 1, 1)

        customer_layout.addWidget(QLabel("تلفن:"), 2, 0)
        self.customer_phone_label = QLabel("-")
        customer_layout.addWidget(self.customer_phone_label, 2, 1)

        customer_layout.addWidget(QLabel("کد ملی:"), 3, 0)
        self.customer_national_id_label = QLabel("-")
        customer_layout.addWidget(self.customer_national_id_label, 3, 1)

        customer_layout.addWidget(QLabel("ایمیل:"), 4, 0)
        self.customer_email_label = QLabel("-")
        customer_layout.addWidget(self.customer_email_label, 4, 1)

        customer_layout.addWidget(QLabel("وبسایت:"), 5, 0)
        self.customer_website_label = QLabel("-")
        customer_layout.addWidget(self.customer_website_label, 5, 1)

        customer_layout.addWidget(QLabel("شهر:"), 6, 0)
        self.customer_city_label = QLabel("-")
        customer_layout.addWidget(self.customer_city_label, 6, 1)

        customer_layout.addWidget(QLabel("استان:"), 7, 0)
        self.customer_province_label = QLabel("-")
        customer_layout.addWidget(self.customer_province_label, 7, 1)

        customer_layout.addWidget(QLabel("کدپستی:"), 8, 0)
        self.customer_postal_code_label = QLabel("-")
        customer_layout.addWidget(self.customer_postal_code_label, 8, 1)

        customer_layout.addWidget(QLabel("آدرس:"), 9, 0)
        self.customer_address_label = QLabel("-")
        self.customer_address_label.setWordWrap(True)
        customer_layout.addWidget(self.customer_address_label, 9, 1)

        customer_layout.addWidget(QLabel("یادداشت‌ها:"), 10, 0)
        self.customer_notes_label = QLabel("-")
        self.customer_notes_label.setWordWrap(True)
        customer_layout.addWidget(self.customer_notes_label, 10, 1)

        edit_customer_btn = QPushButton("✏️ ویرایش مشتری")
        edit_customer_btn.setStyleSheet("background-color: #2196F3; color: white;")
        edit_customer_btn.clicked.connect(self._open_customer_edit)
        customer_layout.addWidget(edit_customer_btn, 11, 0, 1, 2)

        customer_tab.setLayout(customer_layout)

        # تب مالی
        financial_tab = QWidget()
        financial_layout = QGridLayout()

        financial_layout.addWidget(QLabel("هزینه قطعات:"), 0, 0)
        self.parts_cost_input = QSpinBox()
        self.parts_cost_input.setMaximum(999999999)
        self.parts_cost_input.valueChanged.connect(self.calculate_total)
        financial_layout.addWidget(self.parts_cost_input, 0, 1)

        financial_layout.addWidget(QLabel("هزینه تعمیر:"), 1, 0)
        self.labor_cost_input = QSpinBox()
        self.labor_cost_input.setMaximum(999999999)
        self.labor_cost_input.valueChanged.connect(self.calculate_total)
        financial_layout.addWidget(self.labor_cost_input, 1, 1)

        financial_layout.addWidget(QLabel("مالیات (%):"), 2, 0)
        self.tax_input = QDoubleSpinBox()
        self.tax_input.setMaximum(100)
        self.tax_input.valueChanged.connect(self.calculate_total)
        financial_layout.addWidget(self.tax_input, 2, 1)

        financial_layout.addWidget(QLabel("تخفیف:"), 3, 0)
        self.discount_input = QSpinBox()
        self.discount_input.setMaximum(999999999)
        self.discount_input.valueChanged.connect(self.calculate_total)
        financial_layout.addWidget(self.discount_input, 3, 1)

        financial_layout.addWidget(QLabel("مجموع:"), 4, 0)
        self.total_label = QLabel("0 تومان")
        self.total_label.setStyleSheet("font-weight: bold; color: green; font-size: 12pt;")
        financial_layout.addWidget(self.total_label, 4, 1)

        financial_tab.setLayout(financial_layout)

        # تب گارانتی
        notes_tab = QWidget()
        notes_layout = QGridLayout()

        notes_layout.addWidget(QLabel("گارانتی:"), 0, 0)
        self.warranty_input = QTextEdit()
        self.warranty_input.setMaximumHeight(80)
        notes_layout.addWidget(self.warranty_input, 0, 1)

        notes_tab.setLayout(notes_layout)

        tabs.addTab(main_tab, "اطلاعات اصلی")
        tabs.addTab(customer_tab, "اطلاعات مشتری")
        tabs.addTab(financial_tab, "اطلاعات مالی")
        tabs.addTab(notes_tab, "گارانتی")

        layout.addWidget(tabs)

        # دکمه‌ها
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("ذخیره")
        cancel_btn = QPushButton("انصراف")

        save_btn.clicked.connect(self.validate_and_accept)
        cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    # --- بخش انتخاب مشتری ---

    def _init_customer_completer(self):
        self._completer_timer = QTimer()
        self._completer_timer.setSingleShot(True)
        self._completer_timer.timeout.connect(self._on_completer_search)

        self._completer_model = QStandardItemModel()
        self._completer = QCompleter()
        self._completer.setCaseSensitivity(Qt.CaseInsensitive)
        self._completer.setFilterMode(Qt.MatchContains)
        self._completer.setModel(self._completer_model)
        self._completer.setCompletionMode(QCompleter.PopupCompletion)
        self._completer_delegate = CompleterItemDelegate()
        self._completer.popup().setItemDelegate(self._completer_delegate)
        self._completer.popup().setLayoutDirection(Qt.RightToLeft)
        self._completer.activated[QModelIndex].connect(self._on_completer_activated)

        self._completer.setCompletionRole(Qt.EditRole)
        self.customer_selector_input.setCompleter(self._completer)
        self.customer_selector_input.textChanged.connect(self._on_selector_text_changed)

    def _on_selector_text_changed(self, text):
        self._selected_customer_id = None
        self._clear_customer_display()
        self._completer.setCompletionPrefix(text)
        self._completer_timer.start(250)

    def _on_completer_search(self):
        text = self.customer_selector_input.text().strip()
        if len(text) < 2:
            self._completer_model.clear()
            return
        customers = self._workflow.search_customers(text)
        self._completer_model.clear()
        for c in customers:
            phone_line = c['phone'] if c.get('phone') else ''
            label = f"{c['full_name']}\n{phone_line}"
            item = QStandardItem(label)
            item.setData(c['full_name'], Qt.EditRole)
            item.setData(c['id'], Qt.UserRole)
            self._completer_model.appendRow(item)
        self._completer.setCompletionPrefix(text)
        if self._completer.completionCount() > 0:
            self._completer.complete()

    def _on_completer_activated(self, index):
        customer_id = index.data(Qt.UserRole)
        if not customer_id:
            return
        self._select_customer(customer_id)

    def _select_customer(self, customer_id):
        customer = self._workflow.get_customer(customer_id)
        if not customer:
            return
        self._selected_customer_id = customer_id
        self.customer_selector_input.blockSignals(True)
        self.customer_selector_input.setText(customer.get('full_name', ''))
        self.customer_selector_input.blockSignals(False)
        self._refresh_customer_display(customer)

    def _refresh_customer_display(self, customer=None):
        if customer is None:
            if self._selected_customer_id:
                customer = self._workflow.get_customer(self._selected_customer_id)
            if not customer:
                return
        self.customer_code_label.setText(customer.get('customer_code', '') or '-')
        self.customer_full_name_label.setText(customer.get('full_name', '') or '-')
        self.customer_phone_label.setText(customer.get('phone', '') or '-')
        self.customer_national_id_label.setText(customer.get('national_id', '') or '-')
        self.customer_email_label.setText(customer.get('email', '') or '-')
        self.customer_website_label.setText(customer.get('website', '') or '-')
        self.customer_city_label.setText(customer.get('city', '') or '-')
        self.customer_province_label.setText(customer.get('province', '') or '-')
        self.customer_postal_code_label.setText(customer.get('postal_code', '') or '-')
        self.customer_address_label.setText(customer.get('address', '') or '-')
        self.customer_notes_label.setText(customer.get('notes', '') or '-')

    def _clear_customer_display(self):
        self.customer_code_label.setText('-')
        self.customer_full_name_label.setText('-')
        self.customer_phone_label.setText('-')
        self.customer_national_id_label.setText('-')
        self.customer_email_label.setText('-')
        self.customer_website_label.setText('-')
        self.customer_city_label.setText('-')
        self.customer_province_label.setText('-')
        self.customer_postal_code_label.setText('-')
        self.customer_address_label.setText('-')
        self.customer_notes_label.setText('-')

    def _open_customer_selection(self):
        dialog = CustomerSelectionDialog(parent=self)
        if dialog.exec_() == QDialog.Accepted:
            cid = dialog.selected_customer_id
            if cid:
                self._select_customer(cid)

    def _open_customer_creation(self):
        dialog = CustomerEditDialog(customer_id=None, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            created = getattr(dialog, '_created_customer', None)
            if created:
                self._select_customer(created['id'])

    def _open_customer_edit(self):
        if not self._selected_customer_id:
            show_warning(self, "هشدار", "ابتدا یک مشتری انتخاب کنید.")
            return
        dialog = CustomerEditDialog(
            customer_id=self._selected_customer_id, parent=self
        )
        if dialog.exec_() == QDialog.Accepted:
            self._refresh_customer_display()

    # --- ذخیره و بارگذاری ---

    def validate_and_accept(self):
        if not self._selected_customer_id:
            show_warning(self, "خطا", "لطفاً یک مشتری انتخاب کنید.")
            return
        self.accept()

    def calculate_total(self, value):
        """محاسبه مجموع هزینه‌ها"""
        data = {
            'parts_cost': self.parts_cost_input.value(),
            'labor_cost': self.labor_cost_input.value(),
            'tax': self.tax_input.value(),
            'discount': self.discount_input.value(),
        }
        fin = calculate_invoice_totals(data)
        self.total_label.setText(f"{int(fin['total']):,} تومان")

    def load_data(self, data):
        """بارگذاری داده‌ها"""
        customer_id = data.get('customer_id')
        if customer_id:
            self._select_customer(customer_id)
        else:
            name = data.get('customer_name', '')
            phone = data.get('phone', '')
            if phone:
                found = self._workflow.find_customer_by_phone(phone)
                if found:
                    self._select_customer(found['id'])
            if self._selected_customer_id is None and name:
                exact = self._workflow._service.find_by_full_name(name)
                if exact:
                    self._select_customer(exact[0]['id'])

        self.brand_input.setText(data.get('brand', ''))
        self.model_input.setText(data.get('model', ''))
        self.issue_input.setText(data.get('issue', ''))
        self.status_input.setCurrentText(data.get('status', STATUS_PENDING))
        self.receive_date_input.setText(data.get('receive_date', ''))
        self.delivery_date_input.setText(data.get('delivery_date', ''))
        self.parts_cost_input.setValue(data.get('parts_cost', 0))
        self.labor_cost_input.setValue(data.get('labor_cost', 0))
        self.tax_input.setValue(data.get('tax', 0))
        self.discount_input.setValue(data.get('discount', 0))
        self.repair_notes_input.setText(data.get('notes', ''))
        self.warranty_input.setText(data.get('warranty', ''))
        self.calculate_total(0)

    def get_data(self):
        """دریافت داده‌ها"""
        customer_name = ''
        phone = ''
        if self._selected_customer_id:
            customer = self._workflow.get_customer(self._selected_customer_id)
            if customer:
                customer_name = customer.get('full_name', '')
                phone = customer.get('phone', '') or ''
        return {
            'customer_id': self._selected_customer_id,
            'customer_name': customer_name,
            'phone': phone,
            'brand': self.brand_input.text(),
            'model': self.model_input.text(),
            'issue': self.issue_input.toPlainText(),
            'status': self.status_input.currentText(),
            'receive_date': self.receive_date_input.get_date(),
            'delivery_date': self.delivery_date_input.get_date(),
            'parts_cost': self.parts_cost_input.value(),
            'labor_cost': self.labor_cost_input.value(),
            'tax': self.tax_input.value(),
            'discount': self.discount_input.value(),
            'notes': self.repair_notes_input.toPlainText(),
            'warranty': self.warranty_input.toPlainText()
        }
