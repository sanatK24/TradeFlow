# TradeFlow QA Test Cases — Order Entry Module

**Module**: Order Management  
**Component**: `POST /api/v1/orders/`  
**Test Cycle**: Sprint 4 - Core Trading Flow

| Test ID | Title | Description | Steps | Expected Result | Actual Result | Status |
|---------|-------|-------------|-------|-----------------|---------------|--------|
| **TC-OE-001** | Valid Limit Buy | Verify user can place a standard Limit BUY order | 1. Login<br>2. Select bond US10Y<br>3. Set Side=BUY, Type=LIMIT, Price=99.00, Qty=1000<br>4. Submit | Order is created with status PENDING or FILLED depending on market. | Order created successfully. | ✅ PASS |
| **TC-OE-002** | Insufficient Cash | Verify order rejected if cash is insufficient | 1. Login with $100k balance<br>2. Set Side=BUY, Qty=500000<br>3. Submit | Order status immediately moves to CANCELLED with reason "Insufficient cash". | Order cancelled as expected. | ✅ PASS |
| **TC-OE-003** | **Zero Quantity** | Verify system rejects orders with quantity 0 | 1. Login<br>2. Set Side=BUY, Price=99.00, Qty=0<br>3. Submit | API returns HTTP 422 Validation Error. | *(Retest)* API returns HTTP 422 with validation message. | ✅ PASS |
| **TC-OE-004** | **Negative Quantity** | Verify system rejects orders with negative quantities | 1. Login<br>2. Set Side=BUY, Price=99.00, Qty=-1000<br>3. Submit | API returns HTTP 422 Validation Error. | *(Retest)* API returns HTTP 422 with validation message. | ✅ PASS |
| **TC-OE-005** | Short Selling Limit | Verify user cannot short sell beyond -50,000 bonds | 1. Login<br>2. Set Side=SELL, Qty=60000<br>3. Submit | Order is CANCELLED (Short selling limit exceeded). | Order cancelled as expected. | ✅ PASS |
