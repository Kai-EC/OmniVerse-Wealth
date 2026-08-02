import { NextRequest, NextResponse } from "next/server";
import { httpsGet } from "@/lib/httpGet";

/**
 * GET /api/klines?market=btctwd&period=60&limit=100
 *
 * Fetches real K-line data from MAX Exchange API via native https.
 */
export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const market = searchParams.get("market") || "btctwd";
  const period = searchParams.get("period") || "60";
  const limit = searchParams.get("limit") || "100";

  try {
    const rawKlines = await httpsGet(
      `https://max-api.maicoin.com/api/v3/k?market=${market}&period=${period}&limit=${limit}`,
      6000
    );

    // MAX API returns: [[timestamp, open, high, low, close, volume], ...]
    const klines = rawKlines.map((k: number[]) => ({
      time: k[0],
      open: k[1],
      high: k[2],
      low: k[3],
      close: k[4],
      volume: k[5],
    }));

    return NextResponse.json({ market, period, klines });
  } catch (error: any) {
    return NextResponse.json({ error: error.message, klines: [] }, { status: 500 });
  }
}
