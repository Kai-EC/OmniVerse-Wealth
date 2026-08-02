# OmniVerse Wealth 架構設計書 (Design)

## 1. 系統架構概覽

採用 AWS 雲端原生無伺服器（Serverless）架構與 Event-Driven 事件驅動設計，結合 Amazon Bedrock 驅動之 Multi-Agent（多 Agent 協作）體系。

```
[ 前端應用層 (Next.js HUD Dashboard) ]
        │
   (HTTPS / WebSocket API)
        │
        ▼
[ Amazon API Gateway ]
        │
        ▼
[ AWS Lambda / Fargate ]
(Multi-Agent Controller / LangGraph)
        │
┌───────┼───────┐
│       │       │
▼       ▼       ▼
[Bedrock] [Bedrock KB] [DynamoDB]
│         │            │
▼         ▼            ▼
[MAX API] [CSV RAG]  [Session/Risk]
[MAX MCP]
[3rd Party]
```

## 2. Multi-Agent 體系設計

### 2.1 Agent 角色定義

| Agent | 角色 | 職責 | 權限 |
|-------|------|------|------|
| 宙斯 (Zeus) | 總指揮官 | 意圖解析、任務拆解、結果彙整 | Orchestrator |
| 史塔克 (Stark) | 市場技術面 | 即時行情、K線形態、深度圖、技術指標 | Read-Only |
| 密涅瓦 (Minerva) | 輿論鏈上 | 社群情緒、恐懼貪婪指數、巨鯨監控 | Read-Only |
| 墨菲斯 (Morpheus) | 個人化歷史 | CSV RAG 分析、持倉均價、歷史勝率 | Read-Only (Private) |
| 提彌斯 (Themis) | 風控閘門 | 確定性風控規則、否決權 | Gatekeeper (Veto) |
| 赫密士 (Hermes) | 交易執行 | MAX API 下單、訂單管理 | Write (Execute) |

### 2.2 工作流程 (LangGraph StateGraph)

```
[START] → [zeus_parse_intent]
                │
    ┌───────────┼───────────┐  (並行)
    ▼           ▼           ▼
[stark]    [minerva]   [morpheus]
    │           │           │
    └───────────┼───────────┘
                │
        [should_trade?]
           │         │
        Yes│         │No
           ▼         │
    [themis_evaluate] │
           │         │
    [trade_gate?]    │
      │       │      │
   Pass│    Fail│     │
      ▼       │      │
  [hermes]    │      │
      │       │      │
      └───────┼──────┘
              ▼
    [zeus_synthesize] → [END]
```

### 2.3 共用狀態 (OmniVerseState)

```python
class OmniVerseState:
    messages: list[BaseMessage]       # 對話歷史
    user_query: str                   # 用戶輸入
    intent: str                       # 意圖分類
    required_agents: list[AgentRole]  # 需調度的 Agent
    reports: list[AgentReport]        # 各 Agent 報告
    trade_intent: TradeIntent | None  # 交易意圖
    risk_verdict: RiskVerdict | None  # 風控結果
    trade_approved: bool              # 核准狀態
    trade_result: dict | None         # 執行結果
    final_response: str               # 最終回覆
```

## 3. 技術選型

### 3.1 後端核心

| 層級 | 技術選型 | 說明 |
|------|---------|------|
| 語言 | Python 3.12+ | AWS Lambda/Fargate 環境 |
| Agent 框架 | LangGraph | 有狀態、可中斷的 Multi-Agent 工作流 |
| LLM | Amazon Bedrock (Claude 3.5 Sonnet) | Function Calling + 思考邏輯 |
| API Client | httpx (async) | HMAC-SHA256 簽名的 MAX V3 REST API |
| 套件管理 | uv | 快速依賴解析與安裝 |
| 設定管理 | pydantic-settings | 環境變數 + .env 檔 |

### 3.2 前端

| 技術 | 用途 |
|------|------|
| Next.js | React SSR 框架 |
| TailwindCSS | Utility-first CSS |
| TradingView Lightweight Charts | K線/價格圖表 |
| WebSocket | 實時串流回應 |

### 3.3 AWS 雲端服務

| 服務 | 用途 |
|------|------|
| API Gateway (WebSocket) | 前端連線入口 |
| Lambda / Fargate | Multi-Agent 運算 |
| Amazon Bedrock | LLM 推理引擎 |
| Bedrock Knowledge Bases | CSV RAG 向量知識庫 |
| OpenSearch Serverless | 向量搜尋 |
| DynamoDB | Session/風控規則儲存 |
| Secrets Manager | API Key 安全存放 |

### 3.4 外部整合

| 服務 | 端點 | 用途 |
|------|------|------|
| MAX REST API | max-api.maicoin.com/api/v3/* | 行情+帳戶+交易 |
| MAX MCP Server | bistin/max-mcp-server | Agent Tool 介面 |
| MAX API Skill | bistin/max-api-skill | Agent 知識文件 |
| CoinMarketCap | api.coinmarketcap.com | 幣種全球排名 |
| Blockchain.com | api.blockchain.info | BTC 鏈上指標 |
| Alternative.me | api.alternative.me/fng | 恐懼貪婪指數 |

## 4. 安全性設計

### 4.1 權限分離
- 分析 Agent (Zeus, Stark, Minerva, Morpheus): IAM 唯讀角色
- 風控 Agent (Themis): Gatekeeper 角色，具否決權
- 執行 Agent (Hermes): 唯一具寫入 MAX API 權限的角色

### 4.2 風控閘門 (Deterministic Guardrails)
- 單筆下單 ≤ 帳戶總資產 10%
- 市場單日波動 > 20% 時熔斷
- 單日交易筆數 ≤ 20
- 兩筆交易間隔 ≥ 30 秒
- 訂單金額邊界：100 ~ 500,000 TWD

### 4.3 API 認證機制
- HMAC-SHA256 簽名：X-MAX-ACCESSKEY / X-MAX-PAYLOAD / X-MAX-SIGNATURE
- Nonce 毫秒時間戳，±30 秒容差
- Secrets Manager 自動旋轉

### 4.4 隱私保護
- CSV 寫入 Bedrock KB 前執行 PII 遮蔽
- 去識別化處理

## 5. 數據流 (閉環交易 Sequence)

```
用戶: "我最近 BTC 的持倉表現如何？現在適合加碼嗎？"

1. [前端] → API Gateway → Lambda (Zeus)
2. [Zeus] 解析意圖 → 併行調度:
   - [Morpheus] → Bedrock KB → 用戶 BTC 持倉成本/均價/損益
   - [Stark] → MAX API → BTC/TWD 即時 K 線、深度
   - [Minerva] → X/Threads → BTC 社群情緒指數
3. [Zeus] 彙整報告 → 生成建議: "建議分批加碼 0.05 BTC"
4. [Themis] 風控審查:
   - ✅ 單筆 ≤ 10% 帳戶資產
   - ✅ 市場波動 < 20%
   → 渲染「交易確認卡片」
5. [用戶] 點擊【授權並下單】
6. [Hermes] → MAX MCP/Skill → MAX Private API → 完成下單
7. [前端] 更新持倉圖表
```
