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
  green: '#00f5a0',
  greenDim: 'rgba(0, 245, 160, 0.12)',
  greenGlow: 'rgba(0, 245, 160, 0.3)',
  red: '#ff3366',
  redDim: 'rgba(255, 51, 102, 0.12)',
  redGlow: 'rgba(255, 51, 102, 0.3)',
  blue: '#38bdf8',
  blueDim: 'rgba(56, 189, 248, 0.12)',
  blueGlow: 'rgba(56, 189, 248, 0.3)',
  gold: '#f5c842',
  goldDim: 'rgba(245, 200, 66, 0.12)',
  goldGlow: 'rgba(245, 200, 66, 0.3)',
  yellow: '#f5c842',
  accent: '#6366f1',
  accentAlt: '#a855f7',
  accentDim: 'rgba(99, 102, 241, 0.15)',
  accentGlow: 'rgba(99, 102, 241, 0.35)',
};

export const SEED_PRICES = {
  'YESBANK.NS': 25, 'TATASTEEL.NS': 170, 'BANKBARODA.NS': 280,
  'TATAPOWER.NS': 445, 'SBIN.NS': 830, 'HAL.NS': 4400, 'BEL.NS': 280, 'RVNL.NS': 350,
};

export const DEFAULT_WATCHLIST = [
  { symbol: 'YESBANK.NS', name: 'Yes Bank', sector: 'Banking' },
  { symbol: 'TATASTEEL.NS', name: 'Tata Steel', sector: 'Metals' },
  { symbol: 'BANKBARODA.NS', name: 'Bank of Baroda', sector: 'Banking' },
  { symbol: 'TATAPOWER.NS', name: 'Tata Power', sector: 'Power' },
  { symbol: 'SBIN.NS', name: 'SBI', sector: 'Banking' },
];

export const INTERVALS = [
  { label: '1D', interval: '30m', range: '1d' },
  { label: '1W', interval: '30m', range: '5d' },
  { label: '1M', interval: '1d', range: '1mo' },
  { label: '3M', interval: '1d', range: '3mo' },
  { label: '1Y', interval: '1wk', range: '1y' },
  { label: 'ALL', interval: '1mo', range: 'max' },
];

export const PORTFOLIO_SEED = [
  { symbol: 'HAL.NS', shares: 5, avgCost: 4400 },
  { symbol: 'BEL.NS', shares: 50, avgCost: 280 },
  { symbol: 'RVNL.NS', shares: 40, avgCost: 350 },
];

export const fmt = (n, d = 2) => n == null ? '—' : Number(n).toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });
export const fmtK = (n) => n >= 1e9 ? `₹${(n/1e9).toFixed(2)}B` : n >= 1e6 ? `₹${(n/1e6).toFixed(1)}M` : `₹${fmt(n, 0)}`;
export const clr = (v) => v > 0 ? T.green : v < 0 ? T.red : T.textMid;
export const sign = (v) => v > 0 ? '+' : '';
export const escapeHTML = (str) => String(str).replace(/[&<>'"]/g, tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag));

export const PRIMARY_TABS = ['HOME', 'SIMULATOR', 'CHART', 'SIGNALS', 'PREDICTIONS', 'PERFORMANCE', 'JOURNAL', 'ACCOUNT'];
export const SECONDARY_TABS = [];
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
};

export const EMPTY_ARRAY = [];