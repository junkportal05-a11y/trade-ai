import { reticle, registerCapabilities } from '@reticlehq/react';

if (import.meta.env.DEV) {
  try {
    reticle.connect();
  } catch (err) {
    console.warn('[Reticle] Connection fallback notice:', err);
  }

  registerCapabilities({
    testids: [
      'run-backtest-btn',
      'symbol-search-input',
      'bot-start-btn',
      'bot-stop-btn',
      'login-btn',
      'scan-market-btn'
    ],
    signals: [
      'bot:start',
      'bot:stop',
      'backtest:complete',
      'scan:complete'
    ],
    stores: []
  });
}
