"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export type WSStatus = "connecting" | "connected" | "disconnected" | "error";

/**
 * WebSocket message following the API spec:
 * { event, data, timestamp?, requestId? }
 */
export interface WSMessage {
  event: string;
  data: any;
  timestamp?: number;
  requestId?: string;
}

interface UseWebSocketOptions {
  url: string;
  token?: string;
  autoConnect?: boolean;
  onMessage?: (msg: WSMessage) => void;
  onTickerUpdate?: (tickers: Record<string, any>) => void;
  onAgentThinking?: (data: { agent: string; status: string; thought?: string }) => void;
  onAgentResponse?: (data: { message: string; agents_completed: string[] }) => void;
}

interface UseWebSocketReturn {
  status: WSStatus;
  connect: () => void;
  disconnect: () => void;
  subscribe: (channel: string) => void;
  unsubscribe: (channel: string) => void;
  sendQuery: (message: string) => void;
  lastTickers: Record<string, any>;
}

/**
 * WebSocket hook following the project's WSS API specification.
 *
 * Features:
 * - JWT auth via query param
 * - 30s ping/pong heartbeat
 * - Exponential backoff reconnection (1s → 2s → 4s → ... → 30s max)
 * - Channel subscription
 * - Typed event dispatch (ticker_update, agent_thinking, agent_response)
 */
export function useWebSocket({
  url,
  token = "",
  autoConnect = true,
  onMessage,
  onTickerUpdate,
  onAgentThinking,
  onAgentResponse,
}: UseWebSocketOptions): UseWebSocketReturn {
  const [status, setStatus] = useState<WSStatus>("disconnected");
  const [lastTickers, setLastTickers] = useState<Record<string, any>>({});
  const wsRef = useRef<WebSocket | null>(null);
  const pingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectCountRef = useRef(0);
  const reconnectTimerRef = useRef<NodeJS.Timeout | null>(null);
  const maxReconnect = 10;

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    setStatus("connecting");

    const fullUrl = token ? `${url}?token=${token}` : url;

    try {
      const ws = new WebSocket(fullUrl);

      ws.onopen = () => {
        setStatus("connected");
        reconnectCountRef.current = 0;

        // Start 30s heartbeat
        pingIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ event: "ping" }));
          }
        }, 30000);
      };

      ws.onmessage = (event) => {
        try {
          const msg: WSMessage = JSON.parse(event.data);
          onMessage?.(msg);

          // Dispatch by event type
          switch (msg.event) {
            case "pong":
              // Heartbeat acknowledged
              break;
            case "ticker_update":
              setLastTickers(msg.data);
              onTickerUpdate?.(msg.data);
              break;
            case "agent_thinking":
              onAgentThinking?.(msg.data);
              break;
            case "agent_response":
              onAgentResponse?.(msg.data);
              break;
            case "error":
              console.error("[WS Error]", msg.data?.message);
              break;
          }
        } catch {
          // Non-JSON message, ignore
        }
      };

      ws.onclose = () => {
        setStatus("disconnected");
        wsRef.current = null;
        if (pingIntervalRef.current) clearInterval(pingIntervalRef.current);

        // Exponential backoff reconnection
        if (reconnectCountRef.current < maxReconnect) {
          const delay = Math.min(
            1000 * Math.pow(2, reconnectCountRef.current),
            30000
          );
          reconnectTimerRef.current = setTimeout(() => {
            reconnectCountRef.current++;
            connect();
          }, delay);
        }
      };

      ws.onerror = () => {
        setStatus("error");
      };

      wsRef.current = ws;
    } catch {
      setStatus("error");
    }
  }, [url, token, onMessage, onTickerUpdate, onAgentThinking, onAgentResponse]);

  const disconnect = useCallback(() => {
    if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
    if (pingIntervalRef.current) clearInterval(pingIntervalRef.current);
    reconnectCountRef.current = maxReconnect; // Prevent reconnect
    wsRef.current?.close(1000);
    wsRef.current = null;
    setStatus("disconnected");
  }, []);

  const subscribe = useCallback((channel: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          event: "subscribe",
          data: { channel },
          requestId: `sub_${Date.now()}`,
        })
      );
    }
  }, []);

  const unsubscribe = useCallback((channel: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          event: "unsubscribe",
          data: { channel },
          requestId: `unsub_${Date.now()}`,
        })
      );
    }
  }, []);

  const sendQuery = useCallback((message: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          event: "query",
          data: { message },
          timestamp: Date.now(),
          requestId: `q_${Date.now()}`,
        })
      );
    }
  }, []);

  useEffect(() => {
    if (autoConnect && url) {
      connect();
    }
    return () => {
      disconnect();
    };
  }, []);

  return { status, connect, disconnect, subscribe, unsubscribe, sendQuery, lastTickers };
}
