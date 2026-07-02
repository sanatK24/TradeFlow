import React, { useState, useEffect } from "react";
import { useWebSocket } from "../context/WebSocketContext";
import { Search, Download, ShieldCheck, XOctagon, RefreshCw } from "lucide-react";

// Helper component to render progress bars for active settlements
const SettlementProgressBar = ({ status }) => {
  let width = "0%";
  let className = "";
  
  if (status === "EXECUTED") {
    width = "10%";
  } else if (status === "CLEARED") {
    width = "50%";
  } else if (status === "SETTLED" || status === "FAILED") {
    width = "100%";
  }

  return (
    <div className="settlement-progress-container" style={{ width: "100%" }}>
      <div 
        className={`settlement-progress-bar ${status === "SETTLED" ? "settled" : (status === "FAILED" ? "failed" : "")}`} 
        style={{ width: width }}
      />
    </div>
  );
};

const TradeBlotter = () => {
  const { subscribe } = useWebSocket();
  const [trades, setTrades] = useState([]);
  const [loading, setLoading] = useState(false);
  
  // Search & Filters
  const [search, setSearch] = useState("");
  const [sideFilter, setSideFilter] = useState("ALL");
  const [statusFilter, setStatusFilter] = useState("ALL");

  const fetchTrades = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem("token");
      const res = await fetch("http://localhost:8000/api/v1/trades/", {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setTrades(data);
      }
    } catch (err) {
      console.error("Error fetching trades:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTrades();

    // Subscribe to WS updates for trades settlement
    const unsubscribe = subscribe("trade_settlement_update", (update) => {
      setTrades((prevTrades) => {
        return prevTrades.map((t) => {
          if (t.id === update.trade_id) {
            return {
              ...t,
              settlement_status: update.status,
              settled_at: update.status === "SETTLED" || update.status === "FAILED" ? update.timestamp : t.settled_at
            };
          }
          return t;
        });
      });
    });

    const unsubscribeBlotter = subscribe("blotter_update", (data) => {
      // Trigger a soft refresh if a new trade enters the system
      fetchTrades();
    });

    return () => {
      unsubscribe();
      unsubscribeBlotter();
    };
  }, [subscribe]);

  // Export to CSV
  const handleExportCSV = () => {
    if (trades.length === 0) return;
    
    const headers = ["Trade ID", "Bond", "Side", "Price (%)", "Size", "Principal ($)", "Buyer", "Seller", "Status", "Executed At"];
    const rows = filteredTrades.map((t) => [
      t.id,
      t.bond_ticker,
      t.side,
      t.price.toFixed(3),
      t.quantity,
      t.principal.toFixed(2),
      t.buyer_name,
      t.seller_name,
      t.settlement_status,
      new Date(t.executed_at).toLocaleString()
    ]);

    const csvContent = [headers, ...rows].map(e => e.join(",")).join("\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", `TradeBlotter_${new Date().toISOString().slice(0,10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const formatCurrency = (val) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      maximumFractionDigits: 2
    }).format(val);
  };

  const formatSize = (qty) => {
    return `${(qty / 1000).toFixed(1)}M`;
  };

  // Filtering Logic
  const filteredTrades = trades.filter((t) => {
    const matchesSearch = t.bond_ticker.toLowerCase().includes(search.toLowerCase()) ||
                          t.bond_name.toLowerCase().includes(search.toLowerCase()) ||
                          t.buyer_name.toLowerCase().includes(search.toLowerCase()) ||
                          t.seller_name.toLowerCase().includes(search.toLowerCase());
    const matchesSide = sideFilter === "ALL" || t.side === sideFilter;
    const matchesStatus = statusFilter === "ALL" || t.settlement_status === statusFilter;
    
    return matchesSearch && matchesSide && matchesStatus;
  });

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
      {/* Top Banner */}
      <div className="page-title">
        <span>Desk Trade Blotter</span>
        <div style={{ display: "flex", gap: "10px" }}>
          <button className="btn btn-secondary" onClick={fetchTrades} style={{ padding: "8px" }}>
            <RefreshCw size={16} />
          </button>
          <button className="btn btn-secondary" onClick={handleExportCSV} disabled={trades.length === 0}>
            <Download size={16} />
            <span>Export CSV</span>
          </button>
        </div>
      </div>

      {/* Filter Panel */}
      <div className="glass-panel" style={{ padding: "16px", marginBottom: "20px", display: "flex", gap: "16px", flexWrap: "wrap", alignItems: "center", background: "rgba(10, 15, 30, 0.45)" }}>
        {/* Search */}
        <div style={{ flex: 2, minWidth: "200px", position: "relative", display: "flex", alignItems: "center" }}>
          <Search size={16} style={{ position: "absolute", left: "12px", color: "var(--text-muted)" }} />
          <input
            type="text"
            className="form-control"
            style={{ width: "100%", paddingLeft: "36px" }}
            placeholder="Search by ticker, security, or client name..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        {/* Side Filter */}
        <div style={{ flex: 1, minWidth: "120px" }}>
          <select className="form-control" style={{ width: "100%" }} value={sideFilter} onChange={(e) => setSideFilter(e.target.value)}>
            <option value="ALL">ALL SIDES</option>
            <option value="BUY">BUY</option>
            <option value="SELL">SELL</option>
          </select>
        </div>

        {/* Status Filter */}
        <div style={{ flex: 1, minWidth: "140px" }}>
          <select className="form-control" style={{ width: "100%" }} value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="ALL">ALL SETTLEMENTS</option>
            <option value="EXECUTED">EXECUTED</option>
            <option value="CLEARED">CLEARED</option>
            <option value="SETTLED">SETTLED</option>
            <option value="FAILED">FAILED</option>
          </select>
        </div>
      </div>

      {/* Grid List */}
      <div className="glass-panel" style={{ flex: 1, overflowX: "auto", borderBottom: "none" }}>
        {loading ? (
          <div style={{ padding: "40px", textAlign: "center", color: "var(--text-muted)" }}>Loading trade records...</div>
        ) : filteredTrades.length === 0 ? (
          <div style={{ padding: "40px", textAlign: "center", color: "var(--text-muted)" }}>No matching trades found in current session.</div>
        ) : (
          <table className="trading-table">
            <thead>
              <tr>
                <th>Trade ID</th>
                <th>Timestamp</th>
                <th>Security</th>
                <th>Side</th>
                <th>Price (%)</th>
                <th>Quantity</th>
                <th>Principal ($)</th>
                <th>Counterparty</th>
                <th>Settlement</th>
              </tr>
            </thead>
            <tbody>
              {filteredTrades.map((trade) => {
                const isBuy = trade.side === "BUY";
                const isSettled = trade.settlement_status === "SETTLED";
                const isFailed = trade.settlement_status === "FAILED";
                const counterpartyName = isBuy ? trade.seller_name : trade.buyer_name;
                
                return (
                  <tr key={trade.id}>
                    <td style={{ fontFamily: "monospace", color: "var(--text-muted)" }}>#{trade.id}</td>
                    <td style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
                      {new Date(trade.executed_at).toLocaleString()}
                    </td>
                    <td>
                      <div style={{ fontWeight: 600 }}>{trade.bond_ticker}</div>
                      <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", maxWidth: "120px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {trade.bond_name}
                      </div>
                    </td>
                    <td style={{ fontWeight: 700, color: isBuy ? "var(--bid)" : "var(--ask)" }}>{trade.side}</td>
                    <td style={{ fontFamily: "monospace", fontWeight: 600 }}>{trade.price.toFixed(3)}</td>
                    <td style={{ fontFamily: "monospace" }}>{formatSize(trade.quantity)}</td>
                    <td style={{ fontFamily: "monospace", fontWeight: 600 }}>
                      {formatCurrency(trade.principal).replace("$", "")}
                    </td>
                    <td style={{ fontSize: "0.85rem", fontWeight: 500, color: "var(--text-secondary)" }}>
                      {counterpartyName}
                    </td>
                    <td style={{ width: "160px" }}>
                      <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                          <span className={`status-badge ${trade.settlement_status.toLowerCase()}`} style={{ padding: "2px 6px", fontSize: "0.65rem" }}>
                            {trade.settlement_status}
                          </span>
                          {isSettled && <ShieldCheck size={14} style={{ color: "var(--success)" }} />}
                          {isFailed && <XOctagon size={14} style={{ color: "var(--danger)" }} />}
                        </div>
                        {trade.settlement_status !== "SETTLED" && trade.settlement_status !== "FAILED" && (
                          <SettlementProgressBar status={trade.settlement_status} />
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};

export default TradeBlotter;
