import { useRef, useEffect, useCallback } from 'react';
import { AGENTS, AGENT_ORDER } from '../utils/constants';

/**
 * Canvas-based agent constellation visualization.
 * Shows 4 agent nodes with animated connections and a central ledger node.
 * Uses requestAnimationFrame with delta-time for smooth 60fps rendering.
 */
export default function AgentConstellation({ agents, activeAgentIndex, ledgerEntries }) {
  const canvasRef = useRef(null);
  const animRef = useRef(null);
  const timeRef = useRef(0);
  const particlesRef = useRef([]);

  const draw = useCallback((canvas, ctx, time) => {
    const dpr = window.devicePixelRatio || 1;
    const w = canvas.width / dpr;
    const h = canvas.height / dpr;
    const cx = w / 2;
    const cy = h / 2;
    const radius = Math.min(w, h) * 0.3;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Background particles (star field — 40 recycled particles)
    if (particlesRef.current.length === 0) {
      for (let i = 0; i < 40; i++) {
        particlesRef.current.push({
          x: Math.random() * w,
          y: Math.random() * h,
          size: Math.random() * 1.5 + 0.5,
          speed: Math.random() * 0.3 + 0.1,
          opacity: Math.random() * 0.4 + 0.1,
        });
      }
    }
    particlesRef.current.forEach((p) => {
      p.y += p.speed;
      if (p.y > h) { p.y = 0; p.x = Math.random() * w; }
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(0, 229, 255, ${p.opacity * (0.5 + 0.5 * Math.sin(time * 0.001 + p.x))})`;
      ctx.fill();
    });

    // Agent node positions (cardinal arrangement)
    const positions = AGENT_ORDER.map((_, i) => {
      const angle = (i / AGENT_ORDER.length) * Math.PI * 2 - Math.PI / 2;
      return {
        x: cx + Math.cos(angle) * radius,
        y: cy + Math.sin(angle) * radius + Math.sin(time * 0.002 + i) * 4,
      };
    });

    // Draw connections between agents (bezier curves)
    positions.forEach((pos, i) => {
      positions.forEach((pos2, j) => {
        if (j <= i) return;
        ctx.beginPath();
        ctx.moveTo(pos.x, pos.y);
        ctx.lineTo(pos2.x, pos2.y);
        ctx.strokeStyle = 'rgba(255,255,255,0.03)';
        ctx.lineWidth = 1;
        ctx.stroke();
      });

      // Connection to center (ledger)
      ctx.beginPath();
      ctx.moveTo(pos.x, pos.y);
      ctx.lineTo(cx, cy);
      const agentData = agents[i];
      const isActive = agentData?.status === 'active';
      const isSuccess = agentData?.status === 'success';

      if (isActive) {
        ctx.strokeStyle = `rgba(68, 138, 255, ${0.3 + 0.2 * Math.sin(time * 0.004)})`;
        ctx.lineWidth = 2;
        ctx.setLineDash([6, 8]);
        ctx.lineDashOffset = -time * 0.05;
      } else if (isSuccess) {
        ctx.strokeStyle = 'rgba(0, 230, 118, 0.15)';
        ctx.lineWidth = 1.5;
        ctx.setLineDash([]);
      } else {
        ctx.strokeStyle = 'rgba(255,255,255,0.04)';
        ctx.lineWidth = 1;
        ctx.setLineDash([]);
      }
      ctx.stroke();
      ctx.setLineDash([]);
    });

    // Draw central ledger node
    const ledgerPulse = 1 + Math.sin(time * 0.003) * 0.1;
    const ledgerRadius = 22 * ledgerPulse;

    // Glow
    const glow = ctx.createRadialGradient(cx, cy, 0, cx, cy, ledgerRadius * 3);
    glow.addColorStop(0, `rgba(0, 229, 255, ${ledgerEntries.length > 0 ? 0.12 : 0.04})`);
    glow.addColorStop(1, 'rgba(0, 229, 255, 0)');
    ctx.fillStyle = glow;
    ctx.fillRect(cx - ledgerRadius * 3, cy - ledgerRadius * 3, ledgerRadius * 6, ledgerRadius * 6);

    ctx.beginPath();
    ctx.arc(cx, cy, ledgerRadius, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(10, 14, 26, 0.9)';
    ctx.fill();
    ctx.strokeStyle = ledgerEntries.length > 0 ? 'rgba(0, 229, 255, 0.5)' : 'rgba(255,255,255,0.1)';
    ctx.lineWidth = 2;
    ctx.stroke();

    // Ledger label
    ctx.font = '10px Inter, sans-serif';
    ctx.fillStyle = 'rgba(255,255,255,0.5)';
    ctx.textAlign = 'center';
    ctx.fillText('LEDGER', cx, cy + 4);

    // Draw agent nodes
    positions.forEach((pos, i) => {
      const agentId = AGENT_ORDER[i];
      const agentMeta = AGENTS[agentId];
      const agentState = agents[i];
      const nodeRadius = 26;

      // Node glow for active/success
      if (agentState?.status === 'active') {
        const ag = ctx.createRadialGradient(pos.x, pos.y, 0, pos.x, pos.y, nodeRadius * 3);
        ag.addColorStop(0, `${agentMeta.color}22`);
        ag.addColorStop(1, `${agentMeta.color}00`);
        ctx.fillStyle = ag;
        ctx.fillRect(pos.x - nodeRadius * 3, pos.y - nodeRadius * 3, nodeRadius * 6, nodeRadius * 6);
      }

      // Node circle
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, nodeRadius, 0, Math.PI * 2);
      ctx.fillStyle = agentState?.status === 'active'
        ? `${agentMeta.color}20`
        : agentState?.status === 'success'
        ? 'rgba(0, 230, 118, 0.08)'
        : agentState?.status === 'error'
        ? 'rgba(255, 23, 68, 0.08)'
        : 'rgba(15, 20, 36, 0.8)';
      ctx.fill();

      ctx.strokeStyle = agentState?.status === 'active'
        ? agentMeta.color
        : agentState?.status === 'success'
        ? '#00e676'
        : agentState?.status === 'error'
        ? '#ff1744'
        : 'rgba(255,255,255,0.08)';
      ctx.lineWidth = agentState?.status === 'active' ? 2.5 : 1.5;
      ctx.stroke();

      // Icon
      ctx.font = '16px serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillStyle = '#fff';
      ctx.fillText(agentMeta.icon, pos.x, pos.y - 1);

      // Label
      ctx.font = '600 10px Inter, sans-serif';
      ctx.fillStyle = agentState?.status === 'active' ? agentMeta.color : 'rgba(255,255,255,0.5)';
      ctx.textBaseline = 'top';
      ctx.fillText(agentMeta.name, pos.x, pos.y + nodeRadius + 6);

      // Status indicator dot
      if (agentState?.status === 'success') {
        ctx.beginPath();
        ctx.arc(pos.x + nodeRadius - 4, pos.y - nodeRadius + 4, 5, 0, Math.PI * 2);
        ctx.fillStyle = '#00e676';
        ctx.fill();
        ctx.font = '7px sans-serif';
        ctx.fillStyle = '#000';
        ctx.textBaseline = 'middle';
        ctx.fillText('✓', pos.x + nodeRadius - 4, pos.y - nodeRadius + 5);
      } else if (agentState?.status === 'error') {
        ctx.beginPath();
        ctx.arc(pos.x + nodeRadius - 4, pos.y - nodeRadius + 4, 5, 0, Math.PI * 2);
        ctx.fillStyle = '#ff1744';
        ctx.fill();
        ctx.font = '7px sans-serif';
        ctx.fillStyle = '#fff';
        ctx.textBaseline = 'middle';
        ctx.fillText('✗', pos.x + nodeRadius - 4, pos.y - nodeRadius + 5);
      }
    });

    // Data flow particles (active agent → ledger)
    if (activeAgentIndex >= 0 && agents[activeAgentIndex]?.status === 'active') {
      const from = positions[activeAgentIndex];
      for (let p = 0; p < 3; p++) {
        const t = ((time * 0.002 + p * 0.33) % 1);
        const px = from.x + (cx - from.x) * t;
        const py = from.y + (cy - from.y) * t;
        ctx.beginPath();
        ctx.arc(px, py, 2.5 - t * 1.5, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(0, 229, 255, ${0.8 - t * 0.6})`;
        ctx.fill();
      }
    }
  }, [agents, activeAgentIndex, ledgerEntries]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const resize = () => {
      const rect = canvas.parentElement.getBoundingClientRect();
      canvas.width = rect.width * devicePixelRatio;
      canvas.height = rect.height * devicePixelRatio;
      canvas.style.width = rect.width + 'px';
      canvas.style.height = rect.height + 'px';
      ctx.scale(devicePixelRatio, devicePixelRatio);
    };
    resize();
    window.addEventListener('resize', resize);

    const loop = (ts) => {
      timeRef.current = ts;
      ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
      draw(canvas, ctx, ts);
      animRef.current = requestAnimationFrame(loop);
    };
    animRef.current = requestAnimationFrame(loop);

    return () => {
      cancelAnimationFrame(animRef.current);
      window.removeEventListener('resize', resize);
    };
  }, [draw]);

  return (
    <div className="constellation-panel panel glass">
      <div className="panel-header">
        <span className="panel-title">🌌 Agent Constellation</span>
        <span className="panel-badge">{agents.filter(a => a.status === 'success').length}/4 committed</span>
      </div>
      <canvas ref={canvasRef} className="constellation-canvas" />
    </div>
  );
}
