"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import {
  createChart,
  type IChartApi,
  type ISeriesApi,
  type Time,
  CandlestickSeries,
} from "lightweight-charts";

interface KlineData {
  time: Time;
  open: number;
  high: number;
  low: number;
  close: number;
}

export default function ChartPanel() {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const [market, setMarket] = useState("btctwd");
  const [lastPrice, setLastPrice] = useState<string>("");
  const [priceChange, setPriceChange] = useState<string>("");
  const [isPositive, setIsPositive] = useState(true);
  const [loading, setLoading] = useState(true);

  // Fetch real K-line data from MAX API
  const fetchKlines = useCallback(async (mkt: string) => {
    setLoading(true);
    try {
      const res = await fetch(`/api/klines?market=${mkt}&period=60&limit=100`);
      if (!res.ok) return [];
      const data = await res.json();
      const klines: KlineData[] = (data.klines || []).map((k: any) => ({
        time: k.time as Time,
        open: k.open,
        high: k.high,
        low: k.low,
        close: k.close,
      }));
      return klines;
    } catch {
      return [];
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch live ticker for header display
  const fetchTicker = useCallback(async (mkt: string) => {
    try {
      const res = await fetch(`/api/ticker`);
      if (!res.ok) return;
      const data = await res.json();
      const ticker = data.tickers?.find((t: any) => t.market === mkt);
      if (ticker) {
        setLastPrice(parseFloat(ticker.last).toLocaleString("en-US", { maximumFractionDigits: 1 }));
        setPriceChange(`${ticker.positive ? "+" : ""}${ticker.changePct}%`);
        setIsPositive(ticker.positive);
      }
    } catch {}
  }, []);

  // Initialize chart and load data
  useEffect(() => {
    if (!chartRef.current) return;

    const chart = createChart(chartRef.current, {
      layout: {
        background: { color: "#111827" },
        textColor: "#94a3b8",
        fontSize: 11,
      },
      grid: {
        vertLines: { color: "#1e293b" },
        horzLines: { color: "#1e293b" },
      },
      crosshair: {
        vertLine: { color: "#06b6d4", width: 1, style: 2 },
        horzLine: { color: "#06b6d4", width: 1, style: 2 },
      },
      timeScale: {
        borderColor: "#1e293b",
        timeVisible: true,
      },
      rightPriceScale: {
        borderColor: "#1e293b",
      },
    });

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: "#10b981",
      downColor: "#ef4444",
      borderUpColor: "#10b981",
      borderDownColor: "#ef4444",
      wickUpColor: "#10b981",
      wickDownColor: "#ef4444",
    });

    chartInstance.current = chart;
    seriesRef.current = candleSeries;

    // Load real data
    fetchKlines(market).then((klines) => {
      if (klines.length > 0) {
        candleSeries.setData(klines);
        chart.timeScale().fitContent();
      }
    });

    // Fetch ticker
    fetchTicker(market);

    // Auto-refresh ticker every 5 seconds
    const tickerInterval = setInterval(() => fetchTicker(market), 5000);

    // Refresh K-lines every 60 seconds (new candle)
    const klineInterval = setInterval(async () => {
      const klines = await fetchKlines(market);
      if (klines.length > 0 && seriesRef.current) {
        seriesRef.current.setData(klines);
      }
    }, 60000);

    // Handle resize
    const resizeObserver = new ResizeObserver(() => {
      if (chartRef.current) {
        chart.applyOptions({
          width: chartRef.current.clientWidth,
          height: chartRef.current.clientHeight,
        });
      }
    });
    resizeObserver.observe(chartRef.current);

    return () => {
      clearInterval(tickerInterval);
      clearInterval(klineInterval);
      resizeObserver.disconnect();
      chart.remove();
    };
  }, [market, fetchKlines, fetchTicker]);

  // Listen for WebSocket ticker updates to update last candle
  useEffect(() => {
    let ws: WebSocket | null = null;
    let mounted = true;
    let reconnectTimer: NodeJS.Timeout | null = null;

    const connect = () => {
      if (!mounted) return;
      try {
        ws = new WebSocket("ws://localhost:8080");
        ws.onmessage = (event) => {
          if (!mounted) return;
          try {
            const msg = JSON.parse(event.data);
            if (msg.event === "ticker_update" && msg.data[market]) {
              const t = msg.data[market];
              const last = parseFloat(t.last);
              const open = parseFloat(t.open);
              const change = open > 0 ? ((last - open) / open) * 100 : 0;

              setLastPrice(last.toLocaleString("en-US", { maximumFractionDigits: 1 }));
              setPriceChange(`${change >= 0 ? "+" : ""}${change.toFixed(2)}%`);
              setIsPositive(change >= 0);

              if (seriesRef.current) {
                const now = Math.floor(Date.now() / 1000);
                const currentHour = now - (now % 3600);
                seriesRef.current.update({
                  time: currentHour as Time,
                  open: parseFloat(t.open),
                  high: parseFloat(t.high),
                  low: parseFloat(t.low),
                  close: last,
                });
              }
            }
          } catch {}
        };
        ws.onclose = () => {
          if (mounted) {
            reconnectTimer = setTimeout(connect, 5000);
          }
        };
        ws.onerror = () => {};
      } catch {}
    };

    connect();

    return () => {
      mounted = false;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (ws) { ws.onmessage = null; ws.onclose = null; ws.close(); }
    };
  }, [market]);

  return (
    <div className="h-full flex flex-col">
      {/* Chart Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <h3 className="text-sm font-semibold text-white">
            {market.toUpperCase().replace("TWD", "/TWD")}
          </h3>
          {lastPrice && (
            <>
              <span className={`text-xs font-mono ${isPositive ? "text-green-400" : "text-red-400"}`}>
                {lastPrice} TWD
              </span>
              <span className={`text-xs ${isPositive ? "text-green-400" : "text-red-400"}`}>
                {priceChange}
              </span>
            </>
          )}
          {loading && <span className="text-[10px] text-slate-500">載入中...</span>}
        </div>
        <div className="flex items-center gap-1">
          {["btctwd", "ethtwd", "soltwd", "dogetwd"].map((m) => (
            <button
              key={m}
              onClick={() => setMarket(m)}
              className={`px-2 py-1 text-xs rounded ${
                market === m
                  ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40"
                  : "text-slate-500 hover:text-slate-300"
              }`}
            >
              {m.replace("twd", "").toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {/* Chart Container */}
      <div ref={chartRef} className="flex-1" />
    </div>
  );
}
