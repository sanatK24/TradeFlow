# TradeFlow – Electronic Trading Simulator

TradeFlow is a real-time fixed-income electronic trading simulator that models the operations of a bond trading desk. It supports limit/market order book matching, a dual-role Request for Quote (RFQ) workflow, trade blotter tracking, fast-forward clearing/settlement pipelines, and mark-to-market performance analytics.

## 🌟 Key Features

1. **Live Level 2 Order Book**: Real-time bid/ask queues updating via WebSockets with ticking price animations, spread calculations, and depth bars.
2. **Dual-Role RFQ Workflow**:
   - **Client Mode**: Request quotes for size from Wall Street dealers. View competing ticking quotes (GS, JPMorgan) side-by-side with a 30s countdown, and accept the best price.
   - **Dealer Mode (Market Making)**: Receive RFQ alerts from institutional clients (BlackRock, PIMCO). Price the risk under a 15s deadline and compete with other dealers to win the trade.
3. **Trade Blotter & Settlement**: Live blotter showing all transactions. Settle trades in fast-forward over 12 seconds (`EXECUTED` -> `CLEARED` -> `SETTLED`). Simulates clearing house failures with automatic capital refunds.
4. **Analytics Desk**: Recharts visualizations plotting the US Treasury Yield Curve, desk trading volumes, dealer win rates, and asset portfolio distributions.
5. **Hybrid Storage System**: Config-driven automatic fallback. Uses SQLite + In-Memory Redis mock locally for zero-setup execution, and shifts to full PostgreSQL + Redis under Docker.

---

## 🚀 How to Run the Simulator

### Option A: Local Dev Launcher (Zero-Setup & Recommended)

1. Open PowerShell inside the `TradeFlow` root directory.
2. Launch both services using the PowerShell script:
   ```powershell
   .\run.ps1
   ```
   *This initializes the FastAPI python venv backend on port `8000` and the React frontend on port `5173` in separate windows, automatically launching the trading desk in your browser.*

### Option B: Docker Compose (Full PostgreSQL & Redis Stack)

1. Open a terminal in the `TradeFlow` root folder.
2. Build and spin up the container network:
   ```bash
   docker-compose up --build
   ```
3. Open `http://localhost:5173` in your browser.

---

## 📂 Project Directory Structure

```
TradeFlow/
├── backend/
│   ├── app/
│   │   ├── config.py              # Configuration & settings
│   │   ├── database.py            # SQLite/PostgreSQL connectors
│   │   ├── models.py              # Database schemas
│   │   ├── redis_client.py        # Redis connection / Mock client
│   │   ├── schemas.py             # Pydantic validation schemas
│   │   ├── main.py                # FastAPI entry & WebSockets
│   │   ├── routes/                # auth, bonds, orders, rfqs, trades, analytics
│   │   ├── services/              # matching, market sim, rfq, settlement
│   │   └── tests/                 # Unit tests (test_trading.py)
│   ├── requirements.txt           # Python library dependencies
│   └── Dockerfile                 # Backend container definition
├── frontend/
│   ├── src/
│   │   ├── context/               # WebSocketContext state
│   │   ├── components/            # Sidebar, OrderBook, OrderEntry, RfqDashboard, Blotter, Analytics
│   │   ├── App.jsx                # Main controller & authentication screens
│   │   ├── main.jsx               # React DOM mount point
│   │   └── index.css              # Custom global glassmorphic stylesheet
│   ├── index.html                 # HTML layout
│   ├── vite.config.js             # Vite configurations
│   ├── package.json               # NPM packages list
│   └── Dockerfile                 # Frontend container definition
├── docker-compose.yml             # Full docker compose file
├── run.ps1                        # PowerShell fast dev launcher script
└── README.md                      # General documentation
```

---

## 🧪 Running Automated Unit Tests

To run the matching engine and bond math unit test suite locally:

1. Open a terminal in the `TradeFlow` root folder.
2. Run:
   ```powershell
   .\backend\venv\Scripts\python.exe -m unittest backend.app.tests.test_trading
   ```
