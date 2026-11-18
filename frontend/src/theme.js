export const T = {
  bg: '#131313',
  surface: '#131313',
  surfaceDim: '#131313',
  surfaceBright: '#3a3939',
  surfaceContainerLowest: '#0e0e0e',
  surfaceContainerLow: '#1c1b1b',
  surfaceContainer: '#201f1f',
  surfaceContainerHigh: '#2a2a2a',
  surfaceContainerHighest: '#353534',
  onSurface: '#e5e2e1',
  onSurfaceVariant: '#e7bdb7',
  inverseSurface: '#e5e2e1',
  inverseOnSurface: '#313030',
  outline: '#ad8883',
  outlineVariant: '#5d3f3b',
  surfaceTint: '#ffb4a9',
  primary: '#ffb4a9',
  onPrimary: '#690002',
  primaryContainer: '#d41514',
  onPrimaryContainer: '#ffe7e4',
  inversePrimary: '#c00009',
  secondary: '#c8c6c5',
  onSecondary: '#303030',
  secondaryContainer: '#474746',
  onSecondaryContainer: '#b6b5b4',
  tertiary: '#a8c8ff',
  onTertiary: '#003062',
  tertiaryContainer: '#006acc',
  onTertiaryContainer: '#e5ecff',
  error: '#ffb4ab',
  onError: '#690005',
  errorContainer: '#93000a',
  onErrorContainer: '#ffdad6',
  primaryFixed: '#ffdad5',
  primaryFixedDim: '#ffb4a9',
  onPrimaryFixed: '#410001',
  onPrimaryFixedVariant: '#930005',
  secondaryFixed: '#e4e2e1',
  secondaryFixedDim: '#c8c6c5',
  onSecondaryFixed: '#1b1c1b',
  onSecondaryFixedVariant: '#474746',
  tertiaryFixed: '#d6e3ff',
  tertiaryFixedDim: '#a8c8ff',
  onTertiaryFixed: '#001b3d',
  onTertiaryFixedVariant: '#00468a',
  background: '#131313',
  onBackground: '#e5e2e1',
  surfaceVariant: '#353534',

  // --- Backward-compatible aliases (old property names ---
  // these map to the new tri-chromatic DESIGN.md token system) ---
  // Background/surface
  bg: '#131313',
  surface: '#131313',
  panel: '#131313',
  panelAlt: '#1c1b1b',

  // Text colors
  text: '#e5e2e1',
  textMid: '#e7bdb7',
  textDim: '#313030',
  textMuted: '#5d3f3b',

  // Accent / action / risk
  accent: '#ffb4a9',
  accentAlt: '#5d3f3b',
  accentDim: '#ffb4a9',
  accentGlow: 'rgba(212, 21, 20, 0.15)',

  // Action colors
  green: '#c8c6c5',
  greenDim: 'rgba(205, 203, 202, 0.15)',
  greenGlow: 'transparent',

  // Risk / error colors
  red: '#ffb4ab',
  redDim: 'rgba(255, 180, 171, 0.12)',
  redGlow: 'rgba(255, 180, 171, 0.25)',

  // Structure / status
  gold: '#ffb4a9',
  goldDim: '#ffdad5',

  // Borders
  border: '#ad8883',
  borderHi: 'rgba(212, 21, 20, 0.40)',
  // --- End backward-compatible aliases ---
};

export const fmt = (n, d = 2) => n == null ? '—' : Number(n).toLocaleString('en-IN', { minimumFractionDigits: d, maximumFractionDigits: d });
export const fmtINR = (n, d = 2) => n == null ? '—' : `₹${Number(n).toLocaleString('en-IN', { minimumFractionDigits: d, maximumFractionDigits: d })}`;
export const fmtPct = (n, d = 2) => n == null ? '—' : `${n >= 0 ? '+' : ''}${Number(n).toLocaleString('en-IN', { minimumFractionDigits: d, maximumFractionDigits: d })}%`;
export const clr = (v) => v > 0 ? T.secondary : v < 0 ? T.error : T.textMid;
export const sign = (v) => v > 0 ? '+' : '';
export const escapeHTML = (str) => String(str).replace(/[&<>'"]/g, c => ({ '&': '&', '<': '<', '>': '>', "'": '&apos;', '"': '"' }[c] || c));

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
  { interval: '1h', range: '1W' },
  { interval: '4h', range: '1W' },
  { interval: '1d', range: '1M' },
];

export const fmtTime = (date = new Date()) => date.toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });

export const mono = { fontFamily: "'IBM Plex Mono', monospace" };

export const EMPTY_ARRAY = [];