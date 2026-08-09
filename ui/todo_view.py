from typing import List, Dict, Callable

from PyQt5.QtWidgets import (QTableWidget, QTableWidgetItem, QWidget,
                               QHBoxLayout, QPushButton, QHeaderView,
                               QAbstractItemView, QFrame, QLineEdit, QLabel)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont


TODO_COLUMNS = [
    "", "شناسه", "عنوان", "تاریخ سررسید",
    "اولویت", "وضعیت", "تاریخ ایجاد", "عملیات",
]

PRIORITY_COLORS = {
    "فوری": "#DC2626",
    "زیاد": "#D97706",
    "معمولی": "#2563EB",
    "کم": "#6B7280",
}


def build_todo_toolbar(window):
    toolbar = QFrame()
    toolbar.setStyleSheet("background-color: white; border-radius: 5px; padding: 10px;")

    layout = QHBoxLayout()

    add_btn = QPushButton("➕ افزودن وظیفه")
    add_btn.setStyleSheet("background-color: #4CAF50; color: white;")
    add_btn.clicked.connect(window.add_todo)
    layout.addWidget(add_btn)

    delete_btn = QPushButton("🗑️ حذف انتخاب‌شده‌ها")
    delete_btn.setStyleSheet("background-color: #f44336; color: white;")
    delete_btn.clicked.connect(window.delete_selected_todos)
    layout.addWidget(delete_btn)

    toggle_btn = QPushButton("🔄 انجام شد / بازگردانی")
    toggle_btn.setStyleSheet("background-color: #FF9800; color: white;")
    toggle_btn.clicked.connect(window.toggle_selected_todo_done)
    layout.addWidget(toggle_btn)

    layout.addStretch()

    search_label = QLabel("🔍 جستجو:")
    layout.addWidget(search_label)

    window.todo_search_input = QLineEdit()
    window.todo_search_input.setPlaceholderText("عنوان یا توضیحات...")
    window.todo_search_input.setMinimumWidth(200)
    window.todo_search_input.textChanged.connect(window.search_todos)
    layout.addWidget(window.todo_search_input)

    toolbar.setLayout(layout)
    return toolbar


def build_todo_table(window):
    table = QTableWidget()
    table.setColumnCount(len(TODO_COLUMNS))
    table.setHorizontalHeaderLabels(TODO_COLUMNS)

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


def render_todo_rows(table: QTableWidget, todos: List[Dict],
                     edit_callback: Callable):
    table.blockSignals(True)
    table.setRowCount(0)

    sorted_todos = sorted(
        todos, key=lambda t: (t.get('is_done', False), t.get('title', '').strip())
    )

    done_color = QColor(180, 180, 180)

    for t in sorted_todos:
        row = table.rowCount()
        table.insertRow(row)

        check_item = QTableWidgetItem("")
        check_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        check_item.setCheckState(Qt.Unchecked)
        check_item.setData(Qt.UserRole, t.get('id'))
        table.setItem(row, 0, check_item)

        id_item = QTableWidgetItem(str(t.get('id', '')))
        table.setItem(row, 1, id_item)

        title_item = QTableWidgetItem(t.get('title', '') or '')
        table.setItem(row, 2, title_item)

        due_item = QTableWidgetItem(t.get('due_date', '') or '')
        due_item.setTextAlignment(Qt.AlignCenter)
        table.setItem(row, 3, due_item)

        priority = t.get('priority', 'معمولی')
        priority_item = QTableWidgetItem(priority)
        priority_item.setTextAlignment(Qt.AlignCenter)
        priority_color = PRIORITY_COLORS.get(priority, "#6B7280")
        priority_item.setForeground(QColor(priority_color))
        table.setItem(row, 4, priority_item)

        is_done = t.get('is_done', False)
        status_text = "✓ انجام شده" if is_done else "○ در انتظار"
        status_item = QTableWidgetItem(status_text)
        status_item.setTextAlignment(Qt.AlignCenter)
        if is_done:
            status_item.setForeground(QColor("#059669"))
        else:
            status_item.setForeground(QColor("#D97706"))
        table.setItem(row, 5, status_item)

        created_item = QTableWidgetItem(t.get('created_at', '') or '')
        table.setItem(row, 6, created_item)

        edit_btn = QPushButton("ویرایش")
        edit_btn.setMinimumWidth(75)
        edit_btn.setStyleSheet("background-color: #2196F3; color: white; padding: 3px 14px 5px 14px;")
        todo_id = t.get('id')
        edit_btn.clicked.connect(
            lambda checked, tid=todo_id: edit_callback(tid)
        )
        edit_widget = QWidget()
        edit_layout = QHBoxLayout()
        edit_layout.setContentsMargins(5, 2, 5, 2)
        edit_layout.addWidget(edit_btn)
        edit_widget.setLayout(edit_layout)
        table.setCellWidget(row, 7, edit_widget)

        if is_done:
            for col in range(table.columnCount()):
                item = table.item(row, col)
                if item is not None:
                    item.setForeground(done_color)
                    font = item.font()
                    font.setStrikeOut(True)
                    item.setFont(font)

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