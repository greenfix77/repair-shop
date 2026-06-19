# EXTRACTION CANDIDATES

## Analysis Table

| Component | Type | Difficulty | Dependencies | Coupling | Risk | Reusability | Priority | Target Module | Notes |
|-----------|------|------------|--------------|----------|------|-------------|----------|---------------|-------|
| PersianCalendarWidget | UI | Easy | 0 | 1 | Low | High | P0 | ui/widgets/persian_calendar.py | Self-contained, no external deps |
| PersianDateEdit | UI | Easy | 1 (PersianCalendarWidget) | 2 | Low | High | P0 | ui/widgets/persian_date_edit.py | Depends on PersianCalendarWidget |
| NotificationDialog | UI | Easy | 0 | 1 | Low | Medium | P0 | ui/dialogs/notification_dialog.py | Standalone notification UI |
| ShopSettingsDialog | UI | Easy | 0 | 2 | Low | Medium | P0 | ui/dialogs/shop_settings.py | Only file I/O dependencies |
| InvoicePreviewDialog | UI | Hard | 2 (ShopSettingsDialog, QTextEdit) | 5 | High | Low | P2 | ui/dialogs/invoice_preview.py | Complex HTML generation |
| RepairDialog | UI | Medium | 2 (PersianDateEdit, financial calc) | 4 | Medium | Low | P1 | ui/dialogs/repair_dialog.py | Financial calculations embedded |
| LaptopRepairManager | Core | Hard | 6+ (all dialogs, file ops) | 9 | Critical | Low | P3 | core/main_window.py | Central application logic |
| generate_print_invoice | Service | Hard | 2 (repair_data, settings) | 6 | Medium | Low | P2 | services/invoice_generator.py | Large HTML template |
| generate_web_invoice | Service | Hard | 2 (repair_data, settings) | 7 | High | Low | P2 | services/invoice_generator.py | Very large HTML template |
| calculate_total | Service | Medium | 4 (UI fields) | 3 | Low | Medium | P1 | services/calculations.py | Embedded in UI component |

## Analysis Summary

The safest extractions are the Persian date/time widgets (P0 priority) as they have no business logic dependencies. The dialogs can be extracted next (P0-P1) since they're mostly UI-focused. The core application logic (LaptopRepairManager) and invoice generation functions represent the highest risk extractions due to their complexity and coupling scores.