"use client";

import { useEffect, useState } from "react";
import { TrendingUp, TrendingDown, RefreshCw } from "lucide-react";

interface HoldingItem {
  currency: string;
  balance: string;
  avgBuyPrice: string;
  currentPrice: string;
  currentValue: string;
  pnlPercent: string;
  positive: boolean;
  buyCount: number;
  sellCount: number;
}

export default function PortfolioPanel() {
  const [holdings, setHoldings] = useState<HoldingItem[]>([]);
  const [totalValue, setTotalValue] = useState("0");
  const [loading, setLoading] = useState(true);

  const fetchPortfolio = async () => {
    try {
      const res = await fetch("/api/portfolio");
      if (res.ok) {
        const data = await res.json();
        setHoldings(data.holdings || []);
        setTotalValue(data.totalValue || "0");
      }
    } catch {}
    setLoading(false);
  };

  useEffect(() => {
    let mounted = true;
    const doFetch = async () => {
      await fetchPortfolio();
      if (!mounted) return;
    };
    doFetch();
    const interval = setInterval(doFetch, 30000);
    return () => { mounted = false; clearInterval(interval); };
  }, []);

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-slate-800">
        <h3 className="text-xs font-semibold text-cyan-400 uppercase tracking-wider">
          Portfolio
        </h3>
        <div className="flex items-center gap-2">
          <button onClick={fetchPortfolio} className="text-slate-500 hover:text-cyan-400 transition">
            <RefreshCw size={10} />
          </button>
          <div className="text-right">
            <p className="text-xs text-slate-500">Total</p>
            <p className="text-sm font-mono font-bold text-white">
              {parseInt(totalValue).toLocaleString()} TWD
            </p>
          </div>
        </div>
      </div>

      {/* Holdings List */}
      <div className="flex-1 overflow-y-auto px-3 py-2 space-y-1">
        {loading ? (
          <p className="text-xs text-slate-500 text-center py-4">Loading...</p>
        ) : holdings.length === 0 ? (
          <p className="text-xs text-slate-500 text-center py-4">No holdings</p>
        ) : (
          holdings.map((h) => <HoldingRow key={h.currency} holding={h} />)
        )}
      </div>
    </div>
  );
}

function HoldingRow({ holding }: { holding: HoldingItem }) {
  return (
    <div className="flex items-center justify-between py-1.5 px-2 rounded hover:bg-slate-800/50 transition">
      <div className="flex items-center gap-2">
        <div className="w-6 h-6 rounded-full bg-slate-700 flex items-center justify-center">
          <span className="text-[9px] font-bold text-slate-300">
            {holding.currency.slice(0, 2)}
          </span>
        </div>
        <div>
          <p className="text-xs font-medium text-white">{holding.currency}</p>
          <p className="text-[10px] text-slate-500 font-mono">{holding.balance}</p>
        </div>
      </div>
      <div className="text-right">
        <p className="text-xs font-mono text-white">
          {parseInt(holding.currentValue).toLocaleString()}
        </p>
        <div className="flex items-center justify-end gap-0.5">
          {holding.positive ? (
            <TrendingUp size={10} className="text-green-400" />
          ) : (
            <TrendingDown size={10} className="text-red-400" />
          )}
          <span
            className={`text-[10px] font-mono ${
              holding.positive ? "text-green-400" : "text-red-400"
            }`}
          >
            {holding.positive ? "+" : ""}
            {holding.pnlPercent}%
          </span>
        </div>
      </div>
    </div>
  );
}
