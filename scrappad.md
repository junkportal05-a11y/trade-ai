# ==============================================================================
# APEXTRADE AI — INSTITUTIONAL UI/UX WORKSTATION OVERHAUL SPECIFICATION
# (Autonomous Frontend Enhancement Directive for OpenCode)
# ==============================================================================

## 🎯 OBJECTIVE
Transform ApexTrade into an ultra-modern, high-frequency quant workstation (combining TradingView clarity, Linear aesthetics, and Google Finance real-time responsiveness). Replace all toy emojis with Lucide SVG icons, introduce glassmorphism and real-time tick animations, add a Command Palette (Ctrl+K), wire an instant "📸 Snapshot & AI Scan" button directly on the Candlestick chart to Gemini 2.0 Flash, and build a robust Quant Server Connection handshake on app startup.

---

## 🧭 OPERATING RULES FOR OPENCODE
1. **Never Break the Build**: Every component edit must pass `npm run build` in `frontend/` without errors or missing imports.
2. **Use Installed Packages**: `lucide-react` is already installed (`^1.25.0`) in `package.json`. Use it for all icons. Do not add heavy external CSS frameworks.
3. **Keep Real Data Flow Intact**: Preserve all existing state, props, WebSocket ticker feeds, and order placement logic in `App.jsx` and components.
4. **Backend Test Integrity**: Ensure backend tests continue to pass (`.venv\Scripts\python.exe -m pytest backend/tests`).

---

## 📋 DETAILED UI ENHANCEMENT PHASES

### PHASE 1: Design Tokens & Glassmorphic Foundation
- **Files**: `frontend/src/theme.js`, `frontend/src/index.css`
- **Actions**:
  1. In `theme.js`:
     - Upgrade color tokens to deep institutional dark palette:
       ```javascript
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
         accent: '#6366f1',
         accentAlt: '#a855f7',
         accentDim: 'rgba(99, 102, 241, 0.15)',
         accentGlow: 'rgba(99, 102, 241, 0.35)',
       };
       ```
     - Update `TAB_META` to use clean text labels and Lucide icon names instead of emoji characters:
       ```javascript
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
       ```
  2. In `index.css`:
     - Add glowing glass utility classes:
       ```css
       .glass-card {
         background: rgba(17, 22, 34, 0.7);
         backdrop-filter: blur(16px);
         -webkit-backdrop-filter: blur(16px);
         border: 1px solid rgba(255, 255, 255, 0.07);
         box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
       }
       .tick-up {
         animation: flashGreen 0.45s ease-out;
       }
       .tick-down {
         animation: flashRed 0.45s ease-out;
       }
       @keyframes flashGreen {
         0% { background-color: rgba(0, 245, 160, 0.25); color: #00f5a0; }
         100% { background-color: transparent; }
       }
       @keyframes flashRed {
         0% { background-color: rgba(255, 51, 102, 0.25); color: #ff3366; }
         100% { background-color: transparent; }
       }
       ```

---

### PHASE 2: Navigation & Header Overhaul
- **Files**: `frontend/src/components/Header.jsx`
- **Actions**:
  1. Import Lucide icons: `Home`, `Bot`, `TrendingUp`, `Radio`, `Sparkles`, `BarChart3`, `BookOpen`, `ShieldCheck`, `Activity`, `Wifi`, `WifiOff`, `Search`, `Zap`.
  2. Map `TAB_META` icons directly to Lucide SVG components (14px) with crisp 12px text.
  3. Replace cramped 9px buttons with a sleek segmented pill group:
     - Active tab has glowing border (`rgba(99, 102, 241, 0.35)`) and subtle gradient background.
     - Hover micro-interactions with smooth transition (`transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1)`).
  4. Header Market Beacon:
     - Add a live status pill: Pulsing emerald beacon if NSE is open, amber for pre-market, red for closed.
     - Add live latency badge (`<15ms`).
     - Add `Ctrl + K` search trigger pill in the header to open the command palette.

---

### PHASE 3: Global Command Palette (`Ctrl + K` / `Cmd + K`)
- **Files**: `frontend/src/components/CommandPalette.jsx` (New), `frontend/src/App.jsx`
- **Actions**:
  1. Create `frontend/src/components/CommandPalette.jsx`:
     - Global keyboard listener for `Ctrl+K` and `Cmd+K`, plus `Escape` to close.
     - Instant filterable search input for:
       - Watchlist symbols (NIFTY, BANKNIFTY, TATASTEEL, SBIN, etc.) -> switches active symbol and jumps to CHART.
       - Navigation views (Home, Bot, Terminal, Predictions, etc.).
       - Quick Actions: "Emergency Stop Bot", "Open Health Diagnostics", "Clear Order Logs".
     - Styled with glassmorphism backdrop blur (`rgba(0,0,0,0.7)`), keyboard navigation (`ArrowUp`, `ArrowDown`, `Enter`).
  2. Integrate `CommandPalette` in `App.jsx`.

---

### PHASE 4: Chart Station: Instant "📸 Snapshot & AI Scan"
- **Files**: `frontend/src/components/CandleChart.jsx`, `frontend/src/App.jsx`
- **Actions**:
  1. On the top toolbar of `CandleChart.jsx`:
     - Style timeframe buttons (`1D`, `1W`, `1M`, `1Y`, `ALL`) into sleek segmented pill controls.
     - Add a prominent "📸 AI Scan Chart" button styled with an emerald/violet gradient border and `Sparkles` / `Camera` icon.
  2. Implement Snapshot Flow:
     - Capture the HTML5 canvas snapshot from the Lightweight Charts container (`chartContainerRef.current.querySelector('canvas')`).
     - Convert canvas to PNG base64 data url.
     - Send to backend `POST /api/chat/chart` with payload `{"image_base64": dataUrl, "symbol": symbol}`.
     - Show an elegant loading pulse indicator while Gemini 2.0 Flash processes.
     - When response returns, trigger a sleek modal or side-drawer showing:
       - Trend badge (`BULLISH` / `BEARISH` / `SIDEWAYS`).
       - Detected Patterns (e.g. "Bull Flag", "Double Bottom").
       - Key Support & Resistance price pills.
       - Breakout signal direction with AI Confidence meter.

---

### PHASE 5: AI Copilot Drawer & Confidence Gauges
- **Files**: `frontend/src/components/ChatPanel.jsx`
- **Actions**:
  1. Upgrade `ChatPanel.jsx` message bubbles:
     - Render AI messages in sleek card bubbles with glowing border.
     - Display a visual **Confidence Meter** (e.g., `Confidence: 94%` with a colored gradient bar).
     - Add collapsible "Show Reasoning" toggle.
  2. Add **1-Click Prompt Chips** above the input box:
     - ⚡ "Scan Breakouts"
     - 🎯 "Support & Resistance"
     - 🛡️ "Verify VWAP Veto"
     - 📊 "Explain Market Regime"
  3. Clicking any chip immediately submits the prompt to Gemini.

---

### PHASE 6: Quant Server Startup Connection & Live Handshake
- **Files**: `frontend/src/IntroSplash.jsx`, `frontend/src/api.js`, `frontend/src/App.jsx`
- **Actions**:
  1. Replace static/hardcoded Hugging Face boot logs with a real **Quant Server Connection Handshake**:
     - Query `GET /api/health` on boot to verify:
       * Quant Engine Status & Latency (`data.total_latency_ms`)
       * Database Connection (`data.checks.database.status`)
       * Gemini 2.0 Flash AI Brain (`data.checks.ai_services.gemini.status`)
       * NSE Market Session State (`data.checks.market.status`)
  2. Render a sleek live boot status checklist on the splash screen:
     - `✦ [✓] Quant Server Engine: CONNECTED (${latency}ms)`
     - `✦ [✓] Storage Engine: ${database_type.toUpperCase()} ONLINE`
     - `✦ [✓] AI Brain: GEMINI 2.0 FLASH READY`
     - `✦ [✓] Market Feed: NSE IST CLOCK SYNCHRONIZED`
  3. Server URL Configurator & Fallback:
     - If the Quant Server is not reachable within 5 seconds, show a sleek glassmorphic connection card:
       - Current Server Target: `${API_BASE_URL || 'Local Quant Server (localhost:7860)'}`
       - Editable URL input field so users can point to Cloud Run, Hugging Face, or local backend.
       - "Retry Connection" button and "Enter Terminal (Offline Demo Mode)" button so the app never freezes.

---

## 🛠️ VERIFICATION & BUILD GATE
Before finishing, OpenCode must run and ensure:
```bash
# 1. Build frontend without any errors
cd frontend && npm run build

# 2. Verify all backend tests still pass
cd .. && .venv\Scripts\python.exe -m pytest backend/tests -q
```

---

## 🔬 UNIFIED LIVE UI VERIFICATION CHECKLIST (SINGLE SCRATCHPAD)

- [x] **Step 1: Quant Server Startup Screen (`IntroSplash.jsx`)**
  - [x] Target switcher buttons present (`[⚡ Local (7860)]`, `[☁️ HuggingFace]`, `[Custom...]`)
  - [x] Live diagnostics log box and latency counter
  - [x] `[Launch Terminal →]` instant offline bypass button present so user is never locked out
- [x] **Step 2: Personal Workstation Direct Access (`App.jsx`)**
  - [x] Login page completely removed/bypassed — single user personal terminal
  - [x] Bypasses straight into workstation on launch or handshake
- [x] **Step 3: Header & Navigation (`Header.jsx`)**
  - [x] Lucide SVG navigation icons (Bot, Terminal, Scanner, etc.)
  - [x] Live market status beacon (NSE open/closed status, UTC+5:30 clock)
  - [x] `SEARCH` / `Ctrl+K` command trigger in header
- [x] **Step 4: Global Command Palette (`CommandPalette.jsx`)**
  - [x] Trigger with `Ctrl+K`, `Cmd+K`, or header SEARCH button
  - [x] Filterable symbols, view navigation, and emergency actions
  - [x] `ArrowUp`/`ArrowDown` keyboard navigation and `Escape` to close
- [x] **Step 5: Chart Multimodal Scanner (`CandleChart.jsx`)**
  - [x] Candlestick chart toolbar with segmented timeframe pills
  - [x] `📸 AI SCAN CHART` button connected to Gemini 2.0 Flash (`/api/chat/chart`)
- [x] **Step 6: AI Copilot & Analysis (`ChatPanel.jsx`)**
  - [x] Quick prompt chips (Breakouts, Support/Resistance, Regime)
  - [x] Visual confidence gauge and structured cards
- [x] **Step 7: Quality Gates**
  - [x] `frontend/ npm run build` compiles with 0 errors
  - [x] `backend/ pytest backend/tests` passes 216/216 tests (100%)

---

## 🔌 PLUGGED-IN AGENT TOOLING & EXTENSIONS

### 1. Google ARTEMIS (`google/artemis`) — Mobile & Live UI Automation
- **Repo**: `c:\Users\aryan\OneDrive\Desktop\main app\artemis`
- **Active Connected Device**: `emulator-5554` (BlueStacks 5 Android Emulator — 127.0.0.1:5555)
- **Status**: **ONLINE & VERIFIED** (5/5 checks pass, live screenshot & element grounding active)
- **MCP Server Installed**: Registered in `~/.gemini/config/mcp_config.json`, `~/.claude.json`, `.opencode/opencode.json`, and `.mcp.json`.
- **Usage Rule**: **Trigger whenever any app update occurs** to verify UI changes, inspect traces, and audit end-to-end device/browser states using:
  - `mobile_run_task(task="...")`: Launch automated natural-language tasks on `emulator-5554`
  - `mobile_get_device_state(view_type="screenshot" | "hierarchy")`: Pull live screenshot & hierarchy
  - `mobile_inspect_trace(trace_id="...")`: Audit trace logs and execution overlays
  - `mobile_diagnose(attempt_fix=True)`: Diagnostic doctor for connected devices / ADB

### 2. Google Agents CLI (`google/agents-cli`) — Enterprise Agent Platform
- **Repo**: `c:\Users\aryan\OneDrive\Desktop\main app\agents-cli`
- **CLI Command**: `agents-cli` installed globally via `uv tool install google-agents-cli` (v1.11.0)
- **Skills Installed (7/7)**:
  - `google-agents-cli-workflow`: Agent development lifecycle & model routing
  - `google-agents-cli-adk-code`: ADK Python patterns, tools, state management
  - `google-agents-cli-scaffold`: Scaffolding agent projects (`agents-cli create`)
  - `google-agents-cli-eval`: Evaluation metrics, datasets, LLM-as-judge
  - `google-agents-cli-deploy`: Cloud Run and Google Cloud deployments
  - `google-agents-cli-publish`: Gemini registration
  - `google-agents-cli-observability`: Cloud Trace & monitoring
- **Usage Rule**: **Use every time** for AI agent development, scaffolding, evals, and deployment across Antigravity, OpenCode, and Claude Code.



