import React, { useState, useEffect, useRef, useCallback } from 'react';
import { createChart, CandlestickSeries, HistogramSeries, LineSeries } from 'lightweight-charts';
import { useHistory, useQuote, useLivePrices, isNSEMarketOpen } from './hooks/useMarketData';
import SignalsPanel from './SignalsPanel';
import PerformancePanel from './PerformancePanel';
import IntroSplash from './IntroSplash';
import LoginScreen from './LoginScreen';
import AccountPanel from './AccountPanel';



// ── Design tokens ─────────────────────────────────────────────────────────────
const T = {
  bg:         '#080a0f',
  surface:    '#0d1018',
  panel:      '#111520',
  panelAlt:   '#0f1219',
  border:     '#1a1f2e',
  borderHi:   '#252c40',
  text:       '#d0d8ed',
  textMid:    '#6e7a96',
  textDim:    '#363d55',
  green:      '#00e5a8',
  greenDim:   'rgba(0,229,168,0.1)',
  greenGlow:  'rgba(0,229,168,0.25)',
  red:        '#ff3d5a',
  redDim:     'rgba(255,61,90,0.1)',
  redGlow:    'rgba(255,61,90,0.25)',
  blue:       '#4da6ff',
  blueDim:    'rgba(77,166,255,0.1)',
  blueGlow:   'rgba(77,166,255,0.2)',
  gold:       '#f5c842',
  accent:     '#7b6cff',
  accentAlt:  '#9b5de5',
  accentDim:  'rgba(123,108,255,0.12)',
  accentGlow: 'rgba(123,108,255,0.3)',
};

// ── NSE Watchlist ────────────────────────────────────────────────────────────────
const DEFAULT_WATCHLIST = [
  { symbol: 'RELIANCE.NS', name: 'Reliance' },
  { symbol: 'TCS.NS',      name: 'TCS' },
  { symbol: 'HDFCBANK.NS', name: 'HDFC Bank' },
  { symbol: 'INFY.NS',     name: 'Infosys' },
  { symbol: 'ICICIBANK.NS',name: 'ICICI Bank' },
  { symbol: 'SBIN.NS',     name: 'SBI' },
  { symbol: 'BAJFINANCE.NS',name: 'Bajaj Fin' },
  { symbol: 'TMPV.NS',name: 'Tata Motors (TMPV)' },
  { symbol: 'WIPRO.NS',    name: 'Wipro' },
  { symbol: 'AXISBANK.NS', name: 'Axis Bank' },
];

const SEED_PRICES = {
  'RELIANCE.NS': 2920, 'TCS.NS': 4100, 'HDFCBANK.NS': 1780,
  'INFY.NS': 1650, 'ICICIBANK.NS': 1290, 'SBIN.NS': 845,
  'BAJFINANCE.NS': 7200, 'TMPV.NS': 385, 'WIPRO.NS': 490,
  'AXISBANK.NS': 1190,
};

const INTERVALS = [
  { label: '1D',  interval: '5m',  range: '1d' },
  { label: '1W',  interval: '15m', range: '5d' },
  { label: '1M',  interval: '1d',  range: '1mo' },
  { label: '3M',  interval: '1d',  range: '3mo' },
  { label: '1Y',  interval: '1wk', range: '1y' },
  { label: 'ALL', interval: '1mo', range: 'max' },
];

const PORTFOLIO = [
  { symbol: 'RELIANCE.NS', shares: 10, avgCost: 2750 },
  { symbol: 'TCS.NS',      shares: 5,  avgCost: 3850 },
  { symbol: 'HDFCBANK.NS', shares: 15, avgCost: 1650 },
  { symbol: 'INFY.NS',     shares: 20, avgCost: 1500 },
];

// ── Helpers ───────────────────────────────────────────────────────────────────
const fmt  = (n, d = 2) => n == null ? '—' : Number(n).toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });
const fmtK = (n) => n >= 1e9 ? `$${(n/1e9).toFixed(2)}B` : n >= 1e6 ? `$${(n/1e6).toFixed(1)}M` : `$${fmt(n)}`;
const clr  = (v) => v > 0 ? T.green : v < 0 ? T.red : T.textMid;
const sign = (v) => v > 0 ? '+' : '';

// ── Candlestick Chart (with volume and indicators) ────────────────────────
function CandleChart({ symbol, interval, range, indicators, livePrice }) {
  const mainContainerRef = useRef();
  const rsiContainerRef = useRef();
  const macdContainerRef = useRef();
  
  const mainChartRef = useRef();
  const rsiChartRef = useRef();
  const macdChartRef = useRef();

  const candleSeriesRef = useRef();
  const volSeriesRef = useRef();
  
  const { bars, loading } = useHistory(symbol, { interval, range, seedPrice: SEED_PRICES[symbol] });

  useEffect(() => {
    if (loading || !bars.length) return;
    
    // Clear elements inside containers
    if (mainContainerRef.current) mainContainerRef.current.innerHTML = '';
    if (rsiContainerRef.current) rsiContainerRef.current.innerHTML = '';
    if (macdContainerRef.current) macdContainerRef.current.innerHTML = '';
    
    const mainEl = mainContainerRef.current;
    if (!mainEl) return;
    
    const mainChart = createChart(mainEl, {
      width:  mainEl.clientWidth,
      height: mainEl.clientHeight,
      layout: {
        background: { type: 'solid', color: 'transparent' },
        textColor: T.textMid,
        fontSize: 11,
        fontFamily: "'IBM Plex Mono', monospace",
      },
      grid: {
        vertLines: { color: T.border },
        horzLines: { color: T.border },
      },
      crosshair: {
        vertLine: { color: T.borderHi, width: 1, style: 3 },
        horzLine: { color: T.borderHi, width: 1, style: 3 },
      },
      rightPriceScale: {
        borderColor: T.border,
        textColor: T.textMid,
      },
      timeScale: {
        borderColor: T.border,
        textColor: T.textMid,
        timeVisible: true,
      },
    });
    mainChartRef.current = mainChart;

    const candleSeries = mainChart.addSeries(CandlestickSeries, {
      upColor:       T.green,
      downColor:     T.red,
      borderVisible: false,
      wickUpColor:   T.green,
      wickDownColor: T.red,
      priceScaleId:  'right',
    });
    candleSeries.setData(bars);
    candleSeriesRef.current = candleSeries;

    // Volume histogram on main chart
    const volSeries = mainChart.addSeries(HistogramSeries, {
      priceFormat:  { type: 'volume' },
      priceScaleId: 'vol',
      color: 'rgba(77,159,255,0.25)',
    });
    const volData = bars.map(b => ({
      time:  b.time,
      value: b.volume || 0,
      color: b.close >= b.open ? 'rgba(0,216,160,0.22)' : 'rgba(255,78,106,0.22)',
    }));
    volSeries.setData(volData);
    volSeriesRef.current = volSeries;

    mainChart.priceScale('vol').applyOptions({
      scaleMargins: { top: 0.82, bottom: 0 },
    });

    // EMA 9 overlay
    if (indicators.ema9) {
      const ema9Data = calcEMA(bars, 9);
      const ema9Series = mainChart.addSeries(LineSeries, {
        color: '#00e5a8',
        lineWidth: 1.5,
        title: 'EMA 9',
      });
      ema9Series.setData(ema9Data);
    }

    // EMA 21 overlay
    if (indicators.ema21) {
      const ema21Data = calcEMA(bars, 21);
      const ema21Series = mainChart.addSeries(LineSeries, {
        color: '#ff9f43',
        lineWidth: 1.5,
        title: 'EMA 21',
      });
      ema21Series.setData(ema21Data);
    }

    // Bollinger Bands overlays
    if (indicators.bb) {
      const bbData = calcBollingerBands(bars, 20, 2);
      const bbUpSeries = mainChart.addSeries(LineSeries, {
        color: 'rgba(123,108,255,0.6)',
        lineWidth: 1,
      });
      const bbMidSeries = mainChart.addSeries(LineSeries, {
        color: 'rgba(123,108,255,0.3)',
        lineWidth: 1,
        lineStyle: 2,
      });
      const bbDownSeries = mainChart.addSeries(LineSeries, {
        color: 'rgba(123,108,255,0.6)',
        lineWidth: 1,
      });
      bbUpSeries.setData(bbData.upper);
      bbMidSeries.setData(bbData.middle);
      bbDownSeries.setData(bbData.lower);
    }

    const targets = [];

    // RSI Sub-Chart
    if (indicators.rsi && rsiContainerRef.current) {
      const rsiEl = rsiContainerRef.current;
      const rsiChart = createChart(rsiEl, {
        width: rsiEl.clientWidth,
        height: rsiEl.clientHeight,
        layout: {
          background: { type: 'solid', color: 'transparent' },
          textColor: T.textMid,
          fontSize: 10,
          fontFamily: "'IBM Plex Mono', monospace",
        },
        grid: {
          vertLines: { color: T.border },
          horzLines: { color: T.border },
        },
        rightPriceScale: {
          borderColor: T.border,
          textColor: T.textMid,
          visible: true,
        },
        timeScale: {
          borderColor: T.border,
          visible: false,
        },
      });
      rsiChartRef.current = rsiChart;
      targets.push(rsiChart);

      const rsiSeries = rsiChart.addSeries(LineSeries, {
        color: '#7b6cff',
        lineWidth: 1.5,
      });
      const rsiData = calcRSI(bars, 14);
      rsiSeries.setData(rsiData);

      rsiSeries.createPriceLine({
        price: 70,
        color: 'rgba(255,61,90,0.4)',
        lineWidth: 1,
        lineStyle: 3,
        axisLabelVisible: true,
      });
      rsiSeries.createPriceLine({
        price: 30,
        color: 'rgba(0,229,168,0.4)',
        lineWidth: 1,
        lineStyle: 3,
        axisLabelVisible: true,
      });
      rsiChart.priceScale('right').applyOptions({
        autoScale: false,
        min: 0,
        max: 100,
      });
    }

    // MACD Sub-Chart
    if (indicators.macd && macdContainerRef.current) {
      const macdEl = macdContainerRef.current;
      const macdChart = createChart(macdEl, {
        width: macdEl.clientWidth,
        height: macdEl.clientHeight,
        layout: {
          background: { type: 'solid', color: 'transparent' },
          textColor: T.textMid,
          fontSize: 10,
          fontFamily: "'IBM Plex Mono', monospace",
        },
        grid: {
          vertLines: { color: T.border },
          horzLines: { color: T.border },
        },
        rightPriceScale: {
          borderColor: T.border,
          textColor: T.textMid,
          visible: true,
        },
        timeScale: {
          borderColor: T.border,
          visible: false,
        },
      });
      macdChartRef.current = macdChart;
      targets.push(macdChart);

      const macdData = calcMACD(bars);
      
      const macdHistSeries = macdChart.addSeries(HistogramSeries, {
        priceScaleId: 'right',
      });
      const macdHistData = macdData.histogram.map(h => ({
        time: h.time,
        value: h.value,
        color: h.value >= 0 ? 'rgba(0,229,168,0.3)' : 'rgba(255,61,90,0.3)',
      }));
      macdHistSeries.setData(macdHistData);

      const macdLineSeries = macdChart.addSeries(LineSeries, {
        color: '#4da6ff',
        lineWidth: 1.2,
      });
      macdLineSeries.setData(macdData.macdLine.map(m => ({ time: m.time, value: m.value })));

      const macdSigSeries = macdChart.addSeries(LineSeries, {
        color: '#f5c842',
        lineWidth: 1.2,
      });
      macdSigSeries.setData(macdData.signalLine.map(s => ({ time: s.time, value: s.value })));
    }

    if (targets.length > 0) {
      mainChart.timeScale().subscribeVisibleTimeRangeChange(() => {
        const range = mainChart.timeScale().getVisibleRange();
        if (range) {
          targets.forEach(t => t.timeScale().setVisibleRange(range));
        }
      });
    }

    mainChart.timeScale().fitContent();

    const ro = new ResizeObserver(() => {
      if (!mainEl) return;
      const w = mainEl.clientWidth;
      mainChart.applyOptions({ width: w, height: mainEl.clientHeight });
      if (rsiChartRef.current && rsiContainerRef.current) {
        rsiChartRef.current.applyOptions({ width: w, height: rsiContainerRef.current.clientHeight });
      }
      if (macdChartRef.current && macdContainerRef.current) {
        macdChartRef.current.applyOptions({ width: w, height: macdContainerRef.current.clientHeight });
      }
    });
    ro.observe(mainEl);

    return () => {
      ro.disconnect();
      mainChart.remove();
      rsiChartRef.current?.remove();
      macdChartRef.current?.remove();
    };
  }, [bars, loading, indicators]);

  // Live tick updates to the last bar on the chart!
  useEffect(() => {
    if (!livePrice || !bars.length || !candleSeriesRef.current) return;
    const lastBar = bars[bars.length - 1];
    if (!lastBar) return;
    
    const price = livePrice.price;
    const updatedBar = {
      time: lastBar.time,
      open: lastBar.open,
      high: Math.max(lastBar.high, price),
      low: Math.min(lastBar.low, price),
      close: price,
    };
    
    candleSeriesRef.current.update(updatedBar);
    
    if (volSeriesRef.current) {
      volSeriesRef.current.update({
        time: lastBar.time,
        value: lastBar.volume || 0,
        color: updatedBar.close >= updatedBar.open ? 'rgba(0,216,160,0.22)' : 'rgba(255,78,106,0.22)',
      });
    }
  }, [livePrice, bars]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, height: '100%', minHeight: 0, overflow: 'hidden', position: 'relative' }}>
      {loading && (
        <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(10,12,16,0.7)', zIndex: 2, gap: 10, color: T.textMid, fontSize: 13, letterSpacing: '0.05em' }}>
          <span style={{ display: 'inline-block', width: 14, height: 14, border: `2px solid ${T.border}`, borderTopColor: T.accent, borderRadius: '50%', animation: 'spin 0.7s linear infinite' }} />
          LOADING MARKET DATA
        </div>
      )}
      
      {/* Main Chart Container */}
      <div ref={mainContainerRef} style={{ flex: 3, minHeight: 0, position: 'relative' }} />
      
      {/* RSI Container */}
      {indicators.rsi && (
        <div style={{ height: 95, borderTop: `1px solid ${T.border}`, position: 'relative', background: T.surface, flexShrink: 0 }}>
          <div style={{ position: 'absolute', top: 4, left: 12, zIndex: 5, fontSize: 9, color: T.textMid, fontFamily: "'IBM Plex Mono', monospace", fontWeight: 700 }}>
            RSI (14)
          </div>
          <div ref={rsiContainerRef} style={{ width: '100%', height: '100%' }} />
        </div>
      )}

      {/* MACD Container */}
      {indicators.macd && (
        <div style={{ height: 95, borderTop: `1px solid ${T.border}`, position: 'relative', background: T.surface, flexShrink: 0 }}>
          <div style={{ position: 'absolute', top: 4, left: 12, zIndex: 5, fontSize: 9, color: T.textMid, fontFamily: "'IBM Plex Mono', monospace", fontWeight: 700 }}>
            MACD (12, 26, 9)
          </div>
          <div ref={macdContainerRef} style={{ width: '100%', height: '100%' }} />
        </div>
      )}
    </div>
  );
}


// ── Ticker Row (scrolling top bar) ────────────────────────────────────────────
function TickerBar({ prices }) {
  const symbols = DEFAULT_WATCHLIST.map(w => w.symbol);
  return (
    <div style={{ background: T.surface, borderBottom: `1px solid ${T.border}`, overflow: 'hidden', height: 32, display: 'flex', alignItems: 'center', position: 'relative' }}>
      {/* fade edges */}
      <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: 40, background: `linear-gradient(90deg,${T.surface},transparent)`, zIndex: 1, pointerEvents: 'none' }} />
      <div style={{ position: 'absolute', right: 0, top: 0, bottom: 0, width: 40, background: `linear-gradient(270deg,${T.surface},transparent)`, zIndex: 1, pointerEvents: 'none' }} />
      <div style={{ display: 'flex', gap: 0, padding: '0 40px', animation: 'marquee 50s linear infinite', whiteSpace: 'nowrap' }}>
        {[...symbols, ...symbols].map((sym, i) => {
          const p = prices[sym];
          const price = p?.price ?? SEED_PRICES[sym] ?? 0;
          const pct   = p?.changePct ?? 0;
          const isUp  = pct >= 0;
          return (
            <span key={i} style={{ display: 'inline-flex', gap: 7, alignItems: 'center', fontSize: 11, fontFamily: "'IBM Plex Mono', monospace", padding: '0 20px', borderRight: `1px solid ${T.border}` }}>
              <span style={{ color: T.textMid, fontWeight: 600, letterSpacing: '0.05em', fontSize: 10 }}>{sym.replace('.NS', '')}</span>
              <span style={{ color: T.text, fontWeight: 500 }}>₹{fmt(price)}</span>
              <span style={{ color: isUp ? T.green : T.red, fontSize: 10, background: isUp ? T.greenDim : T.redDim, padding: '1px 5px', borderRadius: 3 }}>{sign(pct)}{fmt(pct, 2)}%</span>
            </span>
          );
        })}
      </div>
    </div>
  );
}

// ── Watchlist Panel ───────────────────────────────────────────────────────────
function WatchlistPanel({ prices, selected, onSelect }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <div style={{ padding: '14px 16px 10px', borderBottom: `1px solid ${T.border}`, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.12em', color: T.textMid, fontFamily: "'IBM Plex Mono', monospace" }}>WATCHLIST</span>
        <span style={{ fontSize: 10, color: T.textDim, fontFamily: "'IBM Plex Mono', monospace" }}>{DEFAULT_WATCHLIST.length} SYMBOLS</span>
      </div>
      <div style={{ flex: 1, overflowY: 'auto' }}>
        {DEFAULT_WATCHLIST.map(({ symbol, name }) => {
          const p     = prices[symbol];
          const price = p?.price ?? SEED_PRICES[symbol] ?? 0;
          const pct   = p?.changePct ?? 0;
          const isUp  = pct >= 0;
          const isSel = selected === symbol;
          return (
            <div key={symbol}
              onClick={() => onSelect(symbol)}
              style={{
                padding: '11px 16px', cursor: 'pointer', transition: 'background 0.15s',
                background: isSel ? T.blueDim : 'transparent',
                borderLeft: `2px solid ${isSel ? T.blue : 'transparent'}`,
                borderBottom: `1px solid ${T.border}`,
              }}
              onMouseEnter={e => !isSel && (e.currentTarget.style.background = 'rgba(255,255,255,0.02)')}
              onMouseLeave={e => !isSel && (e.currentTarget.style.background = 'transparent')}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <div style={{ fontSize: 12, fontWeight: 700, color: isSel ? T.blue : T.text, letterSpacing: '0.03em', fontFamily: "'IBM Plex Mono', monospace" }}>{symbol.replace('.NS', '')}</div>
                  <div style={{ fontSize: 10, color: T.textDim, marginTop: 2 }}>{name}</div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: 12, color: T.text, fontFamily: "'IBM Plex Mono', monospace" }}>₹{fmt(price)}</div>
                  <div style={{ fontSize: 10, color: clr(pct), marginTop: 2, background: isUp ? T.greenDim : T.redDim, padding: '1px 5px', borderRadius: 3, fontFamily: "'IBM Plex Mono', monospace" }}>
                    {sign(pct)}{fmt(pct, 2)}%
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Portfolio Panel ───────────────────────────────────────────────────────────
function PortfolioPanel({ prices, portfolio, cash }) {
  let stockValue = 0, totalCost = 0;
  const positions = portfolio.map(pos => {
    const price = prices[pos.symbol]?.price ?? SEED_PRICES[pos.symbol] ?? pos.avgCost;
    const value = price * pos.shares;
    const cost  = pos.avgCost * pos.shares;
    const pnl   = value - cost;
    const pnlPct = cost > 0 ? ((value - cost) / cost) * 100 : 0;
    stockValue += value; totalCost += cost;
    return { ...pos, price, value, pnl, pnlPct };
  });
  const totalValue = stockValue + cash;
  const totalPnl = stockValue - totalCost;
  const totalPct = totalCost > 0 ? (totalPnl / totalCost) * 100 : 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <div style={{ padding: '14px 16px 10px', borderBottom: `1px solid ${T.border}` }}>
        <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.12em', color: T.textMid, fontFamily: "'IBM Plex Mono', monospace" }}>PORTFOLIO</span>
      </div>
      {/* Summary */}
      <div style={{ padding: '14px 16px', borderBottom: `1px solid ${T.border}`, background: 'rgba(255,255,255,0.015)' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
          <div>
            <div style={{ fontSize: 9, color: T.textDim, marginBottom: 4, fontFamily: "'IBM Plex Mono', monospace" }}>NET WORTH</div>
            <div style={{ fontSize: 15, fontWeight: 700, color: T.text, fontFamily: "'IBM Plex Mono', monospace" }}>₹{fmt(totalValue)}</div>
            <div style={{ fontSize: 9, color: clr(totalPnl), marginTop: 2, fontFamily: "'IBM Plex Mono', monospace" }}>
              {sign(totalPnl)}₹{fmt(Math.abs(totalPnl))} ({sign(totalPct)}{fmt(totalPct, 2)}%)
            </div>
          </div>
          <div style={{ borderLeft: `1px solid ${T.border}`, paddingLeft: 10 }}>
            <div style={{ fontSize: 9, color: T.textDim, marginBottom: 4, fontFamily: "'IBM Plex Mono', monospace" }}>AVAILABLE CASH</div>
            <div style={{ fontSize: 15, fontWeight: 700, color: T.blue, fontFamily: "'IBM Plex Mono', monospace" }}>₹{fmt(cash)}</div>
            <div style={{ fontSize: 9, color: T.textDim, marginTop: 2 }}>Stocks: ₹{fmt(stockValue)}</div>
          </div>
        </div>
      </div>
      {/* Positions */}
      <div style={{ flex: 1, overflowY: 'auto' }}>
        {positions.length === 0 ? (
          <div style={{ padding: '30px 16px', textAlign: 'center', color: T.textDim, fontSize: 11, fontFamily: "'IBM Plex Mono', monospace" }}>
            NO POSITIONS HELD
          </div>
        ) : (
          positions.map(pos => (
            <div key={pos.symbol} style={{ padding: '10px 16px', borderBottom: `1px solid ${T.border}` }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5 }}>
                <span style={{ fontSize: 11, fontWeight: 700, color: T.text, fontFamily: "'IBM Plex Mono', monospace" }}>{pos.symbol.replace('.NS', '')}</span>
                <span style={{ fontSize: 11, color: T.text, fontFamily: "'IBM Plex Mono', monospace" }}>₹{fmt(pos.value)}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ fontSize: 10, color: T.textDim }}>{pos.shares} × ₹{fmt(pos.avgCost)}</span>
                <span style={{ fontSize: 10, color: clr(pos.pnl), fontFamily: "'IBM Plex Mono', monospace" }}>{sign(pos.pnl)}₹{fmt(Math.abs(pos.pnl))}</span>
              </div>
              {/* PnL bar */}
              <div style={{ height: 2, background: T.border, borderRadius: 2, marginTop: 6, overflow: 'hidden' }}>
                <div style={{ height: '100%', width: `${Math.min(100, Math.abs(pos.pnlPct) * 3)}%`, background: clr(pos.pnl), transition: 'width 0.6s ease', borderRadius: 2 }} />
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

// ── Order Entry Panel ─────────────────────────────────────────────────────────
function OrderPanel({ symbol, price, cash, openOrders, onExecuteOrder, onCancelOrder }) {
  const [side, setSide]     = useState('buy');
  const [qty, setQty]       = useState('');
  const [type, setType]     = useState('market');
  const [limit, setLimit]   = useState('');
  const [status, setStatus] = useState(null);

  const executionPrice = type === 'limit' ? parseFloat(limit) : price;
  const total = qty && executionPrice ? (parseFloat(qty) * executionPrice).toFixed(2) : '—';

  const submit = () => {
    setStatus('placing');
    const orderData = {
      side,
      symbol,
      type,
      qty,
      limitPrice: type === 'limit' ? limit : price,
      price
    };
    
    setTimeout(() => {
      const res = onExecuteOrder(orderData);
      if (res === 'filled') {
        setStatus('filled');
        setQty('');
        setLimit('');
        setTimeout(() => setStatus(null), 3000);
      } else if (res === 'placed') {
        setStatus('placed');
        setQty('');
        setLimit('');
        setTimeout(() => setStatus(null), 3000);
      } else {
        setStatus(null);
      }
    }, 600);
  };

  return (
    <div style={{ padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: 10, height: '100%', boxSizing: 'border-box', overflowY: 'auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.12em', color: T.textMid, fontFamily: "'IBM Plex Mono', monospace" }}>ORDER ENTRY</span>
        <span style={{ fontSize: 9, color: T.textDim, fontFamily: "'IBM Plex Mono', monospace" }}>CASH: ₹{fmt(cash)}</span>
      </div>

      {/* Buy/Sell toggle */}
      <div style={{ display: 'flex', background: T.bg, borderRadius: 6, padding: 3, border: `1px solid ${T.border}` }}>
        {['buy','sell'].map(s => (
          <button key={s} onClick={() => setSide(s)} style={{
            flex: 1, padding: '7px 0', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 700,
            letterSpacing: '0.08em', fontFamily: "'IBM Plex Mono', monospace", transition: 'all 0.2s',
            background: side === s ? (s === 'buy' ? T.green : T.red) : 'transparent',
            color: side === s ? '#000' : T.textMid,
          }}>{s.toUpperCase()}</button>
        ))}
      </div>

      {/* Order type */}
      <div style={{ display: 'flex', gap: 6 }}>
        {['market','limit'].map(t => (
          <button key={t} onClick={() => setType(t)} style={{
            flex: 1, padding: '6px 0', border: `1px solid ${type === t ? T.accent : T.border}`,
            borderRadius: 4, cursor: 'pointer', fontSize: 10, background: type === t ? T.blueDim : 'transparent',
            color: type === t ? T.accent : T.textMid, fontFamily: "'IBM Plex Mono', monospace", letterSpacing: '0.06em',
            transition: 'all 0.2s',
          }}>{t.toUpperCase()}</button>
        ))}
      </div>

      <Label text="QUANTITY">
        <Input value={qty} onChange={e => setQty(e.target.value)} placeholder="0.00" suffix="SHARES" />
      </Label>

      {type === 'limit' && (
        <Label text="LIMIT PRICE">
          <Input value={limit} onChange={e => setLimit(e.target.value)} placeholder={fmt(price)} prefix="₹" />
        </Label>
      )}

      <div style={{ padding: '8px 10px', background: T.bg, borderRadius: 6, border: `1px solid ${T.border}`, display: 'flex', justifyContent: 'space-between', fontSize: 10, fontFamily: "'IBM Plex Mono', monospace" }}>
        <span style={{ color: T.textDim }}>EST. TOTAL</span>
        <span style={{ color: T.text }}>₹{total === '—' ? '—' : fmt(total)}</span>
      </div>

      {status === 'filled' && (
        <div style={{ padding: '8px 10px', background: T.greenDim, border: `1px solid ${T.green}`, borderRadius: 6, fontSize: 10, color: T.green, fontFamily: "'IBM Plex Mono', monospace", textAlign: 'center' }}>
          ✓ ORDER FILLED (PAPER)
        </div>
      )}

      {status === 'placed' && (
        <div style={{ padding: '8px 10px', background: T.blueDim, border: `1px solid ${T.blue}`, borderRadius: 6, fontSize: 10, color: T.blue, fontFamily: "'IBM Plex Mono', monospace", textAlign: 'center' }}>
          ✓ LIMIT ORDER PLACED (PAPER)
        </div>
      )}

      <button onClick={submit} disabled={!qty || status === 'placing'} style={{
        padding: '11px', border: 'none', borderRadius: 6, cursor: qty ? 'pointer' : 'not-allowed',
        background: side === 'buy' ? T.green : T.red,
        color: '#000', fontWeight: 700, fontSize: 11, letterSpacing: '0.1em',
        fontFamily: "'IBM Plex Mono', monospace", opacity: qty ? 1 : 0.4, transition: 'opacity 0.2s',
      }}>
        {status === 'placing' ? 'PLACING...' : `${side.toUpperCase()} ${symbol.replace('.NS', '')}`}
      </button>

      {/* Open Limit Orders List */}
      {openOrders && openOrders.length > 0 && (
        <div style={{ marginTop: 10, borderTop: `1px solid ${T.border}`, paddingTop: 10 }}>
          <div style={{ fontSize: 9, fontWeight: 700, letterSpacing: '0.12em', color: T.textMid, fontFamily: "'IBM Plex Mono', monospace", marginBottom: 6 }}>
            OPEN LIMIT ORDERS ({openOrders.length})
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
            {openOrders.map(o => (
              <div key={o.id} style={{ background: T.bg, border: `1px solid ${T.border}`, borderRadius: 6, padding: '7px 9px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
                    <span style={{ fontSize: 9, fontWeight: 700, color: o.side === 'buy' ? T.green : T.red, fontFamily: "'IBM Plex Mono', monospace" }}>
                      {o.side.toUpperCase()}
                    </span>
                    <span style={{ fontSize: 9, fontWeight: 700, color: T.text, fontFamily: "'IBM Plex Mono', monospace" }}>
                      {o.symbol.replace('.NS', '')}
                    </span>
                  </div>
                  <div style={{ fontSize: 8, color: T.textDim, marginTop: 1, fontFamily: "'IBM Plex Mono', monospace" }}>
                    {o.qty} shares @ ₹{fmt(o.limitPrice)}
                  </div>
                </div>
                <button
                  onClick={() => onCancelOrder(o.id)}
                  style={{
                    padding: '2px 6px', background: T.redDim, border: `1px solid rgba(255,61,90,0.3)`, borderRadius: 4,
                    color: T.red, fontSize: 8, fontWeight: 700, cursor: 'pointer', fontFamily: "'IBM Plex Mono', monospace",
                    transition: 'all 0.15s'
                  }}
                >
                  CANCEL
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      <div style={{ fontSize: 9, color: T.textDim, textAlign: 'center', lineHeight: 1.4, marginTop: 4 }}>PAPER TRADING ONLY — NO REAL ORDERS EXECUTED</div>
    </div>
  );
}

function Label({ text, children }) {
  return (
    <div>
      <div style={{ fontSize: 9, color: T.textDim, letterSpacing: '0.1em', marginBottom: 5, fontFamily: "'IBM Plex Mono', monospace" }}>{text}</div>
      {children}
    </div>
  );
}

function Input({ value, onChange, placeholder, prefix, suffix }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', background: T.bg, border: `1px solid ${T.borderHi}`, borderRadius: 6, overflow: 'hidden', transition: 'border-color 0.2s' }}
      onFocus={e => e.currentTarget.style.borderColor = T.accent}
      onBlur={e => e.currentTarget.style.borderColor = T.borderHi}
    >
      {prefix && <span style={{ padding: '0 8px', color: T.textDim, fontSize: 11, fontFamily: "'IBM Plex Mono', monospace" }}>{prefix}</span>}
      <input value={value} onChange={onChange} placeholder={placeholder} style={{
        flex: 1, padding: '8px 10px', background: 'transparent', border: 'none', outline: 'none',
        color: T.text, fontSize: 12, fontFamily: "'IBM Plex Mono', monospace",
      }} />
      {suffix && <span style={{ padding: '0 8px', color: T.textDim, fontSize: 9, letterSpacing: '0.06em', fontFamily: "'IBM Plex Mono', monospace" }}>{suffix}</span>}
    </div>
  );
}

// ── Markdown renderer (bold + inline code) ───────────────────────────────────
function MdText({ text }) {
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/);
  return (
    <span>
      {parts.map((p, i) => {
        if (p.startsWith('**') && p.endsWith('**'))
          return <strong key={i} style={{ color: T.text, fontWeight: 700 }}>{p.slice(2,-2)}</strong>;
        if (p.startsWith('`') && p.endsWith('`'))
          return <code key={i} style={{ background: T.bg, color: T.accent, padding: '1px 5px', borderRadius: 3, fontSize: 10, fontFamily: "'IBM Plex Mono', monospace" }}>{p.slice(1,-1)}</code>;
        return p;
      })}
    </span>
  );
}

// ── AI Chat Panel ─────────────────────────────────────────────────────────────
function ChatPanel({ symbol, price, changePct }) {
  const [msgs, setMsgs]         = useState([
    { role: 'assistant', text: `Greetings! I'm your AI Trading Mentor. Ask me any questions about trading strategies, candlestick patterns (Candlestick Bible), risk management (SL Guide), or technical indicators.` }
  ]);
  const [input, setInput]       = useState('');
  const [busy, setBusy]         = useState(false);
  const [aiSource, setAiSource] = useState(null);
  const bottomRef               = useRef();
  const inputRef                = useRef();

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [msgs]);

  const send = useCallback(async () => {
    if (!input.trim() || busy) return;
    const userMsg = input.trim();
    setInput('');
    setMsgs(m => [...m, { role: 'user', text: userMsg }]);
    setBusy(true);
    try {
      const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Session-Token': sessionStorage.getItem('apt_token') || ''
        },
        body: JSON.stringify({
          message: userMsg,
          context: { symbol: symbol.replace('.NS', ''), price, changePct },
          history: msgs.map(m => ({ role: m.role, text: m.text }))
        }),
      });
      if (!res.ok) throw new Error('backend unavailable');
      const data = await res.json();
      setAiSource(data.source);
      setMsgs(m => [...m, { role: 'assistant', text: data.reply || 'No response.' }]);
    } catch {
      const fallback = [
        `**AI Assistant** — The backend isn't running or timed out. Start it with \`uvicorn main:app --reload\` to enable real-time mentor features.`,
        `Risk Management Advice: Always apply the 2% maximum risk rule from your SL Guide. Sizing is key!`,
      ];
      setMsgs(m => [...m, { role: 'assistant', text: fallback[Math.floor(Math.random() * fallback.length)] }]);
    }
    setBusy(false);
  }, [input, busy, symbol, price, changePct]);

  const onKey = (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } };
  const SUGGESTIONS = ['Explain Hammer Candlesticks', 'What is the 2% Risk Rule?', 'How to place Stop Losses?', 'Analyze market trend?'];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <div style={{ padding: '14px 16px 10px', borderBottom: `1px solid ${T.border}`, display: 'flex', alignItems: 'center', gap: 8 }}>
        <div style={{ width: 7, height: 7, borderRadius: '50%', background: T.green, boxShadow: `0 0 6px ${T.green}`, animation: 'pulse 2s ease-in-out infinite' }} />
        <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.12em', color: T.textMid, fontFamily: "'IBM Plex Mono', monospace", flex: 1 }}>AI ASSISTANT</span>
        {aiSource && (
          <span style={{ fontSize: 8, padding: '2px 6px', borderRadius: 3, background: aiSource === 'gemini' ? T.blueDim : T.greenDim, color: aiSource === 'gemini' ? T.blue : T.green, fontFamily: "'IBM Plex Mono', monospace", letterSpacing: '0.06em' }}>
            {aiSource === 'gemini' ? '✦ GEMINI' : 'LOCAL'}
          </span>
        )}
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '12px 14px', display: 'flex', flexDirection: 'column', gap: 10 }}>
        {msgs.map((m, i) => (
          <div key={i} style={{ display: 'flex', justifyContent: m.role === 'user' ? 'flex-end' : 'flex-start', animation: 'fadeIn 0.2s ease' }}>
            <div style={{
              maxWidth: '88%', padding: '9px 13px', borderRadius: m.role === 'user' ? '12px 12px 3px 12px' : '12px 12px 12px 3px',
              background: m.role === 'user' ? T.blueDim : T.panel,
              border: `1px solid ${m.role === 'user' ? T.accent : T.border}`,
              fontSize: 12, lineHeight: 1.6, color: T.text,
            }}><MdText text={m.text} /></div>
          </div>
        ))}
        {busy && (
          <div style={{ display: 'flex', gap: 4, padding: '10px 14px' }}>
            {[0,1,2].map(i => <span key={i} style={{ width: 5, height: 5, borderRadius: '50%', background: T.accent, animation: `bounce 1s ${i * 0.2}s ease-in-out infinite` }} />)}
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {msgs.length <= 2 && (
        <div style={{ padding: '0 12px 8px', display: 'flex', flexWrap: 'wrap', gap: 5 }}>
          {SUGGESTIONS.map(s => (
            <button key={s} onClick={() => { setInput(s); }}
              style={{ fontSize: 9, padding: '4px 8px', borderRadius: 12, border: `1px solid ${T.borderHi}`, background: 'transparent', color: T.textMid, cursor: 'pointer', fontFamily: "'IBM Plex Mono', monospace", transition: 'all 0.15s' }}
              onMouseEnter={e => { e.target.style.borderColor = T.accent; e.target.style.color = T.accent; }}
              onMouseLeave={e => { e.target.style.borderColor = T.borderHi; e.target.style.color = T.textMid; }}
            >{s}</button>
          ))}
        </div>
      )}

      <div style={{ padding: '10px 12px', borderTop: `1px solid ${T.border}`, display: 'flex', gap: 8 }}>
        <input ref={inputRef} value={input} onChange={e => setInput(e.target.value)} onKeyDown={onKey}
          placeholder="Ask the AI Mentor anything (e.g. Hammer candlestick, 2% risk)..."
          style={{ flex: 1, background: T.bg, border: `1px solid ${T.borderHi}`, borderRadius: 8, padding: '9px 12px', color: T.text, fontSize: 12, outline: 'none', fontFamily: 'inherit', transition: 'border-color 0.2s' }}
          onFocus={e => e.target.style.borderColor = T.accent}
          onBlur={e => e.target.style.borderColor = T.borderHi}
        />
        <button onClick={send} disabled={!input.trim() || busy} style={{
          padding: '9px 14px', background: input.trim() ? T.accent : T.border, border: 'none', borderRadius: 8,
          color: input.trim() ? '#fff' : T.textDim, fontSize: 11, fontWeight: 700,
          cursor: input.trim() ? 'pointer' : 'not-allowed', transition: 'all 0.2s',
          fontFamily: "'IBM Plex Mono', monospace",
        }}>ASK</button>
      </div>
    </div>
  );
}

// ── Header ─────────────────────────────────────────────────────────────────────────────
function Header({ symbol, connected, view, onViewChange, isMobile, onLogout }) {
  const { data: quote } = useQuote(symbol);
  const price     = quote?.price ?? SEED_PRICES[symbol] ?? 0;
  const change    = quote?.change ?? 0;
  const changePct = quote?.change_pct ?? 0;
  const isUp      = changePct >= 0;

  const [clock, setClock] = useState(() => new Date().toLocaleTimeString('en-IN', { hour12: true }));
  useEffect(() => {
    const t = setInterval(() => setClock(new Date().toLocaleTimeString('en-IN', { hour12: true })), 1000);
    return () => clearInterval(t);
  }, []);

  return (
    <div style={{ padding: '0 16px', height: 54, display: 'flex', alignItems: 'center', gap: 16, borderBottom: `1px solid ${T.border}`, background: T.surface, flexShrink: 0 }}>
      {/* Logo */}
      <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 13, fontWeight: 700, letterSpacing: '0.12em', whiteSpace: 'nowrap', background: `linear-gradient(135deg, ${T.accent}, ${T.accentAlt})`, WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', flexShrink: 0 }}>
        ◈ APEXTRADE
      </div>

      {/* View switcher — CHART | SIGNALS | PERFORMANCE | ACCOUNT (Hidden on Mobile) */}
      {!isMobile && (
        <div style={{ display: 'flex', background: T.bg, borderRadius: 6, padding: 2, border: `1px solid ${T.border}`, flexShrink: 0 }}>
          {[['CHART', '📈'], ['SIGNALS', '📡'], ['PERFORMANCE', '📊'], ['ACCOUNT', '🛡️ SECURITY']].map(([v, icon]) => (
            <button key={v} onClick={() => onViewChange(v)} style={{
              padding: '4px 12px', borderRadius: 4, border: 'none', cursor: 'pointer',
              background: view === v 
                ? (v === 'SIGNALS' ? T.accentDim : v === 'PERFORMANCE' ? T.greenDim : v === 'ACCOUNT' ? T.accentDim : T.blueDim) 
                : 'transparent',
              color: view === v 
                ? (v === 'SIGNALS' ? T.accentAlt : v === 'PERFORMANCE' ? T.green : v === 'ACCOUNT' ? T.accentAlt : T.accent) 
                : T.textDim,
              fontSize: 9, fontWeight: 700, letterSpacing: '0.08em',
              fontFamily: "'IBM Plex Mono', monospace", transition: 'all 0.2s',
              boxShadow: view === v && v === 'SIGNALS' 
                ? `0 0 10px ${T.accentGlow}` 
                : view === v && v === 'PERFORMANCE' 
                  ? `0 0 10px ${T.greenGlow}` 
                  : view === v && v === 'ACCOUNT' 
                    ? `0 0 10px ${T.accentGlow}` 
                    : 'none',
            }}>{icon} {v === 'SIGNALS' ? 'SCAN & ALLOCATE' : v}</button>
          ))}
        </div>
      )}

      <div style={{ width: 1, height: 22, background: T.border, flexShrink: 0 }} />

      {/* Symbol + price */}
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, minWidth: 0 }}>
        <span style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, fontWeight: 700, color: T.textMid, letterSpacing: '0.06em', flexShrink: 0 }}>
          {symbol.replace('.NS', '')}
        </span>
        <span style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 20, fontWeight: 700, color: T.text, letterSpacing: '-0.02em', flexShrink: 0 }}>₹{fmt(price)}</span>
        <span style={{ fontSize: 10, color: clr(changePct), background: isUp ? T.greenDim : T.redDim, border: `1px solid ${isUp ? T.greenGlow : T.redGlow}`, padding: '2px 7px', borderRadius: 4, fontFamily: "'IBM Plex Mono', monospace", flexShrink: 0 }}>
          {sign(changePct)}{fmt(changePct, 2)}%
        </span>
      </div>

      {/* Quote metadata (Hidden on Mobile) */}
      {quote && !isMobile && (
        <div style={{ display: 'flex', gap: 14 }}>
          {[
            ['H', quote.day_high], ['L', quote.day_low],
            ['VOL', quote.volume ? fmtK(quote.volume) : null],
          ].filter(([, v]) => v).map(([label, value]) => (
            <div key={label} style={{ fontSize: 10, fontFamily: "'IBM Plex Mono', monospace" }}>
              <span style={{ color: T.textDim }}>{label} </span>
              <span style={{ color: T.textMid }}>{typeof value === 'number' ? `₹${fmt(value)}` : value}</span>
            </div>
          ))}
        </div>
      )}

      <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 16 }}>
        {!isMobile && <span style={{ fontSize: 10, color: T.textDim, fontFamily: "'IBM Plex Mono', monospace", letterSpacing: '0.06em' }}>{clock} UTC+5:30</span>}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <div style={{
              width: 6,
              height: 6,
              borderRadius: '50%',
              background: !connected ? T.red : (isNSEMarketOpen() ? T.green : T.gold),
              boxShadow: connected && isNSEMarketOpen() ? `0 0 8px ${T.greenGlow}` : 'none',
              animation: connected && isNSEMarketOpen() ? 'pulse 2s ease-in-out infinite' : 'none'
            }} />
            <span style={{
              fontSize: 10,
              color: !connected ? T.red : (isNSEMarketOpen() ? T.green : T.gold),
              fontFamily: "'IBM Plex Mono', monospace",
              letterSpacing: '0.08em'
            }}>
              {!connected ? 'OFFLINE' : (isNSEMarketOpen() ? 'LIVE' : 'CLOSED')}
            </span>
          </div>

          {onLogout && (
            <button
              onClick={onLogout}
              style={{
                background: 'rgba(255, 61, 90, 0.05)',
                border: '1px solid rgba(255, 61, 90, 0.2)',
                borderRadius: 4,
                padding: '4px 10px',
                color: T.red,
                fontSize: 9,
                fontWeight: 700,
                fontFamily: "'IBM Plex Mono', monospace",
                cursor: 'pointer',
                transition: 'all 0.2s',
                letterSpacing: '0.08em',
                outline: 'none',
              }}
              onMouseEnter={e => {
                e.currentTarget.style.background = 'rgba(255, 61, 90, 0.15)';
                e.currentTarget.style.borderColor = 'rgba(255, 61, 90, 0.4)';
              }}
              onMouseLeave={e => {
                e.currentTarget.style.background = 'rgba(255, 61, 90, 0.05)';
                e.currentTarget.style.borderColor = 'rgba(255, 61, 90, 0.2)';
              }}
            >
              LOGOUT
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Bottom Tab Bar (mobile-friendly) ─────────────────────────────────────────
const TABS = ['CHART', 'WATCHLIST', 'SIGNALS', 'PORTFOLIO', 'ORDER', 'AI', 'ACCOUNT'];

// ── Main App ──────────────────────────────────────────────────────────────────
export default function App() {
  // Security Authentication Gate
  const [loggedIn, setLoggedIn] = useState(() => sessionStorage.getItem('apt_token') !== null);
  const [currentUser, setCurrentUser] = useState(() => localStorage.getItem('apex_user') || 'apex_head_quant');


  // Warm up backend in the background as soon as the app mounts (during login screen presentation)
  useEffect(() => {
    const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
    fetch(`${BASE_URL}/`).catch(() => {});
  }, []);

  const [view, setView]         = useState('CHART');   // 'CHART' | 'SIGNALS'
  const [selected, setSelected] = useState('RELIANCE.NS');
  const [ivIdx, setIvIdx]       = useState(0);          // 1D default for intraday
  const [rightTab, setRightTab] = useState('ORDER');
  
  // Server warming/cold start splash page state
  const [serverWarming, setServerWarming] = useState(true);


  // Mobile Responsiveness State
  const [isMobile, setIsMobile] = useState(window.innerWidth <= 800);
  const [mobileTab, setMobileTab] = useState('CHART'); // 'WATCHLIST' | 'CHART' | 'SIGNALS' | 'ORDER' | 'PORTFOLIO' | 'AI'

  useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth <= 800);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  
  // Interactive Overlays/Oscillators Toggles
  const [indicators, setIndicators] = useState({
    ema9: false,
    ema21: false,
    bb: false,
    rsi: false,
    macd: false,
  });

  // Paper Trading State
  const [portfolio, setPortfolio] = useState([
    { symbol: 'RELIANCE.NS', shares: 10, avgCost: 2750 },
    { symbol: 'TCS.NS',      shares: 5,  avgCost: 3850 },
    { symbol: 'HDFCBANK.NS', shares: 15, avgCost: 1650 },
    { symbol: 'INFY.NS',     shares: 20, avgCost: 1500 },
  ]);
  const [cash, setCash] = useState(1000000); // Starting cash: ₹10,00,000 (10 Lakhs)
  const [openOrders, setOpenOrders] = useState([]);

  const symbols = DEFAULT_WATCHLIST.map(w => w.symbol);
  const { prices, connected } = useLivePrices(symbols);
  const iv = INTERVALS[ivIdx];
  const currentPrice     = prices[selected]?.price ?? SEED_PRICES[selected] ?? 0;
  const currentChangePct = prices[selected]?.changePct ?? 0;

  // Execute market/limit orders
  const handleExecuteOrder = (order) => {
    const qty = parseFloat(order.qty);
    if (isNaN(qty) || qty <= 0) {
      alert("Please enter a valid share quantity!");
      return false;
    }
    
    if (order.type === 'market') {
      const price = order.price;
      const cost = qty * price;
      
      if (order.side === 'buy') {
        if (cost > cash) {
          alert("Insufficient cash balance!");
          return false;
        }
        setCash(prev => prev - cost);
        setPortfolio(prev => {
          const existing = prev.find(p => p.symbol === order.symbol);
          if (existing) {
            const newShares = existing.shares + qty;
            const newAvgCost = ((existing.shares * existing.avgCost) + cost) / newShares;
            return prev.map(p => p.symbol === order.symbol ? { ...p, shares: newShares, avgCost: newAvgCost } : p);
          } else {
            return [...prev, { symbol: order.symbol, shares: qty, avgCost: price }];
          }
        });
      } else {
        // sell
        let valid = true;
        setPortfolio(prev => {
          const existing = prev.find(p => p.symbol === order.symbol);
          if (!existing || existing.shares < qty) {
            valid = false;
            return prev;
          }
          const newShares = existing.shares - qty;
          if (newShares === 0) {
            return prev.filter(p => p.symbol !== order.symbol);
          }
          return prev.map(p => p.symbol === order.symbol ? { ...p, shares: newShares } : p);
        });
        
        if (!valid) {
          alert("Insufficient shares in portfolio to execute sell!");
          return false;
        }
        setCash(prev => prev + cost);
      }
      return 'filled';
    } else {
      // limit order
      const limitPrice = parseFloat(order.limitPrice);
      if (isNaN(limitPrice) || limitPrice <= 0) {
        alert("Please enter a valid limit price!");
        return false;
      }
      
      if (order.side === 'buy' && qty * limitPrice > cash) {
        alert("Insufficient cash to place this limit order!");
        return false;
      }
      
      if (order.side === 'sell') {
        const existing = portfolio.find(p => p.symbol === order.symbol);
        const lockedShares = openOrders
          .filter(o => o.symbol === order.symbol && o.side === 'sell')
          .reduce((sum, o) => sum + o.qty, 0);
        if (!existing || existing.shares < lockedShares + qty) {
          alert("Insufficient shares available (some are locked in other open orders)!");
          return false;
        }
      }

      const newOrder = {
        id: Math.random().toString(36).substr(2, 9),
        symbol: order.symbol,
        side: order.side,
        qty,
        limitPrice,
        timestamp: Date.now()
      };
      
      setOpenOrders(prev => [...prev, newOrder]);
      return 'placed';
    }
  };

  const handleCancelOrder = (id) => {
    setOpenOrders(prev => prev.filter(o => o.id !== id));
  };

  // Limit Order Matching Engine (Check on price ticks)
  useEffect(() => {
    if (openOrders.length === 0) return;
    
    let filledIds = [];
    let updatedCash = cash;
    let updatedPortfolio = [...portfolio];
    
    openOrders.forEach(order => {
      const livePrice = prices[order.symbol]?.price;
      if (!livePrice) return;
      
      let trigger = false;
      if (order.side === 'buy' && livePrice <= order.limitPrice) {
        trigger = true;
      } else if (order.side === 'sell' && livePrice >= order.limitPrice) {
        trigger = true;
      }
      
      if (trigger) {
        filledIds.push(order.id);
        const cost = order.qty * order.limitPrice; // execute at limit price
        
        if (order.side === 'buy') {
          if (cost <= updatedCash) {
            updatedCash -= cost;
            const existingIdx = updatedPortfolio.findIndex(p => p.symbol === order.symbol);
            if (existingIdx !== -1) {
              const existing = updatedPortfolio[existingIdx];
              const newShares = existing.shares + order.qty;
              const newAvgCost = ((existing.shares * existing.avgCost) + cost) / newShares;
              updatedPortfolio[existingIdx] = { ...existing, shares: newShares, avgCost: newAvgCost };
            } else {
              updatedPortfolio.push({ symbol: order.symbol, shares: order.qty, avgCost: order.limitPrice });
            }
          }
        } else {
          // sell
          const existingIdx = updatedPortfolio.findIndex(p => p.symbol === order.symbol);
          if (existingIdx !== -1) {
            const existing = updatedPortfolio[existingIdx];
            if (existing.shares >= order.qty) {
              const newShares = existing.shares - order.qty;
              if (newShares === 0) {
                updatedPortfolio.splice(existingIdx, 1);
              } else {
                updatedPortfolio[existingIdx] = { ...existing, shares: newShares };
              }
              updatedCash += cost;
            }
          }
        }
      }
    });
    
    if (filledIds.length > 0) {
      setCash(updatedCash);
      setPortfolio(updatedPortfolio);
      setOpenOrders(prev => prev.filter(o => !filledIds.includes(o.id)));
    }
  }, [prices, openOrders, cash, portfolio]);

  // Called from SignalsPanel when user clicks a signal card
  const handleSignalSelect = (symbol) => {
    setSelected(symbol);
    setView('CHART');
    setIvIdx(0);  // Switch to 1D (5-min) for intraday
  };

  const handleWokenUp = useCallback(() => {
    setServerWarming(false);
  }, []);

  if (!loggedIn) {
    return <LoginScreen onLogin={(user) => { setLoggedIn(true); setCurrentUser(user); localStorage.setItem('apex_user', user); }} />;
  }

  return (
    <>
      {serverWarming && <IntroSplash onWokenUp={handleWokenUp} />}
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600;700&family=Inter:wght@400;500;600;700&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        html, body, #root { width: 100%; height: 100%; overflow: hidden; background: ${T.bg}; }
        ::-webkit-scrollbar { width: 3px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: ${T.borderHi}; border-radius: 2px; }
        ::-webkit-scrollbar-thumb:hover { background: ${T.accent}; }
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes pulse { 0%,100% { opacity:1; transform:scale(1); } 50% { opacity:0.5; transform:scale(0.85); } }
        @keyframes bounce { 0%,100% { transform:translateY(0); } 50% { transform:translateY(-5px); } }
        @keyframes marquee { from { transform: translateX(0); } to { transform: translateX(-50%); } }
        @keyframes fadeIn { from { opacity:0; transform:translateY(6px); } to { opacity:1; transform:translateY(0); } }
        @keyframes slideIn { from { opacity:0; transform:translateX(8px); } to { opacity:1; transform:translateX(0); } }
        @keyframes shimmer { 0%,100% { opacity:0.6; } 50% { opacity:1; } }
        button:active { transform: scale(0.97); }
      `}</style>

      <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', fontFamily: "'Inter', sans-serif", fontSize: 13, color: T.text, background: T.bg }}>

        {/* Ticker bar */}
        <TickerBar prices={prices} />

        {/* Reconnecting banner if backend offline */}
        {!connected && (
          <div style={{
            background: 'rgba(245,200,66,0.08)',
            borderBottom: `1px solid rgba(245,200,66,0.2)`,
            color: T.gold,
            padding: '6px 16px',
            fontSize: 10,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 8,
            fontFamily: "'IBM Plex Mono', monospace",
            animation: 'shimmer 2s infinite',
            letterSpacing: '0.04em',
            flexShrink: 0
          }}>
            <span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', background: T.gold, animation: 'pulse 1.5s infinite' }} />
            BACKEND OFFLINE — WAITING FOR RENDER SERVER TO WAKE UP (THIS TAKES 30–50 SECONDS)
          </div>
        )}

        {/* Header */}
        <Header symbol={selected} connected={connected} view={view} onViewChange={setView} isMobile={isMobile} onLogout={() => { setLoggedIn(false); sessionStorage.removeItem('apt_token'); localStorage.removeItem('apex_user'); }} />

        {/* Main layout */}
        <div style={{ flex: 1, display: 'flex', minHeight: 0, overflow: 'hidden' }}>

          {view === 'SIGNALS' ? (
            /* SIGNALS VIEW — full width */
            <SignalsPanel onSelectSymbol={handleSignalSelect} selectedSymbol={selected} prices={prices} />
          ) : view === 'PERFORMANCE' ? (
            /* PERFORMANCE VIEW — full width */
            <PerformancePanel />
          ) : view === 'ACCOUNT' ? (
            /* ACCOUNT VIEW — full width */
            <AccountPanel currentUser={currentUser} />
          ) : (
            <>
              {isMobile ? (
                /* MOBILE VIEW — Single column with bottom tabs */
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, background: T.bg }}>
                  {/* Content Area */}
                  <div style={{ flex: 1, overflow: 'auto', display: 'flex', flexDirection: 'column' }}>
                    {mobileTab === 'WATCHLIST' && (
                      <div style={{ flex: 1, background: T.surface }}>
                        <WatchlistPanel prices={prices} selected={selected} onSelect={(s) => { setSelected(s); setMobileTab('CHART'); }} />
                      </div>
                    )}

                    {mobileTab === 'CHART' && (
                      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
                        {/* Interval picker & Indicator Toggles (Scrollable on mobile) */}
                        <div style={{ padding: '8px 12px', borderBottom: `1px solid ${T.border}`, display: 'flex', alignItems: 'center', gap: 6, background: T.surface, overflowX: 'auto', flexShrink: 0, whiteSpace: 'nowrap' }}>
                          {INTERVALS.map((intv, i) => (
                            <button key={intv.label} onClick={() => setIvIdx(i)} style={{
                              padding: '4px 8px', border: `1px solid ${ivIdx === i ? T.accent : T.border}`,
                              borderRadius: 5, cursor: 'pointer', fontSize: 10, fontWeight: 700,
                              background: ivIdx === i ? T.blueDim : 'transparent',
                              color: ivIdx === i ? T.accent : T.textMid,
                              fontFamily: "'IBM Plex Mono', monospace",
                              transition: 'all 0.15s', flexShrink: 0
                            }}>{intv.label}</button>
                          ))}
                          <div style={{ width: 1, height: 16, background: T.border, margin: '0 4px', flexShrink: 0 }} />
                          {/* Indicator Toggles */}
                          {[
                            ['ema9', 'EMA9'], ['ema21', 'EMA21'], ['bb', 'BB'], ['rsi', 'RSI'], ['macd', 'MACD'],
                          ].map(([key, label]) => {
                            const active = indicators[key];
                            return (
                              <button key={key} onClick={() => setIndicators(prev => ({ ...prev, [key]: !prev[key] }))} style={{
                                padding: '4px 8px', border: `1px solid ${active ? T.accent : T.border}`,
                                borderRadius: 5, cursor: 'pointer', fontSize: 9, fontWeight: 700,
                                background: active ? T.accentDim : 'transparent',
                                color: active ? T.accentAlt : T.textDim,
                                fontFamily: "'IBM Plex Mono', monospace",
                                transition: 'all 0.15s', flexShrink: 0
                              }}>{label}</button>
                            );
                          })}
                        </div>
                        {/* Chart */}
                        <CandleChart 
                          key={`${selected}-${INTERVALS[ivIdx].interval}-${INTERVALS[ivIdx].range}-${indicators.rsi}-${indicators.macd}`} 
                          symbol={selected} 
                          interval={INTERVALS[ivIdx].interval} 
                          range={INTERVALS[ivIdx].range} 
                          indicators={indicators} 
                          livePrice={prices[selected]}
                        />
                      </div>
                    )}

                    {mobileTab === 'SIGNALS' && (
                      <div style={{ flex: 1, background: T.surface, overflowY: 'auto' }}>
                        <SignalsPanel onSelectSymbol={(s) => { setSelected(s); setMobileTab('CHART'); }} selectedSymbol={selected} prices={prices} />
                      </div>
                    )}

                    {mobileTab === 'ORDER' && (
                      <div style={{ flex: 1, background: T.surface }}>
                        <OrderPanel symbol={selected} price={currentPrice} cash={cash} openOrders={openOrders} onExecuteOrder={handleExecuteOrder} onCancelOrder={handleCancelOrder} />
                      </div>
                    )}

                    {mobileTab === 'PORTFOLIO' && (
                      <div style={{ flex: 1, background: T.surface }}>
                        <PortfolioPanel prices={prices} portfolio={portfolio} cash={cash} />
                      </div>
                    )}

                    {mobileTab === 'AI' && (
                      <div style={{ flex: 1, background: T.surface }}>
                        <ChatPanel symbol={selected} price={currentPrice} changePct={currentChangePct} />
                      </div>
                    )}

                    {mobileTab === 'ACCOUNT' && (
                      <div style={{ flex: 1, background: T.surface }}>
                        <AccountPanel currentUser={currentUser} />
                      </div>
                    )}
                  </div>

                  {/* Bottom Navigation Bar */}
                  <div style={{ display: 'flex', borderTop: `1px solid ${T.border}`, background: T.panelAlt, flexShrink: 0, paddingBottom: 'env(safe-area-inset-bottom)' }}>
                    {TABS.map(tab => (
                      <button key={tab} onClick={() => setMobileTab(tab)} style={{
                        flex: 1, padding: '12px 0', border: 'none', cursor: 'pointer',
                        background: 'transparent',
                        color: mobileTab === tab ? (tab === 'AI' ? T.accentAlt : tab === 'ACCOUNT' ? T.accentAlt : T.accent) : T.textDim,
                        fontSize: 9, fontWeight: 700, letterSpacing: '0.05em',
                        fontFamily: "'IBM Plex Mono', monospace",
                        transition: 'all 0.2s',
                        borderTop: `2px solid ${mobileTab === tab ? (tab === 'AI' ? T.accentAlt : tab === 'ACCOUNT' ? T.accentAlt : T.accent) : 'transparent'}`,
                        marginTop: -1
                      }}>
                        {tab === 'AI' ? '✦ AI' : tab === 'SIGNALS' ? '📡 SCAN' : tab === 'ACCOUNT' ? '🛡️ SEC' : tab}
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                /* DESKTOP VIEW — 3 Columns */
                <>
                  {/* LEFT — Watchlist */}
                  <div style={{ width: 190, flexShrink: 0, borderRight: `1px solid ${T.border}`, background: T.surface, overflow: 'hidden' }}>
                    <WatchlistPanel prices={prices} selected={selected} onSelect={setSelected} />
                  </div>

                  {/* CENTER — Chart */}
                  <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, background: T.bg }}>
                    {/* Interval picker & Indicator Toggles */}
                    <div style={{ padding: '8px 16px', borderBottom: `1px solid ${T.border}`, display: 'flex', alignItems: 'center', gap: 6, background: T.surface, flexWrap: 'wrap' }}>
                      {INTERVALS.map((intv, i) => (
                        <button key={intv.label} onClick={() => setIvIdx(i)} style={{
                          padding: '4px 11px', border: `1px solid ${ivIdx === i ? T.accent : T.border}`,
                          borderRadius: 5, cursor: 'pointer', fontSize: 10, fontWeight: 700,
                          background: ivIdx === i ? T.blueDim : 'transparent',
                          color: ivIdx === i ? T.accent : T.textMid,
                          fontFamily: "'IBM Plex Mono', monospace", letterSpacing: '0.06em',
                          transition: 'all 0.15s',
                        }}>{intv.label}</button>
                      ))}

                      <div style={{ width: 1, height: 16, background: T.border, margin: '0 8px' }} />

                      {/* Indicator Toggles */}
                      {[
                        ['ema9', 'EMA 9'],
                        ['ema21', 'EMA 21'],
                        ['bb', 'BB Bands'],
                        ['rsi', 'RSI'],
                        ['macd', 'MACD'],
                      ].map(([key, label]) => {
                        const active = indicators[key];
                        return (
                          <button key={key} onClick={() => setIndicators(prev => ({ ...prev, [key]: !prev[key] }))} style={{
                            padding: '4px 9px', border: `1px solid ${active ? T.accent : T.border}`,
                            borderRadius: 5, cursor: 'pointer', fontSize: 9, fontWeight: 700,
                            background: active ? T.accentDim : 'transparent',
                            color: active ? T.accentAlt : T.textDim,
                            fontFamily: "'IBM Plex Mono', monospace", letterSpacing: '0.04em',
                            transition: 'all 0.15s',
                          }}>{label}</button>
                        );
                      })}

                      <div style={{ marginLeft: 'auto', fontSize: 10, color: T.textDim, fontFamily: "'IBM Plex Mono', monospace" }}>
                        {INTERVALS[ivIdx].interval} · {INTERVALS[ivIdx].range}
                      </div>
                    </div>

                    {/* Chart */}
                    <CandleChart 
                      key={`${selected}-${INTERVALS[ivIdx].interval}-${INTERVALS[ivIdx].range}-${indicators.rsi}-${indicators.macd}`} 
                      symbol={selected} 
                      interval={INTERVALS[ivIdx].interval} 
                      range={INTERVALS[ivIdx].range} 
                      indicators={indicators} 
                      livePrice={prices[selected]}
                    />
                  </div>

                  {/* RIGHT — Tabbed panel */}
                  <div style={{ width: 280, flexShrink: 0, borderLeft: `1px solid ${T.border}`, background: T.surface, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                    {/* Tab header */}
                    <div style={{ display: 'flex', borderBottom: `1px solid ${T.border}`, flexShrink: 0, background: T.panelAlt }}>
                      {['ORDER', 'PORTFOLIO', 'AI'].map(tab => (
                        <button key={tab} onClick={() => setRightTab(tab)} style={{
                          flex: 1, padding: '11px 4px', border: 'none', cursor: 'pointer',
                          background: 'transparent',
                          borderBottom: `2px solid ${rightTab === tab ? (tab === 'AI' ? T.accentAlt : T.accent) : 'transparent'}`,
                          color: rightTab === tab ? T.text : T.textDim,
                          fontSize: 9, fontWeight: 700, letterSpacing: '0.1em',
                          fontFamily: "'IBM Plex Mono', monospace", transition: 'all 0.2s',
                          boxShadow: rightTab === tab && tab === 'AI' ? `0 2px 12px ${T.accentGlow}` : 'none',
                        }}>
                          {tab === 'AI' ? '✦ AI' : tab}
                        </button>
                      ))}
                    </div>
                    {/* Tab content */}
                    <div style={{ flex: 1, overflow: 'hidden' }}>
                      {rightTab === 'ORDER'     && <OrderPanel symbol={selected} price={currentPrice} cash={cash} openOrders={openOrders} onExecuteOrder={handleExecuteOrder} onCancelOrder={handleCancelOrder} />}
                      {rightTab === 'PORTFOLIO' && <PortfolioPanel prices={prices} portfolio={portfolio} cash={cash} />}
                      {rightTab === 'AI'        && <ChatPanel symbol={selected} price={currentPrice} changePct={currentChangePct} />}
                    </div>
                  </div>
                </>
              )}
            </>
          )}
        </div>
      </div>
    </>
  );
}

// ══════════════════════════════════════════════════════════════════════════════
//  Indicator Calculation Helper Functions
// ══════════════════════════════════════════════════════════════════════════════

function calcEMA(data, period) {
  const ema = [];
  if (data.length === 0) return [];
  const k = 2 / (period + 1);
  let prevEma = data[0].close;
  ema.push({ time: data[0].time, value: prevEma });
  for (let i = 1; i < data.length; i++) {
    const val = data[i].close * k + prevEma * (1 - k);
    ema.push({ time: data[i].time, value: val });
    prevEma = val;
  }
  return ema;
}

function calcBollingerBands(data, period = 20, multiplier = 2) {
  const upper = [];
  const middle = [];
  const lower = [];
  for (let i = 0; i < data.length; i++) {
    if (i < period - 1) {
      middle.push({ time: data[i].time, value: data[i].close });
      upper.push({ time: data[i].time, value: data[i].close });
      lower.push({ time: data[i].time, value: data[i].close });
      continue;
    }
    let sum = 0;
    for (let j = 0; j < period; j++) {
      sum += data[i - j].close;
    }
    const mean = sum / period;
    let variance = 0;
    for (let j = 0; j < period; j++) {
      variance += Math.pow(data[i - j].close - mean, 2);
    }
    const stdDev = Math.sqrt(variance / period);
    middle.push({ time: data[i].time, value: mean });
    upper.push({ time: data[i].time, value: mean + multiplier * stdDev });
    lower.push({ time: data[i].time, value: mean - multiplier * stdDev });
  }
  return { upper, middle, lower };
}

function calcRSI(data, period = 14) {
  const rsi = [];
  if (data.length < period) return [];
  
  let gains = 0;
  let losses = 0;
  
  for (let i = 1; i <= period; i++) {
    const diff = data[i].close - data[i - 1].close;
    if (diff > 0) gains += diff;
    else losses -= diff;
  }
  
  let avgGain = gains / period;
  let avgLoss = losses / period;
  let rs = avgGain / (avgLoss || 1e-10);
  rsi.push({ time: data[period].time, value: 100 - (100 / (1 + rs)) });
  
  for (let i = period + 1; i < data.length; i++) {
    const diff = data[i].close - data[i - 1].close;
    const gain = diff > 0 ? diff : 0;
    const loss = diff < 0 ? -diff : 0;
    
    avgGain = (avgGain * (period - 1) + gain) / period;
    avgLoss = (avgLoss * (period - 1) + loss) / period;
    rs = avgGain / (avgLoss || 1e-10);
    rsi.push({ time: data[i].time, value: 100 - (100 / (1 + rs)) });
  }
  return rsi;
}

function calcMACD(data, fast = 12, slow = 26, signal = 9) {
  const emaFast = calcEMA(data, fast);
  const emaSlow = calcEMA(data, slow);
  
  const macdLine = [];
  for (let i = 0; i < data.length; i++) {
    const fVal = emaFast[i]?.value ?? data[i].close;
    const sVal = emaSlow[i]?.value ?? data[i].close;
    macdLine.push({ time: data[i].time, value: fVal - sVal });
  }
  
  const signalLine = [];
  const k = 2 / (signal + 1);
  let prevEma = macdLine[0].value;
  signalLine.push({ time: macdLine[0].time, value: prevEma });
  for (let i = 1; i < macdLine.length; i++) {
    const val = macdLine[i].value * k + prevEma * (1 - k);
    signalLine.push({ time: macdLine[i].time, value: val });
    prevEma = val;
  }
  
  const histogram = [];
  for (let i = 0; i < macdLine.length; i++) {
    histogram.push({
      time: macdLine[i].time,
      value: macdLine[i].value - (signalLine[i]?.value || 0)
    });
  }
  
  return { macdLine, signalLine, histogram };
}