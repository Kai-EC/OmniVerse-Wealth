"use client";

import { useEffect, useState } from "react";

interface TickerData {
  market: string;
  symbol: string;
  last: string;
  changePct: string;
  positive: boolean;
}

export default function Header() {
  const [tickers, setTickers] = useState<TickerData[]>([]);
  const [apiConnected, setApiConnected] = useState(false);
  const [wsConnected, setWsConnected] = useState(false);

  // REST polling fallback
  useEffect(() => {
    const fetchTickers = async () => {
      try {
        const res = await fetch("/api/ticker");
        if (res.ok) {
          const data = await res.json();
          setTickers(data.tickers || []);
          setApiConnected(true);
        } else {
          setApiConnected(false);
        }
      } catch {
        setApiConnected(false);
      }
    };
    fetchTickers();
    const interval = setInterval(fetchTickers, 10000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    let mounted = true;
    let ws: WebSocket | null = null;
    let pingInterval: NodeJS.Timeout | null = null;
    let reconnectTimer: NodeJS.Timeout | null = null;
    let reconnectCount = 0;

    const connect = () => {
      if (!mounted) return;
      try {
        ws = new WebSocket("ws://localhost:8080");

        ws.onopen = () => {
          if (!mounted) return;
          setWsConnected(true);
          reconnectCount = 0;
          pingInterval = setInterval(() => {
            if (ws?.readyState === WebSocket.OPEN) {
              ws.send(JSON.stringify({ event: "ping" }));
            }
          }, 30000);
        };

        ws.onmessage = (event) => {
          if (!mounted) return;
          try {
            const msg = JSON.parse(event.data);
            if (msg.event === "ticker_update" && msg.data) {
              const updated: TickerData[] = Object.values(msg.data).map((t: any) => {
                const last = parseFloat(t.last);
                const open = parseFloat(t.open);
                const changePct = open > 0 ? ((last - open) / open) * 100 : 0;
                return {
                  market: t.market,
                  symbol: t.market.replace("twd", "").toUpperCase() + "/TWD",
                  last: t.last,
                  changePct: changePct.toFixed(2),
                  positive: changePct >= 0,
                };
              });
              setTickers(updated);
              setApiConnected(true);
            }
          } catch {}
        };

        ws.onclose = () => {
          if (!mounted) return;
          setWsConnected(false);
          if (pingInterval) clearInterval(pingInterval);
          // Auto reconnect with backoff
          if (reconnectCount < 5) {
            const delay = Math.min(2000 * Math.pow(1.5, reconnectCount), 15000);
            reconnectTimer = setTimeout(() => {
              reconnectCount++;
              connect();
            }, delay);
          }
        };

        ws.onerror = () => {
          if (!mounted) return;
          setWsConnected(false);
        };
      } catch {
        setWsConnected(false);
      }
    };

    connect();

    return () => {
      mounted = false;
      if (pingInterval) clearInterval(pingInterval);
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (ws) { ws.onmessage = null; ws.onclose = null; ws.onerror = null; ws.close(); }
    };
  }, []);

  // Format price with thousands separator
  const formatPrice = (price: string) => {
    const num = parseFloat(price);
    if (num >= 1000000) return (num / 10000).toFixed(1) + "萬";
    if (num >= 10000) return num.toLocaleString("en-US", { maximumFractionDigits: 0 });
    if (num >= 100) return num.toLocaleString("en-US", { maximumFractionDigits: 1 });
    return num.toLocaleString("en-US", { maximumFractionDigits: 2 });
  };

  return (
    <header className="h-12 flex items-center justify-between px-4 border-b border-slate-800 bg-[#0d1320]">
      {/* Logo & Title */}
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-cyan-400 to-purple-500 flex items-center justify-center">
          <span className="text-xs font-bold text-white">OW</span>
        </div>
        <div>
          <h1 className="text-sm font-bold text-white tracking-wide">
            OmniVerse Wealth
          </h1>
          <p className="text-[10px] text-slate-500">
            Multi-Agent AI Investment Assistant
          </p>
        </div>
      </div>

      {/* Center: Live Market Tickers */}
      <div className="hidden md:flex items-center gap-6 text-xs">
        {tickers.length > 0 ? (
          tickers.slice(0, 4).map((t) => (
            <TickerItem
              key={t.market}
              symbol={t.symbol}
              price={formatPrice(t.last)}
              change={`${t.positive ? "+" : ""}${t.changePct}%`}
              positive={t.positive}
            />
          ))
        ) : (
          <span className="text-slate-500 text-xs">Loading tickers...</span>
        )}
      </div>

      {/* Right: Status Indicators */}
      <div className="flex items-center gap-4">
        <StatusDot label="API" connected={apiConnected} />
        <StatusDot label="WS" connected={wsConnected} />
        <StatusDot label="Agent" connected={true} />
      </div>
    </header>
  );
}

function TickerItem({
  symbol,
  price,
  change,
  positive,
}: {
  symbol: string;
  price: string;
  change: string;
  positive: boolean;
}) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-slate-400">{symbol}</span>
      <span className="font-mono text-white">{price}</span>
      <span className={positive ? "text-green-400" : "text-red-400"}>
        {change}
      </span>
    </div>
  );
}

function StatusDot({ label, connected }: { label: string; connected: boolean }) {
  return (
    <div className="flex items-center gap-1">
      <div
        className={`w-2 h-2 rounded-full ${
          connected ? "bg-green-400 animate-pulse-glow" : "bg-slate-600"
        }`}
      />
      <span className="text-[10px] text-slate-500">{label}</span>
    </div>
  );
}
