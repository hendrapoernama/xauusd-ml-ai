# Trading Modes & Analysis - Example Outputs

This document shows realistic examples of what you'll see when using the new Telegram commands.

---

## Trading Modes Examples

### 1. `/modes` — List All Available Modes

**Command:**
```
/modes
```

**Output:**
```
📊 TRADING MODES

✅ AGGRESSIVE (Threshold: 60%, Max Pos: 4, Max Loss: 5%)
   NORMAL (Threshold: 65%, Max Pos: 3, Max Loss: 3%)
   CONSERVATIVE (Threshold: 70%, Max Pos: 2, Max Loss: 2%)
   RESTRICTED (Threshold: 75%, Max Pos: 1, Max Loss: 1%)

Use /mode_info <name> to see full details
```

---

### 2. `/mode_info <NAME>` — Get Details About a Specific Mode

**Command:**
```
/mode_info AGGRESSIVE
```

**Output:**
```
AGGRESSIVE ✅ ACTIVE

High risk, high reward. Ideal for volatile markets and experienced traders.

Settings:
  • ML Threshold: 60%
  • Max Positions: 4
  • Max Daily Loss: 5.0%
  • Risk/Trade: 2.0%
  • Max Loss/Position: $50.00
```

**Another example with CONSERVATIVE:**
```
/mode_info CONSERVATIVE
```

**Output:**
```
CONSERVATIVE 

Low risk, capital preservation. For quiet markets.

Settings:
  • ML Threshold: 70%
  • Max Positions: 2
  • Max Daily Loss: 2.0%
  • Risk/Trade: 1.0%
  • Max Loss/Position: $25.00
```

---

### 3. `/setmode <NAME>` — Switch to a Different Mode

**Command:**
```
/setmode AGGRESSIVE
```

**Output (Successful):**
```
✅ MODE SWITCHED

NORMAL → AGGRESSIVE

New Settings:
  • ML Threshold: 60%
  • Max Positions: 4
  • Max Daily Loss: 5.0%
  • Risk/Trade: 2.0%

Settings applied immediately to live trading.

⏰ 14:35:22 WIB
```

**Output (Invalid Mode):**
```
❌ Unknown mode: UNKNOWN_MODE
Valid modes: AGGRESSIVE, NORMAL, CONSERVATIVE, RESTRICTED
```

---

## Position Analysis Examples

### 1. `/analysis` — Analyze Why No Positions Opened

#### Example 1: Low Execution Rate (Threshold Blocking)

**Command:**
```
/analysis
```

**Output:**
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
  ⚠️ Very low execution: 11.1%. Most signals are blocked.
  🚫 Top blocker: below_threshold (55.6% of signals)
  💡 Suggestion: ML threshold too high. Consider lowering from 0.65 to 0.60 or switch to AGGRESSIVE mode.
  📈 Avg signal confidence: 68%. Signals are strong.
  📊 Market regime: MEDIUM_VOLATILITY. Volatility and trend character affects entry opportunities.
  ✅ Good win rate: 80.0%. The trades that do execute are profitable.
  💰 Session profit: +$156.50. Profitable despite low signal volume.

⏰ 14:35:45 WIB
```

**Analysis & Action:**
- **Problem:** Only 11% execution rate, mostly blocked by threshold
- **Root Cause:** ML threshold (65%) is too high for market conditions
- **Action:** Switch to AGGRESSIVE mode or manually lower threshold to 60%
- **Why It's Good:** Win rate is 80%, so executed trades are profitable — it's a quantity issue, not quality

---

#### Example 2: Perfect Execution (Balanced)

**Command:**
```
/analysis
```

**Output:**
```
📊 POSITION ANALYSIS
(Last 3 days - 2026-06-10)

Summary:
  • Total Signals: 32
  • Total Trades: 22
  • Execution Rate: 68.8%
  • Avg Confidence: 72%

Signals by Type:
  • BUY: 18
  • SELL: 14
  • NONE: 0

Market Regime:
  • TRENDING: 22 signals
  • RANGING: 10 signals

Market Quality Breakdown:
  • EXCELLENT: 15 signals
  • GOOD: 12 signals
  • MODERATE: 5 signals

Top Blocking Factors:
  🚫 max_positions_reached: 8 (25.0%)
  🚫 below_threshold: 2 (6.3%)

Trade Results:
  ✅ Win Rate: 72.7%
  📈 Total P/L: +$485.75

🎯 Key Insights:
  📈 Solid execution: 68.8%. Most strong signals become trades.
  🚫 Top blocker: max_positions_reached (25.0% of signals)
  📈 Avg signal confidence: 72%. Signals are strong.
  📊 Market regime: TRENDING. Good momentum for trend-following signals.
  ✅ Good win rate: 72.7%. Strategy is working well.
  💰 Session profit: +$485.75. Excellent profitable session.

⏰ 14:35:45 WIB
```

**Analysis & Action:**
- **Status:** Everything is balanced and working well
- **Execution Rate:** 68% is healthy
- **Minor Blocking:** Position limits occasionally block signals (25%) — consider taking some profits
- **Performance:** 72% win rate and +$485 profit is excellent
- **Action:** Stay in NORMAL mode, monitor position exits

---

#### Example 3: Poor Win Rate (Strategy Issue)

**Command:**
```
/analysis
```

**Output:**
```
📊 POSITION ANALYSIS
(Last 3 days - 2026-06-09)

Summary:
  • Total Signals: 28
  • Total Trades: 24
  • Execution Rate: 85.7%
  • Avg Confidence: 65%

Signals by Type:
  • BUY: 16
  • SELL: 12
  • NONE: 0

Market Regime:
  • RANGING: 18 signals
  • VOLATILE: 10 signals

Market Quality Breakdown:
  • MODERATE: 16 signals
  • GOOD: 8 signals
  • POOR: 4 signals

Top Blocking Factors:
  🚫 session_filter_failed: 3 (10.7%)
  🚫 position_limit: 1 (3.6%)

Trade Results:
  ❌ Win Rate: 41.7%
  📉 Total P/L: -$125.00

🎯 Key Insights:
  📊 Execution rate is good (85.7%), but win rate is poor.
  ❌ Low win rate: 41.7%. Strategy needs review.
  📊 Market regime: RANGING. Sideways market affects trend-following signals.
  📉 Session loss: -$125.00. Review exit strategy or avoid ranging periods.

⏰ 14:35:45 WIB
```

**Analysis & Action:**
- **Problem:** High execution (85%) but low win rate (41%)
- **Root Cause:** Not a filter problem; market was ranging (sideways), hurting signals
- **Action:** 
  - Switch to CONSERVATIVE mode to reduce entries
  - Wait for trending market
  - Review exit logic (stops may be too tight)
  - Possibly avoid RANGING regime manually

---

#### Example 4: No Signals At All

**Command:**
```
/analysis
```

**Output:**
```
📊 POSITION ANALYSIS
(Last 3 days - 2026-06-08)

Summary:
  • Total Signals: 0
  • Total Trades: 0
  • Execution Rate: 0.0%
  • Avg Confidence: 0%

Signals by Type: {}
Top blocking reasons: []
Regime distribution: {}
Market quality: {}

🎯 Key Insights:
  🟡 No signals generated in the last 3 days. Market may be in ranging/low-conviction regime.

⏰ 14:35:45 WIB
```

**Analysis & Action:**
- **Status:** Market had zero signals — completely quiet or consolidated
- **Market Condition:** Likely RANGING/low volatility
- **Action:** 
  - This is normal during low-volatility periods
  - Wait for breakout
  - Can switch to RESTRICTED mode (won't help, still no signals)
  - Monitor /status to see when trading resumes

---

## Combined Workflow Examples

### Workflow 1: Morning Check with Decision

```
User Action 1: Check modes
Command: /modes
Output: Shows NORMAL is active

User Action 2: Analyze previous 3 days
Command: /analysis
Output: 
  - Execution Rate: 11.1%
  - Top blocker: below_threshold (55.6%)
  - Win rate: 80%

Decision: Threshold is too high! Switch to AGGRESSIVE

User Action 3: Switch mode
Command: /setmode AGGRESSIVE
Output: ✅ MODE SWITCHED: NORMAL → AGGRESSIVE

User Action 4: Verify status
Command: /status
Output: Shows bot with AGGRESSIVE mode active

Result: Bot now accepts more signals (ML threshold 60% vs 65%)
```

---

### Workflow 2: Recovery from Losses

```
User Action 1: Check balance after loss
Command: /balance
Output: 
  - Daily loss: $250 (5% of capital)
  - Daily loss limit reached!

User Action 2: Switch to recovery mode
Command: /setmode RESTRICTED
Output: ✅ MODE SWITCHED: NORMAL → RESTRICTED

User Action 3: Analyze what happened
Command: /analysis
Output:
  - Win rate: 35%
  - Only 4 trades in 3 days
  - Market quality was low

Decision: Market was poor quality, RESTRICTED mode will help

User Action 4: Monitor for recovery
Wait for balance to recover, then /modes to switch back to NORMAL
```

---

### Workflow 3: Optimizing for Volatile Market

```
User Action 1: Notice high volatility in /status
Shows: Volatility = HIGH, Regime = VOLATILE

User Action 2: Check analysis for insights
Command: /analysis
Output:
  - Market regime: HIGH_VOLATILITY
  - Execution rate: 25% (low)
  - Win rate: 78% (high)
  - Top blocker: position_limit (60%)

Insight: Signals are good (78% win) but position limits are blocking

Decision 1: Increase position limit by switching mode
User: /setmode AGGRESSIVE
Result: Max positions 4 (vs 3), can take more trades

Decision 2: Let trades close more naturally
Wait and monitor /positions to see execution

User Action 3: Check results next hour
Command: /analysis (next time)
Should see higher execution rate with AGGRESSIVE mode
```

---

## Real-World Scenarios

### Scenario A: "Why no trades for 3 days?"

**Day 1:** 15:30 WIB - User notices no trades opened
```
/analysis

Output shows:
- Signals: 32
- Trades: 0
- Execution: 0%
- Top blocker: below_threshold (78%)
- Avg confidence: 59% (below 65% threshold)

Insight: Weak signals meet weak threshold → no trades
```

**Action:** Wait for stronger signals OR switch to AGGRESSIVE

**Day 2:** 14:00 WIB - Check again
```
/analysis

Output shows:
- Signals: 8
- Trades: 2
- Execution: 25%
- Top blocker: max_positions_reached
- Win rate: 100%

Insight: Better market, trades executing, positions full
```

**Action:** Keep AGGRESSIVE, trades are winning

---

### Scenario B: "Bot is losing money"

**Day 1:** 16:00 WIB - Check analysis
```
/analysis

Output shows:
- Signals: 42
- Trades: 38
- Execution: 90%
- Win rate: 38%
- P/L: -$280

Insight: High execution but low quality → strategy issue
```

**Action:** Don't change threshold (already executing 90%), review market conditions

**Check regime:**
- If RANGING → Market is consolidating, avoid
- If VOLATILE → Signals may be whipsaw, tighten exits

**Day 2:** Switch mode based on regime
```
If market is RANGING:
  /setmode CONSERVATIVE  (fewer entries in bad market)

If market is VOLATILE:
  /setmode NORMAL  (calm down from AGGRESSIVE if was active)
```

---

## Command Quick Reference

| Goal | Command | Expected Output |
|------|---------|---|
| See all modes | `/modes` | List with ✅ current |
| Get mode details | `/mode_info AGGRESSIVE` | Full config |
| Switch mode | `/setmode CONSERVATIVE` | Confirmation + new settings |
| Analyze 3 days | `/analysis` | Report: signals, blocks, insights |
| Check bot status | `/status` | Current mode + balance |
| See positions | `/positions` | Open trades with P/L |
| Check account | `/balance` | Account metrics |

---

## Tips for Reading Analysis

### High Execution Rate (>60%)
✅ Good — Filters aren't blocking much
- Most signals become trades
- If win rate also high → Mode is perfect
- If win rate low → Quality issue, not quantity

### Low Execution Rate (<20%)
⚠️ Check why:
- If `below_threshold` blocks > 50% → Raise mode to AGGRESSIVE
- If `max_positions_reached` blocks > 50% → Close winners or increase mode
- If `market_score_low` blocks > 50% → Market is poor, use CONSERVATIVE
- If no blocked signals → Market had no signals at all

### High Win Rate (>70%)
✅ Excellent — Your signals are good
- Executed trades are profitable
- If execution is low → Just need more trades (raise mode)
- If execution is high → Perfect, stay in this mode

### Low Win Rate (<50%)
❌ Problem — Need adjustment:
- Market condition doesn't fit strategy
- Exit logic needs review
- Avoid this market regime temporarily
- Consider using CONSERVATIVE mode

### Mixed Signals
- High execution + low win rate → Quantify problem (too many wrong trades)
- Low execution + high win rate → Filter problem (blocking good trades)
- No signals → Wait for market opportunity
- All metrics good → Stay in current mode
