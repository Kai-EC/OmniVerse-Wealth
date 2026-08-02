"use client";

import { useEffect, useState } from "react";

interface TradeItem {
  id: number;
  price: string;
  volume: string;
  side: string;
  timestamp: number;
}

interface TradesPanelProps {
  market?: string;
}

export default function TradesPanel({ market = "btctwd" }: TradesPanelProps) {
  const [trades, setTrades] = useState<TradeItem[]>([]);

  useEffect(() => {
    let mounted = true;

    const fetchTrades = async () => {
      try {
        const res = await fetch(
          `/api/trades?market=${market}&limit=20`
        );
        if (!res.ok || !mounted) return;
        const data = await res.json();
        setTrades(
          data.map((t: any) => ({
            id: t.id,
            price: t.price,
            volume: t.volume,
            side: t.side, // "bid" = buy, "ask" = sell
            timestamp: t.created_at,
          }))
        );
      } catch {}
    };

    fetchTrades();
    const interval = setInterval(fetchTrades, 5000);
    return () => { mounted = false; clearInterval(interval); };
  }, [market]);

  const formatTime = (ts: number) => {
    const d = new Date(ts);
    return d.toLocaleTimeString("zh-TW", { hour12: false });
  };

  return (
    <div className="h-full flex flex-col">
      <div className="px-3 py-1.5 border-b border-slate-800">
        <h3 className="text-[10px] font-semibold text-cyan-400 uppercase tracking-wider">
          Recent Trades
        </h3>
      </div>
      <div className="flex-1 overflow-y-auto px-2 py-1">
        {/* Header */}
        <div className="flex justify-between text-[9px] text-slate-500 px-1 mb-0.5">
          <span>Price</span>
          <span>Amount</span>
          <span>Time</span>
        </div>
        {trades.map((t) => {
          const isBuy = t.side === "bid";
          return (
            <div
              key={t.id}
              className="flex justify-between items-center py-[2px] px-1 text-[10px] font-mono"
            >
              <span className={isBuy ? "text-green-400" : "text-red-400"}>
                {parseFloat(t.price).toLocaleString()}
              </span>
              <span className="text-slate-400">
                {parseFloat(t.volume).toFixed(5)}
              </span>
              <span className="text-slate-600">
                {formatTime(t.timestamp)}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
