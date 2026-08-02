"use client";

import { useState, useEffect, useCallback } from "react";

type AgentStatus = "idle" | "active" | "done";

interface AgentNode {
  id: string;
  label: string;
  role: string;
  status: AgentStatus;
  angle: number; // Position on orbit (degrees)
}

interface BeamConnection {
  from: string;
  to: string;
  active: boolean;
}

const ORBIT_RADIUS = 85;
const CENTER = { x: 130, y: 130 };
const NODE_RADIUS = 20;

// Pre-computed star positions (static, never re-randomized)
const STARS = (() => {
  const colors = ["#ffffff", "#a5f3fc", "#c4b5fd", "#93c5fd", "#fde68a"];
  const seed = [
    23,67,12,89,45,78,34,56,91,3,62,18,74,41,87,29,53,96,7,65,
    38,82,14,71,49,93,26,58,84,11,69,36,77,22,61,48,88,15,73,42,
    95,6,64,31,79,19,55,83,27,51
  ];
  return seed.map((s, i) => ({
    x: `${(s * 1.07 + i * 1.8) % 90 + 5}%`,
    y: `${(s * 0.93 + i * 2.1) % 90 + 5}%`,
    size: i % 7 === 0 ? 1.5 : 1,
    color: colors[i % colors.length],
    opacity: 0.25 + (s % 5) * 0.1,
    twinkle: i % 3 !== 0,
    delay: `${(s % 50) * 0.1}s`,
    duration: `${2.5 + (s % 30) * 0.1}s`,
  }));
})();

const AGENT_COLORS: Record<string, string> = {
  zeus: "#06b6d4",    // Cyan
  stark: "#3b82f6",   // Blue
  minerva: "#a855f7",  // Purple
  morpheus: "#10b981", // Green
  themis: "#f59e0b",   // Amber
  hermes: "#ef4444",   // Red
};

export interface AgentOrbitHandle {
  triggerFlow: (agents: string[]) => void;
  reset: () => void;
}

interface AgentOrbitGraphProps {
  activeAgents?: string[];
}

export default function AgentOrbitGraph({ activeAgents }: AgentOrbitGraphProps) {
  const [agents, setAgents] = useState<AgentNode[]>([
    { id: "stark", label: "Stark", role: "Market", status: "idle", angle: 0 },
    { id: "minerva", label: "Minerva", role: "Sentiment", status: "idle", angle: 72 },
    { id: "morpheus", label: "Morpheus", role: "History", status: "idle", angle: 144 },
    { id: "themis", label: "Themis", role: "Risk", status: "idle", angle: 216 },
    { id: "hermes", label: "Hermes", role: "Trade", status: "idle", angle: 288 },
  ]);
  const [zeusStatus, setZeusStatus] = useState<AgentStatus>("idle");
  const [beams, setBeams] = useState<BeamConnection[]>([]);
  const [orbitPulse, setOrbitPulse] = useState(false);

  // Simulate agent flow when chat is processing
  useEffect(() => {
    if (!activeAgents || activeAgents.length === 0) return;

    // Phase 1: Zeus activates
    setZeusStatus("active");
    setOrbitPulse(true);

    const t1 = setTimeout(() => {
      // Phase 2: Beams shoot out to target agents
      const newBeams = activeAgents
        .filter((a) => a !== "zeus")
        .map((a) => ({ from: "zeus", to: a, active: true }));
      setBeams(newBeams);

      // Activate target agents
      setAgents((prev) =>
        prev.map((agent) => ({
          ...agent,
          status: activeAgents.includes(agent.id) ? "active" : agent.status,
        }))
      );
    }, 600);

    const t2 = setTimeout(() => {
      // Phase 3: Agents complete, beams return
      setAgents((prev) =>
        prev.map((agent) => ({
          ...agent,
          status: activeAgents.includes(agent.id) ? "done" : agent.status,
        }))
      );
      setBeams((prev) => prev.map((b) => ({ ...b, active: false })));
    }, 3000);

    const t3 = setTimeout(() => {
      // Phase 4: Zeus synthesizes
      setZeusStatus("done");
      setOrbitPulse(false);
      setBeams([]);
    }, 4000);

    const t4 = setTimeout(() => {
      // Reset after animation
      setZeusStatus("idle");
      setAgents((prev) => prev.map((a) => ({ ...a, status: "idle" })));
    }, 8000);

    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);
      clearTimeout(t4);
    };
  }, [activeAgents]);

  // Auto demo animation when idle
  useEffect(() => {
    const interval = setInterval(() => {
      if (zeusStatus === "idle") {
        // Random subtle pulse on a random agent
        setAgents((prev) => {
          const idx = Math.floor(Math.random() * prev.length);
          return prev.map((a, i) => ({
            ...a,
            status: i === idx ? "active" : a.status === "active" ? "idle" : a.status,
          }));
        });
        setTimeout(() => {
          setAgents((prev) => prev.map((a) => ({ ...a, status: "idle" })));
        }, 1500);
      }
    }, 5000);
    return () => clearInterval(interval);
  }, [zeusStatus]);

  // Calculate node position from angle
  const getPosition = (angle: number) => ({
    x: CENTER.x + ORBIT_RADIUS * Math.cos(((angle - 90) * Math.PI) / 180),
    y: CENTER.y + ORBIT_RADIUS * Math.sin(((angle - 90) * Math.PI) / 180),
  });

  return (
    <div className="h-full flex flex-col">
      <div className="px-3 py-1.5 border-b border-slate-800 flex items-center justify-between">
        <h3 className="text-[10px] font-semibold text-cyan-400 uppercase tracking-wider">
          Agent Collaboration
        </h3>
        <div className="flex items-center gap-1">
          <div className={`w-1.5 h-1.5 rounded-full ${zeusStatus === "idle" ? "bg-green-400" : "bg-cyan-400 animate-pulse"}`} />
          <span className="text-[9px] text-slate-500">
            {zeusStatus === "idle" ? "Standby" : "Processing"}
          </span>
        </div>
      </div>

      <div className="flex-1 flex items-center justify-center relative overflow-hidden">
        {/* Deep space background */}
        <div className="absolute inset-0 bg-[#040810]" />

        {/* Static stars with opacity twinkle only */}
        <div className="absolute inset-0">
          {STARS.map((star, i) => (
            <div
              key={`s${i}`}
              className={star.twinkle ? "animate-twinkle" : ""}
              style={{
                position: "absolute",
                left: star.x,
                top: star.y,
                width: `${star.size}px`,
                height: `${star.size}px`,
                borderRadius: "50%",
                backgroundColor: star.color,
                opacity: star.opacity,
                animationDelay: star.delay,
                animationDuration: star.duration,
              }}
            />
          ))}
        </div>

        {/* Nebula layer 1 — large cyan cloud */}
        <div
          className="absolute rounded-full blur-3xl opacity-[0.07]"
          style={{
            width: "180px", height: "120px",
            top: "20%", left: "10%",
            background: "radial-gradient(ellipse, #06b6d4 0%, transparent 70%)",
          }}
        />

        {/* Nebula layer 2 — purple cloud */}
        <div
          className="absolute rounded-full blur-3xl opacity-[0.06]"
          style={{
            width: "140px", height: "160px",
            bottom: "15%", right: "10%",
            background: "radial-gradient(ellipse, #8b5cf6 0%, transparent 70%)",
          }}
        />

        {/* Nebula layer 3 — blue wisp */}
        <div
          className="absolute rounded-full blur-2xl opacity-[0.05]"
          style={{
            width: "100px", height: "80px",
            top: "55%", left: "45%",
            background: "radial-gradient(ellipse, #3b82f6 0%, transparent 70%)",
          }}
        />

        {/* Nebula layer 4 — warm accent */}
        <div
          className="absolute rounded-full blur-3xl opacity-[0.04]"
          style={{
            width: "120px", height: "90px",
            top: "10%", right: "20%",
            background: "radial-gradient(ellipse, #f59e0b 0%, transparent 70%)",
          }}
        />

        {/* Subtle dust band across middle */}
        <div
          className="absolute opacity-[0.03]"
          style={{
            width: "100%", height: "40px",
            top: "48%",
            background: "linear-gradient(to right, transparent, #06b6d4, #8b5cf6, #3b82f6, transparent)",
            filter: "blur(8px)",
            transform: "rotate(-5deg)",
          }}
        />

        {/* Slow rotating outer dust ring */}
        <div className="absolute inset-[10%] rounded-full border border-slate-700/20 animate-orbit-spin" style={{ animationDuration: '40s' }} />

        {/* Center energy core */}
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="w-[50px] h-[50px] rounded-full bg-cyan-500/5 blur-2xl animate-pulse-glow" />
        </div>

        <svg viewBox="0 0 260 260" className="w-full h-full max-w-[260px] max-h-[260px] relative z-10">
          <defs>
            {/* Glow filters */}
            <filter id="glow-cyan" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
            <filter id="glow-strong" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="5" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>

            {/* Beam gradient */}
            <linearGradient id="beam-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#06b6d4" stopOpacity="0" />
              <stop offset="50%" stopColor="#06b6d4" stopOpacity="1" />
              <stop offset="100%" stopColor="#06b6d4" stopOpacity="0" />
            </linearGradient>
          </defs>

          {/* Orbit ring */}
          <circle
            cx={CENTER.x}
            cy={CENTER.y}
            r={ORBIT_RADIUS}
            fill="none"
            stroke="#1e293b"
            strokeWidth="1"
            strokeDasharray="4 4"
            className={orbitPulse ? "animate-orbit-spin" : ""}
          />

          {/* Outer decorative ring */}
          <circle
            cx={CENTER.x}
            cy={CENTER.y}
            r={ORBIT_RADIUS + 15}
            fill="none"
            stroke="#0f172a"
            strokeWidth="0.5"
          />

          {/* Beam connections */}
          {beams.map((beam) => {
            const toAgent = agents.find((a) => a.id === beam.to);
            if (!toAgent) return null;
            const pos = getPosition(toAgent.angle);
            return (
              <line
                key={`beam-${beam.from}-${beam.to}`}
                x1={CENTER.x}
                y1={CENTER.y}
                x2={pos.x}
                y2={pos.y}
                stroke={AGENT_COLORS[beam.to]}
                strokeWidth={beam.active ? 2 : 1}
                opacity={beam.active ? 0.8 : 0.3}
                className={beam.active ? "animate-beam-pulse" : ""}
                filter={beam.active ? "url(#glow-cyan)" : ""}
              />
            );
          })}

          {/* Traveling particles on beams */}
          {beams.filter((b) => b.active).map((beam) => {
            const toAgent = agents.find((a) => a.id === beam.to);
            if (!toAgent) return null;
            const pos = getPosition(toAgent.angle);
            return (
              <circle key={`particle-${beam.to}`} r="3" fill={AGENT_COLORS[beam.to]} filter="url(#glow-cyan)">
                <animateMotion
                  dur="1s"
                  repeatCount="indefinite"
                  path={`M${CENTER.x},${CENTER.y} L${pos.x},${pos.y}`}
                />
              </circle>
            );
          })}

          {/* Outer agent nodes */}
          {agents.map((agent) => {
            const pos = getPosition(agent.angle);
            const color = AGENT_COLORS[agent.id];
            const isActive = agent.status === "active";
            const isDone = agent.status === "done";

            return (
              <g key={agent.id}>
                {/* Node background glow */}
                {(isActive || isDone) && (
                  <circle
                    cx={pos.x}
                    cy={pos.y}
                    r={NODE_RADIUS + 4}
                    fill="none"
                    stroke={isDone ? "#10b981" : color}
                    strokeWidth="1"
                    opacity="0.4"
                    className={isActive ? "animate-ping-slow" : ""}
                  />
                )}

                {/* Node circle */}
                <circle
                  cx={pos.x}
                  cy={pos.y}
                  r={NODE_RADIUS}
                  fill={isActive || isDone ? `${color}20` : "#1e293b"}
                  stroke={isDone ? "#10b981" : isActive ? color : "#374151"}
                  strokeWidth={isActive ? 2 : 1}
                  filter={isActive ? "url(#glow-cyan)" : ""}
                />

                {/* Agent label */}
                <text
                  x={pos.x}
                  y={pos.y - 3}
                  textAnchor="middle"
                  fontSize="8"
                  fontWeight="bold"
                  fill={isActive || isDone ? "white" : "#94a3b8"}
                >
                  {agent.label}
                </text>
                <text
                  x={pos.x}
                  y={pos.y + 7}
                  textAnchor="middle"
                  fontSize="6"
                  fill="#64748b"
                >
                  {agent.role}
                </text>

                {/* Done checkmark */}
                {isDone && (
                  <text
                    x={pos.x + 12}
                    y={pos.y - 12}
                    fontSize="10"
                    fill="#10b981"
                  >
                    ✓
                  </text>
                )}
              </g>
            );
          })}

          {/* Center: Zeus node */}
          <g>
            {/* Zeus always-on subtle glow */}
            <circle
              cx={CENTER.x}
              cy={CENTER.y}
              r={30}
              fill="none"
              stroke="#06b6d4"
              strokeWidth="0.5"
              opacity="0.3"
              className="animate-ping-slow"
            />

            {/* Zeus active glow ring */}
            {zeusStatus !== "idle" && (
              <circle
                cx={CENTER.x}
                cy={CENTER.y}
                r={28}
                fill="none"
                stroke="#06b6d4"
                strokeWidth="1.5"
                opacity="0.6"
                className="animate-ping-slow"
              />
            )}

            {/* Zeus circle */}
            <circle
              cx={CENTER.x}
              cy={CENTER.y}
              r={24}
              fill="#06b6d410"
              stroke={zeusStatus === "done" ? "#10b981" : "#06b6d4"}
              strokeWidth={zeusStatus !== "idle" ? 2.5 : 1.5}
              filter="url(#glow-cyan)"
            />

            {/* Zeus label */}
            <text
              x={CENTER.x}
              y={CENTER.y - 3}
              textAnchor="middle"
              fontSize="10"
              fontWeight="bold"
              fill={zeusStatus !== "idle" ? "#06b6d4" : "#e2e8f0"}
            >
              Zeus
            </text>
            <text
              x={CENTER.x}
              y={CENTER.y + 8}
              textAnchor="middle"
              fontSize="6"
              fill="#64748b"
            >
              Commander
            </text>
          </g>
        </svg>
      </div>
    </div>
  );
}
