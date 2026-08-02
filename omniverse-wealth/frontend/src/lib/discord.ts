/**
 * Discord Webhook notification module.
 *
 * Uses Python subprocess for sending (Node.js https has ECONNRESET issues
 * in this Windows environment, but Python httpx works fine).
 */
import { execSync } from "child_process";
import { resolve } from "path";

interface AlertEmbed {
  currency: string;
  changePct: number;
  direction: "up" | "down";
  currentPrice: number;
  avgBuyPrice: number;
  action?: string;
  volume?: string;
}

/**
 * Send a volatility alert notification to Discord.
 */
export async function sendDiscordAlert(alerts: AlertEmbed[]): Promise<boolean> {
  const payload = {
    embeds: [{
      title: "⚠️ OmniVerse Wealth — 波動警報",
      color: 0xff4444,
      description: `偵測到 ${alerts.length} 個持倉幣種超過 10% 波動`,
      fields: alerts.map((a) => ({
        name: `${a.direction === "down" ? "🔴" : "🟢"} ${a.currency}`,
        value: [
          `24H 變化: **${a.direction === "down" ? "" : "+"}${a.changePct}%**`,
          `現價: ${a.currentPrice.toLocaleString()} TWD`,
          `均買價: ${a.avgBuyPrice.toFixed(0)} TWD`,
          a.action ? `⚡ **自動調倉**: 賣出 ${a.volume} (20% 持倉)` : "",
        ].filter(Boolean).join("\n"),
        inline: true,
      })),
      footer: { text: "OmniVerse Wealth Multi-Agent System" },
      timestamp: new Date().toISOString(),
    }],
  };

  return callPythonNotifier(payload);
}

/**
 * Send auto-rebalance execution result to Discord.
 */
export async function sendDiscordTradeResult(
  currency: string,
  side: string,
  volume: string,
  success: boolean,
  message: string,
): Promise<boolean> {
  const payload = {
    embeds: [{
      title: success ? "✅ 自動調倉執行成功" : "❌ 自動調倉執行失敗",
      color: success ? 0x10b981 : 0xff4444,
      fields: [
        { name: "幣種", value: currency, inline: true },
        { name: "方向", value: side === "sell" ? "賣出" : "買入", inline: true },
        { name: "數量", value: volume, inline: true },
        { name: "結果", value: message, inline: false },
      ],
      footer: { text: "OmniVerse Wealth Auto-Rebalancer" },
      timestamp: new Date().toISOString(),
    }],
  };

  return callPythonNotifier(payload);
}

/**
 * Call Python script to send Discord webhook (bypasses Node.js https issues).
 */
function callPythonNotifier(payload: any): boolean {
  try {
    const scriptPath = resolve(process.cwd(), "../src/notify_discord.py");
    const pythonPath = resolve(process.cwd(), "../.venv/Scripts/python.exe");
    const jsonArg = JSON.stringify(payload).replace(/"/g, '\\"');

    execSync(`"${pythonPath}" "${scriptPath}" "${jsonArg}"`, {
      timeout: 10000,
      encoding: "utf-8",
    });

    return true;
  } catch (e) {
    console.error("[Discord] Notification failed:", e);
    return false;
  }
}
