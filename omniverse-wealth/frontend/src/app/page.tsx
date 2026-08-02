"use client";

import { useState, useRef } from "react";
import Header from "@/components/Header";
import ChartPanel from "@/components/ChartPanel";
import PortfolioPanel from "@/components/PortfolioPanel";
import PortfolioPieChart from "@/components/PortfolioPieChart";
import ChatPanel, { ChatPanelHandle } from "@/components/ChatPanel";
import AgentOrbitGraph from "@/components/AgentOrbitGraph";
import DepthPanel from "@/components/DepthPanel";
import TradesPanel from "@/components/TradesPanel";
import SentimentPanel from "@/components/SentimentPanel";
import AlertNotification from "@/components/AlertNotification";
import TradeConfirmCard from "@/components/TradeConfirmCard";
import ErrorBoundary from "@/components/ErrorBoundary";

export default function Dashboard() {
  const chatRef = useRef<ChatPanelHandle>(null);
  const [market, setMarket] = useState("btctwd");
  const [tradeConfirm, setTradeConfirm] = useState<{
    market: string;
    side: "buy" | "sell";
    volume: string;
    price: string;
    reasoning: string;
  } | null>(null);

  const [activeAgents, setActiveAgents] = useState<string[]>([]);

  const handleQuickAction = (query: string) => {
    chatRef.current?.sendMessage(query);
    setActiveAgents(["stark", "minerva", "morpheus"]);
    setTimeout(() => setActiveAgents([]), 5000);
  };

  return (
    <div className="h-screen flex flex-col overflow-hidden">
      {/* Top Header Bar */}
      <Header />

      {/* Alert Notification Banner */}
      <AlertNotification />

      {/* Main 3-column Layout */}
      <main className="flex-1 flex gap-1.5 p-1.5 min-h-0">

        {/* LEFT COLUMN: Pie + Portfolio + Sentiment (3:5:2 ratio) */}
        <div className="w-[200px] flex-shrink-0 flex flex-col gap-1.5 min-h-0">
          <div className="flex-[3] hud-border rounded-lg overflow-hidden bg-[#111827] min-h-0">
            <ErrorBoundary name="PieChart"><PortfolioPieChart /></ErrorBoundary>
          </div>
          <div className="flex-[5] hud-border rounded-lg overflow-hidden bg-[#111827] min-h-0">
            <ErrorBoundary name="Portfolio"><PortfolioPanel /></ErrorBoundary>
          </div>
          <div className="flex-[2] hud-border rounded-lg overflow-hidden bg-[#111827] min-h-0">
            <ErrorBoundary name="Sentiment"><SentimentPanel /></ErrorBoundary>
          </div>
        </div>

        {/* CENTER COLUMN: Chart + Agent Orbit + Depth/Trades */}
        <div className="flex-1 flex flex-col gap-1.5 min-w-0 min-h-0">
          {/* Top row: Chart + Agent Orbit side by side */}
          <div className="flex-1 flex gap-1.5 min-h-0">
            {/* K-line Chart */}
            <div className="flex-1 hud-border rounded-lg overflow-hidden bg-[#111827] min-h-0">
              <ErrorBoundary name="Chart"><ChartPanel /></ErrorBoundary>
            </div>
            {/* Agent Orbit Graph */}
            <div className="w-[240px] flex-shrink-0 hud-border rounded-lg overflow-hidden bg-[#111827]">
              <ErrorBoundary name="AgentOrbit"><AgentOrbitGraph activeAgents={activeAgents} /></ErrorBoundary>
            </div>
          </div>

          {/* Bottom row: Depth + Trades */}
          <div className="h-[160px] flex gap-1.5 flex-shrink-0">
            <div className="flex-1 hud-border rounded-lg overflow-hidden bg-[#111827]">
              <ErrorBoundary name="Depth"><DepthPanel market={market} /></ErrorBoundary>
            </div>
            <div className="flex-1 hud-border rounded-lg overflow-hidden bg-[#111827]">
              <ErrorBoundary name="Trades"><TradesPanel market={market} /></ErrorBoundary>
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN: Chat + Quick Actions */}
        <div className="w-[340px] flex-shrink-0 flex flex-col gap-1.5 min-h-0">
          <div className="flex-1 hud-border rounded-lg overflow-hidden bg-[#111827] min-h-0">
            <ChatPanel ref={chatRef} onTradeConfirm={setTradeConfirm} onAgentsActive={setActiveAgents} />
          </div>

          {/* Quick Actions */}
          <div className="flex gap-1 flex-shrink-0">
            <button
              onClick={() => handleQuickAction("查詢我的持倉表現，各幣種損益如何？")}
              className="flex-1 py-1.5 bg-cyan-500/10 border border-cyan-500/30 rounded text-cyan-300 text-[9px] hover:bg-cyan-500/20 transition"
            >
              📊 持倉
            </button>
            <button
              onClick={() => handleQuickAction("目前市場情緒如何？BTC 適合進場嗎？")}
              className="flex-1 py-1.5 bg-purple-500/10 border border-purple-500/30 rounded text-purple-300 text-[9px] hover:bg-purple-500/20 transition"
            >
              🔮 情緒
            </button>
            <button
              onClick={() => handleQuickAction("BTC 技術面分析，支撐壓力位？趨勢方向？")}
              className="flex-1 py-1.5 bg-green-500/10 border border-green-500/30 rounded text-green-300 text-[9px] hover:bg-green-500/20 transition"
            >
              📈 技術
            </button>
            <button
              onClick={() => handleQuickAction("ETH 和 SOL 比較，哪個更值得加碼？")}
              className="flex-1 py-1.5 bg-amber-500/10 border border-amber-500/30 rounded text-amber-300 text-[9px] hover:bg-amber-500/20 transition"
            >
              ⚡ 比較
            </button>
          </div>
        </div>
      </main>

      {/* Trade Confirmation Overlay */}
      {tradeConfirm && (
        <TradeConfirmCard
          trade={tradeConfirm}
          onConfirm={() => setTradeConfirm(null)}
          onCancel={() => setTradeConfirm(null)}
        />
      )}
    </div>
  );
}
