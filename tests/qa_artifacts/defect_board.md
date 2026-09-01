# Jira / Defect Board Simulation

> This document tracks the QA -> Dev -> QA lifecycle of defects found during testing.

## Active Sprint Board

### 🔴 TO DO
*(No items)*

### 🟡 IN PROGRESS
*(No items)*

### 🔵 IN QA
*(No items)*

### 🟢 DONE
**[BUG-104] Order Entry and RFQ allow Zero and Negative Quantities** (Closed)
* **Found in**: `TC-OE-003`, `TC-OE-004`
* **Resolution**: Fixed in `schemas.py`. Added `Field(..., gt=0)` to `quantity` in both `OrderCreate` and `RfqCreate` schemas. Added regression tests `test_create_order_zero_quantity_rejected` and `test_create_order_negative_quantity_rejected` which both verify API correctly returns HTTP 422.
* **QA Sign-off**: ✅ PASS

**[TASK-101] Build E2E Playwright Suite** (Closed)
**[TASK-102] GitHub Actions Pipeline** (Closed)
**[BUG-103] Missing CORS Headers on Analytics Endpoint** (Closed)
