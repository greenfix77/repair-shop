# OpenCode Rules (v3)

## Priority Order

When rules conflict, follow this priority:

1. Preserve Existing Behaviour
2. Regression Prevention
3. Financial Safety
4. Backward Compatibility
5. Minimal Patch Principle
6. Scope First
7. Token Efficiency
8. UI Consistency

Never violate a higher-priority rule to satisfy a lower-priority one.

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
- glob
- directory listing
- validation
- status commands

If a command succeeds:

Continue to implementation.

Never repeat it unless the result can actually change.

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

- Model
- Repository
- Service
- UI

verify that every required connection is complete.

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

If any step is incomplete:

Report it before ending the phase.

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

---

# 33. Read Before Modify

Never modify a file before reading the relevant function or class.

Avoid blind patches.

Understand the surrounding code first.

---

# 34. Respect Existing Naming

Use the project's existing naming conventions.

Maintain consistency across:

- models
- repositories
- services
- UI

---

# 35. Stability First

When in doubt:

Prefer stability over cleverness.

Prefer compatibility over optimization.

Prefer small patches over rewrites.

Prefer preserving behaviour over new architecture.

---

# 36. Anti-Reasoning Loop

Never repeat or restate the same implementation plan.

Maximum planning iterations: 2.

If the same implementation intent appears more than twice:

- stop reasoning
- begin editing immediately

Do not rewrite the same plan using different wording.

---

# 37. Small Scope Execution

If the remaining work is limited to:

- one file
- one class
- one function

then:

- stop exploring
- stop searching
- modify only that target
- compile
- report
- stop

---

# 38. Progress Requirement

Every reasoning cycle must produce measurable progress.

Allowed progress:

- edit a file
- create a file
- remove obsolete code
- compile
- validate
- complete the task

If no measurable progress is made within two reasoning cycles:

Start implementation immediately.

---

# 39. No Endless Exploration

After the implementation target has been identified:

Do NOT continue performing:

- grep
- glob
- graphify query
- file inspection

Begin editing immediately.

---

# 40. Single Edit Pass

Do not repeatedly edit the same file.

Complete all intended modifications in one edit whenever possible.

Avoid many small edits to the same file.

---

# 41. Complete Patch Rule

Never modify only one side of an interface change.

When changing:

- function parameters
- method signatures
- constructors
- public APIs

update:

- implementation
- all required callers

before ending the phase.

Never leave partially applied interface changes.

---

# 42. Verify Patch Progress

Before editing the same file again:

Check whether the previous patch already contains the intended change.

Do not repeat edits that are already applied.

---

# 43. Batch Related Changes

If several nearby changes belong to the same function or file:

Apply them together.

Avoid many tiny sequential edits.

---

# 44. Command Deduplication

Never execute the same command repeatedly if its result cannot change.

Reuse previous successful results.

Avoid redundant shell commands.

---

# 45. Finish Current Target

Finish the current function or file completely before moving elsewhere.

Do not switch between multiple unfinished sections.

---

# 46. No Planning After Target Identification

Once the exact target has been identified:

Stop planning.

Begin implementation immediately.

Do not generate additional implementation plans.

---

# 47. Final Principle

A successful phase is one that is:

- complete
- minimal
- compiled
- regression-safe
- backward compatible

Stop immediately after these conditions are satisfied.

## Execution Watchdog

If the assistant emits three consecutive messages that begin with phrases like:

- "Now I'll..."
- "I will now..."
- "Next I'll..."
- "Let me..."

without producing an actual code edit,

the reasoning phase is considered stalled.

Immediately:

- stop reasoning
- edit the target function
- compile
- report
- terminate the phase

Do not emit another planning message.