export const T = {
  bg: '#080a0f', surface: '#0d1018', panel: '#111520', panelAlt: '#0f1219',
  border: '#1a1f2e', borderHi: '#252c40', text: '#d0d8ed', textMid: '#6e7a96',
  textDim: '#363d55', green: '#00e5a8', greenDim: 'rgba(0,229,168,0.1)',
  greenGlow: 'rgba(0,229,168,0.25)', red: '#ff3d5a', redDim: 'rgba(255,61,90,0.1)',
  redGlow: 'rgba(255,61,90,0.25)', blue: '#4da6ff', blueDim: 'rgba(77,166,255,0.1)',
  blueGlow: 'rgba(77,166,255,0.2)', gold: '#f5c842', goldDim: 'rgba(245,200,66,0.1)',
  goldGlow: 'rgba(245,200,66,0.25)', accent: '#7b6cff', accentAlt: '#9b5de5',
  accentDim: 'rgba(123,108,255,0.12)', accentGlow: 'rgba(123,108,255,0.3)',
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
export const escapeHTML = (str) => String(str).replace(/[&<>'"]/g, tag => ({ '&': '&', '<': '<', '>': '>', "'": ''', '"': '"' }[tag] || tag));

export const PRIMARY_TABS = ['HOME', 'SIMULATOR', 'CHART', 'PREDICTIONS', 'PERFORMANCE', 'JOURNAL', 'ACCOUNT'];
export const SECONDARY_TABS = ['SIGNALS'];
export const MOBILE_TABS = ['HOME', 'SIMULATOR', 'CHART', 'SIGNALS', 'PREDICTIONS', 'PERFORMANCE', 'JOURNAL', 'ACCOUNT'];

export const TAB_META = {
  HOME: { icon: '🏠', label: 'HOME' }, SIMULATOR: { icon: '🤖', label: 'BOT' }, CHART: { icon: '📈', label: 'CHART' },
  SIGNALS: { icon: '📡', label: 'SCAN' }, PREDICTIONS: { icon: '🔮', label: 'PREDICT' }, PERFORMANCE: { icon: '📊', label: 'PERF' },
  JOURNAL: { icon: '📓', label: 'JRNL' }, ACCOUNT: { icon: '🛡️', label: 'SEC' },
};

export const EMPTY_ARRAY = [];