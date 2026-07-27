import { API_BASE_URL, apiFetch } from './api';
import { Plus, Minus, Info, AlertTriangle, Link, Link2Off, RefreshCw, Layers, Crosshair, TrendingUp, X } from 'lucide-react';
import { calcEMA, calcBollingerBands, calcRSI, calcMACD } from './utils/indicators';
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { createChart, CandlestickSeries, LineSeries, HistogramSeries, createSeriesMarkers } from 'lightweight-charts';
import { useHistory, useLivePrices, isNSEMarketOpen } from './hooks/useMarketData';
import SignalsPanel from './SignalsPanel';
import IntroSplash from './IntroSplash';
import LoginScreen from './LoginScreen';
import AccountPanel from './AccountPanel';
import OrderBookPanel from './OrderBookPanel';
import HomePanel from './HomePanel';
import PredictionsPanel from './PredictionsPanel';
import JournalPanel from './JournalPanel';
import SimulatorPanel from './SimulatorPanel';
import PerformancePanel from './PerformancePanel';
import BotControlPanel from './BotControlPanel';
import TradeLogPanel from './TradeLogPanel';
import StrategySelector from './StrategySelector';
import BacktestRunner from './BacktestRunner';
import { PanelErrorBoundary } from './PanelErrorBoundary';


const EMPTY_ARRAY = [];

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
  goldDim:    'rgba(245,200,66,0.1)',
  goldGlow:   'rgba(245,200,66,0.25)',
  accent:     '#7b6cff',
  accentAlt:  '#9b5de5',
  accentDim:  'rgba(123,108,255,0.12)',
  accentGlow: 'rgba(123,108,255,0.3)',
};

// ── NSE Watchlist ────────────────────────────────────────────────────────────────
const DEFAULT_WATCHLIST = [
  { symbol: 'YESBANK.NS',    name: 'Yes Bank',       sector: 'Banking' },
  { symbol: 'TATASTEEL.NS',  name: 'Tata Steel',     sector: 'Metals' },
  { symbol: 'BANKBARODA.NS', name: 'Bank of Baroda', sector: 'Banking' },
  { symbol: 'TATAPOWER.NS',  name: 'Tata Power',     sector: 'Power' },
  { symbol: 'SBIN.NS',       name: 'SBI',            sector: 'Banking' },
];

const SEED_PRICES = {
  'YESBANK.NS': 25, 'TATASTEEL.NS': 170, 'BANKBARODA.NS': 280,
  'TATAPOWER.NS': 445, 'SBIN.NS': 830
};

const INTERVALS = [
  { label: '1D',  interval: '30m', range: '1d' },
  { label: '1W',  interval: '30m', range: '5d' },
  { label: '1M',  interval: '1d',  range: '1mo' },
  { label: '3M',  interval: '1d',  range: '3mo' },
  { label: '1Y',  interval: '1wk', range: '1y' },
  { label: 'ALL', interval: '1mo', range: 'max' },
];

const PORTFOLIO = [
  { symbol: 'HAL.NS',  shares: 5,  avgCost: 4400 },
  { symbol: 'BEL.NS',  shares: 50, avgCost: 280 },
  { symbol: 'RVNL.NS', shares: 40, avgCost: 350 },
];

// ── Helpers ───────────────────────────────────────────────────────────────────
const fmt  = (n, d = 2) => n == null ? '—' : Number(n).toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });
const fmtK = (n) => n >= 1e9 ? `₹${(n/1e9).toFixed(2)}B` : n >= 1e6 ? `₹${(n/1e6).toFixed(1)}M` : `₹${fmt(n, 0)}`;
const clr  = (v) => v > 0 ? T.green : v < 0 ? T.red : T.textMid;
const sign = (v) => v > 0 ? '+' : '';
const escapeHTML = (str) => String(str).replace(/[&<>'"]/g, tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag));

// ── Candlestick Chart (with volume and indicators) ────────────────────────
function CandleChart({ symbol, interval, range, indicators, livePrice, markers, onLastBarUpdate, drawMode, onDrawComplete, customLines = [], botPaperMode }) {
  const mainContainerRef = useRef();
  const legendRef = useRef();
  const rsiContainerRef = useRef();
  const macdContainerRef = useRef();
  
  const mainChartRef = useRef();
  const rsiChartRef = useRef();
  const macdChartRef = useRef();

  const candleSeriesRef = useRef();
  const volSeriesRef = useRef();
  const liveTickRef = useRef();
  const seriesMarkersRef = useRef();
  
  const { bars, loading, error } = useHistory(symbol, { interval, range, seedPrice: SEED_PRICES[symbol] });

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

    // Watermark removed to prevent chart crash

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

    // Initialize markers in v5
    seriesMarkersRef.current = createSeriesMarkers(candleSeries, markers || []);

    mainChart.subscribeCrosshairMove((param) => {
      const legend = legendRef.current;
      if (!legend) return;
      if (!param.time || !param.point || param.point.x < 0 || param.point.y < 0) {
        legend.style.display = 'none';
        return;
      }
      const data = param.seriesData.get(candleSeries);
      if (data) {
        legend.style.display = 'block';
        const color = data.close >= data.open ? T.green : T.red;
        legend.innerHTML = `
          <div style="font-weight: 700; margin-bottom: 4px; color: ${T.text}; font-size: 14px;">${escapeHTML(symbol)} <span style="color: ${T.textMid}; font-size: 11px;">(${escapeHTML(interval)})</span></div>
          <div style="display: flex; gap: 14px; font-size: 12px; color: ${T.text};">
            <span>O <span style="color: ${color}">${data.open.toFixed(2)}</span></span>
            <span>H <span style="color: ${color}">${data.high.toFixed(2)}</span></span>
            <span>L <span style="color: ${color}">${data.low.toFixed(2)}</span></span>
            <span>C <span style="color: ${color}">${data.close.toFixed(2)}</span></span>
          </div>
        `;
      } else {
        legend.style.display = 'none';
      }
    });

    mainChart.subscribeClick((param) => {
      if (!param.point || !drawMode) return;
      const price = candleSeries.coordinateToPrice(param.point.y);
      if (price !== null && onDrawComplete) {
        onDrawComplete({ price, type: drawMode, id: Date.now() });
      }
    });

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

    // Custom Drawing Lines
    customLines.forEach(line => {
      candleSeries.createPriceLine({
        price: line.price,
        color: line.type === 'SUPPORT' ? T.green : T.red,
        lineWidth: 2,
        lineStyle: 1, // solid
        axisLabelVisible: true,
        title: line.type === 'SUPPORT' ? 'SUP' : 'RES',
      });
    });

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
      seriesMarkersRef.current = null;
    };
  }, [bars, loading, indicators]);

  // Live tick updates to the last bar on the chart!
  useEffect(() => {
    if (!livePrice || !bars.length || !candleSeriesRef.current) return;
    const lastBar = bars[bars.length - 1];
    if (!lastBar) return;
    
    const price = livePrice.price;
    
    // Reset tracking if the base bar time changes
    if (!liveTickRef.current || liveTickRef.current.time !== lastBar.time) {
      liveTickRef.current = {
        time: lastBar.time,
        open: lastBar.open,
        high: lastBar.high,
        low: lastBar.low,
        close: lastBar.close,
        volume: lastBar.volume || 0
      };
    }

    // Accumulate the extremes dynamically
    liveTickRef.current.high = Math.max(liveTickRef.current.high, price);
    liveTickRef.current.low = Math.min(liveTickRef.current.low, price);
    liveTickRef.current.close = price;
    
    candleSeriesRef.current.update(liveTickRef.current);
    
    if (volSeriesRef.current) {
      volSeriesRef.current.update({
        time: liveTickRef.current.time,
        value: liveTickRef.current.volume,
        color: liveTickRef.current.close >= liveTickRef.current.open ? 'rgba(0,216,160,0.22)' : 'rgba(255,78,106,0.22)',
      });
    }
  }, [livePrice, bars]);

  // Set markers when they change or bars load
  useEffect(() => {
    if (seriesMarkersRef.current && !loading) {
      seriesMarkersRef.current.setMarkers(markers || []);
    }
  }, [markers, loading, bars]);

  // Update parent with the last bar time for marker timestamps
  useEffect(() => {
    if (bars && bars.length > 0 && onLastBarUpdate) {
      onLastBarUpdate(bars[bars.length - 1].time);
    }
  }, [bars, onLastBarUpdate]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, height: '100%', minHeight: 0, overflow: 'hidden', position: 'relative' }}>
      {loading && (
        <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(10,12,16,0.7)', zIndex: 2, gap: 10, color: T.textMid, fontSize: 13, letterSpacing: '0.05em' }}>
          <span style={{ display: 'inline-block', width: 14, height: 14, border: `2px solid ${T.border}`, borderTopColor: T.accent, borderRadius: '50%', animation: 'spin 0.7s linear infinite' }} />
          LOADING MARKET DATA
        </div>
      )}

      {!loading && error && (
        <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', background: 'rgba(10,12,16,0.9)', zIndex: 2, gap: 12, color: T.red, fontSize: 13, letterSpacing: '0.05em', padding: 20, textAlign: 'center' }}>
          <span style={{ fontSize: 24 }}>⚠️</span>
          <div style={{ fontWeight: 600 }}>ERROR LOADING MARKET DATA: {error}</div>
          <div style={{ fontSize: 11, color: T.textDim, marginTop: 4, maxWidth: 300, lineHeight: 1.4 }}>
            Live market data unavailable. Please go to the <strong>ACCOUNT</strong> panel to authenticate with <strong>AngelOne Broker</strong>.
          </div>
        </div>
      )}

      {!loading && !error && !bars.length && (
        <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', background: 'rgba(10,12,16,0.9)', zIndex: 2, gap: 12, color: T.textMid, fontSize: 13, letterSpacing: '0.05em' }}>
          <span style={{ fontSize: 24 }}>📭</span>
          <div style={{ fontWeight: 600 }}>NO HISTORICAL DATA FOUND FOR {symbol}</div>
        </div>
      )}
      
      {/* Main Chart Container */}
      <div style={{ flex: 3, minHeight: 0, position: 'relative' }}>
        <div ref={legendRef} style={{ position: 'absolute', top: 12, left: 12, zIndex: 10, fontFamily: "'IBM Plex Mono', monospace", pointerEvents: 'none', background: 'rgba(13,16,24,0.65)', backdropFilter: 'blur(4px)', padding: '8px 12px', borderRadius: 6, display: 'none', border: `1px solid ${T.borderHi}` }} />
        
        {botPaperMode === true && (
          <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', zIndex: 1, pointerEvents: 'none', color: 'rgba(255, 255, 255, 0.05)', fontSize: '8vw', fontWeight: 900, whiteSpace: 'nowrap', userSelect: 'none' }}>
            SIMULATION MODE
          </div>
        )}
        
        {botPaperMode === false && (
          <div style={{ position: 'absolute', top: 12, right: 12, zIndex: 10, background: T.red, color: '#fff', fontSize: 11, fontWeight: 800, padding: '4px 8px', borderRadius: 4, letterSpacing: '0.05em' }}>
            LIVE BROKER
          </div>
        )}
        
        <div ref={mainContainerRef} style={{ position: 'absolute', inset: 0, zIndex: 2 }} />
      </div>
      
      {/* RSI Container */}
      {indicators.rsi && (
        <div style={{ height: 95, borderTop: `1px solid ${T.border}`, position: 'relative', background: T.surface, flexShrink: 0 }}>
          <div style={{ position: 'absolute', top: 4, left: 12, zIndex: 5, fontSize: 9, color: T.textMid, fontFamily: "'IBM Plex Mono', monospace", fontWeight: 700 }}>
            RSI (14)
          </div>
          <div ref={rsiContainerRef} style={{ position: 'absolute', inset: 0 }} />
        </div>
      )}

      {/* MACD Container */}
      {indicators.macd && (
        <div style={{ height: 110, borderTop: `1px solid ${T.border}`, position: 'relative', background: T.surface, flexShrink: 0 }}>
          <div style={{ position: 'absolute', top: 4, left: 12, zIndex: 5, fontSize: 9, color: T.textMid, fontFamily: "'IBM Plex Mono', monospace", fontWeight: 700 }}>
            MACD (12, 26, 9)
          </div>
          <div ref={macdContainerRef} style={{ position: 'absolute', inset: 0 }} />
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
      <div style={{ display: 'flex', gap: 0, padding: '0 40px', animation: 'marquee 120s linear infinite', whiteSpace: 'nowrap' }}>
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
function WatchlistPanel({ prices, selected, onSelect, favorites = [], onToggleFavorite }) {
  const [searchQuery, setSearchQuery] = useState('');

  const filteredList = DEFAULT_WATCHLIST.filter(w => 
    w.symbol.toLowerCase().includes(searchQuery.toLowerCase()) ||
    w.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (w.sector && w.sector.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  const sortedList = [...filteredList].sort((a, b) => {
    const aFav = favorites.includes(a.symbol);
    const bFav = favorites.includes(b.symbol);
    if (aFav && !bFav) return -1;
    if (!aFav && bFav) return 1;
    return 0;
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <div style={{ padding: '12px 14px 8px', borderBottom: `1px solid ${T.border}`, display: 'flex', flexDirection: 'column', gap: 8 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.12em', color: T.textMid }}>WATCHLIST</span>
          <span style={{ fontSize: 9, color: T.textDim, fontFamily: "'IBM Plex Mono', monospace" }}>{sortedList.length} SYMBOLS</span>
        </div>
        {/* Search Input */}
        <input 
          type="text"
          placeholder="🔍 Search watchlist..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          style={{
            width: '100%',
            background: T.bg,
            border: `1px solid ${T.border}`,
            borderRadius: 6,
            color: T.text,
            fontSize: 11,
            padding: '5px 8px',
            outline: 'none',
            transition: 'border-color 0.2s',
          }}
          onFocus={(e) => e.target.style.borderColor = T.accent}
          onBlur={(e) => e.target.style.borderColor = T.border}
        />
      </div>
      <div style={{ flex: 1, overflowY: 'auto' }}>
        {sortedList.length === 0 ? (
          <div style={{ padding: '20px 14px', fontSize: 11, color: T.textDim, textAlign: 'center' }}>No matching symbols</div>
        ) : (
          sortedList.map(({ symbol, name, sector }) => {
            const p     = prices[symbol];
            const price = p?.price ?? SEED_PRICES[symbol] ?? 0;
            const pct   = p?.changePct ?? 0;
            const isUp  = pct >= 0;
            const isSel = selected === symbol;
            const isFav = favorites.includes(symbol);
            return (
              <div key={symbol}
                onClick={() => onSelect(symbol)}
                style={{
                  padding: '10px 14px', cursor: 'pointer', transition: 'background 0.15s',
                  background: isSel ? T.blueDim : 'transparent',
                  borderLeft: `2px solid ${isSel ? T.blue : 'transparent'}`,
                  borderBottom: `1px solid ${T.border}`,
                  position: 'relative',
                }}
                onMouseEnter={e => !isSel && (e.currentTarget.style.background = 'rgba(255,255,255,0.02)')}
                onMouseLeave={e => !isSel && (e.currentTarget.style.background = 'transparent')}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div style={{ minWidth: 0, flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      {/* Favorite Button */}
                      <button 
                        onClick={(e) => { e.stopPropagation(); onToggleFavorite(symbol); }}
                        style={{
                          background: 'none',
                          border: 'none',
                          cursor: 'pointer',
                          padding: 0,
                          fontSize: 12,
                          color: isFav ? T.gold : T.textDim,
                          display: 'flex',
                          alignItems: 'center',
                        }}
                      >
                        {isFav ? '★' : '☆'}
                      </button>
                      <div style={{ fontSize: 11, fontWeight: 700, color: isSel ? T.blue : T.text, letterSpacing: '0.02em', fontFamily: "'IBM Plex Mono', monospace", overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {symbol.replace('.NS', '')}
                      </div>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 4 }}>
                      <span style={{ fontSize: 9, color: T.textDim }}>{name}</span>
                      {sector && (
                        <span style={{ fontSize: 8, background: 'rgba(255,255,255,0.04)', color: T.textMid, padding: '1px 4px', borderRadius: 3, fontWeight: 600 }}>
                          {sector}
                        </span>
                      )}
                    </div>
                  </div>
                  <div style={{ textAlign: 'right', flexShrink: 0 }}>
                    <div style={{ fontSize: 11, color: T.text, fontFamily: "'IBM Plex Mono', monospace" }}>₹{fmt(price)}</div>
                    <div style={{ fontSize: 9, color: clr(pct), marginTop: 4, background: isUp ? T.greenDim : T.redDim, padding: '1px 4px', borderRadius: 3, fontFamily: "'IBM Plex Mono', monospace", display: 'inline-block' }}>
                      {sign(pct)}{fmt(pct, 2)}%
                    </div>
                  </div>
                </div>
              </div>
            );
          })
        )}
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

  // Donut chart calculation
  const C = 157.08; // Circumference for R=25
  const slices = [];
  let accumulatedWeight = 0;

  if (totalValue > 0) {
    const cashWeight = cash / totalValue;
    slices.push({
      label: 'Cash',
      value: cash,
      color: T.blue,
      weight: cashWeight,
      dashOffset: C - (accumulatedWeight * C),
    });
    accumulatedWeight += cashWeight;
  }

  const COLORS = ['#7b6cff', '#00e5a8', '#ff9f43', '#9b5de5', '#f5c842', '#ff3d5a', '#ff4da6'];
  positions.forEach((pos, idx) => {
    if (totalValue > 0 && pos.value > 0) {
      const weight = pos.value / totalValue;
      slices.push({
        label: pos.symbol.replace('.NS', ''),
        value: pos.value,
        color: COLORS[idx % COLORS.length],
        weight,
        dashOffset: C - (accumulatedWeight * C),
      });
      accumulatedWeight += weight;
    }
  });

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
      {/* Allocation Donut Chart */}
      {slices.length > 0 && (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '12px 16px', borderBottom: `1px solid ${T.border}`, gap: 20, background: 'rgba(255,255,255,0.005)' }}>
          <svg width="68" height="68" viewBox="0 0 80 80" style={{ transform: 'rotate(-90deg)', flexShrink: 0 }}>
            {/* Background circle */}
            <circle cx="40" cy="40" r="25" stroke={T.borderHi} strokeWidth="8" fill="transparent" />
            {slices.map((slice, idx) => (
              <circle
                key={idx}
                cx="40"
                cy="40"
                r="25"
                stroke={slice.color}
                strokeWidth="8"
                fill="transparent"
                strokeDasharray={`${slice.weight * C} ${C}`}
                strokeDashoffset={-slice.dashOffset + C}
                style={{ transition: 'stroke-dashoffset 0.6s ease' }}
              />
            ))}
          </svg>
          {/* Mini Legend */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4, flex: 1, minWidth: 0 }}>
            {slices.map((slice, idx) => (
              <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 9, fontFamily: "'IBM Plex Mono', monospace" }}>
                <span style={{ width: 6, height: 6, borderRadius: '50%', background: slice.color, display: 'inline-block', flexShrink: 0 }} />
                <span style={{ color: T.textMid, flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{slice.label}</span>
                <span style={{ color: T.text, fontWeight: 600, flexShrink: 0 }}>{(slice.weight * 100).toFixed(0)}%</span>
              </div>
            ))}
          </div>
        </div>
      )}
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
function OrderPanel({ symbol, price, cash, openOrders, onExecuteOrder, onCancelOrder, priceAlerts = [], onAddAlert, onDeleteAlert, hideLists = false }) {
  const [side, setSide]     = useState('buy');
  const [qty, setQty]       = useState('');
  const [type, setType]     = useState('market');
  const [limit, setLimit]   = useState('');
  const [status, setStatus] = useState(null);

  const [alertCondition, setAlertCondition] = useState('above');
  const [alertPrice, setAlertPrice] = useState('');

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
        <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.12em', color: T.textMid }}>ORDER ENTRY</span>
        <span style={{ fontSize: 9, color: T.textDim, fontFamily: "'IBM Plex Mono', monospace" }}>CASH: ₹{fmt(cash)}</span>
      </div>

      {/* Buy/Sell toggle */}
      <div style={{ display: 'flex', background: T.bg, borderRadius: 6, padding: 3, border: `1px solid ${T.border}` }}>
        {['buy','sell'].map(s => (
          <button key={s} onClick={() => setSide(s)} style={{
            flex: 1, padding: '7px 0', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 700,
            letterSpacing: '0.08em', fontFamily: "'Inter', sans-serif", transition: 'all 0.2s',
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
            color: type === t ? T.accent : T.textMid, fontFamily: "'Inter', sans-serif", letterSpacing: '0.06em',
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
        fontFamily: "'Inter', sans-serif", opacity: qty ? 1 : 0.4, transition: 'opacity 0.2s',
      }}>
        {status === 'placing' ? 'PLACING...' : `${side.toUpperCase()} ${symbol.replace('.NS', '')}`}
      </button>

      {/* Open Limit Orders List */}
      {!hideLists && openOrders && openOrders.length > 0 && (
        <div style={{ marginTop: 10, borderTop: `1px solid ${T.border}`, paddingTop: 10 }}>
          <div style={{ fontSize: 9, fontWeight: 700, letterSpacing: '0.12em', color: T.textMid, marginBottom: 6 }}>
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
                    color: T.red, fontSize: 8, fontWeight: 700, cursor: 'pointer', fontFamily: "'Inter', sans-serif",
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

      {/* Price Alerts Form */}
      <div style={{ marginTop: 10, borderTop: `1px solid ${T.border}`, paddingTop: 10 }}>
        <div style={{ fontSize: 9, fontWeight: 700, letterSpacing: '0.12em', color: T.textMid, marginBottom: 8 }}>
          ⏰ PRICE ALERTS
        </div>
        <div style={{ display: 'flex', gap: 6, alignItems: 'center', marginBottom: 8 }}>
          <select 
            value={alertCondition}
            onChange={e => setAlertCondition(e.target.value)}
            style={{
              flex: 1.2,
              background: T.bg,
              border: `1px solid ${T.border}`,
              borderRadius: 4,
              color: T.text,
              fontSize: 10,
              padding: '4px',
              height: 28,
              outline: 'none',
              fontFamily: "'Inter', sans-serif"
            }}
          >
            <option value="above">Crosses Above (≥)</option>
            <option value="below">Drops Below (≤)</option>
          </select>
          <div style={{ flex: 1.5, position: 'relative' }}>
            <span style={{ position: 'absolute', left: 6, top: 7, fontSize: 9, color: T.textDim }}>₹</span>
            <input 
              type="number" 
              value={alertPrice}
              onChange={e => setAlertPrice(e.target.value)}
              placeholder={price ? price.toFixed(0) : "0"} 
              style={{
                width: '100%',
                background: T.bg,
                border: `1px solid ${T.border}`,
                borderRadius: 4,
                color: T.text,
                fontSize: 10,
                padding: '4px 4px 4px 14px',
                height: 28,
                outline: 'none',
                fontFamily: "'IBM Plex Mono', monospace"
              }}
            />
          </div>
          <button
            onClick={() => {
              if (!alertPrice || isNaN(parseFloat(alertPrice)) || parseFloat(alertPrice) <= 0) {
                alert("Please enter a valid target price!");
                return;
              }
              onAddAlert(symbol, alertCondition, parseFloat(alertPrice));
              setAlertPrice('');
            }}
            style={{
              padding: '0 10px',
              height: 28,
              background: T.accent,
              border: 'none',
              borderRadius: 4,
              color: '#fff',
              fontSize: 9,
              fontWeight: 700,
              cursor: 'pointer',
              fontFamily: "'Inter', sans-serif"
            }}
          >
            SET
          </button>
        </div>

        {/* List of active alerts for this symbol */}
        {!hideLists && priceAlerts && priceAlerts.filter(a => a.symbol === symbol).length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginTop: 6 }}>
            {priceAlerts.filter(a => a.symbol === symbol).map(a => (
              <div key={a.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: T.bg, border: `1px solid ${T.border}`, padding: '4px 8px', borderRadius: 4, fontSize: 9, fontFamily: "'IBM Plex Mono', monospace" }}>
                <span style={{ color: a.condition === 'above' ? T.green : T.red }}>
                  {a.condition === 'above' ? '≥' : '≤'} ₹{fmt(a.targetPrice, 1)}
                </span>
                <button 
                  onClick={() => onDeleteAlert(a.id)}
                  style={{ background: 'none', border: 'none', color: T.red, cursor: 'pointer', fontSize: 8, fontWeight: 700, fontFamily: "'Inter', sans-serif" }}
                >
                  REMOVE
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

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
      const res = await apiFetch('/api/chat', {
        method: 'POST',
        body: JSON.stringify({
          message: userMsg,
          context: { symbol: symbol.replace('.NS', ''), price, changePct },
          history: msgs.map(m => ({ role: m.role, text: m.text }))
        }),
      });
      if (res.status === 401) {
        localStorage.removeItem('is_logged_in');
        localStorage.removeItem('apex_user');
        localStorage.removeItem('apt_token');
        sessionStorage.removeItem('apt_token');
        window.location.reload();
        return;
      }
      if (!res.ok) throw new Error('backend unavailable');
      const data = await res.json();
      setAiSource(data.source);
      setMsgs(m => [...m, { role: 'assistant', text: data.reply || 'No response.' }]);
    } catch {
      setMsgs(m => [...m, { role: 'assistant', text: "AI Mentor is currently unavailable. Please check backend connection." }]);
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
function Header({ connected, view, onViewChange, isMobile, onLogout, netWorth, cash, stockValue, totalPnl, totalPct, selectedSymbol, prices }) {
  const [clock, setClock] = useState(() => new Date().toLocaleTimeString('en-IN', { hour12: true }));
  useEffect(() => {
    const t = setInterval(() => setClock(new Date().toLocaleTimeString('en-IN', { hour12: true })), 1000);
    return () => clearInterval(t);
  }, []);

  const [showMore, setShowMore] = useState(false);

  const p = prices[selectedSymbol];
  const price = p?.price ?? SEED_PRICES[selectedSymbol] ?? 0;
  const pct = p?.changePct ?? 0;
  const isUp = pct >= 0;

  return (
    <div style={{ padding: '0 16px', height: 54, display: 'flex', alignItems: 'center', gap: 16, borderBottom: `1px solid ${T.border}`, background: T.surface, flexShrink: 0 }}>
      {/* Logo */}
      <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 13, fontWeight: 700, letterSpacing: '0.12em', whiteSpace: 'nowrap', background: `linear-gradient(135deg, ${T.accent}, ${T.accentAlt})`, WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', flexShrink: 0 }}>
        ◈ ApexTrade Bot Engine
      </div>

      {/* View switcher — primary tabs (desktop) + collapsed secondary "More" menu */}
      {!isMobile && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <div style={{ display: 'flex', background: T.bg, borderRadius: 6, padding: 2, border: `1px solid ${T.border}`, flexShrink: 0 }}>
            {PRIMARY_TABS.map(v => {
              const meta = TAB_META[v] || { icon: '', label: v };
              const isActive = view === v;
              return (
                <button key={v} onClick={() => onViewChange(v)} style={{
                  padding: '4px 12px', borderRadius: 4, border: 'none', cursor: 'pointer',
                  background: isActive ? T.accentDim : 'transparent',
                  color: isActive ? T.accentAlt : T.textDim,
                  fontSize: 9, fontWeight: 700, letterSpacing: '0.08em',
                  fontFamily: "'Inter', sans-serif", transition: 'all 0.2s',
                }}>{meta.icon} {meta.label}</button>
              );
            })}
          </div>

          {SECONDARY_TABS.length > 0 && (
            <div style={{ position: 'relative' }}>
              <button onClick={() => setShowMore(s => !s)} style={{
                padding: '4px 10px', borderRadius: 6, border: `1px solid ${T.border}`, background: T.bg, cursor: 'pointer',
                color: SECONDARY_TABS.some(t => view === t) ? T.accentAlt : T.textDim,
                fontSize: 9, fontWeight: 700, letterSpacing: '0.08em', fontFamily: "'Inter', sans-serif",
              }}>⋯ MORE</button>
              {showMore && (
                <>
                  <div onClick={() => setShowMore(false)} style={{ position: 'fixed', inset: 0, zIndex: 99 }} />
                  <div style={{ position: 'absolute', top: '100%', right: 0, marginTop: 6, background: T.surface, border: `1px solid ${T.border}`, borderRadius: 8, padding: 4, zIndex: 100, minWidth: 150, boxShadow: '0 8px 24px rgba(0,0,0,0.5)' }}>
                    {SECONDARY_TABS.map(v => {
                      const meta = TAB_META[v] || { icon: '', label: v };
                      const isActive = view === v;
                      return (
                        <button key={v} onClick={() => { onViewChange(v); setShowMore(false); }} style={{
                          display: 'block', width: '100%', textAlign: 'left', padding: '8px 10px', borderRadius: 6, border: 'none', cursor: 'pointer',
                          background: isActive ? T.accentDim : 'transparent',
                          color: isActive ? T.accentAlt : T.text,
                          fontSize: 10, fontWeight: 700, fontFamily: "'Inter', sans-serif",
                        }}>{meta.icon} {meta.label}</button>
                      );
                    })}
                  </div>
                </>
              )}
            </div>
          )}
        </div>
      )}

      <div style={{ width: 1, height: 22, background: T.border, flexShrink: 0 }} />

      {/* Active Symbol Price Quote — Display ONLY on Chart View */}
      {!isMobile && view === 'CHART' && selectedSymbol && (
        <>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, minWidth: 0, flexShrink: 0 }}>
            <span style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, fontWeight: 700, color: T.textMid, letterSpacing: '0.06em' }}>
              {selectedSymbol.replace('.NS', '')}
            </span>
            <span style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 18, fontWeight: 700, color: T.text, letterSpacing: '-0.02em' }}>
              ₹{fmt(price)}
            </span>
            <span style={{
              fontSize: 10,
              color: clr(pct),
              background: isUp ? T.greenDim : T.redDim,
              border: `1px solid ${isUp ? T.greenGlow : T.redGlow}`,
              padding: '1px 6px',
              borderRadius: 4,
              fontFamily: "'IBM Plex Mono', monospace"
            }}>
              {sign(pct)}{fmt(pct, 2)}%
            </span>
          </div>
          <div style={{ width: 1, height: 22, background: T.border, flexShrink: 0 }} />
        </>
      )}

      {/* Account Balances Summary */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, minWidth: 0 }}>
        {/* Net Worth */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <span style={{ fontSize: 8, fontWeight: 700, color: T.textDim, letterSpacing: '0.04em' }}>PORTFOLIO VALUE</span>
          <span style={{ fontSize: 13, fontWeight: 700, color: '#fff', fontFamily: "'IBM Plex Mono', monospace" }}>
            ₹{fmt(netWorth)}
          </span>
        </div>

        {/* Total P&L */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <span style={{ fontSize: 8, fontWeight: 700, color: T.textDim, letterSpacing: '0.04em' }}>TOTAL P&L</span>
          <span style={{ fontSize: 11, fontWeight: 700, color: clr(totalPnl), fontFamily: "'IBM Plex Mono', monospace" }}>
            {sign(totalPnl)}₹{fmt(Math.abs(totalPnl))} ({sign(totalPct)}{fmt(totalPct, 2)}%)
          </span>
        </div>

        {!isMobile && (
          <>
            <div style={{ width: 1, height: 20, background: T.border, flexShrink: 0 }} />

            {/* Available Cash */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <span style={{ fontSize: 8, fontWeight: 700, color: T.textDim, letterSpacing: '0.04em' }}>AVAILABLE CASH</span>
              <span style={{ fontSize: 11, fontWeight: 700, color: T.blue, fontFamily: "'IBM Plex Mono', monospace" }}>
                ₹{fmt(cash)}
              </span>
            </div>

            {/* Stock Holdings */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <span style={{ fontSize: 8, fontWeight: 700, color: T.textDim, letterSpacing: '0.04em' }}>STOCKS HOLDINGS</span>
              <span style={{ fontSize: 11, fontWeight: 700, color: T.textMid, fontFamily: "'IBM Plex Mono', monospace" }}>
                ₹{fmt(stockValue)}
              </span>
            </div>
          </>
        )}
      </div>

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

// ── Bottom Console Tray (desktop-friendly) ───────────────────────────────────
function BottomConsole({ prices, portfolio, cash, openOrders, onCancelOrder, priceAlerts, onDeleteAlert, aiRecommendation, aiRecommendationLoading, selected, onExecuteOrder, onViewChange, consoleTab, setConsoleTab, onRefreshAnalyst }) {

  const totalStockValue = portfolio.reduce((sum, pos) => {
    const price = prices[pos.symbol]?.price ?? SEED_PRICES[pos.symbol] ?? pos.avgCost;
    return sum + (price * pos.shares);
  }, 0);
  const netWorth = totalStockValue + cash;

  return (
    <div style={{ height: 220, borderTop: `1px solid ${T.border}`, background: T.surface, display: 'flex', flexDirection: 'column', flexShrink: 0, overflow: 'hidden' }}>
      {/* Console Header */}
      <div style={{ display: 'flex', alignItems: 'center', borderBottom: `1px solid ${T.border}`, background: T.panelAlt, flexShrink: 0, padding: '0 16px', height: 38 }}>
        <div style={{ display: 'flex', gap: 2 }}>
          {[['POSITIONS', '💼 POSITIONS'], ['ORDERS', '⏳ OPEN ORDERS'], ['ALERTS', '🔔 PRICE ALERTS'], ['AI', '💡 AI ANALYST']].map(([tab, label]) => (
            <button
              key={tab}
              onClick={() => setConsoleTab(tab)}
              style={{
                padding: '0 12px',
                background: 'transparent',
                border: 'none',
                cursor: 'pointer',
                color: consoleTab === tab ? T.accent : T.textMid,
                fontSize: 9.5,
                fontWeight: 700,
                letterSpacing: '0.04em',
                fontFamily: "'Inter', sans-serif",
                borderBottom: `2px solid ${consoleTab === tab ? T.accent : 'transparent'}`,
                height: 38,
                transition: 'all 0.15s'
              }}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Small stats on the right side of header */}
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 16, fontSize: 10, fontFamily: "'IBM Plex Mono', monospace" }}>
          <div>
            <span style={{ color: T.textDim }}>NET WORTH:</span> <strong style={{ color: '#fff' }}>₹{fmt(netWorth)}</strong>
          </div>
          <div>
            <span style={{ color: T.textDim }}>CASH:</span> <strong style={{ color: T.blue }}>₹{fmt(cash)}</strong>
          </div>
        </div>
      </div>

      {/* Console Body */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '12px 16px', position: 'relative' }}>
        {consoleTab === 'POSITIONS' && (
          <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            {portfolio.length === 0 ? (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flex: 1, color: T.textDim, fontSize: 11, fontFamily: "'IBM Plex Mono', monospace" }}>
                NO ACTIVE POSITIONS HELD
              </div>
            ) : (
              <div style={{ flex: 1, overflowY: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: 11 }}>
                  <thead>
                    <tr style={{ color: T.textDim, borderBottom: `1px solid ${T.border}` }}>
                      <th style={{ paddingBottom: 6, fontWeight: 700 }}>SYMBOL</th>
                      <th style={{ paddingBottom: 6, fontWeight: 700 }}>SHARES</th>
                      <th style={{ paddingBottom: 6, fontWeight: 700 }}>AVG COST</th>
                      <th style={{ paddingBottom: 6, fontWeight: 700 }}>LAST PRICE</th>
                      <th style={{ paddingBottom: 6, fontWeight: 700 }}>MARKET VALUE</th>
                      <th style={{ paddingBottom: 6, fontWeight: 700 }}>P&L</th>
                      <th style={{ paddingBottom: 6, fontWeight: 700, textAlign: 'right' }}>ACTION</th>
                    </tr>
                  </thead>
                  <tbody>
                    {portfolio.map(pos => {
                      const price = prices[pos.symbol]?.price ?? SEED_PRICES[pos.symbol] ?? pos.avgCost;
                      const value = price * pos.shares;
                      const cost = pos.avgCost * pos.shares;
                      const pnl = value - cost;
                      const pnlPct = cost > 0 ? (pnl / cost) * 100 : 0;
                      return (
                        <tr key={pos.symbol} style={{ borderBottom: `1px solid ${T.border}` }}>
                          <td style={{ padding: '8px 0', fontWeight: 700, color: '#fff', fontFamily: "'IBM Plex Mono', monospace" }}>{pos.symbol.replace('.NS', '')}</td>
                          <td style={{ padding: '8px 0', fontFamily: "'IBM Plex Mono', monospace" }}>{pos.shares}</td>
                          <td style={{ padding: '8px 0', fontFamily: "'IBM Plex Mono', monospace" }}>₹{fmt(pos.avgCost)}</td>
                          <td style={{ padding: '8px 0', fontFamily: "'IBM Plex Mono', monospace" }}>₹{fmt(price)}</td>
                          <td style={{ padding: '8px 0', fontFamily: "'IBM Plex Mono', monospace" }}>₹{fmt(value)}</td>
                          <td style={{ padding: '8px 0', color: clr(pnl), fontWeight: 700, fontFamily: "'IBM Plex Mono', monospace" }}>
                            {sign(pnl)}₹{fmt(Math.abs(pnl))} ({sign(pnlPct)}{fmt(pnlPct, 2)}%)
                          </td>
                          <td style={{ padding: '8px 0', textAlign: 'right' }}>
                            <button
                              onClick={() => {
                                onExecuteOrder({
                                  side: 'sell',
                                  symbol: pos.symbol,
                                  type: 'market',
                                  qty: pos.shares.toString(),
                                  price: price
                                });
                              }}
                              style={{
                                padding: '3px 8px',
                                background: 'rgba(255, 61, 90, 0.06)',
                                border: `1px solid rgba(255, 61, 90, 0.25)`,
                                borderRadius: 4,
                                color: T.red,
                                fontSize: 9,
                                fontWeight: 700,
                                cursor: 'pointer',
                                fontFamily: "'Inter', sans-serif",
                                transition: 'all 0.15s'
                              }}
                              onMouseEnter={e => {
                                e.currentTarget.style.background = 'rgba(255, 61, 90, 0.12)';
                                e.currentTarget.style.borderColor = 'rgba(255, 61, 90, 0.4)';
                              }}
                              onMouseLeave={e => {
                                e.currentTarget.style.background = 'rgba(255, 61, 90, 0.06)';
                                e.currentTarget.style.borderColor = 'rgba(255, 61, 90, 0.25)';
                              }}
                            >
                              MARKET SELL CLOSE
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {consoleTab === 'ORDERS' && (
          <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            {openOrders.length === 0 ? (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flex: 1, color: T.textDim, fontSize: 11, fontFamily: "'IBM Plex Mono', monospace" }}>
                NO OPEN LIMIT ORDERS
              </div>
            ) : (
              <div style={{ flex: 1, overflowY: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: 11 }}>
                  <thead>
                    <tr style={{ color: T.textDim, borderBottom: `1px solid ${T.border}` }}>
                      <th style={{ paddingBottom: 6, fontWeight: 700 }}>SIDE</th>
                      <th style={{ paddingBottom: 6, fontWeight: 700 }}>SYMBOL</th>
                      <th style={{ paddingBottom: 6, fontWeight: 700 }}>QTY</th>
                      <th style={{ paddingBottom: 6, fontWeight: 700 }}>LIMIT PRICE</th>
                      <th style={{ paddingBottom: 6, fontWeight: 700 }}>ORDER TYPE</th>
                      <th style={{ paddingBottom: 6, fontWeight: 700, textAlign: 'right' }}>ACTION</th>
                    </tr>
                  </thead>
                  <tbody>
                    {openOrders.map(o => (
                      <tr key={o.id} style={{ borderBottom: `1px solid ${T.border}` }}>
                        <td style={{ padding: '8px 0', fontWeight: 700, color: o.side === 'buy' ? T.green : T.red, fontFamily: "'IBM Plex Mono', monospace" }}>
                          {o.side.toUpperCase()}
                        </td>
                        <td style={{ padding: '8px 0', fontWeight: 700, color: '#fff', fontFamily: "'IBM Plex Mono', monospace" }}>{o.symbol.replace('.NS', '')}</td>
                        <td style={{ padding: '8px 0', fontFamily: "'IBM Plex Mono', monospace" }}>{o.qty}</td>
                        <td style={{ padding: '8px 0', fontFamily: "'IBM Plex Mono', monospace" }}>₹{fmt(o.limitPrice)}</td>
                        <td style={{ padding: '8px 0', color: T.textMid }}>LIMIT (PAPER)</td>
                        <td style={{ padding: '8px 0', textAlign: 'right' }}>
                          <button
                            onClick={() => onCancelOrder(o.id)}
                            style={{
                              padding: '3px 8px',
                              background: 'rgba(255, 61, 90, 0.06)',
                              border: `1px solid rgba(255, 61, 90, 0.25)`,
                              borderRadius: 4,
                              color: T.red,
                              fontSize: 9,
                              fontWeight: 700,
                              cursor: 'pointer',
                              fontFamily: "'Inter', sans-serif"
                            }}
                          >
                            CANCEL ORDER
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {consoleTab === 'ALERTS' && (
          <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            {priceAlerts.length === 0 ? (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flex: 1, color: T.textDim, fontSize: 11, fontFamily: "'IBM Plex Mono', monospace" }}>
                NO ACTIVE PRICE ALERTS
              </div>
            ) : (
              <div style={{ flex: 1, overflowY: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: 11 }}>
                  <thead>
                    <tr style={{ color: T.textDim, borderBottom: `1px solid ${T.border}` }}>
                      <th style={{ paddingBottom: 6, fontWeight: 700 }}>SYMBOL</th>
                      <th style={{ paddingBottom: 6, fontWeight: 700 }}>TRIGGER CONDITION</th>
                      <th style={{ paddingBottom: 6, fontWeight: 700 }}>TARGET LEVEL</th>
                      <th style={{ paddingBottom: 6, fontWeight: 700 }}>LAST PRICE</th>
                      <th style={{ paddingBottom: 6, fontWeight: 700, textAlign: 'right' }}>ACTION</th>
                    </tr>
                  </thead>
                  <tbody>
                    {priceAlerts.map(a => {
                      const price = prices[a.symbol]?.price ?? SEED_PRICES[a.symbol] ?? 0;
                      return (
                        <tr key={a.id} style={{ borderBottom: `1px solid ${T.border}` }}>
                          <td style={{ padding: '8px 0', fontWeight: 700, color: '#fff', fontFamily: "'IBM Plex Mono', monospace" }}>{a.symbol.replace('.NS', '')}</td>
                          <td style={{ padding: '8px 0', color: a.condition === 'above' ? T.green : T.red }}>
                            {a.condition === 'above' ? 'Crosses Above (≥)' : 'Drops Below (≤)'}
                          </td>
                          <td style={{ padding: '8px 0', fontWeight: 600, fontFamily: "'IBM Plex Mono', monospace" }}>₹{fmt(a.targetPrice, 1)}</td>
                          <td style={{ padding: '8px 0', fontFamily: "'IBM Plex Mono', monospace" }}>₹{fmt(price)}</td>
                          <td style={{ padding: '8px 0', textAlign: 'right' }}>
                            <button
                              onClick={() => onDeleteAlert(a.id)}
                              style={{
                                padding: '3px 8px',
                                background: 'rgba(255, 61, 90, 0.06)',
                                border: `1px solid rgba(255, 61, 90, 0.25)`,
                                borderRadius: 4,
                                color: T.red,
                                fontSize: 9,
                                fontWeight: 700,
                                cursor: 'pointer',
                                fontFamily: "'Inter', sans-serif"
                              }}
                            >
                              REMOVE
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {consoleTab === 'AI' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6, height: '100%', boxSizing: 'border-box' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: `1px solid ${T.border}`, paddingBottom: 4 }}>
              <div style={{ fontSize: 9.5, fontWeight: 700, color: T.accentAlt, display: 'flex', alignItems: 'center', gap: 6 }}>
                <span>💡</span> AI QUANT ANALYST: {selected.replace('.NS', '')}
              </div>
              {aiRecommendationLoading && (
                <span style={{ display: 'inline-block', width: 10, height: 10, border: `1.5px solid ${T.border}`, borderTopColor: T.accentAlt, borderRadius: '50%', animation: 'spin 0.7s linear infinite' }} />
              )}
            </div>
            <div style={{ fontSize: 11.5, color: T.text, lineHeight: 1.5, overflowY: 'auto', flex: 1, paddingRight: 4 }}>
              {aiRecommendationLoading ? (
                <span style={{ color: T.textDim }}>Running technical scan and generating insights...</span>
              ) : (
                aiRecommendation || "Select a ticker from the watchlist to fetch a quick technical recommendation."
              )}
            </div>
            {!aiRecommendationLoading && aiRecommendation && (
              <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
                <button
                  onClick={() => onViewChange('PREDICTIONS')}
                  style={{
                    padding: '3px 8px',
                    background: 'rgba(245, 200, 66, 0.06)',
                    border: `1px solid rgba(245, 200, 66, 0.25)`,
                    borderRadius: 5,
                    color: T.gold,
                    fontSize: 9,
                    fontWeight: 700,
                    cursor: 'pointer',
                    fontFamily: "'Inter', sans-serif",
                    letterSpacing: '0.04em',
                    transition: 'all 0.2s',
                  }}
                  onMouseEnter={e => {
                    e.currentTarget.style.background = 'rgba(245, 200, 66, 0.12)';
                    e.currentTarget.style.borderColor = 'rgba(245, 200, 66, 0.4)';
                  }}
                  onMouseLeave={e => {
                    e.currentTarget.style.background = 'rgba(245, 200, 66, 0.06)';
                    e.currentTarget.style.borderColor = 'rgba(245, 200, 66, 0.25)';
                  }}
                >
                  🔮 LOG SYSTEM PREDICTION
                </button>
                {onRefreshAnalyst && (
                  <button
                    onClick={onRefreshAnalyst}
                    style={{
                      padding: '3px 8px',
                      background: 'rgba(77, 166, 255, 0.06)',
                      border: `1px solid rgba(77, 166, 255, 0.25)`,
                      borderRadius: 5,
                      color: T.blue,
                      fontSize: 9,
                      fontWeight: 700,
                      cursor: 'pointer',
                      fontFamily: "'Inter', sans-serif",
                      letterSpacing: '0.04em',
                      transition: 'all 0.2s',
                    }}
                    onMouseEnter={e => {
                      e.currentTarget.style.background = 'rgba(77, 166, 255, 0.12)';
                      e.currentTarget.style.borderColor = 'rgba(77, 166, 255, 0.4)';
                    }}
                    onMouseLeave={e => {
                      e.currentTarget.style.background = 'rgba(77, 166, 255, 0.06)';
                      e.currentTarget.style.borderColor = 'rgba(77, 166, 255, 0.25)';
                    }}
                  >
                    🔄 REFRESH
                  </button>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Tab configuration ────────────────────────────────────────────────────────
// Primary tabs: shown in the desktop header and as the main mobile bottom nav.
const PRIMARY_TABS = ['HOME', 'SIMULATOR', 'CHART', 'PREDICTIONS', 'PERFORMANCE', 'JOURNAL', 'ACCOUNT'];
// Secondary (demoted) tabs: collapsed behind a "More" menu on desktop, still reachable.
const SECONDARY_TABS = ['SIGNALS'];
// Mobile keeps the full list (scanner accessible via bottom nav on small screens).
const MOBILE_TABS = ['HOME', 'SIMULATOR', 'CHART', 'SIGNALS', 'PREDICTIONS', 'PERFORMANCE', 'JOURNAL', 'ACCOUNT'];

// Icon + label map for tab rendering
const TAB_META = {
  HOME:        { icon: '🏠', label: 'HOME' },
  SIMULATOR:   { icon: '🤖', label: 'BOT' },
  CHART:       { icon: '📈', label: 'CHART' },
  SIGNALS:     { icon: '📡', label: 'SCAN' },
  PREDICTIONS: { icon: '🔮', label: 'PREDICT' },
  PERFORMANCE: { icon: '📊', label: 'PERF' },
  JOURNAL:     { icon: '📓', label: 'JRNL' },
  ACCOUNT:     { icon: '🛡️', label: 'SEC' },
};

// ── Main App ──────────────────────────────────────────────────────────────────
export default function App() {
  // Security Authentication Gate
  const [loggedIn, setLoggedIn] = useState(true);
  const [currentUser, setCurrentUser] = useState(() => localStorage.getItem('apex_user') || 'apex_head_quant');
  const [userRole, setUserRole] = useState(() => localStorage.getItem('apex_role') || 'Master Quant / Administrator');
  const [userClearance, setUserClearance] = useState(() => localStorage.getItem('apex_clearance') || 'LEVEL_4_ROOT');

  const handleLogout = useCallback(() => {
    localStorage.removeItem('is_logged_in');
    localStorage.removeItem('apex_user');
    localStorage.removeItem('apex_role');
    localStorage.removeItem('apex_clearance');
    localStorage.removeItem('apt_token');
    sessionStorage.removeItem('apt_token');
    setLoggedIn(false);
  }, []);

  // Warm up backend in the background as soon as the app mounts (during login screen presentation)
  useEffect(() => {
    const BASE_URL = API_BASE_URL;
    fetch(`${BASE_URL}/`).catch(() => {});
  }, []);

  const [view, setView]         = useState(() => {
    const pathname = window.location.pathname.toLowerCase();
    if (pathname.includes('/account') || pathname.endsWith('account')) {
      return 'ACCOUNT';
    }
    return 'SIMULATOR';
  });   // 'SIMULATOR' is default now, but routing-aware

  const [selected, setSelected] = useState('YESBANK.NS');
  const [ivIdx, setIvIdx]       = useState(0);          // 1D default for intraday
  const [rightTab, setRightTab] = useState('BOT');
  
  const [drawMode, setDrawMode] = useState(null); // 'SUPPORT' | 'RESISTANCE' | null
  const [chartLines, setChartLines] = useState({}); // { 'AAPL.NS': [{price, type, id}] }
  
  const handleDrawComplete = useCallback((line) => {
    setChartLines(prev => ({
      ...prev,
      [selected]: [...(prev[selected] || []), line]
    }));
    setDrawMode(null); // auto-turn off drawing mode after 1 click
  }, [selected]);
  
  // Server warming/cold start splash page state
  const [serverWarming, setServerWarming] = useState(() => localStorage.getItem('apex_splash_shown') === null);
  const [backendReady, setBackendReady] = useState(false);

  // Paper Trading State
  const [portfolio, setPortfolio] = useState(() => {
    const saved = localStorage.getItem('apex_portfolio');
    return saved ? JSON.parse(saved) : []; // Default is empty portfolio: no stocks
  });
  const [cash, setCash] = useState(() => {
    const saved = localStorage.getItem('apex_cash');
    return saved ? parseFloat(saved) : 1000000; // Starting cash: ₹10,00,000 (10 Lakhs)
  });
  const [openOrders, setOpenOrders] = useState([]);

  useEffect(() => {
    localStorage.setItem('apex_portfolio', JSON.stringify(portfolio));
  }, [portfolio]);

  useEffect(() => {
    localStorage.setItem('apex_cash', cash.toString());
  }, [cash]);

  // Chart markers for executed paper trades
  const [tradeMarkers, setTradeMarkers] = useState({});

  const symbols = DEFAULT_WATCHLIST.map(w => w.symbol);
  const { prices, connected } = useLivePrices(symbols);
  const iv = INTERVALS[ivIdx];
  const currentPrice     = prices[selected]?.price ?? SEED_PRICES[selected] ?? 0;
  const currentChangePct = prices[selected]?.changePct ?? 0;

  const totalStockValue = portfolio.reduce((sum, pos) => {
    const price = prices[pos.symbol]?.price ?? SEED_PRICES[pos.symbol] ?? pos.avgCost;
    return sum + (price * pos.shares);
  }, 0);
  const netWorth = totalStockValue + cash;

  // ── Keyboard Shortcuts ────────────────────────────────────────────────────────
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

      if (e.key === 'b' || e.key === 'B') {
        setView('HOME');
      } else if (e.key === 's' || e.key === 'S') {
        setView('HOME');
      } else if (e.key >= '1' && e.key <= '6') {
        const idx = parseInt(e.key) - 1;
        if (idx < INTERVALS.length) {
          setIvIdx(idx);
          setView('CHART');
        }
      } else if (e.key === 'Tab') {
        e.preventDefault();
        const currentIndex = DEFAULT_WATCHLIST.findIndex(w => w.symbol === selected);
        const nextIndex = (currentIndex + 1) % DEFAULT_WATCHLIST.length;
        setSelected(DEFAULT_WATCHLIST[nextIndex].symbol);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selected]);

  // ── Morning Brief ───────────────────────────────────────────────────────────
  const [showBriefModal, setShowBriefModal] = useState(false);
  const [morningSignals, setMorningSignals] = useState([]);

  // Watchlist panel state (collapsed by default - bot manages its own universe)
  const [showWatchlist, setShowWatchlist] = useState(false);
  
  useEffect(() => {
    const checkMorningBrief = () => {
      if (!loggedIn) return;
      
      const now = new Date();
      const istTime = new Date(now.toLocaleString("en-US", {timeZone: "Asia/Kolkata"}));
      const hours = istTime.getHours();
      const minutes = istTime.getMinutes();
      
      const todayStr = istTime.toDateString();
      const lastShown = localStorage.getItem('last_morning_brief');
      
      if (lastShown !== todayStr && (hours > 9 || (hours === 9 && minutes >= 15))) {
        // Market is open or opened already today
        apiFetch('/api/scan', {
          method: 'POST',
          body: JSON.stringify({ symbols: DEFAULT_WATCHLIST.map(w=>w.symbol), interval: '15m', capital: cash })
        })
        .then(r => r.json())
        .then(data => {
          if (data.signals) {
            setMorningSignals(data.signals.slice(0, 3));
            setShowBriefModal(true);
            localStorage.setItem('last_morning_brief', todayStr);
          }
        }).catch(err => console.error("Morning brief scan failed", err));
      }
    };
    
    checkMorningBrief();
    const t = setInterval(checkMorningBrief, 60000);
    return () => clearInterval(t);
  }, [cash]);

  const totalCost = portfolio.reduce((sum, pos) => {
    return sum + (pos.avgCost * pos.shares);
  }, 0);
  const totalPnl = totalStockValue - totalCost;
  const totalPct = totalCost > 0 ? (totalPnl / totalCost) * 100 : 0;

  // Mobile layout sub-tab for Chart page
  const [mobileSubTab, setMobileSubTab] = useState('CHART');

  // Bot Engine State
  const [botPaperMode, setBotPaperMode] = useState(true);
  const [selectedStrategy, setSelectedStrategy] = useState('intraday_momentum');
  const [strategyPerformance, setStrategyPerformance] = useState(null);
  const [backtestResults, setBacktestResults] = useState(null);

  // Console active tab state
  const [consoleTab, setConsoleTab] = useState('POSITIONS');

  // Price alerts state
  const [priceAlerts, setPriceAlerts] = useState(() => {
    const saved = localStorage.getItem('apex_price_alerts');
    return saved ? JSON.parse(saved) : [];
  });

  // Reference for prices to prevent unnecessary re-fetches in AI effects
  const pricesRef = useRef(prices);
  useEffect(() => {
    pricesRef.current = prices;
  }, [prices]);

  // App-level Cache for Daily Market Briefing & Stats
  const [marketBrief, setMarketBrief] = useState(null);
  const [loadingBrief, setLoadingBrief] = useState(true);
  const [predictionStats, setPredictionStats] = useState(null);
  const [refreshAnalystToken, setRefreshAnalystToken] = useState(0);

  const fetchMarketBrief = useCallback(() => {
    if (!loggedIn || !backendReady) return;
    apiFetch('/api/market_brief')
    .then(res => res.ok ? res.json() : Promise.reject())
    .then(data => {
      setMarketBrief(data);
      setLoadingBrief(false);
    })
    .catch(() => {
      setLoadingBrief(false);
    });
  }, [loggedIn]);

  const fetchPredictionStats = useCallback(() => {
    if (!loggedIn || !backendReady) return;
    apiFetch('/api/predictions/stats')
    .then(res => res.ok ? res.json() : Promise.reject())
    .then(data => {
      setPredictionStats(data);
    })
    .catch(() => {});
  }, [loggedIn]);

  useEffect(() => {
    if (loggedIn && backendReady) {
      fetchMarketBrief();
      fetchPredictionStats();
    }
  }, [loggedIn, backendReady, fetchMarketBrief, fetchPredictionStats]);

  // Watchlist favorites state
  const [favorites, setFavorites] = useState(() => {
    const saved = localStorage.getItem('apex_favorites');
    return saved ? JSON.parse(saved) : ['YESBANK.NS', 'BEL.NS'];
  });

  // AI Analyst embedded card states
  const [aiRecommendation, setAiRecommendation] = useState('');
  const [aiRecommendationLoading, setAiRecommendationLoading] = useState(false);
  const aiRecommendationCache = useRef({});
  const lastRefreshRef = useRef(0);

  // Toast notifications state
  const [toasts, setToasts] = useState([]);

  // Signals state (pre-seeded fallback, fresh scan manually triggered in Signals tab)
  const [signals, setSignals] = useState([
    { symbol: 'YESBANK.NS', name: 'HAL', signal: 'BUY', confidence: 88, rr_ratio: 2.5, reasoning: 'RSI oversold trigger on daily candle chart. Volume spike supports reversal.' },
    { symbol: 'BEL.NS', name: 'BEL', signal: 'BUY', confidence: 75, rr_ratio: 1.8, reasoning: 'Moving average convergence crossover signals strong bullish momentum.' },
    { symbol: 'RVNL.NS', name: 'RVNL', signal: 'BUY', confidence: 82, rr_ratio: 2.1, reasoning: 'Breakout patterns on high volume confirmation.' }
  ]);

  const showToast = useCallback((message, type = 'success') => {
    const id = Math.random().toString(36).substr(2, 9);
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 5000);
  }, []);

  const handleToggleFavorite = useCallback((symbol) => {
    setFavorites(prev => {
      const updated = prev.includes(symbol) ? prev.filter(s => s !== symbol) : [...prev, symbol];
      localStorage.setItem('apex_favorites', JSON.stringify(updated));
      return updated;
    });
  }, []);

  const handleAddAlert = useCallback((symbol, condition, targetPrice) => {
    const newAlert = {
      id: Math.random().toString(36).substr(2, 9),
      symbol,
      condition,
      targetPrice: parseFloat(targetPrice),
      active: true,
    };
    setPriceAlerts(prev => {
      const updated = [...prev, newAlert];
      localStorage.setItem('apex_price_alerts', JSON.stringify(updated));
      return updated;
    });
    showToast(`Price alert created for ${symbol.replace('.NS', '')}`, 'success');
  }, [showToast]);

  const handleDeleteAlert = useCallback((id) => {
    setPriceAlerts(prev => {
      const updated = prev.filter(a => a.id !== id);
      localStorage.setItem('apex_price_alerts', JSON.stringify(updated));
      return updated;
    });
    showToast(`Price alert removed`, 'info');
  }, [showToast]);

  const [pendingPredictions, setPendingPredictions] = useState([]);
  const resolvingIds = useRef(new Set());

  // Fetch pending predictions
  const fetchPendingPredictions = useCallback(async () => {
    if (!loggedIn) return;
    try {
      const res = await apiFetch('/api/predictions');
      if (res.ok) {
        const data = await res.json();
        setPendingPredictions(data.filter(p => p.status === 'PENDING'));
      }
    } catch (err) {
      console.error("Error fetching pending predictions:", err);
    }
  }, [loggedIn]);

  useEffect(() => {
    if (!loggedIn) return;
    fetchPendingPredictions();
    if (view === 'PREDICTIONS') {
      const interval = setInterval(fetchPendingPredictions, 60000); // refresh pending list every 60s when on Predictions view
      return () => clearInterval(interval);
    }
  }, [fetchPendingPredictions, loggedIn, view]);



  // Embedded AI Analyst Recommendation Fetch Effect
  useEffect(() => {
    if (!selected || !loggedIn || view !== 'CHART') return;

    const isManualRefresh = refreshAnalystToken !== lastRefreshRef.current;
    lastRefreshRef.current = refreshAnalystToken;

    if (aiRecommendationCache.current[selected] && !isManualRefresh) {
      setAiRecommendation(aiRecommendationCache.current[selected]);
      setAiRecommendationLoading(false);
      return;
    }

    let active = true;
    setAiRecommendationLoading(true);
    setAiRecommendation('');
    
    const timer = setTimeout(async () => {
      try {
        const cleanedSymbol = selected.replace('.NS', '');
        const currentPrices = pricesRef.current || {};
        const livePrice = currentPrices[selected]?.price ?? SEED_PRICES[selected] ?? 0;
        const pct = currentPrices[selected]?.changePct ?? 0;

        const res = await apiFetch('/api/chat', {
          method: 'POST',
          body: JSON.stringify({
            message: `Provide a quick 1-2 sentence technical analyst recommendation for ${cleanedSymbol} at current price ₹${livePrice} (${pct >= 0 ? '+' : ''}${pct.toFixed(2)}%). Focus on technical metrics like RSI, key levels, or potential triggers. Keep it extremely concise.`,
            context: { symbol: cleanedSymbol, price: livePrice, changePct: pct },
            history: []
          })
        });
        if (res.ok && active) {
          const data = await res.json();
          setAiRecommendation(data.reply);
          aiRecommendationCache.current[selected] = data.reply;
        } else if (active) {
          const fallbackVal = `AI Recommendation unavailable (Backend Error).`;
          setAiRecommendation(fallbackVal);
          aiRecommendationCache.current[selected] = fallbackVal;
        }
      } catch (err) {
        if (active) {
          const fallbackVal = `AI Recommendation unavailable (Network Error).`;
          setAiRecommendation(fallbackVal);
          aiRecommendationCache.current[selected] = fallbackVal;
        }
      } finally {
        if (active) setAiRecommendationLoading(false);
      }
    }, 1000); // 1 second debounce
    
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [selected, loggedIn, view, refreshAnalystToken]); // Removed 'prices' dependency

  // Price Alerts Engine Effect
  useEffect(() => {
    if (priceAlerts.length === 0) return;
    
    const triggeredIds = [];
    priceAlerts.forEach(alert => {
      const liveData = prices[alert.symbol];
      if (!liveData) return;
      
      const price = liveData.price;
      let triggered = false;
      if (alert.condition === 'above' && price >= alert.targetPrice) {
        triggered = true;
      } else if (alert.condition === 'below' && price <= alert.targetPrice) {
        triggered = true;
      }
      
      if (triggered) {
        triggeredIds.push(alert.id);
        const sideSymbol = alert.symbol.replace('.NS', '');
        const direction = alert.condition === 'above' ? 'crossed above' : 'dropped below';
        showToast(`⏰ ALERT TRIGGERED: ${sideSymbol} has ${direction} ₹${fmt(alert.targetPrice, 1)} (Current: ₹${fmt(price, 1)})`, 'info');
      }
    });
    
    if (triggeredIds.length > 0) {
      setPriceAlerts(prev => {
        const updated = prev.filter(a => !triggeredIds.includes(a.id));
        localStorage.setItem('apex_price_alerts', JSON.stringify(updated));
        return updated;
      });
    }
  }, [prices, priceAlerts, showToast]);


  // Mobile Responsiveness State
  const [isMobile, setIsMobile] = useState(window.innerWidth <= 960);
  const [mobileTab, setMobileTab] = useState('CHART'); // 'WATCHLIST' | 'CHART' | 'SIGNALS' | 'ORDER' | 'PORTFOLIO' | 'AI'

  useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth <= 960);
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


  const lastBarTimeRef = useRef(null);

  const handleLastBarUpdate = useCallback((time) => {
    lastBarTimeRef.current = time;
  }, []);

  const getCurrentBarTime = useCallback((interval) => {
    const now = new Date();
    if (interval === '1d' || interval === '1wk' || interval === '1mo' || interval === '3mo') {
      const yyyy = now.getFullYear();
      const mm = String(now.getMonth() + 1).padStart(2, '0');
      const dd = String(now.getDate()).padStart(2, '0');
      return `${yyyy}-${mm}-${dd}`;
    } else {
      let seconds = 300;
      if (interval === '1m') seconds = 60;
      if (interval === '5m') seconds = 300;
      if (interval === '15m') seconds = 900;
      if (interval === '30m') seconds = 1800;
      if (interval === '60m' || interval === '1h') seconds = 3600;
      const ms = seconds * 1000;
      return Math.floor(Math.floor(Date.now() / ms) * ms / 1000);
    }
  }, []);

  const addTradeMarker = useCallback((sym, side, qty, execPrice) => {
    const barTime = (sym === selected && lastBarTimeRef.current) 
      ? lastBarTimeRef.current 
      : getCurrentBarTime(INTERVALS[ivIdx].interval);

    const newMarker = {
      time: barTime,
      position: side === 'buy' ? 'belowBar' : 'aboveBar',
      color: side === 'buy' ? T.green : T.red,
      shape: side === 'buy' ? 'arrowUp' : 'arrowDown',
      text: `${side.toUpperCase()}: ${qty} @ ₹${fmt(execPrice, 1)}`,
    };

    setTradeMarkers(prev => ({
      ...prev,
      [sym]: [...(prev[sym] || []), newMarker]
    }));
  }, [selected, ivIdx, getCurrentBarTime]);



  // Execute market/limit orders
  const handleExecuteOrder = async (order) => {
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
        addTradeMarker(order.symbol, 'buy', qty, price);
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
        addTradeMarker(order.symbol, 'sell', qty, price);
      }

      // Persist to backend Journal
      try {
        await apiFetch('/api/journal', {
          method: 'POST',
          body: JSON.stringify({
            symbol: order.symbol,
            direction: order.side.toUpperCase(),
            entry_price: price,
            qty: qty,
            reason: 'Manual Paper Trade',
            status: order.side === 'buy' ? 'OPEN' : 'CLOSED',
            emotion: 'Calm'
          })
        });
      } catch (e) {
        console.error("Failed to log paper trade to journal", e);
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
        addTradeMarker(order.symbol, order.side, order.qty, order.limitPrice);
        
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
  }, [prices, openOrders, cash, portfolio, addTradeMarker]);

  // Called from SignalsPanel when user clicks a signal card
  const handleSignalSelect = (symbol) => {
    setSelected(symbol);
    setView('CHART');
    setIvIdx(0);  // Switch to 1D (5-min) for intraday
  };

  const handleWokenUp = useCallback(() => {
    setServerWarming(false);
    setBackendReady(true);
    localStorage.setItem('apex_splash_shown', 'true');
  }, []);



  if (!loggedIn) {
    return (
      <PanelErrorBoundary>
        <LoginScreen 
          onLogin={(user, role, clearance) => { 
            setLoggedIn(true); 
            setCurrentUser(user); 
            setUserRole(role || 'Authorized Guest'); 
            setUserClearance(clearance || 'LEVEL_1_GUEST'); 
            localStorage.setItem('apex_user', user); 
            localStorage.setItem('apex_role', role || 'Authorized Guest'); 
            localStorage.setItem('apex_clearance', clearance || 'LEVEL_1_GUEST'); 
          }} 
        />
      </PanelErrorBoundary>
    );
  }

  return (
    <>
      {serverWarming && <IntroSplash onWokenUp={handleWokenUp} />}
      {/* Toast Notifications */}
      <div style={{ position: 'fixed', top: 20, right: 20, zIndex: 999999, display: 'flex', flexDirection: 'column', gap: 10, maxWidth: 360 }}>
        {toasts.map(t => (
          <div key={t.id} style={{
            background: T.surface,
            border: `1px solid ${t.type === 'error' ? T.red : t.type === 'info' ? T.blue : T.green}`,
            boxShadow: `0 4px 16px rgba(0,0,0,0.5)`,
            color: T.text,
            padding: '12px 16px',
            borderRadius: 8,
            fontSize: 12,
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            animation: 'slideIn 0.3s ease',
            backdropFilter: 'blur(8px)',
          }}>
            <span style={{ color: t.type === 'error' ? T.red : t.type === 'info' ? T.blue : T.green }}>
              {t.type === 'error' ? '⚠️' : t.type === 'info' ? '⏰' : '✓'}
            </span>
            <span>{t.message}</span>
          </div>
        ))}
      </div>
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
            <span style={{ display: 'inline-block', width: 12, height: 12, border: `2px solid rgba(245,200,66,0.3)`, borderTopColor: T.gold, borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
            CONNECTING TO QUANT SERVER...
          </div>
        )}

        {/* Header */}
        <Header 
          connected={connected} 
          view={view} 
          onViewChange={setView} 
          isMobile={isMobile} 
          onLogout={handleLogout}
          netWorth={netWorth}
          cash={cash}
          stockValue={totalStockValue}
          totalPnl={totalPnl}
          totalPct={totalPct}
          selectedSymbol={selected}
          prices={prices}
        />

        {/* Main layout */}
        <div style={{ flex: 1, display: 'flex', minHeight: 0, overflow: 'hidden' }}>

          {view === 'HOME' ? (
            /* HOME VIEW — full width */
            <div className="panel-transition" style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0, overflow: 'hidden' }}>
              <HomePanel 
                prices={prices} 
                portfolio={portfolio} 
                cash={cash} 
                onViewChange={setView} 
                onSelectSymbol={setSelected}
                signals={signals}
                priceAlerts={priceAlerts} 
                onDeleteAlert={handleDeleteAlert} 
                brief={marketBrief}
                loadingBrief={loadingBrief}
                stats={predictionStats}
                onRefreshBrief={fetchMarketBrief}
                onUpdateBalances={(newCash, newPortfolio) => {
                  setCash(newCash);
                  setPortfolio(newPortfolio);
                }}
              />
              {isMobile && (
                <div style={{ display: 'flex', borderTop: `1px solid ${T.border}`, background: T.panelAlt, flexShrink: 0, paddingBottom: 'env(safe-area-inset-bottom)' }}>
                  {MOBILE_TABS.map(tab => (
                    <button key={tab} onClick={() => setView(tab)} style={{
                      flex: 1, padding: '12px 0', border: 'none', cursor: 'pointer',
                      background: 'transparent',
                      color: view === tab ? T.accent : T.textDim,
                      fontSize: 9, fontWeight: 700, letterSpacing: '0.05em',
                      fontFamily: "'Inter', sans-serif",
                      transition: 'all 0.2s',
                      borderTop: `2px solid ${view === tab ? T.accent : 'transparent'}`,
                      marginTop: -1
                    }}>
                      {tab === 'HOME' ? '🏠' : tab === 'CHART' ? '📈' : tab === 'SIGNALS' ? '📡' : tab === 'PREDICTIONS' ? '🔮' : tab === 'JOURNAL' ? '📓' : tab === 'SIMULATOR' ? '🤖' : '🛡️'}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ) : view === 'SIGNALS' ? (
            /* SIGNALS VIEW — full width */
            <div className="panel-transition" style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0, overflow: 'hidden' }}>
              <SignalsPanel onSelectSymbol={handleSignalSelect} selectedSymbol={selected} prices={prices} cash={cash} />
              {isMobile && (
                <div style={{ display: 'flex', borderTop: `1px solid ${T.border}`, background: T.panelAlt, flexShrink: 0, paddingBottom: 'env(safe-area-inset-bottom)' }}>
                  {MOBILE_TABS.map(tab => (
                    <button key={tab} onClick={() => setView(tab)} style={{
                      flex: 1, padding: '12px 0', border: 'none', cursor: 'pointer',
                      background: 'transparent',
                      color: view === tab ? T.accent : T.textDim,
                      fontSize: 9, fontWeight: 700, letterSpacing: '0.05em',
                      fontFamily: "'Inter', sans-serif",
                      transition: 'all 0.2s',
                      borderTop: `2px solid ${view === tab ? T.accent : 'transparent'}`,
                      marginTop: -1
                    }}>
                      {tab === 'HOME' ? '🏠' : tab === 'CHART' ? '📈' : tab === 'SIGNALS' ? '📡' : tab === 'PREDICTIONS' ? '🔮' : tab === 'PERFORMANCE' ? '📊' : tab === 'JOURNAL' ? '📓' : '🛡️'}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ) : view === 'PREDICTIONS' ? (
            /* PREDICTIONS VIEW — full width */
            <div className="panel-transition" style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0, overflow: 'hidden' }}>
              <PredictionsPanel prices={prices} selectedSymbol={selected} onSelectSymbol={setSelected} onViewChange={setView} />
              {isMobile && (
                <div style={{ display: 'flex', borderTop: `1px solid ${T.border}`, background: T.panelAlt, flexShrink: 0, paddingBottom: 'env(safe-area-inset-bottom)' }}>
                  {MOBILE_TABS.map(tab => (
                    <button key={tab} onClick={() => setView(tab)} style={{
                      flex: 1, padding: '12px 0', border: 'none', cursor: 'pointer',
                      background: 'transparent',
                      color: view === tab ? T.accent : T.textDim,
                      fontSize: 9, fontWeight: 700, letterSpacing: '0.05em',
                      fontFamily: "'Inter', sans-serif",
                      transition: 'all 0.2s',
                      borderTop: `2px solid ${view === tab ? T.accent : 'transparent'}`,
                      marginTop: -1
                    }}>
                      {tab === 'HOME' ? '🏠' : tab === 'CHART' ? '📈' : tab === 'SIGNALS' ? '📡' : tab === 'PREDICTIONS' ? '🔮' : tab === 'PERFORMANCE' ? '📊' : tab === 'JOURNAL' ? '📓' : '🛡️'}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ) : view === 'JOURNAL' ? (
            /* JOURNAL VIEW — full width */
            <div className="panel-transition" style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0, overflow: 'hidden' }}>
              <JournalPanel />
              {isMobile && (
                <div style={{ display: 'flex', borderTop: `1px solid ${T.border}`, background: T.panelAlt, flexShrink: 0, paddingBottom: 'env(safe-area-inset-bottom)' }}>
                  {MOBILE_TABS.map(tab => (
                    <button key={tab} onClick={() => setView(tab)} style={{
                      flex: 1, padding: '12px 0', border: 'none', cursor: 'pointer',
                      background: 'transparent',
                      color: view === tab ? T.accent : T.textDim,
                      fontSize: 9, fontWeight: 700, letterSpacing: '0.05em',
                      fontFamily: "'Inter', sans-serif",
                      transition: 'all 0.2s',
                      borderTop: `2px solid ${view === tab ? T.accent : 'transparent'}`,
                      marginTop: -1
                    }}>
                      {tab === 'HOME' ? '🏠' : tab === 'CHART' ? '📈' : tab === 'SIGNALS' ? '📡' : tab === 'PREDICTIONS' ? '🔮' : tab === 'PERFORMANCE' ? '📊' : tab === 'JOURNAL' ? '📓' : '🛡️'}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ) : view === 'PERFORMANCE' ? (
            /* PERFORMANCE VIEW — full width */
            <div className="panel-transition" style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0, overflow: 'hidden' }}>
              <PerformancePanel />
              {isMobile && (
                <div style={{ display: 'flex', borderTop: `1px solid ${T.border}`, background: T.panelAlt, flexShrink: 0, paddingBottom: 'env(safe-area-inset-bottom)' }}>
                  {MOBILE_TABS.map(tab => (
                    <button key={tab} onClick={() => setView(tab)} style={{
                      flex: 1, padding: '12px 0', border: 'none', cursor: 'pointer',
                      background: 'transparent',
                      color: view === tab ? T.accent : T.textDim,
                      fontSize: 9, fontWeight: 700, letterSpacing: '0.05em',
                      fontFamily: "'Inter', sans-serif",
                      transition: 'all 0.2s',
                      borderTop: `2px solid ${view === tab ? T.accent : 'transparent'}`,
                      marginTop: -1
                    }}>
                      {tab === 'HOME' ? '🏠' : tab === 'CHART' ? '📈' : tab === 'SIGNALS' ? '📡' : tab === 'PREDICTIONS' ? '🔮' : tab === 'PERFORMANCE' ? '📊' : tab === 'JOURNAL' ? '📓' : '🛡️'}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ) : view === 'ACCOUNT' ? (
            /* ACCOUNT VIEW — full width */
            <div className="panel-transition" style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0, overflow: 'hidden' }}>
              <AccountPanel 
                currentUser={currentUser} 
                userRole={userRole} 
                userClearance={userClearance} 
              />
              {isMobile && (
                <div style={{ display: 'flex', borderTop: `1px solid ${T.border}`, background: T.panelAlt, flexShrink: 0, paddingBottom: 'env(safe-area-inset-bottom)' }}>
                  {MOBILE_TABS.map(tab => (
                    <button key={tab} onClick={() => setView(tab)} style={{
                      flex: 1, padding: '12px 0', border: 'none', cursor: 'pointer',
                      background: 'transparent',
                      color: view === tab ? T.accent : T.textDim,
                      fontSize: 9, fontWeight: 700, letterSpacing: '0.05em',
                      fontFamily: "'Inter', sans-serif",
                      transition: 'all 0.2s',
                      borderTop: `2px solid ${view === tab ? T.accent : 'transparent'}`,
                      marginTop: -1
                    }}>
                      {tab === 'HOME' ? '🏠' : tab === 'CHART' ? '📈' : tab === 'SIGNALS' ? '📡' : tab === 'PREDICTIONS' ? '🔮' : tab === 'JOURNAL' ? '📓' : tab === 'SIMULATOR' ? '🤖' : '🛡️'}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ) : view === 'SIMULATOR' ? (
            /* BOT ENGINE VIEW — Hero panel: BotControl + TradeLog + Strategy + Backtest */
            <div className="panel-transition" style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0, overflow: 'hidden' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 16, padding: 16, flex: 1, overflow: 'auto' }}>
                {/* Top Row: Bot Control + Trade Log */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, minHeight: 0 }}>
                  <BotControlPanel isPaperMode={botPaperMode} onModeChange={setBotPaperMode} />
                  <TradeLogPanel />
                </div>

                {/* Bottom Row: Strategy Selector + Backtest Runner */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, minHeight: 0 }}>
                  <StrategySelector
                    selectedStrategy={selectedStrategy}
                    onSelectStrategy={setSelectedStrategy}
                    performanceData={backtestResults?.performance}
                  />
                  <BacktestRunner onResults={setBacktestResults} />
                </div>
              </div>

              {isMobile && (
                <div style={{ display: 'flex', borderTop: `1px solid ${T.border}`, background: T.panelAlt, flexShrink: 0, paddingBottom: 'env(safe-area-inset-bottom)' }}>
                  {MOBILE_TABS.map(tab => (
                    <button key={tab} onClick={() => setView(tab)} style={{
                      flex: 1, padding: '12px 0', border: 'none', cursor: 'pointer',
                      background: 'transparent',
                      color: view === tab ? T.accent : T.textDim,
                      fontSize: 9, fontWeight: 700, letterSpacing: '0.05em',
                      fontFamily: "'Inter', sans-serif",
                      transition: 'all 0.2s',
                      borderTop: `2px solid ${view === tab ? T.accent : 'transparent'}`,
                      marginTop: -1
                    }}>
                      {tab === 'HOME' ? '🏠' : tab === 'CHART' ? '📈' : tab === 'SIGNALS' ? '📡' : tab === 'PREDICTIONS' ? '🔮' : tab === 'PERFORMANCE' ? '📊' : tab === 'JOURNAL' ? '📓' : tab === 'SIMULATOR' ? '⏱️' : '🛡️'}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <>
              {isMobile ? (
                /* MOBILE VIEW — Single column with bottom tabs and top sub-tabs for Chart view */
                <div className="panel-transition" style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, background: T.bg }}>
                  {/* Content Area */}
                  <div style={{ flex: 1, overflow: 'auto', display: 'flex', flexDirection: 'column' }}>
                    {/* Sub-tab switcher */}
                    <div style={{ display: 'flex', background: T.panelAlt, borderBottom: `1px solid ${T.border}`, flexShrink: 0 }}>
                      {['WATCHLIST', 'CHART', 'ORDER', 'AI'].map(sub => (
                        <button key={sub} onClick={() => setMobileSubTab(sub)} style={{
                          flex: 1, padding: '10px 0', border: 'none', cursor: 'pointer',
                          background: 'transparent',
                          color: mobileSubTab === sub ? T.accent : T.textDim,
                          fontSize: 10, fontWeight: 700,
                          fontFamily: "'Inter', sans-serif",
                          borderBottom: `2px solid ${mobileSubTab === sub ? T.accent : 'transparent'}`,
                          marginTop: -1
                        }}>
                          {sub === 'WATCHLIST' ? '📋 WATCH' : sub === 'CHART' ? '📈 CHART' : sub === 'ORDER' ? '💸 TRADE' : '✦ AI'}
                        </button>
                      ))}
                    </div>

                    {mobileSubTab === 'WATCHLIST' && (
                      <div style={{ flex: 1, background: T.surface }}>
                        <WatchlistPanel prices={prices} selected={selected} onSelect={(s) => { setSelected(s); setMobileSubTab('CHART'); }} favorites={favorites} onToggleFavorite={handleToggleFavorite} />
                      </div>
                    )}

                    {mobileSubTab === 'CHART' && (
                      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
                        {/* Interval picker & Indicator Toggles (Scrollable on mobile) */}
                        <div style={{ padding: '8px 12px', borderBottom: `1px solid ${T.border}`, display: 'flex', alignItems: 'center', gap: 6, background: T.surface, overflowX: 'auto', flexShrink: 0, whiteSpace: 'nowrap' }}>
                          {INTERVALS.map((intv, i) => (
                            <button key={intv.label} onClick={() => setIvIdx(i)} style={{
                              padding: '4px 8px', border: `1px solid ${ivIdx === i ? T.accent : T.border}`,
                              borderRadius: 5, cursor: 'pointer', fontSize: 10, fontWeight: 700,
                              background: ivIdx === i ? T.blueDim : 'transparent',
                              color: ivIdx === i ? T.accent : T.textMid,
                              fontFamily: "'Inter', sans-serif",
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
                                fontFamily: "'Inter', sans-serif",
                                transition: 'all 0.15s', flexShrink: 0
                              }}>{label}</button>
                            );
                          })}
                          
                          <div style={{ width: 1, height: 16, background: T.border, margin: '0 4px', flexShrink: 0 }} />
                          
                          <button onClick={() => setDrawMode(drawMode === 'SUPPORT' ? null : 'SUPPORT')} style={{
                            padding: '4px 8px', border: `1px solid ${drawMode === 'SUPPORT' ? T.green : T.border}`,
                            borderRadius: 5, cursor: 'pointer', fontSize: 9, fontWeight: 700,
                            background: drawMode === 'SUPPORT' ? T.greenDim : 'transparent',
                            color: drawMode === 'SUPPORT' ? T.green : T.textDim,
                            fontFamily: "'Inter', sans-serif", transition: 'all 0.15s', flexShrink: 0
                          }}>DRAW SUPPORT</button>
                          
                          <button onClick={() => setDrawMode(drawMode === 'RESISTANCE' ? null : 'RESISTANCE')} style={{
                            padding: '4px 8px', border: `1px solid ${drawMode === 'RESISTANCE' ? T.red : T.border}`,
                            borderRadius: 5, cursor: 'pointer', fontSize: 9, fontWeight: 700,
                            background: drawMode === 'RESISTANCE' ? T.redDim : 'transparent',
                            color: drawMode === 'RESISTANCE' ? T.red : T.textDim,
                            fontFamily: "'Inter', sans-serif", transition: 'all 0.15s', flexShrink: 0
                          }}>DRAW RESIST</button>
                        </div>
                        {/* Chart */}
                        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
                          <CandleChart 
                            key={`${selected}-${INTERVALS[ivIdx].interval}-${INTERVALS[ivIdx].range}-${indicators.rsi}-${indicators.macd}`} 
                            symbol={selected} 
                            interval={INTERVALS[ivIdx].interval} 
                            range={INTERVALS[ivIdx].range} 
                            indicators={indicators} 
                            livePrice={prices[selected]}
                            markers={tradeMarkers[selected] || EMPTY_ARRAY}
                            onLastBarUpdate={handleLastBarUpdate}
                            drawMode={drawMode}
                            onDrawComplete={handleDrawComplete}
                            customLines={chartLines[selected] || EMPTY_ARRAY}
                            botPaperMode={botPaperMode}
                          />
                        </div>
                        {/* Embedded AI Analyst Card */}
                        <div style={{
                          margin: '8px 12px 12px',
                          background: T.panel,
                          border: `1px solid ${T.border}`,
                          borderRadius: 8,
                          padding: '10px 12px',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: 6,
                          flexShrink: 0
                        }}>
                          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', color: T.accentAlt }}>
                              💡 AI QUANT ANALYST: {selected.replace('.NS', '')}
                            </div>
                            {aiRecommendationLoading && (
                              <span style={{ display: 'inline-block', width: 10, height: 10, border: `1.5px solid ${T.border}`, borderTopColor: T.accentAlt, borderRadius: '50%', animation: 'spin 0.7s linear infinite' }} />
                            )}
                          </div>
                          <div style={{ fontSize: 11, color: T.text, lineHeight: 1.4 }}>
                            {aiRecommendationLoading ? (
                              <span style={{ color: T.textDim }}>Running technical scan...</span>
                            ) : (
                              aiRecommendation || "Select a ticker from the watchlist to fetch a quick technical recommendation."
                            )}
                          </div>
                          <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
                            <button
                              onClick={() => setView('PREDICTIONS')}
                              style={{
                                padding: '3px 8px',
                                background: 'rgba(245, 200, 66, 0.08)',
                                border: `1px solid ${T.gold}30`,
                                borderRadius: 5,
                                color: T.gold,
                                fontSize: 9,
                                fontWeight: 700,
                                cursor: 'pointer',
                                fontFamily: "'Inter', sans-serif",
                                letterSpacing: '0.04em',
                                transition: 'all 0.2s'
                              }}
                              onMouseEnter={e => e.currentTarget.style.background = 'rgba(245, 200, 66, 0.15)'}
                              onMouseLeave={e => e.currentTarget.style.background = 'rgba(245, 200, 66, 0.08)'}
                            >
                              🔮 LOG PREDICTION
                            </button>
                            <button
                              onClick={() => setRefreshAnalystToken(prev => prev + 1)}
                              disabled={aiRecommendationLoading}
                              style={{
                                padding: '3px 8px',
                                background: 'rgba(77, 166, 255, 0.08)',
                                border: `1px solid ${T.blue}30`,
                                borderRadius: 5,
                                color: T.blue,
                                fontSize: 9,
                                fontWeight: 700,
                                cursor: aiRecommendationLoading ? 'not-allowed' : 'pointer',
                                fontFamily: "'Inter', sans-serif",
                                letterSpacing: '0.04em',
                                transition: 'all 0.2s'
                              }}
                              onMouseEnter={e => !aiRecommendationLoading && (e.currentTarget.style.background = 'rgba(77, 166, 255, 0.15)')}
                              onMouseLeave={e => !aiRecommendationLoading && (e.currentTarget.style.background = 'rgba(77, 166, 255, 0.08)')}
                            >
                              🔄 REFRESH
                            </button>
                          </div>
                        </div>
                      </div>
                    )}

                    {mobileSubTab === 'ORDER' && (
                      <div style={{ flex: 1, background: T.surface, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
                        <div style={{ flex: '1 1 50%', overflowY: 'auto', minHeight: 0 }}>
                          <OrderPanel symbol={selected} price={currentPrice} cash={cash} openOrders={openOrders} onExecuteOrder={handleExecuteOrder} onCancelOrder={handleCancelOrder} priceAlerts={priceAlerts} onAddAlert={handleAddAlert} onDeleteAlert={handleDeleteAlert} />
                        </div>
                        <div style={{ flex: '1 1 50%', minHeight: 0 }}>
                          <OrderBookPanel symbol={selected} price={currentPrice} />
                        </div>
                      </div>
                    )}

                    {mobileSubTab === 'AI' && (
                      <div style={{ flex: 1, background: T.surface }}>
                        <ChatPanel symbol={selected} price={currentPrice} changePct={currentChangePct} />
                      </div>
                    )}
                  </div>

                  {/* Bottom Navigation Bar */}
                  <div style={{ display: 'flex', borderTop: `1px solid ${T.border}`, background: T.panelAlt, flexShrink: 0, paddingBottom: 'env(safe-area-inset-bottom)' }}>
                    {MOBILE_TABS.map(tab => (
                      <button key={tab} onClick={() => setView(tab)} style={{
                        flex: 1, padding: '12px 0', border: 'none', cursor: 'pointer',
                        background: 'transparent',
                        color: view === tab ? T.accent : T.textDim,
                        fontSize: 9, fontWeight: 700, letterSpacing: '0.05em',
                        fontFamily: "'Inter', sans-serif",
                        transition: 'all 0.2s',
                        borderTop: `2px solid ${view === tab ? T.accent : 'transparent'}`,
                        marginTop: -1
                      }}>
                        {tab === 'HOME' ? '🏠 HOME' : tab === 'CHART' ? '📈 CHART' : tab === 'SIGNALS' ? '📡 SCAN' : tab === 'PREDICTIONS' ? '🔮 PRED' : tab === 'SIMULATOR' ? '🤖 BOT' : tab === 'PERFORMANCE' ? '📊 PERF' : tab === 'JOURNAL' ? '📓 JRNL' : '🛡️ SEC'}
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                /* DESKTOP VIEW — 3 Columns (Watchlist collapsible) */
                <div className="panel-transition" style={{ flex: 1, display: 'flex', minHeight: 0, overflow: 'hidden' }}>
                  {/* LEFT — Watchlist (Collapsible) */}
                  <div style={{ width: showWatchlist ? 280 : 0, flexShrink: 0, borderRight: showWatchlist ? `1px solid ${T.border}` : 'none', background: T.surface, overflow: 'hidden', transition: 'width 0.3s ease, border 0.3s ease' }}>
                    {showWatchlist && (
                      <WatchlistPanel prices={prices} selected={selected} onSelect={setSelected} favorites={favorites} onToggleFavorite={handleToggleFavorite} />
                    )}
                  </div>

                  {/* Watchlist Toggle Button */}
                  <button
                    onClick={() => setShowWatchlist(!showWatchlist)}
                    style={{
                      position: 'relative',
                      width: 32,
                      flexShrink: 0,
                      border: 'none',
                      background: T.surface,
                      borderRight: `1px solid ${T.border}`,
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      transition: 'background 0.2s'
                    }}
                    onMouseEnter={e => e.currentTarget.style.background = T.panelAlt}
                    onMouseLeave={e => e.currentTarget.style.background = T.surface}
                    aria-label={showWatchlist ? 'Collapse watchlist' : 'Expand watchlist'}
                  >
                    <span style={{
                      fontSize: 14,
                      color: showWatchlist ? T.accent : T.textMid,
                      transform: showWatchlist ? 'rotate(180deg)' : 'rotate(0deg)',
                      transition: 'transform 0.3s ease, color 0.2s'
                    }}>
                      ◀
                    </span>
                  </button>

                  {/* CENTER — Chart and Bottom Console */}
                  <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, background: T.bg }}>
                    {/* Interval picker & Indicator Toggles */}
                    <div style={{ padding: '8px 16px', borderBottom: `1px solid ${T.border}`, display: 'flex', alignItems: 'center', gap: 6, background: T.surface, flexWrap: 'wrap' }}>
                      {INTERVALS.map((intv, i) => (
                        <button key={intv.label} onClick={() => setIvIdx(i)} style={{
                          padding: '4px 11px', border: `1px solid ${ivIdx === i ? T.accent : T.border}`,
                          borderRadius: 5, cursor: 'pointer', fontSize: 10, fontWeight: 700,
                          background: ivIdx === i ? T.blueDim : 'transparent',
                          color: ivIdx === i ? T.accent : T.textMid,
                          fontFamily: "'Inter', sans-serif", letterSpacing: '0.06em',
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
                            fontFamily: "'Inter', sans-serif", letterSpacing: '0.04em',
                            transition: 'all 0.15s',
                          }}>{label}</button>
                        );
                      })}

                      <div style={{ marginLeft: 'auto', fontSize: 10, color: T.textDim, fontFamily: "'IBM Plex Mono', monospace" }}>
                        {INTERVALS[ivIdx].interval} · {INTERVALS[ivIdx].range}
                      </div>
                    </div>

                    {/* Chart */}
                    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
                      <CandleChart 
                        key={`${selected}-${INTERVALS[ivIdx].interval}-${INTERVALS[ivIdx].range}-${indicators.rsi}-${indicators.macd}`} 
                        symbol={selected} 
                        interval={INTERVALS[ivIdx].interval} 
                        range={INTERVALS[ivIdx].range} 
                        indicators={indicators} 
                        livePrice={prices[selected]}
                        markers={tradeMarkers[selected] || EMPTY_ARRAY}
                        onLastBarUpdate={handleLastBarUpdate}
                      />
                    </div>

                    {/* Bottom Console Tray */}
                    <BottomConsole 
                      prices={prices} 
                      portfolio={portfolio} 
                      cash={cash} 
                      openOrders={openOrders} 
                      onCancelOrder={handleCancelOrder} 
                      priceAlerts={priceAlerts} 
                      onDeleteAlert={handleDeleteAlert}
                      aiRecommendation={aiRecommendation}
                      aiRecommendationLoading={aiRecommendationLoading}
                      selected={selected}
                      onExecuteOrder={handleExecuteOrder}
                      onViewChange={setView}
                      consoleTab={consoleTab}
                      setConsoleTab={setConsoleTab}
                      onRefreshAnalyst={() => setRefreshAnalystToken(prev => prev + 1)}
                    />
                  </div>

                  {/* RIGHT — Tabbed panel (Bot Engine) */}
                  <div style={{ width: 360, flexShrink: 0, borderLeft: `1px solid ${T.border}`, background: T.surface, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                    {/* Tab header */}
                    <div style={{ display: 'flex', borderBottom: `1px solid ${T.border}`, flexShrink: 0, background: T.panelAlt }}>
                      {['BOT ENGINE', 'TRADE LOG', 'STRATEGIES', 'BACKTEST'].map(tab => (
                        <button key={tab} onClick={() => setRightTab(tab)} style={{
                          flex: 1, padding: '10px 4px', border: 'none', cursor: 'pointer',
                          background: 'transparent',
                          borderBottom: `2px solid ${rightTab === tab ? T.accent : 'transparent'}`,
                          color: rightTab === tab ? T.text : T.textDim,
                          fontSize: 8.5, fontWeight: 700, letterSpacing: '0.04em',
                          fontFamily: "'Inter', sans-serif", transition: 'all 0.2s',
                        }}>
                          {tab}
                        </button>
                      ))}
                    </div>
                    {/* Tab content */}
                    <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
                      {rightTab === 'BOT ENGINE' && (
                        <div style={{ flex: 1, overflow: 'hidden', padding: 12 }}>
                          <BotControlPanel isPaperMode={botPaperMode} onModeChange={setBotPaperMode} />
                        </div>
                      )}
                      {rightTab === 'TRADE LOG' && (
                        <div style={{ flex: 1, overflow: 'hidden', padding: 12 }}>
                          <TradeLogPanel />
                        </div>
                      )}
                      {rightTab === 'STRATEGIES' && (
                        <div style={{ flex: 1, overflow: 'hidden', padding: 12 }}>
                          <StrategySelector selectedStrategy={selectedStrategy} onSelectStrategy={setSelectedStrategy} performanceData={strategyPerformance} />
                        </div>
                      )}
                      {rightTab === 'BACKTEST' && (
                        <div style={{ flex: 1, overflow: 'hidden', padding: 12 }}>
                          <BacktestRunner onResults={setBacktestResults} />
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
        
        {/* Morning Brief Modal */}
        {showBriefModal && (
          <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.85)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 9999, padding: 20 }}>
            <div style={{ background: T.surface, padding: 30, borderRadius: 12, border: `1px solid ${T.accent}`, width: '100%', maxWidth: 500, display: 'flex', flexDirection: 'column', gap: 20, boxShadow: `0 0 40px ${T.accentDim}` }}>
              <div>
                <h2 style={{ margin: 0, color: T.text, fontFamily: "'IBM Plex Mono', monospace", fontSize: 18 }}>🌅 MORNING MARKET BRIEF</h2>
                <div style={{ color: T.textMid, fontSize: 12, marginTop: 4 }}>Top 3 algorithmic signals for today's open.</div>
              </div>
              
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {morningSignals.length === 0 ? (
                  <div style={{ color: T.textMid, fontSize: 13, textAlign: 'center', padding: 20 }}>No high-confidence signals found at open.</div>
                ) : morningSignals.map((s, i) => (
                  <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: 16, background: T.bg, border: `1px solid ${T.borderHi}`, borderRadius: 8 }}>
                    <div>
                      <div style={{ color: T.text, fontWeight: 'bold', fontFamily: "'IBM Plex Mono', monospace" }}>{s.symbol}</div>
                      <div style={{ color: s.action === 'BUY' ? T.green : T.red, fontSize: 12, fontWeight: 'bold' }}>{s.action} @ ₹{fmt(s.current_price)}</div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <div style={{ color: T.textMid, fontSize: 11 }}>Target: <span style={{color: T.text}}>₹{fmt(s.target)}</span></div>
                      <div style={{ color: T.textMid, fontSize: 11 }}>Stop: <span style={{color: T.text}}>₹{fmt(s.stop_loss)}</span></div>
                    </div>
                  </div>
                ))}
              </div>
              
              <button onClick={() => setShowBriefModal(false)} style={{ background: T.accent, color: '#fff', border: 'none', padding: '12px', borderRadius: 6, fontWeight: 'bold', cursor: 'pointer', fontFamily: "'IBM Plex Mono', monospace", marginTop: 10 }}>ACKNOWLEDGE</button>
            </div>
          </div>
        )}
      </div>
    </>
  );
}

