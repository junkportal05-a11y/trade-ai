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

const BASE_URL = `http://${window.location.hostname}:8000`;
const WS_URL   = `ws://${window.location.hostname}:8000`;

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
          // Fallback: generate synthetic OHLCV so the chart still renders
          setBars(generateFallbackBars(90, seedPrice));
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

    function startFallback() {
      if (fallbackTimer.current) return; // already running
      fallbackTimer.current = setInterval(() => {
        setPrices(prev => {
          const next = { ...prev };
          const marketOpen = isNSEMarketOpen();
          symbols.forEach(sym => {
            const seedPrice = SEED_PRICES[sym] || 150;
            const last = (prev[sym]?.price) || seedRef.current[sym] || seedPrice;
            const newPrice = marketOpen ? simulateTick(last) : last;
            seedRef.current[sym] = newPrice;
            
            // Fix: stable prevClose so changePct fluctuates realistically
            const prevClose = prev[sym]?.prevClose || seedPrice;
            const change    = newPrice - prevClose;
            const changePct = (change / prevClose) * 100;
            
            next[sym] = { price: newPrice, prevClose, change, changePct, timestamp: Date.now() };
          });
          return next;
        });
      }, 1000);
    }

    function stopFallback() {
      if (fallbackTimer.current) {
        clearInterval(fallbackTimer.current);
        fallbackTimer.current = null;
      }
    }

    function connect() {
      try {
        const ws = new WebSocket(`${WS_URL}/ws/prices?symbols=${symbolKey}`);
        wsRef.current = ws;

        ws.onopen = () => {
          if (!isMounted) return;
          setConnected(true);
          stopFallback();
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
          startFallback();
        };

        ws.onclose = () => {
          if (!isMounted) return;
          setConnected(false);
          startFallback();
          // Reconnect after 5 s
          reconnectTimeout = setTimeout(() => {
            if (isMounted) connect();
          }, 5000);
        };
      } catch (_) {
        setConnected(false);
        startFallback();
      }
    }

    connect();

    return () => {
      isMounted = false;
      stopFallback();
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

function simulateTick(last) {
  return Math.max(0.01, last * (1 + (Math.random() - 0.5) * 0.002));
}

function generateFallbackBars(days = 90, startPrice = 150) {
  const bars = [];
  let price = startPrice;
  const now  = Date.now();

  for (let i = days; i >= 0; i--) {
    const d    = new Date(now - i * 86_400_000);
    const open = price;
    const move = (Math.random() - 0.48) * (price * 0.02); // 2% daily moves max
    const close = Math.max(1, open + move);
    const high  = Math.max(open, close) + Math.random() * (price * 0.01);
    const low   = Math.min(open, close) - Math.random() * (price * 0.01);
    bars.push({
      time:   d.toISOString().slice(0, 10),
      open:   +open.toFixed(2),
      high:   +high.toFixed(2),
      low:    +low.toFixed(2),
      close:  +close.toFixed(2),
      volume: Math.floor(5_000_000 + Math.random() * 20_000_000),
    });
    price = close;
  }
  return bars;
}

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