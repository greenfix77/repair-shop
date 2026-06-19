# TABLE_RENDERER_PLAN

## 1. Exact UI Responsibilities Inside refresh_table

- Clearing and setting table row count
- Creating QTableWidgetItem objects
- Setting cell content and styling
- Creating action buttons with layouts
- Applying status-based colors
- Applying font styling
- Connecting button signals to slots
- Managing cell widgets

## 2. Functions That Can Be Extracted Safely

- create_table_item(text: str) -> QTableWidgetItem
- set_status_styling(item: QTableWidgetItem, status: str)
- set_total_styling(item: QTableWidgetItem)
- create_action_buttons(row_index: int, view_callback, invoice_callback) -> QWidget
- render_row_data(table_widget: QTableWidget, row: int, row_data: dict, row_index: int)

## 3. Dependencies Required by Renderer

- PyQt5.QtWidgets: QTableWidgetItem, QWidget, QHBoxLayout, QPushButton, QTableWidget
- PyQt5.QtGui: QColor, QFont
- Callback functions: view_repair, quick_invoice
- Table widget reference
- Row data structure from table_service

## 4. Proposed ui/table_renderer.py Structure

```python
from PyQt5.QtWidgets import QTableWidgetItem, QWidget, QHBoxLayout, QPushButton, QTableWidget
from PyQt5.QtGui import QColor, QFont
from typing import Dict

def create_table_item(text: str) -> QTableWidgetItem:
    """Create a styled table item"""

def set_status_styling(item: QTableWidgetItem, status: str):
    """Apply status-based styling to item"""

def set_total_styling(item: QTableWidgetItem):
    """Apply total cost styling to item"""

def create_action_buttons(row_index: int, view_callback, invoice_callback) -> QWidget:
    """Create action buttons widget"""

def render_row_data(table_widget: QTableWidget, row: int, row_data: Dict, row_index: int):
    """Render a single row of data"""

def render_table_rows(table_widget: QTableWidget, rows_data: list, view_callback, invoice_callback):
    """Render all rows in the table"""
```

## 5. Exact Extraction Order

1. Extract create_table_item function
2. Extract set_status_styling function
3. Extract set_total_styling function
4. Extract create_action_buttons function
5. Extract render_row_data function
6. Extract render_table_rows function
7. Simplify refresh_table to delegate to renderer

## 6. Risk Analysis

Low to Medium Risk:
- All UI operations remain in the renderer
- Same visual behavior maintained
- Only refactoring, no logic changes
- Callback connections preserved
- Existing signal-slot mechanisms maintained

## 7. Rollback Strategy

- Revert refresh_table to original implementation
- Remove ui/table_renderer.py module
- Restore all UI logic to refresh_table method
- Revert imports in app.py