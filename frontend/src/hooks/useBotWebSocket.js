import { useState, useEffect, useRef } from "react";
import { WS_BASE_URL } from "../api";

const WS_URL = WS_BASE_URL;
const WS_PATH = '/ws/bot';

export function useBotWebSocket() {
  const [botData, setBotData] = useState({
    status: { state: "stopped", today_pnl: 0, positions: [], last_signal: null },
    trades: []
  });
  const [connected, setConnected] = useState(false);
  const wsRef = useRef(null);

  useEffect(() => {
    let reconnectTimeout = null;
    let isMounted = true;

    function connect() {
      try {
        const ws = new WebSocket(`${WS_URL}${WS_PATH}`);
        wsRef.current = ws;

        ws.onopen = () => {
          if (!isMounted) return;
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
          } catch (_) { }
        };

        ws.onerror = () => {
          if (!isMounted) return;
          setConnected(false);
        };

        ws.onclose = () => {
          if (!isMounted) return;
          setConnected(false);
          // Reconnect after 3s
          reconnectTimeout = setTimeout(() => {
            if (isMounted) connect();
          }, 3000);
        };
      } catch (_) {
        setConnected(false);
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
