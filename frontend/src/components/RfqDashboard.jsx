import React, { useState, useEffect } from "react";
import { useWebSocket } from "../context/WebSocketContext";
import { Send, Check, AlertTriangle, Clock, RefreshCw } from "lucide-react";

// Helper component for ticking countdown timers
const TimerBadge = ({ expiresAt, onExpire }) => {
  const [secondsLeft, setSecondsLeft] = useState(0);

  useEffect(() => {
    const calculateTime = () => {
      const diff = new Date(expiresAt) - new Date();
      const secs = Math.max(0, Math.round(diff / 1000));
      setSecondsLeft(secs);
      if (secs <= 0 && onExpire) {
        onExpire();
      }
    };

    calculateTime();
    const interval = setInterval(calculateTime, 1000);
    return () => clearInterval(interval);
  }, [expiresAt]);

  const isUrgent = secondsLeft <= 5;

  return (
    <span 
      className={`status-badge ${isUrgent ? "rfq-urgent" : ""}`} 
      style={{ 
        background: isUrgent ? "rgba(239, 68, 68, 0.15)" : "rgba(255, 255, 255, 0.08)", 
        color: isUrgent ? "var(--ask)" : "var(--text-secondary)",
        borderColor: isUrgent ? "var(--ask)" : "transparent",
        display: "inline-flex",
        alignItems: "center",
        gap: "4px"
      }}
    >
      <Clock size={12} />
      {secondsLeft}s
    </span>
  );
};

const RfqDashboard = ({ bonds, activeRole, onTradeExecuted }) => {
  const { subscribe } = useWebSocket();
  const [clientRfqs, setClientRfqs] = useState([]);
  const [incomingRfqs, setIncomingRfqs] = useState([]);
  const [selectedRfqId, setSelectedRfqId] = useState(null);
  
  // Forms
  const [bondId, setBondId] = useState("");
  const [side, setSide] = useState("BUY");
  const [quantity, setQuantity] = useState("5000");
  const [priceInput, setPriceInput] = useState("");
  
  const [loading, setLoading] = useState(false);
  const [rfqMessage, setRfqMessage] = useState(null);
  
  // Status states
  const [quotedDealerId, setQuotedDealerId] = useState(null); // which dealer we quoted for
  const [quoteMessage, setQuoteMessage] = useState(null); // message during dealer quote submission
  
  // Sound/Alert triggers
  const [newRfqAlert, setNewRfqAlert] = useState(false);

  // Sync / Fetch client RFQs (Client Mode) and active incoming RFQs (Dealer Mode)
  const fetchClientRfqs = async () => {
    try {
      const token = localStorage.getItem("token");
      const res = await fetch("http://localhost:8001/api/v1/rfqs/", {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setClientRfqs(data);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const fetchIncomingRfqs = async () => {
    try {
      const token = localStorage.getItem("token");
      const res = await fetch("http://localhost:8001/api/v1/rfqs/incoming", {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setIncomingRfqs(data);
      }
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    if (bonds.length > 0 && !bondId) {
      setBondId(bonds[0].id.toString());
    }
  }, [bonds]);

  useEffect(() => {
    fetchClientRfqs();
    fetchIncomingRfqs();

    // WS subscriptions
    // 1. Client Mode: quotes arrived
    const unsubscribeQuotes = subscribe("rfq_quotes_received", (data) => {
      fetchClientRfqs();
    });

    // 2. Dealer Mode: incoming RFQ alert
    const unsubscribeIncoming = subscribe("incoming_rfq_alert", (data) => {
      fetchIncomingRfqs();
      setNewRfqAlert(true);
      setTimeout(() => setNewRfqAlert(false), 5000);
    });

    // 3. Dealer Mode: quote won / rejected
    const unsubscribeOutcome = subscribe("rfq_accepted", (data) => {
      fetchIncomingRfqs();
      fetchClientRfqs();
      if (onTradeExecuted) onTradeExecuted();
    });

    const unsubscribeRejected = subscribe("rfq_rejected", (data) => {
      fetchIncomingRfqs();
      fetchClientRfqs();
    });

    const unsubscribeExpired = subscribe("rfq_expired", (data) => {
      fetchIncomingRfqs();
      fetchClientRfqs();
    });

    return () => {
      unsubscribeQuotes();
      unsubscribeIncoming();
      unsubscribeOutcome();
      unsubscribeRejected();
      unsubscribeExpired();
    };
  }, [subscribe, onTradeExecuted]);

  // Handle Client RFQ submission
  const handleClientRfqSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setRfqMessage(null);

    const token = localStorage.getItem("token");
    try {
      const res = await fetch("http://localhost:8001/api/v1/rfqs/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          bond_id: parseInt(bondId),
          side: side,
          quantity: parseInt(quantity)
        })
      });

      if (res.ok) {
        setRfqMessage({ type: "success", text: "RFQ Broadcasted. Awaiting Dealer Pricing..." });
        fetchClientRfqs();
      } else {
        const data = await res.json();
        setRfqMessage({ type: "error", text: data.detail || "Failed to submit RFQ" });
      }
    } catch (err) {
      setRfqMessage({ type: "error", text: "Network error submitting RFQ" });
    } finally {
      setLoading(false);
    }
  };

  // Handle Client accepting a quote
  const handleAcceptQuote = async (rfqId, quoteId) => {
    const token = localStorage.getItem("token");
    try {
      const res = await fetch(`http://localhost:8001/api/v1/rfqs/${rfqId}/accept`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ quote_id: quoteId })
      });

      if (res.ok) {
        fetchClientRfqs();
        if (onTradeExecuted) onTradeExecuted();
      } else {
        const data = await res.json();
        alert(data.detail || "Failed to accept quote");
      }
    } catch (err) {
      console.error(err);
    }
  };

  // Handle Dealer submitting quote (Dealer Mode)
  const handleDealerQuoteSubmit = async (e, rfqId) => {
    e.preventDefault();
    setQuoteMessage(null);
    const token = localStorage.getItem("token");

    try {
      const res = await fetch(`http://localhost:8001/api/v1/rfqs/${rfqId}/quote`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ price: parseFloat(priceInput) })
      });

      if (res.ok) {
        setQuoteMessage({ type: "success", text: "Quote submitted. Awaiting client decision..." });
        setQuotedDealerId(rfqId);
        setPriceInput("");
        fetchIncomingRfqs();
      } else {
        const data = await res.json();
        setQuoteMessage({ type: "error", text: data.detail || "Failed to submit quote" });
      }
    } catch (err) {
      setQuoteMessage({ type: "error", text: "Network error submitting quote" });
    }
  };

  const formatCurrency = (val) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      maximumFractionDigits: 0
    }).format(val);
  };

  const formatSize = (qty) => {
    return `${(qty / 1000).toFixed(1)}M`;
  };

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
      {/* Top Roles Banner */}
      <div className="page-title">
        <span>Request For Quote Dashboard</span>
        <div style={{ fontSize: "0.85rem", padding: "4px 12px", borderRadius: "10px", background: "rgba(255,255,255,0.06)", border: "1px solid var(--surface-border)" }}>
          Active Role: <strong style={{ color: "var(--primary)", textTransform: "uppercase" }}>{activeRole} Mode</strong>
        </div>
      </div>

      {newRfqAlert && (
        <div className="glass-panel rfq-alert-card" style={{ padding: "12px 18px", marginBottom: "16px", background: "rgba(245, 158, 11, 0.1)", display: "flex", alignItems: "center", gap: "10px" }}>
          <AlertTriangle style={{ color: "var(--warning)" }} />
          <div>
            <strong>Incoming RFQ Alert!</strong> Institutional client requested quotes. Switch to <strong>Dealer Desk</strong> to price it!
          </div>
        </div>
      )}

      {/* RENDER BASED ON ACTIVE ROLE */}
      {activeRole === "client" ? (
        /* ==================== CLIENT DESK ==================== */
        <div className="dashboard-grid">
          {/* RFQ Form Ticket */}
          <div className="glass-panel" style={{ padding: "20px" }}>
            <h3 style={{ fontSize: "1.1rem", textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--text-secondary)", marginBottom: "16px" }}>
              Request Quotes Ticket
            </h3>
            
            <form onSubmit={handleClientRfqSubmit} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
              <div style={{ display: "flex", gap: "12px" }}>
                {/* Side Selector */}
                <div style={{ flex: 1, display: "flex", borderRadius: "8px", overflow: "hidden", border: "1px solid var(--surface-border)", height: "42px" }}>
                  <button
                    type="button"
                    onClick={() => setSide("BUY")}
                    style={{
                      flex: 1,
                      background: side === "BUY" ? "var(--bid)" : "transparent",
                      color: side === "BUY" ? "white" : "var(--text-muted)",
                      border: "none",
                      cursor: "pointer",
                      fontWeight: 700
                    }}
                  >
                    BUY
                  </button>
                  <button
                    type="button"
                    onClick={() => setSide("SELL")}
                    style={{
                      flex: 1,
                      background: side === "SELL" ? "var(--ask)" : "transparent",
                      color: side === "SELL" ? "white" : "var(--text-muted)",
                      border: "none",
                      cursor: "pointer",
                      fontWeight: 700
                    }}
                  >
                    SELL
                  </button>
                </div>

                {/* Bond Dropdown */}
                <div className="form-group" style={{ flex: 1.5, marginBottom: 0 }}>
                  <select
                    className="form-control"
                    value={bondId}
                    onChange={(e) => setBondId(e.target.value)}
                    style={{ height: "42px" }}
                  >
                    {bonds.map((b) => (
                      <option key={b.id} value={b.id}>
                        {b.ticker} - {b.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Quantity input */}
              <div className="form-group">
                <label>Size / Quantity (contracts)</label>
                <input
                  type="number"
                  className="form-control"
                  value={quantity}
                  onChange={(e) => setQuantity(e.target.value)}
                  placeholder="e.g. 5000"
                  required
                />
                <div style={{ display: "flex", gap: "6px", marginTop: "6px" }}>
                  <button type="button" className="btn btn-secondary" style={{ padding: "4px 8px", fontSize: "0.75rem" }} onClick={() => setQuantity("2000")}>
                    2,000 ($2M par)
                  </button>
                  <button type="button" className="btn btn-secondary" style={{ padding: "4px 8px", fontSize: "0.75rem" }} onClick={() => setQuantity("5000")}>
                    5,000 ($5M par)
                  </button>
                  <button type="button" className="btn btn-secondary" style={{ padding: "4px 8px", fontSize: "0.75rem" }} onClick={() => setQuantity("10000")}>
                    10,000 ($10M par)
                  </button>
                </div>
              </div>

              {rfqMessage && (
                <div style={{
                  padding: "10px",
                  borderRadius: "6px",
                  fontSize: "0.85rem",
                  background: rfqMessage.type === "success" ? "rgba(16, 185, 129, 0.15)" : "rgba(239, 68, 68, 0.15)",
                  color: rfqMessage.type === "success" ? "var(--bid)" : "var(--ask)"
                }}>
                  {rfqMessage.text}
                </div>
              )}

              <button type="submit" className="btn btn-primary" style={{ justifyContent: "center", padding: "12px" }} disabled={loading}>
                <Send size={16} />
                <span>{loading ? "Transmitting..." : "Broadcast RFQ to Street"}</span>
              </button>
            </form>
          </div>

          {/* Active Quotes Panel */}
          <div className="glass-panel" style={{ padding: "20px", display: "flex", flexDirection: "column", maxHeight: "400px" }}>
            <h3 style={{ fontSize: "1.1rem", textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--text-secondary)", marginBottom: "16px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span>Ticking Quotes</span>
              <button className="btn btn-secondary" style={{ padding: "4px 8px" }} onClick={fetchClientRfqs}>
                <RefreshCw size={12} />
              </button>
            </h3>

            <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: "12px" }}>
              {clientRfqs.length === 0 && (
                <div style={{ textAlign: "center", color: "var(--text-muted)", marginTop: "40px" }}>
                  No active RFQs. Submit one on the left!
                </div>
              )}

              {clientRfqs.slice(0, 10).map((rfq) => (
                <div key={rfq.id} className="glass-panel" style={{ padding: "14px", borderLeft: `3px solid ${rfq.side === "BUY" ? "var(--bid)" : "var(--ask)"}` }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                    <div>
                      <strong style={{ color: "var(--text-primary)", fontSize: "1rem" }}>{rfq.bond.ticker}</strong>
                      <span style={{ margin: "0 8px", fontSize: "0.85rem", color: rfq.side === "BUY" ? "var(--bid)" : "var(--ask)" }}>
                        {rfq.side}
                      </span>
                      <span style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
                        {formatSize(rfq.quantity)} ($Par)
                      </span>
                    </div>
                    <div>
                      {rfq.status === "REQUESTED" && (
                        <span className="status-badge requested">broadcasting...</span>
                      )}
                      {rfq.status === "QUOTED" && (
                        <TimerBadge expiresAt={rfq.expires_at} onExpire={fetchClientRfqs} />
                      )}
                      {rfq.status === "ACCEPTED" && (
                        <span className="status-badge settled" style={{ border: "none" }}>ACCEPTED</span>
                      )}
                      {rfq.status === "REJECTED" && (
                        <span className="status-badge failed">REJECTED</span>
                      )}
                      {rfq.status === "EXPIRED" && (
                        <span className="status-badge failed">EXPIRED</span>
                      )}
                    </div>
                  </div>

                  {/* Quotes List inside RFQ */}
                  {rfq.status === "QUOTED" && rfq.quotes && (
                    <div style={{ marginTop: "10px", display: "flex", flexDirection: "column", gap: "8px" }}>
                      {rfq.quotes.map((quote) => (
                        <div key={quote.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", background: "rgba(255,255,255,0.03)", padding: "6px 12px", borderRadius: "6px" }}>
                          <div>
                            <span style={{ fontSize: "0.85rem", fontWeight: 600 }}>{quote.dealer_name}</span>
                            <span style={{ marginLeft: "8px", fontSize: "0.75rem", color: "var(--text-muted)" }}>
                              YTM: {quote.yield_pct.toFixed(3)}%
                            </span>
                          </div>
                          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                            <span style={{ fontFamily: "monospace", fontWeight: 700, color: "var(--primary)" }}>
                              {quote.price.toFixed(3)}
                            </span>
                            <button
                              className="btn btn-primary"
                              style={{ padding: "4px 8px", fontSize: "0.75rem" }}
                              onClick={() => handleAcceptQuote(rfq.id, quote.id)}
                            >
                              Accept
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {rfq.status === "ACCEPTED" && (
                    <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: "4px" }}>
                      Executed at price: {rfq.quotes.find(q => q.id)?.price || "N/A"}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      ) : (
        /* ==================== DEALER DESK ==================== */
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h3 style={{ fontSize: "1.1rem", textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--text-secondary)" }}>
              Incoming Client RFQs
            </h3>
            <button className="btn btn-secondary" style={{ padding: "4px 8px" }} onClick={fetchIncomingRfqs}>
              <RefreshCw size={12} />
            </button>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))", gap: "20px" }}>
            {incomingRfqs.length === 0 && (
              <div className="glass-panel" style={{ gridColumn: "1/-1", padding: "40px", textAlign: "center", color: "var(--text-muted)" }}>
                Waiting for incoming client RFQs... (a client will request a quote every 25 seconds)
              </div>
            )}

            {incomingRfqs.map((rfq) => {
              const isUserQuoted = quotedDealerId === rfq.id;
              
              return (
                <div 
                  key={rfq.id} 
                  className={`glass-panel ${!isUserQuoted ? "rfq-alert-card" : ""}`} 
                  style={{ padding: "20px", display: "flex", flexDirection: "column", gap: "12px", background: "rgba(16, 20, 48, 0.6)" }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <div>
                      <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase" }}>Client</span>
                      <div style={{ fontWeight: 700, fontSize: "1.1rem", color: "var(--text-primary)" }}>
                        {INSTITUTIONAL_CLIENTS[rfq.id % INSTITUTIONAL_CLIENTS.length]}
                      </div>
                    </div>
                    <div>
                      <TimerBadge expiresAt={rfq.expires_at} onExpire={fetchIncomingRfqs} />
                    </div>
                  </div>

                  <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 12px", background: "rgba(0,0,0,0.15)", borderRadius: "6px" }}>
                    <div>
                      <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase" }}>Security</span>
                      <div style={{ fontWeight: 600 }}>{rfq.bond.ticker}</div>
                    </div>
                    <div>
                      <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase" }}>Side</span>
                      <div style={{ fontWeight: 700, color: rfq.side === "BUY" ? "var(--bid)" : "var(--ask)" }}>
                        {rfq.side === "BUY" ? "BUY (You Sell)" : "SELL (You Buy)"}
                      </div>
                    </div>
                    <div>
                      <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase" }}>Size</span>
                      <div style={{ fontWeight: 600 }}>{formatSize(rfq.quantity)}</div>
                    </div>
                  </div>

                  {isUserQuoted ? (
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "8px", padding: "12px", background: "rgba(16, 185, 129, 0.1)", border: "1px solid rgba(16, 185, 129, 0.3)", borderRadius: "8px", color: "var(--bid)", fontSize: "0.9rem", fontWeight: 600 }}>
                      <Check size={16} />
                      Quote submitted. Awaiting client decision.
                    </div>
                  ) : (
                    <form onSubmit={(e) => handleDealerQuoteSubmit(e, rfq.id)} style={{ display: "flex", gap: "10px", marginTop: "4px" }}>
                      <div style={{ flex: 1, position: "relative", display: "flex", alignItems: "center" }}>
                        <input
                          type="number"
                          step="0.001"
                          className="form-control"
                          style={{ width: "100%", height: "42px", paddingRight: "30px" }}
                          placeholder={`Fair Mid: ${rfq.bond.last_price}`}
                          value={priceInput}
                          onChange={(e) => setPriceInput(e.target.value)}
                          required
                        />
                        <span style={{ position: "absolute", right: "12px", color: "var(--text-muted)", fontSize: "0.85rem" }}>
                          %
                        </span>
                      </div>
                      <button type="submit" className="btn btn-primary" style={{ padding: "0 18px", height: "42px" }}>
                        <span>Send Quote</span>
                      </button>
                    </form>
                  )}

                  {quoteMessage && quotedDealerId === rfq.id && quoteMessage.type === "error" && (
                    <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: "4px" }}>
                      {quoteMessage.text}
                    </div>
                  )}

                  <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", display: "flex", justifyContent: "space-between" }}>
                    <span>Coupon: {rfq.bond.coupon}%</span>
                    <span>Par Value: {formatCurrency(rfq.quantity * rfq.bond.face_value)}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};

export default RfqDashboard;
