#!/usr/bin/env python
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from angelone_feed import AngelOneFeed
from backtest_engine import run_historical_backtest, BacktestConfig
def parse_arguments():
    """Parse command line arguments for backtest configuration."""
    parser = argparse.ArgumentParser(
        description="Run historical backtest with configurable parameters",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s RELIANCE --period 2y --entry-score 5 --risk-pct 0.02
  %(prog)s RELIANCE --json-output --adx-min 25
  %(prog)s RELIANCE 1y --target-atr 3.0 --stop-atr 1.5
        """
    )

    # Required positional argument
    parser.add_argument("symbol", help="Trading symbol (e.g., RELIANCE, TCS)")

    # Backtest configuration parameters (from BacktestConfig)
    parser.add_argument("--period", dest="period_range", default="2y",
                        help="Time period for historical data (e.g., 1mo, 3mo, 6mo, 1y, 2y, 5y, max)")

    parser.add_argument("--initial-capital", type=float, dest="initial_capital",
                        default=10000.0,
                        help="Initial capital for backtest simulation (default: 10000.0)")

    # Validation helper functions
    def validate_score(value):
        ivalue = int(value)
        if ivalue < 0 or ivalue > 10:
            raise argparse.ArgumentTypeError(f"{value} is not a valid score (0-10)")
        return ivalue

    def validate_risk_pct(value):
        ivalue = float(value)
        if ivalue <= 0 or ivalue > 1:
            raise argparse.ArgumentTypeError(f"{value} is not a valid risk percentage (0.01-1.0)")
        return ivalue

    def validate_period(value):
        valid_periods = ["1d", "1w", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "max"]
        if value not in valid_periods:
            raise argparse.ArgumentTypeError(f"{value} is not a valid period. Use one of: {', '.join(valid_periods)}")
        return value

    parser.add_argument("--entry-score", type=validate_score,
                        dest="entry_score", default=5,
                        help="Minimum score to trigger buy signal (0-10)")

    parser.add_argument("--stop-atr", type=float, dest="stop_atr",
                        default=1.5,
                        help="Stop loss distance in ATR units (default: 1.5)")

    parser.add_argument("--target-atr", type=float, dest="target_atr",
                        default=2.5,
                        help="Target profit distance in ATR units (default: 2.5)")

    parser.add_argument("--risk-pct", type=validate_risk_pct,
                        dest="risk_pct", default=0.02,
                        help="Risk percentage per trade (0.01-1.0)")

    parser.add_argument("--early-exit", type=int, dest="early_exit",
                        default=-4,
                        help="Early exit score threshold for bearish indicators (default: -4)")

    parser.add_argument("--adx-min", type=float, dest="adx_min",
                        default=0.0,
                        help="Minimum ADX value required for entry (default: 0.0)")

    # Convenience arguments
    parser.add_argument("-j", "--json-output", action="store_true",
                        help="Output results in JSON format for programmatic use")

    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Enable verbose logging")

    return parser.parse_args()
def main():
    args = parse_arguments()

    # Configure logging if verbose
    if args.verbose:
        import logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    feed = AngelOneFeed()
    if not feed.auto_login():
        print('WARNING: AngelOne login failed — will use yfinance fallback', file=sys.stderr)

    print(f'Running backtest: {args.symbol} / {args.period_range}', file=sys.stderr if args.verbose else sys.stdout)

    try:
        # Create BacktestConfig from arguments
        config = BacktestConfig(
            period_range=args.period_range,
            initial_capital=args.initial_capital,
            entry_score=args.entry_score,
            stop_atr=args.stop_atr,
            target_atr=args.target_atr,
            risk_pct=args.risk_pct,
            early_exit=args.early_exit,
            adx_min=args.adx_min,
        )

        result = run_historical_backtest(args.symbol, config)

        if 'error' in result:
            error_msg = result['error']
            if args.json_output:
                json.dump({"status": "error", "message": error_msg, "input": vars(args)}, sys.stdout)
                sys.exit(1)
            else:
                print(f'ERROR: {error_msg}')
                sys.exit(1)

        # Output formatting
        if args.json_output:
            # Include configuration used in output
            output_data = {
                "symbol": args.symbol,
                "config": {
                    "period_range": config.period_range,
                    "initial_capital": config.initial_capital,
                    "entry_score": config.entry_score,
                    "stop_atr": config.stop_atr,
                    "target_atr": config.target_atr,
                    "risk_pct": config.risk_pct,
                    "early_exit": config.early_exit,
                    "adx_min": config.adx_min,
                },
                "backtest_result": result
            }
            json.dump(output_data, sys.stdout, indent=2)
        else:
            # Original output format (less verbose, suitable for CLI)
            for k, v in result.items():
                if k not in ('trades', 'equity_curve'):
                    print(f'{k}: {v}')
            print(f'trade count: {len(result.get("trades", []))}')

    except Exception as e:
        error_msg = f'BACKTEST FAILED: {str(e)}'
        if args.json_output:
            json.dump({"status": "error", "message": error_msg, "input": vars(args)}, sys.stdout)
            sys.exit(1)
        else:
            print(error_msg, file=sys.stderr if args.verbose else sys.stdout)
            sys.exit(1)
if __name__ == '__main__':
    main()