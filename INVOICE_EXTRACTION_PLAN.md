# INVOICE EXTRACTION PLAN

## 1. All methods inside InvoicePreviewDialog
- __init__ (lines 21-30)
- init_ui (lines 31-81)
- generate_print_invoice (lines 86-310)
- generate_web_invoice (lines 319-619)
- print_invoice (lines 621-627)
- save_pdf (lines 629-641)
- update_preview (lines 643-652)

## 2. Line count of each method
- __init__: 10 lines
- init_ui: 51 lines
- generate_print_invoice: 225 lines
- generate_web_invoice: 301 lines
- print_invoice: 7 lines
- save_pdf: 13 lines
- update_preview: 10 lines

## 3. Pure calculation logic
- Financial calculations inside generate_print_invoice and generate_web_invoice:
  - parts_cost + labor_cost = subtotal
  - subtotal * (tax_rate / 100) = tax_amount
  - subtotal + tax_amount - discount = total

## 4. Pure HTML generation logic
- generate_print_invoice: Creates HTML string for print invoice
- generate_web_invoice: Creates HTML string for web invoice with extensive CSS styling

## 5. Pure PDF/Print logic
- print_invoice: Handles printing via QPrinter
- save_pdf: Handles PDF saving via QPrinter.PdfFormat

## 6. UI-only logic
- init_ui: Creates UI elements for invoice preview dialog
- update_preview: Updates the QTextEdit preview widget

## 7. Reusable invoice functions
- Financial calculation algorithms (can be reused across invoice types)
- HTML template generation (separable from UI context)
- Print/PDF export functionality (reusable for other documents)

## 8. Dependencies used by each method
- __init__: ShopSettingsDialog.get_settings(), repair_data
- init_ui: PyQt5 UI components
- generate_print_invoice: repair_data, shop_settings, jdatetime
- generate_web_invoice: repair_data, shop_settings, jdatetime, Path
- print_invoice: QPrinter, QPrintDialog, QTextEdit.preview
- save_pdf: QPrinter, QFileDialog, QTextEdit.preview, QMessageBox
- update_preview: QTextEdit.preview, generate_*_invoice methods

## 9. Safe extraction order
1. Extract financial calculations to services/invoice_calculator.py
2. Extract HTML generation to services/invoice_generator.py
3. Extract PDF/print logic to services/invoice_exporter.py
4. Update InvoicePreviewDialog to use these services

## 10. Proposed structure:

services/
  invoice_calculator.py
    - calculate_invoice_totals(repair_data) -> dict
  invoice_generator.py
    - generate_print_invoice_html(repair_data, settings) -> str
    - generate_web_invoice_html(repair_data, settings) -> str
  invoice_exporter.py
    - print_invoice(html_content)
    - save_invoice_as_pdf(html_content, file_path) -> bool