# Bug History

## 2026-06-04

Bug:
Repair records not shown on startup

Root Cause:
refresh_table() not called after load_repairs()

Fix:
Call refresh_table() after loading data

Status:
Fixed