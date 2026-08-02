/**
 * Server-side HTTPS helpers with retry, timeout, and keep-alive.
 *
 * Uses Node.js native `https` module with persistent Agent for connection reuse.
 * Includes automatic retry with exponential backoff.
 *
 * Optimized for Bedrock stability:
 * - TCP keep-alive enabled
 * - Connection reuse (persistent agent)
 * - Configurable retry with backoff
 * - Proper socket timeout handling
 */
import https from "https";
import http from "http";

const DEFAULT_TIMEOUT = 5000;
const MAX_RETRIES = 2;

// Persistent HTTPS agent with keep-alive for connection reuse
const keepAliveAgent = new https.Agent({
  keepAlive: true,
  keepAliveMsecs: 30000,
  maxSockets: 10,
  maxFreeSockets: 5,
  timeout: 60000,
});

/**
 * HTTPS GET with retry and timeout.
 */
export function httpsGet(url: string, timeoutMs = DEFAULT_TIMEOUT, retries = MAX_RETRIES): Promise<any> {
  return _withRetry(() => _doGet(url, timeoutMs), retries);
}

/**
 * HTTPS POST with retry and timeout.
 * For Bedrock calls: use retries=2, timeoutMs=40000
 */
export function httpsPost(
  url: string,
  body: any,
  headers: Record<string, string> = {},
  timeoutMs = 35000,
  retries = 2,
): Promise<{ status: number; data: any }> {
  return _withRetry(() => _doPost(url, body, headers, timeoutMs), retries);
}

// ─── Internal ──────────────────────────────────────────────────────────────

function _doGet(url: string, timeoutMs: number): Promise<any> {
  return new Promise((resolve, reject) => {
    const parsed = new URL(url);

    const options = {
      hostname: parsed.hostname,
      port: 443,
      path: parsed.pathname + parsed.search,
      method: "GET",
      agent: keepAliveAgent,
      timeout: timeoutMs,
    };

    const timer = setTimeout(() => {
      req.destroy();
      reject(new Error(`GET timeout (${timeoutMs}ms)`));
    }, timeoutMs);

    const req = https.get(options, (res) => {
      let data = "";
      res.on("data", (chunk) => (data += chunk));
      res.on("end", () => {
        clearTimeout(timer);
        try {
          resolve(JSON.parse(data));
        } catch {
          reject(new Error(`Invalid JSON`));
        }
      });
    });

    req.on("timeout", () => {
      req.destroy();
      clearTimeout(timer);
      reject(new Error(`Socket timeout (${timeoutMs}ms)`));
    });

    req.on("error", (err) => {
      clearTimeout(timer);
      reject(new Error(`GET: ${err.message}`));
    });
  });
}

function _doPost(
  url: string,
  body: any,
  headers: Record<string, string>,
  timeoutMs: number,
): Promise<{ status: number; data: any }> {
  return new Promise((resolve, reject) => {
    const parsed = new URL(url);
    const postData = JSON.stringify(body);

    const timer = setTimeout(() => {
      req.destroy();
      reject(new Error(`POST timeout (${timeoutMs}ms)`));
    }, timeoutMs);

    const options: https.RequestOptions = {
      hostname: parsed.hostname,
      port: 443,
      path: parsed.pathname + parsed.search,
      method: "POST",
      agent: keepAliveAgent,
      timeout: timeoutMs,
      headers: {
        "Content-Type": "application/json",
        "Content-Length": Buffer.byteLength(postData),
        "Connection": "keep-alive",
        ...headers,
      },
    };

    const req = https.request(options, (res) => {
      let data = "";
      res.on("data", (chunk) => (data += chunk));
      res.on("end", () => {
        clearTimeout(timer);
        try {
          resolve({ status: res.statusCode || 500, data: JSON.parse(data) });
        } catch {
          resolve({ status: res.statusCode || 500, data: { raw: data.slice(0, 300) } });
        }
      });
    });

    req.on("timeout", () => {
      req.destroy();
      clearTimeout(timer);
      reject(new Error(`Socket timeout (${timeoutMs}ms)`));
    });

    req.on("error", (err) => {
      clearTimeout(timer);
      reject(new Error(`POST: ${err.message}`));
    });

    req.write(postData);
    req.end();
  });
}

/**
 * Retry with exponential backoff.
 * Wait: 500ms, 1500ms, 3000ms between retries.
 */
async function _withRetry<T>(fn: () => Promise<T>, retries: number): Promise<T> {
  let lastError: Error | null = null;
  for (let i = 0; i <= retries; i++) {
    try {
      return await fn();
    } catch (e: any) {
      lastError = e;
      if (i < retries) {
        const delay = 500 * Math.pow(2, i); // 500ms, 1000ms, 2000ms
        await new Promise((r) => setTimeout(r, delay));
      }
    }
  }
  throw lastError;
}
