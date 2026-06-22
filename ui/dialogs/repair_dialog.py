from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
                              QTabWidget, QWidget, QLineEdit, QTextEdit, QSpinBox,
                              QDoubleSpinBox, QComboBox, QLabel, QPushButton)
from PyQt5.QtCore import QRegularExpression
from PyQt5.QtGui import QFont, QRegularExpressionValidator

from services.notification_service import show_warning
from core.status import ALL_STATUSES, STATUS_PENDING
from repair_manager.ui.components import PersianDateEdit
from services.invoice_calculator import calculate_invoice_totals


class RepairDialog(QDialog):
    """دیالوگ افزودن/ویرایش تعمیر"""

    def __init__(self, repair_data=None, parent=None):
        super().__init__(parent)
        self.repair_data = repair_data

        self.setWindowTitle("ثبت/ویرایش تعمیر")
        self.setModal(True)
        self.setMinimumSize(700, 600)

        self.init_ui()

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

    def validate_and_accept(self):
        if self.phone_input.text() and not self.phone_input.hasAcceptableInput():
            show_warning(self, "خطا", "شماره تلفن باید ۱۱ رقم و با ۰ شروع شود")
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
