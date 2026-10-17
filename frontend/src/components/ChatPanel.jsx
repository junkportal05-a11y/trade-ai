import React, { useState, useEffect, useRef, useCallback } from 'react';
import MdText from './MdText';
import { API_BASE_URL } from '../api';
import { T } from '../theme';

export default function ChatPanel({ symbol, price, changePct }) {
  const [msgs, setMsgs] = useState([{ role: 'assistant', text: `Greetings! I'm your AI Trading Mentor. Ask me any questions about trading strategies, candlestick patterns (Candlestick Bible), risk management (SL Guide), or technical indicators.` }]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [aiSource, setAiSource] = useState(null);
  const bottomRef = useRef();
  const inputRef = useRef();

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [msgs]);

  const send = useCallback(async () => {
    if (!input.trim() || busy) return;
    const userMsg = input.trim();
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
            <div style={{ maxWidth: '88%', padding: '9px 13px', borderRadius: m.role === 'user' ? '12px 12px 3px 12px' : '12px 12px 12px 3px', background: m.role === 'user' ? T.blueDim : T.panel, border: `1px solid ${m.role === 'user' ? T.accent : T.border}`, fontSize: 12, lineHeight: 1.6, color: T.text }}><MdText text={m.text} /></div>
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
          onBlur={e => e.target.style.borderColor = T.borderHi} />
        <button onClick={send} disabled={!input.trim() || busy} style={{ padding: '9px 14px', background: input.trim() ? T.accent : T.border, border: 'none', borderRadius: 8,
          color: input.trim() ? '#fff' : T.textDim, fontSize: 11, fontWeight: 700, cursor: input.trim() ? 'pointer' : 'not-allowed', transition: 'all 0.2s',
          fontFamily: "'IBM Plex Mono', monospace" }}>ASK</button>
      </div>
    </div>
  );
}