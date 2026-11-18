import React, { useCallback, useEffect, useRef, useState } from 'react';
import { BarChart3, Camera, ChevronDown, ChevronUp, ShieldCheck, Sparkles, Target, Zap } from 'lucide-react';
import MdText from './MdText';
import { apiFetch } from '../api';
import { T } from '../theme';

const SUGGESTIONS = [
  { label: 'Scan Breakouts', icon: Zap },
  { label: 'Support & Resistance', icon: Target },
  { label: 'Verify VWAP Veto', icon: ShieldCheck },
  { label: 'Explain Market Regime', icon: BarChart3 },
];

const confidenceColor = (value) => value > 0.7 ? T.green : value > 0.4 ? T.gold : T.red;

function priceList(levels) {
  if (!levels?.length) return 'None';
  return levels.map(level => `₹${Number(level).toLocaleString('en-IN')}`).join(' · ');
}

export default function ChatPanel({ symbol, price, changePct }) {
  const [msgs, setMsgs] = useState([{
    role: 'assistant',
    text: "Greetings! I'm your AI Trading Mentor. Ask me any questions about trading strategies, candlestick patterns (Candlestick Bible), risk management (SL Guide), or technical indicators.",
  }]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [aiSource, setAiSource] = useState(null);
  const [openReasoning, setOpenReasoning] = useState({});
  const bottomRef = useRef();
  const fileInputRef = useRef();

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [msgs, busy]);

  const send = useCallback(async (override) => {
    const text = typeof override === 'string' ? override : input;
    if (!text.trim() || busy) return;
    const userMsg = text.trim();
    setInput('');
    setMsgs(m => [...m, { role: 'user', text: userMsg }]);
    setBusy(true);
    try {
      const res = await apiFetch('/api/chat', {
        method: 'POST',
        body: JSON.stringify({
          message: userMsg,
          context: { symbol: symbol.replace('.NS', ''), price, changePct },
          history: msgs.map(m => ({ role: m.role, text: m.text })),
        }),
      });
      if (res.status === 401) {
        localStorage.removeItem('is_logged_in');
        localStorage.removeItem('apex_user');
        localStorage.removeItem('apt_token');
        localStorage.removeItem('apt_csrf');
        sessionStorage.removeItem('apt_token');
        sessionStorage.removeItem('apt_csrf');
        window.location.reload();
        return;
      }
      if (!res.ok) throw new Error('backend unavailable');
      const data = await res.json();
      setAiSource(data.source);
      setMsgs(m => [...m, {
        role: 'assistant',
        text: data.reply || 'No response.',
        confidence: data.confidence,
        reasoning: data.reasoning,
      }]);
    } catch {
      setMsgs(m => [...m, { role: 'assistant', text: 'AI Mentor is currently unavailable. Please check backend connection.' }]);
    } finally {
      setBusy(false);
    }
  }, [input, busy, symbol, price, changePct, msgs]);

  const analyzeChart = useCallback(async (file) => {
    if (!file) return;
    if (file.size > 10 * 1024 * 1024) {
      setMsgs(m => [...m, { role: 'assistant', text: 'Chart image is too large. Maximum size is 10 MB.' }]);
      return;
    }
    if (!file.type.match(/^image\/(png|jpeg|jpg)$/)) {
      setMsgs(m => [...m, { role: 'assistant', text: 'Only PNG and JPEG chart images are supported.' }]);
      return;
    }
    setBusy(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await apiFetch('/api/chat/chart/upload', { method: 'POST', body: formData });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Chart analysis failed');
      }
      const data = await res.json();
      setAiSource(data.source);
      setMsgs(m => [...m, {
        role: 'assistant',
        text: `Chart analysis complete for ${file.name}.`,
        confidence: data.confidence,
        reasoning: data.notes,
        chartAnalysis: data,
      }]);
    } catch (err) {
      setMsgs(m => [...m, { role: 'assistant', text: `Chart analysis failed: ${err.message}` }]);
    } finally {
      setBusy(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  }, []);

  const onKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  const toggleReasoning = (index) => {
    setOpenReasoning(prev => ({ ...prev, [index]: !prev[index] }));
  };

  const renderMessage = (m, i) => {
    const isUser = m.role === 'user';
    const confidence = Math.max(0, Math.min(1, Number(m.confidence) || 0));
    const color = confidenceColor(confidence);
    const reasoningOpen = Boolean(openReasoning[i]);
    return (
      <div key={i} style={{ display: 'flex', justifyContent: isUser ? 'flex-end' : 'flex-start', animation: 'fadeIn 0.2s ease' }}>
        <div style={{
          maxWidth: '90%',
          padding: '10px 13px',
          borderRadius: isUser ? '12px 12px 3px 12px' : '12px 12px 12px 3px',
          background: isUser ? T.surfaceDim : `linear-gradient(160deg, ${T.panel}, ${T.surface})`,
          border: `1px solid ${isUser ? T.borderHi : T.borderHi}`,
          boxShadow: isUser ? 'none' : `0 6px 18px rgba(0, 0, 0, 0.25), inset 0 0 20px rgba(0, 0, 0, 0.05)`,
          fontSize: 12,
          lineHeight: 1.65,
          color: T.text,
        }}>
          <MdText text={m.text} />

          {!isUser && m.confidence !== undefined && (
            <div style={{ marginTop: 9, paddingTop: 9, borderTop: `1px solid ${T.border}`, display: 'flex', flexDirection: 'column', gap: 7 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ fontSize: 9, fontWeight: 700, color: T.textMid, fontFamily: "'IBM Plex Mono', monospace", letterSpacing: '0.06em' }}>
                  CONFIDENCE
                </span>
                <div style={{ flex: 1, height: 4, background: T.border, borderRadius: 999, overflow: 'hidden' }}>
                  <div style={{
                    width: `${Math.round(confidence * 100)}%`,
                    height: '100%',
                    borderRadius: 999,
                    background: `linear-gradient(90deg, ${color}, ${T.accentAlt})`,
                    transition: 'width 0.35s cubic-bezier(0.16, 1, 0.3, 1)',
                  }} />
                </div>
                <span style={{ fontSize: 10, fontWeight: 700, color, fontFamily: "'IBM Plex Mono', monospace" }}>
                  {Math.round(confidence * 100)}%
                </span>
              </div>

              {m.reasoning && (
                <button
                  onClick={() => toggleReasoning(i)}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 4,
                    alignSelf: 'flex-start',
                    fontSize: 9,
                    padding: '3px 8px',
                    borderRadius: 999,
                    border: `1px solid ${T.borderHi}`,
                    background: reasoningOpen ? T.accentDim : 'transparent',
                    color: reasoningOpen ? T.accentAlt : T.textMid,
                    cursor: 'pointer',
                    fontFamily: "'IBM Plex Mono', monospace",
                    fontWeight: 700,
                  }}
                >
                  {reasoningOpen ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
                  REASONING
                </button>
              )}

              {reasoningOpen && m.reasoning && (
                <div style={{ fontSize: 10, color: T.textMid, fontStyle: 'italic', padding: '8px 10px', background: T.bg, borderRadius: 6, border: `1px solid ${T.border}` }}>
                  {m.reasoning}
                </div>
              )}

              {m.chartAnalysis && (
                <div style={{ marginTop: 2, padding: 10, background: T.bg, borderRadius: 8, border: `1px solid ${T.border}`, fontSize: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 10, fontWeight: 700, color: T.text, marginBottom: 8, fontFamily: "'IBM Plex Mono', monospace" }}>
                    <Sparkles size={12} color={T.accentAlt} />
                    CHART ANALYSIS
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                    <div>
                      <div style={{ color: T.textMid, fontSize: 9 }}>TREND</div>
                      <div style={{ color: m.chartAnalysis.trend === 'bullish' ? T.green : m.chartAnalysis.trend === 'bearish' ? T.red : T.gold, fontWeight: 700 }}>
                        {m.chartAnalysis.trend?.toUpperCase() || 'UNKNOWN'}
                      </div>
                    </div>
                    <div>
                      <div style={{ color: T.textMid, fontSize: 9 }}>BREAKOUT</div>
                      <div style={{ color: m.chartAnalysis.breakout_signal === 'up' ? T.green : m.chartAnalysis.breakout_signal === 'down' ? T.red : T.textMid, fontWeight: 700 }}>
                        {m.chartAnalysis.breakout_signal?.toUpperCase() || 'NONE'}
                      </div>
                    </div>
                    <div style={{ gridColumn: '1 / -1' }}>
                      <div style={{ color: T.textMid, fontSize: 9 }}>SUPPORT</div>
                      <div style={{ color: T.green, fontFamily: "'IBM Plex Mono', monospace" }}>{priceList(m.chartAnalysis.support_levels)}</div>
                    </div>
                    <div style={{ gridColumn: '1 / -1' }}>
                      <div style={{ color: T.textMid, fontSize: 9 }}>RESISTANCE</div>
                      <div style={{ color: T.red, fontFamily: "'IBM Plex Mono', monospace" }}>{priceList(m.chartAnalysis.resistance_levels)}</div>
                    </div>
                    <div style={{ gridColumn: '1 / -1' }}>
                      <div style={{ color: T.textMid, fontSize: 9 }}>PATTERNS</div>
                      <div style={{ color: T.text }}>{m.chartAnalysis.patterns?.join(', ') || 'None'}</div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <div style={{ padding: '13px 16px 10px', borderBottom: `1px solid ${T.border}`, display: 'flex', alignItems: 'center', gap: 8 }}>
        <div style={{ width: 7, height: 7, borderRadius: '50%', background: T.green, boxShadow: `0 0 8px ${T.greenGlow}`, animation: 'pulse 2s ease-in-out infinite' }} />
        <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.12em', color: T.textMid, fontFamily: "'IBM Plex Mono', monospace", flex: 1 }}>
          AI COPILOT
        </span>
        {aiSource && (
          <span style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 4,
            fontSize: 8,
            padding: '2px 7px',
            borderRadius: 999,
            background: aiSource === 'gemini' ? T.goldDim : T.greenDim,
            color: aiSource === 'gemini' ? T.blue : T.green,
            border: `1px solid ${aiSource === 'gemini' ? T.borderHi : T.greenGlow}`,
            fontFamily: "'IBM Plex Mono', monospace",
            letterSpacing: '0.06em',
          }}>
            {aiSource === 'gemini' ? <Sparkles size={9} /> : null}
            {aiSource === 'gemini' ? 'GEMINI 2.0 FLASH' : 'LOCAL'}
          </span>
        )}
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '12px 14px', display: 'flex', flexDirection: 'column', gap: 10 }}>
        {msgs.map(renderMessage)}
        {busy && (
          <div style={{ display: 'flex', gap: 4, padding: '10px 14px' }}>
            {[0, 1, 2].map(i => (
              <span key={i} style={{
                width: 5, height: 5, borderRadius: '50%', background: T.accent,
                animation: `bounce 1s ${i * 0.2}s ease-in-out infinite`,
              }} />
            ))}
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div style={{ padding: '0 12px 8px', display: 'flex', flexWrap: 'wrap', gap: 5 }}>
        {SUGGESTIONS.map(({ label, icon: Icon }) => (
          <button
            key={label}
            onClick={() => send(label)}
            disabled={busy}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 5,
              fontSize: 9,
              padding: '4px 9px',
              borderRadius: 999,
              border: `1px solid ${T.borderHi}`,
              background: T.panel,
              color: T.textMid,
              cursor: busy ? 'wait' : 'pointer',
              fontFamily: "'IBM Plex Mono', monospace",
              transition: 'all 0.15s',
            }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = T.borderHi; e.currentTarget.style.color = T.text; }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = T.borderHi; e.currentTarget.style.color = T.textMid; }}
          >
            <Icon size={11} />
            {label}
          </button>
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
            title="Upload chart image for AI analysis (PNG/JPEG, max 10MB)"
            style={{
              padding: '0 12px',
              background: T.panel,
              border: `1px solid ${T.borderHi}`,
              borderRadius: 8,
              color: T.text,
              cursor: busy ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              fontFamily: "'IBM Plex Mono', monospace",
              fontSize: 10,
              fontWeight: 700,
            }}
          >
            <Camera size={14} />
          </button>
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={onKey}
            placeholder="Ask the AI Mentor anything..."
            style={{
              flex: 1,
              background: T.bg,
              border: `1px solid ${T.borderHi}`,
              borderRadius: 8,
              padding: '9px 12px',
              color: T.text,
              fontSize: 12,
              outline: 'none',
              fontFamily: 'inherit',
              transition: 'border-color 0.2s',
            }}
            onFocus={e => { e.currentTarget.style.borderColor = T.accent; }}
            onBlur={e => { e.currentTarget.style.borderColor = T.borderHi; }}
          />
          <button
            onClick={() => send()}
            disabled={!input.trim() || busy}
            style={{
              padding: '9px 14px',
              background: input.trim() ? `linear-gradient(135deg, ${T.accent}, ${T.accentAlt})` : T.border,
              border: 'none',
              borderRadius: 8,
              color: input.trim() ? T.text : T.textDim,
              fontSize: 11,
              fontWeight: 700,
              cursor: input.trim() ? 'pointer' : 'not-allowed',
              transition: 'all 0.2s',
              fontFamily: "'IBM Plex Mono', monospace",
            }}
          >
            ASK
          </button>
        </div>
      </div>
    </div>
  );
}
