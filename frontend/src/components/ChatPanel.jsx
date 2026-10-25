import React, { useState, useEffect, useRef, useCallback } from 'react';
import MdText from './MdText';
import { API_BASE_URL } from '../api';
import { T } from '../theme';

export default function ChatPanel({ symbol, price, changePct }) {
  const [msgs, setMsgs] = useState([{ role: 'assistant', text: `Greetings! I'm your AI Trading Mentor. Ask me any questions about trading strategies, candlestick patterns (Candlestick Bible), risk management (SL Guide), or technical indicators.` }]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [aiSource, setAiSource] = useState(null);
  const [chartAnalysis, setChartAnalysis] = useState(null);
  const [showReasoning, setShowReasoning] = useState(false);
  const bottomRef = useRef();
  const inputRef = useRef();
  const fileInputRef = useRef();

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [msgs]);

  const send = useCallback(async (override) => {
    const text = typeof override === 'string' ? override : input;
    if (!text.trim() || busy) return;
    const userMsg = text.trim();
    setInput('');
    setMsgs(m => [...m, { role: 'user', text: userMsg }]);
    setBusy(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/chat`, {
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
      // Store full message with confidence and reasoning
      setMsgs(m => [...m, { 
        role: 'assistant', 
        text: data.reply || 'No response.',
        confidence: data.confidence,
        reasoning: data.reasoning
      }]);
    } catch {
      setMsgs(m => [...m, { role: 'assistant', text: "AI Mentor is currently unavailable. Please check backend connection." }]);
    }
    setBusy(false);
  }, [input, busy, symbol, price, changePct, msgs]);

  const analyzeChart = useCallback(async (file) => {
    if (!file) return;
    if (file.size > 10 * 1024 * 1024) {
      alert('File too large (max 10MB)');
      return;
    }
    if (!file.type.match(/^image\/(png|jpeg|jpg)$/)) {
      alert('Only PNG/JPEG images supported');
      return;
    }
    setBusy(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await fetch(`${API_BASE_URL}/api/chat/chart/upload`, {
        method: 'POST',
        body: formData,
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Chart analysis failed');
      }
      const data = await res.json();
      setChartAnalysis(data);
      setMsgs(m => [...m, { 
        role: 'assistant', 
        text: `Chart analysis complete for ${file.name}.`,
        confidence: data.confidence,
        reasoning: data.notes,
        chartAnalysis: data
      }]);
    } catch (err) {
      setMsgs(m => [...m, { role: 'assistant', text: `Chart analysis failed: ${err.message}` }]);
    }
    setBusy(false);
  }, []);

  const onKey = (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } };
  const SUGGESTIONS = ['Scan Breakouts', 'Support & Resistance', 'Verify VWAP Veto', 'Explain Market Regime'];

  const renderMessage = (m, i) => (
    <div key={i} style={{ display: 'flex', justifyContent: m.role === 'user' ? 'flex-end' : 'flex-start', animation: 'fadeIn 0.2s ease' }}>
      <div style={{ maxWidth: '88%', padding: '9px 13px', borderRadius: m.role === 'user' ? '12px 12px 3px 12px' : '12px 12px 12px 3px', background: m.role === 'user' ? T.blueDim : T.panel, border: `1px solid ${m.role === 'user' ? T.accent : T.border}`, fontSize: 12, lineHeight: 1.6, color: T.text }}>
        <MdText text={m.text} />
        {m.confidence !== undefined && m.role === 'assistant' && (
          <div style={{ marginTop: 8, paddingTop: 8, borderTop: `1px solid ${T.border}`, display: 'flex', flexDirection: 'column', gap: 6 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: 10, fontWeight: 700, color: T.textMid, fontFamily: "'IBM Plex Mono', monospace" }}>CONFIDENCE</span>
              <div style={{ flex: 1, height: 4, background: T.border, borderRadius: 2, overflow: 'hidden' }}>
                <div style={{ width: `${Math.round(m.confidence * 100)}%`, height: '100%', background: m.confidence > 0.7 ? T.green : m.confidence > 0.4 ? T.yellow : T.red, transition: 'width 0.3s' }} />
              </div>
              <span style={{ fontSize: 10, fontWeight: 700, color: m.confidence > 0.7 ? T.green : m.confidence > 0.4 ? T.yellow : T.red, fontFamily: "'IBM Plex Mono', monospace" }}>
                {Math.round(m.confidence * 100)}%
              </span>
            </div>
            {m.reasoning && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <button 
                  onClick={() => setShowReasoning(!showReasoning)}
                  style={{ fontSize: 9, padding: '2px 8px', borderRadius: 12, border: `1px solid ${T.borderHi}`, background: showReasoning ? T.accent : 'transparent', color: showReasoning ? '#fff' : T.textMid, cursor: 'pointer', fontFamily: "'IBM Plex Mono', monospace", fontWeight: 700 }}
                >
                  {showReasoning ? 'HIDE REASONING' : 'SHOW REASONING'}
                </button>
              </div>
            )}
            {showReasoning && m.reasoning && (
              <div style={{ fontSize: 10, color: T.textMid, fontStyle: 'italic', padding: '8px 12px', background: T.bg, borderRadius: 6, border: `1px solid ${T.border}` }}>
                {m.reasoning}
              </div>
            )}
            {m.chartAnalysis && (
              <div style={{ marginTop: 8, padding: 10, background: T.bg, borderRadius: 8, border: `1px solid ${T.border}`, fontSize: 10 }}>
                <div style={{ fontSize: 10, fontWeight: 700, color: T.text, marginBottom: 6, fontFamily: "'IBM Plex Mono', monospace" }}>CHART ANALYSIS</div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <div style={{ color: T.textMid, fontSize: 9 }}>TREND</div>
                    <div style={{ color: m.chartAnalysis.trend === 'bullish' ? T.green : m.chartAnalysis.trend === 'bearish' ? T.red : T.yellow, fontWeight: 700 }}>
                      {m.chartAnalysis.trend.toUpperCase()}
                    </div>
                  </div>
                  <div>
                    <div style={{ color: T.textMid, fontSize: 9 }}>BREAKOUT</div>
                    <div style={{ color: m.chartAnalysis.breakout_signal === 'up' ? T.green : m.chartAnalysis.breakout_signal === 'down' ? T.red : T.textMid, fontWeight: 700 }}>
                      {m.chartAnalysis.breakout_signal?.toUpperCase() || 'NONE'}
                    </div>
                  </div>
                  <div style={{ gridColumn: '1 / -1' }}>
                    <div style={{ color: T.textMid, fontSize: 9 }}>SUPPORT LEVELS</div>
                    <div style={{ color: T.green, fontFamily: "'IBM Plex Mono', monospace" }}>
                      {m.chartAnalysis.support_levels?.length ? m.chartAnalysis.support_levels.map((l, i) => <div key={i}>₹{l.toLocaleString()}</div>) : 'None'}
                    </div>
                  </div>
                  <div style={{ gridColumn: '1 / -1' }}>
                    <div style={{ color: T.textMid, fontSize: 9 }}>RESISTANCE LEVELS</div>
                    <div style={{ color: T.red, fontFamily: "'IBM Plex Mono', monospace" }}>
                      {m.chartAnalysis.resistance_levels?.length ? m.chartAnalysis.resistance_levels.map((l, i) => <div key={i}>₹{l.toLocaleString()}</div>) : 'None'}
                    </div>
                  </div>
                  <div style={{ gridColumn: '1 / -1' }}>
                    <div style={{ color: T.textMid, fontSize: 9 }}>PATTERNS</div>
                    <div style={{ color: T.text }}>
                      {m.chartAnalysis.patterns?.length ? m.chartAnalysis.patterns.map((p, i) => <div key={i}>{p}</div>) : 'None'}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );

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
        {msgs.map((m, i) => renderMessage(m, i))}
        {busy && (
          <div style={{ display: 'flex', gap: 4, padding: '10px 14px' }}>
            {[0,1,2].map(i => <span key={i} style={{ width: 5, height: 5, borderRadius: '50%', background: T.accent, animation: `bounce 1s ${i * 0.2}s ease-in-out infinite` }} />)}
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div style={{ padding: '0 12px 8px', display: 'flex', flexWrap: 'wrap', gap: 5 }}>
        {SUGGESTIONS.map(s => (
          <button key={s} onClick={() => send(s)} disabled={busy}
            style={{ fontSize: 9, padding: '4px 8px', borderRadius: 12, border: `1px solid ${T.borderHi}`, background: 'transparent', color: T.textMid, cursor: busy ? 'wait' : 'pointer', fontFamily: "'IBM Plex Mono', monospace", transition: 'all 0.15s' }}
            onMouseEnter={e => { e.target.style.borderColor = T.accent; e.target.style.color = T.accent; }}
            onMouseLeave={e => { e.target.style.borderColor = T.borderHi; e.target.style.color = T.textMid; }}
          >{s}</button>
        ))}
      </div>

      <div style={{ padding: '10px 12px', borderTop: `1px solid ${T.border}`, display: 'flex', flexDirection: 'column', gap: 8 }}>
        <div style={{ display: 'flex', gap: 8 }}>
          <input 
            ref={fileInputRef} 
            type="file" 
            accept="image/png,image/jpeg" 
            style={{ display: 'none' }} 
            onChange={e => e.target.files[0] && analyzeChart(e.target.files[0])}
          />
          <button 
            onClick={() => fileInputRef.current?.click()}
            disabled={busy}
            style={{ padding: '9px 12px', background: T.panel, border: `1px solid ${T.borderHi}`, borderRadius: 8, color: T.text, fontSize: 11, fontWeight: 700, cursor: busy ? 'not-allowed' : 'pointer', transition: 'all 0.2s', fontFamily: "'IBM Plex Mono', monospace", display: 'flex', alignItems: 'center', gap: 6 }}
            title="Upload chart image for AI analysis (PNG/JPEG, max 10MB)"
          >
            <span style={{ fontSize: 14 }}>📸</span>
            <span>ANALYZE CHART</span>
          </button>
          <input ref={inputRef} value={input} onChange={e => setInput(e.target.value)} onKeyDown={onKey}
            placeholder="Ask the AI Mentor anything (e.g. Hammer candlestick, 2% risk)..."
            style={{ flex: 1, background: T.bg, border: `1px solid ${T.borderHi}`, borderRadius: 8, padding: '9px 12px', color: T.text, fontSize: 12, outline: 'none', fontFamily: 'inherit', transition: 'border-color 0.2s' }}
            onFocus={e => e.target.style.borderColor = T.accent}
            onBlur={e => e.target.style.borderColor = T.borderHi} />
          <button onClick={send} disabled={!input.trim() || busy} style={{ padding: '9px 14px', background: input.trim() ? T.accent : T.border, border: 'none', borderRadius: 8,
            color: input.trim() ? '#fff' : T.textDim, fontSize: 11, fontWeight: 700, cursor: input.trim() ? 'pointer' : 'not-allowed', transition: 'all 0.2s',
            fontFamily: "'IBM Plex Mono', monospace" }}>ASK</button>
        </div>
      </div>
    </div>
  );
}