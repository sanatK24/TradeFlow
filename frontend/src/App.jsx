import React, { useState, useEffect } from "react";
import { WebSocketProvider, useWebSocket } from "./context/WebSocketContext";
import Sidebar from "./components/Sidebar";
import OrderBook from "./components/OrderBook";
import OrderEntry from "./components/OrderEntry";
import RfqDashboard from "./components/RfqDashboard";
import TradeBlotter from "./components/TradeBlotter";
import AnalyticsDashboard from "./components/AnalyticsDashboard";
import { Zap, Lock, Mail, ChevronRight, UserPlus } from "lucide-react";

const AppContent = () => {
  const { connect, disconnect, connected, subscribe } = useWebSocket();
  const [token, setToken] = useState(localStorage.getItem("token") || null);
  const [user, setUser] = useState(null);
  const [activeTab, setActiveTab] = useState("client"); // client | dealer | blotter | analytics
  const [bonds, setBonds] = useState([]);
  const [selectedBond, setSelectedBond] = useState(null);
  const [pnl, setPnl] = useState(0.0);
  
  // Presets from clicking order book rows
  const [presetPrice, setPresetPrice] = useState(null);
  const [presetQty, setPresetQty] = useState(null);
  const [presetSide, setPresetSide] = useState(null);

  // Authentication states
  const [authMode, setAuthMode] = useState("login"); // login | register
  const [usernameInput, setUsernameInput] = useState("");
  const [passwordInput, setPasswordInput] = useState("");
  const [authError, setAuthError] = useState("");

  // Fetch bonds list
  const fetchBonds = async (authToken) => {
    try {
      const res = await fetch("http://localhost:8001/api/v1/bonds/", {
        headers: { Authorization: `Bearer ${authToken}` }
      });
      if (res.ok) {
        const data = await res.json();
        setBonds(data);
        if (data.length > 0 && !selectedBond) {
          setSelectedBond(data[0]);
        }
      }
    } catch (err) {
      console.error("Error fetching bonds:", err);
    }
  };

  // Fetch current user details (balance, etc.)
  const fetchUser = async (authToken) => {
    try {
      const res = await fetch("http://localhost:8001/api/v1/auth/me", {
        headers: { Authorization: `Bearer ${authToken}` }
      });
      if (res.ok) {
        const data = await res.json();
        setUser(data);
      } else {
        handleLogout();
      }
    } catch (err) {
      console.error("Error fetching user profile:", err);
    }
  };

  // Fetch current desk P&L
  const fetchPnl = async (authToken) => {
    try {
      const res = await fetch("http://localhost:8001/api/v1/analytics/", {
        headers: { Authorization: `Bearer ${authToken}` }
      });
      if (res.ok) {
        const data = await res.json();
        setPnl(data.user_pnl);
      }
    } catch (err) {
      console.error("Error fetching desk P&L:", err);
    }
  };

  // Run on startup / token change
  useEffect(() => {
    if (token) {
      connect(token);
      fetchUser(token);
      fetchBonds(token);
      fetchPnl(token);
    } else {
      disconnect();
      setUser(null);
    }
  }, [token]);

  // Subscribe to real-time events that affect financial balances
  useEffect(() => {
    if (!token) return;

    // Refresh user balance and P&L on fills or settlement updates
    const onFill = () => {
      fetchUser(token);
      fetchPnl(token);
    };

    const unsubscribeFill = subscribe("order_filled", onFill);
    const unsubscribePartFill = subscribe("order_partially_filled", onFill);
    const unsubscribeSettlement = subscribe("trade_settlement_update", onFill);
    const unsubscribeRfqAccept = subscribe("rfq_accepted", onFill);

    return () => {
      unsubscribeFill();
      unsubscribePartFill();
      unsubscribeSettlement();
      unsubscribeRfqAccept();
    };
  }, [token, subscribe]);

  const handleLoginSubmit = async (e) => {
    e.preventDefault();
    setAuthError("");
    
    // URLSearchParams for Form request
    const params = new URLSearchParams();
    params.append("username", usernameInput);
    params.append("password", passwordInput);

    try {
      const res = await fetch("http://localhost:8001/api/v1/auth/token", {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded"
        },
        body: params
      });

      const data = await res.json();
      if (res.ok) {
        localStorage.setItem("token", data.access_token);
        setToken(data.access_token);
        setUsernameInput("");
        setPasswordInput("");
      } else {
        setAuthError(data.detail || "Authentication failed. Check your password.");
      }
    } catch (err) {
      setAuthError("Network error. Make sure FastAPI server is running.");
    }
  };

  const handleRegisterSubmit = async (e) => {
    e.preventDefault();
    setAuthError("");

    try {
      const res = await fetch("http://localhost:8001/api/v1/auth/register", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          username: usernameInput,
          password: passwordInput
        })
      });

      const data = await res.json();
      if (res.ok) {
        // Switch to login
        setAuthMode("login");
        setAuthError("Account created! Please log in.");
        setPasswordInput("");
      } else {
        setAuthError(data.detail || "Registration failed. Username might be taken.");
      }
    } catch (err) {
      setAuthError("Network error connecting to registration server.");
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("token");
    setToken(null);
    disconnect();
  };

  // Callback when user clicks on orderbook row
  const handleSelectPriceSize = (price, size, side) => {
    setPresetPrice(price);
    setPresetQty(size);
    setPresetSide(side === "BUY" ? "SELL" : "BUY"); // click ask to buy, click bid to sell
  };

  // Re-fetch telemetry on order entries
  const handleOrderSubmitted = () => {
    fetchUser(token);
    fetchPnl(token);
  };

  if (!token) {
    /* ==================== LOGIN/REGISTER WORKSPACE ==================== */
    return (
      <div style={{ display: "flex", width: "100vw", height: "100vh", alignItems: "center", justifyContent: "center", position: "relative" }}>
        
        {/* Background Decorative Gradients */}
        <div style={{ position: "absolute", top: "10%", left: "15%", width: "250px", height: "250px", borderRadius: "50%", background: "radial-gradient(circle, var(--primary) 0%, transparent 70%)", filter: "blur(40px)", opacity: 0.35, zIndex: 0 }} />
        <div style={{ position: "absolute", bottom: "10%", right: "15%", width: "300px", height: "300px", borderRadius: "50%", background: "radial-gradient(circle, var(--secondary) 0%, transparent 70%)", filter: "blur(50px)", opacity: 0.3, zIndex: 0 }} />

        <div className="glass-panel" style={{ width: "420px", padding: "40px", zIndex: 1, display: "flex", flexDirection: "column", gap: "20px", border: "1px solid rgba(255,255,255,0.06)" }}>
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "10px" }}>
            <div style={{ padding: "12px", borderRadius: "14px", background: "rgba(99, 102, 241, 0.1)", border: "1px solid rgba(99, 102, 241, 0.2)", display: "flex", alignItems: "center", justifyItems: "center" }}>
              <Zap size={32} style={{ color: "var(--primary)", filter: "drop-shadow(0 0 5px var(--primary))" }} />
            </div>
            <h1 style={{ fontSize: "1.8rem", fontWeight: 800, fontFamily: "var(--font-display)" }}>TradeFlow Desk</h1>
            <span style={{ fontSize: "0.85rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
              Fixed-Income Electronic Trading
            </span>
          </div>

          <form onSubmit={authMode === "login" ? handleLoginSubmit : handleRegisterSubmit} style={{ display: "flex", flexDirection: "column", gap: "16px", marginTop: "10px" }}>
            
            <div className="form-group">
              <label>Trader Username</label>
              <div style={{ position: "relative", display: "flex", alignItems: "center" }}>
                <Mail size={16} style={{ position: "absolute", left: "12px", color: "var(--text-muted)" }} />
                <input
                  type="text"
                  className="form-control"
                  style={{ width: "100%", paddingLeft: "36px" }}
                  placeholder="e.g. S.Karkhanis"
                  value={usernameInput}
                  onChange={(e) => setUsernameInput(e.target.value)}
                  required
                />
              </div>
            </div>

            <div className="form-group">
              <label>Desk Password</label>
              <div style={{ position: "relative", display: "flex", alignItems: "center" }}>
                <Lock size={16} style={{ position: "absolute", left: "12px", color: "var(--text-muted)" }} />
                <input
                  type="password"
                  className="form-control"
                  style={{ width: "100%", paddingLeft: "36px" }}
                  placeholder="••••••••"
                  value={passwordInput}
                  onChange={(e) => setPasswordInput(e.target.value)}
                  required
                />
              </div>
            </div>

            {authError && (
              <div style={{ padding: "8px 12px", background: "rgba(239, 68, 68, 0.15)", border: "1px solid rgba(239, 68, 68, 0.3)", borderRadius: "6px", color: "var(--ask)", fontSize: "0.85rem" }}>
                {authError}
              </div>
            )}

            <button type="submit" className="btn btn-primary" style={{ height: "46px", justifyContent: "center" }}>
              <span>{authMode === "login" ? "Open Blotter" : "Create Trader Profile"}</span>
              <ChevronRight size={18} />
            </button>
          </form>

          <div style={{ textAlign: "center", borderTop: "1px solid var(--surface-border)", paddingTop: "16px" }}>
            {authMode === "login" ? (
              <button 
                onClick={() => { setAuthMode("register"); setAuthError(""); }}
                className="btn btn-secondary"
                style={{ background: "transparent", border: "none", fontSize: "0.85rem", color: "var(--text-muted)", cursor: "pointer", display: "inline-flex", gap: "6px" }}
              >
                <UserPlus size={16} />
                <span>New Trader? Register Profile</span>
              </button>
            ) : (
              <button 
                onClick={() => { setAuthMode("login"); setAuthError(""); }}
                className="btn btn-secondary"
                style={{ background: "transparent", border: "none", fontSize: "0.85rem", color: "var(--text-muted)", cursor: "pointer" }}
              >
                <span>Already registered? Log In</span>
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  /* ==================== TRADING WORKSPACE MAIN LAYOUT ==================== */
  return (
    <div className="app-container">
      <Sidebar 
        user={user} 
        activeTab={activeTab} 
        setActiveTab={setActiveTab} 
        connected={connected} 
        onLogout={handleLogout} 
        pnl={pnl}
      />

      <main className="main-content">
        {activeTab === "client" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "24px", flex: 1 }}>
            {/* Top Row: L2 Book + Order Ticket */}
            <div className="dashboard-grid" style={{ marginBottom: 0 }}>
              <OrderBook 
                bonds={bonds} 
                selectedBond={selectedBond} 
                setSelectedBond={setSelectedBond} 
                onSelectPriceSize={handleSelectPriceSize}
              />
              <OrderEntry 
                selectedBond={selectedBond} 
                presetPrice={presetPrice}
                presetQty={presetQty}
                presetSide={presetSide}
                onOrderSubmitted={handleOrderSubmitted}
              />
            </div>
            
            {/* Bottom Row: Client RFQ Panel */}
            <div className="glass-panel" style={{ padding: "20px", display: "flex", flexDirection: "column" }}>
              <RfqDashboard 
                bonds={bonds} 
                activeRole="client" 
                onTradeExecuted={handleOrderSubmitted}
              />
            </div>
          </div>
        )}

        {activeTab === "dealer" && (
          <div className="glass-panel" style={{ padding: "20px", display: "flex", flexDirection: "column", flex: 1 }}>
            <RfqDashboard 
              bonds={bonds} 
              activeRole="dealer" 
              onTradeExecuted={handleOrderSubmitted}
            />
          </div>
        )}

        {activeTab === "blotter" && (
          <div className="glass-panel" style={{ padding: "20px", display: "flex", flexDirection: "column", flex: 1 }}>
            <TradeBlotter />
          </div>
        )}

        {activeTab === "analytics" && (
          <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
            <AnalyticsDashboard />
          </div>
        )}
      </main>
    </div>
  );
};

// Wrap in provider
const App = () => (
  <WebSocketProvider>
    <AppContent />
  </WebSocketProvider>
);

export default App;
