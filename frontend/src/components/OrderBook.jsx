import React, { useState, useEffect, useRef } from "react";
import { useWebSocket } from "../context/WebSocketContext";
import { ArrowUp, ArrowDown } from "lucide-react";

const OrderBook = ({ bonds, selectedBond, setSelectedBond, onSelectPriceSize }) => {
  const { subscribe } = useWebSocket();
  const [bookData, setBookData] = useState(null);
  const prevPriceRef = useRef(null);
  const [tickDirection, setTickDirection] = useState(null); // 'up' | 'down' | null

  // Fetch initial order book via REST on bond switch
  useEffect(() => {
    if (!selectedBond) return;

    const fetchOrderBook = async () => {
      try {
        const token = localStorage.getItem("token");
        const res = await fetch(`http://localhost:8001/api/v1/bonds/${selectedBond.id}/order-book`, {
          headers: {
            Authorization: `Bearer ${token}`
          }
        });
        if (res.ok) {
          const data = await res.json();
          setBookData(data);
          prevPriceRef.current = data.last_price;
        }
      } catch (err) {
        console.error("Error fetching order book:", err);
      }
    };

    fetchOrderBook();

    // Subscribe to WebSocket updates for this bond
    const unsubscribe = subscribe("order_book_update", (update) => {
      if (update.bond_id === selectedBond.id) {
        setBookData((prev) => {
          if (prev) {
            if (update.last_price > prev.last_price) {
              setTickDirection("up");
            } else if (update.last_price < prev.last_price) {
              setTickDirection("down");
            }
          }
          return update;
        });
      }
    });

    return () => {
      unsubscribe();
      setTickDirection(null);
    };
  }, [selectedBond, subscribe]);

  const handleBondChange = (e) => {
    const bondId = parseInt(e.target.value);
    const bond = bonds.find((b) => b.id === bondId);
    if (bond) {
      setSelectedBond(bond);
    }
  };

  if (!selectedBond) {
    return (
      <div className="glass-panel" style={{ padding: "24px", height: "100%", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div style={{ color: "var(--text-muted)", textAlign: "center" }}>Loading bonds list...</div>
      </div>
    );
  }

  // Calculate spreads
  const bids = bookData?.bids || [];
  const asks = bookData?.asks || [];
  
  // Sort asks descending so highest ask is at top, lowest ask (best ask) is at bottom
  const sortedAsks = [...asks].sort((a, b) => b.price - a.price);
  const bestAsk = asks[0]?.price || 0.0;
  const bestBid = bids[0]?.price || 0.0;
  const spread = bestAsk && bestBid ? (bestAsk - bestBid).toFixed(3) : "0.000";

  // Calculate max sizes for depth bar calculations
  const maxBidQty = bids.reduce((max, b) => b.qty > max ? b.qty : max, 0) || 1;
  const maxAskQty = asks.reduce((max, a) => a.qty > max ? a.qty : max, 0) || 1;

  const formatSize = (qty) => {
    // Show in MM, e.g. 5,000 -> 5.0M, or 10,000 -> 10.0M
    return `${(qty / 1000).toFixed(1)}M`;
  };

  return (
    <div className="glass-panel" style={{ padding: "20px", display: "flex", flexDirection: "column", height: "100%" }}>
      {/* Header Select */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px", gap: "10px" }}>
        <h3 style={{ fontSize: "1.1rem", textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--text-secondary)" }}>
          Live Order Book
        </h3>
        
        <select 
          className="form-control" 
          value={selectedBond.id} 
          onChange={handleBondChange}
          style={{ width: "150px", padding: "6px 12px", background: "rgba(10, 12, 30, 0.6)" }}
        >
          {bonds.map((b) => (
            <option key={b.id} value={b.id}>
              {b.ticker}
            </option>
          ))}
        </select>
      </div>

      {/* Bond Specs Card */}
      <div className="glass-panel" style={{ background: "rgba(0,0,0,0.15)", padding: "12px 16px", marginBottom: "16px", display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px", fontSize: "0.8rem", border: "1px solid rgba(255,255,255,0.04)" }}>
        <div>
          <span style={{ color: "var(--text-muted)" }}>ISIN:</span>{" "}
          <span style={{ color: "var(--text-secondary)", fontWeight: 500 }}>{selectedBond.isin}</span>
        </div>
        <div>
          <span style={{ color: "var(--text-muted)" }}>Maturity:</span>{" "}
          <span style={{ color: "var(--text-secondary)", fontWeight: 500 }}>{selectedBond.maturity_date}</span>
        </div>
        <div>
          <span style={{ color: "var(--text-muted)" }}>Coupon:</span>{" "}
          <span style={{ color: "var(--text-secondary)", fontWeight: 500 }}>{selectedBond.coupon.toFixed(3)}%</span>
        </div>
        <div>
          <span style={{ color: "var(--text-muted)" }}>Type:</span>{" "}
          <span style={{ color: "var(--text-secondary)", fontWeight: 500 }}>{selectedBond.type}</span>
        </div>
      </div>

      {/* Level 2 Grid */}
      <div style={{ display: "flex", flexDirection: "column", flex: 1, justifyItems: "stretch" }}>
        
        {/* Table Column Labels */}
        <div style={{ display: "flex", justifyContent: "space-between", padding: "6px 12px", borderBottom: "1px solid var(--surface-border)", fontSize: "0.75rem", textTransform: "uppercase", color: "var(--text-muted)", fontWeight: 600, marginBottom: "8px" }}>
          <span>Size (Contracts)</span>
          <span>Price (%)</span>
        </div>

        {/* Asks (Sell Orders) */}
        <div style={{ display: "flex", flexDirection: "column", justifyContent: "flex-end" }}>
          {sortedAsks.map((ask, idx) => (
            <div 
              key={`ask-${idx}`} 
              className="orderbook-row ask"
              onClick={() => onSelectPriceSize(ask.price, ask.qty, "SELL")}
            >
              <div 
                className="orderbook-depth-bar ask" 
                style={{ width: `${(ask.qty / maxAskQty) * 100}%` }}
              />
              <span className="orderbook-qty">{formatSize(ask.qty)}</span>
              <span className="orderbook-price ask">{ask.price.toFixed(3)}</span>
            </div>
          ))}
          {sortedAsks.length === 0 && (
            <div style={{ textAlign: "center", padding: "10px", color: "var(--text-muted)", fontSize: "0.85rem" }}>
              No Sellers
            </div>
          )}
        </div>

        {/* Mid-Market / Spread Bar */}
        <div className="glass-panel" style={{ background: "rgba(10, 15, 35, 0.55)", margin: "8px 0", padding: "8px 12px", display: "flex", justifyContent: "space-between", alignItems: "center", borderLeft: "3px solid var(--primary)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span style={{ fontSize: "1.15rem", fontWeight: 700, fontFamily: "var(--font-display)" }}>
              {bookData?.last_price.toFixed(2) || "00.00"}
            </span>
            <div style={{ display: "flex", alignItems: "center" }}>
              {tickDirection === "up" && <ArrowUp size={16} className="price-tick-up" />}
              {tickDirection === "down" && <ArrowDown size={16} className="price-tick-down" />}
            </div>
            <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
              YTM: {bookData?.yield.toFixed(3) || "0.000"}%
            </span>
          </div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", textAlign: "right" }}>
            Spread: <strong style={{ color: "var(--text-secondary)" }}>{spread}</strong>
          </div>
        </div>

        {/* Bids (Buy Orders) */}
        <div style={{ display: "flex", flexDirection: "column" }}>
          {bids.map((bid, idx) => (
            <div 
              key={`bid-${idx}`} 
              className="orderbook-row bid"
              onClick={() => onSelectPriceSize(bid.price, bid.qty, "BUY")}
            >
              <div 
                className="orderbook-depth-bar bid" 
                style={{ width: `${(bid.qty / maxBidQty) * 100}%` }}
              />
              <span className="orderbook-qty">{formatSize(bid.qty)}</span>
              <span className="orderbook-price bid">{bid.price.toFixed(3)}</span>
            </div>
          ))}
          {bids.length === 0 && (
            <div style={{ textAlign: "center", padding: "10px", color: "var(--text-muted)", fontSize: "0.85rem" }}>
              No Buyers
            </div>
          )}
        </div>

      </div>
      
      {/* Help Hint */}
      <span style={{ fontSize: "0.7rem", color: "var(--text-muted)", marginTop: "12px", textAlign: "center" }}>
        *Click any row to auto-populate the order entry ticket.
      </span>
    </div>
  );
};

export default OrderBook;
