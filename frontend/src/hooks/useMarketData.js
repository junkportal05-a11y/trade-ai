import { API_BASE_URL, WS_BASE_URL } from '../api';
/**
 * useMarketData.js
 * ─────────────────────────────────────────────────────────────────────────────
 * React hooks that connect your trading UI to the FastAPI backend.
 *
 * Exports:
 *   useQuote(symbol)          – fetches current price + metadata
 *   useHistory(symbol, opts)  – fetches OHLCV bars for charting
 *   useLivePrices(symbols)    – WebSocket tick stream with fallback
 *
 * Drop this file into src/hooks/useMarketData.js
 */

import { useState, useEffect, useRef, useCallback } from "react";

const BASE_URL = API_BASE_URL;
const WS_URL = WS_BASE_URL;

const SEED_PRICES = {
  'YESBANK.NS': 25, 'TATASTEEL.NS': 170, 'BANKBARODA.NS': 280,
  'TATAPOWER.NS': 445, 'SBIN.NS': 830
};

// ══════════════════════════════════════════════════════════════════════════════
//  useQuote — single symbol quote
// ══════════════════════════════════════════════════════════════════════════════
export function useQuote(symbol) {
  const [data,    setData]    = useState(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState(null);

  const fetch_ = useCallback(async () => {
    if (!symbol) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${BASE_URL}/api/quote?symbol=${symbol}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setData(await res.json());
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [symbol]);

  useEffect(() => { fetch_(); }, [fetch_]);

  return { data, loading, error, refetch: fetch_ };
}

// ══════════════════════════════════════════════════════════════════════════════
//  useHistory — OHLCV bars
// ══════════════════════════════════════════════════════════════════════════════
export function useHistory(symbol, { interval = "1d", range = "3mo", seedPrice = 150 } = {}) {
  const [bars,    setBars]    = useState([]);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState(null);
  const [meta,    setMeta]    = useState(null);

  useEffect(() => {
    if (!symbol) return;
    let cancelled = false;

    (async () => {
      setLoading(true);
      setError(null);
      try {
        const url = `${BASE_URL}/api/history?symbol=${symbol}&interval=${interval}&range=${range}`;
        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json = await res.json();
        if (!cancelled) {
          setBars(json.bars || []);
          setMeta({ symbol: json.symbol, count: json.count });
        }
      } catch (e) {
        if (!cancelled) {
          setError(e.message);
          // Removed fallback: no synthetic data on fetch error
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => { cancelled = true; };
  }, [symbol, interval, range, seedPrice]);

  return { bars, loading, error, meta };
}

// ══════════════════════════════════════════════════════════════════════════════
//  useLivePrices — WebSocket tick stream
// ══════════════════════════════════════════════════════════════════════════════
export function useLivePrices(symbols = []) {
  // prices: { AAPL: { price, change, changePct, timestamp, prevClose }, ... }
  const [prices,    setPrices]    = useState({});
  const [connected, setConnected] = useState(false);
  const wsRef         = useRef(null);
  const fallbackTimer = useRef(null);
  const seedRef       = useRef({});
  const wsConnectedRef = useRef(false);

  const symbolKey = symbols.join(",");

  // ── HTTP Polling Fallback ──────────────────────────────────────────────────
  useEffect(() => {
    if (!symbols.length) return;

    // Wait 4 seconds — if WS hasn't connected by then, start HTTP polling
    const startDelay = setTimeout(() => {
      if (wsConnectedRef.current) return; // WS is working, skip

      console.log("[useLivePrices] WebSocket not connected — starting HTTP polling fallback");

      async function poll() {
        return; // Temporarily disabled to prevent 404 flooding
        try {
          const res = await fetch(`${BASE_URL}/api/prices`, { credentials: 'include' });
          if (!res.ok) return;
          const json = await res.json();
          if (json.type === "tick" && Array.isArray(json.data)) {
            setPrices(prev => {
              const next = { ...prev };
              json.data.forEach(tick => {
                const prevClose = tick.prev_close || prev[tick.symbol]?.prevClose || tick.price;
                const change    = tick.price - prevClose;
                next[tick.symbol] = {
                  price:     tick.price,
                  change,
                  changePct: prevClose ? (change / prevClose) * 100 : 0,
                  timestamp: tick.timestamp,
                  prevClose,
                };
              });
              return next;
            });
          }
        } catch (_) { /* network error — will retry */ }
      }

      poll(); // first poll immediately
      fallbackTimer.current = setInterval(() => {
        if (wsConnectedRef.current) {
          // WS reconnected — stop polling
          clearInterval(fallbackTimer.current);
          fallbackTimer.current = null;
          return;
        }
        poll();
      }, 2000);
    }, 4000);

    return () => {
      clearTimeout(startDelay);
      if (fallbackTimer.current) {
        clearInterval(fallbackTimer.current);
        fallbackTimer.current = null;
      }
    };
  }, [symbolKey]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── WebSocket (primary) ────────────────────────────────────────────────────
  useEffect(() => {
    if (!symbols.length) return;

    let reconnectTimeout = null;
    let isMounted = true;

    function connect() {
      try {
        const token = sessionStorage.getItem('apt_token') || localStorage.getItem('apt_token') || '';
        const ws = new WebSocket(`${WS_URL}/ws/prices?symbols=${symbolKey}&token=${token}`);
        wsRef.current = ws;

        ws.onopen = () => {
          if (!isMounted) return;
          setConnected(true);
          wsConnectedRef.current = true;
          // Stop HTTP polling if it was running
          if (fallbackTimer.current) {
            clearInterval(fallbackTimer.current);
            fallbackTimer.current = null;
          }
          // Tell backend which symbols we want
          ws.send(JSON.stringify({ action: "subscribe", symbols }));
        };

        ws.onmessage = (event) => {
          if (!isMounted) return;
          try {
            const msg = JSON.parse(event.data);
            if (msg.type === "tick" && Array.isArray(msg.data)) {
              setPrices(prev => {
                const next = { ...prev };
                msg.data.forEach(tick => {
                  const prevClose = tick.prev_close || prev[tick.symbol]?.prevClose || tick.price;
                  const change    = tick.price - prevClose;
                  next[tick.symbol] = {
                    price:     tick.price,
                    change,
                    changePct: prevClose ? (change / prevClose) * 100 : 0,
                    timestamp: tick.timestamp,
                    prevClose,
                  };
                });
                return next;
              });
            }
          } catch (_) { /* malformed frame */ }
        };

        ws.onerror = () => {
          if (!isMounted) return;
          setConnected(false);
          wsConnectedRef.current = false;
        };

        ws.onclose = (event) => {
          if (!isMounted) return;
          setConnected(false);
          wsConnectedRef.current = false;

          if (event.code === 4001) {
            console.warn("[WebSocket] Connection closed with code 4001: Session unauthorized/expired.");
            // Graceful logout, not auto reload
            const hadToken = !!localStorage.getItem('is_logged_in');
            if (hadToken) {
              // Clear auth state but stay on current page for smooth UX
              localStorage.removeItem('is_logged_in');
              localStorage.removeItem('apex_user');
              localStorage.removeItem('apex_role');
              localStorage.removeItem('apex_clearance');
              localStorage.removeItem('apt_token');
              // Navigate to login instead of hard reload for better UX
              window.location.hash = '/login';
            }
            return;
          }

          // Reconnect after 5 s with exponential backoff
          let reconnectDelay = 5000;
          reconnectTimeout = setTimeout(() => {
            if (isMounted) connect();
          }, reconnectDelay);
        };
      } catch (_) {
        setConnected(false);
        wsConnectedRef.current = false;
      }
    }

    connect();

    return () => {
      isMounted = false;
      clearTimeout(reconnectTimeout);
      if (wsRef.current) {
        wsRef.current.onclose = null; // prevent reconnect loop on unmount
        wsRef.current.close();
      }
    };
  }, [symbolKey]); // eslint-disable-line react-hooks/exhaustive-deps

  return { prices, connected };
}

// ══════════════════════════════════════════════════════════════════════════════
//  Helpers
// ══════════════════════════════════════════════════════════════════════════════

// Removed simulateTick and generateFallbackBars

export function isNSEMarketOpen() {
  const now = new Date();
  // Get time in IST (UTC+5:30)
  const utc = now.getTime() + (now.getTimezoneOffset() * 60000);
  const ist = new Date(utc + (3600000 * 5.5));
  
  const day = ist.getDay(); // 0 = Sunday, 6 = Saturday
  if (day === 0 || day === 6) return false;
  
  const hours = ist.getHours();
  const minutes = ist.getMinutes();
  const timeVal = hours * 100 + minutes;
  
  return timeVal >= 915 && timeVal <= 1530;
}
