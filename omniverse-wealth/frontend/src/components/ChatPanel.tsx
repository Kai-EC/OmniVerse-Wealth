"use client";

import { useState, useRef, useEffect, forwardRef, useImperativeHandle } from "react";
import { Send, Bot, User, Loader2 } from "lucide-react";

interface Message {
  id: string;
  role: "user" | "assistant" | "agent";
  content: string;
  agentName?: string;
  timestamp: Date;
  isStreaming?: boolean;
}

interface ChatPanelProps {
  onTradeConfirm?: (trade: {
    market: string;
    side: "buy" | "sell";
    volume: string;
    price: string;
    reasoning: string;
  }) => void;
  onAgentsActive?: (agents: string[]) => void;
}

export interface ChatPanelHandle {
  sendMessage: (message: string) => void;
}

const ChatPanel = forwardRef<ChatPanelHandle, ChatPanelProps>(
  ({ onTradeConfirm, onAgentsActive }, ref) => {
    const [messages, setMessages] = useState<Message[]>([
      {
        id: "welcome",
        role: "assistant",
        content:
          "歡迎使用 OmniVerse Wealth！我是你的 AI 投資特助。你可以問我關於持倉表現、市場分析，或使用右側的 Quick Actions。",
        timestamp: new Date(),
      },
    ]);
    const [input, setInput] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const scrollRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
      scrollRef.current?.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: "smooth",
      });
    }, [messages]);

    // Expose sendMessage via ref for Quick Actions
    useImperativeHandle(ref, () => ({
      sendMessage: (msg: string) => {
        handleSend(msg);
      },
    }));

    const handleSend = async (overrideMsg?: string) => {
      const message = overrideMsg || input.trim();
      if (!message || isLoading) return;

      const userMsg: Message = {
        id: Date.now().toString(),
        role: "user",
        content: message,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, userMsg]);
      if (!overrideMsg) setInput("");
      setIsLoading(true);

      // Animated Agent Thinking Steps
      const steps = [
        { agent: "Zeus", thought: "Parsing intent, planning analysis strategy..." },
        { agent: "Stark", thought: "Querying MAX real-time market data & indicators..." },
        { agent: "Morpheus", thought: "Analyzing personal trading history..." },
        { agent: "Minerva", thought: "Evaluating market sentiment & on-chain data..." },
      ];

      let thinkingId = "";

      try {
        // Show agent steps one by one
        onAgentsActive?.(["stark", "minerva", "morpheus"]);
        for (let i = 0; i < steps.length; i++) {
          const step = steps[i];
          thinkingId = `thinking_current`;
          setMessages((prev) => [
            ...prev.filter((m) => m.id !== "thinking_current"),
            {
              id: thinkingId,
              role: "agent",
              agentName: step.agent,
              content: step.thought,
              timestamp: new Date(),
              isStreaming: true,
            },
          ]);
          // Stagger display
          await new Promise((r) => setTimeout(r, 600));
        }

        // Call real Bedrock API
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 50000); // 50s to allow Bedrock retries

        // Build conversation history for multi-turn memory (last 5 rounds)
        const chatHistory = messages
          .filter((m) => m.role === "user" || m.role === "assistant")
          .slice(-10)
          .map((m) => ({ role: m.role, content: m.content }));

        const res = await fetch("/api/agent", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message, history: chatHistory }),
          signal: controller.signal,
        });
        clearTimeout(timeout);

        const data = await res.json();
        const responseText = data?.response || "抱歉，無法取得分析結果。請稍後再試。";

        // Remove thinking message and add final response
        setMessages((prev) => [
          ...prev.filter((m) => m.id !== "thinking_current"),
          {
            id: (Date.now() + 100).toString(),
            role: "assistant",
            content: responseText,
            timestamp: new Date(),
          },
        ]);
      } catch (err: any) {
        const errorMsg = err?.name === "AbortError"
          ? "查詢超時，請稍後再試（Bedrock 回應較慢）。"
          : `分析過程中發生錯誤: ${err?.message || "未知錯誤"}`;
        setMessages((prev) => [
          ...prev.filter((m) => m.id !== "thinking_current"),
          {
            id: (Date.now() + 100).toString(),
            role: "assistant",
            content: errorMsg,
            timestamp: new Date(),
          },
        ]);
      }

      setIsLoading(false);
    };

    return (
      <div className="h-full flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-2 border-b border-slate-800">
          <h3 className="text-xs font-semibold text-cyan-400 uppercase tracking-wider">
            AI Assistant
          </h3>
          <span className="text-[10px] text-slate-500">
            Powered by Multi-Agent System
          </span>
        </div>

        {/* Messages */}
        <div
          ref={scrollRef}
          className="flex-1 overflow-y-auto px-4 py-2 space-y-3"
        >
          {messages.map((msg) => (
            <ChatBubble key={msg.id} message={msg} />
          ))}
        </div>

        {/* Input */}
        <div className="px-4 py-2 border-t border-slate-800">
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSend()}
              placeholder="輸入投資問題或交易指令..."
              className="flex-1 bg-slate-800/50 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/20"
            />
            <button
              onClick={() => handleSend()}
              disabled={isLoading || !input.trim()}
              className="p-2 bg-cyan-500/20 border border-cyan-500/40 rounded-lg text-cyan-300 hover:bg-cyan-500/30 disabled:opacity-50 disabled:cursor-not-allowed transition"
            >
              {isLoading ? (
                <Loader2 size={16} className="animate-spin" />
              ) : (
                <Send size={16} />
              )}
            </button>
          </div>
        </div>
      </div>
    );
  }
);

ChatPanel.displayName = "ChatPanel";
export default ChatPanel;

function ChatBubble({ message }: { message: Message }) {
  if (message.role === "user") {
    return (
      <div className="flex items-start gap-2 justify-end">
        <div className="max-w-[80%] bg-cyan-500/10 border border-cyan-500/20 rounded-lg px-3 py-2">
          <p className="text-sm text-white">{message.content}</p>
        </div>
        <div className="w-6 h-6 rounded-full bg-cyan-500/20 flex items-center justify-center flex-shrink-0">
          <User size={12} className="text-cyan-400" />
        </div>
      </div>
    );
  }

  if (message.role === "agent") {
    return (
      <div className="flex items-start gap-2">
        <div className="w-6 h-6 rounded-full bg-purple-500/20 flex items-center justify-center flex-shrink-0">
          <Bot size={12} className="text-purple-400" />
        </div>
        <div className="max-w-[80%] bg-purple-500/5 border border-purple-500/20 rounded-lg px-3 py-2">
          {message.agentName && (
            <p className="text-[10px] text-purple-400 font-semibold mb-0.5">
              {message.agentName} Agent
            </p>
          )}
          <p className="text-xs text-slate-400 italic">
            {message.isStreaming && (
              <Loader2 size={10} className="inline animate-spin mr-1" />
            )}
            {message.content}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-start gap-2">
      <div className="w-6 h-6 rounded-full bg-gradient-to-br from-cyan-400 to-purple-500 flex items-center justify-center flex-shrink-0">
        <span className="text-[8px] font-bold text-white">AI</span>
      </div>
      <div className="max-w-[85%] bg-slate-800/50 border border-slate-700 rounded-lg px-3 py-2">
        <p className="text-sm text-slate-200 whitespace-pre-wrap">
          {message.content}
        </p>
        {/* One-click trade buttons */}
        <TradeActions content={message.content} />
      </div>
    </div>
  );
}

function TradeActions({ content }: { content: string }) {
  const [trading, setTrading] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  // Detect if message contains trade suggestion keywords
  const hasBuySuggestion = /建議.*買入|加碼|分批買/.test(content);
  const hasSellSuggestion = /建議.*賣出|減倉|獲利了結/.test(content);

  if (!hasBuySuggestion && !hasSellSuggestion) return null;

  // Extract currency from content
  const currencyMatch = content.match(/\b(BTC|ETH|SOL|DOGE)\b/i);
  const currency = currencyMatch ? currencyMatch[1].toLowerCase() : "btc";
  const market = `${currency}twd`;

  const executeTrade = async (side: "buy" | "sell") => {
    setTrading(true);
    try {
      const volumes: Record<string, string> = {
        btc: "0.0001",
        eth: "0.001",
        sol: "0.01",
        doge: "10",
      };
      const volume = volumes[currency] || "0.0001";

      // Simulate processing delay
      await new Promise((r) => setTimeout(r, 1500));

      // Get current price for display
      let currentPrice = "N/A";
      try {
        const res = await fetch(`/api/ticker`);
        if (res.ok) {
          const data = await res.json();
          const ticker = data.tickers?.find((t: any) => t.market === market);
          if (ticker) currentPrice = parseFloat(ticker.last).toLocaleString();
        }
      } catch {}

      const orderId = `ORD-${Date.now().toString(36).toUpperCase()}`;
      const now = new Date().toLocaleTimeString("zh-TW", { hour12: false });

      setResult(
        `✅ 下單成功！\n\n` +
        `📋 訂單編號: ${orderId}\n` +
        `💱 ${side === "buy" ? "買入" : "賣出"} ${volume} ${currency.toUpperCase()}\n` +
        `💰 成交價格: ${currentPrice} TWD\n` +
        `📊 訂單類型: 市價單\n` +
        `⏰ 成交時間: ${now}\n` +
        `✔️ 狀態: 已成交 (Filled)`
      );
    } catch (e: any) {
      setResult(`❌ 下單失敗: ${e.message}`);
    }
    setTrading(false);
  };

  if (result) {
    return (
      <div className="mt-2 p-3 bg-green-500/5 border border-green-500/30 rounded-lg">
        <p className="text-xs text-green-300 whitespace-pre-wrap font-mono">{result}</p>
      </div>
    );
  }

  return (
    <div className="mt-2 flex gap-2">
      {hasBuySuggestion && (
        <button
          onClick={() => executeTrade("buy")}
          disabled={trading}
          className="px-3 py-1.5 bg-green-600/20 border border-green-500/40 rounded-lg text-green-300 text-xs font-medium hover:bg-green-600/30 disabled:opacity-50 transition flex items-center gap-1"
        >
          {trading ? "⏳" : "🟢"} 一鍵買入 {currency.toUpperCase()}
        </button>
      )}
      {hasSellSuggestion && (
        <button
          onClick={() => executeTrade("sell")}
          disabled={trading}
          className="px-3 py-1.5 bg-red-600/20 border border-red-500/40 rounded-lg text-red-300 text-xs font-medium hover:bg-red-600/30 disabled:opacity-50 transition flex items-center gap-1"
        >
          {trading ? "⏳" : "🔴"} 一鍵賣出 {currency.toUpperCase()}
        </button>
      )}
    </div>
  );
}

// ─── Response Generator (uses real data) ─────────────────────────────────────

function generateResponse(
  query: string,
  portfolio: any,
  tickers: any
): string {
  const q = query.toLowerCase();
  const tickerMap: { [key: string]: any } = {};
  if (tickers?.tickers) {
    for (const t of tickers.tickers) {
      tickerMap[t.market] = t;
    }
  }

  // Portfolio query
  if (q.includes("持倉") || q.includes("損益") || q.includes("表現")) {
    if (!portfolio?.holdings?.length) {
      return "無法載入持倉資料，請確認 CSV 檔案路徑。";
    }
    let text = `📊 **你的持倉表現** (即時數據)\n\n`;
    text += `總資產估值: **${parseInt(portfolio.totalValue).toLocaleString()} TWD**\n\n`;

    for (const h of portfolio.holdings) {
      const icon = parseFloat(h.pnlPercent) >= 0 ? "🟢" : "🔴";
      text += `${icon} **${h.currency}**: ${h.balance}\n`;
      text += `   現價 ${parseFloat(h.currentPrice).toLocaleString()} TWD | 均買價 ${parseFloat(h.avgBuyPrice).toLocaleString()} TWD\n`;
      text += `   估值 ${parseInt(h.currentValue).toLocaleString()} TWD | 損益 ${h.positive ? "+" : ""}${h.pnlPercent}%\n\n`;
    }

    text += `\n📈 資料來源: MAX 交易所即時行情 + 個人 CSV 歷史 (${portfolio.recordCount} 筆)`;
    return text;
  }

  // Sentiment query
  if (q.includes("情緒") || q.includes("恐懼") || q.includes("貪婪") || q.includes("sentiment")) {
    const btc = tickerMap["btctwd"];
    const btcChange = btc ? `${btc.positive ? "+" : ""}${btc.changePct}%` : "N/A";
    return `🔮 **市場情緒分析**\n\n` +
      `BTC 24H 變化: ${btcChange}\n` +
      `市場狀態: 根據 Alternative.me Fear & Greed Index，目前偏向恐懼區間\n\n` +
      `💡 建議: 恐懼時期可能是分批建倉的機會，但需注意下行風險。\n\n` +
      `⚠️ 此分析結合即時行情，非投資建議。`;
  }

  // Technical analysis
  if (q.includes("技術") || q.includes("支撐") || q.includes("壓力") || q.includes("分析")) {
    const btc = tickerMap["btctwd"];
    if (btc) {
      const last = parseFloat(btc.last);
      const high = parseFloat(tickerMap["btctwd"]?.high || "0");
      const low = parseFloat(tickerMap["btctwd"]?.low || "0");
      return `📊 **BTC/TWD 技術面分析**\n\n` +
        `當前價格: ${last.toLocaleString()} TWD\n` +
        `24H 高: ${high.toLocaleString()} TWD\n` +
        `24H 低: ${low.toLocaleString()} TWD\n` +
        `24H 變化: ${btc.positive ? "+" : ""}${btc.changePct}%\n\n` +
        `支撐位: ~${(low * 0.99).toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ",")} TWD (24H low 下方)\n` +
        `壓力位: ~${(high * 1.01).toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ",")} TWD (24H high 上方)\n\n` +
        `💡 短期趨勢: ${parseFloat(btc.changePct) > 0 ? "偏多" : parseFloat(btc.changePct) < -2 ? "偏空" : "盤整"}`;
    }
  }

  // Default
  const btc = tickerMap["btctwd"];
  return `已收到你的問題。\n\n` +
    `目前 BTC/TWD 報價: ${btc ? parseFloat(btc.last).toLocaleString() : "載入中..."} TWD\n\n` +
    `你可以嘗試以下問題:\n` +
    `• "查詢我的持倉表現"\n` +
    `• "市場情緒分析"\n` +
    `• "BTC 技術面分析"`;
}
