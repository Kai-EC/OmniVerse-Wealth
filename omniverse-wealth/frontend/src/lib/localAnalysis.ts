/**
 * Local Analysis Engine — Fallback when Bedrock is unavailable.
 *
 * Generates intelligent responses using rule-based logic from:
 * - Live ticker data (MAX API)
 * - Portfolio CSV data
 * - Technical indicators
 * - On-chain data
 *
 * Not as good as LLM, but far better than showing an error.
 */

interface TickerData {
  market: string;
  last: string;
  open: string;
  high: string;
  low: string;
  vol: string;
}

interface Holding {
  currency: string;
  balance: number;
  avgBuyPrice: number;
  livePrice: number;
}

export function generateLocalResponse(
  message: string,
  tickers: Record<string, TickerData>,
  holdings: Holding[],
  technicalSummary: string,
  onchainSummary: string,
): string {
  const q = message.toLowerCase();
  const lines: string[] = [];

  // Detect intent
  const isPortfolio = /持倉|損益|表現|資產/.test(q);
  const isTechnical = /技術|RSI|MACD|支撐|壓力|指標/.test(q);
  const isPrice = /多少錢|價格|行情|漲|跌/.test(q);
  const isBuy = /買|加碼|進場|適合/.test(q);
  const isCompare = /比較|哪個/.test(q);
  const isOnchain = /鏈上|hash|挖礦|區塊/.test(q);

  // Extract mentioned currency
  const currencies = ["btc", "eth", "sol", "doge", "usdt"];
  const mentioned = currencies.filter(c =>
    q.includes(c) || q.includes(getCurrencyName(c))
  );
  const targetCurrencies = mentioned.length > 0 ? mentioned : ["btc"];

  if (isPortfolio) {
    lines.push("📊 **持倉表現摘要**\n");
    let totalValue = 0;
    for (const h of holdings) {
      if (h.balance < 0.0001 || h.currency === "twd") continue;
      const value = h.balance * h.livePrice;
      const pnl = h.avgBuyPrice > 0 ? ((h.livePrice - h.avgBuyPrice) / h.avgBuyPrice * 100) : 0;
      const icon = pnl >= 0 ? "🟢" : "🔴";
      totalValue += value;
      lines.push(`${icon} **${h.currency.toUpperCase()}**: ${h.balance.toFixed(4)}`);
      lines.push(`   現價 ${h.livePrice.toLocaleString()} TWD | 均價 ${h.avgBuyPrice.toLocaleString()} TWD | 損益 ${pnl >= 0 ? "+" : ""}${pnl.toFixed(1)}%`);
      lines.push("");
    }
    lines.push(`💎 總資產估值: **${totalValue.toLocaleString()} TWD**`);
  } else if (isTechnical) {
    lines.push("📈 **技術面分析**\n");
    if (technicalSummary) {
      lines.push(technicalSummary);
    } else {
      for (const cur of targetCurrencies) {
        const t = tickers[`${cur}twd`];
        if (!t) continue;
        const last = parseFloat(t.last);
        const open = parseFloat(t.open);
        const high = parseFloat(t.high);
        const low = parseFloat(t.low);
        const change = open > 0 ? ((last - open) / open * 100) : 0;
        lines.push(`**${cur.toUpperCase()}/TWD**`);
        lines.push(`現價: ${last.toLocaleString()} TWD (${change >= 0 ? "+" : ""}${change.toFixed(2)}%)`);
        lines.push(`24H 區間: ${low.toLocaleString()} ~ ${high.toLocaleString()}`);
        lines.push(`趨勢: ${change > 2 ? "短期偏多" : change < -2 ? "短期偏空" : "盤整震盪"}`);
        lines.push("");
      }
    }
  } else if (isOnchain && onchainSummary) {
    lines.push("⛓️ **鏈上數據**\n");
    lines.push(onchainSummary);
  } else if (isCompare && mentioned.length >= 2) {
    lines.push(`⚡ **${mentioned.map(c => c.toUpperCase()).join(" vs ")} 比較**\n`);
    for (const cur of mentioned) {
      const t = tickers[`${cur}twd`];
      if (!t) continue;
      const change = parseFloat(t.open) > 0
        ? ((parseFloat(t.last) - parseFloat(t.open)) / parseFloat(t.open) * 100)
        : 0;
      const h = holdings.find(x => x.currency === cur);
      lines.push(`**${cur.toUpperCase()}**: ${parseFloat(t.last).toLocaleString()} TWD (${change >= 0 ? "+" : ""}${change.toFixed(2)}%)`);
      if (h) {
        const pnl = h.avgBuyPrice > 0 ? ((h.livePrice - h.avgBuyPrice) / h.avgBuyPrice * 100) : 0;
        lines.push(`  你的損益: ${pnl >= 0 ? "+" : ""}${pnl.toFixed(1)}%`);
      }
      lines.push("");
    }
  } else {
    // Default: show price + brief analysis
    lines.push("📊 **即時行情**\n");
    for (const cur of targetCurrencies) {
      const t = tickers[`${cur}twd`];
      if (!t) continue;
      const last = parseFloat(t.last);
      const open = parseFloat(t.open);
      const change = open > 0 ? ((last - open) / open * 100) : 0;
      const icon = change >= 0 ? "🟢" : "🔴";
      lines.push(`${icon} **${cur.toUpperCase()}/TWD**: ${last.toLocaleString()} (${change >= 0 ? "+" : ""}${change.toFixed(2)}%)`);

      const h = holdings.find(x => x.currency === cur);
      if (h && h.avgBuyPrice > 0) {
        const pnl = ((last - h.avgBuyPrice) / h.avgBuyPrice * 100);
        lines.push(`  你的均價: ${h.avgBuyPrice.toLocaleString()} TWD | 損益: ${pnl >= 0 ? "+" : ""}${pnl.toFixed(1)}%`);
      }
      lines.push("");
    }

    if (isBuy) {
      const t = tickers[`${targetCurrencies[0]}twd`];
      if (t) {
        const change = parseFloat(t.open) > 0
          ? ((parseFloat(t.last) - parseFloat(t.open)) / parseFloat(t.open) * 100)
          : 0;
        if (change < -3) {
          lines.push("💡 24H 下跌超過 3%，可能是分批建倉機會，但需注意下行風險。");
        } else if (change > 3) {
          lines.push("💡 24H 上漲超過 3%，短期追高風險較大，建議觀望回調。");
        } else {
          lines.push("💡 目前盤整中，無明確方向，建議觀望或小倉試探。");
        }
      }
    }
  }

  lines.push("\n⚠️ 以上為即時數據分析（本地引擎），非投資建議。");
  lines.push("📡 資料來源: MAX 交易所 + 個人歷史交易");

  return lines.join("\n");
}

function getCurrencyName(cur: string): string {
  const names: Record<string, string> = {
    btc: "比特幣", eth: "以太", sol: "sol", doge: "狗狗幣", usdt: "usdt",
  };
  return names[cur] || cur;
}
