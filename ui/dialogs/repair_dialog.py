from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
                              QTabWidget, QWidget, QLineEdit, QTextEdit, QSpinBox,
                              QDoubleSpinBox, QComboBox, QLabel, QPushButton,
                              QCompleter, QStyledItemDelegate)
from PyQt5.QtCore import Qt, QTimer, QStringListModel, QRegularExpression, QSize
from PyQt5.QtGui import (
    QFont,
    QRegularExpressionValidator,
    QColor,
)

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QTabWidget, QWidget, QLineEdit, QTextEdit, QSpinBox,
    QDoubleSpinBox, QComboBox, QLabel, QPushButton,
    QCompleter, QStyledItemDelegate, QStyle
)

from services.notification_service import show_warning, show_question
from core.status import ALL_STATUSES, STATUS_PENDING
from repair_manager.ui.components import PersianDateEdit
from services.invoice_calculator import calculate_invoice_totals
from services.customer_service import CustomerService


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
        self._customer_service = CustomerService()
        self._completer_cache = {}
        self._skip_next_search = False

        self.setWindowTitle("ثبت/ویرایش تعمیر")
        self.setModal(True)
        self.setMinimumSize(700, 600)

        self.init_ui()
        self._init_customer_completer()
        self._connect_auto_fill()

        if repair_data:
            self.load_data(repair_data)
        else:
            self.calculate_total(0)

    def init_ui(self):
        layout = QVBoxLayout()

        tabs = QTabWidget()

        # تب اطلاعات اصلی
        main_tab = QWidget()
        main_layout = QGridLayout()

        main_layout.addWidget(QLabel("نام مشتری:"), 0, 0)
        self.customer_name_input = QLineEdit()
        main_layout.addWidget(self.customer_name_input, 0, 1)

        main_layout.addWidget(QLabel("تلفن:"), 1, 0)
        self.phone_input = QLineEdit()
        self.phone_input.setValidator(QRegularExpressionValidator(QRegularExpression(r'^0\d{10}$')))
        main_layout.addWidget(self.phone_input, 1, 1)

        main_layout.addWidget(QLabel("برند:"), 2, 0)
        self.brand_input = QLineEdit()
        main_layout.addWidget(self.brand_input, 2, 1)

        main_layout.addWidget(QLabel("مدل:"), 3, 0)
        self.model_input = QLineEdit()
        main_layout.addWidget(self.model_input, 3, 1)

        main_layout.addWidget(QLabel("ایراد:"), 4, 0)
        self.issue_input = QTextEdit()
        self.issue_input.setMaximumHeight(80)
        main_layout.addWidget(self.issue_input, 4, 1)

        main_layout.addWidget(QLabel("وضعیت:"), 5, 0)
        self.status_input = QComboBox()
        self.status_input.addItems(ALL_STATUSES)
        main_layout.addWidget(self.status_input, 5, 1)

        main_layout.addWidget(QLabel("تاریخ دریافت:"), 6, 0)
        self.receive_date_input = PersianDateEdit()
        main_layout.addWidget(self.receive_date_input, 6, 1)

        main_layout.addWidget(QLabel("تاریخ تحویل:"), 7, 0)
        self.delivery_date_input = PersianDateEdit()
        main_layout.addWidget(self.delivery_date_input, 7, 1)

        main_tab.setLayout(main_layout)

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

        # تب اطلاعات مشتری
        customer_tab = QWidget()
        customer_layout = QGridLayout()

        customer_layout.addWidget(QLabel("ایمیل:"), 0, 0)
        self.email_input = QLineEdit()
        customer_layout.addWidget(self.email_input, 0, 1)

        customer_layout.addWidget(QLabel("وبسایت:"), 1, 0)
        self.website_input = QLineEdit()
        customer_layout.addWidget(self.website_input, 1, 1)

        customer_layout.addWidget(QLabel("کد ملی:"), 2, 0)
        self.national_id_input = QLineEdit()
        customer_layout.addWidget(self.national_id_input, 2, 1)

        customer_layout.addWidget(QLabel("آدرس:"), 3, 0)
        self.address_input = QLineEdit()
        customer_layout.addWidget(self.address_input, 3, 1)

        customer_layout.addWidget(QLabel("شهر:"), 4, 0)
        self.city_input = QLineEdit()
        customer_layout.addWidget(self.city_input, 4, 1)

        customer_layout.addWidget(QLabel("استان:"), 5, 0)
        self.province_input = QLineEdit()
        customer_layout.addWidget(self.province_input, 5, 1)

        customer_layout.addWidget(QLabel("کدپستی:"), 6, 0)
        self.postal_code_input = QLineEdit()
        customer_layout.addWidget(self.postal_code_input, 6, 1)

        customer_tab.setLayout(customer_layout)

        # تب یادداشت و گارانتی
        notes_tab = QWidget()
        notes_layout = QGridLayout()

        notes_layout.addWidget(QLabel("یادداشت‌ها:"), 0, 0)
        self.notes_input = QTextEdit()
        notes_layout.addWidget(self.notes_input, 0, 1)

        notes_layout.addWidget(QLabel("گارانتی:"), 1, 0)
        self.warranty_input = QTextEdit()
        self.warranty_input.setMaximumHeight(80)
        notes_layout.addWidget(self.warranty_input, 1, 1)

        notes_tab.setLayout(notes_layout)

        tabs.addTab(main_tab, "اطلاعات اصلی")
        tabs.addTab(customer_tab, "اطلاعات مشتری")
        tabs.addTab(financial_tab, "اطلاعات مالی")
        tabs.addTab(notes_tab, "یادداشت و گارانتی")

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

    def _init_customer_completer(self):
        self._completer_timer = QTimer()
        self._completer_timer.setSingleShot(True)
        self._completer_timer.timeout.connect(self._on_completer_search)

        self._completer_model = QStringListModel()
        self._completer = QCompleter()
        self._completer.setCaseSensitivity(Qt.CaseInsensitive)
        self._completer.setFilterMode(Qt.MatchContains)
        self._completer.setModel(self._completer_model)
        self._completer.setCompletionMode(QCompleter.PopupCompletion)
        self._completer_delegate = CompleterItemDelegate()
        self._completer.popup().setItemDelegate(self._completer_delegate)
        self._completer.popup().setLayoutDirection(Qt.RightToLeft)
        self._completer.activated.connect(self._on_completer_activated)

        self.customer_name_input.setCompleter(self._completer)
        self.customer_name_input.textChanged.connect(self._on_name_text_changed)

    def _on_name_text_changed(self, text):
        self._completer.setCompletionPrefix(text)
        self._completer_timer.start(250)

    def _on_completer_search(self):
        text = self.customer_name_input.text().strip()
        if len(text) < 2:
            self._completer_model.setStringList([])
            return
        if self._skip_next_search:
            self._skip_next_search = False
            return
        customers = self._customer_service.search_customers(text)
        items = []
        self._completer_cache = {}
        for c in customers:
            label = f"\U0001f464 {c['full_name']}\n\U0001f4de {c['phone']}"
            items.append(label)
            self._completer_cache[label] = c
        self._completer_model.setStringList(items)

    def _on_completer_activated(self, text):
        customer = self._completer_cache.get(text)
        if not customer:
            return
        self._skip_next_search = True
        self.customer_name_input.blockSignals(True)
        self.customer_name_input.setText(customer.get('full_name', ''))
        self.customer_name_input.blockSignals(False)
        self.phone_input.setText(customer.get('phone', ''))
        if customer.get('email'):
            self.email_input.setText(customer['email'])
        if customer.get('address'):
            self.address_input.setText(customer['address'])
        if customer.get('city'):
            self.city_input.setText(customer['city'])
        if customer.get('province'):
            self.province_input.setText(customer['province'])
        if customer.get('postal_code'):
            self.postal_code_input.setText(customer['postal_code'])
        if customer.get('website'):
            self.website_input.setText(customer['website'])
        if customer.get('national_id'):
            self.national_id_input.setText(customer['national_id'])
        if customer.get('notes'):
            self.notes_input.setPlainText(customer['notes'])

    def _connect_auto_fill(self):
        self.phone_input.editingFinished.connect(self._on_phone_editing_finished)

    def _on_phone_editing_finished(self):
        phone = self.phone_input.text()
        if not phone or not self.phone_input.hasAcceptableInput():
            return
        customer = self._customer_service.find_customer(phone)
        if not customer:
            return
        self.phone_input.blockSignals(True)
        self.customer_name_input.setText(customer.get('full_name', ''))
        if customer.get('email'):
            self.email_input.setText(customer['email'])
        if customer.get('website'):
            self.website_input.setText(customer['website'])
        if customer.get('national_id'):
            self.national_id_input.setText(customer['national_id'])
        if customer.get('address'):
            self.address_input.setText(customer['address'])
        if customer.get('city'):
            self.city_input.setText(customer['city'])
        if customer.get('province'):
            self.province_input.setText(customer['province'])
        if customer.get('postal_code'):
            self.postal_code_input.setText(customer['postal_code'])
        if customer.get('notes'):
            self.notes_input.setPlainText(customer['notes'])
        self.phone_input.blockSignals(False)

    def validate_and_accept(self):
        if self.phone_input.text() and not self.phone_input.hasAcceptableInput():
            show_warning(self, "خطا", "شماره تلفن باید ۱۱ رقم و با ۰ شروع شود")
            return
        if self.repair_data:
            self.accept()
            return
        phone = self.phone_input.text().strip()
        full_name = self.customer_name_input.text().strip()
        if phone:
            existing = self._customer_service.find_by_phone(phone)
            if existing:
                self.accept()
                return
            customer_data = self._get_customer_data()
            self._customer_service.create_customer(customer_data)
            self.accept()
            return
        if full_name:
            existing = self._customer_service.find_by_full_name(full_name)
            if existing:
                confirmed = show_question(
                    self,
                    "مشتری مشابه",
                    "مشتری مشابهی وجود دارد.\nاز همان مشتری استفاده شود؟"
                )
                if confirmed:
                    self.accept()
                    return
            customer_data = self._get_customer_data()
            self._customer_service.create_customer(customer_data)
            self.accept()
            return
        self.accept()

    def _get_customer_data(self):
        return {
            'full_name': self.customer_name_input.text().strip(),
            'phone': self.phone_input.text().strip(),
            'email': self.email_input.text().strip(),
            'website': self.website_input.text().strip(),
            'national_id': self.national_id_input.text().strip(),
            'address': self.address_input.text().strip(),
            'city': self.city_input.text().strip(),
            'province': self.province_input.text().strip(),
            'postal_code': self.postal_code_input.text().strip(),
            'notes': self.notes_input.toPlainText().strip(),
        }

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
        self.customer_name_input.setText(data.get('customer_name', ''))
        self.phone_input.setText(data.get('phone', ''))
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
        self.notes_input.setText(data.get('notes', ''))
        self.warranty_input.setText(data.get('warranty', ''))
        self.calculate_total(0)

    def get_data(self):
        """دریافت داده‌ها"""
        return {
            'customer_name': self.customer_name_input.text(),
            'phone': self.phone_input.text(),
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
            'notes': self.notes_input.toPlainText(),
            'warranty': self.warranty_input.toPlainText()
        }
