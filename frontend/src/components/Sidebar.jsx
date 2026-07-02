import React from "react";
import { 
  TrendingUp, 
  User, 
  BookOpen, 
  FileText, 
  BarChart2, 
  LogOut, 
  Zap,
  DollarSign
} from "lucide-react";

const Sidebar = ({ user, activeTab, setActiveTab, connected, onLogout, pnl }) => {
  const formatCurrency = (val) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
    }).format(val || 0);
  };

  const isPnlPositive = pnl >= 0;

  return (
    <aside className="glass-panel" style={{ width: "280px", minWidth: "280px", display: "flex", flexDirection: "column", height: "100vh", borderRadius: "0px", borderTop: "none", borderLeft: "none", borderBottom: "none", zIndex: 10 }}>
      {/* Title */}
      <div style={{ padding: "24px 20px", borderBottom: "1px solid var(--surface-border)", display: "flex", alignItems: "center", gap: "12px" }}>
        <Zap style={{ color: "var(--primary)", width: "32px", height: "32px", filter: "drop-shadow(0 0 8px var(--primary))" }} />
        <div>
          <h2 style={{ fontFamily: "var(--font-display)", fontWeight: 800, fontSize: "1.4rem", letterSpacing: "-0.03em" }}>TradeFlow</h2>
          <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>Bond Desk Sim</span>
        </div>
      </div>

      {/* Account Info Card */}
      {user && (
        <div style={{ padding: "20px", borderBottom: "1px solid var(--surface-border)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "16px" }}>
            <div style={{ width: "36px", height: "36px", borderRadius: "50%", background: "linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%)", display: "flex", alignItems: "center", justifyItems: "center", justifyContent: "center" }}>
              <User size={18} style={{ color: "white" }} />
            </div>
            <div>
              <div style={{ fontWeight: 600, fontSize: "0.95rem" }}>{user.username}</div>
              <span className="status-badge" style={{ padding: "1px 6px", fontSize: "0.65rem", background: "rgba(99, 102, 241, 0.15)", color: "#818cf8", border: "1px solid rgba(99, 102, 241, 0.3)" }}>
                TRADER
              </span>
            </div>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            <div>
              <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase" }}>Cash Capital</div>
              <div style={{ fontSize: "1.15rem", fontWeight: 700, fontFamily: "var(--font-display)", display: "flex", alignItems: "center" }}>
                <DollarSign size={16} style={{ color: "var(--bid)", marginRight: "2px" }} />
                {formatCurrency(user.cash_balance).replace("$", "")}
              </div>
            </div>
            <div>
              <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase" }}>Mark-to-Market P&L</div>
              <div style={{ 
                fontSize: "1.1rem", 
                fontWeight: 700, 
                fontFamily: "var(--font-display)", 
                color: isPnlPositive ? "var(--bid)" : "var(--ask)" 
              }}>
                {isPnlPositive ? "+" : ""}{formatCurrency(pnl)}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Navigation */}
      <nav style={{ padding: "20px 10px", flex: 1, display: "flex", flexDirection: "column", gap: "6px" }}>
        <button 
          onClick={() => setActiveTab("client")} 
          className={`btn ${activeTab === "client" ? "btn-primary" : "btn-secondary"}`}
          style={{ width: "100%", justifyContent: "flex-start", padding: "12px 16px", background: activeTab === "client" ? undefined : "transparent", borderColor: activeTab === "client" ? undefined : "transparent" }}
        >
          <TrendingUp size={18} />
          <span>Client Desk</span>
        </button>

        <button 
          onClick={() => setActiveTab("dealer")} 
          className={`btn ${activeTab === "dealer" ? "btn-primary" : "btn-secondary"}`}
          style={{ width: "100%", justifyContent: "flex-start", padding: "12px 16px", background: activeTab === "dealer" ? undefined : "transparent", borderColor: activeTab === "dealer" ? undefined : "transparent" }}
        >
          <BookOpen size={18} />
          <span>Dealer Desk</span>
        </button>

        <button 
          onClick={() => setActiveTab("blotter")} 
          className={`btn ${activeTab === "blotter" ? "btn-primary" : "btn-secondary"}`}
          style={{ width: "100%", justifyContent: "flex-start", padding: "12px 16px", background: activeTab === "blotter" ? undefined : "transparent", borderColor: activeTab === "blotter" ? undefined : "transparent" }}
        >
          <FileText size={18} />
          <span>Trade Blotter</span>
        </button>

        <button 
          onClick={() => setActiveTab("analytics")} 
          className={`btn ${activeTab === "analytics" ? "btn-primary" : "btn-secondary"}`}
          style={{ width: "100%", justifyContent: "flex-start", padding: "12px 16px", background: activeTab === "analytics" ? undefined : "transparent", borderColor: activeTab === "analytics" ? undefined : "transparent" }}
        >
          <BarChart2 size={18} />
          <span>Analytics Desk</span>
        </button>
      </nav>

      {/* Footer Info */}
      <div style={{ padding: "20px", borderTop: "1px solid var(--surface-border)", display: "flex", flexDirection: "column", gap: "12px" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>Server Status:</span>
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <span style={{ 
              width: "8px", 
              height: "8px", 
              borderRadius: "50%", 
              backgroundColor: connected ? "var(--success)" : "var(--danger)",
              boxShadow: connected ? "0 0 8px var(--success)" : "0 0 8px var(--danger)"
            }}></span>
            <span style={{ fontSize: "0.8rem", fontWeight: 500, color: connected ? "var(--text-primary)" : "var(--text-muted)" }}>
              {connected ? "Connected" : "Offline"}
            </span>
          </div>
        </div>

        <button 
          onClick={onLogout}
          className="btn btn-secondary"
          style={{ width: "100%", justifyContent: "center", padding: "10px", gap: "8px" }}
        >
          <LogOut size={16} />
          <span>Exit Blotter</span>
        </button>
      </div>
    </aside>
  );
};

export default Sidebar;
