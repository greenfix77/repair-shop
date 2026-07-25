from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QGridLayout, QWidget,
                              QLineEdit, QTextEdit, QLabel, QPushButton,
                              QSpinBox, QCheckBox, QComboBox)
from PyQt5.QtCore import Qt

from services.notification_service import show_warning, show_error
from services.charge_service import ChargeService


CHARGE_CATEGORIES = [
    "ارسال",
    "پیک",
    "بسته‌بندی",
    "بیمه",
    "خدمات متفرقه",
    "سایر",
]


class ChargeEditDialog(QDialog):
    """دیالوگ افزودن/ویرایش هزینه"""

    def __init__(self, charge_id=None, parent=None):
        super().__init__(parent)
        self._service = ChargeService()
        self._charge_id = charge_id
        self._is_create = charge_id is None
        self._created_charge = None

        self.setWindowTitle("افزودن هزینه" if self._is_create else "ویرایش هزینه")
        self.setModal(True)
        self.setMinimumSize(500, 420)

        if self._is_create:
            self.charge = {}
            self._init_failed = False
        else:
            self.charge = self._service.get_charge(charge_id)
            if not self.charge:
                show_error(self, "خطا", "هزینه یافت نشد.")
                self._init_failed = True
                return
            self._init_failed = False

        self.init_ui()
        self._load_fields()

    def init_ui(self):
        layout = QVBoxLayout()

        form = QWidget()
        grid = QGridLayout()

        grid.addWidget(QLabel("نام هزینه *:"), 0, 0)
        self.name_input = QLineEdit()
        grid.addWidget(self.name_input, 0, 1)

        grid.addWidget(QLabel("دسته:"), 1, 0)
        self.category_combo = QComboBox()
        self.category_combo.setEditable(True)
        self.category_combo.addItems(CHARGE_CATEGORIES)
        self.category_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.category_combo.setMinimumContentsLength(10)
        grid.addWidget(self.category_combo, 1, 1)

        grid.addWidget(QLabel("مبلغ پیش‌فرض:"), 2, 0)
        self.default_amount_input = QSpinBox()
        self.default_amount_input.setMinimum(0)
        self.default_amount_input.setMaximum(999999999)
        self.default_amount_input.setValue(0)
        grid.addWidget(self.default_amount_input, 2, 1)

        grid.addWidget(QLabel("توضیحات:"), 3, 0)
        self.description_input = QTextEdit()
        self.description_input.setMaximumHeight(80)
        grid.addWidget(self.description_input, 3, 1)

        grid.addWidget(QLabel("فعال:"), 4, 0)
        self.is_active_input = QCheckBox()
        self.is_active_input.setChecked(True)
        grid.addWidget(self.is_active_input, 4, 1)

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
        self.setLayoutDirection(Qt.RightToLeft)

    def _load_fields(self):
        c = self.charge
        self.name_input.setText(c.get('name', ''))
        self.category_combo.setEditText(c.get('category', '') or '')
        self.default_amount_input.setValue(c.get('default_amount', 0) or 0)
        self.description_input.setPlainText(c.get('description', ''))
        self.is_active_input.setChecked(c.get('is_active', True))

    def _get_data(self):
        return {
            'name': self.name_input.text().strip(),
            'category': self.category_combo.currentText().strip(),
            'default_amount': self.default_amount_input.value(),
            'description': self.description_input.toPlainText().strip(),
            'is_active': self.is_active_input.isChecked(),
        }

    def _save(self):
        data = self._get_data()

        if not data['name']:
            show_warning(self, "خطا", "نام هزینه الزامی است.")
            return

        try:
            if self._is_create:
                result = self._service.create_charge(data)
                self._created_charge = result
            else:
                result = self._service.update_charge(self._charge_id, data)
        except ValueError as e:
            show_warning(self, "خطا", str(e))
            return
        except Exception as e:
            show_error(self, "خطا", f"ذخیره‌سازی ناموفق بود: {e}")
            return

        if not result:
            show_error(self, "خطا", "ذخیره‌سازی ناموفق بود.")
            return

        self.accept()
