# QWebEngineView Migration Audit

## Overview

Replace `QTextEdit` invoice preview with `QWebEngineView` for modern HTML/CSS rendering, proper CSS3/gradient/flexbox support, and native Chromium-based print/PDF capabilities.

---

## Affected Files

| File | Role | Impact |
|---|---|---|
| `ui/dialogs/invoice_dialog.py` | Invoice preview dialog | QTextEdit → QWebEngineView |
| `services/invoice_exporter.py` | Print & PDF export | Replace QTextDocument + QPrinter with QWebEngineView.page() API |
| `services/invoice_generator.py` | HTML generation | Low — CSS may need minor Chromium adjustments |
| `requirements.txt` (not yet read) | Dependencies | Must add `PyQtWebEngine` |

---

## QTextEdit Dependencies

### `invoice_dialog.py` — QTextEdit usage (4 sites)

| Line | Code | Role |
|---|---|---|
| 2 | `from PyQt5.QtWidgets import ... QTextEdit ...` | Import |
| 52–53 | `self.preview = QTextEdit()` / `setReadOnly(True)` | Widget instantiation |
| 82, 95 | `self.preview.toHtml()` | Extract HTML for print/PDF |
| 105 | `self.preview.setHtml(html)` | Render HTML preview |

**Breaking change**: `QWebEngineView` has `setHtml()` but **no synchronous `toHtml()`**. Callback-based `page().toHtml(callback)` is required.

---

## Print / PDF Dependencies

### `invoice_exporter.py` — QTextDocument + QPrinter usage (2 sites)

| Line | Code | Role |
|---|---|---|
| 2 | `from PyQt5.QtGui import QTextDocument` | Document model for print/PDF |
| 3 | `from PyQt5.QtPrintSupport import QPrinter, QPrintDialog` | Printer + dialog |
| 13–15 | `QTextDocument().setHtml(...)` + `doc.print_(printer)` | Print execution |
| 20–25 | `QPrinter(PdfFormat)` + `doc.print_(printer)` | PDF export |

**Breaking change**: `QWebEngineView` replaces both with:
- `page().printToPdf(filename)` — async (callback/Q promise based)
- `page().print()` — triggers Chromium's own print dialog

---

## Migration Risks

### 1. Async printToPdf breaks synchronous API
`save_invoice_to_pdf` currently calls `doc.print_(printer)` synchronously and then shows a success message. `QWebEnginePage.printToPdf()` is asynchronous (callback or `QFuture`). The success notification must move into the callback, and `QFileDialog` + save flow must be restructured.

### 2. No synchronous toHtml()
`invoice_dialog.py` calls `self.preview.toHtml()` to grab HTML for printing/PDF. `QWebEngineView` provides `page().toHtml(callback)` only. The HTML content must be stored as a member variable (`self._current_html`) instead of extracted from the widget.

### 3. Chromium `file:///` security policy
`invoice_generator.py` loads logo images via:
```html
<img src="file:///{settings['logo']}">
```
Chromium blocks `file:///` requests by default. Either:
- Serve via a `QWebEngineUrlSchemeHandler`, or
- Convert logo to base64 data URI, or
- Disable web security (`--disable-web-security`, not recommended)

### 4. Print dialog UX change
Current flow shows a native `QPrintDialog` (print-to-printer or print-to-PDF). `QWebEnginePage.print()` shows Chromium's built-in print dialog — different UX, no QPrinter configuration.

### 5. Application size increase
`PyQtWebEngine` bundles Chromium (~100–200 MB). Significant installer size increase.

### 6. Startup time increase
Chromium engine initialization adds noticeable delay on first web view creation.

### 7. CSS rendering differences
The `@page` CSS rule (line 29 of generator) and print-specific styles may behave differently in Chromium's print engine vs QTextDocument's layout engine.

### 8. New dependency
`PyQtWebEngine` is a separate package from `PyQt5`. Must be added to `requirements.txt`.

### 9. Persian/RTL rendering
Current Persian text renders via QTextEdit's built-in BiDi engine. Chromium has its own RTL shaping — minor rendering differences possible but generally better.

### 10. Status badge colors
`get_status_color()` returns CSS color strings used inline. No change needed.

---

## Recommended Migration Steps

### Phase 1 — Foundation (no functional changes)

1. **Add dependency**
   - `pip install PyQtWebEngine`
   - Add to `requirements.txt`

2. **Store HTML in `invoice_dialog.py`**
   - Add `self._current_html = ""` in `__init__`
   - Store HTML in `update_preview()` before calling `setHtml()`
   - Replace `self.preview.toHtml()` with `self._current_html` in `print_invoice` and `save_pdf`

### Phase 2 — Swap widget

3. **Replace QTextEdit → QWebEngineView**
   - Change import: `from PyQt5.QtWebEngineWidgets import QWebEngineView`
   - Remove `QTextEdit` from import line
   - `self.preview = QWebEngineView()` (no `setReadOnly` needed)
   - `self.preview.setHtml(self._current_html)` — keep existing API

### Phase 3 — Refactor print/PDF

4. **Refactor `print_invoice`** — use `QWebEngineView` approach
   - Option A: `self.preview.page().print()` — uses Chromium print dialog
   - Option B: Keep `print_invoice_content()` but pass HTML string instead of extracting from widget

5. **Refactor `save_invoice_to_pdf`** — async printToPdf
   ```python
   def save_pdf(self):
       file_path, _ = QFileDialog.getSaveFileName(...)
       if file_path:
           self.preview.page().printToPdf(file_path)
           # Success notification in callback
   ```

6. **Update `invoice_exporter.py`**
   - Either keep as thin wrapper receiving the webview/page object, or
   - Remove QTextDocument/QPrinter imports entirely

### Phase 4 — Polish

7. **Test logo rendering** — convert to base64 data URI if `file:///` is blocked
8. **Test Persian font rendering** in Chromium
9. **Test print-to-PDF output** for A4 layout correctness
10. **Remove unused imports** (`QTextEdit`, `QTextDocument`, `QPrinter`, `QPrintDialog`)

---

## Summary

| Metric | Value |
|---|---|
| Files directly modified | 2 (invoice_dialog, invoice_exporter) |
| Files indirectly affected | 1 (invoice_generator — low risk) |
| New dependencies | 1 (PyQtWebEngine) |
| Sync → async changes | 1 (printToPdf) |
| High risk items | Async printToPdf, file:/// logo, app size |

**Recommendation**: Proceed with Phase 1 (store HTML separately) and Phase 2 (swap widget) as a single commit. Phase 3 (print/PDF refactor) in a follow-up commit.
