import React, { useState, useEffect } from 'react';
import { getJournal, addJournalEntry, deleteJournalEntry } from '../api';
import { X, Plus, TrendingUp, TrendingDown, Minus, Calendar, Target, AlertTriangle, CheckCircle, MoreVertical } from './Icons';

const EMOTIONS = ['Calm', 'Confident', 'Anxious', 'Excited', 'Frustrated', 'Disciplined', 'FOMO', 'Patient'];
const STATUSES = ['OPEN', 'CLOSED'];
const DIRECTIONS = ['BUY', 'SELL', 'LONG', 'SHORT'];

export default function JournalPanel() {
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingEntry, setEditingEntry] = useState(null);
  const [formData, setFormData] = useState({
    symbol: '',
    direction: 'BUY',
    entry_price: '',
    exit_price: '',
    qty: '',
    entry_date: new Date().toISOString().split('T')[0],
    reason: '',
    emotion: 'Calm',
    status: 'OPEN',
    target_price: '',
    stop_loss: '',
  });
  const [stats, setStats] = useState({ totalTrades: 0, winRate: 0, totalPnl: 0 });
  const [filter, setFilter] = useState({ symbol: '', status: '', direction: '' });

  const fetchJournal = async () => {
    try {
      const res = await getJournal();
      const data = await res.json();
      if (res.ok && data.entries) {
        setEntries(data.entries);
        calculateStats(data.entries);
      }
    } catch (e) {
      console.error('Failed to fetch journal:', e);
    } finally {
      setLoading(false);
    }
  };

  const calculateStats = (entries) => {
    const resolved = entries.filter(e => e.status === 'CLOSED' && e.pnl !== null);
    const totalPnl = resolved.reduce((sum, e) => sum + (e.pnl || 0), 0);
    const wins = resolved.filter(e => (e.pnl || 0) > 0).length;
    const winRate = resolved.length > 0 ? ((wins / resolved.length) * 100).toFixed(1) : 0;
    setStats({ totalTrades: entries.length, winRate, totalPnl: totalPnl.toFixed(2) });
  };

  useEffect(() => {
    fetchJournal();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    const payload = {
      symbol: formData.symbol.toUpperCase(),
      direction: formData.direction,
      entry_price: parseFloat(formData.entry_price),
      exit_price: formData.exit_price ? parseFloat(formData.exit_price) : null,
      qty: parseInt(formData.qty, 10),
      entry_date: formData.entry_date,
      reason: formData.reason || null,
      emotion: formData.emotion,
      status: formData.status,
      target_price: formData.target_price ? parseFloat(formData.target_price) : null,
      stop_loss: formData.stop_loss ? parseFloat(formData.stop_loss) : null,
    };

    try {
      const res = await addJournalEntry(payload);
      if (res.ok) {
        setShowForm(false);
        setEditingEntry(null);
        resetForm();
        fetchJournal();
      }
    } catch (err) {
      console.error('Failed to save journal entry:', err);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this journal entry?')) return;
    try {
      const res = await deleteJournalEntry(id);
      if (res.ok) fetchJournal();
    } catch (err) {
      console.error('Failed to delete:', err);
    }
  };

  const startEdit = (entry) => {
    setEditingEntry(entry);
    setFormData({
      symbol: entry.symbol,
      direction: entry.direction,
      entry_price: entry.entry_price,
      exit_price: entry.exit_price || '',
      qty: entry.qty,
      entry_date: entry.entry_date ? entry.entry_date.split('T')[0] : new Date().toISOString().split('T')[0],
      reason: entry.reason || '',
      emotion: entry.emotion || 'Calm',
      status: entry.status,
      target_price: entry.target_price || '',
      stop_loss: entry.stop_loss || '',
    });
    setShowForm(true);
  };

  const resetForm = () => {
    setFormData({
      symbol: '',
      direction: 'BUY',
      entry_price: '',
      exit_price: '',
      qty: '',
      entry_date: new Date().toISOString().split('T')[0],
      reason: '',
      emotion: 'Calm',
      status: 'OPEN',
      target_price: '',
      stop_loss: '',
    });
    setEditingEntry(null);
  };

  const filteredEntries = entries.filter(e => {
    if (filter.symbol && !e.symbol.toUpperCase().includes(filter.symbol.toUpperCase())) return false;
    if (filter.status && e.status !== filter.status) return false;
    if (filter.direction && e.direction !== filter.direction) return false;
    return true;
  });

  const formatDate = (iso) => {
    if (!iso) return '-';
    try {
      return new Date(iso).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
    } catch {
      return iso.split('T')[0];
    }
  };

  const pnlClass = (pnl) => {
    if (pnl === null || pnl === undefined) return '';
    return pnl > 0 ? 'text-emerald-400' : pnl < 0 ? 'text-red-400' : '';
  };

  const directionBadge = (dir) => {
    const isLong = ['BUY', 'LONG'].includes(dir);
    return (
      <span className={`px-2 py-0.5 text-xs font-medium rounded ${isLong ? 'bg-emerald-900/30 text-emerald-400' : 'bg-red-900/30 text-red-400'} border ${isLong ? 'border-emerald-800' : 'border-red-800'}`}>
        {dir}
      </span>
    );
  };

  const statusBadge = (status) => {
    return (
      <span className={`px-2 py-0.5 text-xs font-medium rounded ${status === 'OPEN' ? 'bg-amber-900/30 text-amber-400 border-amber-800' : 'bg-slate-700 text-slate-300 border-slate-600'}`}>
        {status}
      </span>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-2 border-gold-500 border-t-transparent"></div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-slate-950/50 rounded-xl border border-slate-800 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-slate-800 bg-slate-900/50">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-emerald-900/30 rounded-lg">
            <svg className="w-5 h-5 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <div>
            <h2 className="text-lg font-semibold text-white">Trade Journal</h2>
            <p className="text-xs text-slate-500">Track trades, review performance, build discipline</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-4 text-sm">
            <span className="text-slate-400">Total:</span>
            <span className="text-white font-mono">{stats.totalTrades}</span>
            <span className="text-slate-400">Win Rate:</span>
            <span className="text-emerald-400 font-mono">{stats.winRate}%</span>
            <span className="text-slate-400">P&L:</span>
            <span className={`font-mono ${parseFloat(stats.totalPnl) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
              {parseFloat(stats.totalPnl) >= 0 ? '+' : ''}{stats.totalPnl}
            </span>
          </div>
          <button
            onClick={() => { resetForm(); setShowForm(true); }}
            className="px-4 py-2 bg-gold-500/10 hover:bg-gold-500/20 text-gold-400 border border-gold-500/30 rounded-lg text-sm font-medium transition-colors flex items-center gap-2"
          >
            <Plus className="w-4 h-4" /> Add Entry
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="px-4 py-3 border-b border-slate-800 bg-slate-900/30 flex flex-wrap gap-3">
        <input
          type="text"
          placeholder="Filter symbol..."
          value={filter.symbol}
          onChange={(e) => setFilter({...filter, symbol: e.target.value})}
          className="flex-1 min-w-[150px] px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 text-sm focus:outline-none focus:border-gold-500"
        />
        <select
          value={filter.status}
          onChange={(e) => setFilter({...filter, status: e.target.value})}
          className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:border-gold-500"
        >
          <option value="">All Status</option>
          <option value="OPEN">OPEN</option>
          <option value="CLOSED">CLOSED</option>
        </select>
        <select
          value={filter.direction}
          onChange={(e) => setFilter({...filter, direction: e.target.value})}
          className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:border-gold-500"
        >
          <option value="">All Direction</option>
          <option value="BUY">BUY</option>
          <option value="SELL">SELL</option>
          <option value="LONG">LONG</option>
          <option value="SHORT">SHORT</option>
        </select>
      </div>

      {/* Journal Form Modal */}
      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm" onClick={() => { setShowForm(false); resetForm(); }}>
          <div className="w-full max-w-2xl max-h-[90vh] overflow-y-auto bg-slate-900 border border-slate-700 rounded-xl p-6" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-xl font-semibold text-white">{editingEntry ? 'Edit Journal Entry' : 'New Journal Entry'}</h3>
              <button onClick={() => { setShowForm(false); resetForm(); }} className="p-2 hover:bg-slate-800 rounded-lg text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Symbol *</label>
                  <input
                    type="text"
                    value={formData.symbol}
                    onChange={(e) => setFormData({...formData, symbol: e.target.value.toUpperCase()})}
                    placeholder="RELIANCE.NS"
                    required
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 text-sm focus:outline-none focus:border-gold-500"
                  />
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Direction *</label>
                  <select
                    value={formData.direction}
                    onChange={(e) => setFormData({...formData, direction: e.target.value})}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:border-gold-500"
                  >
                    {DIRECTIONS.map(d => <option key={d} value={d}>{d}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Entry Price *</label>
                  <input
                    type="number"
                    step="0.01"
                    value={formData.entry_price}
                    onChange={(e) => setFormData({...formData, entry_price: e.target.value})}
                    placeholder="2500.00"
                    required
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 text-sm focus:outline-none focus:border-gold-500"
                  />
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Exit Price</label>
                  <input
                    type="number"
                    step="0.01"
                    value={formData.exit_price}
                    onChange={(e) => setFormData({...formData, exit_price: e.target.value})}
                    placeholder="2650.00"
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 text-sm focus:outline-none focus:border-gold-500"
                  />
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Quantity *</label>
                  <input
                    type="number"
                    min="1"
                    value={formData.qty}
                    onChange={(e) => setFormData({...formData, qty: e.target.value})}
                    placeholder="10"
                    required
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 text-sm focus:outline-none focus:border-gold-500"
                  />
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Entry Date *</label>
                  <input
                    type="date"
                    value={formData.entry_date}
                    onChange={(e) => setFormData({...formData, entry_date: e.target.value})}
                    required
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:border-gold-500"
                  />
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Status *</label>
                  <select
                    value={formData.status}
                    onChange={(e) => setFormData({...formData, status: e.target.value})}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:border-gold-500"
                  >
                    {STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Target Price</label>
                  <input
                    type="number"
                    step="0.01"
                    value={formData.target_price}
                    onChange={(e) => setFormData({...formData, target_price: e.target.value})}
                    placeholder="2700.00"
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 text-sm focus:outline-none focus:border-gold-500"
                  />
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Stop Loss</label>
                  <input
                    type="number"
                    step="0.01"
                    value={formData.stop_loss}
                    onChange={(e) => setFormData({...formData, stop_loss: e.target.value})}
                    placeholder="2400.00"
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 text-sm focus:outline-none focus:border-gold-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs text-slate-400 mb-1">Emotion</label>
                <select
                  value={formData.emotion}
                  onChange={(e) => setFormData({...formData, emotion: e.target.value})}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:border-gold-500"
                >
                  {EMOTIONS.map(e => <option key={e} value={e}>{e}</option>)}
                </select>
              </div>

              <div>
                <label className="block text-xs text-slate-400 mb-1">Reason / Notes</label>
                <textarea
                  value={formData.reason}
                  onChange={(e) => setFormData({...formData, reason: e.target.value})}
                  rows={3}
                  placeholder="What was your thesis? Market context? Lessons learned?"
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 text-sm focus:outline-none focus:border-gold-500 resize-none"
                />
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => { setShowForm(false); resetForm(); }}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-600 rounded-lg text-sm font-medium transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-gold-500 hover:bg-gold-400 text-slate-950 border border-gold-500 rounded-lg text-sm font-medium transition-colors flex items-center gap-2"
                >
                  <Plus className="w-4 h-4" />
                  {editingEntry ? 'Update Entry' : 'Add Entry'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Entries Table */}
      <div className="flex-1 overflow-auto">
        {filteredEntries.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-slate-500">
            <svg className="w-16 h-16 mb-4 opacity-30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <p className="text-lg">No journal entries yet</p>
            <p className="text-sm">Start tracking your trades to build discipline</p>
            <button
              onClick={() => { resetForm(); setShowForm(true); }}
              className="mt-4 px-4 py-2 bg-gold-500/10 hover:bg-gold-500/20 text-gold-400 border border-gold-500/30 rounded-lg text-sm font-medium transition-colors"
            >
              Add Your First Entry
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-slate-500 uppercase tracking-wider bg-slate-900/50 border-b border-slate-800">
                  <th className="px-4 py-3">Date</th>
                  <th className="px-4 py-3">Symbol</th>
                  <th className="px-4 py-3">Dir</th>
                  <th className="px-4 py-3">Entry</th>
                  <th className="px-4 py-3">Exit</th>
                  <th className="px-4 py-3">Qty</th>
                  <th className="px-4 py-3">P&L</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Emotion</th>
                  <th className="px-4 py-3">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {filteredEntries.map((entry) => (
                  <tr key={entry.id} className="hover:bg-slate-900/50 transition-colors">
                    <td className="px-4 py-3 text-slate-400 font-mono">{formatDate(entry.entry_date)}</td>
                    <td className="px-4 py-3 text-white font-medium font-mono">{entry.symbol}</td>
                    <td className="px-4 py-3">{directionBadge(entry.direction)}</td>
                    <td className="px-4 py-3 text-slate-300 font-mono">{entry.entry_price?.toLocaleString()}</td>
                    <td className="px-4 py-3 text-slate-300 font-mono">{entry.exit_price ? entry.exit_price.toLocaleString() : '<span class="text-slate-500">-</span>'}</td>
                    <td className="px-4 py-3 text-slate-300 font-mono">{entry.qty?.toLocaleString()}</td>
                    <td className="px-4 py-3 font-mono font-medium">
                      {entry.pnl !== null && entry.pnl !== undefined ? (
                        <span className={pnlClass(entry.pnl)}>
                          {entry.pnl > 0 ? '+' : ''}{entry.pnl.toFixed(2)}
                        </span>
                      ) : (
                        <span className="text-slate-500">-</span>
                      )}
                    </td>
                    <td className="px-4 py-3">{statusBadge(entry.status)}</td>
                    <td className="px-4 py-3 text-slate-400 text-xs capitalize">{entry.emotion?.toLowerCase()}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => startEdit(entry)}
                          className="p-1.5 hover:bg-slate-800 rounded-lg text-slate-500 hover:text-gold-400 transition-colors"
                          title="Edit"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" /></svg>
                        </button>
                        <button
                          onClick={() => handleDelete(entry.id)}
                          className="p-1.5 hover:bg-slate-800 rounded-lg text-slate-500 hover:text-red-400 transition-colors"
                          title="Delete"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}