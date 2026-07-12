from typing import List, Dict, Callable

from PyQt5.QtWidgets import (QTableWidget, QTableWidgetItem, QWidget,
                              QHBoxLayout, QPushButton, QHeaderView,
                              QAbstractItemView, QFrame)
from PyQt5.QtCore import Qt


CUSTOMER_COLUMNS = [
    "", "کد مشتری", "نام مشتری", "تلفن",
    "تعداد کل سفارشات", "تحویل شده", "در دست انجام",
    "ایمیل", "شهر", "تاریخ ایجاد", "ویرایش",
]


def build_customer_toolbar(window):
    """ایجاد نوار ابزار مدیریت مشتریان"""
    toolbar = QFrame()
    toolbar.setStyleSheet("background-color: white; border-radius: 5px; padding: 10px;")

    layout = QHBoxLayout()

    add_btn = QPushButton("➕ افزودن مشتری")
    add_btn.setStyleSheet("background-color: #4CAF50; color: white;")
    add_btn.clicked.connect(window.add_customer)
    layout.addWidget(add_btn)

    delete_btn = QPushButton("🗑️ حذف انتخاب‌شده‌ها")
    delete_btn.setStyleSheet("background-color: #f44336; color: white;")
    delete_btn.clicked.connect(window.delete_selected_customers)
    layout.addWidget(delete_btn)

    layout.addStretch()

    toolbar.setLayout(layout)
    return toolbar


def build_customer_table(window):
    """ایجاد جدول مشتریان"""
    table = QTableWidget()
    table.setColumnCount(len(CUSTOMER_COLUMNS))
    table.setHorizontalHeaderLabels(CUSTOMER_COLUMNS)

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
    header.setSectionResizeMode(8, QHeaderView.ResizeToContents)
    header.setSectionResizeMode(9, QHeaderView.ResizeToContents)
    header.setSectionResizeMode(10, QHeaderView.ResizeToContents)

    select_all_item = QTableWidgetItem("")
    select_all_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
    select_all_item.setCheckState(Qt.Unchecked)
    table.setHorizontalHeaderItem(0, select_all_item)

    table.horizontalHeader().sectionClicked.connect(
        lambda logical: _on_header_clicked(table, logical)
    )
    table.itemChanged.connect(lambda item: _on_item_changed(table, item))

    return table


def render_customer_rows(table: QTableWidget, customers: List[Dict],
                         edit_callback: Callable, stats: Dict = None):
    """رندر کردن ردیف‌های مشتریان (مرتب بر اساس نام)"""
    table.blockSignals(True)
    table.setRowCount(0)

    sorted_customers = sorted(
        customers, key=lambda c: c.get('full_name', '').strip()
    )

    for c in sorted_customers:
        row = table.rowCount()
        table.insertRow(row)

        check_item = QTableWidgetItem("")
        check_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        check_item.setCheckState(Qt.Unchecked)
        check_item.setData(Qt.UserRole, c.get('id'))
        table.setItem(row, 0, check_item)

        table.setItem(row, 1, QTableWidgetItem(c.get('customer_code', '') or ''))
        table.setItem(row, 2, QTableWidgetItem(c.get('full_name', '') or ''))
        table.setItem(row, 3, QTableWidgetItem(c.get('phone', '') or ''))

        cid = c.get('id')
        entry = (stats or {}).get(cid) if cid is not None else None
        total = str(entry['total']) if entry else '0'
        delivered = str(entry['delivered']) if entry else '0'
        in_progress = str(entry['in_progress']) if entry else '0'

        total_item = QTableWidgetItem(total)
        total_item.setTextAlignment(Qt.AlignCenter)
        table.setItem(row, 4, total_item)

        delivered_item = QTableWidgetItem(delivered)
        delivered_item.setTextAlignment(Qt.AlignCenter)
        table.setItem(row, 5, delivered_item)

        in_progress_item = QTableWidgetItem(in_progress)
        in_progress_item.setTextAlignment(Qt.AlignCenter)
        table.setItem(row, 6, in_progress_item)

        table.setItem(row, 7, QTableWidgetItem(c.get('email', '') or ''))
        table.setItem(row, 8, QTableWidgetItem(c.get('city', '') or ''))
        table.setItem(row, 9, QTableWidgetItem(c.get('created_at', '') or ''))

        edit_btn = QPushButton("ویرایش")
        edit_btn.setMinimumWidth(75)
        edit_btn.setStyleSheet("background-color: #2196F3; color: white;")
        customer_id = c.get('id')
        edit_btn.clicked.connect(
            lambda checked, cid=customer_id: edit_callback(cid)
        )
        edit_widget = QWidget()
        edit_layout = QHBoxLayout()
        edit_layout.setContentsMargins(5, 2, 5, 2)
        edit_layout.addWidget(edit_btn)
        edit_widget.setLayout(edit_layout)
        table.setCellWidget(row, 10, edit_widget)

    header_item = table.horizontalHeaderItem(0)
    if header_item is not None:
        header_item.setCheckState(Qt.Unchecked)

    table.blockSignals(False)


def _on_header_clicked(table: QTableWidget, logical_index: int):
    """تغییر وضعیت همه چک‌باکس‌ها با کلیک روی هدر"""
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
    """به‌روزرسانی وضعیت چک‌باکس هدر بر اساس ردیف‌ها"""
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
