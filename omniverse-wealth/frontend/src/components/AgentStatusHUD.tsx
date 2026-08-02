"use client";

import { useState, useEffect } from "react";

interface AgentState {
  name: string;
  label: string;
  status: "idle" | "active" | "done";
}

const initialAgents: AgentState[] = [
  { name: "zeus", label: "Zeus", status: "idle" },
  { name: "stark", label: "Stark", status: "idle" },
  { name: "minerva", label: "Minerva", status: "idle" },
  { name: "morpheus", label: "Morpheus", status: "idle" },
  { name: "themis", label: "Themis", status: "idle" },
  { name: "hermes", label: "Hermes", status: "idle" },
];

export default function AgentStatusHUD() {
  const [agents, setAgents] = useState<AgentState[]>(initialAgents);

  useEffect(() => {
    const interval = setInterval(() => {
      setAgents((prev) =>
        prev.map((a) => ({
          ...a,
          status: Math.random() > 0.75
            ? (["active", "done", "idle"][Math.floor(Math.random() * 3)] as AgentState["status"])
            : a.status,
        }))
      );
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between px-3 py-1.5 border-b border-slate-800">
        <h3 className="text-[10px] font-semibold text-cyan-400 uppercase tracking-wider">
          Agent Network
        </h3>
        <div className="flex items-center gap-1">
          <div className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse-glow" />
          <span className="text-[9px] text-slate-500">Online</span>
        </div>
      </div>
      <div className="flex-1 flex items-center justify-around px-2">
        {agents.map((agent) => (
          <div key={agent.name} className="flex flex-col items-center gap-0.5">
            <div
              className={`w-7 h-7 rounded-full flex items-center justify-center border transition-all duration-300 ${
                agent.status === "active"
                  ? "border-cyan-500/60 bg-cyan-500/15 shadow-[0_0_8px_rgba(6,182,212,0.3)]"
                  : agent.status === "done"
                  ? "border-green-500/60 bg-green-500/10"
                  : "border-slate-700 bg-slate-800/40"
              }`}
            >
              <span className="text-[8px] font-bold text-slate-300">
                {agent.label.slice(0, 1)}
              </span>
            </div>
            <span className="text-[8px] text-slate-500">{agent.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
