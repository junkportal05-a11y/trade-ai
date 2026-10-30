import React, { useState } from 'react';
import Label from './Label';
import Input from './TextInput';
import { T, fmt } from '../theme';

export default function OrderPanel({ symbol, price, cash, openOrders, onExecuteOrder, onCancelOrder, priceAlerts = [], onAddAlert, onDeleteAlert, hasLiveTick = false }) {
  const [side, setSide] = useState('buy');
  const [qty, setQty] = useState('');
  const [type, setType] = useState('market');
  const [limit, setLimit] = useState('');
  const [status, setStatus] = useState(null);
  const [alertCondition, setAlertCondition] = useState('above');
  const [alertPrice, setAlertPrice] = useState('');
  const [limitError, setLimitError] = useState(false);
  const marketBlocked = type === 'market' && !hasLiveTick;

  const executionPrice = type === 'limit' ? (limit ? parseFloat(limit) : NaN) : price;
  const total = qty && !isNaN(executionPrice) ? (parseFloat(qty) * executionPrice).toFixed(2) : '—';

  const submit = () => {
    if (type === 'limit' && (!limit || isNaN(parseFloat(limit)))) {
      setLimitError(true);
      return;
    }
    setLimitError(false);
    setStatus('placing');
    setTimeout(() => {
      const res = onExecuteOrder({ side, symbol, type, qty, limitPrice: type === 'limit' ? limit : price, price });
      if (res === 'filled') { setStatus('filled'); setQty(''); setLimit(''); setTimeout(() => setStatus(null), 3000); }
      else if (res === 'placed') { setStatus('placed'); setQty(''); setLimit(''); setTimeout(() => setStatus(null), 3000); }
      else { setStatus(null); }
    }, 600);
  };

  return (
    <div style={{ padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: 10, height: '100%', boxSizing: 'border-box', overflowY: 'auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.12em', color: T.textMid }}>ORDER ENTRY</span>
        <span style={{ fontSize: 9, color: T.textDim, fontFamily: "'IBM Plex Mono', monospace" }}>CASH: ₹{fmt(cash)}</span>
      </div>
      <div style={{ display: 'flex', background: T.bg, borderRadius: 6, padding: 3, border: `1px solid ${T.border}` }}>
        {['buy', 'sell'].map(s => (
          <button key={s} onClick={() => setSide(s)} style={{ flex: 1, padding: '7px 0', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', fontFamily: "'Inter', sans-serif",
            background: side === s ? (s === 'buy' ? T.green : T.red) : 'transparent', color: side === s ? '#000' : T.textMid }}>{s.toUpperCase()}</button>
        ))}
      </div>
      <div style={{ display: 'flex', gap: 6 }}>
        {['market', 'limit'].map(t => (
          <button key={t} onClick={() => setType(t)} style={{ flex: 1, padding: '6px 0', border: `1px solid ${type === t ? T.accent : T.border}`, borderRadius: 4, cursor: 'pointer', fontSize: 10,
            background: type === t ? 'rgba(56,189,248,0.12)' : 'transparent', color: type === t ? T.accent : T.textDim, fontFamily: "'Inter', sans-serif" }}>{t.toUpperCase()}</button>
        ))}
      </div>
      <Label text="QUANTITY"><Input value={qty} onChange={e => setQty(e.target.value)} placeholder="0.00" suffix="SHARES" /></Label>
      {type === 'limit' && (
        <Label text="LIMIT PRICE">
          <Input value={limit} onChange={e => { setLimit(e.target.value); setLimitError(false); }} placeholder={fmt(price)} prefix="₹" error={limitError} />
        </Label>
      )}
      <div style={{ padding: '8px 10px', background: T.bg, borderRadius: 6, border: `1px solid ${T.border}`, display: 'flex', justifyContent: 'space-between', fontSize: 10, fontFamily: "'IBM Plex Mono', monospace" }}>
        <span style={{ color: T.textDim }}>EST. TOTAL</span><span style={{ color: total === '—' ? T.textDim : T.text }}>₹{total === '—' ? '—' : fmt(total)}</span>
      </div>
      {status === 'filled' && <div style={{ padding: '8px 10px', background: T.greenDim, border: `1px solid ${T.green}`, borderRadius: 6, fontSize: 10, color: T.green, fontFamily: "'IBM Plex Mono', monospace", textAlign: 'center' }}>✓ ORDER FILLED (PAPER)</div>}
      {status === 'placed' && <div style={{ padding: '8px 10px', background: 'rgba(56,189,248,0.12)', border: `1px solid ${T.blue}`, borderRadius: 6, fontSize: 10, color: T.blue, fontFamily: "'IBM Plex Mono', monospace", textAlign: 'center' }}>✓ LIMIT ORDER PLACED (PAPER)</div>}
      {marketBlocked && (
        <div style={{ padding: '6px 10px', background: 'rgba(245,200,66,0.12)', border: '1px solid rgba(245,200,66,0.3)', borderRadius: 6, fontSize: 10, color: '#f5c842', fontFamily: "'IBM Plex Mono', monospace", textAlign: 'center' }}>
          MARKET ORDERS LOCKED — waiting for the first feed tick for this symbol (seeded prices are not orderable)
        </div>
      )}
      <button onClick={submit} disabled={!qty || status === 'placing' || marketBlocked} style={{ padding: '11px', border: 'none', borderRadius: 6, cursor: (qty && !marketBlocked) ? 'pointer' : 'not-allowed',
        background: side === 'buy' ? T.green : T.red, color: '#000', fontWeight: 700, fontSize: 11, letterSpacing: '0.1em', fontFamily: "'Inter', sans-serif", opacity: (qty && !marketBlocked) ? 1 : 0.4 }}>{status === 'placing' ? 'PLACING...' : `${side.toUpperCase()} ${symbol.replace('.NS', '')}`}</button>

      {openOrders?.length > 0 && (
        <div style={{ marginTop: 10, borderTop: `1px solid ${T.border}`, paddingTop: 10 }}>
          <div style={{ fontSize: 9, fontWeight: 700, letterSpacing: '0.12em', color: T.textMid, marginBottom: 6 }}>OPEN LIMIT ORDERS ({openOrders.length})</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
            {openOrders.map(o => (
              <div key={o.id} style={{ background: T.bg, border: `1px solid ${T.border}`, borderRadius: 6, padding: '7px 9px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
                    <span style={{ fontSize: 9, fontWeight: 700, color: o.side === 'buy' ? T.green : T.red, fontFamily: "'IBM Plex Mono', monospace" }}>{o.side.toUpperCase()}</span>
                    <span style={{ fontSize: 9, fontWeight: 700, color: T.text, fontFamily: "'IBM Plex Mono', monospace" }}>{o.symbol.replace('.NS', '')}</span>
                  </div>
                  <div style={{ fontSize: 8, color: T.textDim, marginTop: 1, fontFamily: "'IBM Plex Mono', monospace" }}>{o.qty} shares @ ₹{fmt(o.limitPrice)}</div>
                </div>
                <button onClick={() => onCancelOrder(o.id)} style={{ padding: '2px 6px', background: T.redDim, border: `1px solid rgba(255,61,90,0.3)`, borderRadius: 4, color: T.red, fontSize: 8, fontWeight: 700, cursor: 'pointer', fontFamily: "'Inter', sans-serif" }}>CANCEL</button>
              </div>
            ))}
          </div>
        </div>
      )}

      <div style={{ marginTop: 10, borderTop: `1px solid ${T.border}`, paddingTop: 10 }}>
        <div style={{ fontSize: 9, fontWeight: 700, letterSpacing: '0.12em', color: T.textMid, marginBottom: 8 }}>⏰ PRICE ALERTS</div>
        <div style={{ display: 'flex', gap: 6, alignItems: 'center', marginBottom: 8 }}>
          <select value={alertCondition} onChange={e => setAlertCondition(e.target.value)} style={{ flex: 1.2, background: T.bg, border: `1px solid ${T.border}`, borderRadius: 4, color: T.text, fontSize: 10, padding: '4px', height: 28, outline: 'none', fontFamily: "'Inter', sans-serif" }}>
            <option value="above">Crosses Above (≥)</option>
            <option value="below">Drops Below (≤)</option>
          </select>
          <div style={{ flex: 1.5, position: 'relative' }}>
            <span style={{ position: 'absolute', left: 6, top: '50%', transform: 'translateY(-50%)', color: T.textDim, fontSize: 9 }}>₹</span>
            <input type="number" value={alertPrice} onChange={e => setAlertPrice(e.target.value)} placeholder={price ? price.toFixed(0) : "0"}
              style={{ width: '100%', background: T.bg, border: `1px solid ${T.border}`, borderRadius: 4, color: T.text, fontSize: 10, padding: '4px 4px 4px 14px', height: 28, outline: 'none', fontFamily: "'IBM Plex Mono', monospace" }} />
          </div>
          <button onClick={() => { if (!alertPrice || isNaN(parseFloat(alertPrice)) || parseFloat(alertPrice) <= 0) { alert('Please enter a valid target price!'); return; } onAddAlert(symbol, alertCondition, parseFloat(alertPrice)); setAlertPrice(''); }}
            style={{ padding: '0 10px', height: 28, background: T.accent, border: 'none', borderRadius: 4, color: '#fff', fontSize: 9, fontWeight: 700, cursor: 'pointer', fontFamily: "'Inter', sans-serif" }}>SET</button>
        </div>
        {priceAlerts.filter(a => a.symbol === symbol).length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginTop: 6 }}>
            {priceAlerts.filter(a => a.symbol === symbol).map(a => (
              <div key={a.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: T.bg, border: `1px solid ${T.border}`, padding: '4px 8px', borderRadius: 4, fontSize: 9, fontFamily: "'IBM Plex Mono', monospace" }}>
                <span style={{ color: a.condition === 'above' ? T.green : T.red }}>{a.condition === 'above' ? '≥' : '≤'} ₹{fmt(a.targetPrice, 1)}</span>
                <button onClick={() => onDeleteAlert(a.id)} style={{ background: 'none', border: 'none', color: T.red, cursor: 'pointer', fontSize: 8, fontWeight: 700, fontFamily: "'Inter', sans-serif" }}>REMOVE</button>
              </div>
            ))}
          </div>
        )}
      </div>
      <div style={{ fontSize: 9, color: T.textDim, textAlign: 'center', lineHeight: 1.4, marginTop: 4 }}>PAPER TRADING ONLY — NO REAL ORDERS EXECUTED</div>
    </div>
  );
}