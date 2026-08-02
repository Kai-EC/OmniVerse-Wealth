# OmniVerse Wealth 需求規格書

## 簡介

OmniVerse Wealth（全域多元宇宙投資特助系統）是針對「2026 雲湧智生：臺灣生成式 AI 應用黑客松競賽」MaiCoin 命題所研發之多 Agent AI 投資助理系統。系統透過六個專業 Agent 協作，整合即時行情、鏈上數據、社群輿論與個人歷史交易分析，提供閉環式智慧投資建議與自動下單執行功能。

## 詞彙表

- **Zeus（宙斯）**：系統總指揮 Agent，負責意圖解析、任務調度與結果彙整
- **Stark（史塔克）**：市場與技術分析 Agent，負責即時行情、K 線形態與技術指標
- **Minerva（密涅瓦）**：鏈上數據與輿論情緒分析 Agent
- **Morpheus（墨菲斯）**：個人歷史交易 RAG 分析 Agent
- **Themis（提彌斯）**：風險控制閘門 Agent，擁有交易否決權
- **Hermes（赫密士）**：交易執行 Agent，唯一具備下單寫入權限的 Agent
- **MAX_API**：MaiCoin/MAX 交易所 V3 REST API
- **MAX_MCP_Server**：MAX 交易所 MCP 工具式 API 存取伺服器
- **HUD_Dashboard**：抬頭顯示器式互動儀表板前端介面
- **Guardrail_Engine**：確定性風控規則引擎（不依賴 LLM）
- **RAG_Knowledge_Base**：基於 Amazon Bedrock Knowledge Bases 與 OpenSearch Serverless 的向量檢索知識庫
- **Trade_Confirmation_Card**：交易確認卡片，供使用者授權交易之 UI 元件
- **Fear_Greed_Index**：貪婪恐懼指數，綜合多維度數據反映市場情緒（0-100）
- **OmniVerseState**：LangGraph 工作流程中各 Agent 共享的狀態物件

## 需求

### 需求 1：自然語言意圖解析與任務調度

**使用者故事：** 身為投資者，我希望以自然語言提問投資相關問題，系統能準確理解我的意圖並調度適當的專家 Agent 進行分析，以便獲得精準且全面的回覆。

#### 驗收條件

1. WHEN 使用者輸入自然語言查詢，THE Zeus SHALL 將其解析為以下意圖分類之一：query_portfolio、query_market、query_sentiment、trade_suggestion、execute_trade、general
2. WHEN Zeus 完成意圖解析，THE Zeus SHALL 產生包含 intent、required_agents、trade_intent 與 brief_plan 的結構化 JSON 回應
3. WHEN 意圖涉及持倉查詢，THE Zeus SHALL 將 Morpheus 納入 required_agents 列表
4. WHEN 意圖涉及市場行情，THE Zeus SHALL 將 Stark 納入 required_agents 列表
5. WHEN 意圖涉及情緒分析，THE Zeus SHALL 將 Minerva 納入 required_agents 列表
6. WHEN 意圖為 execute_trade，THE Zeus SHALL 產生完整的 trade_intent 物件（包含 market、side、volume、ord_type）
7. IF Zeus 無法解析使用者意圖，THEN THE Zeus SHALL 退回至保守路由策略（預設調度 Stark 與 Morpheus）
8. WHEN 多個專家 Agent 被指派，THE LangGraph_Workflow SHALL 以平行方式執行各 Agent 分析節點

### 需求 2：即時行情與技術分析

**使用者故事：** 身為投資者，我希望獲得即時的加密貨幣行情數據與技術分析，以便做出有依據的交易決策。

#### 驗收條件

1. WHEN 使用者查詢特定幣種行情，THE Stark SHALL 透過 MAX_API 取得該幣種的即時 ticker 數據（最新價、24 小時漲跌幅、成交量）
2. WHEN Stark 執行技術分析，THE Stark SHALL 取得至少最近 24 根 1 小時 K 線數據
3. WHEN Stark 執行深度分析，THE Stark SHALL 取得至少 20 檔買賣掛單深度
4. WHEN Stark 執行分析，THE Stark SHALL 取得最近 30 筆公開成交明細
5. WHEN Stark 完成分析，THE Stark SHALL 產生包含趨勢判斷（多/空/盤整）、支撐壓力價位、買賣力道比率與技術指標訊號的結構化報告
6. WHEN 使用者未指定特定幣種，THE Stark SHALL 預設分析 BTC/TWD 市場
7. IF MAX_API 回傳錯誤，THEN THE Stark SHALL 在報告中標示資料取得失敗的幣種與錯誤原因
8. THE Stark SHALL 以字串格式保留所有價格數據的原始精度

### 需求 3：鏈上數據與社群輿論情緒分析

**使用者故事：** 身為投資者，我希望了解當前市場情緒、社群討論熱度與鏈上大額動態，以便判斷市場風向與潛在風險。

#### 驗收條件

1. WHEN Minerva 執行情緒分析，THE Minerva SHALL 取得 Alternative.me Fear & Greed Index 最近 7 日數據
2. WHEN Minerva 執行鏈上分析，THE Minerva SHALL 取得 Bitcoin 近 7 日 hash rate 與交易量數據
3. WHEN Minerva 完成分析，THE Minerva SHALL 產生 0-100 的市場情緒指數並標示對應等級（極度恐懼/恐懼/中性/貪婪/極度貪婪）
4. WHEN Minerva 完成分析，THE Minerva SHALL 報告社群討論熱度趨勢方向（上升/下降/持平）
5. WHEN Minerva 偵測到巨鯨大額轉帳，THE Minerva SHALL 標示轉帳金額與方向（交易所入/出）
6. IF 第三方 API 連線逾時或失敗，THEN THE Minerva SHALL 在報告中標注資料來源不可用，並基於可取得的數據提供部分分析
7. THE Minerva SHALL 從使用者查詢中提取加密貨幣關鍵字用於社群搜尋過濾

### 需求 4：個人歷史交易 RAG 分析

**使用者故事：** 身為投資者，我希望系統能分析我的歷史交易紀錄，計算持倉均價與歷史勝率，以便獲得超個人化的投資建議。

#### 驗收條件

1. WHEN Morpheus 接收到持倉相關查詢，THE Morpheus SHALL 載入並解析使用者的 CSV 歷史交易紀錄（包含 timestamp、currency、price、action、change、balance 欄位）
2. WHEN Morpheus 完成 CSV 解析，THE Morpheus SHALL 計算每個幣種的加權平均買入成本（total_buy_cost_twd / total_bought）
3. WHEN Morpheus 完成分析，THE Morpheus SHALL 產生包含持倉損益、交易頻率、偏好幣種與歷史勝率的結構化報告
4. WHEN 使用者查詢包含特定幣種關鍵字，THE Morpheus SHALL 過濾並回傳該幣種最近 50 筆相關交易明細
5. THE Morpheus SHALL 以百分比或趨勢描述方式呈現分析結果，避免直接暴露使用者的確切餘額數字
6. WHEN CSV 檔案不存在或路徑無效，THE Morpheus SHALL 回傳空資料集並在報告中說明無歷史數據可用
7. FOR ALL 有效的 CSV 交易紀錄，解析後再序列化回結構化格式 SHALL 產生等價的資料物件（round-trip 屬性）

### 需求 5：CSV 資料去識別化與 RAG 向量知識庫建構

**使用者故事：** 身為投資者，我希望我的歷史交易資料在寫入雲端知識庫前經過去識別化處理，以保護個人隱私同時保留分析價值。

#### 驗收條件

1. WHEN CSV 資料寫入 RAG_Knowledge_Base 前，THE System SHALL 執行 PII 遮蔽處理（移除或雜湊可識別個人身份的欄位）
2. WHEN PII 遮蔽完成，THE System SHALL 保留交易時間戳、幣種、動作類型、價格與數量等分析所需欄位
3. THE RAG_Knowledge_Base SHALL 使用 Amazon Bedrock Knowledge Bases 搭配 OpenSearch Serverless 作為向量儲存後端
4. WHEN 使用者查詢觸發 RAG 檢索，THE RAG_Knowledge_Base SHALL 回傳與查詢語義最相關的交易紀錄片段
5. IF 去識別化後的資料與原始資料進行語義比對，THEN THE System SHALL 確保核心交易模式（買賣頻率、幣種偏好、時間分佈）得以保留

### 需求 6：確定性風險控制與交易閘門

**使用者故事：** 身為投資者，我希望系統在執行任何交易前進行嚴格的風控檢查，確保不會因單筆失誤而造成重大損失。

#### 驗收條件

1. WHEN Themis 接收到交易意圖進行評估，THE Themis SHALL 執行兩階段風控檢查：第一階段為確定性邊界檢查，第二階段為 LLM 輔助情境評估
2. THE Guardrail_Engine SHALL 執行以下確定性規則且不可被 LLM 覆寫：單筆下單金額不得超過帳戶總資產的 10%
3. THE Guardrail_Engine SHALL 執行波動熔斷規則：目標幣種單日漲跌幅超過 20% 時暫停該幣種交易
4. THE Guardrail_Engine SHALL 執行頻率限制規則：單日交易不超過 20 筆
5. THE Guardrail_Engine SHALL 執行金額邊界規則：訂單價值至少 100 TWD 且不超過 500,000 TWD
6. THE Guardrail_Engine SHALL 執行冷卻期規則：兩筆交易間隔至少 30 秒
7. WHEN 任一確定性檢查未通過，THE Themis SHALL 否決該交易並回傳具體的失敗原因與建議調整方案
8. WHEN 所有確定性檢查通過，THE Themis SHALL 進行 LLM 輔助的情境風險評估（逆勢操作、集中度過高等）
9. THE Themis SHALL 為每次風控評估產生包含 approved（布林）、risk_score（0.0-1.0）、checks_passed 與 checks_failed 的結構化 RiskVerdict
10. IF trade_intent 缺少必要欄位（market、side、volume），THEN THE Themis SHALL 拒絕評估並回傳參數不完整的錯誤

### 需求 7：交易執行與訂單管理

**使用者故事：** 身為投資者，我希望在風控通過且我明確授權後，系統能透過 MAX 交易所自動執行下單，以降低操作障礙並提高效率。

#### 驗收條件

1. WHEN trade_approved 為 True 且 risk_verdict.approved 為 True，THE Hermes SHALL 透過 MAX_API 提交交易訂單
2. WHEN trade_approved 為 False，THE Hermes SHALL 拒絕執行交易並回傳「未獲風控核准」的錯誤報告
3. WHEN risk_verdict 不存在或 approved 為 False，THE Hermes SHALL 拒絕執行交易並回傳「風控審查未通過」的錯誤報告
4. WHEN Hermes 成功提交訂單，THE Hermes SHALL 回傳包含訂單 ID、市場、方向、數量與訂單狀態的執行結果
5. IF MAX_API 回傳交易錯誤，THEN THE Hermes SHALL 記錄錯誤碼與錯誤訊息，且不得自行重試未經授權的操作
6. THE Hermes SHALL 支援 limit、market、stop_limit、stop_market 四種訂單類型
7. WHEN MAX_ENABLE_TRADING 設定為 False，THE MAX_API_Client SHALL 拒絕所有寫入操作並回傳 403 錯誤
8. THE Hermes SHALL 為系統中唯一具備交易寫入權限的 Agent，其他 Agent 僅具備唯讀存取權限

### 需求 8：多 Agent 報告彙整與投資建議生成

**使用者故事：** 身為投資者，我希望系統整合來自多個專家的分析觀點，生成一份連貫、全面且易懂的投資建議。

#### 驗收條件

1. WHEN 所有被指派的專家 Agent 完成分析，THE Zeus SHALL 彙整所有 AgentReport 並生成最終回覆
2. WHEN 最終回覆涉及交易建議，THE Zeus SHALL 明確列出幣種、方向、數量建議與理由
3. THE Zeus SHALL 在每次最終回覆中附上風險提示與免責聲明
4. THE Zeus SHALL 以繁體中文產生所有面向使用者的回覆
5. WHEN 涉及金額數據，THE Zeus SHALL 保留精確小數位不做四捨五入
6. WHEN 風控審查結果存在，THE Zeus SHALL 在最終回覆中包含審查通過/未通過狀態、風險分數與原因
7. WHEN 交易執行結果存在，THE Zeus SHALL 在最終回覆中包含訂單 ID 與執行狀態
8. THE Zeus SHALL 為每份 AgentReport 標示該 Agent 的信心度分數

### 需求 9：HUD 互動式儀表板前端

**使用者故事：** 身為投資者，我希望擁有一個多維度、動態且支援即時數據視覺化的互動式儀表板，以便直覺地掌握市場狀況與投資組合表現。

#### 驗收條件

1. THE HUD_Dashboard SHALL 使用 Next.js 搭配 TailwindCSS 建構前端介面
2. THE HUD_Dashboard SHALL 整合 TradingView Lightweight Charts 顯示 K 線圖與技術指標
3. WHEN 使用者開啟儀表板，THE HUD_Dashboard SHALL 顯示即時更新的 BTC/TWD 價格與 24 小時漲跌幅
4. THE HUD_Dashboard SHALL 顯示即時的 Fear & Greed Index 儀表盤（0-100 色階量表）
5. THE HUD_Dashboard SHALL 顯示使用者投資組合的幣種分佈與損益概覽
6. WHEN 系統產生交易建議，THE HUD_Dashboard SHALL 渲染 Trade_Confirmation_Card 供使用者審閱與授權
7. WHEN 使用者點擊 Trade_Confirmation_Card 的確認按鈕，THE HUD_Dashboard SHALL 將授權訊號傳送至後端觸發 Hermes 執行
8. THE HUD_Dashboard SHALL 以流式方式顯示 Agent 的思考過程（Chain-of-Thought 串流）
9. THE HUD_Dashboard SHALL 符合 WCAG 2.1 AA 級無障礙標準

### 需求 10：WebSocket 即時串流通訊

**使用者故事：** 身為投資者，我希望系統回應能以即時串流方式呈現，包括 Agent 的思考過程，以便我能即時追蹤分析進度而非等待完整回覆。

#### 驗收條件

1. THE System SHALL 透過 WebSocket 連線提供即時串流回應給前端
2. WHEN Agent 開始執行分析，THE System SHALL 透過 WebSocket 推送該 Agent 的啟動狀態通知
3. WHEN Agent 產生中間思考過程，THE System SHALL 以 token-by-token 串流方式推送至前端
4. WHEN 所有 Agent 完成分析，THE System SHALL 透過 WebSocket 推送最終彙整回覆
5. IF WebSocket 連線中斷，THEN THE System SHALL 支援重新連線機制並恢復最近的對話上下文
6. THE System SHALL 支援多個同時連線的使用者，每個使用者擁有獨立的對話 Session

### 需求 11：MAX API 整合與 HMAC-SHA256 認證

**使用者故事：** 身為投資者，我希望系統能安全地連接我的 MAX 交易所帳戶，以便讀取帳戶資訊並執行交易。

#### 驗收條件

1. THE MAX_API_Client SHALL 使用 HMAC-SHA256 簽章機制進行 Private API 認證
2. THE MAX_API_Client SHALL 依序執行：組裝參數（含 nonce）→ 加入 path → Base64 編碼 → HMAC-SHA256 簽章 → 設定 X-MAX-ACCESSKEY、X-MAX-PAYLOAD、X-MAX-SIGNATURE 標頭
3. THE MAX_API_Client SHALL 使用毫秒級時間戳作為 nonce 確保請求唯一性
4. WHEN 呼叫 Public API，THE MAX_API_Client SHALL 不附帶認證標頭直接發送請求
5. WHEN 呼叫 Private API，THE MAX_API_Client SHALL 自動附帶認證標頭
6. IF MAX_API 回傳 HTTP 4xx/5xx 狀態碼，THEN THE MAX_API_Client SHALL 拋出 MaxAPIError 包含 status_code、error code 與 message
7. THE MAX_API_Client SHALL 設定 30 秒的請求逾時上限
8. FOR ALL 認證請求，簽章計算後驗證 SHALL 能重現相同的 payload 與 signature（round-trip 屬性）

### 需求 12：LangGraph 多 Agent 工作流程編排

**使用者故事：** 身為系統開發者，我希望六個 Agent 的協作流程以可靠的狀態機方式編排，以確保正確的執行順序、平行分析與條件式路由。

#### 驗收條件

1. THE LangGraph_Workflow SHALL 以 OmniVerseState 作為所有節點間共享的狀態物件
2. THE LangGraph_Workflow SHALL 依序執行：Zeus 意圖解析 → 專家 Agent 平行分析 → 條件式風控評估 → 條件式交易執行 → Zeus 結果彙整
3. WHEN Zeus 指定多個 required_agents，THE LangGraph_Workflow SHALL 以平行方式執行這些 Agent 節點
4. WHEN trade_intent 存在於 State 中，THE LangGraph_Workflow SHALL 路由至 Themis 風控評估節點
5. WHEN trade_intent 不存在，THE LangGraph_Workflow SHALL 跳過 Themis 與 Hermes 直接路由至 Zeus 彙整節點
6. WHEN Themis 核准交易（trade_approved 為 True），THE LangGraph_Workflow SHALL 路由至 Hermes 執行節點
7. WHEN Themis 否決交易，THE LangGraph_Workflow SHALL 跳過 Hermes 直接路由至 Zeus 彙整節點
8. THE LangGraph_Workflow SHALL 確保 Hermes 節點只可從 Themis 核准路徑到達，不存在繞過風控的路由

### 需求 13：AWS 雲端無伺服器架構

**使用者故事：** 身為系統架構師，我希望系統採用 AWS 雲端原生無伺服器架構，以實現彈性擴展、按需付費並降低營運負擔。

#### 驗收條件

1. THE System SHALL 使用 AWS Lambda 或 AWS Fargate 作為後端運算層
2. THE System SHALL 使用 Amazon API Gateway 作為 REST/WebSocket API 閘道
3. THE System SHALL 使用 Amazon Bedrock（Claude 3.5 Sonnet）作為 LLM 推理引擎
4. THE System SHALL 使用 Amazon Bedrock Knowledge Bases 搭配 OpenSearch Serverless 作為 RAG 向量知識庫
5. THE System SHALL 使用 Amazon DynamoDB 儲存 Session 與風控策略資料
6. THE System SHALL 使用 AWS Secrets Manager 儲存 API Key 與 Secret
7. WHEN 系統負載增加，THE AWS_Infrastructure SHALL 自動擴展運算資源而無需人工介入
8. THE System SHALL 採用 Infrastructure as Code（AWS CDK 或 SAM）管理所有雲端資源

### 需求 14：安全性與權限控制

**使用者故事：** 身為投資者，我希望系統嚴格控制各 Agent 的權限範圍，確保我的 API 金鑰與資產安全，防止未授權的交易執行。

#### 驗收條件

1. THE System SHALL 將 MAX API Key 與 Secret 儲存於 AWS Secrets Manager，並設定自動旋轉機制
2. THE System SHALL 以 IAM 最小權限原則分配各 Agent 的存取權限
3. THE System SHALL 確保僅 Hermes 可存取交易憑證（MAX API Key with trade permission）
4. THE System SHALL 確保 Stark、Minerva、Morpheus 僅能存取唯讀 API 端點
5. WHEN Hermes 執行交易前，THE System SHALL 驗證 trade_approved 旗標與 risk_verdict.approved 雙重條件
6. THE System SHALL 於 DynamoDB 記錄所有交易嘗試（含成功與失敗）供稽核追蹤
7. IF 偵測到異常交易模式（超過頻率限制或金額上限），THEN THE System SHALL 自動暫停交易功能並發送告警
8. THE System SHALL 確保使用者 CSV 資料在傳輸與儲存過程中均加密處理

### 需求 15：MAX MCP Server 與 MAX Skill 整合

**使用者故事：** 身為投資者，我希望系統能同時利用 MAX MCP Server（工具式）與 MAX Skill（知識型）兩種 API 存取方式，以最大化對 MAX 交易所的功能覆蓋。

#### 驗收條件

1. THE System SHALL 整合 MAX MCP Server（bistin/max-mcp-server）作為 MCP 工具式 API 存取管道
2. THE System SHALL 整合 MAX API Skill（bistin/max-api-skill）作為 Agent 知識型 API 文件參考
3. WHEN Hermes 執行交易，THE Hermes SHALL 優先透過 MAX MCP Server 的工具介面下單
4. IF MAX MCP Server 不可用，THEN THE Hermes SHALL 退回至直接 REST API 呼叫作為備援
5. THE System SHALL 利用 MAX API Skill 文件增強 Agent 對 MAX API 能力與限制的理解
6. WHEN Agent 查詢 MAX API 功能，THE System SHALL 從 MAX API Skill 知識庫中檢索相關文件

### 需求 16：對話 Session 管理

**使用者故事：** 身為投資者，我希望系統能記住我在同一對話中的上下文，以便進行多輪對話式的投資諮詢。

#### 驗收條件

1. THE System SHALL 使用 DynamoDB 儲存每個使用者的對話 Session 狀態
2. WHEN 使用者發送新訊息，THE System SHALL 載入該使用者最近的對話歷史作為上下文
3. THE OmniVerseState SHALL 透過 LangGraph 的 add_messages 機制累積對話訊息列表
4. WHEN 對話超過上下文長度限制，THE System SHALL 執行摘要壓縮保留關鍵資訊
5. IF 使用者開始新的對話 Session，THEN THE System SHALL 初始化全新的 OmniVerseState
6. THE System SHALL 為每個 Session 設定逾時機制（閒置超過 30 分鐘自動結束）

### 需求 17：系統效能與可靠性

**使用者故事：** 身為投資者，我希望系統能快速回應我的查詢，在交易時段提供低延遲服務，確保不會因系統延遲而錯失交易機會。

#### 驗收條件

1. WHEN 使用者發送非交易類查詢，THE System SHALL 在 5 秒內開始串流回覆
2. WHEN 使用者發送交易類指令，THE System SHALL 在 3 秒內完成風控評估
3. THE MAX_API_Client SHALL 在 30 秒內完成單次 API 呼叫，否則回傳逾時錯誤
4. THE System SHALL 支援至少 50 個同時連線的使用者而不降低效能
5. IF Amazon Bedrock 服務暫時不可用，THEN THE System SHALL 回傳友善的服務暫時中斷訊息，並在服務恢復後自動重連
6. THE System SHALL 為所有外部 API 呼叫實作指數退避（exponential backoff）重試機制，最多重試 3 次

### 需求 18：競賽評分項目對照與展示功能

**使用者故事：** 身為競賽參與者，我希望系統的設計完整對應競賽評分標準，並能在 Live Demo 中有效展示各項創新亮點。

#### 驗收條件

1. THE System SHALL 提供多 Agent 動態會診視覺化 HUD，對應創意度評分項目（25%）
2. THE System SHALL 基於 AWS 原生 Serverless 架構部署，對應技術可行性評分項目（20%）
3. THE System SHALL 實現從分析到下單的完整閉環流程，對應商業應用性評分項目（20%）
4. THE System SHALL 實現 Multi-Agent 協作搭配 RAG 與 Guardrails 架構，對應 AI 設計評分項目（15%）
5. THE System SHALL 完整整合 MAX API、MAX MCP Server、MAX Skill 與 CSV 數據，對應主題切合度評分項目（10%）
6. THE System SHALL 提供可運行的 Live Demo 與 GitHub 開源程式碼，對應完成度評分項目（10%）
7. THE System SHALL 支援透過 Private API 執行實際交易，對應加分項目（+10%）
8. THE System SHALL 使用 Kiro IDE 進行開發，對應加分項目（+10%）

### 需求 19：設定管理與環境變數

**使用者故事：** 身為系統開發者，我希望系統設定以環境變數方式管理，支援本地開發與雲端部署的無縫切換。

#### 驗收條件

1. THE System SHALL 使用 pydantic-settings 從 .env 檔案或環境變數載入所有設定
2. THE System SHALL 定義以下必要設定項：AWS_REGION、BEDROCK_MODEL_ID、MAX_API_KEY、MAX_API_SECRET、MAX_API_BASE_URL、MAX_ENABLE_TRADING
3. THE System SHALL 定義以下選用設定項：COINMARKETCAP_API_KEY、BLOCKCHAIN_COM_API_KEY、OPENSEARCH_ENDPOINT、CSV_DATA_PATH
4. WHEN MAX_ENABLE_TRADING 未設定或設為 False，THE System SHALL 禁止所有交易寫入操作
5. THE System SHALL 提供 .env.example 檔案列出所有設定項及其預設值說明
6. IF 必要設定項缺失，THEN THE System SHALL 在啟動時以明確的錯誤訊息提示缺失的設定項

### 需求 20：錯誤處理與日誌記錄

**使用者故事：** 身為系統開發者，我希望系統具備完善的錯誤處理與日誌記錄機制，以便快速定位問題並確保系統穩定性。

#### 驗收條件

1. WHEN 任何 Agent 執行過程中發生未預期例外，THE System SHALL 捕獲該例外並回傳結構化的 AgentReport（含錯誤摘要與 confidence=0.0）
2. THE System SHALL 為每次 API 呼叫記錄請求路徑、回應狀態碼與回應時間
3. WHEN MAX_API 回傳非 2xx 狀態碼，THE MAX_API_Client SHALL 解析回應 body 中的 error.code 與 error.message 欄位
4. THE System SHALL 使用結構化日誌格式（JSON）記錄所有 Agent 的執行事件
5. IF LLM 回覆無法解析為預期的 JSON 格式，THEN THE Zeus SHALL 使用備援解析策略（退回保守路由）而非拋出例外
6. THE System SHALL 為每次完整的使用者請求產生唯一的 correlation_id 用於跨 Agent 追蹤

## 競賽評分對照表

| 評分項目 (佔比) | 對應需求 | 說明 |
|---------------|---------|------|
| 創意度 (25%) | 需求 9, 10 | 多 Agent 動態會診視覺化 HUD + 即時串流 |
| 技術可行性 (20%) | 需求 13 | AWS 原生 Serverless 架構 |
| 商業應用性 (20%) | 需求 7, 9（AC6-7） | 閉環下單 + 一鍵確認降低交易障礙 |
| AI 設計 (15%) | 需求 1, 4, 5, 8, 12 | Multi-Agent + RAG + Guardrails |
| 主題切合度 (10%) | 需求 2, 11, 15 | MAX API/MCP/Skill/CSV 完整整合 |
| 完成度 (10%) | 需求 18 | Live Demo + GitHub |
| 加分項 (+10%) | 需求 7, 18（AC7-8） | 實際交易 + Kiro IDE |
