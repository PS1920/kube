import React, { useState, useEffect, useRef } from "react";

export default function ChaosModal({ 
  onClose, 
  deployments, 
  onInject, 
  logs 
}) {
  const [selectedService, setSelectedService] = useState("");
  const [selectedFault, setSelectedFault] = useState("crashloop");
  const [isInjecting, setIsInjecting] = useState(false);
  const logsEndRef = useRef(null);

  // Auto-scroll logs
  useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [logs]);

  // If logs signify recovery or success, re-enable button after a slight delay
  useEffect(() => {
    const lastLog = logs[logs.length - 1] || "";
    if (lastLog.includes("✅ MTTR") || lastLog.includes("Error")) {
      setTimeout(() => setIsInjecting(false), 2000); // 2s pause before re-enabling
    }
  }, [logs]);

  const handleInject = () => {
    if (!selectedService || isInjecting) return;
    setIsInjecting(true);
    onInject(selectedService, selectedFault);
  };

  return (
    <div style={{
      position: "fixed",
      inset: 0,
      background: "rgba(2, 6, 23, 0.7)",
      backdropFilter: "blur(6px)",
      zIndex: 100,
      display: "flex",
      alignItems: "center",
      justifyContent: "center"
    }}>
      <aside style={{
        width: "420px",
        background: "rgba(15, 23, 42, 0.95)",
        border: "1px solid #f43f5e",
        borderRadius: "16px",
        padding: "24px",
        display: "flex",
        flexDirection: "column",
        gap: "20px",
        color: "#fff",
        fontFamily: "'JetBrains Mono', monospace",
        boxShadow: "0 0 50px rgba(244, 63, 94, 0.25)"
      }}>
        {/* Header */}
        <h3 style={{
          color: "#f43f5e",
          margin: 0,
          fontSize: "1.1rem",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          textShadow: "0 0 10px rgba(244, 63, 94, 0.5)"
        }}>
          <span>🧪 Chaos Injection Terminal</span>
          <button 
            onClick={onClose}
            style={{
              background: "transparent",
              border: "none",
              color: "#94a3b8",
              fontSize: "1.5rem",
              cursor: "pointer",
              transition: "color 0.2s"
            }}
            onMouseEnter={(e) => e.target.style.color = "#fff"}
            onMouseLeave={(e) => e.target.style.color = "#94a3b8"}
          >
            &times;
          </button>
        </h3>
        
        {/* Dropdowns */}
        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          <select 
            value={selectedService} 
            onChange={e => setSelectedService(e.target.value)} 
            disabled={isInjecting}
            style={{ 
              padding: "12px", 
              background: "rgba(0,0,0,0.4)", 
              border: "1px solid rgba(255,255,255,0.15)", 
              color: "#f8fafc", 
              borderRadius: "8px", 
              outline: "none",
              cursor: isInjecting ? "not-allowed" : "pointer"
            }}
          >
            <option value="">-- Select Target Service --</option>
            {deployments.map(d => <option key={d.name} value={d.name}>{d.name}</option>)}
          </select>

          <select 
            value={selectedFault} 
            onChange={e => setSelectedFault(e.target.value)} 
            disabled={isInjecting}
            style={{ 
              padding: "12px", 
              background: "rgba(0,0,0,0.4)", 
              border: "1px solid rgba(255,255,255,0.15)", 
              color: "#f8fafc", 
              borderRadius: "8px", 
              outline: "none",
              cursor: isInjecting ? "not-allowed" : "pointer"
            }}
          >
            <option value="crashloop">CrashLoop (Pod Crash)</option>
            <option value="resource">Resource Pressure (CPU/Memory)</option>
            <option value="misconfig">Misconfiguration</option>
            <option value="pending">Pending Status</option>
          </select>
        </div>

        {/* Action Button */}
        <button 
          onClick={handleInject} 
          disabled={isInjecting || !selectedService}
          style={{ 
            width: "100%", 
            padding: "16px", 
            background: isInjecting ? "transparent" : "rgba(244, 63, 94, 0.15)", 
            border: `1px solid ${isInjecting ? "#475569" : "#f43f5e"}`, 
            color: isInjecting ? "#94a3b8" : "#f43f5e", 
            fontWeight: "bold", 
            cursor: (isInjecting || !selectedService) ? "not-allowed" : "pointer", 
            borderRadius: "8px", 
            transition: "all 0.3s ease", 
            textTransform: "uppercase", 
            letterSpacing: "2px",
            boxShadow: (!isInjecting && selectedService) ? "0 0 15px rgba(244, 63, 94, 0.4)" : "none"
          }}
          onMouseEnter={(e) => {
            if (!isInjecting && selectedService) {
              e.target.style.background = "rgba(244, 63, 94, 0.3)";
            }
          }}
          onMouseLeave={(e) => {
            if (!isInjecting && selectedService) {
              e.target.style.background = "rgba(244, 63, 94, 0.15)";
            }
          }}
        >
          {isInjecting ? "Initiating..." : "🔥 Inject Chaos"}
        </button>

        {/* Terminal Logs Window */}
        <div style={{ 
          background: "#000", 
          padding: "16px", 
          borderRadius: "8px", 
          fontSize: "0.75rem", 
          color: "#cbd5e1", 
          height: "180px", 
          overflowY: "auto", 
          border: "1px solid rgba(255,255,255,0.05)",
          boxShadow: "inset 0 0 20px rgba(0,0,0,0.8)"
        }}>
          {logs.length === 0 && <span style={{opacity: 0.4, fontStyle: "italic"}}>&gt; Awaiting chaos command...</span>}
          {logs.map((log, i) => (
            <div 
              key={i} 
              style={{
                marginBottom: "8px", 
                color: log.includes("✅") ? "#10b981" : log.includes("🔥") || log.includes("Injecting") ? "#f59e0b" : "#cbd5e1",
                animation: "fade-in 0.3s ease forwards"
              }}
            >
              <span style={{ color: "#f43f5e", marginRight: "6px" }}>$&gt;</span>
              {log}
            </div>
          ))}
          <div ref={logsEndRef} />
        </div>
      </aside>
    </div>
  );
}
