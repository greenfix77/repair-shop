from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                              QTableWidget, QTableWidgetItem, QLabel,
                              QLineEdit, QPushButton, QAbstractItemView,
                              QHeaderView)
from PyQt5.QtCore import Qt

from services.customer_workflow import CustomerWorkflow


class CustomerSelectionDialog(QDialog):
    """دیالوگ انتخاب مشتری از لیست"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._workflow = CustomerWorkflow()
        self.selected_customer_id = None

        self.setWindowTitle("انتخاب مشتری")
        self.setModal(True)
        self.setMinimumSize(600, 400)

        layout = QVBoxLayout()

        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("🔍 جستجو:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("نام یا تلفن...")
        self.search_input.textChanged.connect(self._filter)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["کد", "نام", "تلفن", "کد ملی"])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
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
        self._load_customers()

    def _load_customers(self):
        customers = self._workflow.get_all_customers()
        customers = sorted(customers, key=lambda c: c.get('full_name', '').strip())
        self.table.setRowCount(0)
        for c in customers:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(c.get('customer_code', '') or ''))
            self.table.setItem(row, 1, QTableWidgetItem(c.get('full_name', '') or ''))
            self.table.setItem(row, 2, QTableWidgetItem(c.get('phone', '') or '-'))
            self.table.setItem(row, 3, QTableWidgetItem(c.get('national_id', '') or '-'))
            self.table.item(row, 0).setData(Qt.UserRole, c.get('id'))

    def _filter(self, text):
        text = text.strip().lower()
        for row in range(self.table.rowCount()):
            name = self.table.item(row, 1).text().lower()
            phone = self.table.item(row, 2).text().lower()
            self.table.setRowHidden(row, bool(text) and text not in name and text not in phone)

    def _on_select(self):
        row = self.table.currentRow()
        if row < 0:
            return
        item = self.table.item(row, 0)
        if item:
            self.selected_customer_id = item.data(Qt.UserRole)
            self.accept()
