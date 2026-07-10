from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QGridLayout, QWidget,
                              QLineEdit, QTextEdit, QLabel, QPushButton)
from PyQt5.QtGui import QRegularExpressionValidator
from PyQt5.QtCore import QRegularExpression

from services.notification_service import show_warning, show_error
from services.customer_workflow import CustomerWorkflow


class CustomerEditDialog(QDialog):
    """دیالوگ افزودن/ویرایش اطلاعات مشتری"""

    def __init__(self, customer_id=None, parent=None):
        super().__init__(parent)
        self._workflow = CustomerWorkflow()
        self._customer_id = customer_id
        self._is_create = customer_id is None

        self.setWindowTitle("افزودن مشتری" if self._is_create else "ویرایش مشتری")
        self.setModal(True)
        self.setMinimumSize(600, 480)

        if self._is_create:
            self.customer = {}
            self._init_failed = False
        else:
            self.customer = self._workflow.get_customer(customer_id)
            if not self.customer:
                show_error(self, "خطا", "مشتری یافت نشد.")
                self._init_failed = True
                return
            self._init_failed = False

        self.init_ui()
        self._load_fields()

    def init_ui(self):
        layout = QVBoxLayout()

        form = QWidget()
        grid = QGridLayout()

        grid.addWidget(QLabel("نام مشتری:"), 0, 0)
        self.full_name_input = QLineEdit()
        grid.addWidget(self.full_name_input, 0, 1)

        grid.addWidget(QLabel("تلفن:"), 1, 0)
        self.phone_input = QLineEdit()
        self.phone_input.setValidator(
            QRegularExpressionValidator(QRegularExpression(r'^0\d{10}$'))
        )
        grid.addWidget(self.phone_input, 1, 1)

        grid.addWidget(QLabel("ایمیل:"), 2, 0)
        self.email_input = QLineEdit()
        grid.addWidget(self.email_input, 2, 1)

        grid.addWidget(QLabel("وبسایت:"), 3, 0)
        self.website_input = QLineEdit()
        grid.addWidget(self.website_input, 3, 1)

        grid.addWidget(QLabel("کد ملی:"), 4, 0)
        self.national_id_input = QLineEdit()
        self.national_id_input.setValidator(QRegularExpressionValidator(QRegularExpression(r'^\d{0,10}$')))
        grid.addWidget(self.national_id_input, 4, 1)

        grid.addWidget(QLabel("آدرس:"), 5, 0)
        self.address_input = QLineEdit()
        grid.addWidget(self.address_input, 5, 1)

        grid.addWidget(QLabel("شهر:"), 6, 0)
        self.city_input = QLineEdit()
        grid.addWidget(self.city_input, 6, 1)

        grid.addWidget(QLabel("استان:"), 7, 0)
        self.province_input = QLineEdit()
        grid.addWidget(self.province_input, 7, 1)

        grid.addWidget(QLabel("کدپستی:"), 8, 0)
        self.postal_code_input = QLineEdit()
        self.postal_code_input.setValidator(QRegularExpressionValidator(QRegularExpression(r'^\d{0,10}$')))
        grid.addWidget(self.postal_code_input, 8, 1)

        grid.addWidget(QLabel("یادداشت‌ها:"), 9, 0)
        self.notes_input = QTextEdit()
        self.notes_input.setMaximumHeight(80)
        grid.addWidget(self.notes_input, 9, 1)

        form.setLayout(grid)
        layout.addWidget(form)

        btn_layout = QWidget()
        btns = QVBoxLayout()
        btns.setContentsMargins(0, 10, 0, 0)

        save_btn = QPushButton("ذخیره" if self._is_create else "ذخیره تغییرات")
        save_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        save_btn.clicked.connect(self._save)
        btns.addWidget(save_btn)

        cancel_btn = QPushButton("انصراف")
        cancel_btn.setStyleSheet("background-color: #607D8B; color: white;")
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(cancel_btn)

        btn_layout.setLayout(btns)
        layout.addWidget(btn_layout)

        self.setLayout(layout)

    def _load_fields(self):
        c = self.customer
        self.full_name_input.setText(c.get('full_name', ''))
        self.phone_input.setText(c.get('phone', '') or '')
        self.email_input.setText(c.get('email', ''))
        self.website_input.setText(c.get('website', ''))
        self.national_id_input.setText(c.get('national_id', ''))
        self.address_input.setText(c.get('address', ''))
        self.city_input.setText(c.get('city', ''))
        self.province_input.setText(c.get('province', ''))
        self.postal_code_input.setText(c.get('postal_code', ''))
        self.notes_input.setPlainText(c.get('notes', ''))

    def _get_data(self):
        return {
            'full_name': self.full_name_input.text().strip(),
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

    def _save(self):
        data = self._get_data()

        if data['phone'] and not self.phone_input.hasAcceptableInput():
            show_warning(self, "خطا", "شماره تلفن باید ۱۱ رقم و با ۰ شروع شود")
            return

        if data['national_id'] and len(data['national_id']) != 10:
            show_warning(self, "خطا", "کد ملی باید دقیقاً ۱۰ رقم باشد.")
            return

        if data['postal_code'] and len(data['postal_code']) != 10:
            show_warning(self, "خطا", "کد پستی باید دقیقاً ۱۰ رقم باشد.")
            return

        if not data['phone'] and not data['full_name']:
            show_warning(self, "خطا", "حداقل نام یا تلفن مشتری را وارد کنید")
            return

        try:
            if self._is_create:
                duplicate_msg = self._workflow.check_create_duplicate(data)
                if duplicate_msg:
                    show_warning(self, "خطا", duplicate_msg)
                    return
                result = self._workflow.create_customer(data)
            else:
                result = self._workflow.update_customer(self._customer_id, data)
        except Exception as e:
            show_error(self, "خطا", f"ذخیره‌سازی ناموفق بود: {e}")
            return

        if not result:
            show_error(self, "خطا", "ذخیره‌سازی ناموفق بود.")
            return

        self.accept()
