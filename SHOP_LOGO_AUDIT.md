# Shop Logo Usage Audit

## 1. Where Logo Path Is Stored

**File:** `shop_settings.json` → key `"logo"`

Current value:
```
"C:/Users/AL/Desktop/repair_manager/logo.png"
```

The logo path is persisted as an absolute filesystem path with forward-slash separators (Windows-compatible).

Additional logo-related keys now in `shop_settings.json`:
- `invoice_logo_size` (96) — intended for invoice logo sizing
- `header_logo_size` (64) — intended for header logo sizing
- `use_logo_as_app_icon` (true) — intended to set application icon from logo

---

## 2. Whether Logo Path Is Loaded Correctly

| Consumer | Method | Loads Logo? | Correct? |
|---|---|---|---|
| `ShopSettingsDialog.load_settings()` | `settings.get("logo", "")` | ✅ Yes | ✅ Sets `self.logo_path` and displays filename |
| `ShopSettingsDialog.get_settings()` (static) | Returns full JSON | ✅ Yes | ✅ Returns `logo` key from file |
| `InvoicePreviewDialog.__init__()` | `ShopSettingsDialog.get_settings()` | ✅ Yes | ✅ Logo path available as `shop_settings['logo']` |
| `ui/main_window.py` `_get_shop_name()` | Reads JSON manually | ❌ No | Only reads `shop_name`, ignores logo entirely |

---

## 3. Whether Invoice HTML Uses the Logo

### `generate_print_invoice_html()` — Print invoice
**Does NOT use the logo at all.** There is no `<img>` tag, no logo variable, no logo reference anywhere in the print template.

### `generate_web_invoice_html()` — Web/color invoice  
**Uses the logo** (lines 264–266):
```python
if settings.get('logo') and Path(settings['logo']).exists():
    logo_html = f'<img src="file:///{settings["logo"]}" style="max-width: 120px; max-height: 80px;">'
```

**Issue:** The `max-width`/`max-height` are hardcoded to `120px` / `80px`. The `invoice_logo_size` setting is stored but never read here.

---

## 4. Whether QWebEngineView Receives the Logo Image

**Current state:** `USE_WEB_PREVIEW = True` in `invoice_dialog.py`.

The web invoice HTML is generated with:
```html
<img src="file:///C:/Users/AL/Desktop/repair_manager/logo.png" ...>
```

**Problem:** `QWebEngineView` (Chromium) **blocks `file:///` URLs by default** for security. The logo image will not render inside `QWebEngineView` unless:
- A `QWebEngineUrlSchemeHandler` is registered for `file://`, or
- The logo is converted to a base64 data URI and inlined, or
- Web security is disabled (`--disable-web-security`, not recommended)

When rendered in `QTextEdit` (non-web mode), this `file:///` URL may also fail because `QTextEdit` does not resolve `file:///` paths with absolute Windows paths reliably.

---

## 5. Whether Application Icon Is Connected to Shop Logo

**No connection exists.**

`app.py` creates `QApplication(sys.argv)` at line 280 but never calls `app.setWindowIcon()`. The `use_logo_as_app_icon` key is:
- ✅ Saved to `shop_settings.json` by `ShopSettingsDialog.save_settings()`
- ✅ Loaded into UI by `load_settings()` (checkbox state)
- ❌ **Never read or applied** anywhere outside the settings dialog
- ❌ No code converts the logo image to a `QIcon` and sets it as application/window icon

---

## 6. Whether Header Title Icon Is Connected to Shop Logo

**No connection exists.**

`ui/main_window.py` builds the header (lines 34–63):
- Uses a **text-only emoji** prefix `"🔧 "` in `_make_title()`
- Sets window title text via `window.setWindowTitle(_make_title(icon=False))`
- Does **not** render an actual `QPixmap` / `QLabel(pixmap)` for the shop logo
- Does **not** read `shop_settings.json` for the logo at all
- The `header_logo_size` setting is stored but **never read** anywhere

---

## 7. Missing Links Preventing Logo Display

| # | Gap | Impact | Location |
|---|---|---|---|
| 1 | Print invoice has **no logo slot** | Logo never appears in black-and-white invoice | `services/invoice_generator.py:9` `generate_print_invoice_html()` |
| 2 | Web invoice uses `file:///` URL | **Blocked by Chromium** in QWebEngineView; unreliable in QTextEdit | `services/invoice_generator.py:266` |
| 3 | `invoice_logo_size` stored but **never consumed** | Hardcoded 120×80px sizing cannot be customized | `invoice_generator.py:266` vs `shop_settings.json` |
| 4 | `header_logo_size` stored but **never consumed** | Orphan setting with no consumer | `shop_settings.json` key has zero references |
| 5 | `use_logo_as_app_icon` stored but **never applied** | No `QApplication.setWindowIcon()` call exists | `app.py` — no logo-to-icon pipeline |
| 6 | Header has **no image widget** for logo | Title bar and header use text/emoji only | `ui/main_window.py:34-63` `build_header()` |
| 7 | No centralized logo loading utility | Each consumer would need to re-read JSON and convert to appropriate format | Across all files |

### Recommended Fixes (in order of priority)

1. **Convert logo to base64 data URI** in `generate_web_invoice_html()` to work in both QTextEdit and QWebEngineView
2. **Add logo to print invoice template** (mirror the web template's logo block)
3. **Apply `use_logo_as_app_icon`** in `app.py` after loading shop settings
4. **Consume `invoice_logo_size`** in the web invoice template instead of hardcoded values
5. **Add logo `QPixmap` to header** in `main_window.py` using `header_logo_size`
6. **Create a shared `get_shop_logo()` helper** to avoid scattered JSON reads
