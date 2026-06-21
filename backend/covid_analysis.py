import sys
sys.path.insert(0, '.')
from quant.market_regime import MarketRegimeClassifier
from collections import Counter

classifier = MarketRegimeClassifier()
classifier.load_data()

h = classifier.classify_history(start_date="2020-02-01", end_date="2020-04-15")

print("\nFeb - Apr 2020 Regime Timeline:")
print(f"{'Date':12s} {'Close':>8s} {'Regime':12s} {'ADX':>6s} {'ATR_Pct':>8s}")
print("-" * 55)

for _, r in h.iterrows():
    if r['ADX'] is not None:
        print(f"{str(r['Date'])[:10]:12s} {r['Close']:8.0f} {r['Regime']:12s} {r['ADX']:6.1f} {r['ATR_Percentile']:7.0f}%")

rc = Counter(h['Regime'])
print(f"\nRegime Distribution:")
for k, v in rc.most_common():
    print(f"  {k}: {v} days")
