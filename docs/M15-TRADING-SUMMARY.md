# M15 Trading Cycle — Quick Reference

## The 15-Minute Trading Cycle Explained

```
┌─────────────────────────────────────────────────────────────────┐
│                    EVERY 15 MINUTES (M15)                       │
└─────────────────────────────────────────────────────────────────┘

WHY 15 MINUTES?
- XAUBot uses M15 candles (15-minute bars)
- Each M15 candle = 1 trading opportunity window
- When new M15 candle closes → full analysis runs
- Between candles → only monitor positions
```

---

## 2-Phase Architecture

### ⏱️ Every ~5 seconds (Main Loop)
```
while bot_running:
    if new_M15_candle_formed():
        → PHASE 2: Full Analysis (15-min cycle)
    else:
        → Quick position check (update stops, check TP)
    
    await asyncio.sleep(5)
```

### 🔍 Every 15 minutes (PHASE 2: Full Analysis)
```
M15 Candle Closes
    ↓
1️⃣ Fetch 200 M15 bars (50 hours history)
    ↓
2️⃣ Calculate 37 technical features (RSI, ATR, Bollinger, etc.)
    ↓
3️⃣ SMC Analysis (Order Blocks, Fair Value Gaps, BOS)
    ↓
4️⃣ Multi-timeframe bias (Check H1 trend)
    ↓
5️⃣ HMM Regime Detection (TRENDING/RANGING/VOLATILE?)
    ↓
6️⃣ XGBoost ML Prediction (BUY/SELL/HOLD + confidence)
    ↓
7️⃣ Apply 11 Entry Filters
    │
    ├─ Warmup done?
    ├─ Trading session allowed?
    ├─ No flash crash?
    ├─ Regime not RANGING?
    ├─ ML confidence >65%?
    ├─ SMC signal aligned?
    ├─ Spread <5 pips?
    ├─ No cooldown?
    ├─ Positions <5 open?
    ├─ Daily loss limit OK?
    └─ Dynamic confidence OK?
    ↓
    ALL FILTERS PASS? → Continue to 8️⃣
    ANY FILTER FAILS? → SKIP TRADE (Try next M15)
    ↓
8️⃣ Calculate risk-based position size
    ↓
9️⃣ Send order to MT5
    ↓
🔟 Log trade to database + Telegram notification
    ↓
1️⃣1️⃣ Manage open positions until next M15 or exit signal
```

---

## Timeline: Detailed Breakdown

```
14:15:00 — M15 Candle CLOSES
│
├─ 0ms:    Get new candle time from MT5
├─ 2ms:    Detect = NEW CANDLE → start iteration
├─ 5ms:    Fetch last 200 M15 bars (OHLCV data)
├─ 8ms:    Calculate 37 features (momentum, volatility, trend)
├─ 11ms:   SMC analysis (order blocks, FVG, BOS/CHOCH)
├─ 14ms:   HMM regime prediction (TRENDING/RANGING/VOLATILE)
├─ 20ms:   XGBoost inference (ML BUY/SELL/HOLD probability)
├─ 30ms:   Entry filter checks (11 conditions)
│
├─→ DECISION POINT (30ms elapsed)
│   │
│   ├─ If ALL filters pass:
│   │  ├─ 40ms: Calculate position size (Kelly criterion or fixed)
│   │  ├─ 50ms: Build order request
│   │  ├─ 70ms: Send to MT5 API
│   │  ├─ 80ms: Receive order confirmation
│   │  ├─ 85ms: Log to database
│   │  ├─ 90ms: Send Telegram notification
│   │  └─ Trade ENTERED ✓
│   │
│   └─ If ANY filter fails:
│      └─ 35ms: Log why trade was skipped
│          → Wait for next M15 candle
│
├─ 14:15:30 (15 seconds later)
│  └─ Position monitoring every 5 seconds:
│     ├─ Get current bid/ask price
│     ├─ Check if SL or TP hit
│     ├─ Update trailing SL
│     ├─ Evaluate exit conditions
│     └─ Poll Telegram commands
│
├─ 14:30:00 (15 minutes later)
│  └─ M15 Candle CLOSES again
│     └─ Next iteration begins (back to 0ms)
```

---

## 11 Entry Filters (All Must Pass)

| # | Filter | Purpose | Example |
|---|--------|---------|---------|
| 1 | ✓ Warmup Done | Let indicators stabilize | Skip first 3 M15 candles |
| 2 | ✓ Session | Trade only in high-liquidity hours | Allow 08:00-22:00 London/NY |
| 3 | ✓ Flash Crash | Detect sudden 2%+ moves | Emergency close if >2% in 5min |
| 4 | ✓ Regime | Skip choppy markets | Skip RANGING regime (optional) |
| 5 | ✓ ML Confidence | Signal must be strong enough | Require ≥65% confidence (tunable) |
| 6 | ✓ SMC Signal | Direction must match | BUY only if SMC=BUY or NONE |
| 7 | ✓ Spread | Execution cost acceptable | Reject if spread >5 pips |
| 8 | ✓ Cooldown | Avoid revenge trading | Don't re-enter for 15min |
| 9 | ✓ Position Limit | Don't over-expose | Max 5 open positions |
| 10 | ✓ Daily Loss | Stop if losing too much | Max -3% loss per day |
| 11 | ✓ Dynamic Confidence | Adjust for win rate | Raise threshold if losing streak |

**Example: Why Trade Was Rejected**
```
ML Signal: BUY (78% confidence)
SMC Signal: BUY (82% confidence)
Regime: RANGING ← ❌ FILTER 4 FAILS
Session: London (08:30) ✓
Spread: 2.5 pips ✓
...

Result: TRADE REJECTED
Reason: RANGING regime filter enabled (too risky to trade choppy market)
Action: Wait for next M15 candle (regime might change to TRENDING)
```

---

## What Happens Between Candles (5-10 second checks)

**While waiting for next M15 candle:**

```
Every 5 seconds (between M15 candles):

1. Get current price (1-2ms)
2. Check if SL/TP hit (1ms)
3. Update trailing SL if profit >$3 (1ms)
4. Evaluate regime change exit (1ms)
5. Check flash crash (2ms)
6. Poll Telegram commands (2ms)
7. Dashboard update (1ms)

Total: ~10ms (very lightweight)
↑
No full feature calculation
No re-prediction
Just use cached ML signal from last M15 candle
```

**Why not full analysis every 5 seconds?**
- ❌ Would waste CPU (50× recalculation)
- ❌ Would increase over-trading
- ❌ Would lag on real trades
- ✅ Reuse cached ML + just update price/stops

---

## Position Management (Active)

Once a trade is open:

```
Entry: BUY @ $2550.00
SL: $2538.50 (hard stop, 11.5 pips)
TP1: $2557.50 (1/3 close)
TP2: $2565.00 (1/3 close)
TP3: $2572.50 (1/3 close)

⏱️ Every 5 seconds → Check position:

✓ Is price >TP1?
  → Close 1/3 (lock profit)
  → Trail stop on remaining 2/3

✓ Has regime changed?
  → Close remaining positions (avoid whipsaw)

✓ Is profit >$3?
  → Activate trailing stop (-15 pips)

✓ Has position been open >4 hours?
  → Close all (avoid overnight gap)

✓ Did price hit SL?
  → Close immediately
  → Log loss
  → Trigger SL Learning Loop (AI analysis)
```

---

## SL Learning Loop (3 Layers)

**Every time a position closes with LOSS:**

```
┌──────────────────────────────────────────┐
│ Lapis 1: Detect SL Hit                   │
├──────────────────────────────────────────┤
│ Check MT5 history deals every 10 iter    │
│ Found: Position closed @ SL level        │
│ Log: ticket, exit price, loss amount     │
└──────────────────────────────────────────┘
         ↓
┌──────────────────────────────────────────┐
│ Lapis 2: Trigger ML Retrain              │
├──────────────────────────────────────────┤
│ If consecutive_losses >= 3:              │
│  → Immediately retrain XGBoost model     │
│  → Weight losing conditions 2× higher    │
│  → Next trades avoid same losing setup   │
└──────────────────────────────────────────┘
         ↓
┌──────────────────────────────────────────┐
│ Lapis 3: AI Narrative Analysis           │
├──────────────────────────────────────────┤
│ Send SL event to Z.AI/OpenRouter:        │
│ "Why did SL hit?"                        │
│ "Was it session wrong? Regime unstable?" │
│ AI returns: root_cause + lesson_learned  │
│ → Send to Telegram for user review       │
└──────────────────────────────────────────┘
```

**Example:**
```
SL Hit: Loss $12 @ 14:47
Z.AI Analysis:
  Root Cause: "Session off-hours (low liquidity), 
              bid-ask spread widened, SL grazed"
  Lesson: "Avoid entries 30min before session change"
  Confidence Modifier: -0.15 (reduce confidence next trade)

Result: Next BUY signal confidence drops 15% until 1 winning trade
```

---

## Why M15 (Not M5, H1, Daily)?

**XAUUSD Characteristics:**
- ✓ 24/5 liquid (excellent M15 data)
- ✓ Volatile but not noisy (M15 captures swings, M1 too spiky)
- ✓ News events clear at M15 (not buried in M1, not missed at H1)
- ✓ Session transitions visible (Sydney → London → NY cycles)

**Timeframe comparison:**

| TF | Noise | Signals | Opportunities/Day | Execution Risk | Verdict |
|----|-------|---------|-------------------|-----------------|---------|
| M1 | 🔴 High | Too many false | 100+ | Slippage | ❌ No |
| M5 | 🟡 Medium | Mixed | 30-50 | Medium | ⚠️ Maybe |
| **M15** | 🟢 Low | Clean | 10-15 | Low | ✅ **BEST** |
| H1 | 🟢 Very Low | Very clean | 3-5 | Very low | ⚠️ Slow |
| H4 | 🟢 Minimal | Excellent | 1-2 | Minimal | ⚠️ Very slow |
| Daily | 🟢 Clean | Beautiful | 1 | Minimal | ❌ Miss intraday |

---

## Key Statistics

| Metric | Value | Notes |
|--------|-------|-------|
| Execution Timeframe | M15 | 15-minute candles |
| Data History | 200 bars | ≈ 50 hours of OHLCV |
| Technical Features | 37 | Momentum, Volatility, Trend, Volume |
| SMC Detections | Order Blocks, FVG, BOS, CHOCH | Market structure analysis |
| Regime States | 3 (TRENDING/RANGING/VOLATILE) | HMM based |
| ML Model | XGBoost | Trained on 5000+ historical trades |
| Entry Filters | 11 | All must pass to enter |
| Position Limit | 5 max | Prevent over-leverage |
| Target Execution | <50ms | Iteration time |
| Loop Check Freq | Every 5 sec | Check for new candle |
| Position Check Freq | Every 5-10 sec | Update stops, evaluate exits |
| Telegram Polling | Every ~3 sec | Command responsiveness |

---

## Performance Optimization Tips

**If entries are too few (missing opportunities):**
```
↓ ML confidence threshold: 0.65 → 0.60
↑ Expand session filter: Add off-hours
→ Disable regime filter (accept RANGING)
```

**If entries are too many (over-trading):**
```
↑ ML confidence threshold: 0.65 → 0.75
↑ Require SMC signal strength >75%
→ Tighten spread filter: <3 pips
```

**If drawdown is high:**
```
↓ Position size: -50%
↑ SL distance: 11.5 → 20 pips
↓ Trailing start threshold: $3 → $2
→ Force close time: 4h → 2h
```

**If exits are slow:**
```
↑ Trailing stop distance: 15 → 8 pips
↓ TP1/TP2/TP3 levels: More aggressive
↑ Max daily loss: -3% → -2%
```

---

## Telegram Commands to Monitor

Check performance every hour:

```
/balance    → Account equity, drawdown, daily P/L
/positions  → Current open positions with P/L pips
/status     → Bot mode, consecutive losses, last trade
/news       → Economic calendar (if enabled)
/recommend  → AI trading recommendation (ML + SMC + Macro)
```

---

## Summary

- **Why 15 minutes?** M15 candles are optimal for XAUUSD (balance of noise vs. opportunity)
- **How many times/day?** 96 M15 candles per 24 hours = 96 potential entries/day
- **Analysis depth?** 11-step process (data → features → SMC → regime → ML → filters → entry)
- **Between entries?** Lightweight 5-second checks (price, SL, TP, flash crash, commands)
- **Learning?** 3-layer SL Learning Loop automatically improves after losses
- **Execution?** <50ms latency per iteration (very fast, no delays)

This design maximizes **signal quality** while minimizing **false signals** and **over-trading**.

Check `/recommend` command every hour to see current market alignment! 🚀
