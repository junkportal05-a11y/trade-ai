import { useState, useEffect, useRef } from "react";
import { WS_BASE_URL } from "../api";

const WS_URL = WS_BASE_URL;
const WS_PATH = '/ws/bot';
const AUTH_CLOSE_CODES = new Set([4001, 1008]);
const INITIAL_RECONNECT_MS = 3000;
const MAX_RECONNECT_MS = 30000;

const getToken = () => {
  if (typeof window === "undefined") return "";
  return sessionStorage.getItem('apt_token') || localStorage.getItem('apt_token') || '';
};

export const buildBotWsUrl = (token) => {
  if (!token || !WS_URL) return null;
  return `${WS_URL}${WS_PATH}?token=${encodeURIComponent(token)}`;
};

export function useBotWebSocket() {
  const [botData, setBotData] = useState({
    status: { state: "stopped", today_pnl: 0, positions: [], last_signal: null },
    trades: []
  });
  const [connected, setConnected] = useState(false);
  const wsRef = useRef(null);

  useEffect(() => {
    let reconnectTimeout = null;
    let reconnectDelay = INITIAL_RECONNECT_MS;
    let isMounted = true;

    function scheduleReconnect() {
      if (!isMounted) return;
      reconnectTimeout = setTimeout(() => {
        reconnectDelay = Math.min(reconnectDelay * 2, MAX_RECONNECT_MS);
        connect();
      }, reconnectDelay);
    }

    function connect() {
      const url = buildBotWsUrl(getToken());
      if (!url) {
        setConnected(false);
        return;
      }

      try {
        const ws = new WebSocket(url);
        wsRef.current = ws;

        ws.onopen = () => {
          if (!isMounted) return;
          reconnectDelay = INITIAL_RECONNECT_MS;
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
          if (AUTH_CLOSE_CODES.has(event.code)) return;
          scheduleReconnect();
        };
      } catch {
        setConnected(false);
        scheduleReconnect();
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
