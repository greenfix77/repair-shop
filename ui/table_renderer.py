from PyQt5.QtWidgets import QTableWidgetItem, QWidget, QHBoxLayout, QPushButton, QTableWidget
from PyQt5.QtGui import QColor, QFont
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


def create_action_buttons(row_index: int, view_callback, invoice_callback) -> QWidget:
    """Create action buttons widget"""
    actions_widget = QWidget()
    actions_layout = QHBoxLayout()
    actions_layout.setContentsMargins(5, 2, 5, 2)
    
    # View button
    view_btn = QPushButton("👁️")
    view_btn.setFixedSize(30, 25)
    view_btn.setStyleSheet("background-color: #2196F3; color: white;")
    view_btn.clicked.connect(lambda checked, r=row_index: view_callback(r))
    actions_layout.addWidget(view_btn)
    
    # Invoice button
    invoice_btn = QPushButton("📄")
    invoice_btn.setFixedSize(30, 25)
    invoice_btn.setStyleSheet("background-color: #FF9800; color: white;")
    invoice_btn.clicked.connect(lambda checked, r=row_index: invoice_callback(r))
    actions_layout.addWidget(invoice_btn)
    
    actions_widget.setLayout(actions_layout)
    return actions_widget


def render_single_row(table_widget: QTableWidget, row: int, row_data: Dict):
    """Render a single row of data"""
    # Set basic items
    table_widget.setItem(row, 0, create_table_item(row_data['id']))
    table_widget.setItem(row, 1, create_table_item(row_data['customer_name']))
    table_widget.setItem(row, 2, create_table_item(row_data['phone']))
    table_widget.setItem(row, 3, create_table_item(row_data['brand']))
    table_widget.setItem(row, 4, create_table_item(row_data['model']))
    table_widget.setItem(row, 5, create_table_item(row_data['issue']))
    
    # Set status item with styling
    status_item = create_table_item(row_data['status'])
    set_status_styling(status_item, row_data['status'])
    table_widget.setItem(row, 6, status_item)
    
    table_widget.setItem(row, 7, create_table_item(row_data['receive_date']))
    table_widget.setItem(row, 8, create_table_item(row_data['delivery_date']))
    
    # Set total cost item with styling
    total_item = create_table_item(row_data['total_cost'])
    set_total_styling(total_item)
    table_widget.setItem(row, 9, total_item)


def render_table_rows(table_widget: QTableWidget, rows_data: List[Dict], view_callback, invoice_callback):
    """Render all rows in the table"""
    table_widget.setRowCount(0)
    
    for row_idx, row_data in enumerate(rows_data):
        row = table_widget.rowCount()
        table_widget.insertRow(row)
        
        render_single_row(table_widget, row, row_data)
        
        # Create and set action buttons
        actions_widget = create_action_buttons(row_idx, view_callback, invoice_callback)
        table_widget.setCellWidget(row, 10, actions_widget)