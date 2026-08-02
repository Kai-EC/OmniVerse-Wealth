import { NextRequest, NextResponse } from "next/server";
import { httpsGet } from "@/lib/httpGet";

/**
 * GET /api/onchain
 *
 * Fetches Bitcoin on-chain data from Blockchain.com public API.
 * No API key required.
 */
export async function GET(request: NextRequest) {
  try {
    const stats = await httpsGet("https://api.blockchain.info/stats", 8000);

    return NextResponse.json({
      btc_price_usd: stats.market_price_usd,
      hash_rate_th: (stats.hash_rate / 1e12).toFixed(1),
      difficulty: stats.difficulty,
      total_tx_24h: stats.n_tx,
      blocks_mined_24h: stats.n_blocks_mined,
      minutes_between_blocks: stats.minutes_between_blocks,
      total_btc_sent_24h: (stats.total_btc_sent / 1e8).toFixed(2),
      miners_revenue_usd: stats.miners_revenue_usd,
      timestamp: Date.now(),
    });
  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
