import { NextRequest, NextResponse } from "next/server";
import { httpsGet } from "@/lib/httpGet";

/**
 * GET /api/ticker
 *
 * Fetches real-time ticker data from MAX Exchange API via native https.
 */
export async function GET(request: NextRequest) {
  const markets = ["btctwd", "ethtwd", "soltwd", "dogetwd", "usdttwd"];

  try {
    const tickers: any[] = [];

    for (const market of markets) {
      try {
        const ticker = await httpsGet(
          `https://max-api.maicoin.com/api/v3/ticker?market=${market}`,
          4000
        );

        const last = parseFloat(ticker.last);
        const open = parseFloat(ticker.open);
        const changePct = open > 0 ? ((last - open) / open) * 100 : 0;

        tickers.push({
          market: ticker.market,
          symbol: ticker.market.replace("twd", "").toUpperCase() + "/TWD",
          last: ticker.last,
          open: ticker.open,
          high: ticker.high,
          low: ticker.low,
          vol: ticker.vol,
          changePct: changePct.toFixed(2),
          positive: changePct >= 0,
        });
      } catch {}
    }

    return NextResponse.json({ tickers, timestamp: Date.now() });
  } catch (error: any) {
    return NextResponse.json({ error: error.message, tickers: [] }, { status: 500 });
  }
}
