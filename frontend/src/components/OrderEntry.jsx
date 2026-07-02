import React, { useState, useEffect } from "react";

const OrderEntry = ({ selectedBond, presetPrice, presetQty, presetSide, onOrderSubmitted }) => {
  const [side, setSide] = useState("BUY"); // BUY | SELL
  const [type, setType] = useState("LIMIT"); // LIMIT | MARKET
  const [price, setPrice] = useState("100.00");
  const [quantity, setQuantity] = useState("1000");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null); // { type: 'success'|'error', text: '' }

  // Sync with presets when user clicks on order book
  useEffect(() => {
    if (presetPrice !== null) {
      setPrice(presetPrice.toFixed(3));
    }
    if (presetQty !== null) {
      setQuantity(presetQty.toString());
    }
    if (presetSide !== null) {
      setSide(presetSide);
    }
  }, [presetPrice, presetQty, presetSide]);

  // Set price to bond's last price if type changes to market or is empty
  useEffect(() => {
    if (type === "MARKET" && selectedBond) {
      setPrice(selectedBond.last_price.toFixed(3));
    }
  }, [type, selectedBond]);

  if (!selectedBond) return null;

  const handleQtyShortcut = (amount) => {
    const currentVal = parseInt(quantity) || 0;
    setQuantity((currentVal + amount).toString());
  };

  // Compute estimated principal
  const priceNum = parseFloat(price) || 0;
  const qtyNum = parseInt(quantity) || 0;
  const faceValue = selectedBond.face_value || 1000.0;
  const estimatedPrincipal = qtyNum * priceNum * (faceValue / 100.0);

  const formatCurrency = (val) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
    }).format(val);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage(null);

    const token = localStorage.getItem("token");
    if (!token) {
      setMessage({ type: "error", text: "Authentication token missing" });
      setLoading(false);
      return;
    }

    try {
      const res = await fetch("http://localhost:8000/api/v1/orders/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          bond_id: selectedBond.id,
          side: side,
          type: type,
          price: parseFloat(price),
          quantity: parseInt(quantity),
        }),
      });

      const data = await res.json();
      if (res.ok) {
        setMessage({
          type: "success",
          text: `Order submitted! Status: ${data.status} (Remaining Qty: ${data.remaining_qty})`,
        });
        if (onOrderSubmitted) {
          onOrderSubmitted();
        }
      } else {
        setMessage({ type: "error", text: data.detail || "Order submission failed" });
      }
    } catch (err) {
      console.error(err);
      setMessage({ type: "error", text: "Network error submitting order" });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="glass-panel" style={{ padding: "20px", display: "flex", flexDirection: "column", height: "100%" }}>
      <h3 style={{ fontSize: "1.1rem", textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--text-secondary)", marginBottom: "16px" }}>
        Order Entry Ticket
      </h3>

      <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "16px", flex: 1 }}>
        
        {/* Side Selection Tab-Toggles */}
        <div style={{ display: "flex", borderRadius: "8px", overflow: "hidden", border: "1px solid var(--surface-border)" }}>
          <button
            type="button"
            onClick={() => setSide("BUY")}
            style={{
              flex: 1,
              padding: "10px",
              background: side === "BUY" ? "var(--bid)" : "transparent",
              color: side === "BUY" ? "white" : "var(--text-muted)",
              border: "none",
              cursor: "pointer",
              fontFamily: "var(--font-display)",
              fontWeight: 700,
              transition: "all 0.15s"
            }}
          >
            BUY
          </button>
          <button
            type="button"
            onClick={() => setSide("SELL")}
            style={{
              flex: 1,
              padding: "10px",
              background: side === "SELL" ? "var(--ask)" : "transparent",
              color: side === "SELL" ? "white" : "var(--text-muted)",
              border: "none",
              cursor: "pointer",
              fontFamily: "var(--font-display)",
              fontWeight: 700,
              transition: "all 0.15s"
            }}
          >
            SELL
          </button>
        </div>

        {/* Order Type SELECT */}
        <div className="form-group">
          <label>Order Type</label>
          <select
            className="form-control"
            value={type}
            onChange={(e) => setType(e.target.value)}
          >
            <option value="LIMIT">LIMIT ORDER</option>
            <option value="MARKET">MARKET ORDER</option>
          </select>
        </div>

        {/* Price Input */}
        <div className="form-group">
          <label>Price (% of par)</label>
          <div style={{ position: "relative", display: "flex", alignItems: "center" }}>
            <input
              type="number"
              step="0.001"
              className="form-control"
              style={{ width: "100%", paddingRight: "40px" }}
              value={price}
              onChange={(e) => setPrice(e.target.value)}
              disabled={type === "MARKET"}
              placeholder="e.g. 99.500"
              required
            />
            <span style={{ position: "absolute", right: "12px", color: "var(--text-muted)", fontSize: "0.85rem" }}>
              {type === "MARKET" ? "MKT" : "%"}
            </span>
          </div>
        </div>

        {/* Qty Input */}
        <div className="form-group">
          <label>Quantity (Contracts)</label>
          <input
            type="number"
            className="form-control"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            placeholder="e.g. 1000"
            required
            min="1"
          />
          {/* Shortcuts */}
          <div style={{ display: "flex", gap: "6px", marginTop: "6px" }}>
            <button type="button" className="btn btn-secondary" style={{ padding: "4px 8px", fontSize: "0.75rem" }} onClick={() => handleQtyShortcut(1000)}>
              +1k
            </button>
            <button type="button" className="btn btn-secondary" style={{ padding: "4px 8px", fontSize: "0.75rem" }} onClick={() => handleQtyShortcut(5000)}>
              +5k
            </button>
            <button type="button" className="btn btn-secondary" style={{ padding: "4px 8px", fontSize: "0.75rem" }} onClick={() => handleQtyShortcut(10000)}>
              +10k
            </button>
            <button type="button" className="btn btn-secondary" style={{ padding: "4px 8px", fontSize: "0.75rem" }} onClick={() => setQuantity("1000")}>
              Reset
            </button>
          </div>
        </div>

        {/* Telemetry/Summary Panel */}
        <div className="glass-panel" style={{ padding: "12px", background: "rgba(0,0,0,0.2)", fontSize: "0.85rem", display: "flex", flexDirection: "column", gap: "6px", border: "1px solid rgba(255,255,255,0.03)" }}>
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <span style={{ color: "var(--text-muted)" }}>Face Value Par:</span>
            <span style={{ fontWeight: 500 }}>{formatCurrency(qtyNum * faceValue)}</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", borderTop: "1px solid rgba(255,255,255,0.04)", paddingTop: "6px" }}>
            <span style={{ color: "var(--text-muted)" }}>Estimated Principal:</span>
            <span style={{ fontWeight: 700, color: "var(--text-primary)" }}>
              {formatCurrency(estimatedPrincipal)}
            </span>
          </div>
        </div>

        {/* Message Banner */}
        {message && (
          <div style={{
            padding: "10px 12px",
            borderRadius: "6px",
            fontSize: "0.85rem",
            background: message.type === "success" ? "rgba(16, 185, 129, 0.15)" : "rgba(239, 68, 68, 0.15)",
            color: message.type === "success" ? "var(--bid)" : "var(--ask)",
            border: message.type === "success" ? "1px solid rgba(16, 185, 129, 0.3)" : "1px solid rgba(239, 68, 68, 0.3)"
          }}>
            {message.text}
          </div>
        )}

        {/* Submit Button */}
        <button
          type="submit"
          className="btn btn-primary"
          style={{
            marginTop: "auto",
            justifyContent: "center",
            padding: "12px",
            background: side === "BUY" ? "linear-gradient(135deg, var(--bid) 0%, #059669 100%)" : "linear-gradient(135deg, var(--ask) 0%, #dc2626 100%)",
            boxShadow: side === "BUY" ? "0 4px 15px rgba(16, 185, 129, 0.3)" : "0 4px 15px rgba(239, 68, 68, 0.3)"
          }}
          disabled={loading}
        >
          {loading ? "Transmitting..." : `Submit ${side} Order`}
        </button>

      </form>
    </div>
  );
};

export default OrderEntry;
