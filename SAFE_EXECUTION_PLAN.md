# SAFE EXECUTION PLAN

## 1. Exact Extraction Sequence (Risk-Based)

### Phase 1: Lowest Risk (Dependency Isolation)
1. Extract UI creation methods to ui/main_window.py
2. Extract statistics calculation to services/statistics.py
3. Extract filtering logic to core/filters.py

### Phase 2: Medium Risk (Logic Separation)
4. Extract table rendering to ui/table_renderer.py
5. Extract business logic methods to core/business_logic.py

### Phase 3: Higher Risk (Integration Points)
6. Extract invoice service to services/invoice_service.py

## 2. Step-by-Step Execution

### Step 1: UI Components Extraction
- **Files**: app.py → ui/main_window.py
- **Methods**: init_ui, create_header, create_toolbar, create_table, create_status_bar
- **Risk**: Low
- **Rollback**: Revert import statements and method calls
- **Test**: Verify UI still renders correctly

### Step 2: Statistics Logic Extraction
- **Files**: app.py → services/statistics.py
- **Methods**: update_statistics
- **Risk**: Low
- **Rollback**: Revert import and method call
- **Test**: Verify stats counters still update

### Step 3: Filtering Logic Extraction
- **Files**: app.py → core/filters.py
- **Methods**: search_repairs, filter_repairs
- **Risk**: Low
- **Rollback**: Revert import and method calls
- **Test**: Verify search/filter still works

### Step 4: Table Rendering Extraction
- **Files**: app.py → ui/table_renderer.py
- **Methods**: refresh_table
- **Risk**: Medium
- **Rollback**: Revert import and method call
- **Test**: Verify table displays data correctly

### Step 5: Business Logic Extraction
- **Files**: app.py → core/business_logic.py
- **Methods**: add_repair, edit_repair, delete_repair
- **Risk**: Medium
- **Rollback**: Revert import and method calls
- **Test**: Verify CRUD operations work

### Step 6: Invoice Service Extraction
- **Files**: app.py → services/invoice_service.py
- **Methods**: preview_invoice
- **Risk**: High
- **Rollback**: Revert import and method call
- **Test**: Verify invoice preview still works

## 3. First Safe Commit
Extract UI creation methods (init_ui, create_header, etc.) to ui/main_window.py - lowest risk with immediate structural benefit.

## 4. First High Impact Commit
Extract refresh_table to ui/table_renderer.py - significantly reduces main class complexity.

## 5. Danger Commits (Delay These)
- Invoice service extraction (preview_invoice) - complex integration with InvoicePreviewDialog
- Business logic extraction (CRUD operations) - many dependencies on dialogs and storage

## 6. Testing Checkpoints
- After each commit: Run application and verify core functionality
- UI rendering after Step 1
- Stats updating after Step 2
- Search/filter after Step 3
- Table display after Step 4
- CRUD operations after Step 5
- Invoice preview after Step 6

## 7. Dependency Freeze Rules
- Do not modify storage layer during UI extraction
- Do not modify UI components during business logic extraction
- Maintain backward compatibility until all phases complete

## 8. UI Break Prevention Strategy
- Keep all UI signals/slots intact during extraction
- Maintain same method signatures during transition
- Test UI interactions after each commit
- Preserve QMessageBox behaviors during refactoring