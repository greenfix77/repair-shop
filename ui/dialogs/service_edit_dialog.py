from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QGridLayout, QWidget,
                              QLineEdit, QTextEdit, QLabel, QPushButton,
                              QSpinBox, QCheckBox)
from PyQt5.QtCore import Qt

from services.notification_service import show_warning, show_error
from services.service_service import ServiceService


class ServiceEditDialog(QDialog):
    """دیالوگ افزودن/ویرایش خدمت"""

    def __init__(self, service_id=None, parent=None):
        super().__init__(parent)
        self._service = ServiceService()
        self._service_id = service_id
        self._is_create = service_id is None
        self._created_service = None

        self.setWindowTitle("افزودن خدمت" if self._is_create else "ویرایش خدمت")
        self.setModal(True)
        self.setMinimumSize(500, 400)

        if self._is_create:
            self.service = {}
            self._init_failed = False
        else:
            self.service = self._service.get_service(service_id)
            if not self.service:
                show_error(self, "خطا", "خدمت یافت نشد.")
                self._init_failed = True
                return
            self._init_failed = False

        self.init_ui()
        self._load_fields()

    def init_ui(self):
        layout = QVBoxLayout()

        form = QWidget()
        grid = QGridLayout()

        grid.addWidget(QLabel("کد خدمت:"), 0, 0)
        self.service_code_label = QLabel("-")
        self.service_code_label.setStyleSheet("color: #666;")
        grid.addWidget(self.service_code_label, 0, 1)

        grid.addWidget(QLabel("نام خدمت *:"), 1, 0)
        self.name_input = QLineEdit()
        grid.addWidget(self.name_input, 1, 1)

        grid.addWidget(QLabel("قیمت پیش‌فرض:"), 2, 0)
        self.price_input = QSpinBox()
        self.price_input.setMaximum(999999999)
        self.price_input.setValue(0)
        grid.addWidget(self.price_input, 2, 1)

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

    def _load_fields(self):
        s = self.service
        self.service_code_label.setText(s.get('service_code', '') or '-')
        self.name_input.setText(s.get('name', ''))
        self.price_input.setValue(s.get('default_price', 0))
        self.description_input.setPlainText(s.get('description', ''))
        self.is_active_input.setChecked(s.get('is_active', True))

    def _get_data(self):
        return {
            'name': self.name_input.text().strip(),
            'default_price': self.price_input.value(),
            'description': self.description_input.toPlainText().strip(),
            'is_active': self.is_active_input.isChecked(),
        }

    def _save(self):
        data = self._get_data()

        if not data['name']:
            show_warning(self, "خطا", "نام خدمت الزامی است.")
            return

        try:
            if self._is_create:
                result = self._service.create_service(data)
                self._created_service = result
            else:
                result = self._service.update_service(self._service_id, data)
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
