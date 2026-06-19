# InvoicePreviewDialog — Preview Render Audit

## 1. `update_preview()` — Exact Implementation

**File:** `app.py:132–139`

```python
def update_preview(self):
    if self.print_radio.isChecked():
        html = generate_print_invoice_html(self.repair_data, self.shop_settings)
    else:
        html = generate_web_invoice_html(self.repair_data, self.shop_settings)
    self.preview.setHtml(html)
```

Logic:
- If `self.print_radio` is checked → calls `generate_print_invoice_html()`
- Otherwise → calls `generate_web_invoice_html()`
- The returned string is assigned to `html`, then passed directly to `self.preview.setHtml(html)`

---

## 2. Widget Type of `self.preview`

**File:** `app.py:80`

```python
self.preview = QTextEdit()
```

- `self.preview` is a **`QTextEdit`** (from `PyQt5.QtWidgets`).
- Set to read-only at line 81: `self.preview.setReadOnly(True)`

---

## 3. Every Call to `setHtml` / `setText` / `setPlainText`

| Method         | Location    | Line | Context |
|----------------|-------------|------|---------|
| `setHtml`      | `app.py`    | 139  | `self.preview.setHtml(html)` inside `update_preview()` |
| `setText`      | —           | —    | **Never called** in `InvoicePreviewDialog` |
| `setPlainText` | —           | —    | **Never called** in `InvoicePreviewDialog` |

---

## 4. Every Use of `encode(...)` / `decode(...)` / `bytes(...)`

**None found** anywhere within:
- `InvoicePreviewDialog` (app.py:40–140)
- `generate_print_invoice_html()` (services/invoice_generator.py:9–235)
- `generate_web_invoice_html()` (services/invoice_generator.py:238–538)

---

## 5. Conversions Applied to Generated HTML Before Rendering

**None.**

The HTML string returned by `generate_print_invoice_html()` or `generate_web_invoice_html()` is assigned directly to the local variable `html` and then immediately passed to `self.preview.setHtml(html)` without any intermediate transformation, encoding, decoding, sanitization, or string manipulation.
