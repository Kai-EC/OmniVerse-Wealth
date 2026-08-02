import { NextRequest, NextResponse } from "next/server";
import { readFileSync } from "fs";
import { resolve } from "path";
import { sendDiscordAlert, sendDiscordTradeResult } from "@/lib/discord";
import { httpsGet } from "@/lib/httpGet";

/**
 * GET /api/alerts
 *
 * Monitors portfolio holdings against market volatility.
 * Triggers alerts when any held asset's 24H price change exceeds threshold (10%).
 * Calls Bedrock LLM to generate rebalancing suggestions.
 */

const VOLATILITY_THRESHOLD = 10; // 10% trigger

export async function GET(request: NextRequest) {
  try {
    // 1. Load portfolio holdings from CSV
    let holdings: Record<string, { balance: number; avgBuyPrice: number }> = {};
    try {
      const csvPath = resolve(process.cwd(), "../../MaiCoin_最近一年份出入金及交易紀錄.csv");
      const csv = readFileSync(csvPath, "utf-8");
      const lines = csv.trim().split("\n").slice(1);

      const raw: Record<string, { balance: number; bought: number; cost: number }> = {};
      for (const line of lines) {
        const [, currency, price, action, change, balance] = line.split(",");
        const cur = currency.trim().toLowerCase();
        if (!raw[cur]) raw[cur] = { balance: 0, bought: 0, cost: 0 };
        raw[cur].balance = parseFloat(balance);
        if (action.trim() === "buy") {
          raw[cur].bought += Math.abs(parseFloat(change));
          raw[cur].cost += Math.abs(parseFloat(change)) * parseFloat(price);
        }
      }

      for (const [cur, data] of Object.entries(raw)) {
        if (cur === "twd" || data.balance < 0.0001) continue;
        holdings[cur] = {
          balance: data.balance,
          avgBuyPrice: data.bought > 0 ? data.cost / data.bought : 0,
        };
      }
    } catch {}

    // 2. Fetch live tickers for held assets
    const alerts: Array<{
      currency: string;
      changePct: number;
      direction: "up" | "down";
      currentPrice: number;
      avgBuyPrice: number;
      balance: number;
      unrealizedPnlPct: number;
      severity: "warning" | "critical";
    }> = [];

    await Promise.all(
      Object.entries(holdings).map(async ([cur, data]) => {
        if (cur === "usdt" || cur === "usdc") return; // Skip stablecoins
        try {
          const ticker = await httpsGet(
            `https://max-api.maicoin.com/api/v3/ticker?market=${cur}twd`,
            5000
          );

          const last = parseFloat(ticker.last);
          const open = parseFloat(ticker.open);
          const changePct = open > 0 ? ((last - open) / open) * 100 : 0;
          const unrealizedPnlPct = data.avgBuyPrice > 0
            ? ((last - data.avgBuyPrice) / data.avgBuyPrice) * 100
            : 0;

          if (Math.abs(changePct) >= VOLATILITY_THRESHOLD) {
            alerts.push({
              currency: cur.toUpperCase(),
              changePct: parseFloat(changePct.toFixed(2)),
              direction: changePct >= 0 ? "up" : "down",
              currentPrice: last,
              avgBuyPrice: data.avgBuyPrice,
              balance: data.balance,
              unrealizedPnlPct: parseFloat(unrealizedPnlPct.toFixed(2)),
              severity: Math.abs(changePct) >= 20 ? "critical" : "warning",
            });
          }
        } catch {}
      })
    );

    // 3. If alerts exist, generate rebalancing suggestion via Bedrock
    let suggestion = "";
    const autoTrades: any[] = [];

    if (alerts.length > 0) {
      suggestion = await generateSuggestion(alerts);

      // AUTO REBALANCE: If any asset drops > 10%, auto-sell 20% of position
      for (const alert of alerts) {
        if (alert.direction === "down" && Math.abs(alert.changePct) >= 10) {
          const sellVolume = (alert.balance * 0.2).toFixed(8); // Sell 20% of position
          const market = `${alert.currency.toLowerCase()}twd`;

          try {
            const tradeRes = await fetch(new URL("/api/trade", request.url).toString(), {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                market,
                side: "sell",
                volume: sellVolume,
                ord_type: "market",
                auto: true,
              }),
            });
            const tradeResult = await tradeRes.json();
            autoTrades.push({
              currency: alert.currency,
              action: "auto_sell_20pct",
              volume: sellVolume,
              result: tradeResult,
            });
          } catch (e: any) {
            autoTrades.push({
              currency: alert.currency,
              action: "auto_sell_failed",
              error: e.message,
            });
          }
        }
      }
    }

    // 4. Send Discord notification if alerts triggered
    if (alerts.length > 0) {
      await sendDiscordAlert(
        alerts.map((a) => ({
          currency: a.currency,
          changePct: a.changePct,
          direction: a.direction,
          currentPrice: a.currentPrice,
          avgBuyPrice: a.avgBuyPrice,
          action: autoTrades.find((t) => t.currency === a.currency)?.action,
          volume: autoTrades.find((t) => t.currency === a.currency)?.volume,
        }))
      );

      // Notify each auto-trade result
      for (const trade of autoTrades) {
        await sendDiscordTradeResult(
          trade.currency,
          "sell",
          trade.volume || "0",
          trade.action === "auto_sell_20pct",
          trade.result?.message || trade.error || "Unknown",
        );
      }
    }

    return NextResponse.json({
      alerts,
      suggestion,
      autoTrades,
      threshold: VOLATILITY_THRESHOLD,
      checkedAt: Date.now(),
      holdingsChecked: Object.keys(holdings).filter(c => c !== "usdt" && c !== "usdc"),
    });
  } catch (error: any) {
    return NextResponse.json({ alerts: [], suggestion: "", error: error.message }, { status: 500 });
  }
}

async function generateSuggestion(alerts: any[]): Promise<string> {
  const BEDROCK_API_KEY = process.env.BEDROCK_API_KEY || "";
  const MODEL_ID = process.env.BEDROCK_MODEL_ID || "amazon.nova-lite-v1:0";
  const REGION = process.env.AWS_REGION || "us-east-1";

  if (!BEDROCK_API_KEY) return "（Bedrock 未配置，無法生成建議）";

  const alertSummary = alerts.map(a =>
    `${a.currency}: 24H ${a.direction === "up" ? "漲" : "跌"} ${Math.abs(a.changePct)}%, 現價=${a.currentPrice}, 均買價=${a.avgBuyPrice.toFixed(0)}, 未實現損益=${a.unrealizedPnlPct}%`
  ).join("\n");

  const systemPrompt = `你是 OmniVerse Wealth 的風險管理顧問。以下持倉幣種出現超過 10% 的 24 小時波動，請給出簡潔的調倉建議（3-5 句話）。考慮：
- 波動方向（暴漲 vs 暴跌）
- 用戶的未實現損益
- 風險分散原則
回覆請用繁體中文，簡潔有力。`;

  try {
    const url = `https://bedrock-runtime.${REGION}.amazonaws.com/model/${MODEL_ID}/converse`;
    const { httpsPost } = await import("@/lib/httpGet");
    const { status, data } = await httpsPost(
      url,
      {
        system: [{ text: systemPrompt }],
        messages: [{ role: "user", content: [{ text: `波動警報：\n${alertSummary}\n\n請給出調倉建議。` }] }],
        inferenceConfig: { maxTokens: 500, temperature: 0.3 },
      },
      { Authorization: `Bearer ${BEDROCK_API_KEY}` },
      15000
    );

    if (status === 200) {
      const content = data?.output?.message?.content || [];
      return content.map((c: any) => c.text || "").join("");
    }
  } catch {}

  return "建議：密切關注波動幣種，考慮適度減倉以降低風險。";
}
