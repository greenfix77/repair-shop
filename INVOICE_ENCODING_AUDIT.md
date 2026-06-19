# Invoice Generator — Encoding & Integrity Audit

**File:** `services/invoice_generator.py`  
**Audit date:** 2026-06-18

---

## 1. File Encoding

| Property          | Status                        |
|-------------------|-------------------------------|
| Encoding          | UTF-8 (no BOM)                |
| Line endings      | LF (Unix-style)               |
| Size              | 19,819 bytes                  |
| BOM               | Not present                   |
| Control chars     | None found                    |
| Mixed tabs/spaces | None (4-space indentation)    |

**Verdict:** ✅ Correct encoding. No BOM, no carriage-return contamination, no control characters.

---

## 2. Mojibake Text (Ø§Ù... etc.)

No instances of Windows-1252/Latin-1 mojibake (e.g. `Ø§`, `Ù…`, `ÃŒ`, `Å¡`, `Â`) were found in the file.

All Persian text is stored as proper UTF-8 byte sequences and renders correctly. ZWNJ (zero-width non-joiner `\u200C`) is used intentionally in Persian words such as `گزارش‌شده` (line 165) and `یادداشت‌ها` (lines 205, 519) — these are legitimate and correctly formed.

**Verdict:** ✅ No mojibake present.

---

## 3. Corrupted Persian Strings

All Persian strings are intact and grammatically correct:

- فارسی header labels (شماره فاکتور, تاریخ, نام مشتری, etc.)
- Table row labels (دستگاه, مشکل گزارش‌شده, هزینه قطعات, etc.)
- Section titles (یادداشت‌ها, گارانتی, امضای مشتری, etc.)
- `jdatetime` Persian date formatting

**Verdict:** ✅ No corrupted Persian strings.

---

## 4. Broken CSS

Three CSS issues were found, all in f-string escaped braces (`{{` / `}}` — correct for Python f-strings):

### Issue A — Line 42
```css
padding-bottom: 10px;margin-bottom: 15px;
```
Missing whitespace after the semicolon. Valid syntax, but inconsistent with the rest of the file.

### Issue B — Line 118
```css
font-size: 9pt;color: #333;
```
Missing whitespace after the semicolon. Same style inconsistency.

### Issue C — Lines 322–323 (CRITICAL)
```css
                    co                    color: #667eea;
```
**Accidental text:** The fragment `co` followed by ~20 spaces and then a full `color: #667eea;` declaration. This is a clear copy-paste / refactoring artifact. The property `color` appears twice — once as a partial word `co` and once correctly. This **will** be ignored by browsers (the second `color` wins), so it does not break rendering, but it is dead/invalid CSS text.

**Verdict:** ⚠️ 3 CSS issues found, one of which (line 322) is a refactoring artifact.

---

## 5. Accidental Text Inserted During Refactor

### Line 322 — `co                    color: #667eea;`
- Hex dump confirms `63 6F` (`co`) followed by 20 spaces (`20`) followed by a complete `color: #667eea;` declaration.
- This reads as someone began typing `color`, paused (or pasted), then typed the full `color` declaration again.
- The stray `co` is inert CSS (overridden by the subsequent `color`), but it is technically garbage text.

**No other accidental insertions found.**

**Verdict:** ⚠️ One refactoring fragment on line 322.

---

## Summary

| Category                        | Finding                                                       | Severity |
|---------------------------------|---------------------------------------------------------------|----------|
| File encoding                   | UTF-8 no BOM — correct                                        | ✅       |
| Mojibake                        | None                                                          | ✅       |
| Corrupted Persian strings       | None                                                          | ✅       |
| Broken CSS                      | 3 instances (lines 42, 118 missing whitespace; line 322 `co` artifact) | ⚠️ |
| Accidental refactor text        | `co` fragment on line 322                                     | ⚠️       |

### Recommended Fixes

1. **Line 322:** Remove the stray `co                    ` before `color: #667eea;`.
2. **Line 42:** Add space: `padding-bottom: 10px; margin-bottom: 15px;`
3. **Line 118:** Add space: `font-size: 9pt; color: #333;`
