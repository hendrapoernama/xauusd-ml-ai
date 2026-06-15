# DYNAMIC MODE - QUICK START

## 🚀 Activate Now

### Step 1: Enable DYNAMIC Mode
```
Send to Telegram bot: /setmode DYNAMIC
```

Expected response:
```
✅ Trading mode changed: NORMAL → DYNAMIC
```

### Step 2: Verify Activation
```
Send to Telegram bot: /mode_info DYNAMIC
```

Expected output:
```
DYNAMIC ✅ ACTIVE

AI-adaptive mode. Thresholds adjust hourly based on 
market regime, volatility, and recent performance.

Settings:
  • ML Threshold: 65%
  • Max Positions: 4
  • Max Daily Loss: 3.5%
  • Risk/Trade: 1.25%
  • Max Loss/Position: $35
```

---

## 📊 What Happens Now

### Every Hour (4 M15 candles)

1. **Market Analysis**
   - ✅ Measures volatility (ATR)
   - ✅ Detects trend/range/volatile regimes
   - ✅ Calculates win rate
   - ✅ Checks spread width

2. **Threshold Adjustment**
   - ML threshold adjusts from **50% to 80%**
   - Log entry appears: `[DYNAMIC] Thresholds updated: ML=XX%`

3. **Trading Adapts**
   - **High volatility + good performance** → Lower threshold (more trades)
   - **Low volatility + poor performance** → Higher threshold (fewer trades)
   - **Neutral conditions** → Stays near 65% (baseline)

---

## 📈 Example Thresholds You'll See

| Market Condition | ML Threshold | Strategy |
|-----------------|--------------|----------|
| 🟢 Trending up + 60% win rate | **58%** | Be aggressive |
| 🔴 Ranging market + 40% win rate | **72%** | Be selective |
| 🟡 Neutral market + 50% win rate | **65%** | Normal trading |
| 🚀 Perfect trend + 90% win rate | **54%** | Maximum aggression |

---

## 📋 Log Examples

### Startup Log
```
[INFO] Trading mode initialized: DYNAMIC
[INFO] Dynamic Mode Integration initialized
```

### Hourly Update Log (Every 4 candles)
```
[DYNAMIC] Thresholds updated: ML=58% | SMC=58% | Quality=75/100 | Confidence=82%
[DYNAMIC] Reason: Trending (82% confidence) | Strong performance (WR: 65%)
```

### Status Display (Every `/status`)
```
AI Signal
├ ML: HOLD 52% / thresh 58%     ← Current threshold shown!
├ SMC: BUY (63%)
└ Quality: GOOD (score:75)
```

---

## 🎯 Monitoring Commands

### Check Status
```
/status
```
Shows current ML threshold in real-time.

### View Account
```
/balance
```
Shows current threshold in account info section.

### View All Modes
```
/modes
```
See DYNAMIC mode alongside AGGRESSIVE, NORMAL, CONSERVATIVE, etc.

---

## ⚙️ Behind the Scenes

### Calculation Factors (Weighted)
- **Regime Type (40%)** — Trending markets get aggressive, ranging gets conservative
- **Performance (35%)** — Good win rate lowers threshold, bad win rate raises it
- **Volatility (25%)** — High ATR = lower threshold, low ATR = higher threshold
- **Spread Penalty** — Wide spreads increase threshold to reduce noise

### Example Calculation
```
Market conditions:
  - Trending (regime factor: 0.8)
  - 65% win rate (performance factor: 0.8)
  - High volatility (vol factor: 0.8)
  - Tight spread (penalty: 0.0)

Combined Factor = (0.8×0.40 + 0.8×0.35 + 0.8×0.25) - 0.0 = 0.8
→ Adjustment = (0.5 - 0.8) × 0.25 = -0.075
→ Final ML threshold = 0.65 - 0.075 = 57% ✅ AGGRESSIVE
```

---

## 🔄 Update Cycle (M15 Timeframe)

```
Time    | Loop | Event
--------|------|------------------
0:00    | 1    | Start trading
0:15    | 2    | Continue trading
0:30    | 3    | Continue trading
0:45    | 4    | UPDATE THRESHOLDS ← HERE
1:00    | 5    | New thresholds applied
...     | ...  | ...
4:00    | 16   | Continue trading
4:15    | 17   | Continue trading
4:20    | 18   | Auto-retrain check
4:30    | 19   | Continue trading
4:45    | 20   | UPDATE THRESHOLDS + RETRAIN
```

---

## 🎛️ Manual Fallback

If DYNAMIC mode feels too aggressive or conservative:

```
# Switch to fixed mode
/setmode NORMAL        # Back to baseline (65% threshold)
/setmode CONSERVATIVE  # Safe mode (70% threshold)
/setmode AGGRESSIVE    # Offensive mode (60% threshold)
/setmode SCALPING      # Ultra-fast scalps (55% threshold)
```

---

## 📊 Data Saved

### Threshold History
**File:** `data/dynamic_thresholds_history.json`

Saves every threshold update with:
- ML threshold
- SMC threshold
- AI quality score
- Confidence level
- Reason (what caused the change)
- Timestamp

**View it:**
```bash
cat data/dynamic_thresholds_history.json | jq '.'
```

---

## ⚠️ Important Notes

1. **First Hour:** Thresholds may fluctuate while bot gathers data
2. **Stable After:** 2-3 hours of trading, thresholds stabilize
3. **No Manual Intervention Needed:** DYNAMIC mode updates automatically
4. **Non-Blocking:** Threshold updates don't delay trading (happens every 1 hour)
5. **Fallback Available:** Always can switch to NORMAL/AGGRESSIVE if needed

---

## ✅ Checklist

- [ ] Sent `/setmode DYNAMIC` to bot
- [ ] Verified with `/mode_info DYNAMIC`
- [ ] Monitoring threshold changes in logs
- [ ] No errors in `logs/trading_bot_*.log`
- [ ] First hour complete, observing threshold adjustments
- [ ] Comfortable with threshold range (50-80%)

---

## 🆘 Troubleshooting

| Issue | Solution |
|-------|----------|
| Thresholds not updating | Check: `/mode_info DYNAMIC` should show "DYNAMIC ✅ ACTIVE" |
| Updates too frequent | Expected every 1 hour (4 M15 candles) |
| Threshold stuck at 65% | Wait for new candles, check MT5 connection |
| Logs show errors | Check `logs/trading_bot_*.log` for details |
| Want to stop DYNAMIC | `/setmode NORMAL` to revert to fixed mode |

---

## 📞 Support

**Questions about thresholds:**
- Read: `docs/DYNAMIC_MODE_GUIDE.md` (detailed guide)
- Check: Logs for `[DYNAMIC]` messages
- Test: Run `python test_dynamic_mode.py` (verify calculations)

---

## 🎉 Summary

**DYNAMIC Mode is now LIVE!**

- ✅ Thresholds update automatically every hour
- ✅ Adapts to market volatility & performance
- ✅ 100% non-blocking (doesn't slow trading)
- ✅ Can fall back to fixed modes anytime
- ✅ History saved for analysis

**Next steps:**
1. Monitor logs for `[DYNAMIC]` messages
2. Watch threshold changes over 2-3 hours
3. Compare profitability vs NORMAL mode
4. Adjust or keep based on results

---

**Status:** 🟢 Production Ready

Start trading with DYNAMIC mode now! 🚀
