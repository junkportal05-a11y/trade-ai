import { API_BASE_URL, apiFetch } from './api';
import React, { useState, useEffect } from 'react';

const BASE = API_BASE_URL;

const T = {
  bg:       '#080a0f',
  surface:  '#0d1018',
  panel:    '#111520',
  border:   '#1a1f2e',
  borderHi: '#252c40',
  text:     '#d0d8ed',
  textMid:  '#6e7a96',
  textDim:  '#363d55',
  green:    '#00e5a8',
  greenDim: 'rgba(0,229,168,0.1)',
  red:      '#ff3d5a',
  redDim:   'rgba(255,61,90,0.1)',
  blue:     '#4da6ff',
  blueDim:  'rgba(77,166,255,0.1)',
  gold:     '#f5c842',
  goldDim:  'rgba(245,200,66,0.1)',
  accent:   '#7b6cff',
  accentDim:'rgba(123,108,255,0.12)',
};

const mono = { fontFamily: "'IBM Plex Mono', monospace" };
const fmt = (n, d = 2) => n == null ? '—' : Number(n).toLocaleString('en-IN', { minimumFractionDigits: d, maximumFractionDigits: d });
const clr = (v) => v > 0 ? T.green : v < 0 ? T.red : T.textMid;

export default function JournalPanel() {
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [showAddModal, setShowAddModal] = useState(false);
  const [newEntry, setNewEntry] = useState({
    symbol: '',
    direction: 'LONG',
    entry_price: '',
    exit_price: '',
    qty: '',
    reason: '',
    emotion: '',
    pnl: '',
    status: 'CLOSED'
  });

  const fetchJournal = async () => {
    setLoading(true);
    try {
      const res = await apiFetch('/api/journal');
      if (!res.ok) throw new Error("Failed to fetch journal entries");
      const data = await res.json();
      setEntries(Array.isArray(data) ? data : (data.entries || []));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJournal();
  }, []);

  const handleAddSubmit = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        ...newEntry,
        entry_price: parseFloat(newEntry.entry_price) || 0,
        exit_price: parseFloat(newEntry.exit_price) || 0,
        qty: parseInt(newEntry.qty) || 0,
        pnl: parseFloat(newEntry.pnl) || 0,
        entry_date: new Date().toISOString()
      };

      const res = await apiFetch('/api/journal', {
        method: 'POST',
        body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error("Failed to save entry");
      setShowAddModal(false);
      setNewEntry({ symbol: '', direction: 'LONG', entry_price: '', exit_price: '', qty: '', reason: '', emotion: '', pnl: '', status: 'CLOSED' });
      fetchJournal();
    } catch (err) {
      alert("Error adding entry: " + err.message);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Delete this journal entry?")) return;
    try {
      const res = await apiFetch(`/api/journal/${id}`, {
        method: 'DELETE'
      });
      if (!res.ok) throw new Error("Failed to delete");
      fetchJournal();
    } catch (err) {
      alert(err.message);
    }
  };

  const totalTrades = entries.length;
  const winningTrades = entries.filter(e => e.pnl > 0).length;
  const winRate = totalTrades > 0 ? ((winningTrades / totalTrades) * 100).toFixed(1) : 0;
  const totalPnl = entries.reduce((sum, e) => sum + (e.pnl || 0), 0);
  const bestTrade = entries.length > 0 ? Math.max(...entries.map(e => e.pnl || 0)) : 0;
  const worstTrade = entries.length > 0 ? Math.min(...entries.map(e => e.pnl || 0)) : 0;

  return (
    <div style={{ padding: 24, flex: 1, display: 'flex', flexDirection: 'column', gap: 24, overflowY: 'auto', background: T.bg }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ margin: 0, fontSize: 18, color: T.text, ...mono }}>TRADE JOURNAL</h2>
          <div style={{ fontSize: 12, color: T.textMid, marginTop: 4 }}>Log and review historical trades to improve your edge.</div>
        </div>
        <button
          onClick={() => setShowAddModal(true)}
          style={{ background: T.accent, color: '#fff', border: 'none', padding: '8px 16px', borderRadius: 4, cursor: 'pointer', ...mono, fontSize: 12, fontWeight: 'bold' }}
        >
          + NEW ENTRY
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, ...mono }}>
        {[
          { label: 'TOTAL PNL', value: `₹${fmt(totalPnl)}`, color: totalPnl >= 0 ? T.green : T.red },
          { label: 'WIN RATE', value: `${winRate}%`, color: T.text },
          { label: 'TOTAL TRADES', value: totalTrades, color: T.text },
          { label: 'BEST / WORST', value: `₹${fmt(bestTrade)} / ₹${fmt(worstTrade)}`, color: T.textMid }
        ].map((stat, i) => (
          <div key={i} style={{ background: T.surface, border: `1px solid ${T.borderHi}`, borderRadius: 8, padding: '16px', display: 'flex', flexDirection: 'column', gap: 8 }}>
            <div style={{ fontSize: 11, color: T.textMid }}>{stat.label}</div>
            <div style={{ fontSize: 20, fontWeight: 'bold', color: stat.color }}>{stat.value}</div>
          </div>
        ))}
      </div>

      {loading ? (
        <div style={{ color: T.textMid, ...mono, fontSize: 12 }}>LOADING JOURNAL...</div>
      ) : error ? (
        <div style={{ color: T.red, ...mono, fontSize: 12 }}>ERROR: {error}</div>
      ) : entries.length === 0 ? (
        <div style={{ color: T.textMid, ...mono, fontSize: 13, textAlign: 'center', padding: 60, border: `1px dashed ${T.borderHi}`, borderRadius: 12, background: 'rgba(26,31,46,0.2)' }}>
          <div style={{ fontSize: 32, marginBottom: 12 }}>📓</div>
          <div style={{ fontWeight: 'bold', color: T.text, marginBottom: 8 }}>NO TRADE LOGS YET</div>
          <div>Start journaling your trades to analyze your edge over time.</div>
          <button
            onClick={() => setShowAddModal(true)}
            style={{ marginTop: 24, background: T.accent, color: '#fff', border: 'none', padding: '8px 16px', borderRadius: 4, cursor: 'pointer', ...mono, fontSize: 12, fontWeight: 'bold' }}
          >
            + ADD FIRST TRADE
          </button>
        </div>
      ) : (
        <div style={{ background: T.surface, borderRadius: 8, border: `1px solid ${T.borderHi}`, overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', ...mono, fontSize: 11 }}>
            <thead>
              <tr style={{ background: 'rgba(26,31,46,0.5)', color: T.textDim, borderBottom: `1px solid ${T.borderHi}` }}>
                <th style={{ padding: '14px 16px' }}>DATE</th>
                <th style={{ padding: '14px 16px' }}>SYMBOL</th>
                <th style={{ padding: '14px 16px' }}>TYPE</th>
                <th style={{ padding: '14px 16px' }}>ENTRY</th>
                <th style={{ padding: '14px 16px' }}>EXIT</th>
                <th style={{ padding: '14px 16px' }}>PNL</th>
                <th style={{ padding: '14px 16px' }}>EMOTION</th>
                <th style={{ padding: '14px 16px' }}>REASON</th>
                <th style={{ padding: '14px 16px', textAlign: 'right' }}>ACTIONS</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((e, idx) => (
                <tr key={e.id} style={{ borderBottom: idx === entries.length - 1 ? 'none' : `1px solid ${T.border}`, transition: 'background 0.2s' }} onMouseEnter={ev => ev.currentTarget.style.background = 'rgba(255,255,255,0.02)'} onMouseLeave={ev => ev.currentTarget.style.background = 'transparent'}>
                  <td style={{ padding: '14px 16px', color: T.textMid }}>{new Date(e.entry_date).toLocaleDateString('en-IN', { month: 'short', day: 'numeric', year: 'numeric' })}</td>
                  <td style={{ padding: '14px 16px', color: T.text, fontWeight: 'bold' }}>{e.symbol}</td>
                  <td style={{ padding: '14px 16px' }}>
                    <span style={{ padding: '4px 8px', borderRadius: 4, background: e.direction === 'LONG' ? T.greenDim : T.redDim, color: e.direction === 'LONG' ? T.green : T.red, fontSize: 10, fontWeight: 'bold' }}>
                      {e.direction}
                    </span>
                  </td>
                  <td style={{ padding: '14px 16px', color: T.textMid }}>₹{fmt(e.entry_price)}</td>
                  <td style={{ padding: '14px 16px', color: T.textMid }}>₹{fmt(e.exit_price)}</td>
                  <td style={{ padding: '14px 16px' }}>
                    <span style={{ padding: '4px 8px', borderRadius: 4, background: e.pnl > 0 ? T.greenDim : e.pnl < 0 ? T.redDim : T.borderHi, color: e.pnl > 0 ? T.green : e.pnl < 0 ? T.red : T.textMid, fontSize: 10, fontWeight: 'bold' }}>
                      {e.pnl > 0 ? '+' : ''}₹{fmt(e.pnl)}
                    </span>
                  </td>
                  <td style={{ padding: '14px 16px', color: T.textMid }}>{e.emotion || '—'}</td>
                  <td style={{ padding: '14px 16px', color: T.textMid }}>{e.reason || '—'}</td>
                  <td style={{ padding: '14px 16px', textAlign: 'right' }}>
                    <button onClick={() => handleDelete(e.id)} style={{ background: 'none', border: 'none', color: T.textDim, cursor: 'pointer', ...mono, fontSize: 14, transition: 'color 0.2s' }} onMouseEnter={ev => ev.target.style.color = T.red} onMouseLeave={ev => ev.target.style.color = T.textDim}>
                      &times;
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showAddModal && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.85)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 999 }}>
          <form onSubmit={handleAddSubmit} style={{ background: T.surface, padding: 32, borderRadius: 12, border: `1px solid ${T.borderHi}`, width: 440, display: 'flex', flexDirection: 'column', gap: 16, boxShadow: '0 24px 48px rgba(0,0,0,0.5)' }}>
            <h3 style={{ margin: 0, color: T.text, ...mono, fontSize: 16 }}>ADD TRADE LOG</h3>
            <input placeholder="Symbol (e.g. HAL.NS)" value={newEntry.symbol} onChange={e => setNewEntry({...newEntry, symbol: e.target.value.toUpperCase()})} style={{ padding: 12, background: T.bg, border: `1px solid ${T.borderHi}`, borderRadius: 6, color: T.text, ...mono }} required />
            
            <select value={newEntry.direction} onChange={e => setNewEntry({...newEntry, direction: e.target.value})} style={{ padding: 12, background: T.bg, border: `1px solid ${T.borderHi}`, borderRadius: 6, color: T.text, ...mono }}>
              <option value="LONG">LONG</option>
              <option value="SHORT">SHORT</option>
            </select>
            
            <div style={{ display: 'flex', gap: 12 }}>
              <input type="number" step="0.05" placeholder="Entry Price" value={newEntry.entry_price} onChange={e => setNewEntry({...newEntry, entry_price: e.target.value})} style={{ flex: 1, padding: 12, background: T.bg, border: `1px solid ${T.borderHi}`, borderRadius: 6, color: T.text, ...mono }} required />
              <input type="number" step="0.05" placeholder="Exit Price" value={newEntry.exit_price} onChange={e => setNewEntry({...newEntry, exit_price: e.target.value})} style={{ flex: 1, padding: 12, background: T.bg, border: `1px solid ${T.borderHi}`, borderRadius: 6, color: T.text, ...mono }} required />
            </div>
            
            <div style={{ display: 'flex', gap: 12 }}>
              <input type="number" placeholder="Quantity" value={newEntry.qty} onChange={e => setNewEntry({...newEntry, qty: e.target.value})} style={{ flex: 1, padding: 12, background: T.bg, border: `1px solid ${T.borderHi}`, borderRadius: 6, color: T.text, ...mono }} required />
              <input type="number" step="0.05" placeholder="Total PnL (₹)" value={newEntry.pnl} onChange={e => setNewEntry({...newEntry, pnl: e.target.value})} style={{ flex: 1, padding: 12, background: T.bg, border: `1px solid ${T.borderHi}`, borderRadius: 6, color: T.text, ...mono }} required />
            </div>

            <input placeholder="Emotion (e.g. Confident, FOMO, Panic)" value={newEntry.emotion} onChange={e => setNewEntry({...newEntry, emotion: e.target.value})} style={{ padding: 12, background: T.bg, border: `1px solid ${T.borderHi}`, borderRadius: 6, color: T.text, ...mono }} />
            <input placeholder="Reason (e.g. Breakout retest)" value={newEntry.reason} onChange={e => setNewEntry({...newEntry, reason: e.target.value})} style={{ padding: 12, background: T.bg, border: `1px solid ${T.borderHi}`, borderRadius: 6, color: T.text, ...mono }} />
            
            <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end', marginTop: 12 }}>
              <button type="button" onClick={() => setShowAddModal(false)} style={{ background: 'none', border: 'none', color: T.textMid, cursor: 'pointer', ...mono, fontWeight: 'bold' }}>CANCEL</button>
              <button type="submit" style={{ background: T.accent, color: '#fff', border: 'none', padding: '10px 20px', borderRadius: 6, cursor: 'pointer', ...mono, fontWeight: 'bold' }}>SAVE LOG</button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
