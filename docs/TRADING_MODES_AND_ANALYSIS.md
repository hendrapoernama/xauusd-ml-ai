# Trading Modes & Position Analysis Guide

## Overview

Two new features have been added to XAUBot AI to help you understand and control trading behavior:

1. **Trading Modes System** — Dynamic trading mode configuration via Telegram
2. **Position Analysis** — Automatic ML-driven analysis of why positions aren't opening

---

## Feature 1: Trading Modes System

### What It Does

The Trading Modes system allows you to quickly switch between 4 predefined trading modes via Telegram, each with different risk parameters optimized for different market conditions.

### Available Modes

#### 🟢 AGGRESSIVE
**Best for:** High volatility, strong trends, growth phase
- **ML Threshold:** 60% (lowest - more signals)
- **Max Positions:** 4
- **Max Daily Loss:** 5% of capital
- **Risk per Trade:** 2%
- **Max Loss per Position:** $50

#### 🟡 NORMAL (Default)
**Best for:** Balanced trading, most market conditions
- **ML Threshold:** 65%
- **Max Positions:** 3
- **Max Daily Loss:** 3% of capital
- **Risk per Trade:** 1.5%
- **Max Loss per Position:** $40

#### 🔵 CONSERVATIVE
**Best for:** Low volatility, range-bound markets, capital preservation
- **ML Threshold:** 70%
- **Max Positions:** 2
- **Max Daily Loss:** 2% of capital
- **Risk per Trade:** 1%
- **Max Loss per Position:** $25

#### 🔴 RESTRICTED
**Best for:** Recovery mode, low confidence periods, drawdown management
- **ML Threshold:** 75% (highest - only strong signals)
- **Max Positions:** 1
- **Max Daily Loss:** 1% of capital
- **Risk per Trade:** 0.5%
- **Max Loss per Position:** $10

### Telegram Commands

#### `/modes`
Lists all available trading modes with current active mode marked.
```
📊 TRADING MODES

✅ AGGRESSIVE (Threshold: 60%, Max Pos: 4, Max Loss: 5%)
   NORMAL (Threshold: 65%, Max Pos: 3, Max Loss: 3%)
   CONSERVATIVE (Threshold: 70%, Max Pos: 2, Max Loss: 2%)
   RESTRICTED (Threshold: 75%, Max Pos: 1, Max Loss: 1%)
```

#### `/mode_info <NAME>`
Shows detailed information about a specific mode.
```
/mode_info AGGRESSIVE
```
Returns full specification with description and all parameters.

#### `/setmode <NAME>`
Switches to a new trading mode immediately.
```
/setmode AGGRESSIVE
```
The bot will:
1. Switch the mode
2. Apply new ML threshold to signal filtering
3. Update max positions allowed
4. Adjust daily loss limits
5. Send confirmation message

Settings are applied **immediately** to live trading (no restart needed).

### How Modes Work

When you switch modes:

1. **ML Threshold** - Controls the confidence requirement for ML signals to trigger trades
   - Lower threshold (AGGRESSIVE) = more trades, higher variance
   - Higher threshold (RESTRICTED) = fewer trades, higher quality

2. **Max Positions** - Limits concurrent open positions
   - AGGRESSIVE: Up to 4 positions
   - NORMAL: Up to 3 positions
   - CONSERVATIVE: Up to 2 positions
   - RESTRICTED: Only 1 position

3. **Daily Loss Limit** - Hard stop when daily loss reaches this %
   - At this point, bot enters STOPPED mode until next day

4. **Risk per Trade** - % of capital at risk per individual trade
   - Affects position sizing

### When to Use Each Mode

| Market Condition | Regime | Volatility | Recommended Mode |
|---|---|---|---|
| Strong trend, high conviction | TRENDING | HIGH | AGGRESSIVE |
| Normal market conditions | TRENDING | MEDIUM | NORMAL |
| Range-bound, low confidence | RANGING | LOW | CONSERVATIVE |
| Recovery from losses | ANY | ANY | RESTRICTED |
| Drawdown period | ANY | ANY | RESTRICTED |

### Mode Persistence

- Current mode is saved to `data/current_mode.json`
- On bot restart, it loads the previously active mode
- Mode switching is logged with timestamp

---

## Feature 2: Position Analysis

### What It Does

The Position Analysis feature automatically examines your trade logs and signal history to understand **why no positions opened** during a selected period (typically last 3 days).

It uses ML-driven analysis to:
- Count total signals generated vs executed trades
- Identify top blocking factors preventing trades
- Analyze market conditions during the period
- Calculate win rate and profitability of executed trades
- Generate AI-driven insights with recommendations

### Telegram Command

#### `/analysis`
Analyzes the last 3 days and generates a comprehensive report.

```
📊 POSITION ANALYSIS
(Last 3 days - 2026-06-11)

Summary:
  • Total Signals: 45
  • Total Trades: 5
  • Execution Rate: 11.1%
  • Avg Confidence: 68%

Signals by Type:
  • BUY: 28
  • SELL: 17
  • NONE: 0

Market Regime:
  • MEDIUM_VOLATILITY: 32 signals
  • HIGH_VOLATILITY: 13 signals

Market Quality Breakdown:
  • GOOD: 22 signals
  • MODERATE: 15 signals
  • POOR: 8 signals

Top Blocking Factors:
  🚫 below_threshold: 25 (55.6%)
  🚫 max_positions_reached: 12 (26.7%)
  🚫 market_score_low: 5 (11.1%)
  🚫 session_filter_failed: 3 (6.7%)

Trade Results:
  ✅ Win Rate: 80.0%
  📈 Total P/L: +$156.50

🎯 Key Insights:
  ⚠️ Very low execution: 11.1%. Most signals are blocked by filters.
  🚫 Top blocker: below_threshold (55.6% of signals)
  💡 Suggestion: ML threshold too high. Consider lowering from 0.65 to 0.60 or switch to AGGRESSIVE mode.
  📈 Avg signal confidence: 68%. Signals are strong.
  📊 Market regime: MEDIUM_VOLATILITY. Volatility and trend character affects entry opportunities.
  ✅ Good win rate: 80.0%. The trades that do execute are profitable.
  💰 Session profit: +$156.50. Profitable despite low signal volume.
```

### What the Report Shows

#### Summary
- **Total Signals:** How many trade signals were generated
- **Total Trades:** How many of those signals became actual trades
- **Execution Rate:** % of signals that were executed
- **Avg Confidence:** Average ML confidence of generated signals

#### Signals by Type
- **BUY:** Number of buy signals
- **SELL:** Number of sell signals
- **NONE:** Number of neutral signals

#### Market Regime Distribution
Shows what market conditions were present during the period:
- TRENDING, RANGING, VOLATILE, etc.

#### Market Quality Breakdown
Shows signal quality distribution:
- **EXCELLENT** (score >= 70)
- **GOOD** (score 60-69)
- **MODERATE** (score 50-59)
- **POOR** (score < 50)

#### Top Blocking Factors
Shows the **most common reasons** signals weren't executed:
- `below_threshold` — ML confidence below required threshold
- `max_positions_reached` — Already at max concurrent positions
- `market_score_low` — Market quality filter too strict
- `session_filter_failed` — Trading session restrictions
- `regime_filter_failed` — Market regime not suitable

#### Trade Results
If trades were executed during the period:
- **Win Rate:** % of trades that were profitable
- **Total P/L:** Net profit/loss from all trades

#### AI-Driven Insights
Automatic recommendations based on the data:
- High execution rate is good; low rate suggests filters are too strict
- If threshold blocking > 50%, suggests lowering ML threshold or switching to AGGRESSIVE mode
- If position limit blocking > 30%, suggests closing winners to free slots
- If win rate < 50%, suggests reviewing exit strategy
- Market regime analysis tells you what conditions to expect

### How to Use Analysis

**Scenario 1: No positions for 3 days**
```
Use /analysis to see if:
- Market had no signals at all → wait for breakout or use RESTRICTED
- Signals generated but blocked → threshold too high or filters too strict
- Max positions reached → close profitable positions first
```

**Scenario 2: Low win rate on executed trades**
```
/analysis shows win rate < 50%
→ Recommendation: Review exit strategy, possibly lower risk or switch to CONSERVATIVE
```

**Scenario 3: Good win rate but low execution**
```
/analysis shows 80% win rate but 10% execution
→ Recommendation: Raise ML threshold is not the issue; market simply had low signal quality
```

**Scenario 4: High volatility period**
```
/analysis shows VOLATILE regime with many blocked signals
→ Recommendation: Try AGGRESSIVE mode to capture volatile moves
```

### Analysis Data Sources

The analyzer reads from trade logs:
- **Signals:** `data/trade_logs/signals/signals_YYYY_MM.csv`
- **Trades:** `data/trade_logs/trades/trades_YYYY_MM.csv`

Each signal record contains:
- Timestamp, signal type (BUY/SELL/NONE)
- ML confidence, SMC confidence
- Market score, regime, volatility, session
- **execution_reason** — Why it was/wasn't executed

---

## Integration with Main Bot

### Trading Modes Integration

1. **On Startup:**
   - `trading_modes.py` loads current mode from `data/current_mode.json`
   - If file doesn't exist, defaults to NORMAL
   - Mode settings are applied to `config.risk` and `dynamic_confidence.threshold`

2. **During Trading:**
   - ML signals are filtered by current mode's threshold
   - Position limits are enforced from current mode's max_positions
   - Daily loss limits are enforced from current mode's max_daily_loss_pct

3. **On Mode Switch (via Telegram):**
   - `trading_modes.py` validates mode name
   - Saves to `data/current_mode.json`
   - Updates live config without restart
   - Telegram notifies you of settings applied

### Position Analysis Integration

1. **On `/analysis` Command:**
   - `position_analysis.py` reads last 3 days of signal/trade logs
   - Analyzes execution patterns and blocking factors
   - Generates insights based on data patterns
   - Formats output for Telegram display

2. **No Real-Time Impact:**
   - Analysis is read-only, purely informational
   - Doesn't affect live trading
   - Can be run at any time without performance impact

---

## Files Added/Modified

### New Files Created
```
src/trading_modes.py        — Trading mode definitions & manager
src/position_analysis.py    — Position analysis engine
docs/TRADING_MODES_AND_ANALYSIS.md  — This guide
```

### Modified Files
```
src/telegram_commands.py    — Added 4 new Telegram command handlers
main_live.py               — Initialized trading mode manager on startup
```

### New Data Files (Auto-Created)
```
data/current_mode.json     — Persists current mode between restarts
```

---

## FAQ

**Q: Can I switch modes during an open position?**
A: Yes! Mode switches apply immediately. Existing positions are unaffected. The new mode affects only new trades.

**Q: What if I want to add a custom mode?**
A: Edit `src/trading_modes.py`, add new mode to `TRADING_MODES` dict, and the system will include it.

**Q: Does mode switching require bot restart?**
A: No! Changes apply immediately to live trading without any restart.

**Q: What if I manually close positions from another app?**
A: The analysis will still be accurate because it reads actual trade logs, not position count.

**Q: Can I analyze longer than 3 days?**
A: Not via Telegram, but you can modify the call in code. Edit the `/analysis` command in `telegram_commands.py`.

**Q: What does "market_score" mean in the analysis?**
A: It's a composite quality score (0-100) considering market volatility, trend strength, and signal alignment.

**Q: How often is analysis run?**
A: Only when you use `/analysis` command. It's computed on-demand, not continuously.

**Q: Can I see historical mode changes?**
A: Yes, they're logged to `logs/trading_bot_YYYY-MM-DD.log` with "Trading mode changed:" entries.

---

## Tips & Tricks

### Use Modes Like This:
1. **Start with NORMAL** — baseline balanced mode
2. **If many blocked signals** → switch to AGGRESSIVE to be more permissive
3. **If you hit daily loss limit** → switch to RESTRICTED to recover
4. **When drawdown recovers** → return to NORMAL
5. **In quiet markets** → try CONSERVATIVE to avoid false signals

### Combine with Analysis:
1. Run `/analysis` to understand current bottleneck
2. If threshold blocking is high → use AGGRESSIVE
3. If position limit blocking is high → close winners, stay in current mode
4. If market quality poor → use CONSERVATIVE
5. Check again after 24 hours

### Smart Mode Switching:
```
Morning: Check /analysis
  - If execution rate < 20% and threshold blocking > 50%
    → Use AGGRESSIVE for the session
  
  - If execution rate > 50% but win rate < 50%
    → Stay in NORMAL, review exits

Afternoon: Check /balance and /positions
  - If daily P/L positive and open positions
    → Consider CONSERVATIVE to protect profits

Evening: Use /status to verify current mode before close
```

---

## Technical Details

### Mode Manager Class Diagram

```
TradingModeManager
├── get_current_mode() → str
├── set_mode(name: str) → bool
├── get_mode_config(name: str) → ModeConfig
├── list_modes() → List[Dict]
├── get_mode_summary(name: str) → str
├── get_all_modes_summary() → str
├── apply_mode_to_config(config) → bool
└── get_mode_stats() → Dict
```

### Position Analyzer Class Diagram

```
PositionAnalyzer
├── analyze_no_positions(days: int) → AnalysisResult
├── _load_signals_last_days(days: int) → List[SignalRecord]
├── _load_trades_last_days(days: int) → List[Dict]
├── _analyze_blocking_factors(signals) → Dict[str, int]
├── _analyze_signal_types(signals) → Dict[str, int]
├── _analyze_regimes(signals) → Dict[str, int]
├── _analyze_market_quality(signals) → Dict[str, int]
└── _generate_insights(analysis, signals) → List[str]
```

---

## Support & Debugging

If modes/analysis aren't working:

1. **Check mode file exists:**
   ```
   ls -la data/current_mode.json
   ```

2. **Check Telegram commands are registered:**
   - Run bot and look for:
     ```
     Telegram commands registered: /balance, /positions, /status, ..., /modes, /setmode, /analysis
     ```

3. **Check trade logs exist:**
   ```
   ls -la data/trade_logs/trades/
   ls -la data/trade_logs/signals/
   ```

4. **Run test manually:**
   ```
   python -m src.trading_modes
   python -m src.position_analysis
   ```

5. **Check logs for errors:**
   ```
   tail -f logs/trading_bot_2026-06-11.log | grep -i "mode\|analysis"
   ```

---

## Version History

- **v1.0** (2026-06-11)
  - Initial release with 4 trading modes
  - Position analysis for last 3 days
  - Telegram command integration
  - Mode persistence and auto-load
  - AI-driven insights generation
