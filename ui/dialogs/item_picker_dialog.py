from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                              QTableWidget, QTableWidgetItem, QLabel,
                              QLineEdit, QPushButton, QAbstractItemView,
                              QHeaderView)
from PyQt5.QtCore import Qt


class ItemPickerDialog(QDialog):
    """دیالوگ انتخاب آیتم از کاتالوگ (خدمات یا قطعات)"""

    def __init__(self, title, items, name_key, price_key, parent=None):
        super().__init__(parent)
        self.selected_item = None

        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumSize(550, 350)

        layout = QVBoxLayout()

        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("🔍 جستجو:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("نام یا کد...")
        self.search_input.textChanged.connect(self._filter)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["نام", "قیمت", "کد"])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.doubleClicked.connect(self._on_select)
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        select_btn = QPushButton("انتخاب")
        select_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        select_btn.clicked.connect(self._on_select)
        btn_layout.addWidget(select_btn)

        cancel_btn = QPushButton("انصراف")
        cancel_btn.setStyleSheet("background-color: #607D8B; color: white;")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

        self._items = items
        self._name_key = name_key
        self._price_key = price_key
        self._load_items()

    def _load_items(self):
        self.table.setRowCount(0)
        for item in self._items:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(item.get(self._name_key, '') or '-'))
            self.table.setItem(row, 1, QTableWidgetItem(f"{item.get(self._price_key, 0):,}"))
            code = item.get('service_code', '') or item.get('part_code', '') or '-'
            self.table.setItem(row, 2, QTableWidgetItem(code))
            self.table.item(row, 0).setData(Qt.UserRole, item)

    def _filter(self, text):
        text = text.strip().lower()
        for row in range(self.table.rowCount()):
            name = self.table.item(row, 0).text().lower()
            code = self.table.item(row, 2).text().lower()
            self.table.setRowHidden(row, bool(text) and text not in name and text not in code)

    def _on_select(self):
        row = self.table.currentRow()
        if row < 0:
            return
        item = self.table.item(row, 0)
        if item:
            self.selected_item = item.data(Qt.UserRole)
            self.accept()
