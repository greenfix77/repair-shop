# TABLE DECOMPOSITION PLAN

## refresh_table Analysis

### Current Method Overview
The refresh_table method handles multiple responsibilities:
- Clears and rebuilds the table
- Formats repair data for display
- Calculates financial totals
- Sets UI styling
- Updates statistics

### 1. Data Extraction Logic
- Iterates through self.repairs
- Extracts individual repair fields (id, customer_name, phone, brand, model, issue, status, dates, costs)

### 2. Transformation Logic
- Converts repair data to table row format
- Truncates long text (issue field > 30 chars)
- Calculates financial totals per row:
  - subtotal = parts + labor
  - tax_amount = subtotal * (tax / 100)
  - total = subtotal + tax_amount - discount

### 3. UI Rendering Logic
- table.setRowCount(0)
- table.insertRow(row)
- table.setItem(row, col, QTableWidgetItem)
- table.setCellWidget(row, col, actions_widget)
- table.setRowHidden(row, bool)

### 4. Formatting Logic
- Sets colors based on status (background/foreground)
- Formats currency with commas
- Sets fonts and styles
- Creates action buttons (view, invoice)

### 5. Dependency Map
- Depends on: self.repairs (data source)
- Calls: update_statistics() (after processing)
- Uses: PersianDateEdit, QColor, QFont, QPushButton

### 6. Hidden Business Logic
- Financial calculation algorithm
- Status-based coloring scheme
- Text truncation rule (>30 chars)
- Action button creation

## Variable Analysis

### Input Variables
- self.repairs (list of repair dictionaries)
- self.table (QTableWidget reference)

### Computed Variables
- row (current table row index)
- repair (individual repair data)
- parts, labor, tax, discount (cost components)
- subtotal, tax_amount, total (calculated amounts)
- issue (potentially truncated)
- status (for coloring)

### UI Variables
- QTableWidgetItem instances
- QWidget for action buttons
- QHBoxLayout for button layout
- QPushButton instances

## UI Calls (Qt Methods)
- table.setRowCount()
- table.insertRow()
- table.setItem()
- table.setCellWidget()
- table.setRowHidden()
- QTableWidgetItem.setForeground()
- QTableWidgetItem.setBackground()
- QTableWidgetItem.setFont()
- QTableWidgetItem.setText()

## Calculations
- subtotal = parts + labor
- tax_amount = subtotal * (tax / 100)
- total = subtotal + tax_amount - discount
- total formatting with commas (int(total):,)

## Coupling Points
- update_statistics() call at end
- Financial calculation logic duplicated from other parts
- Status coloring scheme (shared with other UI elements)

## Proposed Decomposition

### New Module: services/table_data_processor.py
- transform_repairs_for_table(repairs: list) -> list[dict]
- calculate_repair_totals(repair: dict) -> dict

### New Module: ui/table_renderer.py
- render_table_rows(table_widget: QTableWidget, row_data: list[dict])
- format_currency(amount: float) -> str
- set_status_styling(item: QTableWidgetItem, status: str)

### New Module: services/data_formatter.py
- format_repair_for_display(repair: dict) -> dict
- truncate_text(text: str, max_length: int) -> str

## Safe Extraction Order
1. Extract financial calculations to services/table_data_processor.py
2. Extract data transformation to services/table_data_processor.py
3. Extract UI rendering to ui/table_renderer.py
4. Extract formatting to services/data_formatter.py
5. Update refresh_table to orchestrate the new services