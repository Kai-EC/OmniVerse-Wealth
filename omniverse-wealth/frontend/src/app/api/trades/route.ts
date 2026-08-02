import { NextRequest, NextResponse } from "next/server";
import { httpsGet } from "@/lib/httpGet";

/**
 * GET /api/trades?market=btctwd&limit=20
 *
 * Proxies MAX recent trades data.
 */
export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const market = searchParams.get("market") || "btctwd";
  const limit = searchParams.get("limit") || "20";

  try {
    const data = await httpsGet(
      `https://max-api.maicoin.com/api/v3/trades?market=${market}&limit=${limit}`,
      5000
    );
    return NextResponse.json(data);
  } catch (error: any) {
    return NextResponse.json([], { status: 500 });
  }
}
