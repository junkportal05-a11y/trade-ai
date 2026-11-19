import os
from app.core.config import settings

# Simulate the lifespan worker-enabling logic from main.py
enable_workers = os.getenv('ENABLE_BACKGROUND_WORKERS', 'false').lower() == 'true'
print(f'ENABLE_BACKGROUND_WORKERS env: {os.getenv("ENABLE_BACKGROUND_WORKERS", "false")}')
print(f'enable_workers = {enable_workers}')

if not enable_workers:
    print('Background workers DISABLED (ENABLE_BACKGROUND_WORKERS not true)')
elif settings.skip_background_workers:
    print('Background workers SKIPPED (SKIP_BACKGROUND_WORKERS=true)')
else:
    print('Background workers WILL BE LAUNCHED')
    print('  - trading_agent_loop')
    print('  - prediction_resolver_worker')  
    print('  - governance_loop')
    print(f'skip_background_workers={settings.skip_background_workers}')
    print(f'live_trading_armed={settings.live_trading_armed}')
    print(f'trading_mode={settings.trading_mode}')
print('\\n--- Verification Complete ---')