import React, { useState, useEffect, useRef, useCallback } from 'react';
import { T, escapeHTML } from '../theme.js';
import { calcEMA, calcBollingerBands, calcRSI, calcMACD } from '../utils/indicators';
import { createChart, CandlestickSeries, LineSeries, HistogramSeries, createSeriesMarkers } from 'lightweight-charts';

export default function CandleChart({ symbol, interval, range, indicators, livePrice, markers, onLastBarUpdate, drawMode, onDrawComplete, customLines = [], botPaperMode }) {
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
  const [bars, setBars] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(`${import.meta.env.VITE_API_URL || ''}/api/history?symbol=${symbol}&interval=${interval}&range=${range}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json = await res.json();
        setBars(json.bars || []);
      } catch (e) { setError(e.message); }
      finally { setLoading(false); }
    })();
  }, [symbol, interval, range]);

  useEffect(() => {
    if (loading || !bars.length) return;
    if (mainContainerRef.current) mainContainerRef.current.innerHTML = '';
    if (rsiContainerRef.current) rsiContainerRef.current.innerHTML = '';
    if (macdContainerRef.current) macdContainerRef.current.innerHTML = '';
    const mainEl = mainContainerRef.current;
    if (!mainEl) return;
    const mainChart = createChart(mainEl, {
      width: mainEl.clientWidth, height: mainEl.clientHeight,
      layout: { background: { type: 'solid', color: 'transparent' }, textColor: T.textMid, fontSize: 11, fontFamily: "'IBM Plex Mono', monospace" },
      grid: { vertLines: { color: T.border }, horzLines: { color: T.border } },
      crosshair: { vertLine: { color: T.borderHi, width: 1, style: 3 }, horzLine: { color: T.borderHi, width: 1, style: 3 } },
      rightPriceScale: { borderColor: T.border, textColor: T.textMid },
      timeScale: { borderColor: T.border, textColor: T.textMid, timeVisible: true },
    });
    mainChartRef.current = mainChart;
    const candleSeries = mainChart.addSeries(CandlestickSeries, {
      upColor: T.green, downColor: T.red, borderVisible: false, wickUpColor: T.green, wickDownColor: T.red, priceScaleId: 'right',
    });
    candleSeries.setData(bars);
    candleSeriesRef.current = candleSeries;
    seriesMarkersRef.current = createSeriesMarkers(candleSeries, markers || []);
    mainChart.subscribeCrosshairMove((param) => {
      const legend = legendRef.current;
      if (!legend) return;
      if (!param.time || !param.point || param.point.x < 0 || param.point.y < 0) { legend.style.display = 'none'; return; }
      const data = param.seriesData.get(candleSeries);
      if (data) {
        legend.style.display = 'block';
        const color = data.close >= data.open ? T.green : T.red;
        legend.innerHTML = `<div style="font-weight: 700; margin-bottom: 4px; color: ${T.text}; font-size: 14px;">${escapeHTML(symbol)} <span style="color: ${T.textMid}; font-size: 11px;">(${escapeHTML(interval)})</span></div>
          <div style="display: flex; gap: 14px; font-size: 12px; color: ${T.text};">
            <span>O <span style="color: ${color}">${data.open.toFixed(2)}</span></span>
            <span>H <span style="color: ${color}">${data.high.toFixed(2)}</span></span>
            <span>L <span style="color: ${color}">${data.low.toFixed(2)}</span></span>
            <span>C <span style="color: ${color}">${data.close.toFixed(2)}</span></span>
          </div>`;
      } else { legend.style.display = 'none'; }
    });
    mainChart.subscribeClick((param) => {
      if (!param.point || !drawMode) return;
      const price = candleSeries.coordinateToPrice(param.point.y);
      if (price !== null && onDrawComplete) onDrawComplete({ price, type: drawMode, id: Date.now() });
    });
    const volSeries = mainChart.addSeries(HistogramSeries, { priceFormat: { type: 'volume' }, priceScaleId: 'vol', color: 'rgba(77,159,255,0.25)' });
    const volData = bars.map(b => ({ time: b.time, value: b.volume || 0, color: b.close >= b.open ? 'rgba(0,216,160,0.22)' : 'rgba(255,78,106,0.22)' }));
    volSeries.setData(volData);
    volSeriesRef.current = volSeries;
    mainChart.priceScale('vol').applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });
    if (indicators.ema9) {
      const ema9Data = calcEMA(bars, 9);
      const ema9Series = mainChart.addSeries(LineSeries, { color: '#00e5a8', lineWidth: 1.5, title: 'EMA 9' });
      ema9Series.setData(ema9Data);
    }
    if (indicators.ema21) {
      const ema21Data = calcEMA(bars, 21);
      const ema21Series = mainChart.addSeries(LineSeries, { color: '#ff9f43', lineWidth: 1.5, title: 'EMA 21' });
      ema21Series.setData(ema21Data);
    }
    if (indicators.bb) {
      const bbData = calcBollingerBands(bars, 20, 2);
      mainChart.addSeries(LineSeries, { color: 'rgba(123,108,255,0.6)', lineWidth: 1 }).setData(bbData.upper);
      mainChart.addSeries(LineSeries, { color: 'rgba(123,108,255,0.3)', lineWidth: 1, lineStyle: 2 }).setData(bbData.middle);
      mainChart.addSeries(LineSeries, { color: 'rgba(123,108,255,0.6)', lineWidth: 1 }).setData(bbData.lower);
    }
    customLines.forEach(line => {
      candleSeries.createPriceLine({ price: line.price, color: line.type === 'SUPPORT' ? T.green : T.red, lineWidth: 2, lineStyle: 1, axisLabelVisible: true, title: line.type === 'SUPPORT' ? 'SUP' : 'RES' });
    });
    const targets = [];
    if (indicators.rsi && rsiContainerRef.current) {
      const rsiEl = rsiContainerRef.current;
      const rsiChart = createChart(rsiEl, {
        width: rsiEl.clientWidth, height: rsiEl.clientHeight,
        layout: { background: { type: 'solid', color: 'transparent' }, textColor: T.textMid, fontSize: 10, fontFamily: "'IBM Plex Mono', monospace" },
        grid: { vertLines: { color: T.border }, horzLines: { color: T.border } },
        rightPriceScale: { borderColor: T.border, textColor: T.textMid, visible: true },
        timeScale: { borderColor: T.border, visible: false },
      });
      rsiChartRef.current = rsiChart;
      targets.push(rsiChart);
      const rsiSeries = rsiChart.addSeries(LineSeries, { color: '#7b6cff', lineWidth: 1.5 });
      rsiSeries.setData(calcRSI(bars, 14));
      rsiSeries.createPriceLine({ price: 70, color: 'rgba(255,61,90,0.4)', lineWidth: 1, lineStyle: 3, axisLabelVisible: true });
      rsiSeries.createPriceLine({ price: 30, color: 'rgba(0,229,168,0.4)', lineWidth: 1, lineStyle: 3, axisLabelVisible: true });
      rsiChart.priceScale('right').applyOptions({ autoScale: false, min: 0, max: 100 });
    }
    if (indicators.macd && macdContainerRef.current) {
      const macdEl = macdContainerRef.current;
      const macdChart = createChart(macdEl, {
        width: macdEl.clientWidth, height: macdEl.clientHeight,
        layout: { background: { type: 'solid', color: 'transparent' }, textColor: T.textMid, fontSize: 10, fontFamily: "'IBM Plex Mono', monospace" },
        grid: { vertLines: { color: T.border }, horzLines: { color: T.border } },
        rightPriceScale: { borderColor: T.border, textColor: T.textMid, visible: true },
        timeScale: { borderColor: T.border, visible: false },
      });
      macdChartRef.current = macdChart;
      targets.push(macdChart);
      const macdData = calcMACD(bars);
      const macdHistSeries = macdChart.addSeries(HistogramSeries, { priceScaleId: 'right' });
      macdHistSeries.setData(macdData.histogram.map(h => ({ time: h.time, value: h.value, color: h.value >= 0 ? 'rgba(0,229,168,0.3)' : 'rgba(255,61,90,0.3)' })));
      macdChart.addSeries(LineSeries, { color: '#4da6ff', lineWidth: 1.2 }).setData(macdData.macdLine.map(m => ({ time: m.time, value: m.value })));
      macdChart.addSeries(LineSeries, { color: '#f5c842', lineWidth: 1.2 }).setData(macdData.signalLine.map(s => ({ time: s.time, value: s.value })));
    }
    if (targets.length > 0) {
      mainChart.timeScale().subscribeVisibleTimeRangeChange(() => {
        const range = mainChart.timeScale().getVisibleRange();
        if (range) targets.forEach(t => t.timeScale().setVisibleRange(range));
      });
    }
    mainChart.timeScale().fitContent();
    const ro = new ResizeObserver(() => {
      if (!mainEl) return;
      mainChart.applyOptions({ width: mainEl.clientWidth, height: mainEl.clientHeight });
      if (rsiChartRef.current && rsiContainerRef.current) rsiChartRef.current.applyOptions({ width: mainEl.clientWidth, height: rsiContainerRef.current.clientHeight });
      if (macdChartRef.current && macdContainerRef.current) macdChartRef.current.applyOptions({ width: mainEl.clientWidth, height: macdContainerRef.current.clientHeight });
    });
    ro.observe(mainEl);
    return () => { ro.disconnect(); mainChart.remove(); rsiChartRef.current?.remove(); macdChartRef.current?.remove(); };
  }, [bars, loading, indicators]);

  useEffect(() => {
    if (!livePrice || !bars.length || !candleSeriesRef.current) return;
    const lastBar = bars[bars.length - 1];
    if (!lastBar) return;
    const price = livePrice.price;
    if (!liveTickRef.current || liveTickRef.current.time !== lastBar.time) {
      liveTickRef.current = { time: lastBar.time, open: lastBar.open, high: lastBar.high, low: lastBar.low, close: lastBar.close, volume: lastBar.volume || 0 };
    }
    liveTickRef.current.high = Math.max(liveTickRef.current.high, price);
    liveTickRef.current.low = Math.min(liveTickRef.current.low, price);
    liveTickRef.current.close = price;
    candleSeriesRef.current.update(liveTickRef.current);
    if (volSeriesRef.current) {
      volSeriesRef.current.update({ time: liveTickRef.current.time, value: liveTickRef.current.volume, color: liveTickRef.current.close >= liveTickRef.current.open ? 'rgba(0,216,160,0.22)' : 'rgba(255,78,106,0.22)' });
    }
  }, [livePrice, bars]);

  useEffect(() => {
    if (seriesMarkersRef.current && !loading) seriesMarkersRef.current.setMarkers(markers || []);
  }, [markers, loading, bars]);

  useEffect(() => {
    if (bars && bars.length > 0 && onLastBarUpdate) onLastBarUpdate(bars[bars.length - 1].time);
  }, [bars, onLastBarUpdate]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, height: '100%', minHeight: 0, overflow: 'hidden', position: 'relative' }}>
      {loading && <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(10,12,16,0.7)', zIndex: 2, gap: 10, color: T.textMid, fontSize: 13, letterSpacing: '0.05em' }}>
        <span style={{ display: 'inline-block', width: 14, height: 14, border: `2px solid ${T.border}`, borderTopColor: T.accent, borderRadius: '50%', animation: 'spin 0.7s linear infinite' }} />
        LOADING MARKET DATA
      </div>}
      {!loading && error && <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', background: 'rgba(10,12,16,0.9)', zIndex: 2, gap: 12, color: T.red, fontSize: 13, letterSpacing: '0.05em', padding: 20, textAlign: 'center' }}>
        <span style={{ fontSize: 24 }}>⚠️</span>
        <div style={{ fontWeight: 600 }}>ERROR LOADING MARKET DATA: {error}</div>
        <div style={{ fontSize: 11, color: T.textDim, marginTop: 4, maxWidth: 300, lineHeight: 1.4 }}>Live market data unavailable. Please go to the ACCOUNT panel to authenticate with AngelOne Broker.</div>
      </div>}
      {!loading && !error && !bars.length && <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', background: 'rgba(10,12,16,0.9)', zIndex: 2, gap: 12, color: T.textMid, fontSize: 13, letterSpacing: '0.05em' }}>
        <span style={{ fontSize: 24 }}>📭</span>
        <div style={{ fontWeight: 600 }}>NO HISTORICAL DATA FOUND FOR {symbol}</div>
      </div>}
      <div style={{ flex: 3, minHeight: 0, position: 'relative' }}>
        <div ref={legendRef} style={{ position: 'absolute', top: 12, left: 12, zIndex: 10, fontFamily: "'IBM Plex Mono', monospace", pointerEvents: 'none', background: 'rgba(13,16,24,0.65)', backdropFilter: 'blur(4px)', padding: '8px 12px', borderRadius: 6, display: 'none', border: `1px solid ${T.borderHi}` }} />
        {botPaperMode === true && <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', zIndex: 1, pointerEvents: 'none', color: 'rgba(255,255,255,0.05)', fontSize: '8vw', fontWeight: 900, whiteSpace: 'nowrap', userSelect: 'none' }}>SIMULATION MODE</div>}
        {botPaperMode === false && <div style={{ position: 'absolute', top: 12, right: 12, zIndex: 10, background: T.red, color: '#fff', fontSize: 11, fontWeight: 800, padding: '4px 8px', borderRadius: 4, letterSpacing: '0.05em' }}>LIVE BROKER</div>}
        <div ref={mainContainerRef} style={{ position: 'absolute', inset: 0, zIndex: 2 }} />
      </div>
      {indicators.rsi && (
        <div style={{ height: 95, borderTop: `1px solid ${T.border}`, position: 'relative', background: T.surface, flexShrink: 0 }}>
          <div style={{ position: 'absolute', top: 4, left: 12, zIndex: 5, fontSize: 9, color: T.textMid, fontFamily: "'IBM Plex Mono', monospace", fontWeight: 700 }}>RSI (14)</div>
          <div ref={rsiContainerRef} style={{ position: 'absolute', inset: 0 }} />
        </div>
      )}
      {indicators.macd && (
        <div style={{ height: 110, borderTop: `1px solid ${T.border}`, position: 'relative', background: T.surface, flexShrink: 0 }}>
          <div style={{ position: 'absolute', top: 4, left: 12, zIndex: 5, fontSize: 9, color: T.textMid, fontFamily: "'IBM Plex Mono', monospace", fontWeight: 700 }}>MACD (12, 26, 9)</div>
          <div ref={macdContainerRef} style={{ position: 'absolute', inset: 0 }} />
        </div>
      )}
    </div>
  );
}