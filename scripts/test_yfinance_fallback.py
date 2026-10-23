import sys
import types

# Create a mock module for angelone_feed
mock_angelone_feed = types.ModuleType('angelone_feed')
class MockFeed:
    def is_authorized(self):
        return False
    def get_historical_candles(self, symbol, period, interval):
        return None
mock_angelone_feed.get_angelone_feed = lambda: MockFeed()
sys.modules['angelone_feed'] = mock_angelone_feed

# Now import the function
from backend.signals import download_market_data_df

# Test the function
df = download_market_data_df('RELIANCE', period='5d', interval='5m')
print('Data fetched:', df is not None and not df.empty)
if df is not None and not df.empty:
    print('Shape:', df.shape)
    print('Columns:', df.columns.tolist())
    print('First row:')
    print(df.head(1))
