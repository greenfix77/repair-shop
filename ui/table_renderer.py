from PyQt5.QtWidgets import QTableWidgetItem, QWidget, QHBoxLayout, QPushButton, QTableWidget
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtCore import Qt
from typing import Dict, List

from core.status import STATUS_BG_COLORS, STATUS_FG_COLORS


def create_table_item(text: str) -> QTableWidgetItem:
    """Create a styled table item"""
    return QTableWidgetItem(text)


def set_status_styling(item: QTableWidgetItem, status: str):
    """Apply status-based styling to item"""
    bg = STATUS_BG_COLORS.get(status)
    fg = STATUS_FG_COLORS.get(status)
    if bg and fg:
        item.setBackground(QColor(bg))
        item.setForeground(QColor(fg))


def set_total_styling(item: QTableWidgetItem):
    """Apply total cost styling to item"""
    item.setForeground(QColor("#4CAF50"))
    item.setFont(QFont("Segoe UI", 10, QFont.Bold))


def setup_selection_column(table: QTableWidget):
    """Set up checkbox selection column (column 0) with header select-all."""
    select_all_item = QTableWidgetItem("")
    select_all_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
    select_all_item.setCheckState(Qt.Unchecked)
    table.setHorizontalHeaderItem(0, select_all_item)

    table.horizontalHeader().sectionClicked.connect(
        lambda logical: _on_header_clicked(table, logical)
    )
    table.itemChanged.connect(lambda item: _on_item_changed(table, item))


def create_action_buttons(row_index: int, edit_callback) -> QWidget:
    """Create action buttons widget"""
    actions_widget = QWidget()
    actions_layout = QHBoxLayout()
    actions_layout.setContentsMargins(5, 2, 5, 2)
    
    # Edit button
    edit_btn = QPushButton("ویرایش")
    edit_btn.setFixedHeight(30)
    edit_btn.setStyleSheet(
        "background-color: #2196F3; color: white; "
        "border-radius: 4px; padding: 3px 14px 5px 14px;"
    )
    edit_btn.clicked.connect(
        lambda checked, r=row_index: edit_callback(r)
    )
    actions_layout.addWidget(edit_btn)
    
    actions_widget.setLayout(actions_layout)
    return actions_widget


def render_single_row(table_widget: QTableWidget, row: int, row_data: Dict):
    """Render a single row of data (columns shifted +1 for checkbox column)"""
    # Set basic items
    table_widget.setItem(row, 1, create_table_item(row_data['id']))
    table_widget.setItem(row, 2, create_table_item(row_data['customer_name']))
    table_widget.setItem(row, 3, create_table_item(row_data['phone']))
    table_widget.setItem(row, 4, create_table_item(row_data['brand']))
    table_widget.setItem(row, 5, create_table_item(row_data['model']))
    table_widget.setItem(row, 6, create_table_item(row_data['issue']))
    
    # Set status item with styling
    status_item = create_table_item(row_data['status'])
    set_status_styling(status_item, row_data['status'])
    table_widget.setItem(row, 7, status_item)
    
    table_widget.setItem(row, 8, create_table_item(row_data['receive_date']))
    table_widget.setItem(row, 9, create_table_item(row_data['delivery_date']))
    
    # Set total cost item with styling
    total_item = create_table_item(row_data['total_cost'])
    set_total_styling(total_item)
    table_widget.setItem(row, 10, total_item)


def render_table_rows(table_widget: QTableWidget, rows_data: List[Dict], edit_callback):
    """Render all rows in the table"""
    table_widget.blockSignals(True)
    table_widget.setRowCount(0)
    
    for row_idx, row_data in enumerate(rows_data):
        row = table_widget.rowCount()
        table_widget.insertRow(row)
        
        # Checkbox column (column 0)
        check_item = QTableWidgetItem("")
        check_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        check_item.setCheckState(Qt.Unchecked)
        check_item.setData(Qt.UserRole, int(row_data['id']))
        table_widget.setItem(row, 0, check_item)
        
        render_single_row(table_widget, row, row_data)
        
        # Create and set action buttons (column 11)
        actions_widget = create_action_buttons(row_idx, edit_callback)
        table_widget.setCellWidget(row, 11, actions_widget)

    # Reset header checkbox to unchecked after refresh
    header_item = table_widget.horizontalHeaderItem(0)
    if header_item is not None:
        header_item.setCheckState(Qt.Unchecked)

    table_widget.blockSignals(False)


def _on_header_clicked(table: QTableWidget, logical_index: int):
    """Toggle all row checkboxes via header click"""
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
    """Sync header checkbox state based on row checkboxes"""
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