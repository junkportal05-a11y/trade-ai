export const T = {
  bg: '#050506',
  surface: '#0c0a09',
  panel: '#0e0c0a',
  panelAlt: '#141210',
  glass: 'rgba(12, 10, 9, 0.85)',
  border: 'rgba(245, 158, 11, 0.15)',
  borderHi: 'rgba(245, 158, 11, 0.35)',
  text: '#f8fafc',
  textMid: '#94a3b8',
  textDim: '#64748b',
  textMuted: '#475569',
  green: '#f59e0b',
  greenDim: 'rgba(245, 158, 11, 0.12)',
  greenGlow: 'rgba(245, 158, 11, 0.3)',
  red: '#ef4444',
  redDim: 'rgba(239, 68, 68, 0.12)',
  redGlow: 'rgba(239, 68, 68, 0.3)',
  blue: '#f59e0b',
  orange: '#f59e0b',
  orangeDim: 'rgba(245, 158, 11, 0.1)',
  accent: '#f59e0b',
  accentAlt: '#d97706',
  accentDim: 'rgba(245, 158, 11, 0.15)',
  accentGlow: 'rgba(245, 158, 11, 0.35)',
};

export const fmt = (n, d = 2) => n == null ? '—' : Number(n).toLocaleString('en-IN', { minimumFractionDigits: d, maximumFractionDigits: d });
export const fmtINR = (n, d = 2) => n == null ? '—' : `₹${Number(n).toLocaleString('en-IN', { minimumFractionDigits: d, maximumFractionDigits: d })}`;
export const fmtPct = (n, d = 2) => n == null ? '—' : `${n >= 0 ? '+' : ''}${Number(n).toLocaleString('en-IN', { minimumFractionDigits: d, maximumFractionDigits: d })}%`;
export const clr = (v) => v > 0 ? T.green : v < 0 ? T.red : T.textMid;
export const sign = (v) => v > 0 ? '+' : '';
export const escapeHTML = (str) => String(str).replace(/[&<>'"]/g, c => ({ '&': '&', '<': '<', '>': '>', "'": "'", '"': '"' }[c] || c));

export const fmtIST = (date = new Date()) => date.toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
export const fmtISTDate = (date = new Date()) => date.toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', year: 'numeric', month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
export const fmtISTShort = (date = new Date()) => date.toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', hour: '2-digit', minute: '2-digit', hour12: false });

export const PRIMARY_TABS = ['HOME', 'SIMULATOR', 'CHART', 'SIGNALS', 'PREDICTIONS', 'PERFORMANCE', 'JOURNAL', 'ACCOUNT'];
export const SECONDARY_TABS = ['STRATEGIES', 'SETTINGS', 'HELP'];
export const MOBILE_TABS = ['HOME', 'SIMULATOR', 'CHART', 'SIGNALS', 'PREDICTIONS', 'PERFORMANCE', 'JOURNAL', 'ACCOUNT'];

export const TAB_META = {
  HOME: { label: 'Home', icon: 'Home' },
  SIMULATOR: { label: 'Bot Engine', icon: 'Bot' },
  CHART: { label: 'Terminal', icon: 'TrendingUp' },
  SIGNALS: { label: 'Scanner', icon: 'Radio' },
  PREDICTIONS: { label: 'Predictions', icon: 'Sparkles' },
  PERFORMANCE: { label: 'Analytics', icon: 'BarChart3' },
  JOURNAL: { label: 'Journal', icon: 'BookOpen' },
  ACCOUNT: { label: 'Security', icon: 'ShieldCheck' },
  STRATEGIES: { label: 'Strategies', icon: 'Settings' },
  SETTINGS: { label: 'Settings', icon: 'Settings' },
  HELP: { label: 'Help', icon: 'HelpCircle' },
};

export const SEED_PRICES = {
  'RELIANCE.NS': 2445.35,
  'TCS.NS': 3128.80,
  'INFY.NS': 1456.70,
  'HDFCBANK.NS': 1485.60,
  'ICICIBANK.NS': 958.20,
  'SBIN.NS': 723.40,
  'BHARTIARTL.NS': 826.50,
  'ITC.NS': 412.15,
  'KOTAKBANK.NS': 1748.75,
  'LT.NS': 3892.60,
};

export const DEFAULT_WATCHLIST = [
  { symbol: 'RELIANCE.NS' },
  { symbol: 'TCS.NS' },
  { symbol: 'INFY.NS' },
  { symbol: 'HDFCBANK.NS' },
  { symbol: 'ICICIBANK.NS' },
  { symbol: 'SBIN.NS' },
  { symbol: 'BHARTIARTL.NS' },
  { symbol: 'ITC.NS' },
  { symbol: 'KOTAKBANK.NS' },
  { symbol: 'LT.NS' },
];

export const INTERVALS = [
  { interval: '15m', range: '1D' },
  { interval: '30m', range: '1D' },
  { interval: '1h', range: '1D' },
  { interval: '4h', range: '1W' },
  { interval: '1d', range: '1M' },
];

export const fmtTime = (date = new Date()) => date.toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });

export const mono = { fontFamily: "'IBM Plex Mono', monospace" };

export const EMPTY_ARRAY = [];