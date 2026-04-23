import React, { useMemo } from 'react';

export default function SystemChart({ pods }) {
  const total = pods.length || 1;
  const healthy = pods.filter(p => p.status === "Running").length;
  const healthPercent = Math.round((healthy / total) * 100);

  // Generate a consistent but "random-looking" waveform
  const bars = useMemo(() => {
    return Array.from({ length: 20 }).map(() => ({
      height: 20 + Math.random() * 80,
      opacity: 0.2 + Math.random() * 0.5
    }));
  }, [total]); // Re-generate only when pod count changes

  return (
    <div style={{ width: '100%', marginTop: '15px', fontFamily: "'JetBrains Mono', monospace" }}>
      {/* Health Bar Label */}
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', fontSize: '0.65rem' }}>
        <span style={{ color: '#94a3b8' }}>STABILITY_INDEX</span>
        <span style={{ color: healthPercent > 70 ? '#10b981' : '#f43f5e' }}>{healthPercent}%</span>
      </div>

      {/* Progress Bar */}
      <div style={{ 
        height: '6px', 
        width: '100%', 
        background: 'rgba(30, 41, 59, 0.5)', 
        borderRadius: '3px', 
        overflow: 'hidden',
        border: '1px solid rgba(255,255,255,0.05)'
      }}>
        <div style={{ 
          width: `${healthPercent}%`, 
          height: '100%', 
          background: healthPercent > 70 ? '#10b981' : '#f43f5e',
          boxShadow: `0 0 10px ${healthPercent > 70 ? '#10b981' : '#f43f5e'}`,
          transition: 'width 1s cubic-bezier(0.4, 0, 0.2, 1)'
        }} />
      </div>

      {/* Neural Waveform Visualization */}
      <div style={{ 
        display: 'flex', 
        alignItems: 'flex-end', 
        height: '40px', 
        gap: '3px', 
        marginTop: '20px',
        padding: '0 5px'
      }}>
        {bars.map((bar, i) => (
          <div 
            key={i} 
            style={{ 
              flex: 1, 
              background: healthPercent > 70 ? '#10b981' : '#f43f5e', 
              height: `${bar.height}%`, 
              opacity: bar.opacity,
              borderRadius: '1px',
              transition: 'height 0.3s ease'
            }} 
          />
        ))}
      </div>
      
      <div style={{ fontSize: '0.55rem', color: '#475569', marginTop: '8px', textAlign: 'center', letterSpacing: '1px' }}>
        LIVE_NEURAL_TELEMETRY
      </div>
    </div>
  );
}