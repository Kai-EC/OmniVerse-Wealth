"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, TrendingDown, TrendingUp, X, Bell } from "lucide-react";

interface Alert {
  currency: string;
  changePct: number;
  direction: "up" | "down";
  currentPrice: number;
  avgBuyPrice: number;
  balance: number;
  unrealizedPnlPct: number;
  severity: "warning" | "critical";
}

interface AlertData {
  alerts: Alert[];
  suggestion: string;
  autoTrades: Array<{ currency: string; action: string; volume?: string; result?: any; error?: string }>;
  threshold: number;
  checkedAt: number;
}

export default function AlertNotification() {
  const [data, setData] = useState<AlertData | null>(null);
  const [dismissed, setDismissed] = useState(false);
  const [checking, setChecking] = useState(false);
  const [lastCheck, setLastCheck] = useState<string>("");

  const checkAlerts = async () => {
    setChecking(true);
    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 12000);
      const res = await fetch("/api/alerts", { signal: controller.signal });
      clearTimeout(timeout);
      if (res.ok) {
        const result = await res.json();
        setData(result);
        setLastCheck(new Date().toLocaleTimeString("zh-TW", { hour12: false }));
        if (result.alerts.length > 0) {
          setDismissed(false);
        }
      }
    } catch {}
    setChecking(false);
  };

  // Check every 30 seconds
  useEffect(() => {
    let mounted = true;
    const run = () => { if (mounted) checkAlerts(); };
    run();
    const interval = setInterval(run, 30000);
    return () => { mounted = false; clearInterval(interval); };
  }, []);

  // No alerts or dismissed
  if (!data || data.alerts.length === 0 || dismissed) {
    return (
      <div className="flex items-center gap-2 px-3 py-1.5 border-b border-slate-800 bg-[#0d1320]">
        <Bell size={12} className="text-slate-600" />
        <span className="text-[10px] text-slate-600">
          {checking ? "偵測中..." : `無波動警報 (上次檢查: ${lastCheck || "—"})`}
        </span>
      </div>
    );
  }

  const hasCritical = data.alerts.some((a) => a.severity === "critical");

  return (
    <div
      className={`border-b ${
        hasCritical
          ? "border-red-500/50 bg-red-500/5"
          : "border-amber-500/50 bg-amber-500/5"
      }`}
    >
      {/* Alert Banner */}
      <div className="flex items-center justify-between px-4 py-2">
        <div className="flex items-center gap-2">
          <AlertTriangle
            size={14}
            className={hasCritical ? "text-red-400" : "text-amber-400"}
          />
          <span
            className={`text-xs font-semibold ${
              hasCritical ? "text-red-300" : "text-amber-300"
            }`}
          >
            ⚠️ 波動警報：{data.alerts.length} 個持倉幣種超過 {data.threshold}% 波動
          </span>
        </div>
        <button
          onClick={() => setDismissed(true)}
          className="text-slate-500 hover:text-white transition"
        >
          <X size={14} />
        </button>
      </div>

      {/* Alert Details */}
      <div className="px-4 pb-2 flex flex-wrap gap-3">
        {data.alerts.map((alert) => (
          <div
            key={alert.currency}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border ${
              alert.severity === "critical"
                ? "border-red-500/40 bg-red-500/10"
                : "border-amber-500/40 bg-amber-500/10"
            }`}
          >
            {alert.direction === "up" ? (
              <TrendingUp size={12} className="text-green-400" />
            ) : (
              <TrendingDown size={12} className="text-red-400" />
            )}
            <span className="text-xs font-mono text-white">{alert.currency}</span>
            <span
              className={`text-xs font-bold ${
                alert.direction === "up" ? "text-green-400" : "text-red-400"
              }`}
            >
              {alert.direction === "up" ? "+" : ""}
              {alert.changePct}%
            </span>
            <span className="text-[10px] text-slate-400">
              (未實現: {alert.unrealizedPnlPct > 0 ? "+" : ""}
              {alert.unrealizedPnlPct}%)
            </span>
          </div>
        ))}
      </div>

      {/* AI Suggestion */}
      {data.suggestion && (
        <div className="px-4 pb-2">
          <div className="p-2.5 bg-slate-800/50 border border-slate-700 rounded-lg">
            <p className="text-[10px] text-cyan-400 font-semibold mb-1">
              🤖 AI 調倉建議
            </p>
            <p className="text-xs text-slate-300 leading-relaxed whitespace-pre-wrap">
              {data.suggestion}
            </p>
          </div>
        </div>
      )}

      {/* Auto Trade Results */}
      {data.autoTrades && data.autoTrades.length > 0 && (
        <div className="px-4 pb-3">
          <div className="p-2.5 bg-green-500/5 border border-green-500/30 rounded-lg">
            <p className="text-[10px] text-green-400 font-semibold mb-1">
              ⚡ 自動調倉已執行
            </p>
            {data.autoTrades.map((t, i) => (
              <p key={i} className="text-xs text-slate-300">
                {t.action === "auto_sell_20pct" ? (
                  <>✅ 已自動賣出 {t.currency} {t.volume} (持倉 20%) — {t.result?.message || t.result?.error || "已提交"}</>
                ) : (
                  <>❌ {t.currency} 自動調倉失敗: {t.error}</>
                )}
              </p>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
