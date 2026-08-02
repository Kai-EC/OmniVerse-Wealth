import { NextRequest, NextResponse } from "next/server";
import { httpsGet } from "@/lib/httpGet";

/**
 * GET /api/depth?market=btctwd&limit=8
 *
 * Proxies MAX order book depth data.
 */
export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const market = searchParams.get("market") || "btctwd";
  const limit = searchParams.get("limit") || "8";

  try {
    const data = await httpsGet(
      `https://max-api.maicoin.com/api/v3/depth?market=${market}&limit=${limit}`,
      5000
    );
    return NextResponse.json(data);
  } catch (error: any) {
    return NextResponse.json({ asks: [], bids: [], error: error.message }, { status: 500 });
  }
}
