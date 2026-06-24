# Invoice Blank Preview Audit

## Root Cause

**The base64-encoded logo inflates the HTML to ~2 MB, overwhelming QWebEngineView.**

| Metric | Value |
|---|---|
| Normal invoice HTML (no logo) | 6,556 bytes (6.5 KB) |
| Invoice HTML with logo base64 | 2,035,005 bytes (~2 MB) |
| Logo file size (logo.png) | 1,521,277 bytes (1.5 MB) |
| Base64 data in HTML | 2,028,372 chars |
| Size inflation factor | 310× |

The 1.5 MB PNG logo is converted to a base64 data URI (~2 MB) and embedded directly in the HTML via `<img src="data:image/png;base64,...">`. This makes the HTML string passed to `QWebEngineView.setHtml()` approximately **2 MB** instead of the expected ~6 KB.

### Why this causes a blank preview

1. **QWebEngineView.setHtml() limit**: Chromium's `QWebEngineView` has practical limits on inline HTML size. A 2 MB HTML string with an embedded data URI can cause the engine to time out, render a white page, or silently fail.

2. **QTextEdit.setHtml() limit**: `QTextEdit` also struggles with multi-megabyte HTML. It may truncate or fail to render content.

3. **Data URI size limit**: Chromium has an effective ~2 MB limit for data URI resources. The logo base64 (~2 MB) pushes this boundary.

4. **Memory pressure**: Creating and passing a 2 MB Python string for every preview update consumes excessive memory.

---

## Affected Files

| File | Role | Impact |
|---|---|---|
| `services/logo_service.py:44-54` | `get_invoice_logo_html()` | Embeds full-size logo as base64 without size check |
| `services/invoice_generator.py:24,134,268` | Both generators | Calls `get_invoice_logo_html()`, inflating HTML to 2 MB |
| `ui/widgets/web_invoice_view.py:16-17` | `set_html()` | Receives 2 MB HTML, passes to QWebEngineView |
| `ui/dialogs/invoice_dialog.py:114-116` | `update_preview()` | Feeds 2 MB HTML to both QTextEdit and QWebEngineView |

---

## Checks Performed

| Check | Result |
|---|---|
| 1. Is HTML actually generated? | ✅ Yes |
| 2. Is generated HTML empty? | ❌ No — but 2 MB is too large |
| 3. Is `setHtml()` receiving HTML? | ✅ Yes |
| 4. Is CSS hiding content? | ❌ No — no `display:none`, `visibility:hidden`, or color=background issue |
| 5. Is body text color same as background? | ❌ No — print: `#000` on white; web: black on white container |
| 6. Is invoice container width collapsing? | ❌ No — `max-width: 180mm` / `210mm` with `margin: 0 auto` |
| 7. Does base64 logo break HTML? | ✅ Yes — 2 MB data URI exceeds Chromium inline limits |
| 8. Is QWebEngineView rendering white page? | ✅ Yes — due to 2 MB HTML size |
| 9. Does QTextEdit preview still show content? | ❌ Likely also fails with 2 MB HTML |

### CSS anomalies found (not root cause)

- `.meta-section h3` has invalid CSS: `co                    color: #667eea;` (typo `co` before `color`). Browsers ignore unknown properties — not a blank-page cause.
- HTML starts with newline before `<!DOCTYPE html>` (f-string formatting). Browsers tolerate this.

---

## Risk Level

**HIGH** — The logo service has no size guard. Any user-selected logo larger than ~100 KB will silently break the invoice preview. A 1.5 MB logo is extreme, but even a 500 KB image would produce ~700 KB of HTML, risking preview failure.

---

## Recommended Minimal Fix

1. **Resize logo to `invoice_logo_size` before base64 encoding** in `image_to_base64()` or `get_invoice_logo_html()`. Load the image with `PIL` (Pillow) or `QPixmap`, scale it to the configured size (default 96 px), then encode the scaled version. This keeps the base64 data small regardless of the original file size.

2. **Add a maximum size guard** — if the image file exceeds ~200 KB, skip the logo and return empty string to avoid breaking the preview.

3. **Alternative**: Cache the base64 result so the file is not re-read and re-encoded on every preview update.

**Without a size limit, any logo upload will risk rendering the entire invoice preview unusable.**
