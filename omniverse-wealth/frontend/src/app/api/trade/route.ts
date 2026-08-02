import { NextRequest, NextResponse } from "next/server";
import { createHmac } from "crypto";

/**
 * POST /api/trade
 *
 * Execute a trade on MAX Exchange via Private API.
 * Supports both manual (user-triggered) and auto (system-triggered) orders.
 *
 * Body: { market, side, volume, price?, ord_type?, auto?: boolean }
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { market, side, volume, price, ord_type = "market", auto = false } = body;

    if (!market || !side || !volume) {
      return NextResponse.json({ error: "market, side, volume are required" }, { status: 400 });
    }

    const API_KEY = process.env.MAX_API_KEY || "";
    const API_SECRET = process.env.MAX_API_SECRET || "";
    const ENABLE_TRADING = process.env.MAX_ENABLE_TRADING || "0";

    if (!API_KEY || !API_SECRET) {
      return NextResponse.json({ error: "MAX API credentials not configured" }, { status: 403 });
    }

    if (ENABLE_TRADING !== "1" && ENABLE_TRADING !== "true") {
      return NextResponse.json({
        error: "Trading is disabled. Set MAX_ENABLE_TRADING=1 to enable.",
        simulated: true,
        order: { market, side, volume, price, ord_type, status: "simulated" },
      });
    }

    // Build order params
    const nonce = Date.now();
    const params: Record<string, any> = {
      nonce,
      market,
      side,
      volume,
      ord_type,
    };
    if (price && ord_type === "limit") {
      params.price = price;
    }

    const path = "/api/v3/orders";
    const paramsToBeSigned = { ...params, path };
    const payload = Buffer.from(JSON.stringify(paramsToBeSigned)).toString("base64");
    const signature = createHmac("sha256", API_SECRET).update(payload).digest("hex");

    // Submit to MAX
    const res = await fetch(`https://max-api.maicoin.com${path}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-MAX-ACCESSKEY": API_KEY,
        "X-MAX-PAYLOAD": payload,
        "X-MAX-SIGNATURE": signature,
      },
      body: JSON.stringify(params),
    });

    const data = await res.json();

    if (res.ok) {
      return NextResponse.json({
        success: true,
        order: data,
        auto,
        message: `${auto ? "[自動調倉]" : ""} ${side === "buy" ? "買入" : "賣出"} ${volume} ${market.replace("twd", "").toUpperCase()} 成功`,
      });
    } else {
      return NextResponse.json({
        success: false,
        error: data?.error?.message || "Order failed",
        code: data?.error?.code,
        simulated: false,
      });
    }
  } catch (error: any) {
    return NextResponse.json({ success: false, error: error.message }, { status: 500 });
  }
}
