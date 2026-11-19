export const T = {
  // Near-black family (#080808)
  bg: '#080808',
  surface: '#0d0d0d',
  surfaceDim: '#1a1a1a',
  surfaceBright: '#222222',
  surfaceContainerLowest: '#050505',
  surfaceContainerLow: '#121212',
  surfaceContainer: '#181818',
  surfaceContainerHigh: '#1f1f1f',
  surfaceContainerHighest: '#262626',
  onSurface: '#cdcbc9',
  onSurfaceVariant: '#a8a6a4',
  inverseSurface: '#cdcbc9',
  inverseOnSurface: '#1a1a1a',
  outline: '#4a4948',
  outlineVariant: '#3a3938',
  primary: '#d41514',
  onPrimary: '#ffffff',
  primaryContainer: '#3a0d0d',
  onPrimaryContainer: '#ffdad6',
  inversePrimary: '#d41514',
  secondary: '#787776',
  onSecondary: '#1a1a1a',
  secondaryContainer: '#2a2a2a',
  onSecondaryContainer: '#d4d3d2',
  tertiary: '#4a90d9',
  onTertiary: '#001e3a',
  tertiaryContainer: '#1a3a5c',
  onTertiaryContainer: '#d6e8ff',
  error: '#f44336',
  onError: '#ffffff',
  errorContainer: '#4a0d0d',
  onErrorContainer: '#ffdad6',
  primaryFixed: '#ffbdbd',
  onPrimaryFixed: '#4a0000',
  secondaryFixed: '#c5c4c3',
  onSecondaryFixed: '#1a1a1a',
  tertiaryFixed: '#bdd8ff',
  onTertiaryFixed: '#001e3a',
  background: '#080808',
  onBackground: '#cdcbc9',
  surfaceVariant: '#262626',

  // --- Tri-chromatic DESIGN.md token system (single source of truth) ---
  // Text hierarchy: one neutral ramp for all copy
  text: '#cdcbc9',
  textMid: '#a8a6a4',
  textDim: '#6a6968',
  textMuted: '#4a4948',

  // One accent, used sparingly for primary CTA/indicators
  accent: '#d41514',
  accentAlt: '#e84040',
  // accentDim — subtle depth using surface dimension
  accentDim: '#2a0e0e',
  // accentGlow — subtle surface shadow for depth (not a branded color)
  accentGlow: '0 4px 12px rgba(212, 21, 20, 0.3)',

  // Action colors — distinct from accent
  green: '#00e676',
  greenDim: 'rgba(0, 230, 118, 0.12)',
  greenGlow: 'rgba(0, 230, 118, 0.25)',

  // Risk / error colors
  red: '#ff5252',
  redDim: 'rgba(255, 82, 82, 0.12)',
  redGlow: 'rgba(255, 82, 82, 0.25)',

  // Structure / status — gold uses accent as base for consistency
  gold: '#ffab00',
  goldDim: 'rgba(255, 171, 0, 0.12)',

  // Borders — fixed opacity for consistency
  border: '#3a3938',
  borderHi: '#d41514',
  // --- End tri-chromatic system ---
};

export const fmt = (n, d = 2) => n == null ? '\u2014' : Number(n).toLocaleString('en-IN', { minimumFractionDigits: d, maximumFractionDigits: d });
export const fmtINR = (n, d = 2) => n == null ? '\u2014' : `\u20b9${Number(n).toLocaleString('en-IN', { minimumFractionDigits: d, maximumFractionDigits: d })}`;
export const fmtPct = (n, d = 2) => n == null ? '\u2014' : `${n >= 0 ? '+' : ''}${Number(n).toLocaleString('en-IN', { minimumFractionDigits: d, maximumFractionDigits: d })}%`;
export const clr = (v) => v > 0 ? T.green : v < 0 ? T.red : T.textMid;
export const sign = (v) => v > 0 ? '+' : '';
export const escapeHTML = (str) =>
  String(str).replace(/[&<>'"]/g, c =>
    ({ "&": "&", "<": "<", ">": ">", "'": "'", '"': "" }[c] || c)
  );

export const fmtIST = (date = new Date()) => date.toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
export const fmtISTDate = (date = new Date()) => date.toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', year: 'numeric', month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
export const fmtISTShort = (date = new Date()) => date.toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', hour: '2-digit', minute: '2-digit', hour12: false });
export const PRIMARY_TABS = ['HOME', 'CHART', 'SIGNALS', 'PREDICTIONS', 'STRATEGIES'];
export const SECONDARY_TABS = [];

export const MOBILE_TABS = ['HOME', 'CHART', 'SIGNALS', 'PREDICTIONS', 'STRATEGIES'];

export const TAB_META = {
  HOME: { label: 'Home', icon: 'Home' },
  CHART: { label: 'Charts', icon: 'TrendingUp' },
  SIGNALS: { label: 'Scanner', icon: 'Radio' },
  PREDICTIONS: { label: 'Predictions', icon: 'Sparkles' },
  STRATEGIES: { label: 'Strategies', icon: 'Settings' },
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