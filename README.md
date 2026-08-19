# OmniVerse Wealth 全域多元宇宙投資特助系統

> 2026 雲湧智生：臺灣生成式 AI 應用黑客松 — MaiCoin 智慧理財命題

[![AWS](https://img.shields.io/badge/AWS-Bedrock%20%7C%20Lambda%20%7C%20DynamoDB-orange)](https://aws.amazon.com)
[![Python](https://img.shields.io/badge/Python-3.12+-blue)](https://python.org)
[![Next.js](https://img.shields.io/badge/Next.js-16-black)](https://nextjs.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-Multi--Agent-green)](https://langchain-ai.github.io/langgraph/)

## 專案簡介

OmniVerse Wealth 採用 AWS 雲端原生 Serverless 架構與 Amazon Bedrock 驅動的 Multi-Agent 體系，串接 MAX 交易所 API、MCP Server 與 Skill 模組，實現從「多維度數據實時會診」、「個人化歷史 RAG 分析」至「一鍵對話式安全下單」的端到端閉環交易生態。

## 系統架構

```
┌─────────────────────────────────────────────────────────────────┐
│          Frontend (Next.js + TradingView + Agent Orbit)          │
├─────────────────────────────────────────────────────────────────┤
│         API Gateway (REST + WebSocket Real-time)                 │
├─────────────────────────────────────────────────────────────────┤
│         Lambda / LangGraph Multi-Agent Controller                │
├────────┬────────┬────────┬────────┬────────┬────────────────────┤
│  Zeus  │ Stark  │Minerva │Morpheus│ Themis │      Hermes        │
│Commander│Market │Sentiment│ RAG   │  Risk  │     Executor       │
├────────┴────────┴────────┴────────┴────────┴────────────────────┤
│ Bedrock │ MAX API │ Bedrock KB │ DynamoDB │ Secrets │ Discord Bot│
└─────────────────────────────────────────────────────────────────┘
```

## Multi-Agent 體系

| Agent | 角色 | 功能 | 權限 |
|-------|------|------|------|
| 🏛️ Zeus | Commander | 意圖解析、任務拆解、結果彙整、多輪對話記憶 | Orchestrator |
| 📊 Stark | Market & Technical | K線形態、RSI/MA/MACD/布林帶、深度圖分析 | Read-Only |
| 🔮 Minerva | Sentiment | Fear & Greed Index、社群情緒、巨鯨監控 | Read-Only |
| 🧠 Morpheus | Personal History | CSV RAG (10,000筆)、持倉均價、歷史勝率 | Read-Only |
| ⚖️ Themis | Risk Control | 確定性 Guardrails、波動熔斷、二階段驗證 | Gatekeeper (Veto) |
| ⚡ Hermes | Trade Execution | MAX API 下單、自動調倉、Discord Bot 執行 | Write |

## 核心功能

### 即時數據面板
- **K 線圖** — MAX 交易所真實 1H K 線，WebSocket 即時更新最新蠟燭
- **Order Book** — 即時買賣掛單深度，紅綠量柱
- **Recent Trades** — 最近 20 筆即時成交
- **Ticker** — Header 即時價格跳動 (BTC/ETH/SOL/DOGE)
- **Fear & Greed Index** — Alternative.me 情緒指標 + 進度條

### AI 智慧分析
- **Bedrock LLM** — Amazon Nova Lite 即時推理
- **技術指標注入** — RSI(14)、MA(7/25/99)、EMA(12/26)、MACD、布林帶、ATR 即時計算
- **多輪對話記憶** — 最近 5 輪上下文，支援追問
- **Few-shot Prompt** — 統一回答風格：結論→數據→建議→風險提示
- **最近 30 筆交易明細** — 回答具體歷史操作問題

### 交易執行
- **Chat 一鍵下單** — AI 建議買/賣時自動顯示執行按鈕
- **自動調倉** — 持倉幣種 24H 下跌 > 10% 自動賣出 20%
- **Discord Bot 交易** — `!buy btc 0.001` / `!sell eth 0.01 price=60000`
- **二階段 HMAC 驗證** — Token 防篡改、5 分鐘過期

### 風控引擎 (61 項測試通過)
- 單筆限額 ≤ 帳戶 10%
- 波動熔斷 (24H > 20% 暫停)
- 冷卻期 30 秒 + 每日 20 筆上限
- 確定性邏輯 (非 LLM，不可被繞過)

### 通知系統
- **Discord Webhook** — 波動警報即時推送
- **自動調倉通知** — 執行結果 Embed 推送
- **Alert Banner** — 前端即時顯示警報 + AI 建議

### Agent 星系圖可視化
- Zeus 中心持續發光，5 Agent 環繞軌道
- 查詢時光束射向目標 Agent + 粒子動畫
- 處理完成節點轉綠 + ✓
- 純 SVG + CSS，零外部依賴

## 技術棧

| 層級 | 技術 |
|------|------|
| 前端 | Next.js 16 · TailwindCSS · TradingView Lightweight Charts v5 · SVG Animation |
| AI | Amazon Bedrock (Nova Lite) · LangGraph · Multi-Agent · RAG |
| 後端 | Python 3.12 · httpx · Pydantic · WebSocket |
| 交易 | MAX V3 REST API · HMAC-SHA256 簽名 · MCP Server · Skill |
| 風控 | Guardrail Engine · Rate Limiter · Circuit Breaker · Trade Authorizer |
| 數據 | CSV Processor (10,000 筆) · PII Masker · Bedrock KB · Fear/Greed API |
| 通知 | Discord Bot (discord.py) · Discord Webhook |
| 雲端 | AWS CDK · API Gateway · Lambda · DynamoDB · Secrets Manager · S3 · CloudFront |
| 工具 | Kiro IDE · uv · MAX MCP Server |

## 快速開始

### 前提條件
- Node.js 22+
- Python 3.12+ (建議用 uv)
- AWS Bedrock API Key
- MAX Exchange API Key

### 後端

```bash
cd omniverse-wealth
uv sync
cp .env.example .env  # 填入 API Keys
uv run python -m src.main "BTC 目前適合加碼嗎？"
```

### 前端

```bash
cd frontend
npm install
# 建立 .env.local 填入 BEDROCK_API_KEY, MAX_API_KEY, MAX_API_SECRET
npm run dev  # http://localhost:3000
```

### WebSocket Server (即時行情)

```bash
uv run python -m src.ws_server  # ws://localhost:8080
```

### Discord Bot

```bash
uv run python -m src.discord_bot
```

Discord 指令：
- `!help` — 查看指令
- `!price btc` — 即時價格
- `!balance` — 帳戶餘額
- `!portfolio` — 持倉損益
- `!buy btc 0.001` — 市價買入 (需確認)
- `!sell eth 0.01 price=60000` — 限價賣出

### AWS 部署

```powershell
cd infra
.\deploy.ps1
```

## 專案結構

```
omniverse-wealth/
├── src/                          # Python 後端
│   ├── agents/                   # 6 Multi-Agent (Zeus/Stark/Minerva/Morpheus/Themis/Hermes)
│   ├── tools/                    # MAX API Client + CoinMarketCap + Blockchain + WebSocket
│   ├── rag/                      # CSV Processor + PII Masker + Embedder + Bedrock KB
│   ├── guardrails/               # Engine + Rate Limiter + Circuit Breaker + Authorizer
│   ├── graph.py                  # LangGraph 工作流
│   ├── ws_server.py              # WebSocket Dev Server (即時行情推送)
│   ├── discord_bot.py            # Discord Trading Bot
│   └── notify_discord.py         # Discord Webhook 通知
├── frontend/                     # Next.js HUD Dashboard
│   ├── src/app/api/              # agent, ticker, klines, depth, trades, portfolio, alerts, trade
│   ├── src/components/           # ChartPanel, PortfolioPanel, ChatPanel, AgentOrbitGraph...
│   ├── src/hooks/                # useWebSocket
│   └── src/lib/                  # httpGet, indicators, discord
├── infra/                        # AWS CDK
│   ├── stacks/                   # 6 CloudFormation Stacks
│   └── lambda/                   # Agent + WebSocket handlers
├── tests/                        # 61 項測試 (guardrails + graph + max_client + rag)
└── .kiro/                        # Kiro IDE 配置
    ├── settings/mcp.json         # MAX MCP Server
    └── specs/                    # Requirements / Design / Tasks
```

## 安全性設計

| 機制 | 說明 |
|------|------|
| 職責分離 | 分析 Agent 唯讀，僅 Hermes 有寫入權 |
| 確定性風控 | 61 項測試覆蓋，純邏輯不受 LLM 幻覺影響 |
| 二階段驗證 | HMAC Token 簽名，參數防篡改，5 分鐘過期 |
| 波動熔斷 | 24H 漲跌 > 20% 自動暫停所有交易 |
| 自動調倉 | 下跌 > 10% 自動減倉 20%，Discord 即時通知 |
| API 安全 | Secrets Manager 存放，環境變數隔離 |
| PII 保護 | CSV 寫入 KB 前去識別化 |

## 競賽評分對照

| 評分項目 (佔比) | 本專案落實 |
|---------------|-----------|
| 創意度 (25%) | Multi-Agent 星系圖動態可視化 + 閉環交易 HUD |
| 技術可行性 (20%) | AWS CDK 完整 Serverless + 61 項測試通過 |
| 商業應用性 (20%) | 一鍵下單 + 自動調倉 + Discord Bot 操盤 |
| AI 設計 (15%) | 6 Agent 協作 + RAG + 技術指標計算 + 多輪記憶 |
| 主題切合度 (10%) | MAX API + MCP + Skill + CSV 深度整合 |
| 完成度 (10%) | Live Demo + GitHub + 完整端到端流程 |
| 加分項 (+10%) | MAX Lv2 實際交易 + Kiro IDE 全程開發 |

## License

MIT

---

*Built with Kiro IDE for 2026 雲湧智生 Hackathon*
