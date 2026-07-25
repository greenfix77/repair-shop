from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QGridLayout, QWidget,
                              QLineEdit, QTextEdit, QLabel, QPushButton,
                              QSpinBox, QCheckBox)
from PyQt5.QtCore import Qt

from services.notification_service import show_warning, show_error
from services.part_service import PartService


class PartEditDialog(QDialog):
    """دیالوگ افزودن/ویرایش قطعه"""

    def __init__(self, part_id=None, parent=None):
        super().__init__(parent)
        self._service = PartService()
        self._part_id = part_id
        self._is_create = part_id is None
        self._created_part = None

        self.setWindowTitle("افزودن قطعه" if self._is_create else "ویرایش قطعه")
        self.setModal(True)
        self.setMinimumSize(500, 450)

        if self._is_create:
            self.part = {}
            self._init_failed = False
        else:
            self.part = self._service.get_part(part_id)
            if not self.part:
                show_error(self, "خطا", "قطعه یافت نشد.")
                self._init_failed = True
                return
            self._init_failed = False

        self.init_ui()
        self._load_fields()

    def init_ui(self):
        layout = QVBoxLayout()

        form = QWidget()
        grid = QGridLayout()

        grid.addWidget(QLabel("کد قطعه:"), 0, 0)
        self.part_code_label = QLabel("-")
        self.part_code_label.setStyleSheet("color: #666;")
        grid.addWidget(self.part_code_label, 0, 1)

        grid.addWidget(QLabel("نام قطعه *:"), 1, 0)
        self.name_input = QLineEdit()
        grid.addWidget(self.name_input, 1, 1)

        grid.addWidget(QLabel("قیمت خرید:"), 2, 0)
        self.purchase_price_input = QSpinBox()
        self.purchase_price_input.setMaximum(999999999)
        self.purchase_price_input.setValue(0)
        grid.addWidget(self.purchase_price_input, 2, 1)

        grid.addWidget(QLabel("قیمت فروش پیشنهادی:"), 3, 0)
        self.default_sale_price_input = QSpinBox()
        self.default_sale_price_input.setMaximum(999999999)
        self.default_sale_price_input.setValue(0)
        grid.addWidget(self.default_sale_price_input, 3, 1)

        grid.addWidget(QLabel("قیمت فروش:"), 4, 0)
        self.sale_price_input = QSpinBox()
        self.sale_price_input.setMaximum(999999999)
        self.sale_price_input.setValue(0)
        grid.addWidget(self.sale_price_input, 4, 1)

        grid.addWidget(QLabel("موجودی:"), 5, 0)
        self.stock_quantity_input = QSpinBox()
        self.stock_quantity_input.setMaximum(999999999)
        self.stock_quantity_input.setValue(0)
        grid.addWidget(self.stock_quantity_input, 5, 1)

        grid.addWidget(QLabel("توضیحات:"), 6, 0)
        self.description_input = QTextEdit()
        self.description_input.setMaximumHeight(80)
        grid.addWidget(self.description_input, 6, 1)

        grid.addWidget(QLabel("فعال:"), 7, 0)
        self.is_active_input = QCheckBox()
        self.is_active_input.setChecked(True)
        grid.addWidget(self.is_active_input, 7, 1)

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
        p = self.part
        self.part_code_label.setText(p.get('part_code', '') or '-')
        self.name_input.setText(p.get('name', ''))
        purchase_price = p.get('purchase_price', 0) or 0
        self.purchase_price_input.setValue(purchase_price)
        self.default_sale_price_input.setValue(p.get('default_sale_price', purchase_price) or purchase_price)
        self.sale_price_input.setValue(p.get('sale_price', 0))
        self.stock_quantity_input.setValue(p.get('stock_quantity', 0))
        self.description_input.setPlainText(p.get('description', ''))
        self.is_active_input.setChecked(p.get('is_active', True))

    def _get_data(self):
        data = {
            'name': self.name_input.text().strip(),
            'purchase_price': self.purchase_price_input.value(),
            'sale_price': self.sale_price_input.value(),
            'stock_quantity': self.stock_quantity_input.value(),
            'description': self.description_input.toPlainText().strip(),
            'is_active': self.is_active_input.isChecked(),
        }
        default_sale_price = self.default_sale_price_input.value()
        if self._is_create and default_sale_price <= 0:
            default_sale_price = data['purchase_price']
        data['default_sale_price'] = default_sale_price
        return data

    def _save(self):
        data = self._get_data()

        if not data['name']:
            show_warning(self, "خطا", "نام قطعه الزامی است.")
            return

        try:
            if self._is_create:
                result = self._service.create_part(data)
                self._created_part = result
            else:
                result = self._service.update_part(self._part_id, data)
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
