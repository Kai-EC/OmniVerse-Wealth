/**
 * Technical Indicators Calculator.
 *
 * Computes from raw K-line data (OHLCV):
 * - RSI (14-period)
 * - SMA (7, 25, 99)
 * - EMA (12, 26)
 * - MACD (12, 26, 9)
 * - Bollinger Bands (20, 2σ)
 * - ATR (14-period)
 * - Volume trend
 */

export interface KlineRaw {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface TechnicalAnalysis {
  rsi14: number;
  sma7: number;
  sma25: number;
  sma99: number;
  ema12: number;
  ema26: number;
  macd: number;
  macdSignal: number;
  macdHistogram: number;
  bollingerUpper: number;
  bollingerMiddle: number;
  bollingerLower: number;
  atr14: number;
  volumeAvg: number;
  volumeLatest: number;
  volumeTrend: "increasing" | "decreasing" | "stable";
  pricePosition: string; // relative to bollinger bands
  trend: string;
  summary: string;
}

/**
 * Calculate all technical indicators from K-line data.
 */
export function calculateIndicators(klines: KlineRaw[]): TechnicalAnalysis | null {
  if (klines.length < 30) return null;

  const closes = klines.map((k) => k.close);
  const highs = klines.map((k) => k.high);
  const lows = klines.map((k) => k.low);
  const volumes = klines.map((k) => k.volume);

  // RSI (14)
  const rsi14 = calcRSI(closes, 14);

  // SMA
  const sma7 = calcSMA(closes, 7);
  const sma25 = calcSMA(closes, 25);
  const sma99 = klines.length >= 99 ? calcSMA(closes, 99) : sma25;

  // EMA
  const ema12 = calcEMA(closes, 12);
  const ema26 = calcEMA(closes, 26);

  // MACD
  const macdLine = ema12 - ema26;
  const ema12All = calcEMAArray(closes, 12);
  const ema26All = calcEMAArray(closes, 26);
  const macdArray = ema12All.map((v, i) => v - ema26All[i]);
  const macdSignal = calcEMA(macdArray.slice(-26), 9);
  const macdHistogram = macdLine - macdSignal;

  // Bollinger Bands (20, 2σ)
  const bb = calcBollinger(closes, 20, 2);

  // ATR (14)
  const atr14 = calcATR(highs, lows, closes, 14);

  // Volume analysis
  const volumeAvg = calcSMA(volumes, 14);
  const volumeLatest = volumes[volumes.length - 1];
  const volumeRecent = calcSMA(volumes.slice(-5), 5);
  const volumeOlder = calcSMA(volumes.slice(-14, -5), 9);
  const volumeTrend: "increasing" | "decreasing" | "stable" =
    volumeRecent > volumeOlder * 1.2 ? "increasing" :
    volumeRecent < volumeOlder * 0.8 ? "decreasing" : "stable";

  // Price position relative to Bollinger
  const lastClose = closes[closes.length - 1];
  let pricePosition: string;
  if (lastClose > bb.upper) pricePosition = "超買區（高於布林上軌）";
  else if (lastClose > bb.middle) pricePosition = "偏多區（中軌與上軌之間）";
  else if (lastClose > bb.lower) pricePosition = "偏空區（中軌與下軌之間）";
  else pricePosition = "超賣區（低於布林下軌）";

  // Trend determination
  let trend: string;
  if (sma7 > sma25 && lastClose > sma7) trend = "短期上升趨勢";
  else if (sma7 < sma25 && lastClose < sma7) trend = "短期下降趨勢";
  else if (Math.abs(sma7 - sma25) / sma25 < 0.005) trend = "盤整震盪";
  else trend = "方向不明，觀望";

  // Summary
  const signals: string[] = [];
  if (rsi14 < 30) signals.push("RSI 超賣");
  else if (rsi14 > 70) signals.push("RSI 超買");
  if (macdHistogram > 0 && macdLine > 0) signals.push("MACD 多頭");
  else if (macdHistogram < 0 && macdLine < 0) signals.push("MACD 空頭");
  if (lastClose < bb.lower) signals.push("觸及布林下軌(超賣)");
  else if (lastClose > bb.upper) signals.push("觸及布林上軌(超買)");

  const summary = signals.length > 0
    ? `技術訊號: ${signals.join("、")}`
    : "技術面中性，無明確訊號";

  return {
    rsi14: round(rsi14),
    sma7: round(sma7),
    sma25: round(sma25),
    sma99: round(sma99),
    ema12: round(ema12),
    ema26: round(ema26),
    macd: round(macdLine),
    macdSignal: round(macdSignal),
    macdHistogram: round(macdHistogram),
    bollingerUpper: round(bb.upper),
    bollingerMiddle: round(bb.middle),
    bollingerLower: round(bb.lower),
    atr14: round(atr14),
    volumeAvg: round(volumeAvg, 4),
    volumeLatest: round(volumeLatest, 4),
    volumeTrend,
    pricePosition,
    trend,
    summary,
  };
}

/**
 * Format indicators into text for LLM prompt injection.
 */
export function formatIndicatorsForPrompt(
  market: string,
  indicators: TechnicalAnalysis
): string {
  const symbol = market.replace("twd", "").toUpperCase();
  return `## ${symbol}/TWD 技術指標 (1H K線)
趨勢判斷: ${indicators.trend}
${indicators.summary}

RSI(14): ${indicators.rsi14} ${indicators.rsi14 < 30 ? "⚠️超賣" : indicators.rsi14 > 70 ? "⚠️超買" : "(中性)"}
MA(7): ${indicators.sma7.toLocaleString()} | MA(25): ${indicators.sma25.toLocaleString()} | MA(99): ${indicators.sma99.toLocaleString()}
MACD: ${indicators.macd.toFixed(0)} | Signal: ${indicators.macdSignal.toFixed(0)} | Histogram: ${indicators.macdHistogram > 0 ? "+" : ""}${indicators.macdHistogram.toFixed(0)}
布林帶: 上軌=${indicators.bollingerUpper.toLocaleString()} | 中軌=${indicators.bollingerMiddle.toLocaleString()} | 下軌=${indicators.bollingerLower.toLocaleString()}
價格位置: ${indicators.pricePosition}
ATR(14): ${indicators.atr14.toLocaleString()} (波動度)
成交量趨勢: ${indicators.volumeTrend === "increasing" ? "放大📈" : indicators.volumeTrend === "decreasing" ? "萎縮📉" : "持平"}`;
}

// ─── Internal Calculation Functions ────────────────────────────────────────

function calcRSI(prices: number[], period: number): number {
  if (prices.length < period + 1) return 50;

  let gains = 0, losses = 0;
  for (let i = prices.length - period; i < prices.length; i++) {
    const diff = prices[i] - prices[i - 1];
    if (diff > 0) gains += diff;
    else losses += Math.abs(diff);
  }

  const avgGain = gains / period;
  const avgLoss = losses / period;

  if (avgLoss === 0) return 100;
  const rs = avgGain / avgLoss;
  return 100 - (100 / (1 + rs));
}

function calcSMA(values: number[], period: number): number {
  const slice = values.slice(-period);
  return slice.reduce((a, b) => a + b, 0) / slice.length;
}

function calcEMA(values: number[], period: number): number {
  const arr = calcEMAArray(values, period);
  return arr[arr.length - 1];
}

function calcEMAArray(values: number[], period: number): number[] {
  const k = 2 / (period + 1);
  const ema: number[] = [values[0]];
  for (let i = 1; i < values.length; i++) {
    ema.push(values[i] * k + ema[i - 1] * (1 - k));
  }
  return ema;
}

function calcBollinger(prices: number[], period: number, stdMult: number) {
  const slice = prices.slice(-period);
  const middle = slice.reduce((a, b) => a + b, 0) / slice.length;
  const variance = slice.reduce((sum, p) => sum + (p - middle) ** 2, 0) / slice.length;
  const std = Math.sqrt(variance);
  return {
    upper: middle + std * stdMult,
    middle,
    lower: middle - std * stdMult,
  };
}

function calcATR(highs: number[], lows: number[], closes: number[], period: number): number {
  const trueRanges: number[] = [];
  for (let i = 1; i < highs.length; i++) {
    const tr = Math.max(
      highs[i] - lows[i],
      Math.abs(highs[i] - closes[i - 1]),
      Math.abs(lows[i] - closes[i - 1])
    );
    trueRanges.push(tr);
  }
  return calcSMA(trueRanges, period);
}

function round(value: number, decimals = 1): number {
  return parseFloat(value.toFixed(decimals));
}
