# Graph Report - repair_manager  (2026-06-29)

## Corpus Check
- 69 files · ~44,976 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 612 nodes · 893 edges · 49 communities (40 shown, 9 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 38 edges (avg confidence: 0.61)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `d04ca09e`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Customer Database Layer|Customer Database Layer]]
- [[_COMMUNITY_Customer Service Operations|Customer Service Operations]]
- [[_COMMUNITY_Application Entry & UI Setup|Application Entry & UI Setup]]
- [[_COMMUNITY_Main Window & Repair Actions|Main Window & Repair Actions]]
- [[_COMMUNITY_Calendar & UI Components|Calendar & UI Components]]
- [[_COMMUNITY_Controller & Data Operations|Controller & Data Operations]]
- [[_COMMUNITY_Settings & Notification Dialogs|Settings & Notification Dialogs]]
- [[_COMMUNITY_Core Data Models|Core Data Models]]
- [[_COMMUNITY_OpenCode Configuration|OpenCode Configuration]]
- [[_COMMUNITY_Customer Workflow Audit|Customer Workflow Audit]]
- [[_COMMUNITY_Shop Branding & Logo|Shop Branding & Logo]]
- [[_COMMUNITY_SQLite Migration Audit|SQLite Migration Audit]]
- [[_COMMUNITY_Architecture Documentation|Architecture Documentation]]
- [[_COMMUNITY_Customer Workflow Refactor|Customer Workflow Refactor]]
- [[_COMMUNITY_Logo & Invoice Audit|Logo & Invoice Audit]]
- [[_COMMUNITY_OpenCode Plugin Config|OpenCode Plugin Config]]
- [[_COMMUNITY_Package Dependencies|Package Dependencies]]
- [[_COMMUNITY_Invoice Preview Migration|Invoice Preview Migration]]
- [[_COMMUNITY_Invoice Generator|Invoice Generator]]
- [[_COMMUNITY_Repair Dialog|Repair Dialog]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 47|Community 47]]
- [[_COMMUNITY_Community 48|Community 48]]

## God Nodes (most connected - your core abstractions)
1. `CustomerService` - 38 edges
2. `LaptopRepairManager` - 32 edges
3. `CustomerRepository` - 24 edges
4. `RepairDialog` - 24 edges
5. `ShopSettingsDialog` - 17 edges
6. `SQLiteStorage` - 16 edges
7. `make_callback()` - 16 edges
8. `PersianDateEdit` - 15 edges
9. `InvoicePreviewDialog` - 14 edges
10. `Customer Workflow Architecture Audit` - 13 edges

## Surprising Connections (you probably didn't know these)
- `NotificationDialog` --uses--> `MainController`  [INFERRED]
  app.py → controllers/main_controller.py
- `NotificationDialog` --uses--> `SQLiteStorage`  [INFERRED]
  app.py → core/storage/sqlite_storage.py
- `NotificationDialog` --uses--> `PersianCalendarWidget`  [INFERRED]
  app.py → repair_manager/ui/components.py
- `NotificationDialog` --uses--> `PersianDateEdit`  [INFERRED]
  app.py → repair_manager/ui/components.py
- `NotificationDialog` --uses--> `InvoicePreviewDialog`  [INFERRED]
  app.py → ui/dialogs/invoice_dialog.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Customer Management Workflow** — customer_workflow_audit_customer_service, customer_workflow_audit_customer_repository, customer_workflow_audit_customer_db_model, architecture_final_repair_dialog, resolve_customer_decision_tree_resolve_customer, customer_workflow_audit_validate_and_accept, customer_workflow_audit_get_or_create_customer, phone_normalization_audit_phone_normalization, customer_workflow_audit_duplicated_customer_logic, customer_workflow_refactor_centralized_operations [INFERRED 0.95]
- **Invoice Generation Pipeline** — architecture_final_invoice_preview_dialog, architecture_final_invoice_generator, shop_logo_audit_logo_service, qwebengine_migration_audit_qwebengine_view, invoice_blank_preview_audit_logo_base64_inflation, shop_logo_audit_chromium_file_url_block [INFERRED 0.95]
- **Storage Layer Architecture** — sqlite_migration_audit_dualstorage, sqlite_migration_audit_repairs_storage, sqlite_migration_audit_sqlite_storage, sqlite_only_audit_json_read_dependency, architecture_final_laptop_repair_manager [INFERRED 0.95]

## Communities (49 total, 9 thin omitted)

### Community 0 - "Customer Database Layer"
Cohesion: 0.08
Nodes (17): Base, CustomerDB, CustomerRepository, DualStorage, init_database(), migrate_json_to_sqlite(), RepairDB, Load all repairs from file (+9 more)

### Community 1 - "Customer Service Operations"
Cohesion: 0.07
Nodes (35): CustomerService, Find a single customer by phone., Search customers by full_name or phone (contains, case-insensitive)., Get a single customer by primary key., Update customer fields. Returns updated dict or None if not found., Return every customer as a list of dicts., Return the next customer_code in C000001, C000002, … format., Return existing customer by phone, or create a new one.          Validates pho (+27 more)

### Community 2 - "Application Entry & UI Setup"
Cohesion: 0.23
Nodes (9): today_persian(), calculate_invoice_totals(), Any, generate_print_invoice_html(), generate_web_invoice_html(), get_invoice_logo_html(), Calculate statistics for repairs, update_statistics() (+1 more)

### Community 3 - "Main Window & Repair Actions"
Cohesion: 0.12
Nodes (8): LaptopRepairManager, نمایش/پنهان کردن پاپ‌آپ وضعیت‌ها, بستن پاپ‌آپ هنگام کلیک خارج از آن یا ESC, بارگذاری داده‌ها از فایل, کلاس اصلی برنامه مدیریت تعمیرات, QMainWindow, get_repair_by_id(), Find and return a repair by its ID.

### Community 4 - "Calendar & UI Components"
Cohesion: 0.08
Nodes (12): QCalendarWidget, QLineEdit, QStyledItemDelegate, PersianCalendarWidget, PersianDateEdit, ویجت تقویم شمسی سفارشی, دریافت تاریخ شمسی انتخاب شده, ویجت ورودی تاریخ شمسی (+4 more)

### Community 5 - "Controller & Data Operations"
Cohesion: 0.10
Nodes (24): MainController, QTableWidget, filter_repairs(), Return matching repair indices, Return matching repair indices by status, search_repairs(), QTableWidgetItem, calculate_invoice() (+16 more)

### Community 6 - "Settings & Notification Dialogs"
Cohesion: 0.14
Nodes (8): QWidget, print_invoice_content(), InvoicePreviewDialog, به‌روزرسانی پیش‌نمایش فاکتور, دیالوگ پیش‌نمایش و چاپ فاکتور, دریافت تنظیمات فروشگاه, Invoice preview widget using QWebEngineView, WebInvoiceView

### Community 7 - "Core Data Models"
Cohesion: 0.23
Nodes (8): Any, Repair, add_repair(), delete_repair(), Delete a repair by ID from the repairs list., Update a repair by ID with new data., Add a new repair to the repairs list.     Assigns a unique ID to the new repair., update_repair()

### Community 8 - "OpenCode Configuration"
Cohesion: 0.22
Nodes (8): agent, build, plan, temperature, model, temperature, $schema, small_model

### Community 9 - "Customer Workflow Audit"
Cohesion: 0.29
Nodes (6): CustomerDB SQLAlchemy Model, CustomerRepository, CustomerService, get_or_create_customer() (Unused by UI), Phone Normalization (NULL vs Empty String for UNIQUE), resolve_customer() Decision Tree

### Community 10 - "Shop Branding & Logo"
Cohesion: 0.29
Nodes (7): Application Icon Usage, Shop Branding Asset, Header Logo Usage, Invoice Logo Usage, Shop Logo Image (logo.png), Logo Service (logo_service.py), Repair Shop

### Community 11 - "SQLite Migration Audit"
Cohesion: 0.50
Nodes (4): DualStorage, RepairsStorage (JSON), SQLiteStorage, JSON-Only Read Dependency

### Community 12 - "Architecture Documentation"
Cohesion: 1.00
Nodes (3): Four-Layer Architecture (UI/Controller/Service/Storage), LaptopRepairManager, MainController

### Community 13 - "Customer Workflow Refactor"
Cohesion: 0.67
Nodes (3): Duplicated Customer Lookup/Creation Logic, Centralized Customer Operations via resolve_customer(), Zero Data Loss Principle

### Community 14 - "Logo & Invoice Audit"
Cohesion: 0.67
Nodes (3): Logo Base64 HTML Inflation Problem, Chromium file:/// URL Security Block, LogoService

### Community 25 - "Community 25"
Cohesion: 0.06
Nodes (32): 10. RepairDialog — Customer-Related Methods Grouped by Responsibility, 11. Duplicated Logic Inventory, 12. Answers to the Six Questions, 1. Layered Architecture Overview, 2.1 All methods and their callers, 2. Complete Call Graph, 3. Workflow Trace: A — Phone Auto-fill, 4. Workflow Trace: B — Customer Completer (+24 more)

### Community 26 - "Community 26"
Cohesion: 0.07
Nodes (28): 1. Every Location Reading Repairs, 2. Every Location Writing Repairs, 3. & 4. Every Location Saving/Loading Data, 5. Current Storage Implementation, 6. DualStorage Usage Map, 7. Remaining Direct JSON Dependencies, 8. Risk Assessment for Removing RepairsStorage, Audit Metadata (+20 more)

### Community 27 - "Community 27"
Cohesion: 0.08
Nodes (23): 10. Status badge colors, 1. Async printToPdf breaks synchronous API, 3. Chromium `file:///` security policy, 4. Print dialog UX change, 5. Application size increase, 6. Startup time increase, 7. CSS rendering differences, 8. New dependency (+15 more)

### Community 28 - "Community 28"
Cohesion: 0.09
Nodes (22): ALWAYS, ANALYZE FIRST, BEFORE MODIFYING, Commit, Commit format, COMPILATION CHECK, CURRENT ROADMAP, DIRTY WORKTREE POLICY (+14 more)

### Community 29 - "Community 29"
Cohesion: 0.20
Nodes (15): main(), بازسازی هدر پس از تغییر تنظیمات, get_app_icon(), get_header_logo_pixmap(), load_logo_path(), _load_settings(), build_header(), build_status_bar() (+7 more)

### Community 30 - "Community 30"
Cohesion: 0.24
Nodes (7): ذخیره داده‌ها در فایل, save_invoice_to_pdf(), show_error(), show_info(), show_question(), show_warning(), بازگردانی تنظیمات پیش‌فرض ظاهری

### Community 31 - "Community 31"
Cohesion: 0.11
Nodes (17): app.py, Architecture Final, controllers/, core/, core/storage/, Existing dialogs, Existing services, Future extension points (+9 more)

### Community 32 - "Community 32"
Cohesion: 0.12
Nodes (16): 1. What happens when phone == ""?, 2. Can resolve_customer() call create_customer() with an empty phone?, 3. Under what exact conditions is Repository.create() executed?, 4. Why does SQLite receive phone="" instead of reusing an existing customer?, 5. Is duplicate detection skipped when phone is empty?, Answers, Combined Decision Flowchart, Entry (+8 more)

### Community 33 - "Community 33"
Cohesion: 0.12
Nodes (15): Current Architecture Status, Current Health Status, Current Next UI Tasks, Future Invoice Improvements, Future Roadmap, Git Status, Invoice Logo System, Invoice Preview Status (+7 more)

### Community 34 - "Community 34"
Cohesion: 0.12
Nodes (15): 1. PyQt5 Import Sources, 2. Duplicate Imports (⚠️ Warning), 3. QStyle — Correct Module, 4. QCompleter Setup, 5. Delegate, 6. Circular Import Check, 7. Runtime Import Error Check, Line 5 — `PyQt5.QtCore` (+7 more)

### Community 35 - "Community 35"
Cohesion: 0.21
Nodes (6): NotificationDialog, باز کردن تنظیمات فروشگاه, دیالوگ نمایش اعلان‌ها, QDialog, دیالوگ تنظیمات فروشگاه, ShopSettingsDialog

### Community 36 - "Community 36"
Cohesion: 0.15
Nodes (12): Customer Workflow Refactor, Duplicate A: Phone Lookup (3 → 1), Duplicate B: Customer Creation (2 → 1), Duplicate C: Phone Duplicate Detection (3 → 1), Duplicate D: Field Population (2 → 1), Duplicated Logic Removed, Files Created, Files Modified (+4 more)

### Community 37 - "Community 37"
Cohesion: 0.17
Nodes (11): Application Startup Flow, Data Files, InvoicePreviewDialog, Known Critical Methods, Laptop Repair Manager, LaptopRepairManager, Main Classes, NotificationDialog (+3 more)

### Community 38 - "Community 38"
Cohesion: 0.17
Nodes (11): 1. Where Logo Path Is Stored, 2. Whether Logo Path Is Loaded Correctly, 3. Whether Invoice HTML Uses the Logo, 4. Whether QWebEngineView Receives the Logo Image, 5. Whether Application Icon Is Connected to Shop Logo, 6. Whether Header Title Icon Is Connected to Shop Logo, 7. Missing Links Preventing Logo Display, `generate_print_invoice_html()` — Print invoice (+3 more)

### Community 39 - "Community 39"
Cohesion: 0.18
Nodes (10): 1. Essential project files, 2. Generated files (runtime data), 3. Cache files (regeneratable, safe to exclude), 4. Debug files, 5. Obsolete files, Backup checklist, Backup Report, Classification summary (+2 more)

### Community 40 - "Community 40"
Cohesion: 0.20
Nodes (9): Customer Decision Refactor, Files changed, Known limitation, New Decision Tree (after refactor), Old Decision Tree (before refactor), Verification, Weaknesses, What changed (+1 more)

### Community 41 - "Community 41"
Cohesion: 0.22
Nodes (8): Affected Files, Checks Performed, CSS anomalies found (not root cause), Invoice Blank Preview Audit, Recommended Minimal Fix, Risk Level, Root Cause, Why this causes a blank preview

### Community 42 - "Community 42"
Cohesion: 0.25
Nodes (7): `core/storage/customer_model_db.py`, `core/storage/customer_repository.py`, Phone Normalization Audit, What was NOT changed (as required), Where normalization is implemented, Why empty string caused UNIQUE failure, Why NULL solves it

### Community 43 - "Community 43"
Cohesion: 0.25
Nodes (7): 1. Which storage is used for `load_all()`, 2. Which storage is used for `save_all()`, 3. Whether JSON is still required, 4. Whether any code imports `RepairsStorage` directly, 5. Whether any code still depends on `repairs.json`, SQLite-Only Migration — Final Audit, Summary

### Community 44 - "Community 44"
Cohesion: 0.40
Nodes (4): Current Tasks, High Priority, Low Priority, Medium Priority

## Knowledge Gaps
- **224 isolated node(s):** `$schema`, `plugin`, `@opencode-ai/plugin`, `$schema`, `model` (+219 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **9 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `CustomerService` connect `Customer Service Operations` to `Customer Database Layer`, `Application Entry & UI Setup`, `Calendar & UI Components`?**
  _High betweenness centrality (0.072) - this node is a cross-community bridge._
- **Why does `RepairDialog` connect `Calendar & UI Components` to `Customer Service Operations`, `Application Entry & UI Setup`, `Community 35`, `Main Window & Repair Actions`, `Community 30`?**
  _High betweenness centrality (0.051) - this node is a cross-community bridge._
- **Why does `LaptopRepairManager` connect `Main Window & Repair Actions` to `Customer Database Layer`, `Application Entry & UI Setup`, `Community 35`, `Calendar & UI Components`, `Controller & Data Operations`, `Settings & Notification Dialogs`, `Community 29`, `Community 30`?**
  _High betweenness centrality (0.038) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `CustomerService` (e.g. with `CustomerRepository` and `CompleterItemDelegate`) actually correct?**
  _`CustomerService` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 7 inferred relationships involving `LaptopRepairManager` (e.g. with `MainController` and `SQLiteStorage`) actually correct?**
  _`LaptopRepairManager` has 7 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `CustomerRepository` (e.g. with `CustomerDB` and `CustomerService`) actually correct?**
  _`CustomerRepository` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `RepairDialog` (e.g. with `LaptopRepairManager` and `NotificationDialog`) actually correct?**
  _`RepairDialog` has 4 INFERRED edges - model-reasoned connections that need verification._