import sys
with open('backend/historical_simulator.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
skip = False
for i, line in enumerate(lines):
    if "result = signals.analyse_symbol(" in line:
        skip = True
        
        block = """                                result = signals.analyse_symbol(
                                    symbol=symbol,
                                    name=symbol,
                                    sector="General",
                                    style="Intraday Momentum",
                                    risk="Medium",
                                    segment="NSE",
                                    capital=self.BASE_CAPITAL * (self.POSITION_SIZE_PERCENT / 100),
                                    atr_multiplier=atr_multiplier,
                                    rr_target=rr_target
                                )
                                
                                if result and abs(result.get('score', 0)) >= 4 and result.get('confidence', 0) >= 60:
                                    simulation_status.stats["total_signals"] += 1
                                    
                                    # Signal Details
                                    signal_type = 'BUY' if result.get('score', 0) > 0 else 'SELL'
                                    entry_price = result.get('current_price', df_day.iloc[i]['Close'])
                                    
                                    # Fallback to ATR-based stops if target/stop is 0
                                    target = result.get('target', 0)
                                    stop_loss = result.get('stop_loss', 0)
                                    atr = result.get('atr', 20.0)
                                    if target == 0 or stop_loss == 0:
                                        if signal_type == 'BUY':
                                            stop_loss = entry_price - (atr_multiplier * atr)
                                            target = entry_price + (rr_target * atr_multiplier * atr)
                                        else:
                                            stop_loss = entry_price + (atr_multiplier * atr)
                                            target = entry_price - (rr_target * atr_multiplier * atr)
                                            
                                    is_long = signal_type == 'BUY'
                                    
                                    # Hybrid Trading Model - Tier 1 vs Tier 2
                                    target_pct = abs((target - entry_price) / entry_price) * 100
                                    
                                    if target_pct > 5.0:
                                        # Tier 2: Swing Trade (Allow up to 10 days hold)
                                        df_forward = df.iloc[i+1 : i+1+(75*10)]
                                    else:
                                        # Tier 1: Intraday Trade (Close EOD)
                                        df_forward = df_day.iloc[i+1:]
                                        
                                    if df_forward.empty:
                                        continue
                                        
                                    outcome, exit_price, exit_time = self._resolve_trade(df_forward, entry_price, target, stop_loss, is_long)
                                    
                                    # PnL Calculation
                                    if is_long:
                                        pnl_pct = ((exit_price - entry_price) / entry_price) * 100
                                    else:
                                        pnl_pct = ((entry_price - exit_price) / entry_price) * 100
                                    
                                    if outcome == 'WIN':
                                        simulation_status.stats["wins"] += 1
                                    elif outcome == 'LOSS':
                                        simulation_status.stats["losses"] += 1
                                    else:
                                        if pnl_pct > 0.05:
                                            simulation_status.stats["wins"] += 1
                                        elif pnl_pct < -0.05:
                                            simulation_status.stats["losses"] += 1
                                        else:
                                            simulation_status.stats["timeouts"] += 1
                                            
                                    quantity = result.get('quantity', 0)
                                    if quantity > 0:
                                        capital_deployed = quantity * entry_price
                                    else:
                                        capital_deployed = self.BASE_CAPITAL * (self.POSITION_SIZE_PERCENT / 100)
                                        
                                    risk_amount = result.get('risk_amount', self.BASE_CAPITAL * (self.RISK_PERCENT / 100))
                                    pnl_inr = capital_deployed * (pnl_pct / 100)
                                    
                                    # Construct trade record
                                    trade_record = {
                                        'symbol': symbol,
                                        'prediction_date': current_time.isoformat(),
"""
        new_lines.append(block)
    
    if skip and "'prediction_type': signal_type," in line:
        skip = False
        new_lines.append(line)
        continue
        
    if not skip:
        new_lines.append(line)

with open('backend/historical_simulator.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
