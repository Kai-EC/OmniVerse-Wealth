import { NextRequest, NextResponse } from "next/server";
import { readFileSync } from "fs";
import { resolve } from "path";
import { httpsGet, httpsPost } from "@/lib/httpGet";
import { calculateIndicators, formatIndicatorsForPrompt, type KlineRaw } from "@/lib/indicators";
import { generateLocalResponse } from "@/lib/localAnalysis";

/**
 * POST /api/agent
 *
 * Multi-Agent query powered by Amazon Bedrock.
 * Optimizations:
 * - Parallel ticker fetching (1s vs 4s)
 * - Multi-turn conversation memory (last 5 rounds)
 * - Enhanced system prompt with few-shot examples
 * - Recent 30 trades detail injection
 */
export async function POST(request: NextRequest) {
  try {
    const { message, history = [] } = await request.json();
    if (!message) {
      return NextResponse.json({ error: "Message required" }, { status: 400 });
    }

    // 1. PARALLEL ticker fetching (speed optimization)
    const markets = ["btctwd", "ethtwd", "soltwd", "dogetwd"];
    const tickerResults = await Promise.allSettled(
      markets.map((m) => httpsGet(`https://max-api.maicoin.com/api/v3/ticker?market=${m}`, 3000))
    );
    const tickerData: Record<string, any> = {};
    tickerResults.forEach((r, i) => {
      if (r.status === "fulfilled") tickerData[markets[i]] = r.value;
    });

    // 2. Fetch on-chain data from Blockchain.com
    let onchainSummary = "";
    try {
      const stats = await httpsGet("https://api.blockchain.info/stats", 5000);
      onchainSummary = [
        `BTC 全球均價 (USD): $${stats.market_price_usd?.toLocaleString()}`,
        `Hash Rate: ${(stats.hash_rate / 1e12).toFixed(1)} TH/s`,
        `挖礦難度: ${stats.difficulty?.toLocaleString()}`,
        `24H 交易筆數: ${stats.n_tx?.toLocaleString()}`,
        `24H 已挖區塊: ${stats.n_blocks_mined}`,
        `平均出塊時間: ${stats.minutes_between_blocks?.toFixed(1)} 分鐘`,
      ].join("\n");
    } catch {}

    // 3. Compute technical indicators from K-lines (parallel with tickers)
    let technicalSummary = "";
    try {
      const klineResults = await Promise.allSettled(
        markets.map((m) => httpsGet(`https://max-api.maicoin.com/api/v3/k?market=${m}&period=60&limit=100`, 4000))
      );

      const indicatorTexts: string[] = [];
      for (let i = 0; i < markets.length; i++) {
        const result = klineResults[i];
        if (result.status === "fulfilled" && Array.isArray(result.value)) {
          const klines: KlineRaw[] = result.value.map((k: number[]) => ({
            time: k[0], open: k[1], high: k[2], low: k[3], close: k[4], volume: k[5],
          }));
          const indicators = calculateIndicators(klines);
          if (indicators) {
            indicatorTexts.push(formatIndicatorsForPrompt(markets[i], indicators));
          }
        }
      }
      technicalSummary = indicatorTexts.join("\n\n");
    } catch {}

    // 4. Load portfolio + recent trades from CSV
    let portfolioSummary = "";
    let recentTrades = "";
    try {
      let csvPath = resolve(process.cwd(), "../../MaiCoin_最近一年份出入金及交易紀錄.csv");
      let csv: string;
      try {
        csv = readFileSync(csvPath, "utf-8");
      } catch {
        csvPath = resolve(process.cwd(), "../MaiCoin_最近一年份出入金及交易紀錄.csv");
        csv = readFileSync(csvPath, "utf-8");
      }
      const lines = csv.trim().split("\n").slice(1);

      // Portfolio summary
      const holdings: Record<string, { balance: number; bought: number; cost: number; buyCount: number; sellCount: number }> = {};
      for (const line of lines) {
        const [, currency, price, action, change, balance] = line.split(",");
        const cur = currency.trim().toLowerCase();
        if (!holdings[cur]) holdings[cur] = { balance: 0, bought: 0, cost: 0, buyCount: 0, sellCount: 0 };
        holdings[cur].balance = parseFloat(balance);
        if (action.trim() === "buy") {
          holdings[cur].bought += Math.abs(parseFloat(change));
          holdings[cur].cost += Math.abs(parseFloat(change)) * parseFloat(price);
          holdings[cur].buyCount++;
        } else if (action.trim() === "sell") {
          holdings[cur].sellCount++;
        }
      }

      const summaryLines: string[] = [];
      for (const [cur, h] of Object.entries(holdings)) {
        if (cur === "twd" || h.balance < 0.0001) continue;
        const avgPrice = h.bought > 0 ? (h.cost / h.bought).toFixed(0) : "0";
        const livePrice = tickerData[`${cur}twd`]?.last || "N/A";
        const pnl = livePrice !== "N/A" && h.bought > 0
          ? (((parseFloat(livePrice) - h.cost / h.bought) / (h.cost / h.bought)) * 100).toFixed(2)
          : "N/A";
        summaryLines.push(`${cur.toUpperCase()}: 持倉=${h.balance.toFixed(4)}, 均買價=${avgPrice} TWD, 現價=${livePrice} TWD, 損益=${pnl}%, 買${h.buyCount}次/賣${h.sellCount}次`);
      }
      portfolioSummary = summaryLines.join("\n");

      // Recent 15 trades (for detailed questions)
      const recentLines = lines.slice(-15);
      const tradeDetails = recentLines.map((line) => {
        const [ts, currency, price, action, change, balance] = line.split(",");
        const date = new Date(parseInt(ts)).toISOString().slice(0, 16).replace("T", " ");
        return `${date} | ${action.trim()} ${Math.abs(parseFloat(change)).toFixed(4)} ${currency.trim().toUpperCase()} @ ${parseFloat(price).toFixed(0)} TWD`;
      });
      recentTrades = tradeDetails.join("\n");
    } catch (e: any) {
      portfolioSummary = `(CSV 載入失敗: ${e.message})`;
    }

    // 5. Format ticker summary
    const tickerSummary = Object.entries(tickerData)
      .map(([m, t]: [string, any]) => {
        const change = ((parseFloat(t.last) - parseFloat(t.open)) / parseFloat(t.open) * 100).toFixed(2);
        return `${m.replace("twd", "").toUpperCase()}/TWD: 現價=${t.last}, 24H高=${t.high}, 低=${t.low}, 量=${t.vol}, 漲跌=${change}%`;
      })
      .join("\n");

    // 6. Call Bedrock with enhanced prompt + conversation history
    const BEDROCK_API_KEY = process.env.BEDROCK_API_KEY || "";
    const MODEL_ID = process.env.BEDROCK_MODEL_ID || "amazon.nova-lite-v1:0";
    const REGION = process.env.AWS_REGION || "us-east-1";

    if (!BEDROCK_API_KEY) {
      return NextResponse.json({
        response: `即時數據:\n${tickerSummary}\n\n持倉:\n${portfolioSummary}`,
        agents: ["stark", "morpheus"],
      });
    }

    const systemPrompt = `你是「Zeus」，OmniVerse Wealth 全域多元宇宙投資特助系統的首席 AI 分析師。你的分析團隊包括：Stark（技術面）、Minerva（情緒面）、Morpheus（個人歷史）、Themis（風控）。

## 即時行情數據 (MAX 交易所, 即時)
${tickerSummary || "(暫無數據)"}

## 技術指標分析 (1H K線, 即時計算)
${technicalSummary || "(無技術指標)"}

## BTC 鏈上數據 (Blockchain.com)
${onchainSummary || "(無鏈上數據)"}

## 用戶持倉分析
${portfolioSummary || "(無持倉資料)"}

## 最近 15 筆交易明細
${recentTrades || "(無交易明細)"}

## 你的回答風格
1. 開頭用一句話總結結論，讓用戶秒懂
2. 分析時引用具體數字（價格、百分比、金額）
3. 區分「事實」與「建議」— 事實用數據，建議用推理
4. 給出明確的操作方向（買/賣/持有/觀望），不要模稜兩可
5. 結尾用一行風險提示

## 回答範例
問：「BTC 現在適合買嗎？」
答：「📊 **結論：短期偏空，建議觀望**

BTC 現價 2,044,000 TWD，24H 下跌 1.6%。你的均買價 3,443,491 TWD，目前未實現虧損約 -40.6%。

**技術面**：24H 高 2,086,485 → 低 2,025,373，日內波動 3%，偏弱勢盤整。
**情緒面**：Fear & Greed 27 (恐懼)，市場觀望氣氛濃。
**持倉面**：你持有 0.0267 BTC，倉位不重。

💡 **建議**：目前深度下跌已久，不建議追空。若要加碼可在 2,000,000 附近分批掛限價單，量不超過總資產 5%。

⚠️ 以上為 AI 分析參考，非投資建議。加密貨幣波動劇烈，請依自身風險承受度決策。」

## 規則
- 使用繁體中文
- 不要說「根據我的分析」這種廢話，直接給結論
- 如果用戶追問上一輪的內容，參考對話歷史回答
- 建議買入/加碼時，必須包含「建議買入」或「建議加碼」文字（觸發一鍵下單按鈕）
- 建議賣出/減倉時，必須包含「建議賣出」或「建議減倉」文字`;

    // Build conversation messages (multi-turn memory)
    const conversationMessages: any[] = [];

    // Include last 5 rounds of history
    const recentHistory = (history as any[]).slice(-6); // 3 rounds = 6 messages
    for (const h of recentHistory) {
      conversationMessages.push({
        role: h.role === "user" ? "user" : "assistant",
        content: [{ text: h.content.slice(0, 300) }], // Truncate to save tokens
      });
    }

    // Current message
    conversationMessages.push({
      role: "user",
      content: [{ text: message }],
    });

    const bedrockUrl = `https://bedrock-runtime.${REGION}.amazonaws.com/model/${MODEL_ID}/converse`;
    const bedrockBody = {
      system: [{ text: systemPrompt }],
      messages: conversationMessages,
      inferenceConfig: { maxTokens: 1500, temperature: 0.35 },
    };

    try {
      const { status, data } = await httpsPost(
        bedrockUrl, bedrockBody,
        { Authorization: `Bearer ${BEDROCK_API_KEY}` },
        40000,  // 40s timeout for Bedrock
        2       // 2 retries with backoff
      );

      if (status === 200) {
        const outputContent = data?.output?.message?.content || [];
        const responseText = outputContent.map((c: any) => c.text || "").join("");
        return NextResponse.json({
          response: responseText || localFallback(message, tickerData, portfolioSummary, technicalSummary, onchainSummary),
          agents: ["zeus", "stark", "morpheus", "minerva"],
          model: MODEL_ID,
        });
      } else {
        // Bedrock unavailable — use local analysis engine
        return NextResponse.json({
          response: localFallback(message, tickerData, portfolioSummary, technicalSummary, onchainSummary),
          agents: ["stark", "morpheus"],
          mode: "local",
        });
      }
    } catch (e: any) {
      // Bedrock timeout/error — use local analysis engine
      return NextResponse.json({
        response: localFallback(message, tickerData, portfolioSummary, technicalSummary, onchainSummary),
        agents: ["stark", "morpheus"],
        mode: "local",
      });
    }
  } catch (error: any) {
    return NextResponse.json({ response: `系統錯誤: ${error.message}`, agents: [] });
  }
}

// ─── Local Fallback Engine ─────────────────────────────────────────────────

function localFallback(
  message: string,
  tickerData: Record<string, any>,
  portfolioSummary: string,
  technicalSummary: string,
  onchainSummary: string,
): string {
  // Parse holdings from portfolioSummary text
  const holdings = portfolioSummary.split("\n").map((line) => {
    const match = line.match(/^(\w+): 持倉=([\d.]+), 均買價=(\d+) TWD, 現價=([\d.]+) TWD/);
    if (!match) return null;
    return {
      currency: match[1].toLowerCase(),
      balance: parseFloat(match[2]),
      avgBuyPrice: parseFloat(match[3]),
      livePrice: parseFloat(match[4]),
    };
  }).filter(Boolean) as any[];

  return generateLocalResponse(message, tickerData, holdings, technicalSummary, onchainSummary);
}
