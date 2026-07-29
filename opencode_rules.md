# OpenCode Rules (v2)

## Primary Goal

This project is a long-term production application.

The objective is to improve the software incrementally while preserving all existing functionality.

Never sacrifice stability for speed.

---

# 1. Scope First

Never explore or modify the whole project.

Always work inside the smallest possible scope.

Before writing code determine:

- exact files
- exact functions
- exact classes

that are required.

Never inspect unrelated modules.

---

# 2. One Phase Only

Each request represents one implementation phase.

Never continue into later roadmap phases.

Never anticipate future features.

Never refactor outside the requested phase.

---

# 3. Architecture Preservation

Do not redesign architecture unless explicitly requested.

Reuse existing:

- Services
- Repositories
- Dialogs
- Widgets
- Models

Avoid creating new abstractions unless absolutely necessary.

---

# 4. Preserve Existing Behaviour

Existing behaviour has higher priority than new features.

Never modify existing workflows unless explicitly requested.

Do NOT change:

- calculations
- persistence
- dashboard
- reports
- invoice generation
- customer workflow
- payment workflow

unless the phase explicitly requires it.

---

# 5. Minimal Patch Principle

Generate the smallest possible patch.

Avoid:

- formatting-only edits
- unrelated cleanup
- moving code
- automatic refactoring
- file-wide rewrites

Modify only the required code.

---

# 6. Never Delete Without Verification

Never delete:

- files
- classes
- methods
- imports
- functions

unless ALL are true:

- verified unused
- searched project-wide
- explicitly requested

If uncertain:

Leave the code.

---

# 7. Never Rewrite Large Files

Never regenerate an entire file.

Patch only the necessary section.

Large rewrites dramatically increase regression risk.

---

# 8. UI Rules

Maintain:

- RTL
- existing spacing
- existing layout
- existing workflow
- existing navigation

Do not redesign unrelated widgets.

All new UI must match the current application style.

---

# 9. Design Rules

Always follow these UI standards:

- Main buttons height: 36 px
- Green only for confirmation actions
- Red only for delete actions
- 16 px spacing between cards
- Financial forms share one common layout
- Tables share one common header style
- Dialogs use one common grid layout

Never violate these rules.

---

# 10. Financial Safety

Financial code is critical.

Never modify:

- invoice calculations
- pricing
- payment logic
- dashboard totals
- ledger
- reports

unless explicitly requested.

---

# 11. Invoice Immutability

Invoices are immutable.

Historical snapshots never change.

Catalog changes must never modify historical invoices.

Never rewrite historical financial records.

---

# 12. Backward Compatibility

Every new field requires:

- safe default
- migration
- legacy fallback

Old databases must continue working.

Old JSON files must continue working.

---

# 13. Regression Prevention

Before modifying any function identify:

- who calls it
- who depends on it
- what data flows through it

Never modify shared code blindly.

---

# 14. Search Strategy

Never grep the whole repository.

Never recursively inspect every file.

Search only the requested subsystem.

Prefer Graphify whenever available.

Read only the files required.

---

# 15. Graphify Rules

If graphify-out exists:

Use Graphify queries first.

Never read GRAPH_REPORT.md for small tasks.

Prefer focused graph queries.

Use grep only when Graphify cannot answer.

---

# 16. Exploration Limit

Stop exploring once sufficient information exists.

Maximum:

- 3 file reads

OR

- 5 focused searches

before implementation.

If enough information exists:

Start coding.

Never continue exploring indefinitely.

---

# 17. Prevent Infinite Loops

Never repeatedly execute:

- echo
- compile
- graphify
- grep
- directory listing
- validation
- status commands

If a command succeeds:

Continue to implementation.

Never repeat it.

---

# 18. Validation Rules

Run validation only once.

Allowed:

python -m py_compile app.py

Only perform additional validation if explicitly requested.

Never repeatedly compile.

---

# 19. Safe Editing

Before editing:

Locate the exact function.

Patch only that function.

Do not regenerate surrounding code.

---

# 20. Error Recovery

If implementation fails:

Stop immediately.

Explain the failure.

Do not continue making speculative edits.

---

# 21. Deliverables

Each completed phase must include:

- Modified files
- Architecture impact
- Backward compatibility
- Migration details
- Regression assessment
- Compilation result

Nothing more.

---

# 22. Git Safety

Never:

- commit
- branch
- stash
- reset
- restore
- checkout
- rebase
- merge

unless explicitly instructed.

---

# 23. File Safety

Never:

- delete source files
- overwrite entire files
- replace app.py
- remove methods because they "appear unused"

If something appears unused:

Report it.

Do not delete it.

---

# 24. Large Project Rule

This repository is large.

Token efficiency matters.

Prefer:

- small reads
- focused patches
- concise outputs

Avoid long architectural summaries unless requested.

---

# 25. Stop Rule

When the requested phase is complete:

Stop.

Do not begin the next roadmap phase.

Wait for the next instruction.

---

# 26. Maximum Execution Time

If implementation exceeds approximately 10 minutes without producing a code patch:

Stop.

Explain why.

Suggest narrowing the scope.

Never continue indefinitely.

---

# 27. No Temporary Validation Scripts

Do NOT create:

- validation scripts
- helper scripts
- sandbox scripts
- migration simulators
- temporary testing utilities

unless explicitly requested.

Prefer reasoning over temporary code.

---

# 28. Existing Code First

Before creating any new:

- Service
- Repository
- Utility
- Helper
- Dialog
- Widget

verify whether an equivalent already exists.

Reuse existing code whenever possible.

Avoid duplicate business logic.

---

# 29. Single Source of Truth

Business logic must exist in exactly one place.

Never duplicate calculations.

Never duplicate financial logic.

Never duplicate persistence logic.

Always reuse the existing implementation.

---

# 30. Feature Completion Rule

Never leave a feature half-implemented.

If introducing:

- a new model
- a new repository
- a new service
- a new UI

verify that every required connection is complete.

Example:

Model

↓

Repository

↓

Service

↓

UI

↓

Navigation

↓

Persistence

↓

Loading

↓

Saving

↓

Compilation

Missing any step should be reported before ending the phase.

---

# 31. Navigation Safety

Whenever adding a new page, dialog, or view:

Verify:

- navigation button
- navigation handler
- stacked widget index
- refresh method
- signal connections

Never assume they already exist.

---

# 32. Compilation Before Completion

A phase is not complete until:

python -m py_compile app.py

passes successfully.

Compilation is mandatory before reporting success.

---

# 33. Read Before Modify

Never modify a file before reading the relevant function or class.

Avoid blind patches.

Understand the surrounding code first.

---

# 34. Respect Existing Naming

Use the project's existing naming conventions.

Do not introduce inconsistent names.

Maintain consistency across models, repositories, services, and UI.

---

# 35. Final Principle

When in doubt:

Prefer stability over cleverness.

Prefer compatibility over optimization.

Prefer small patches over large rewrites.

Prefer preserving existing behaviour over introducing new architecture.