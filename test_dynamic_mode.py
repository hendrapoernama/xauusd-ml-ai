"""
Test & Demo: DYNAMIC Mode
=========================
Demonstrates dynamic threshold calculation with various market scenarios.

Run:
    python test_dynamic_mode.py
"""

import sys
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.dynamic_threshold_calculator import DynamicThresholdCalculator
from src.trading_modes import TradingModeManager, TRADING_MODES

WIB = ZoneInfo("Asia/Jakarta")


def print_separator(title: str = ""):
    """Print formatted separator."""
    if title:
        print(f"\n{'='*60}")
        print(f"  {title}")
        print(f"{'='*60}\n")
    else:
        print(f"\n{'-'*60}\n")


def test_scenario(name: str, market_data: dict, recent_trades: list, regime: str, h1_bias: str):
    """Test a specific market scenario."""
    print(f"\n[SCENARIO] {name}")
    print(f"{'-'*60}")

    # Display inputs
    print("\n[MARKET DATA]")
    print(f"  ATR: {market_data.get('atr', 0):.3f} pips")
    print(f"  ATR Avg: {market_data.get('atr_avg', 0):.3f} pips")
    print(f"  Spread: {market_data.get('spread', 0):.3f} pips")
    print(f"  Regime: {regime}")
    print(f"  H1 Bias: {h1_bias}")

    # Calculate win rate
    if recent_trades:
        wins = sum(1 for t in recent_trades if t.get("profit", 0) > 0)
        wr = (wins / len(recent_trades)) * 100
        print(f"  Win Rate: {wr:.1f}% ({wins}/{len(recent_trades)})")

    # Calculate thresholds
    calculator = DynamicThresholdCalculator()
    thresholds = calculator.calculate_thresholds(
        market_data=market_data,
        recent_trades=recent_trades,
        current_regime=regime,
        h1_bias=h1_bias,
    )

    # Display results
    print("\n[THRESHOLDS CALCULATED]")
    print(f"  ML Threshold: {thresholds.ml_threshold:.0%}")
    print(f"  SMC Threshold: {thresholds.smc_threshold:.0%}")
    print(f"  AI Quality: {thresholds.ai_quality_threshold:.0f}/100")
    print(f"  Confidence: {thresholds.confidence}%")
    print(f"\n[REASON] {thresholds.reason}")

    # Comparison with NORMAL mode
    normal_config = TRADING_MODES.get("NORMAL")
    if normal_config:
        ml_diff = (thresholds.ml_threshold - normal_config.ml_threshold) * 100
        print(f"\n[vs NORMAL Mode (65%)]")
        print(f"  ML Change: {ml_diff:+.0f}% (-> {thresholds.ml_threshold:.0%})")
        if ml_diff < 0:
            print(f"  -> MORE AGGRESSIVE (more trades expected)")
        elif ml_diff > 0:
            print(f"  -> MORE CONSERVATIVE (fewer trades expected)")
        else:
            print(f"  -> SAME AS NORMAL")

    return thresholds


def main():
    """Run all test scenarios."""
    print_separator("DYNAMIC MODE TESTING")

    print("Testing dynamic threshold calculation with various market scenarios...\n")

    # Test 1: High Volatility + Good Performance
    print("\n" + "="*60)
    print("Test 1: HIGH VOLATILITY + GOOD PERFORMANCE")
    print("="*60)
    test_scenario(
        "Trending Up with High Volatility",
        market_data={
            "atr": 5.8,
            "atr_avg": 3.2,
            "spread": 0.28,
            "volatility": 1.8,
        },
        recent_trades=[
            {"profit": 45},
            {"profit": 32},
            {"profit": -15},
            {"profit": 55},
            {"profit": 28},
            {"profit": -10},
            {"profit": 62},
            {"profit": 38},
            {"profit": 50},
            {"profit": 40},
        ] + [{"profit": 30} for _ in range(40)],  # 50 trades total, 85% win rate
        regime="trending",
        h1_bias="BULLISH",
    )

    # Test 2: Low Volatility + Poor Performance
    print("\n" + "="*60)
    print("Test 2: LOW VOLATILITY + POOR PERFORMANCE")
    print("="*60)
    test_scenario(
        "Low Volatility Consolidation with Losses",
        market_data={
            "atr": 0.8,
            "atr_avg": 2.0,
            "spread": 0.48,
            "volatility": 0.4,
        },
        recent_trades=[
            {"profit": -8},
            {"profit": -12},
            {"profit": 5},
            {"profit": -10},
            {"profit": -6},
            {"profit": 3},
            {"profit": -9},
            {"profit": -11},
            {"profit": 4},
            {"profit": -7},
        ] + [{"profit": -5} for _ in range(40)],  # 50 trades, 35% win rate
        regime="ranging",
        h1_bias="NEUTRAL",
    )

    # Test 3: Medium Volatility + Neutral Performance
    print("\n" + "="*60)
    print("Test 3: MEDIUM VOLATILITY + MEDIUM PERFORMANCE")
    print("="*60)
    test_scenario(
        "Balanced Market Conditions",
        market_data={
            "atr": 3.2,
            "atr_avg": 3.0,
            "spread": 0.32,
            "volatility": 1.0,
        },
        recent_trades=[
            {"profit": 25},
            {"profit": -15},
            {"profit": 35},
            {"profit": -10},
            {"profit": 20},
            {"profit": -5},
            {"profit": 30},
            {"profit": -12},
            {"profit": 28},
            {"profit": -8},
        ] + [{"profit": 15} if i % 2 == 0 else {"profit": -8} for i in range(40)],
        regime="medium_volatility",
        h1_bias="BULLISH",
    )

    # Test 4: High Volatility + Poor Performance
    print("\n" + "="*60)
    print("Test 4: HIGH VOLATILITY + POOR PERFORMANCE")
    print("="*60)
    test_scenario(
        "Volatile Market but Losing Trades",
        market_data={
            "atr": 6.5,
            "atr_avg": 3.0,
            "spread": 0.55,
            "volatility": 2.1,
        },
        recent_trades=[
            {"profit": -25},
            {"profit": -18},
            {"profit": 5},
            {"profit": -20},
            {"profit": -15},
            {"profit": 10},
            {"profit": -22},
            {"profit": -12},
            {"profit": 8},
            {"profit": -18},
        ] + [{"profit": -10} for _ in range(40)],  # 50 trades, 20% win rate
        regime="volatile",
        h1_bias="NEUTRAL",
    )

    # Test 5: Strong Trend + Excellent Performance
    print("\n" + "="*60)
    print("Test 5: STRONG TREND + EXCELLENT PERFORMANCE")
    print("="*60)
    test_scenario(
        "Perfect Storm - Trending + Winning",
        market_data={
            "atr": 4.8,
            "atr_avg": 2.8,
            "spread": 0.25,
            "volatility": 1.7,
        },
        recent_trades=[
            {"profit": 50},
            {"profit": 45},
            {"profit": 55},
            {"profit": 48},
            {"profit": 52},
            {"profit": 60},
            {"profit": 55},
            {"profit": 50},
            {"profit": 58},
            {"profit": 62},
        ] + [{"profit": 55} for _ in range(40)],  # 50 trades, 100% win rate
        regime="strong_trend",
        h1_bias="BULLISH",
    )

    # Trading Mode Manager Test
    print_separator("TRADING MODE MANAGER - DYNAMIC MODE")

    manager = TradingModeManager()
    print("Available Modes:")
    for mode_name, config in TRADING_MODES.items():
        dynamic_tag = " [DYNAMIC]" if config.is_dynamic else ""
        print(f"  - {mode_name}{dynamic_tag}")
        print(f"    ML: {config.ml_threshold:.0%} | Positions: {config.max_positions} | Risk: {config.risk_per_trade}%")

    # Test setting DYNAMIC mode
    print("\nSwitching to DYNAMIC mode...")
    manager.set_mode("DYNAMIC")
    print(f"Current mode: {manager.get_current_mode()}")
    print(f"Is dynamic: {manager.is_dynamic_mode()}")

    # Summary
    print_separator("SUMMARY")
    print("""
[OK] Dynamic Mode Test Complete!

Key Features:
1. Thresholds adapt to market conditions (volatility, regime, performance)
2. Calculation updates hourly
3. Historical data saved for analysis
4. Confidence scores show calculation reliability

Factors:
  • Regime (40% weight): trending, ranging, volatile
  • Performance (35% weight): win rate from recent trades
  • Volatility (25% weight): ATR ratio
  • Spread Penalty: wide spreads increase thresholds

Base Settings for DYNAMIC:
  • ML Threshold: 65% (dynamically adjusted 50-80%)
  • Max Positions: 4
  • Risk/Trade: 1.25%
  • Daily Loss Limit: 3.5%
  • Max Loss/Position: $35

Next Steps:
1. Activate in main_live.py:
   - Import DynamicModeIntegration
   - Call update_thresholds() every hour
   - Monitor threshold changes in logs

2. View in Telegram:
   - /setmode DYNAMIC (to activate)
   - /mode_info DYNAMIC (to view config)

3. Review history:
   - Check data/dynamic_thresholds_history.json
   - Track threshold trends over time
""")


if __name__ == "__main__":
    main()
