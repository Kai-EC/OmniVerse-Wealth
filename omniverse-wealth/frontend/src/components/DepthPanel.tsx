"use client";

import { useEffect, useState } from "react";

interface DepthLevel {
  price: string;
  volume: string;
  total: number;
}

interface DepthPanelProps {
  market?: string;
}

export default function DepthPanel({ market = "btctwd" }: DepthPanelProps) {
  const [asks, setAsks] = useState<DepthLevel[]>([]);
  const [bids, setBids] = useState<DepthLevel[]>([]);

  useEffect(() => {
    let mounted = true;

    const fetchDepth = async () => {
      try {
        const res = await fetch(
          `/api/depth?market=${market}&limit=8`
        );
        if (!res.ok || !mounted) return;
        const data = await res.json();

        const rawAsks = (data.asks || []).slice(0, 8).reverse();
        const rawBids = (data.bids || []).slice(0, 8);

        let askTotal = 0;
        const parsedAsks = rawAsks.map((a: string[]) => {
          askTotal += parseFloat(a[1]);
          return { price: a[0], volume: a[1], total: askTotal };
        });

        let bidTotal = 0;
        const parsedBids = rawBids.map((b: string[]) => {
          bidTotal += parseFloat(b[1]);
          return { price: b[0], volume: b[1], total: bidTotal };
        });

        setAsks(parsedAsks);
        setBids(parsedBids);
      } catch {}
    };

    fetchDepth();
    const interval = setInterval(fetchDepth, 5000);
    return () => { mounted = false; clearInterval(interval); };
  }, [market]);

  const maxTotal = Math.max(
    ...asks.map((a) => a.total),
    ...bids.map((b) => b.total),
    1
  );

  return (
    <div className="h-full flex flex-col">
      <div className="px-3 py-1.5 border-b border-slate-800">
        <h3 className="text-[10px] font-semibold text-cyan-400 uppercase tracking-wider">
          Order Book
        </h3>
      </div>
      <div className="flex-1 overflow-hidden flex flex-col px-2 py-1 text-[10px] font-mono">
        {/* Header */}
        <div className="flex justify-between text-slate-500 mb-0.5 px-1">
          <span>Price (TWD)</span>
          <span>Amount</span>
        </div>

        {/* Asks (sells) */}
        <div className="flex-1 flex flex-col justify-end overflow-hidden">
          {asks.map((a, i) => (
            <div key={`ask-${i}`} className="relative flex justify-between items-center py-[1px] px-1">
              <div
                className="absolute right-0 top-0 bottom-0 bg-red-500/10"
                style={{ width: `${(a.total / maxTotal) * 100}%` }}
              />
              <span className="text-red-400 relative z-10">
                {parseFloat(a.price).toLocaleString()}
              </span>
              <span className="text-slate-400 relative z-10">{parseFloat(a.volume).toFixed(5)}</span>
            </div>
          ))}
        </div>

        {/* Spread indicator */}
        <div className="py-1 text-center border-y border-slate-800/50 my-0.5">
          {asks.length > 0 && bids.length > 0 && (
            <span className="text-slate-400">
              Spread: {(parseFloat(asks[asks.length - 1]?.price || "0") - parseFloat(bids[0]?.price || "0")).toLocaleString()} TWD
            </span>
          )}
        </div>

        {/* Bids (buys) */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {bids.map((b, i) => (
            <div key={`bid-${i}`} className="relative flex justify-between items-center py-[1px] px-1">
              <div
                className="absolute left-0 top-0 bottom-0 bg-green-500/10"
                style={{ width: `${(b.total / maxTotal) * 100}%` }}
              />
              <span className="text-green-400 relative z-10">
                {parseFloat(b.price).toLocaleString()}
              </span>
              <span className="text-slate-400 relative z-10">{parseFloat(b.volume).toFixed(5)}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
