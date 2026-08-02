"use client";

import { useEffect, useState } from "react";
import { X, Maximize2 } from "lucide-react";

interface Holding {
  currency: string;
  currentValue: string;
  pnlPercent: string;
  positive: boolean;
  balance?: string;
  avgBuyPrice?: string;
  currentPrice?: string;
}

const COLORS: Record<string, string> = {
  BTC: "#f7931a",
  ETH: "#627eea",
  SOL: "#9945ff",
  DOGE: "#c3a634",
  USDT: "#26a17b",
  USDC: "#2775ca",
};

export default function PortfolioPieChart() {
  const [holdings, setHoldings] = useState<Holding[]>([]);
  const [totalValue, setTotalValue] = useState(0);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    let mounted = true;
    const fetchData = async () => {
      try {
        const res = await fetch("/api/portfolio");
        if (res.ok && mounted) {
          const data = await res.json();
          setHoldings(data.holdings || []);
          setTotalValue(parseFloat(data.totalValue || "0"));
        }
      } catch {}
    };
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => { mounted = false; clearInterval(interval); };
  }, []);

  if (!holdings.length || totalValue === 0) {
    return (
      <div className="h-full flex items-center justify-center text-xs text-slate-500">
        Loading...
      </div>
    );
  }

  const segments = holdings.map((h) => ({
    ...h,
    value: parseFloat(h.currentValue),
    pct: (parseFloat(h.currentValue) / totalValue) * 100,
    color: COLORS[h.currency] || "#6b7280",
  }));

  let cumulativeAngle = 0;
  const arcs = segments.map((seg) => {
    const startAngle = cumulativeAngle;
    const sweepAngle = (seg.pct / 100) * 360;
    cumulativeAngle += sweepAngle;
    const startRad = ((startAngle - 90) * Math.PI) / 180;
    const endRad = (((startAngle + sweepAngle) - 90) * Math.PI) / 180;
    const r = 40;
    const cx = 50, cy = 50;
    const x1 = cx + r * Math.cos(startRad);
    const y1 = cy + r * Math.sin(startRad);
    const x2 = cx + r * Math.cos(endRad);
    const y2 = cy + r * Math.sin(endRad);
    const largeArc = sweepAngle > 180 ? 1 : 0;
    const path = `M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 ${largeArc} 1 ${x2} ${y2} Z`;
    return { ...seg, path };
  });

  // Mini view (in panel)
  const MiniView = () => (
    <div className="h-full flex flex-col">
      <div className="px-3 py-1.5 border-b border-slate-800 flex items-center justify-between">
        <h3 className="text-[10px] font-semibold text-cyan-400 uppercase tracking-wider">
          Asset Allocation
        </h3>
        <button
          onClick={() => setExpanded(true)}
          className="text-slate-500 hover:text-cyan-400 transition"
          title="放大檢視"
        >
          <Maximize2 size={12} />
        </button>
      </div>
      <div
        className="flex-1 flex items-center gap-2 px-3 cursor-pointer hover:bg-slate-800/30 transition"
        onClick={() => setExpanded(true)}
      >
        <div className="w-[60px] h-[60px] flex-shrink-0">
          <svg viewBox="0 0 100 100" className="w-full h-full">
            {arcs.map((arc, i) => (
              <path key={i} d={arc.path} fill={arc.color} stroke="#111827" strokeWidth="0.5" />
            ))}
            <circle cx="50" cy="50" r="20" fill="#111827" />
            <text x="50" y="54" textAnchor="middle" fontSize="8" fontWeight="bold" fill="white">
              {(totalValue / 10000).toFixed(0)}萬
            </text>
          </svg>
        </div>
        <div className="flex-1 space-y-0.5 overflow-hidden">
          {segments.slice(0, 4).map((seg) => (
            <div key={seg.currency} className="flex items-center justify-between">
              <div className="flex items-center gap-1">
                <div className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: seg.color }} />
                <span className="text-[9px] text-white">{seg.currency}</span>
              </div>
              <span className={`text-[8px] font-mono ${seg.positive ? "text-green-400" : "text-red-400"}`}>
                {seg.positive ? "+" : ""}{seg.pnlPercent}%
              </span>
            </div>
          ))}
          {segments.length > 4 && (
            <p className="text-[8px] text-slate-500">+{segments.length - 4} more...</p>
          )}
        </div>
      </div>
    </div>
  );

  // Expanded modal view
  const ExpandedView = () => (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50" onClick={() => setExpanded(false)}>
      <div className="w-full max-w-lg mx-4 bg-[#111827] border border-slate-700 rounded-xl shadow-2xl overflow-hidden" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-700">
          <h2 className="text-lg font-bold text-white">Asset Allocation</h2>
          <button onClick={() => setExpanded(false)} className="text-slate-400 hover:text-white transition">
            <X size={20} />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 flex gap-8">
          {/* Large Pie Chart */}
          <div className="w-[200px] h-[200px] flex-shrink-0">
            <svg viewBox="0 0 100 100" className="w-full h-full">
              {arcs.map((arc, i) => (
                <path key={i} d={arc.path} fill={arc.color} stroke="#111827" strokeWidth="0.3" className="hover:opacity-80 transition" />
              ))}
              <circle cx="50" cy="50" r="18" fill="#111827" />
              <text x="50" y="47" textAnchor="middle" fontSize="5" fill="#94a3b8">Total Value</text>
              <text x="50" y="55" textAnchor="middle" fontSize="7" fontWeight="bold" fill="white">
                {totalValue.toLocaleString()} TWD
              </text>
            </svg>
          </div>

          {/* Detailed Legend */}
          <div className="flex-1 space-y-3">
            {segments.map((seg) => (
              <div key={seg.currency} className="flex items-center justify-between py-1 border-b border-slate-800/50">
                <div className="flex items-center gap-3">
                  <div className="w-3 h-3 rounded-full" style={{ backgroundColor: seg.color }} />
                  <div>
                    <p className="text-sm font-medium text-white">{seg.currency}</p>
                    <p className="text-[11px] text-slate-500">
                      {seg.balance ? `${seg.balance} units` : ""}
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-sm font-mono text-white">
                    {parseInt(seg.currentValue).toLocaleString()} TWD
                  </p>
                  <div className="flex items-center gap-2 justify-end">
                    <span className="text-xs text-slate-400">{seg.pct.toFixed(1)}%</span>
                    <span className={`text-xs font-mono ${seg.positive ? "text-green-400" : "text-red-400"}`}>
                      {seg.positive ? "+" : ""}{seg.pnlPercent}%
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-slate-700 bg-slate-800/30">
          <p className="text-[11px] text-slate-500 text-center">
            資料來源：MAX 交易所即時行情 + 個人歷史交易紀錄 (10,000 筆)
          </p>
        </div>
      </div>
    </div>
  );

  return (
    <>
      <MiniView />
      {expanded && <ExpandedView />}
    </>
  );
}
