# FINAL INVOICE ARCHITECTURE

## 1. Current Flow Diagram
```
InvoicePreviewDialog.__init__ → init_ui → update_preview
                                    ↓
                            generate_print_invoice OR generate_web_invoice
                                    ↓
                            print_invoice OR save_pdf
```

## 2. Full Dependency Graph
```
InvoicePreviewDialog
├── ShopSettingsDialog.get_settings() (line 24)
├── init_ui()
│   ├── QTextEdit (line 58)
│   ├── QButtonGroup (line 40)
│   ├── QRadioButton (lines 41-42)
│   ├── QPushButton (lines 65-70)
│   └── Layout managers
├── generate_print_invoice()
│   ├── repair_data (line 88)
│   ├── shop_settings (line 89)
│   └── jdatetime (line 306)
├── generate_web_invoice()
│   ├── repair_data (line 319)
│   ├── shop_settings (line 320)
│   ├── Path (line 353)
│   └── jdatetime (line 1127)
├── print_invoice()
│   ├── QPrinter (line 622)
│   ├── QPrintDialog (line 623)
│   └── QTextEdit.preview (line 626)
└── save_pdf()
    ├── QPrinter (line 632)
    ├── QFileDialog (line 633)
    └── QMessageBox (line 640)
```

## 3. Separation of Concerns Violations
- Lines 86-310: generate_print_invoice mixes financial calculations with HTML generation
- Lines 319-619: generate_web_invoice mixes financial calculations with HTML generation
- Lines 621-627: print_invoice mixes UI logic with printing side effects
- Lines 629-641: save_pdf mixes UI logic with file operations

## 4. HTML Generation Breakdown
- generate_print_invoice: Lines 100-309 (HTML template with CSS)
- generate_web_invoice: Lines 343-1128 (HTML template with extensive CSS)

## 5. Financial Calculation Breakdown
- generate_print_invoice: Lines 92-98 (subtotal, tax, total calculations)
- generate_web_invoice: Lines 323-329 (same calculations as above)

## 6. Print/PDF Side-Effect Analysis
- print_invoice: Creates QPrinter, shows QPrintDialog, executes print operation
- save_pdf: Creates QPrinter with PDF format, shows file dialog, saves file, shows confirmation

## 7. Pure vs Side-Effect Functions
Pure Functions:
- Financial calculations (subtotal, tax, total) - can be extracted

Side-Effect Functions:
- print_invoice (printing side effect)
- save_pdf (file writing side effect)
- init_ui (UI creation side effect)
- update_preview (widget update side effect)

## 8. Clean API Definition

Calculator Layer:
- calculate_invoice_totals(repair_data: dict) -> dict (returns subtotal, tax_amount, total)

Generator Layer:
- generate_print_invoice_html(repair_data: dict, settings: dict) -> str
- generate_web_invoice_html(repair_data: dict, settings: dict) -> str

Exporter Layer:
- print_invoice_content(html_content: str) -> None
- save_invoice_to_pdf(html_content: str, file_path: str) -> bool

## 9. Migration Strategy with Zero UI Break
Step 1: Create services/invoice_calculator.py with calculate_invoice_totals
Step 2: Create services/invoice_generator.py with HTML generation functions
Step 3: Create services/invoice_exporter.py with print/save functions
Step 4: Update InvoicePreviewDialog to use these services while maintaining same UI behavior
Step 5: Gradually replace internal methods with service calls

## 10. Risk Analysis for Extraction Order
Low Risk: Calculator extraction (pure functions, easy to test)
Medium Risk: Generator extraction (complex HTML templates, need careful verification)
High Risk: Exporter extraction (side effects, UI interactions, harder to test)
Recommended Order: Calculator → Generator → Exporter