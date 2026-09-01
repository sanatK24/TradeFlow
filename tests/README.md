# TradeFlow Test Automation Suite

> Comprehensive three-tier test pyramid covering **Unit Tests**, **API Integration Tests**, and **End-to-End UI Tests** for the TradeFlow electronic bond trading simulator.

---

## Test Architecture

```
┌─────────────────────────────────────────┐
│        Load Tests (Locust)              │
│    Concurrency & Performance Testing    │
├─────────────────────────────────────────┤
│          E2E UI Tests (Playwright)      │  ← 17 tests
│        Full browser-based flows         │
├─────────────────────────────────────────┤
│    Contract Tests (requests+Pydantic)   │  ← 4 tests
│     Live API schema validation          │
├─────────────────────────────────────────┤
│       API Integration Tests (pytest)    │  ← 30 tests
│    FastAPI TestClient + in-memory DB    │
├─────────────────────────────────────────┤
│         Unit Tests (pytest)             │  ← 7 tests
│   Bond math, matching engine logic      │
└─────────────────────────────────────────┘
```

| Tier | Framework | Scope | Isolation |
|------|-----------|-------|-----------|
| **Unit** | pytest | Matching engine, bond math | In-memory SQLite |
| **API** | pytest + FastAPI TestClient | All REST endpoints | File-based SQLite (test_tradeflow.db) |
| **Contract** | pytest + requests + Pydantic | API Response JSON schemas | Live dev server |
| **E2E** | Playwright + pytest | Full UI user flows | Live dev server |
| **Load** | Locust | Endpoint scalability | Live dev server |

---

## Test Coverage Summary

### API Endpoint Coverage

| Endpoint | Method | Test File | Tests |
|----------|--------|-----------|-------|
| `/api/v1/auth/register` | POST | `test_auth.py` | register_success, register_duplicate |
| `/api/v1/auth/token` | POST | `test_auth.py` | login_success, login_wrong_password, login_nonexistent |
| `/api/v1/auth/me` | GET | `test_auth.py` | get_me_authenticated, no_token, invalid_token |
| `/api/v1/bonds/` | GET | `test_bonds.py` | get_all_bonds |
| `/api/v1/bonds/{id}` | GET | `test_bonds.py` | get_single_bond, not_found |
| `/api/v1/bonds/{id}/order-book` | GET | `test_bonds.py` | get_order_book |
| `/api/v1/orders/` | POST | `test_orders.py` | create_limit_buy, create_limit_sell, invalid_bond |
| `/api/v1/orders/` | GET | `test_orders.py` | get_orders, filter_by_status |
| `/api/v1/orders/open` | GET | `test_orders.py` | get_open_orders |
| `/api/v1/orders/{id}/cancel` | POST | `test_orders.py` | cancel_order |
| `/api/v1/rfqs/` | POST | `test_rfqs.py` | create_client_rfq |
| `/api/v1/rfqs/` | GET | `test_rfqs.py` | get_client_rfqs |
| `/api/v1/rfqs/{id}` | GET | `test_rfqs.py` | get_rfq_details |
| `/api/v1/rfqs/incoming` | GET | `test_rfqs.py` | get_incoming_rfqs |
| `/api/v1/rfqs/incoming/history` | GET | `test_rfqs.py` | get_incoming_rfqs_history |
| `/api/v1/trades/` | GET | `test_trades.py` | get_trades_empty, after_order_fill, response_schema |
| `/api/v1/analytics/` | GET | `test_analytics.py` | get_analytics, yield_curve_sorted, schema_types |

### UI Flow Coverage

| User Flow | Test File | Tests |
|-----------|-----------|-------|
| Register new trader | `test_auth_flow.py` | register_new_trader |
| Login with credentials | `test_auth_flow.py` | login_valid, login_wrong_password |
| Logout | `test_auth_flow.py` | logout |
| Toggle auth forms | `test_auth_flow.py` | toggle_auth_forms |
| Order book rendering | `test_order_flow.py` | order_book_renders |
| Place limit order | `test_order_flow.py` | place_limit_buy |
| Place market order | `test_order_flow.py` | place_market_order |
| Click order book row | `test_order_flow.py` | click_orderbook_populates |
| RFQ client broadcast | `test_rfq_flow.py` | rfq_client_broadcast |
| RFQ dealer view | `test_rfq_flow.py` | rfq_dealer_view |
| RFQ dealer quote | `test_rfq_flow.py` | rfq_dealer_quote |
| Blotter table | `test_blotter_flow.py` | blotter_table_renders |
| Blotter filters | `test_blotter_flow.py` | blotter_filters |
| Blotter export | `test_blotter_flow.py` | blotter_export_csv |
| Analytics dashboard | `test_analytics_flow.py` | analytics_renders |
| Analytics KPIs | `test_analytics_flow.py` | analytics_kpi_cards |

### Unit Test Coverage

| Module | Function | Tests |
|--------|----------|-------|
| `market_data_simulator` | `calculate_ytm()` | ytm_at_par, ytm_discount, ytm_premium |
| `market_data_simulator` | `calculate_bond_price()` | price_at_par, inverse_relationship |
| `matching_engine` | `process_order()` | insufficient_funds, short_sell_limit |

---

## How to Run Tests

### Prerequisites

```bash
# Install test dependencies (from project root)
pip install -r backend/requirements.txt
pip install -r requirements-test.txt

# For E2E tests, also install Playwright browsers
playwright install chromium
```

### Run All Tests

```bash
pytest
```

### Run by Tier

```bash
# Unit tests only
pytest tests/unit/ -v -m unit

# API integration tests only
pytest tests/api/ -v -m api

# Contract API validation (requires live backend)
pytest tests/contract/ -v -m contract

# E2E UI tests only (requires live servers running)
pytest tests/e2e/ -v -m e2e
```

### Run Load Tests

```bash
# Start Locust UI
locust -f load_tests/locustfile.py

# Then open http://localhost:8089 in your browser
```

### Run with Coverage

```bash
# API tests with coverage report
pytest tests/api/ -v --cov=backend/app --cov-report=term-missing --cov-report=html:coverage-report

# Open the HTML report
start coverage-report/index.html   # Windows
open coverage-report/index.html    # macOS
```

### Run E2E Tests Locally

E2E tests require both backend and frontend servers to be running:

```powershell
# Terminal 1: Start backend
cd TradeFlow
.\backend\venv\Scripts\python.exe -m uvicorn backend.app.main:app --port 8001

# Terminal 2: Start frontend
cd TradeFlow\frontend
npm run dev

# Terminal 3: Run E2E tests
cd TradeFlow
pytest tests/e2e/ -v -m e2e
```

---

## CI/CD Pipeline

The GitHub Actions workflow (`.github/workflows/ci.yml`) runs automatically on every **push** and **pull request** to `main`, `master`, or `develop` branches.

### Pipeline Jobs

| Job | Description | Trigger |
|-----|-------------|---------|
| `unit-tests` | Bond math & matching engine tests | Every push/PR |
| `api-tests` | All endpoint integration tests + coverage | Every push/PR |
| `e2e-tests` | Playwright browser tests against live stack | Every push/PR |

### Artifacts

- **Coverage Report** (HTML) — uploaded after API tests
- **Coverage XML** — uploaded for CI integrations
- **Playwright Traces** — uploaded on E2E test failure for debugging

---

## Test Data Strategy

### API Tests
- Each test function gets a **fresh database** via the `test_db` fixture
- The database is seeded with:
  - 7 bond instruments (4 Treasuries + 3 Corporates)
  - System market-maker bot (user id=0, `STREET_LIQUIDITY`)
- Test users are created per-test to avoid state leakage
- Background simulators (market data, settlement, RFQ manager) are **NOT** started during API tests

### E2E Tests
- Tests run against a **live dev server** stack
- Each test creates a unique user with a timestamped username
- Tests are independent and can run in any order

### Unit Tests
- Uses a fully **in-memory SQLite** database (`:memory:`)
- Minimal seed data (one bond, one trader)
- Tests the matching engine and bond math in complete isolation

---

## Directory Structure

```
tests/
├── README.md                    # This file
├── conftest.py                  # Shared fixtures (test DB, TestClient, auth)
├── api/
│   ├── __init__.py
│   ├── test_auth.py             # 8 tests — Auth endpoints
│   ├── test_bonds.py            # 4 tests — Bond endpoints
│   ├── test_orders.py           # 7 tests — Order endpoints
│   ├── test_rfqs.py             # 5 tests — RFQ endpoints
│   ├── test_trades.py           # 3 tests — Trade blotter endpoints
│   └── test_analytics.py        # 3 tests — Analytics endpoints
├── e2e/
│   ├── __init__.py
│   ├── conftest.py              # E2E fixtures (register_and_login helper)
│   ├── test_auth_flow.py        # 5 tests — Auth UI flows
│   ├── test_order_flow.py       # 4 tests — Order placement flows
│   ├── test_rfq_flow.py         # 3 tests — RFQ workflow flows
│   ├── test_blotter_flow.py     # 3 tests — Blotter UI flows
│   └── test_analytics_flow.py   # 2 tests — Analytics dashboard flows
└── unit/
    ├── __init__.py
    └── test_trading.py          # 7 tests — Bond math + matching engine
```
