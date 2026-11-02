export const T = {
  bg: '#07090e',
  surface: '#0d111a',
  panel: '#111622',
  panelAlt: '#141a29',
  glass: 'rgba(17, 22, 34, 0.75)',
  border: '#1b2234',
  borderHi: '#2c3652',
  text: '#e2e8f0',
  textMid: '#8290ad',
  textDim: '#475470',
  textMuted: '#6b7280',
  green: '#00f5a0',
  greenDim: 'rgba(0, 245, 160, 0.12)',
  greenGlow: 'rgba(0, 245, 160, 0.3)',
  red: '#ff3366',
  redDim: 'rgba(255, 51, 102, 0.12)',
  redGlow: 'rgba(255, 51, 102, 0.3)',
  blue: '#38bdf8',
  orange: '#f59e0b',
  orangeDim: 'rgba(245, 158, 11, 0.1)',
  accent: '#6366f1',
  accentAlt: '#a855f7',
  accentDim: 'rgba(99, 102, 241, 0.15)',
  accentGlow: 'rgba(99, 102, 241, 0.35)',
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