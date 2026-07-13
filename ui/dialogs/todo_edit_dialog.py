from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QGridLayout, QWidget,
                               QLineEdit, QTextEdit, QLabel, QPushButton,
                               QComboBox, QCheckBox)
from PyQt5.QtCore import Qt

from services.notification_service import show_warning, show_error
from services.todo_service import TodoService


class TodoEditDialog(QDialog):
    """دیالوگ افزودن/ویرایش وظیفه"""

    PRIORITIES = ["کم", "معمولی", "زیاد", "فوری"]

    def __init__(self, todo_id=None, parent=None):
        super().__init__(parent)
        self._service = TodoService()
        self._todo_id = todo_id
        self._is_create = todo_id is None
        self._created_todo = None

        self.setWindowTitle("افزودن وظیفه" if self._is_create else "ویرایش وظیفه")
        self.setModal(True)
        self.setMinimumSize(500, 400)

        if self._is_create:
            self.todo = {}
            self._init_failed = False
        else:
            self.todo = self._service.get_todo(todo_id)
            if not self.todo:
                show_error(self, "خطا", "وظیفه یافت نشد.")
                self._init_failed = True
                return
            self._init_failed = False

        self.init_ui()
        self._load_fields()

    def init_ui(self):
        layout = QVBoxLayout()

        form = QWidget()
        grid = QGridLayout()

        grid.addWidget(QLabel("عنوان *:"), 0, 0)
        self.title_input = QLineEdit()
        grid.addWidget(self.title_input, 0, 1)

        grid.addWidget(QLabel("توضیحات:"), 1, 0)
        self.description_input = QTextEdit()
        self.description_input.setMaximumHeight(80)
        grid.addWidget(self.description_input, 1, 1)

        grid.addWidget(QLabel("تاریخ سررسید:"), 2, 0)
        self.due_date_input = QLineEdit()
        self.due_date_input.setPlaceholderText("مثال: 1405/04/22")
        grid.addWidget(self.due_date_input, 2, 1)

        grid.addWidget(QLabel("اولویت:"), 3, 0)
        self.priority_combo = QComboBox()
        self.priority_combo.addItems(self.PRIORITIES)
        self.priority_combo.setCurrentText("معمولی")
        grid.addWidget(self.priority_combo, 3, 1)

        grid.addWidget(QLabel("انجام شده:"), 4, 0)
        self.is_done_check = QCheckBox()
        grid.addWidget(self.is_done_check, 4, 1)

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
        t = self.todo
        self.title_input.setText(t.get('title', ''))
        self.description_input.setPlainText(t.get('description', ''))
        self.due_date_input.setText(t.get('due_date', ''))
        priority = t.get('priority', 'معمولی')
        idx = self.priority_combo.findText(priority)
        if idx >= 0:
            self.priority_combo.setCurrentIndex(idx)
        else:
            self.priority_combo.setCurrentText('معمولی')
        self.is_done_check.setChecked(t.get('is_done', False))

    def _get_data(self):
        return {
            'title': self.title_input.text().strip(),
            'description': self.description_input.toPlainText().strip(),
            'due_date': self.due_date_input.text().strip(),
            'priority': self.priority_combo.currentText(),
            'is_done': self.is_done_check.isChecked(),
        }

    def _save(self):
        data = self._get_data()

        if not data['title']:
            show_warning(self, "خطا", "عنوان وظیفه الزامی است.")
            return

        try:
            if self._is_create:
                result = self._service.create_todo(data)
                self._created_todo = result
            else:
                result = self._service.update_todo(self._todo_id, data)
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