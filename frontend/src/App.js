import React, { useState, useEffect, useRef, useMemo } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { OrbitControls, Stars, Float } from "@react-three/drei";
import * as THREE from "three";
import Typewriter from 'typewriter-effect';

import Node from "./components/Node";
import FlowParticles from "./components/FlowParticles";
import CurvedLine from "./components/CurvedLine";
import SystemChart from "./components/SystemChart";
import ChaosModal from "./components/ChaosModal";

const BACKEND = "http://127.0.0.1:8000";

/* ============================================================
   🎥 CINEMATIC CAMERA
============================================================ */
function CinematicCamera({ targetPos }) {
  const { camera, controls } = useThree();
  const homePosition = useMemo(() => new THREE.Vector3(25, 18, 25), []);
  const homeTarget = useMemo(() => new THREE.Vector3(0, 0, 0), []);

  useFrame(() => {
    const dPos = targetPos 
      ? new THREE.Vector3(targetPos[0] + 10, targetPos[1] + 6, targetPos[2] + 10) 
      : homePosition;
    
    const dTarget = targetPos ? new THREE.Vector3(...targetPos) : homeTarget;

    camera.position.lerp(dPos, 0.08);

    if (controls) {
      controls.target.lerp(dTarget, 0.08);
      controls.update();
    }
  });
  return null;
}

/* ============================================================
   🧠 HOLOGRAPHIC AI CORE
============================================================ */
function AICore({ isSpeaking, onCoreClick }) {
  const ref = useRef();
  useFrame(({ clock }) => {
    ref.current.rotation.y += 0.005;
    let pulse = 1 + Math.sin(clock.elapsedTime * 2) * 0.05;
    ref.current.scale.setScalar(isSpeaking ? pulse * 1.15 : pulse);
  });

  return (
    <Float speed={2} rotationIntensity={0.5} floatIntensity={0.5}>
      <mesh 
        ref={ref} 
        onClick={(e) => { 
          e.stopPropagation(); 
          onCoreClick(); 
        }}
      >
        <sphereGeometry args={[2.5, 64, 64]} />
        <meshStandardMaterial 
          color="#06b6d4" 
          emissive="#0891b2" 
          emissiveIntensity={isSpeaking ? 8 : 4} 
          wireframe 
          transparent 
          opacity={0.8} 
        />
      </mesh>
    </Float>
  );
}

/* ============================================================
   🚀 MAIN DASHBOARD
============================================================ */
export default function App() {
  const [deployments, setDeployments] = useState([]);
  const [dependencies, setDependencies] = useState([]);
  const [selectedNode, setSelectedNode] = useState(null);
  const [selectedPos, setSelectedPos] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [hasAiResult, setHasAiResult] = useState(false);
  
  const [showChaos, setShowChaos] = useState(false);
  const [chaosLogs, setChaosLogs] = useState([]);
  
  const controlsRef = useRef();

  useEffect(() => {
    // Initial fetch to paint immediately
    const fetchData = () => {
      fetch(`${BACKEND}/api/deployments`)
        .then(res => res.json())
        .then(data => setDeployments(Array.isArray(data) ? data : []))
        .catch(() => setDeployments([]));
        
      fetch(`${BACKEND}/api/graph/status`)
        .then(res => res.json())
        .then(data => setDependencies(data.dependencies || []))
        .catch(() => setDependencies([]));
    };
    fetchData();

    // WebSocket real-time subscription with auto-reconnect
    let wsUrl = BACKEND.replace(/^http/, "ws") + "/ws";
    let ws;
    let reconnectTimeout;
    let isMounted = true;

    const connectWebSocket = () => {
      ws = new WebSocket(wsUrl);

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === "DEPLOYMENT_UPDATE") {
            setDeployments(prev => {
              const newDeps = msg.deployments || [];
              // B. DEPLOYMENT_UPDATE must NOT override manual state
              return newDeps.map(nd => {
                const existing = prev.find(p => p.name === nd.name);
                if (existing && existing.manualOverride) {
                   return { ...nd, status: existing.status, manualOverride: true };
                }
                return nd;
              });
            });
          } else if (msg.type === "CHAOS_LOG") {
            setChaosLogs(prev => [...prev, msg.message]);
          } else if (msg.type === "SYSTEM_EVENT") {
            // A. SYSTEM_EVENT must update UI state
            setDeployments(prev => prev.map(d => {
              if (d.name === msg.service) {
                // C. Clear override ONLY when status == "healthy"
                const isHealthy = msg.status === "healthy";
                return { 
                  ...d, 
                  status: msg.status, 
                  manualOverride: !isHealthy 
                };
              }
              return d;
            }));
          }
        } catch (err) {}
      };

      ws.onclose = () => {
        if (isMounted) {
          reconnectTimeout = setTimeout(connectWebSocket, 1500); // Reconnect after 1.5s
        }
      };
    };

    connectWebSocket();

    return () => {
      isMounted = false;
      clearTimeout(reconnectTimeout);
      if (ws) ws.close();
    };
  }, []);

  const handleNodeClick = (dep, pos) => {
    if (selectedNode === dep.name) {
      resetView();
      return;
    }
    setSelectedNode(dep.name);
    setSelectedPos(pos);
    setIsSpeaking(false);
    setIsAnalyzing(false);
    setHasAiResult(false);
    // Instant initial evaluation handled implicitly by useEffect below
  };

  const runRuleEngine = (serviceName, systemDeployments) => {
    const serviceNode = systemDeployments.find(d => d.name === serviceName);
    if (!serviceNode) return null;
    
    if (serviceNode.status === 'failed') {
       const deps = dependencies.filter(d => d.from === serviceName);
       const failedDeps = deps.filter(d => {
           const depNode = systemDeployments.find(n => n.name === d.to);
           return depNode && (depNode.status === 'failed' || depNode.status === 'degraded');
       });
       if (failedDeps.length === 1) {
           return `${serviceName} is failing because ${failedDeps[0].to} is down.`;
       } else if (failedDeps.length > 1) {
           return null;
       } else {
           return `${serviceName} is failing due to an internal fault.`;
       }
    }
    if (serviceNode.status === 'recovering') {
       return `System is recovering as Kubernetes restarts failed instances.`;
    }
    if (serviceNode.status === 'degraded') {
       const deps = dependencies.filter(d => d.from === serviceName);
       const failedDeps = deps.filter(d => {
           const depNode = systemDeployments.find(n => n.name === d.to);
           return depNode && (depNode.status === 'failed' || depNode.status === 'degraded');
       });
       if (failedDeps.length === 1) {
           return `Service is degraded due to resource pressure on ${failedDeps[0].to}.`;
       }
       return null;
    }
    return `System reports: ${serviceNode.status.toUpperCase()}. Replicas: ${serviceNode.running}/${serviceNode.desired}.`;
  };

  useEffect(() => {
     if (selectedNode && deployments.length > 0 && !isAnalyzing && !hasAiResult) {
         const quickAnswer = runRuleEngine(selectedNode, deployments);
         if (quickAnswer) {
             setAnalysis({
                 answer: quickAnswer,
                 suggestion: deployments.find(d => d.name === selectedNode)?.event_message || "Monitoring stability...",
                 isFast: true
             });
         } else {
             setAnalysis({
                 answer: "Multiple failures or unclear root cause detected. Use AI Analysis.",
                 suggestion: "AI Fallback Required",
                 isFast: true
             });
         }
     }
  }, [deployments, selectedNode, dependencies, isAnalyzing, hasAiResult]);

  const handleInjectChaos = async (serviceName, faultType) => {
    setChaosLogs([]);
    try {
        await fetch(`${BACKEND}/api/chaos/start`, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({ service: serviceName, fault: faultType })
        });
    } catch(err) {}
  };

  const handleAIAnalysis = async () => {
    if (!selectedNode || isAnalyzing) return;
    
    const dep = deployments.find(d => d.name === selectedNode);
    if (!dep) return;

    setIsAnalyzing(true);
    setIsSpeaking(true); // Open AI panel
    setAnalysis({ answer: "", suggestion: "AI is investigating dependencies...", isFast: false });

    try {
      const url = `${BACKEND}/api/ai/analyze?name=${dep.name}&running=${dep.running}&desired=${dep.desired}&status=${dep.status}`;
      const response = await fetch(url);
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      
      let fullText = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value);
        fullText += chunk;
        setAnalysis(prev => ({ ...prev, answer: fullText }));
      }
      setHasAiResult(true);
    } catch (err) {
      setAnalysis({ answer: "AI Sync Failed.", suggestion: "Check connections." });
      setHasAiResult(false);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleCoreClick = () => {
    setIsSpeaking(true); // Trigger HUD terminal
  };

  const resetView = () => {
    setSelectedNode(null);
    setSelectedPos(null);
    setIsSpeaking(false);
    setIsAnalyzing(false);
  };

  const radius = 14;
  const nodePositions = useMemo(() => 
    deployments.map((_, i) => [
      radius * Math.cos((i / deployments.length) * Math.PI * 2),
      0,
      radius * Math.sin((i / deployments.length) * Math.PI * 2)
    ]), [deployments.length]);

  const getStatusColor = (status) => {
    if (status === "healthy") return "#10b981"; // Green
    if (status === "recovering") return "#facc15"; // Yellow
    if (status === "degraded") return "#fb923c"; // Orange
    return "#f43f5e"; // Red
  };

  return (
    <div style={{ height: "100vh", width: "100vw", background: "#020617", overflow: "hidden", position: "relative" }}>
      
      {/* 🌌 FULLSCREEN 3D VIEWPORT */}
      <div style={{ position: "absolute", inset: 0, zIndex: 1 }}>
        <Canvas camera={{ position: [25, 18, 25], fov: 40, near: 0.1, far: 1000 }} onClick={resetView}>
          <CinematicCamera targetPos={selectedPos} />
          <ambientLight intensity={0.5} />
          <pointLight position={[10, 20, 10]} intensity={2} color="#06b6d4" />
          <Stars radius={150} count={5000} factor={4} fade />
          
          <AICore isSpeaking={isSpeaking} onCoreClick={handleCoreClick} />

          {deployments.map((dep, i) => (
            <React.Fragment key={`group-${dep.name}`}>
              <Node 
                key={`node-${dep.name}`}
                position={nodePositions[i]} 
                status={dep.status} 
                label={dep.name}
                onClick={(e) => { e.stopPropagation(); handleNodeClick(dep, nodePositions[i]); }} 
              />
            </React.Fragment>
          ))}
          
          {dependencies.map((depLink, idx) => {
             const fromIdx = deployments.findIndex(d => d.name === depLink.from);
             const toIdx = deployments.findIndex(d => d.name === depLink.to);
             if (fromIdx === -1 || toIdx === -1) return null;
             
             const startPos = nodePositions[fromIdx];
             const endPos = nodePositions[toIdx];
             const targetStatus = deployments[toIdx].status;
             
             return (
               <React.Fragment key={`link-${idx}`}>
                 <CurvedLine start={startPos} end={endPos} color={getStatusColor(targetStatus)} opacity={0.6} />
                 <FlowParticles start={startPos} end={endPos} count={4} />
               </React.Fragment>
             );
          })}

          <OrbitControls ref={controlsRef} makeDefault enableDamping autoRotate={!selectedNode} autoRotateSpeed={0.5} />
        </Canvas>
      </div>

      {/* 📊 TOP-LEFT OVERLAY: FLEET HEALTH */}
      <aside style={{ position: "absolute", top: "25px", left: "25px", width: "280px", zIndex: 10, background: "rgba(15, 23, 42, 0.7)", backdropFilter: "blur(20px)", padding: "20px", borderRadius: "16px", border: "1px solid rgba(255,255,255,0.1)" }}>
        <div style={{ fontSize: "0.6rem", color: "#10b981", fontWeight: "bold", letterSpacing: "2px", marginBottom: "10px" }}>SYSTEM STATUS</div>
        <SystemChart pods={deployments} />
        
        <div style={{ marginTop: "20px", fontSize: "0.6rem", color: "#06b6d4", fontWeight: "bold", letterSpacing: "1px", marginBottom: "8px" }}>LIVE TRANSITION LOG</div>
        {deployments.filter(d => d.event_message).slice(0, 3).map(d => (
           <div key={`msg-${d.name}`} style={{ fontSize: "0.65rem", color: "#cbd5e1", marginBottom: "6px", borderLeft: `2px solid ${getStatusColor(d.status)}`, paddingLeft: "8px" }}>
             <div style={{ color: getStatusColor(d.status), fontWeight: "bold", fontSize: "0.55rem" }}>{d.name.toUpperCase()}</div>
             <div>{d.event_message}</div>
           </div>
        ))}
      </aside>

      {/* 🛠️ TOP-RIGHT STACK: NEURAL LINK + HUD TERMINAL */}
      <div style={{ 
        position: "absolute", 
        top: "25px", 
        right: "25px", 
        width: "340px", 
        zIndex: 10, 
        display: "flex", 
        flexDirection: "column", 
        gap: "15px" 
      }}>
        
        {/* 1. Neural Link Dialogue (Active Pod Info) */}
        <aside style={{ 
          background: "rgba(15, 23, 42, 0.7)", 
          backdropFilter: "blur(20px)", 
          border: "1px solid rgba(255,255,255,0.1)", 
          padding: "20px", 
          borderRadius: "16px", 
          opacity: selectedNode ? 1 : 0, 
          transform: selectedNode ? "translateX(0)" : "translateX(20px)", 
          transition: "all 0.4s cubic-bezier(0.16, 1, 0.3, 1)" 
        }}>
          <h3 style={{ color: "#06b6d4", fontFamily: "'JetBrains Mono'", fontSize: "0.75rem", margin: 0, letterSpacing: "2px" }}>NEURAL_LINK</h3>
          {analysis && (
            <div style={{ marginTop: "12px", fontFamily: "'JetBrains Mono'", fontSize: "0.80rem", color: "#cbd5e1" }}>
              <div style={{ color: "#10b981", marginBottom: "8px", borderBottom: "1px solid rgba(16, 185, 129, 0.2)", paddingBottom: "4px" }}>&gt; {selectedNode}</div>
              
              <div style={{ minHeight: "60px", marginBottom: "12px", whiteSpace: "pre-wrap", color: analysis.isFast ? "#94a3b8" : "#f8fafc" }}>
                {analysis.isFast ? (
                  analysis.answer 
                ) : (
                  <>
                    <span style={{ color: "#06b6d4" }}>AI Analysis:</span> {analysis.answer}
                    {isAnalyzing && <span className="cursor">█</span>}
                  </>
                )}
              </div>

              {analysis.isFast && (
                <button 
                  onClick={handleAIAnalysis}
                  disabled={isAnalyzing}
                  style={{ 
                    width: "100%", 
                    padding: "8px", 
                    background: "rgba(6, 182, 212, 0.1)", 
                    border: "1px solid #06b6d4", 
                    borderRadius: "8px", 
                    color: "#06b6d4", 
                    fontSize: "0.65rem", 
                    cursor: "pointer",
                    textTransform: "uppercase",
                    letterSpacing: "1px",
                    fontWeight: "bold",
                    transition: "all 0.2s"
                  }}
                  onMouseEnter={(e) => e.target.style.background = "rgba(6, 182, 212, 0.2)"}
                  onMouseLeave={(e) => e.target.style.background = "rgba(6, 182, 212, 0.1)"}
                >
                  {isAnalyzing ? "Analyzing..." : "Run AI Analysis"}
                </button>
              )}

              <div style={{ color: "#f59e0b", marginTop: "12px", fontSize: "0.7rem", fontWeight: "bold" }}>STATUS: {analysis.suggestion}</div>
            </div>
          )}
        </aside>

        {/* 2. HUD Terminal (AI Dialogue) */}
        <aside style={{ 
          background: "rgba(10, 15, 28, 0.8)", 
          backdropFilter: "blur(15px)", 
          border: "1px solid #06b6d4", 
          padding: "15px 20px", 
          borderRadius: "16px", 
          boxShadow: "0 0 30px rgba(6, 182, 212, 0.2)",
          opacity: isSpeaking ? 1 : 0,
          transform: isSpeaking ? "translateY(0)" : "translateY(-10px)",
          transition: "all 0.4s ease",
          minHeight: "120px"
        }}>
          <div style={{ fontSize: "0.6rem", color: "#06b6d4", marginBottom: "8px", fontWeight: "bold" }}>AI_COMMAND_STREAM</div>
          <div style={{ fontFamily: "'JetBrains Mono', monospace", color: "#f8fafc", fontSize: "0.8rem", lineHeight: "1.5" }}>
            {isSpeaking && (
              <Typewriter
                key={selectedNode || 'core-mode'}
                options={{ 
                  strings: [selectedNode ? `> ANALYZING: ${selectedNode}...<br/>> LINKING NEURAL SYNC.` : `> CORE_ONLINE<br/>> SYSTEM PROTOCOLS LOADED.<br/>> STANDBY FOR COMMANDS.`], 
                  autoStart: true, 
                  delay: 60,
                  cursor: "█",
                  pauseFor: 15000
                }}
              />
            )}
          </div>
        </aside>
      </div>

      <nav style={{ position: "absolute", bottom: "30px", left: "50%", transform: "translateX(-50%)", zIndex: 10, display: "flex", gap: "10px", padding: "10px", background: "rgba(15, 23, 42, 0.4)", backdropFilter: "blur(30px)", borderRadius: "20px", border: "1px solid rgba(255,255,255,0.1)", maxWidth: "90vw", overflowX: "auto", scrollbarWidth: "none" }}>
        {deployments.map((dep, i) => (
          <div 
            key={`dock-${dep.name}`} 
            onClick={() => handleNodeClick(dep, nodePositions[i])} 
            style={{ 
              minWidth: "100px", padding: "10px", borderRadius: "14px", cursor: "pointer", 
              textAlign: "center", border: selectedNode === dep.name ? "1px solid #06b6d4" : "1px solid transparent",
              transition: "all 0.2s"
            }}
          >
            <div style={{ width: "22px", height: "22px", borderRadius: "6px", background: getStatusColor(dep.status), margin: "0 auto 6px auto", boxShadow: `0 0 8px ${getStatusColor(dep.status)}` }} />
            <div style={{ fontSize: "0.55rem", fontWeight: "bold", color: "#cbd5e1", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{dep.name}</div>
          </div>
        ))}
      </nav>

      {/* 🌪️ CHAOS INJECTION MODAL AND TOGGLE */}
      <button 
        onClick={() => setShowChaos(!showChaos)}
        style={{ position: 'absolute', bottom: '30px', right: '30px', zIndex: 20, padding: '12px 24px', background: 'rgba(244, 63, 94, 0.2)', border: '1px solid #f43f5e', color: '#f43f5e', borderRadius: '12px', cursor: 'pointer', fontFamily: "'JetBrains Mono'", fontWeight: 'bold', backdropFilter: 'blur(10px)', transition: 'all 0.2s', boxShadow: '0 0 15px rgba(244, 63, 94, 0.2)' }}
      >
        [ ⚡ TRIGGER CHAOS ]
      </button>

      {showChaos && (
        <ChaosModal
           deployments={deployments}
           logs={chaosLogs}
           onInject={handleInjectChaos}
           onClose={() => setShowChaos(false)}
        />
      )}
    </div>
  );
}