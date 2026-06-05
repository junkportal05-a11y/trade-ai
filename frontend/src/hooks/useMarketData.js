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

const BASE_URL = import.meta.env.VITE_API_URL || `http://${window.location.hostname}:8000`;
const WS_URL   = import.meta.env.VITE_WS_URL || BASE_URL.replace(/^http/, 'ws');

const SEED_PRICES = {
  'RELIANCE.NS': 2920, 'TCS.NS': 4100, 'HDFCBANK.NS': 1780,
  'INFY.NS': 1650, 'ICICIBANK.NS': 1290, 'SBIN.NS': 845,
  'BAJFINANCE.NS': 7200, 'TMPV.NS': 385, 'WIPRO.NS': 490,
  'AXISBANK.NS': 1190,
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

  const symbolKey = symbols.join(",");

  useEffect(() => {
    if (!symbols.length) return;

    let reconnectTimeout = null;
    let isMounted = true;

    // Removed synthetic fallback simulation

    function connect() {
      try {
        const ws = new WebSocket(`${WS_URL}/ws/prices?symbols=${symbolKey}`);
        wsRef.current = ws;

        ws.onopen = () => {
          if (!isMounted) return;
          setConnected(true);
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
        };

        ws.onclose = () => {
          if (!isMounted) return;
          setConnected(false);
          // Reconnect after 5 s
          reconnectTimeout = setTimeout(() => {
            if (isMounted) connect();
          }, 5000);
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