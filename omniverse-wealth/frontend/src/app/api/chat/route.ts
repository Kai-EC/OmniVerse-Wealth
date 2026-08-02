import { NextRequest, NextResponse } from "next/server";

/**
 * POST /api/chat
 *
 * Proxies user queries to the OmniVerse Wealth backend (Multi-Agent system).
 * In production, this connects to the AWS API Gateway endpoint.
 * During development, returns mock responses.
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { message } = body;

    if (!message) {
      return NextResponse.json(
        { error: "Message is required" },
        { status: 400 }
      );
    }

    // TODO: In production, forward to AWS API Gateway
    // const backendUrl = process.env.BACKEND_API_URL;
    // const response = await fetch(`${backendUrl}/query`, {
    //   method: "POST",
    //   headers: { "Content-Type": "application/json" },
    //   body: JSON.stringify({ user_query: message }),
    // });
    // const data = await response.json();

    // Development: Return mock agent response
    const mockResponse = {
      intent: "query_market",
      agents_invoked: ["stark", "minerva", "morpheus"],
      final_response: generateMockResponse(message),
      trade_suggestion: null,
    };

    return NextResponse.json(mockResponse);
  } catch (error) {
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}

function generateMockResponse(query: string): string {
  if (query.toLowerCase().includes("btc") || query.includes("比特幣")) {
    return `根據 Multi-Agent 會診結果：

**市場分析 (史塔克)**
BTC/TWD 當前報價 3,452,100，24H 漲幅 +2.3%。RSI(14) 為 58.4，處於中性偏多區間。短期支撐 3,380,000，壓力位 3,520,000。

**情緒分析 (密涅瓦)**
恐懼貪婪指數 62 (Greed)，社群情緒偏向樂觀。近期無重大利空事件。

**個人持倉 (墨菲斯)**
你持有 0.02673 BTC，均價 3,443,491 TWD，目前小幅獲利 +0.25%。

建議：市場情緒正面且技術面支撐良好，可考慮在回調至支撐位時小幅加碼。`;
  }

  return `已收到你的問題。Agent 團隊正在處理中，請稍候...`;
}
