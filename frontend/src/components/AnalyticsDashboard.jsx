import React, { useState, useEffect } from "react";
import { 
  ResponsiveContainer, 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend, 
  AreaChart, 
  Area, 
  PieChart, 
  Pie, 
  Cell 
} from "recharts";
import { useWebSocket } from "../context/WebSocketContext";
import { BarChart, DollarSign, Award, Percent, Clock, RefreshCw } from "lucide-react";

const AnalyticsDashboard = () => {
  const { subscribe } = useWebSocket();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  const fetchAnalytics = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem("token");
      const res = await fetch("http://localhost:8000/api/v1/analytics/", {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const result = await res.json();
        setData(result);
      }
    } catch (err) {
      console.error("Error fetching analytics:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();

    // Re-fetch analytics on trade execution or settlement update
    const unsubscribeTrade = subscribe("blotter_update", () => {
      fetchAnalytics();
    });

    const unsubscribeSettlement = subscribe("trade_settlement_update", () => {
      fetchAnalytics();
    });

    const unsubscribeRfq = subscribe("rfq_accepted", () => {
      fetchAnalytics();
    });

    // Also auto-refresh every 10 seconds to keep yield curves updated in real-time
    const interval = setInterval(fetchAnalytics, 10000);

    return () => {
      unsubscribeTrade();
      unsubscribeSettlement();
      unsubscribeRfq();
      clearInterval(interval);
    };
  }, [subscribe]);

  const COLORS = ["#6366f1", "#a855f7", "#10b981", "#ef4444", "#3b82f6", "#f59e0b", "#c084fc"];

  const formatCurrency = (val) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      maximumFractionDigits: 0
    }).format(val);
  };

  if (loading && !data) {
    return (
      <div style={{ padding: "40px", textAlign: "center", color: "var(--text-muted)" }}>
        Loading Desk Analytics...
      </div>
    );
  }

  if (!data) {
    return (
      <div style={{ padding: "40px", textAlign: "center", color: "var(--text-muted)" }}>
        No analytics data available. Place some orders or RFQs first!
      </div>
    );
  }

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: "24px" }}>
      {/* Page Title */}
      <div className="page-title">
        <span>Bond Desk Analytics</span>
        <button className="btn btn-secondary" onClick={fetchAnalytics} style={{ padding: "8px" }}>
          <RefreshCw size={16} />
        </button>
      </div>

      {/* Stats Summary Row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "20px" }}>
        
        {/* Total Capital */}
        <div className="glass-panel" style={{ padding: "20px", display: "flex", alignItems: "center", gap: "16px", background: "rgba(16, 20, 48, 0.4)" }}>
          <div style={{ width: "48px", height: "48px", borderRadius: "12px", background: "rgba(16, 185, 129, 0.1)", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <DollarSign size={24} style={{ color: "var(--bid)" }} />
          </div>
          <div>
            <span style={{ fontSize: "0.8rem", color: "var(--text-muted)", textTransform: "uppercase" }}>Capital Cash</span>
            <div style={{ fontSize: "1.3rem", fontWeight: 700, fontFamily: "var(--font-display)" }}>
              {formatCurrency(data.user_cash)}
            </div>
          </div>
        </div>

        {/* Traded Volume */}
        <div className="glass-panel" style={{ padding: "20px", display: "flex", alignItems: "center", gap: "16px", background: "rgba(16, 20, 48, 0.4)" }}>
          <div style={{ width: "48px", height: "48px", borderRadius: "12px", background: "rgba(99, 102, 241, 0.1)", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <BarChart size={24} style={{ color: "var(--primary)" }} />
          </div>
          <div>
            <span style={{ fontSize: "0.8rem", color: "var(--text-muted)", textTransform: "uppercase" }}>Traded Volume</span>
            <div style={{ fontSize: "1.3rem", fontWeight: 700, fontFamily: "var(--font-display)" }}>
              ${data.total_volume_millions.toFixed(2)}M
            </div>
          </div>
        </div>

        {/* RFQ Win Rate */}
        <div className="glass-panel" style={{ padding: "20px", display: "flex", alignItems: "center", gap: "16px", background: "rgba(16, 20, 48, 0.4)" }}>
          <div style={{ width: "48px", height: "48px", borderRadius: "12px", background: "rgba(168, 85, 247, 0.1)", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Percent size={24} style={{ color: "var(--secondary)" }} />
          </div>
          <div>
            <span style={{ fontSize: "0.8rem", color: "var(--text-muted)", textTransform: "uppercase" }}>Dealer Win Rate</span>
            <div style={{ fontSize: "1.3rem", fontWeight: 700, fontFamily: "var(--font-display)" }}>
              {data.rfq_win_rate}%
            </div>
          </div>
        </div>

        {/* Avg Response Time */}
        <div className="glass-panel" style={{ padding: "20px", display: "flex", alignItems: "center", gap: "16px", background: "rgba(16, 20, 48, 0.4)" }}>
          <div style={{ width: "48px", height: "48px", borderRadius: "12px", background: "rgba(245, 158, 11, 0.1)", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Clock size={24} style={{ color: "var(--warning)" }} />
          </div>
          <div>
            <span style={{ fontSize: "0.8rem", color: "var(--text-muted)", textTransform: "uppercase" }}>Avg Quoting Speed</span>
            <div style={{ fontSize: "1.3rem", fontWeight: 700, fontFamily: "var(--font-display)" }}>
              {data.rfq_avg_response_time > 0 ? `${data.rfq_avg_response_time}s` : "N/A"}
            </div>
          </div>
        </div>

      </div>

      {/* Main Charts Grid */}
      <div className="dashboard-grid">
        
        {/* Yield Curve Line Chart */}
        <div className="glass-panel" style={{ padding: "20px", height: "350px" }}>
          <h3 style={{ fontSize: "1rem", color: "var(--text-secondary)", textTransform: "uppercase", marginBottom: "16px" }}>
            Treasury Yield Curve
          </h3>
          <ResponsiveContainer width="100%" height="90%">
            <LineChart data={data.yield_curve} margin={{ top: 10, right: 20, left: -20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis 
                dataKey="maturity_years" 
                type="number"
                domain={[0, 32]}
                ticks={[2, 5, 10, 30]}
                name="Maturity"
                unit="Y"
                stroke="var(--text-muted)"
              />
              <YAxis 
                domain={['auto', 'auto']}
                name="Yield"
                unit="%"
                stroke="var(--text-muted)"
              />
              <Tooltip 
                contentStyle={{ background: "rgba(10,12,30,0.9)", borderColor: "var(--surface-border)", borderRadius: "8px" }}
                formatter={(value, name, props) => [`${value}%`, `Yield (${props.payload.ticker})`]}
              />
              <Line 
                type="monotone" 
                dataKey="yield_pct" 
                stroke="var(--primary)" 
                strokeWidth={3}
                activeDot={{ r: 8 }}
                dot={{ stroke: 'var(--secondary)', strokeWidth: 2, r: 4 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Volume History Area Chart */}
        <div className="glass-panel" style={{ padding: "20px", height: "350px" }}>
          <h3 style={{ fontSize: "1rem", color: "var(--text-secondary)", textTransform: "uppercase", marginBottom: "16px" }}>
            Real-Time Trading Activity
          </h3>
          <ResponsiveContainer width="100%" height="90%">
            <AreaChart data={data.monthly_volumes} margin={{ top: 10, right: 10, left: -20, bottom: 5 }}>
              <defs>
                <linearGradient id="colorVol" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="var(--primary)" stopOpacity={0.8}/>
                  <stop offset="95%" stopColor="var(--primary)" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="time" stroke="var(--text-muted)" />
              <YAxis stroke="var(--text-muted)" unit="M" />
              <Tooltip contentStyle={{ background: "rgba(10,12,30,0.9)", borderColor: "var(--surface-border)", borderRadius: "8px" }} formatter={(value) => [`$${value}M`, "Volume"]} />
              <Area type="monotone" dataKey="volume" stroke="var(--primary)" fillOpacity={1} fill="url(#colorVol)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Asset Distribution Pie Chart */}
        <div className="glass-panel grid-full" style={{ padding: "20px", height: "350px", display: "flex", flexDirection: "column" }}>
          <h3 style={{ fontSize: "1rem", color: "var(--text-secondary)", textTransform: "uppercase", marginBottom: "16px" }}>
            Traded Bonds Portfolio Allocation
          </h3>
          <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "space-around", flexWrap: "wrap" }}>
            
            <div style={{ width: "300px", height: "240px" }}>
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={data.bond_distribution}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={90}
                    paddingAngle={3}
                    dataKey="value"
                  >
                    {data.bond_distribution.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ background: "rgba(10,12,30,0.9)", borderColor: "var(--surface-border)", borderRadius: "8px" }} formatter={(value) => [`$${value}M`, "Traded"]} />
                </PieChart>
              </ResponsiveContainer>
            </div>

            {/* Custom Legend */}
            <div style={{ display: "flex", flexDirection: "column", gap: "10px", maxHeight: "200px", overflowY: "auto" }}>
              {data.bond_distribution.map((entry, index) => (
                <div key={entry.name} style={{ display: "flex", alignItems: "center", gap: "12px", fontSize: "0.9rem" }}>
                  <div style={{ width: "12px", height: "12px", borderRadius: "3px", backgroundColor: COLORS[index % COLORS.length] }}></div>
                  <strong style={{ width: "60px" }}>{entry.name}</strong>
                  <span style={{ color: "var(--text-muted)" }}>${entry.value.toFixed(2)}M Traded</span>
                </div>
              ))}
            </div>

          </div>
        </div>

      </div>
    </div>
  );
};

export default AnalyticsDashboard;
