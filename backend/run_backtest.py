import sys
sys.path.insert(0, '.')
from angelone_feed import AngelOneFeed
from backtest_engine import run_historical_backtest, BacktestConfig

symbol = sys.argv[1] if len(sys.argv) > 1 else 'RELIANCE'
period = sys.argv[2] if len(sys.argv) > 2 else '2y'

feed = AngelOneFeed()
feed.auto_login()

result = run_historical_backtest(symbol, BacktestConfig(period_range=period, entry_score=3, adx_min=25))
for k, v in result.items():
    if k not in ('trades', 'equity_curve'):
        print(f'{k}: {v}')
print('trade count:', len(result.get('trades', [])))
