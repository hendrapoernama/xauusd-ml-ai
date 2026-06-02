# Trading Analysis Flow — Why Every 15 Minutes?

## Overview

XAUBot AI is a **CANDLE-BASED trading bot**, not time-based. Every 15 minutes corresponds to the **M15 (15-minute) execution timeframe**. Let's analyze the complete flow of what happens during each trading cycle.

---

## Architecture: Two-Phase Loop

### Phase 1: Main Loop (Every ~5 seconds)
```
┌─────────────────────────────────────────┐
│  Main Loop Runs Every 5 Seconds         │
│  (Lightweight candle check)             │
└─────────────┬───────────────────────────┘
              │
              ├─→ Check if NEW M15 candle formed?
              │
              ├─→ YES → Phase 2: Full Trading Iteration
              │
              └─→ NO  → Position Check Only (5-10 second frequency)
```

### Phase 2: Full Trading Iteration (Every M15 = ~15 minutes)
```
When a NEW M15 candle is detected:
┌──────────────────────────────────────────────────┐
│  FULL TRADING ITERATION RUNS                     │
│  (Complete analysis + entry/exit decisions)      │
└──────────────────────────────────────────────────┘
```

---

## Detailed: What Happens Every 15 Minutes?

### Step-by-Step Flow in `_trading_iteration()`

#### **1. MARKET DATA COLLECTION** (0ms)
```python
df = self.mt5.get_market_data(
    symbol="XAUUSD",
    timeframe="M15",
    count=200,  # Last 200 M15 candles = 50 hours of data
)
```
- **Why 200 candles?** — Sufficient history for HMM regime detection, SMC analysis, and feature engineering
- **Why M15?** — Gold volatility is captured best at 15-min granularity; not too noisy (M1) or too slow (H1)

---

#### **2. FEATURE ENGINEERING** (2-5ms)
```python
df = self.features.calculate_all(df, include_ml_features=True)
```
**37 technical features calculated:**
- Momentum: RSI, MACD, Stochastic, Rate of Change
- Volatility: ATR, Bollinger Bands, Standard Deviation, Keltner Channels
- Trend: EMA, SMA, ADX, PSAR
- Volume: OBV, CMF, MFI
- Support/Resistance: Pivot Points, Donchian Bands
- Price Action: High-Low Range, Close-Open Range, Body vs Wick

**Why this many features?**
- XGBoost model trained on these 37 features
- Captures multi-dimensional market conditions
- More features = better predictive power (if not overfitted)

---

#### **3. SMART MONEY CONCEPTS (SMC) ANALYSIS** (1-3ms)
```python
df = self.smc.calculate_all(df)
smc_signal = self.smc.generate_signal(df)
```
**SMC detects:**
- **Order Blocks** — Zones where large orders accumulated
- **Fair Value Gaps (FVG)** — Unfinished buy/sell pressure zones
- **Break of Structure (BOS)** — Trend reversal confirmation
- **Change of Character (CHoCH)** — Market structure shift

**Example signal:**
```
SMC Signal: BUY
- Reason: "FVG fill + BOS on H4 bias"
- Confidence: 78%
```

---

#### **4. MULTI-TIMEFRAME BIAS (H1)** (2-3ms)
```python
h1_bias = self._get_h1_bias()  # Check H1 trend context
```
**Why H1?**
- M15 is prone to noise/false breakouts
- H1 provides "bias direction" — bullish or bearish macro trend
- Reduces false entries by filtering against H1 trend

**Example:**
```
H1 Bias: DOWNTREND
- H1 is trading below 20-EMA
- Even if M15 signals BUY, high risk of reversal
- Apply 15% confidence penalty on BUY signals
```

---

#### **5. HIDDEN MARKOV MODEL (HMM) REGIME DETECTION** (5-10ms)
```python
regime_state = self.regime_detector.predict(df)
# Returns: TRENDING, RANGING, or VOLATILE
```
**Why HMM (not just ADX)?**
- ADX only tells you IF trend exists (0-100 scale)
- HMM tells you **state transitions** (hidden states)
- Can detect regime BEFORE traditional indicators catch it

**3 Market Regimes:**
1. **TRENDING** — Clear direction, low reversal risk
   - Entry: Ride the trend
   - Exit: Regime change OR TP hit
   
2. **RANGING** — Bouncing between support/resistance
   - Entry: Risky! High chance of whipsaw
   - Exit: Quick (strict TP) OR skip this regime
   
3. **VOLATILE** — High volatility, no clear trend
   - Entry: Only with very strong signal (ML >85% + SMC aligned)
   - Exit: ASAP to avoid drawdown

---

#### **6. XGBoost ML PREDICTION** (10-20ms)
```python
ml_prediction = self.ml_model.predict(df, features=37)
# Returns: BUY/SELL/HOLD + confidence 0-100%
```
**XGBoost trained on:**
- 5000+ historical XAUUSD trades (backtest data)
- Features: 37 technical indicators + SMC + Regime
- Labels: 1 (profitable entry), 0 (loss-making entry)

**Output example:**
```
ML Signal: BUY
Confidence: 74%
Buy Probability: 0.74
Sell Probability: 0.26
```

**Why XGBoost?**
- Handles non-linear relationships (e.g., RSI + Regime interaction)
- Robust to outliers (good for sudden news events)
- Interpretable feature importance (know which indicators drive decisions)

---

#### **7. ENTRY FILTERING (11 filters)** (5-15ms)
Even if ML says BUY, must pass ALL these checks:

```
1. ✓ Warmup Done        — At least 3 M15 candles analyzed
2. ✓ Session Filter     — Trading in high-liquidity session (London/NY)
3. ✓ Flash Crash Guard  — No >2% sudden move
4. ✓ Regime Filter      — Skip RANGING regime (optional)
5. ✓ ML Confidence      — Must be >65% (configurable)
6. ✓ SMC Signal         — Must match BUY/SELL direction
7. ✓ Spread Filter      — Bid-Ask spread <5 pips
8. ✓ Cooldown Filter    — Don't re-enter within 15 min
9. ✓ Max Positions      — Don't exceed 5 open positions
10. ✓ Daily Loss Limit   — Don't trade if -3% loss today
11. ✓ Dynamic Confidence — Adjust threshold based on win rate
```

**Example rejection:**
```
BUY signal from ML (75% confidence)
BUT
- Regime = RANGING (low quality)
- Time = 22:45 (off-hours, low liquidity)
Result: FILTERED OUT → NO TRADE
```

---

#### **8. RISK SIZING** (3-5ms)
```python
position_size = risk_engine.calculate_size(
    capital=$5000,
    risk_per_trade=1.5%,
    sl_distance=12 pips,
)
# Returns: 0.01 lots (fixed size based on risk)
```

**Capital-based lot sizing:**
- MICRO (<$500): 2% risk/trade
- SMALL ($500-$10k): 1.5% risk/trade
- MEDIUM ($10k-$100k): 0.5% risk/trade
- LARGE (>$100k): 0.25% risk/trade

**Why percentage-based?** — Protects against catastrophic loss

---

#### **9. ENTRY EXECUTION** (20-50ms)
If all filters PASS:
```python
order = {
    "symbol": "XAUUSD",
    "action": "BUY",
    "volume": 0.01,
    "entry_price": 2550.25,
    "sl": 2538.75,  # 11.5 pips below entry
    "tp": 2562.75,  # 12.5 pips above entry (2:1 RRR)
}
result = mt5.send_order(order)
```

**Order types used:**
- **Limit Order** (usually) — Enter at specific price, wait for fill
- **Market Order** (sometimes) — Immediate fill, might slippage

---

#### **10. POSITION MANAGEMENT (Active monitoring)** (5-10ms)
Once trade is open:

**Smart Position Manager runs EVERY ITERATION checking:**

1. **Trailing Stop Loss** (dynamic)
   - Start trail when profit ≥ $3
   - Trail distance = 15 pips
   - "Lock in" profit as trade moves favorably

2. **Take Profit** (multiple levels)
   - 1/3 position close at 1.5:1 RRR
   - 1/3 position close at 2.0:1 RRR
   - 1/3 position close at 3.0:1 RRR (let winner run)

3. **Maximum Loss** (per position)
   - Hard stop at 20 pips loss
   - No "revenge trading"

4. **Regime-based Exit** (dynamic)
   - If regime changes from TRENDING → RANGING
   - Close with 50% of profit to bank
   - Reduce drawdown risk in choppy market

5. **Time-based Exit** (maximum hold)
   - Close if position open >4 hours
   - Prevent overnight gap risk

**Example flow:**
```
Position entered: BUY @ $2550.00
SL: $2538.50 (hard stop)
TP Levels: $2557.50 (1/3), $2565.00 (1/3), $2572.50 (1/3)

After 10 minutes: Price = $2552.50 (+$2.50 profit)
- Trailing stop activates (profit >$3 threshold)
- Set stop at $2537.50 (15 pips trail)

After 30 minutes: Price = $2557.50 (profit hits TP1)
- Close 1/3 position (lock profit)
- Trail stop on remaining 2/3

After 1 hour: Price drops to $2555.00, trailing stop hits
- Close remaining 2/3 position
- Total session profit: ~$20 on 0.01 lot
```

---

#### **11. SL LEARNING LOOP (Lapis 1-3)** (Async, non-blocking)
If position closed with loss:

**Lapis 1: Detect broker-closed positions**
```python
await self._detect_broker_closed_positions()
# Runs every 10 iterations to log broker SL/TP hits
```

**Lapis 2: Trigger ML retrain if consecutive losses ≥3**
```python
if consecutive_losses >= 3:
    await auto_trainer.trigger_retrain()
    # Retrain XGBoost model with recent losing trades
    # Adjust feature weights to avoid losing conditions
```

**Lapis 3: AI analysis for narrative**
```python
await self.ai_provider.analyze_sl_event(
    entry_price=2550.00,
    sl_price=2538.50,
    exit_price=2536.00,
    profit_usd=-8.00,
    ...
)
# Z.AI/OpenRouter analyzes:
# "Why did this SL hit?"
# "Was it session wrong? Regime unstable? Signal weak?"
# Result sent to Telegram for user review
```

---

#### **12. LOGGING & NOTIFICATIONS** (5-10ms)
```python
self.trade_logger.log_trade_open(ticket=12345, ...)
await self.notifications.notify_trade_open(...)
# Log to PostgreSQL (or CSV fallback)
# Send Telegram: "🟢 BUY #12345 XAUUSD 0.01L @ $2550.25"
```

---

## Timeline: Single M15 Iteration

```
14:15 — M15 Candle CLOSES
│
├─→ (14:15:00) New candle detected → _trading_iteration() starts
│
├─→ (14:15:02) Market data fetched (200 M15 bars)
├─→ (14:15:03) Feature engineering (37 indicators)
├─→ (14:15:04) SMC analysis (order blocks, FVG, BOS)
├─→ (14:15:05) HMM regime detection
├─→ (14:15:06) XGBoost ML prediction
├─→ (14:15:07) Entry filter checks (11 filters)
│
├─→ (14:15:08) DECISION MADE:
│   ├─ Signal = BUY, Confidence = 78%
│   ├─ All filters PASS
│   ├─ → ORDER SENT TO MT5
│   │
│   └─→ (14:15:10) BUY confirmed: #12345 @ $2550.25
│
├─→ (14:15:11) Entry logged to database
├─→ (14:15:12) Telegram notification sent
│
├─→ (14:15:13-14:30:00) POSITION MONITORING
│   ├─ Every 5 seconds: Check price, move trailing SL
│   ├─ Every 5 seconds: Evaluate exit conditions
│   ├─ If TP hit: Close 1/3, trail stop on remainder
│   ├─ If SL hit: Close position, log loss, trigger SL analysis
│   ├─ If regime changes: Consider early exit
│
└─→ (14:30:00) M15 Candle CLOSES again → Next iteration begins

Total iteration time: ~50-100ms (target <50ms for performance)
```

---

## Why M15? (Not M5, H1, or Daily)

| Timeframe | Pros | Cons | Verdict |
|-----------|------|------|--------|
| **M1** | Super fast feedback | Too noisy, whipsaws, high spread slippage | ❌ Too risky |
| **M5** | Responsive | Still too noisy for XAUUSD (commodity volatility) | ❌ Marginal |
| **M15** ✅ | Sweet spot — captures trends, filters noise | Slightly slower feedback | ✅ **OPTIMAL** |
| **H1** | Cleaner signals, less whipsaw | Misses 15-min opportunities, slow exits | ⚠️ Too slow |
| **H4** | Very clean | Too slow for day trading, overnight gaps | ❌ Not for scalping |
| **Daily** | Beautiful trends | Only 1 entry/exit per day, misses intraday swings | ❌ Too slow |

**For XAUUSD specifically:**
- Gold is liquid 24/5, so M15 has excellent data density
- Volatility at M15 is manageable (not spiky like M1)
- News events (economic data) impact is clear at M15 (not buried in M1 noise)
- Session transitions (Sydney → London → NY) are visible at M15

---

## Between Candles (5-second intervals)

While waiting for next M15 candle:

```python
async def _position_check_only(self):
    """Lightweight check every 5 seconds between candles."""
    
    # 1. Get live tick price (cheap call to MT5)
    tick = self.mt5.get_tick(symbol)
    
    # 2. Flash crash detection (uses cached M15 data)
    is_flash, move_pct = self.flash_crash.detect(df_mini)
    if is_flash:
        await self._emergency_close_all()  # Immediate close on crash
        
    # 3. Position management (trailing SL, partial TP)
    # Uses cached ML prediction from last candle (no recalculation)
    await self._evaluate_positions_for_exit()
    
    # 4. Telegram command polling (responsive ~3s latency)
    await self.telegram.poll_commands()
```

**Why not run full analysis every 5 seconds?**
- Too expensive (37 features × 200 candles × 12 times/min = waste)
- Leads to over-trading (changing decisions too frequently)
- Increases latency (slower responses to real trades)

**Instead:** Reuse cached ML prediction + only check price/stops

---

## Dashboard View: What's Happening in Real-Time?

When you check `/status` command:
```
🤖 BOT STATUS

Trading Mode: NORMAL
Warmup Done: ✅ Yes
Consecutive Losses: 0
Daily Loss: $0.00

Open Positions: 2 (#12345, #12346)
Last Trade: 3 min ago
Current Price: $2550.45
Loop Count: 1234 (= 123 full iterations)
```

**Loop Count interpretation:**
- Loop count increments by 1 every M15 candle
- At 10:30 AM, if Loop Count = 1234:
  - = 1234 × 15 min = 18,510 minutes ≈ 12.8 days uptime
  - = Bot has analyzed 1234 M15 candles since startup

---

## Performance Metrics

**Target execution time per iteration:** <50ms

**Typical breakdown:**
- Data fetch: 5-10ms
- Feature calculation: 5-10ms
- SMC analysis: 2-5ms
- Regime detection: 5-10ms
- ML prediction: 10-20ms
- Filtering: 5-10ms
- Risk calculation: 2-3ms
- **Total: 35-68ms** ✓ Within budget

**If iteration >100ms:**
- Likely: MT5 API slow
- Impact: Delayed entry by 1+ M15 candles
- Risk: Miss good entry or late SL adjustment

---

## Summary: Why Every 15 Minutes?

1. **Candle-based**, not time-based
2. **M15 is optimal** for XAUUSD (balances noise vs. opportunity)
3. **Full iteration** only when M15 candle closes (not every 5 seconds)
4. **Between candles:** Lightweight position checks (5-sec frequency)
5. **11-step analysis** including features, SMC, HMM, XGBoost, filtering
6. **SL Learning Loop** automatically improves model after losses
7. **Total latency:** <50ms per iteration (very fast)

This architecture balances:
- ✅ Responsiveness (not missing opportunities)
- ✅ Signal quality (enough data to avoid noise)
- ✅ Computational efficiency (not wasting resources)
- ✅ Risk management (active monitoring between candles)

---

## Next Steps to Optimize

If you observe:
- **Too many false entries** → Increase ML confidence threshold (0.65 → 0.75)
- **Missed opportunities** → Check session filter (might be filtering valid signals)
- **High drawdown** → Review regime filter (maybe RANGING is too strict)
- **Slow exits** → Tighten trailing stop distance (15 → 10 pips)

Monitor `/recommend` command every hour to see current macro sentiment + technical alignment.
