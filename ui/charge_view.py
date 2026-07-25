from typing import List, Dict, Callable

from PyQt5.QtWidgets import (QTableWidget, QTableWidgetItem, QWidget,
                              QHBoxLayout, QPushButton, QHeaderView,
                              QAbstractItemView, QFrame, QLineEdit, QLabel)
from PyQt5.QtCore import Qt


CHARGE_COLUMNS = [
    "", "شناسه", "نام هزینه", "دسته",
    "مبلغ پیش‌فرض", "فعال", "توضیحات", "ویرایش",
]


def build_charge_toolbar(window):
    """ایجاد نوار ابزار مدیریت هزینه‌ها"""
    toolbar = QFrame()
    toolbar.setStyleSheet("background-color: white; border-radius: 5px; padding: 10px;")

    layout = QHBoxLayout()

    add_btn = QPushButton("➕ افزودن هزینه")
    add_btn.setStyleSheet("background-color: #4CAF50; color: white;")
    add_btn.clicked.connect(window.add_charge)
    layout.addWidget(add_btn)

    delete_btn = QPushButton("🗑️ حذف انتخاب‌شده‌ها")
    delete_btn.setStyleSheet("background-color: #f44336; color: white;")
    delete_btn.clicked.connect(window.delete_selected_charges)
    layout.addWidget(delete_btn)

    refresh_btn = QPushButton("🔄 به‌روزرسانی")
    refresh_btn.setStyleSheet("background-color: #607D8B; color: white;")
    refresh_btn.clicked.connect(window.refresh_charge_table)
    layout.addWidget(refresh_btn)

    layout.addStretch()

    search_label = QLabel("🔍 جستجو:")
    layout.addWidget(search_label)

    window.charge_search_input = QLineEdit()
    window.charge_search_input.setPlaceholderText("نام یا دسته هزینه...")
    window.charge_search_input.setMinimumWidth(200)
    window.charge_search_input.textChanged.connect(window.search_charges)
    layout.addWidget(window.charge_search_input)

    toolbar.setLayout(layout)
    return toolbar


def build_charge_table(window):
    """ایجاد جدول هزینه‌ها"""
    table = QTableWidget()
    table.setColumnCount(len(CHARGE_COLUMNS))
    table.setHorizontalHeaderLabels(CHARGE_COLUMNS)

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
    header.setSectionResizeMode(6, QHeaderView.Stretch)
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


def render_charge_rows(table: QTableWidget, charges: List[Dict],
                       edit_callback: Callable):
    """رندر کردن ردیف‌های هزینه‌ها (مرتب بر اساس نام)"""
    table.blockSignals(True)
    table.setRowCount(0)

    sorted_charges = sorted(
        charges, key=lambda c: c.get('name', '').strip()
    )

    for c in sorted_charges:
        row = table.rowCount()
        table.insertRow(row)

        check_item = QTableWidgetItem("")
        check_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        check_item.setCheckState(Qt.Unchecked)
        check_item.setData(Qt.UserRole, c.get('id'))
        table.setItem(row, 0, check_item)

        table.setItem(row, 1, QTableWidgetItem(str(c.get('id', '') or '')))
        table.setItem(row, 2, QTableWidgetItem(c.get('name', '') or ''))
        table.setItem(row, 3, QTableWidgetItem(c.get('category', '') or ''))
        table.setItem(row, 4, QTableWidgetItem(f"{c.get('default_amount', 0):,}"))

        active_item = QTableWidgetItem("✓" if c.get('is_active') else "✗")
        active_item.setTextAlignment(Qt.AlignCenter)
        table.setItem(row, 5, active_item)

        table.setItem(row, 6, QTableWidgetItem(c.get('description', '') or ''))

        edit_btn = QPushButton("ویرایش")
        edit_btn.setMinimumWidth(75)
        edit_btn.setStyleSheet("background-color: #2196F3; color: white;")
        charge_id = c.get('id')
        edit_btn.clicked.connect(
            lambda checked, cid=charge_id: edit_callback(cid)
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
