import asyncio
import db
import signals
from quant.correlation_matrix import CorrelationEngine
from trade_quality import TradeQualityEngine

async def run_manual_check():
    print("[test] Simulating Manual Check for Correlation Rejection")
    
    correlation_engine = CorrelationEngine()
    # It will automatically build the matrix from the real .parquet files
    
    
    # 1. Open 1 paper trade on HDFCBANK.NS
    open_positions = [{"id": 1, "symbol": "HDFCBANK.NS", "status": "PENDING"}]
    print(f"\n[test] Currently holding: {open_positions[0]['symbol']}")
    
    # 2. Attempt to open a second on ICICIBANK.NS
    sig1 = {"symbol": "ICICIBANK.NS", "signal": "BUY", "confidence": 90, "market_regime_snapshot": "TRENDING", "atr": 0, "vol_ratio": 2}
    print(f"[test] Agent evaluating new signal for: {sig1['symbol']}")
    open_symbols = [p["symbol"] for p in open_positions]
    if not correlation_engine.check_trade_allowed(sig1["symbol"], open_symbols):
        print(f"[trading_agent] Blocked trade for {sig1['symbol']} due to high correlation.")
    else:
        print(f"[trading_agent] Placed paper trade for {sig1['symbol']} (Correlation is < 0.75 in real data)")
        
    # 3. Open 1 paper trade on TCS.NS
    open_positions_2 = [{"id": 2, "symbol": "TCS.NS", "status": "PENDING"}]
    print(f"\n[test] Currently holding: {open_positions_2[0]['symbol']}")
    
    # 4. Attempt to open a second on INFY.NS
    sig2 = {"symbol": "INFY.NS", "signal": "BUY", "confidence": 90, "market_regime_snapshot": "TRENDING", "atr": 0, "vol_ratio": 2}
    print(f"[test] Agent evaluating new signal for: {sig2['symbol']}")
    open_symbols_2 = [p["symbol"] for p in open_positions_2]
    if not correlation_engine.check_trade_allowed(sig2["symbol"], open_symbols_2):
        print(f"[trading_agent] Blocked trade for {sig2['symbol']} due to high correlation.")
    else:
        print(f"[trading_agent] Placed paper trade for {sig2['symbol']}")
            
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.DEBUG)
    asyncio.run(run_manual_check())
