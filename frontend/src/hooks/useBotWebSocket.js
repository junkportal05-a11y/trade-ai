import { useState, useEffect, useRef } from "react";
import { WS_BASE_URL } from "../api";
import { buildWsUrl } from "../utils/wsUrl";

const WS_URL = WS_BASE_URL;
export const BOT_WS_PATH = '/ws/bot';
export const AUTH_CLOSE_CODES = [4001, 1008];
const RECONNECT_BASE_MS = 3000;
const RECONNECT_MAX_MS = 30000;

export function buildBotWsUrl(baseUrl) {
  return buildWsUrl(baseUrl, BOT_WS_PATH);
}

export function shouldReconnect(code) {
  return !AUTH_CLOSE_CODES.includes(code);
}

export function getReconnectDelay(attempt) {
  return Math.min(RECONNECT_BASE_MS * (2 ** attempt), RECONNECT_MAX_MS);
}

export function useBotWebSocket() {
  const [botData, setBotData] = useState({
    status: { state: "stopped", today_pnl: 0, positions: [], last_signal: null },
    trades: []
  });
  const [connected, setConnected] = useState(false);
  const wsRef = useRef(null);

  useEffect(() => {
    let reconnectTimeout = null;
    let reconnectAttempt = 0;
    let isMounted = true;

    function connect() {
      try {
        const ws = new WebSocket(buildBotWsUrl(WS_URL));
        wsRef.current = ws;

        ws.onopen = () => {
          if (!isMounted) return;
          reconnectAttempt = 0;
          setConnected(true);
        };

        ws.onmessage = (event) => {
          if (!isMounted) return;
          try {
            const msg = JSON.parse(event.data);
            if (msg.type === "bot_update") {
              setBotData({
                status: msg.status,
                trades: msg.trades
              });
            }
          } catch {
            return;
          }
        };

        ws.onerror = () => {
          if (!isMounted) return;
          setConnected(false);
        };

        ws.onclose = (event) => {
          if (!isMounted) return;
          setConnected(false);
          if (!shouldReconnect(event.code)) return;

          const delay = getReconnectDelay(reconnectAttempt);
          reconnectAttempt += 1;
          reconnectTimeout = setTimeout(() => {
            if (isMounted) connect();
          }, delay);
        };
      } catch {
        if (!isMounted) return;
        setConnected(false);
        const delay = getReconnectDelay(reconnectAttempt);
        reconnectAttempt += 1;
        reconnectTimeout = setTimeout(() => {
          if (isMounted) connect();
        }, delay);
      }
    }

    connect();

    return () => {
      isMounted = false;
      clearTimeout(reconnectTimeout);
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
      }
    };
  }, []);

  return { botData, connected };
}
