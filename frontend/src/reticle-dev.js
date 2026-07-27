import { registerCapabilities } from '@reticlehq/react';

if (import.meta.env.DEV) {
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
