# GIT POLICY

Every successful step MUST end with:

1. Verify:

python -m py_compile app.py

2. Manual run and quick test.

3. Create a small atomic commit.

Commit message format:

<scope>: <short description>

Examples:

refactor: extract repair service
refactor: extract invoice calculator
refactor: move dialogs to ui.dialogs
refactor: remove duplicated status styling
fix: restore utf8 persian text
fix: repair imports after dialog extraction
fix: resolve circular import
cleanup: remove dead code

---

NEVER create large commits.

One architectural change = one commit.

---

Before any modification:

git status

After successful modification:

git add .
git commit -m "<message>"

Report:

- modified files
- created files
- deleted files
- commit message used

---

If compilation fails:

DO NOT commit.

Fix errors first.

---

Before starting a new step:

Ensure working tree is clean:

git status

If not clean:
STOP and ask.

---

Before risky refactors:

Create safety checkpoint:

git add .
git commit -m "checkpoint: before <operation>"

Example:

checkpoint: before dialog extraction
checkpoint: before invoice generator extraction

---

FORBIDDEN

Never force push.
Never amend previous commits.
Never squash commits automatically.
Never commit broken code.
Never continue with uncommitted changes.

---

PRIORITY

1. Compiles
2. Runs
3. Tested
4. Commit
5. Next step

# PROJECT STATUS

Architecture refactor is COMPLETE.

Do not perform additional architectural refactors unless explicitly requested.

Avoid changing:

- invoice_generator.py
- notification logic
- invoice_exporter.py

Current priority:

1. Stability
2. Bug fixes
3. New features

Not priority:

- More layers
- More abstractions
- Rewriting working code
- Cosmetic refactors

Always prefer feature development over architecture changes.