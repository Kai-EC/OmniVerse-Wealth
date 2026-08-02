import { NextRequest, NextResponse } from "next/server";
import { readFileSync } from "fs";
import { resolve } from "path";

/**
 * GET /api/portfolio
 *
 * Returns portfolio summary by combining:
 * 1. CSV historical trading data (holdings, avg prices)
 * 2. Live MAX ticker prices (current value, PnL)
 */
export async function GET(request: NextRequest) {
  try {
    // Load CSV data
    const csvPath = resolve(process.cwd(), "../../MaiCoin_最近一年份出入金及交易紀錄.csv");
    let csvContent: string;
    try {
      csvContent = readFileSync(csvPath, "utf-8");
    } catch {
      // Try alternative path
      const altPath = resolve(process.cwd(), "../MaiCoin_最近一年份出入金及交易紀錄.csv");
      csvContent = readFileSync(altPath, "utf-8");
    }
    const lines = csvContent.trim().split("\n");
    const headers = lines[0].split(",");

    // Parse records
    interface Record {
      timestamp: number;
      currency: string;
      price: number;
      action: string;
      change: number;
      balance: number;
    }

    const records: Record[] = lines.slice(1).map((line) => {
      const parts = line.split(",");
      return {
        timestamp: parseInt(parts[0]),
        currency: parts[1].trim().toLowerCase(),
        price: parseFloat(parts[2]),
        action: parts[3].trim().toLowerCase(),
        change: parseFloat(parts[4]),
        balance: parseFloat(parts[5]),
      };
    });

    // Compute portfolio from CSV
    const portfolio: { [key: string]: {
      balance: number;
      totalBought: number;
      totalBuyCost: number;
      buyCount: number;
      sellCount: number;
      avgBuyPrice: number;
    }} = {};

    for (const r of records) {
      if (!portfolio[r.currency]) {
        portfolio[r.currency] = {
          balance: 0, totalBought: 0, totalBuyCost: 0,
          buyCount: 0, sellCount: 0, avgBuyPrice: 0,
        };
      }
      const p = portfolio[r.currency];
      p.balance = r.balance;

      if (r.action === "buy") {
        p.totalBought += Math.abs(r.change);
        p.totalBuyCost += Math.abs(r.change) * r.price;
        p.buyCount++;
      } else if (r.action === "sell") {
        p.sellCount++;
      }
    }

    // Calculate avg buy price
    for (const cur of Object.keys(portfolio)) {
      const p = portfolio[cur];
      if (p.totalBought > 0) {
        p.avgBuyPrice = p.totalBuyCost / p.totalBought;
      }
    }

    // Fetch live prices from MAX
    const cryptos = ["btc", "eth", "sol", "doge", "usdt", "usdc"];
    const livePrices: { [key: string]: number } = { twd: 1 };

    await Promise.all(
      cryptos.map(async (cur) => {
        try {
          const res = await fetch(
            `https://max-api.maicoin.com/api/v3/ticker?market=${cur}twd`,
            { cache: "no-store" }
          );
          if (res.ok) {
            const data = await res.json();
            livePrices[cur] = parseFloat(data.last);
          }
        } catch {}
      })
    );

    // Build response
    const holdings = cryptos
      .filter((cur) => portfolio[cur] && portfolio[cur].balance > 0.0001)
      .map((cur) => {
        const p = portfolio[cur];
        const livePrice = livePrices[cur] || 0;
        const currentValue = p.balance * livePrice;
        const costBasis = p.balance * p.avgBuyPrice;
        const pnl = costBasis > 0 ? ((currentValue - costBasis) / costBasis) * 100 : 0;

        return {
          currency: cur.toUpperCase(),
          balance: p.balance.toFixed(cur === "usdt" || cur === "usdc" ? 2 : 8),
          avgBuyPrice: p.avgBuyPrice.toFixed(cur === "usdt" || cur === "usdc" ? 2 : 0),
          currentPrice: livePrice.toFixed(cur === "usdt" || cur === "usdc" ? 2 : 1),
          currentValue: currentValue.toFixed(0),
          pnlPercent: pnl.toFixed(2),
          positive: pnl >= 0,
          buyCount: p.buyCount,
          sellCount: p.sellCount,
        };
      });

    const totalValue = holdings.reduce(
      (sum, h) => sum + parseFloat(h.currentValue), 0
    );

    return NextResponse.json({
      holdings,
      totalValue: totalValue.toFixed(0),
      recordCount: records.length,
      lastUpdate: Date.now(),
    });
  } catch (error: any) {
    return NextResponse.json(
      { error: error.message, holdings: [], totalValue: "0" },
      { status: 500 }
    );
  }
}
