# Font Usage Audit

## 1. Every Occurrence of `setFont(`, `QFont(`, `font-family:`

### `setFont(` (6 occurrences)

| File | Line | Code |
|------|------|------|
| `app.py` | 60 | `type_label.setFont(QFont("Segoe UI", 10, QFont.Bold))` |
| `app.py` | 161 | `title.setFont(QFont("Segoe UI", 14, QFont.Bold))` |
| `app.py` | 322 | `title.setFont(QFont("Segoe UI", 14, QFont.Bold))` |
| `app.py` | 975 | `app.setFont(font)` |
| `ui/table_renderer.py` | 25 | `item.setFont(QFont("Segoe UI", 10, QFont.Bold))` |
| `repair_manager/ui/components.py` | 27 | `self.setFont(font)` |

### `QFont(` (6 occurrences)

| File | Line | Code |
|------|------|------|
| `app.py` | 60 | `QFont("Segoe UI", 10, QFont.Bold)` |
| `app.py` | 161 | `QFont("Segoe UI", 14, QFont.Bold)` |
| `app.py` | 322 | `QFont("Segoe UI", 14, QFont.Bold)` |
| `app.py` | 974 | `QFont("Segoe UI", 10)` |
| `ui/table_renderer.py` | 25 | `QFont("Segoe UI", 10, QFont.Bold)` |
| `repair_manager/ui/components.py` | 26 | `QFont("Segoe UI", 10)` |

### `font-family:` (2 occurrences, both in CSS embedded in HTML strings)

| File | Line | Value |
|------|------|-------|
| `services/invoice_generator.py` | 32 | `'Segoe UI', Tahoma, Arial, sans-serif` |
| `services/invoice_generator.py` | 267 | `'Segoe UI', Tahoma, Arial, sans-serif` |

---

## 2. All Font Names Used

| Font Name | Where Used |
|-----------|-----------|
| **Segoe UI** | Every `QFont()` call (6 times); every `font-family` fallback list (2 times) |
| **Tahoma** | `font-family` fallback in both HTML generators |
| **Arial** | `font-family` fallback in both HTML generators |
| **sans-serif** | Generic fallback in both HTML generators |

No other font names appear anywhere in `app.py`, `ui/*`, or `services/*`.

---

## 3. Font Name Changes After Refactoring

**None.** The font name `"Segoe UI"` has been present since the initial commit (`2249a63`) and has never changed across any refactoring commit. All `QFont()` and `setFont()` calls have consistently used `"Segoe UI"`. The CSS `font-family` stack `'Segoe UI', Tahoma, Arial, sans-serif` is also unchanged across all commits.

---

## 4. Persian-Capable Font in Generated HTML

Both HTML generators (`generate_print_invoice_html` at line 9, `generate_web_invoice_html` at line 238) use the same `font-family` declaration:

```
font-family: 'Segoe UI', Tahoma, Arial, sans-serif;
```

- **Segoe UI** — ships with Windows; includes full Arabic-script (Persian) character support. Yes, it supports Persian.
- **Tahoma** — ships with Windows; includes Arabic-script (Persian) support. Yes, it supports Persian.
- **Arial** — does NOT include Arabic/Persian glyphs by default on most systems.
- **sans-serif** — system-dependent; may or may not render Persian.

The first two fonts in the stack (Segoe UI, Tahoma) both support Persian. On a standard Windows system, Persian text will render correctly.

---

## 5. Fonts That May NOT Support Persian in Qt `QTextDocument`

| Font | Risk | Notes |
|------|------|-------|
| **Segoe UI** | ✅ Safe | Ships with Windows 7+; full Arabic/Persian glyph set |
| **Tahoma** | ✅ Safe | Ships with Windows; full Arabic/Persian glyph set |
| **Arial** | ⚠️ Unsafe | Default Arial on Windows lacks Arabic/Persian glyphs; Persian characters render as boxes/tofu |
| **sans-serif** | ⚠️ Unknown | Depends on system default sans-serif; on Windows this typically maps to Microsoft Sans Serif (no Persian) or Segoe UI (has Persian) |

**Summary:** Persian text will render correctly as long as Segoe UI or Tahoma is available (both are present on all modern Windows systems). Arial will *not* render Persian, but it is only a fallback, so it should never be reached for Persian content on a standard Windows installation.
