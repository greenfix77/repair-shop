# REPAIR_MANAGER OPCODE RULES

## PRIMARY GOAL

Fast, safe development with:

* zero data loss
* zero encoding corruption
* small atomic changes
* production stability

Architecture refactor is COMPLETE.

Current focus:

1. Stability
2. Bug fixes
3. SQLite validation
4. New features

Not current focus:

* architecture rewrites
* extra abstraction layers
* cosmetic refactors
* rewriting working code

---

# NEVER

Never:

* change file encoding
* convert UTF-8 Persian text
* touch Persian comments
* rewrite entire files
* reformat unrelated code
* move code and refactor logic in same step
* perform multiple architectural changes at once
* change UI appearance unless requested
* rename keys used by existing code
* add unnecessary abstractions
* create circular imports
* modify working code without reason
* auto-format large files
* reorder imports unnecessarily
* optimize working code
* change database schema without approval

---

# ENCODING PROTECTION

CRITICAL

Persian text exists in this project.

Never:

* save Python files as ANSI
* save files as Windows-1252
* save files as Latin-1
* convert Persian comments
* convert Persian strings
* replace Persian text globally
* rewrite files only for formatting

Required:

* UTF-8 only
* UTF-8 without BOM preferred

If a file contains Persian text:

DO NOT TOUCH ENCODING.

If encoding is uncertain:

STOP

Create report.

Do not modify file.

---

# ALWAYS

Always:

* use smallest possible changes
* create new files instead of rewriting existing files
* move code first, refactor later
* one extraction per step
* one feature per step
* validate imports after each change
* preserve all behavior exactly
* preserve Persian text exactly
* preserve UTF-8 encoding
* preserve comments
* prefer copy → import → delete
* keep commits small
* keep changes reversible

---

# BEFORE MODIFYING

Always run:

```bash
git status
```

Working tree must be clean.

If not clean:

STOP

Report uncommitted files.

Wait for approval.

---

# ANALYZE FIRST

Before coding:

Analyze first.

If uncertain:

DO NOT MODIFY.

Create report instead.

---

# COMPILATION CHECK

After modifications:

```bash
python -m py_compile app.py
```

If compilation fails:

STOP

Fix errors.

Do NOT commit.

Do NOT push.

---

# MANUAL TESTING

Before commit:

Run application.

Test affected functionality.

Minimum validation:

* application starts
* modified feature works
* no visible regression

---

# GIT POLICY

Every successful step MUST end with:

1. Compilation
2. Manual test
3. Commit
4. Push

---

## Commit format

```text
<scope>: <short description>
```

Examples:

```text
feat: add customer validation
feat: add sqlite repository
fix: restore utf8 persian text
fix: resolve circular import
refactor: extract repair service
refactor: move dialogs to ui.dialogs
cleanup: remove dead code
docs: update architecture
```

Rules:

* one feature = one commit
* one bug fix = one commit
* one refactor = one commit
* never mix unrelated changes

---

## Commit

```bash
git add .
git commit -m "<message>"
```

---

## Push

After successful commit:

```bash
git push origin main
```

If using another branch:

```bash
git push origin <branch>
```

Verify push succeeded.

---

# SAFETY CHECKPOINTS

Before risky operations:

```bash
git add .
git commit -m "checkpoint: before <operation>"
git push origin main
```

Examples:

```text
checkpoint: before sqlite migration
checkpoint: before pyqt6 migration
checkpoint: before customer database
checkpoint: before inventory module
```

---

# REPORT FORMAT

After every change report:

* modified files
* created files
* deleted files
* imports added
* imports removed
* commit message used
* push status

Example:

```text
modified files:
- app.py

created files:
- services/customer_service.py

deleted files:
- none

imports added:
- from services.customer_service import CustomerService

imports removed:
- none

commit:
feat: add customer service

push:
success
```

---

# FORBIDDEN GIT ACTIONS

Never:

* force push
* amend commits
* rewrite history
* auto squash commits
* commit broken code
* push broken code
* continue with uncommitted changes

---

# SQLITE STATUS

Current storage mode:

```text
DualStorage
├── repairs.json
└── repair_manager.db
```

Rules:

* do not remove DualStorage yet
* do not delete repairs.json
* do not switch to SQLite-only mode without audit
* validate SQLite through real usage first

---

# PROJECT STATUS

Architecture refactor is COMPLETE.

Do not perform additional architecture refactors unless explicitly requested.

Avoid modifying:

* services/invoice_generator.py
* services/invoice_exporter.py
* notification workflow

unless fixing a verified bug.

---

# CURRENT ROADMAP

Current order:

1. SQLite validation
2. SQLite-only migration
3. Customer database
4. Reports
5. Dashboard
6. Inventory
7. SMS notifications
8. Multi-user support
9. PyQt6 migration

Do not change roadmap unless requested.

---

# PRIORITY

1. Data safety
2. UTF-8 safety
3. Compiles
4. Runs
5. Tested
6. Commit
7. Push
8. Next step
