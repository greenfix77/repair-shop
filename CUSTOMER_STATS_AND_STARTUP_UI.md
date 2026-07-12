# Customer Repair Statistics & Startup Notifications UI

## Overview

This document describes two changes delivered together:

1. **Customer repair statistics columns** added to the Customers table.
2. **Startup notifications screen** improved with a scrollable, compact layout.

Both changes preserve the existing Persian RTL styling, invoice logic, and
customer workflow. No database schema changes were made.

---

## 1. Customer Repair Statistics Columns

### New columns

The Customers tab table gained three new columns, placed **after** the
customer name and phone columns:

| Column (Persian) | Meaning |
|---|---|
| تعداد کل سفارشات | Total repairs linked to the customer |
| تحویل شده | Repairs whose status represents delivered/completed |
| در دست انجام | Repairs that are not delivered/completed/cancelled |

### Column order (new layout)

```
[select] کد مشتری | نام مشتری | تلفن | تعداد کل سفارشات | تحویل شده | در دست انجام | ایمیل | شهر | تاریخ ایجاد | ویرایش
```

Indices: 0=select, 1=code, 2=name, 3=phone, **4=total, 5=delivered, 6=in_progress**, 7=email, 8=city, 9=created_at, 10=edit.

### Status definitions

Using the existing status values defined in `core/status.py`:

- **تحویل شده (delivered)** = repairs with status
  `STATUS_DELIVERED` ('تحویل داده شده') or `STATUS_COMPLETED` ('تعمیر شده').
- **در دست انجام (in progress)** = all other repairs. There is no
  "cancelled" status defined in `core.status`, so this is every repair
  that is not delivered/completed. In practice this covers
  `STATUS_PENDING` and `STATUS_IN_PROGRESS`.
- **تعداد کل سفارشات (total)** = all repairs linked to the customer.

### Customer ↔ Repair linkage

Repairs do not carry a `customer_id` foreign key. They store `customer_name`
and `phone`. Linkage mirrors the existing
`LaptopRepairManager._has_related_repairs` logic in `app.py`:

1. Match by **phone** (exact, trimmed) — preferred.
2. If phone is absent, match by **customer_name** (exact, trimmed).

This keeps the statistics consistent with the rest of the application.

### Efficient computation (no N+1)

Statistics are computed by `services/customer_stats_service.py`:

```
compute_customer_repair_stats(repairs, customers) -> {customer_id: {total, delivered, in_progress}}
```

Algorithm:

1. Build two lookup maps from customers: `by_phone` and `by_name`
   (single pass over customers).
2. Single pass over repairs: for each repair, resolve matched customer
   ids via the maps and increment the relevant counters.

This is **O(R + C)** — one pass over repairs, one over customers —
avoiding any per-customer query against the database.

### Automatic refresh

Counts update automatically after any repair mutation:

| Action | Refresh trigger |
|---|---|
| Create repair (`add_repair`) | `_refresh_customer_table_if_visible()` |
| Edit repair (`edit_repair`) | `_refresh_customer_table_if_visible()` |
| Delete repair (`delete_repair`) | `_refresh_customer_table_if_visible()` |
| Bulk delete (`delete_selected_repairs`) | `_refresh_customer_table_if_visible()` |

`_refresh_customer_table_if_visible()` only recomputes when the Customers
view is the current page (`view_stack.currentIndex() == 1`), avoiding
unnecessary work while the Repairs view is shown. When the user switches
to the Customers tab, `show_customers_view()` calls `refresh_customer_table()`
which recomputes fresh stats from `self.repairs`.

Because editing a repair can change its status (delivered ↔ in-progress),
the edit path also triggers the refresh, so status changes are reflected.

### Display rules

- Numeric values are **center-aligned** (`Qt.AlignCenter`).
- **0** is displayed when there are no linked repairs.
- Column headers use `ResizeToContents` so sorting (via the existing
  `QTableWidget` sorting) keeps working for the whole table.

### Files changed

- `services/customer_stats_service.py` (new) — statistics computation.
- `ui/customer_view.py` — added 3 columns, header resize modes, stats
  rendering with center alignment, shifted email/city/created_at/edit indices.
- `app.py` — import stats service, `refresh_customer_table` computes stats,
  `_refresh_customer_table_if_visible()` called after repair mutations.

---

## 2. Startup Notifications Screen

The `NotificationDialog` (shown at startup when there are repair reminders)
was improved visually.

### Requirements met

- **Reduced vertical spacing** between task lines: layout spacing reduced
  to 3px, frame padding to `4px 8px`, margins to `1px`.
- **Professional, compact layout**: frames use a light card style
  (`#F9FAFB` background, `1px solid #E5E7EB` border, 4px radius).
- **Scrollable when more than 5 items**: a `QScrollArea` wraps the
  notification list. The window height is sized to show ~5 items; extra
  items are reached via the vertical scrollbar.
- **Reasonable size on small displays**: window height capped at 500px,
  minimum 300px, width 500px.
- **Existing functionality preserved**: same `notifications` list input,
  same close button, same modal behavior and loading logic
  (`check_notifications` in `LaptopRepairManager`).
- **QScrollArea used** as the scrolling widget, with
  `setWidgetResizable(True)` and horizontal scrollbar disabled.
- **RTL preserved**: `setLayoutDirection(Qt.RightToLeft)` on the dialog
  and the scroll container; labels are RTL with word wrap.
- **Long text wraps** instead of overflowing horizontally
  (`setWordWrap(True)` on each message label, horizontal scrollbar off).

### Suggested behavior

- The first five items are shown without requiring scrolling.
- Additional items are reachable via the scrollbar.
- Long text wraps within the frame width.

### Files changed

- `app.py` — `NotificationDialog` rewritten, `QScrollArea` added to imports.

---

## Verification

- `python -m py_compile app.py` — passes.
- `python app.py` — launches successfully.
- Customers table shows the three new statistics columns.
- Creating a repair increases تعداد کل سفارشات for the linked customer.
- Changing a repair to delivered (تحویل داده شده / تعمیر شده) updates
  تحویل شده and در دست انجام.
- Deleting a repair updates all counters.
- Startup notifications screen becomes scrollable when more than five items.
- Spacing between task lines is noticeably reduced.

---

## What was NOT changed

- Invoice logic (invoice_generator, invoice_exporter, invoice_widget).
- Customer workflow (CustomerWorkflow / CustomerService).
- Database schema.
- UI appearance beyond the two requested areas.
- Persian RTL styling.
