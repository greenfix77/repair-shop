from typing import List, Dict, Callable

from PyQt5.QtWidgets import (QTableWidget, QTableWidgetItem, QWidget,
                              QHBoxLayout, QPushButton, QHeaderView,
                              QAbstractItemView, QFrame, QLineEdit, QLabel)
from PyQt5.QtCore import Qt


SERVICE_COLUMNS = [
    "", "کد خدمت", "نام خدمت", "قیمت پیش‌فرض",
    "توضیحات", "فعال", "ویرایش",
]


def build_service_toolbar(window):
    """ایجاد نوار ابزار مدیریت خدمات"""
    toolbar = QFrame()
    toolbar.setStyleSheet("background-color: white; border-radius: 5px; padding: 10px;")

    layout = QHBoxLayout()

    add_btn = QPushButton("➕ افزودن خدمت")
    add_btn.setStyleSheet("background-color: #4CAF50; color: white;")
    add_btn.clicked.connect(window.add_service)
    layout.addWidget(add_btn)

    delete_btn = QPushButton("🗑️ حذف انتخاب‌شده‌ها")
    delete_btn.setStyleSheet("background-color: #f44336; color: white;")
    delete_btn.clicked.connect(window.delete_selected_services)
    layout.addWidget(delete_btn)

    layout.addStretch()

    search_label = QLabel("🔍 جستجو:")
    layout.addWidget(search_label)

    window.service_search_input = QLineEdit()
    window.service_search_input.setPlaceholderText("نام یا کد خدمت...")
    window.service_search_input.setMinimumWidth(200)
    window.service_search_input.textChanged.connect(window.search_services)
    layout.addWidget(window.service_search_input)

    toolbar.setLayout(layout)
    return toolbar


def build_service_table(window):
    """ایجاد جدول خدمات"""
    table = QTableWidget()
    table.setColumnCount(len(SERVICE_COLUMNS))
    table.setHorizontalHeaderLabels(SERVICE_COLUMNS)

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
    header.setSectionResizeMode(4, QHeaderView.Stretch)
    header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
    header.setSectionResizeMode(6, QHeaderView.ResizeToContents)

    select_all_item = QTableWidgetItem("")
    select_all_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
    select_all_item.setCheckState(Qt.Unchecked)
    table.setHorizontalHeaderItem(0, select_all_item)

    table.horizontalHeader().sectionClicked.connect(
        lambda logical: _on_header_clicked(table, logical)
    )
    table.itemChanged.connect(lambda item: _on_item_changed(table, item))

    return table


def render_service_rows(table: QTableWidget, services: List[Dict],
                        edit_callback: Callable):
    """رندر کردن ردیف‌های خدمات (مرتب بر اساس نام)"""
    table.blockSignals(True)
    table.setRowCount(0)

    sorted_services = sorted(
        services, key=lambda s: s.get('name', '').strip()
    )

    for s in sorted_services:
        row = table.rowCount()
        table.insertRow(row)

        check_item = QTableWidgetItem("")
        check_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        check_item.setCheckState(Qt.Unchecked)
        check_item.setData(Qt.UserRole, s.get('id'))
        table.setItem(row, 0, check_item)

        table.setItem(row, 1, QTableWidgetItem(s.get('service_code', '') or ''))
        table.setItem(row, 2, QTableWidgetItem(s.get('name', '') or ''))
        table.setItem(row, 3, QTableWidgetItem(f"{s.get('default_price', 0):,}"))
        table.setItem(row, 4, QTableWidgetItem(s.get('description', '') or ''))

        active_item = QTableWidgetItem("✓" if s.get('is_active') else "✗")
        active_item.setTextAlignment(Qt.AlignCenter)
        table.setItem(row, 5, active_item)

        edit_btn = QPushButton("ویرایش")
        edit_btn.setMinimumWidth(75)
        edit_btn.setStyleSheet("background-color: #2196F3; color: white; padding: 3px 14px 5px 14px;")
        service_id = s.get('id')
        edit_btn.clicked.connect(
            lambda checked, sid=service_id: edit_callback(sid)
        )
        edit_widget = QWidget()
        edit_layout = QHBoxLayout()
        edit_layout.setContentsMargins(5, 2, 5, 2)
        edit_layout.addWidget(edit_btn)
        edit_widget.setLayout(edit_layout)
        table.setCellWidget(row, 6, edit_widget)

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
