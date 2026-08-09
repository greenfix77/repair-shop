from typing import List, Dict, Callable

from PyQt5.QtWidgets import (QTableWidget, QTableWidgetItem, QWidget,
                              QHBoxLayout, QPushButton, QHeaderView,
                              QAbstractItemView, QFrame, QLineEdit, QLabel)
from PyQt5.QtCore import Qt


PART_COLUMNS = [
    "", "کد قطعه", "نام قطعه", "قیمت خرید",
    "قیمت فروش", "موجودی", "تاریخ ایجاد", "ویرایش",
]


def build_part_toolbar(window):
    """ایجاد نوار ابزار مدیریت قطعات"""
    toolbar = QFrame()
    toolbar.setStyleSheet("background-color: white; border-radius: 5px; padding: 10px;")

    layout = QHBoxLayout()

    add_btn = QPushButton("➕ افزودن قطعه")
    add_btn.setStyleSheet("background-color: #4CAF50; color: white;")
    add_btn.clicked.connect(window.add_part)
    layout.addWidget(add_btn)

    delete_btn = QPushButton("🗑️ حذف انتخاب‌شده‌ها")
    delete_btn.setStyleSheet("background-color: #f44336; color: white;")
    delete_btn.clicked.connect(window.delete_selected_parts)
    layout.addWidget(delete_btn)

    layout.addStretch()

    search_label = QLabel("🔍 جستجو:")
    layout.addWidget(search_label)

    window.part_search_input = QLineEdit()
    window.part_search_input.setPlaceholderText("نام یا کد قطعه...")
    window.part_search_input.setMinimumWidth(200)
    window.part_search_input.textChanged.connect(window.search_parts)
    layout.addWidget(window.part_search_input)

    toolbar.setLayout(layout)
    return toolbar


def build_part_table(window):
    """ایجاد جدول قطعات"""
    table = QTableWidget()
    table.setColumnCount(len(PART_COLUMNS))
    table.setHorizontalHeaderLabels(PART_COLUMNS)

    table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectRows)
    table.setSelectionMode(QAbstractItemView.SingleSelection)
    table.setAlternatingRowColors(True)
    table.verticalHeader().setVisible(False)

    header = table.horizontalHeader()
    header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
    header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
    header.setSectionResizeMode(2, QHeaderView.Stretch)
    header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
    header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
    header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
    header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
    header.setSectionResizeMode(7, QHeaderView.ResizeToContents)

    select_all_item = QTableWidgetItem("")
    select_all_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
    select_all_item.setCheckState(Qt.Unchecked)
    table.setHorizontalHeaderItem(0, select_all_item)

    table.horizontalHeader().sectionClicked.connect(
        lambda logical: _on_header_clicked(table, logical)
    )
    table.itemChanged.connect(lambda item: _on_item_changed(table, item))

    return table


def render_part_rows(table: QTableWidget, parts: List[Dict],
                    edit_callback: Callable):
    """رندر کردن ردیف‌های قطعات (مرتب بر اساس نام)"""
    table.blockSignals(True)
    table.setRowCount(0)

    sorted_parts = sorted(
        parts, key=lambda p: p.get('name', '').strip()
    )

    for p in sorted_parts:
        row = table.rowCount()
        table.insertRow(row)

        check_item = QTableWidgetItem("")
        check_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        check_item.setCheckState(Qt.Unchecked)
        check_item.setData(Qt.UserRole, p.get('id'))
        table.setItem(row, 0, check_item)

        table.setItem(row, 1, QTableWidgetItem(p.get('part_code', '') or ''))
        table.setItem(row, 2, QTableWidgetItem(p.get('name', '') or ''))
        table.setItem(row, 3, QTableWidgetItem(f"{p.get('purchase_price', 0):,}"))
        table.setItem(row, 4, QTableWidgetItem(f"{p.get('sale_price', 0):,}"))

        stock = p.get('stock_quantity', 0)
        stock_item = QTableWidgetItem(str(stock))
        if stock <= 0:
            stock_item.setForeground(Qt.red)
        table.setItem(row, 5, stock_item)

        table.setItem(row, 6, QTableWidgetItem(p.get('created_at', '') or ''))

        edit_btn = QPushButton("ویرایش")
        edit_btn.setMinimumWidth(75)
        edit_btn.setStyleSheet("background-color: #2196F3; color: white; padding: 3px 14px 5px 14px;")
        part_id = p.get('id')
        edit_btn.clicked.connect(
            lambda checked, pid=part_id: edit_callback(pid)
        )
        edit_widget = QWidget()
        edit_layout = QHBoxLayout()
        edit_layout.setContentsMargins(5, 2, 5, 2)
        edit_layout.addWidget(edit_btn)
        edit_widget.setLayout(edit_layout)
        table.setCellWidget(row, 7, edit_widget)

    header_item = table.horizontalHeaderItem(0)
    if header_item is not None:
        header_item.setCheckState(Qt.Unchecked)

    table.blockSignals(False)


def _on_header_clicked(table: QTableWidget, logical_index: int):
    if logical_index != 0:
        return
    header_item = table.horizontalHeaderItem(0)
    if header_item is None:
        return
    new_state = Qt.Unchecked if header_item.checkState() == Qt.Checked else Qt.Checked
    table.blockSignals(True)
    header_item.setCheckState(new_state)
    for row in range(table.rowCount()):
        item = table.item(row, 0)
        if item is not None:
            item.setCheckState(new_state)
    table.blockSignals(False)


def _on_item_changed(table: QTableWidget, item: QTableWidgetItem):
    if item.column() != 0:
        return
    _sync_header_state(table)


def _sync_header_state(table: QTableWidget):
    rows = table.rowCount()
    if rows == 0:
        return
    all_checked = all(
        table.item(r, 0) is not None
        and table.item(r, 0).checkState() == Qt.Checked
        for r in range(rows)
    )
    header_item = table.horizontalHeaderItem(0)
    if header_item is not None:
        table.blockSignals(True)
        header_item.setCheckState(Qt.Checked if all_checked else Qt.Unchecked)
        table.blockSignals(False)
