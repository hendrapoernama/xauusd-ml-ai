# DYNAMIC Mode - Adaptive Trading Guide

## Overview

**DYNAMIC mode** adalah mode trading yang adaptif dimana threshold ML, SMC, dan AI quality **otomatis menyesuaikan setiap jam** berdasarkan analisis pasar real-time.

Threshold diubah-ubah untuk optimal dengan kondisi pasar:
- **High volatility** → Lower thresholds (lebih banyak opportunities)
- **Low volatility** → Higher thresholds (lebih selective)
- **Trending market** → Aggressive thresholds (follow trend)
- **Ranging market** → Conservative thresholds (wait for setup)
- **Good performance** → Lower thresholds (confidence boost)
- **Poor performance** → Higher thresholds (protection mode)

---

## Architecture

### Components

1. **DynamicThresholdCalculator** (`src/dynamic_threshold_calculator.py`)
   - Analyzes market conditions
   - Calculates optimal thresholds
   - Updates every hour

2. **DynamicModeIntegration** (`src/dynamic_mode_integration.py`)
   - Integrates calculator into main loop
   - Fetches recent trade data
   - Saves history for analysis

3. **TradingModeManager** (`src/trading_modes.py`)
   - Manages DYNAMIC mode config
   - Applies dynamic thresholds
   - Tracks mode history

---

## How It Works

### Calculation Factors

Dynamic thresholds are calculated from 4 main factors:

#### 1. **Volatility Factor (25% weight)**
```
Current ATR / Average ATR = Volatility Ratio
- 0.5x ATR → Factor 0.0 (low vol)
- 1.0x ATR → Factor 0.5 (normal)
- 2.0x ATR → Factor 1.0 (high vol)
```

#### 2. **Performance Factor (35% weight)**
```
Recent Win Rate from last 50 trades
- <40% → Factor 0.0 (avoid trading)
- 50% → Factor 0.5 (neutral)
- 70%+ → Factor 1.0 (aggressive)
```

#### 3. **Regime Factor (40% weight)**
```
Market regime + H1 bias alignment
- Low volatility + ranging → Factor 0.3
- Medium volatility + medium trend → Factor 0.6
- Strong trend + high volatility → Factor 0.9
- Trending + H1 aligned → +0.1 boost
```

#### 4. **Spread Penalty (0-0.5)**
```
Wide spread = higher penalty = higher thresholds needed
- <0.3 pips → Penalty 0.0
- 0.3-0.5 pips → Penalty 0.1-0.2
- >0.5 pips → Penalty up to 0.5
```

### Final Threshold Calculation

```
Combined Factor = (Regime×0.40 + Perf×0.35 + Vol×0.25) - SpreadPenalty

Adjustment = (0.5 - CombinedFactor) × 0.25

Final ML Threshold = 0.65 + Adjustment (clamped 0.50-0.80)
Final SMC Threshold = 0.65 + Adjustment (clamped 0.50-0.80)
Final Quality Score = 65 - (Adjustment×100) (clamped 40-80)

Confidence = 50% + (CombinedFactor × 50%) → range 50-100%
```

---

## Configuration

### DYNAMIC Mode Defaults
```python
DYNAMIC Mode:
├ ML Threshold: 0.65 (dynamically adjusted)
├ SMC Threshold: 0.65 (dynamically adjusted)
├ Max Positions: 4
├ Risk/Trade: 1.25%
├ Daily Loss Limit: 3.5%
└ Max Loss/Position: $35
```

---

## Integration in main_live.py

### 1. Import
```python
from src.dynamic_mode_integration import DynamicModeIntegration
from src.trading_modes import get_trading_mode_manager

# Initialize
mode_manager = get_trading_mode_manager()
dynamic_mode = DynamicModeIntegration(mode_manager, data_dir="data")
```

### 2. In Main Loop
```python
async def main_loop():
    # ... existing code ...
    
    # Every iteration, check if DYNAMIC mode needs threshold update
    if dynamic_mode.should_update():
        thresholds = await dynamic_mode.update_thresholds(
            market_data={
                "atr": current_atr,
                "spread": current_spread,
                "volatility": current_volatility,
            },
            atr_values=recent_atr_values,  # Last 20 candles
            regime=current_regime,           # From regime_detector
            h1_bias=h1_bias,                # From SMC analysis
            db=db_connection,               # Optional: for recent trades
        )
        
        if thresholds:
            logger.info(f"Dynamic thresholds updated: {thresholds.reason}")
```

### 3. Use Updated Thresholds
```python
# The threshold is automatically applied via TradingModeManager
mode_config = mode_manager.get_mode_config()
ml_threshold = mode_config.ml_threshold  # Already updated!
```

---

## Telegram Commands

### Activate DYNAMIC Mode
```
/setmode DYNAMIC
```

### View Current Thresholds
```
/mode_info DYNAMIC
```

Output:
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

### View Detailed Threshold Analysis
Create a Telegram command handler:
```python
@dp.message_handler(commands=['dynamic_info'])
async def cmd_dynamic_info(message: Message):
    thresholds = dynamic_mode.get_current_thresholds()
    msg = dynamic_mode.format_for_telegram(thresholds)
    await message.answer(msg, parse_mode='HTML')
```

Output:
```
🔄 DYNAMIC MODE - CURRENT THRESHOLDS

Adaptive Thresholds:
  • ML: 62%
  • SMC: 63%
  • AI Quality: 68/100

Confidence: 75%

Reason: Trending (75% confidence) | Strong performance (WR: 58%)

Updated: 15:30:42 WIB
Next update: Hourly
```

---

## Example Scenarios

### Scenario 1: High Volatility Period
```
Market Conditions:
├ Regime: High Volatility (ATR 1.8x normal)
├ Win Rate: 55%
├ Spread: 0.28 pips
└ H1 Bias: BULLISH

Calculation:
├ Vol Factor: 0.85 (high volatility)
├ Perf Factor: 0.65 (moderate win rate)
├ Regime Factor: 0.75 (trending up)
├ Spread Penalty: 0.0
└ Combined: 0.73 → Very Aggressive

Result Thresholds:
├ ML: 57% ↓ (from 65%)
├ SMC: 57% ↓ (from 65%)
├ Quality: 78/100
└ Confidence: 87%

Strategy: Enter more trades, lower quality bar
```

### Scenario 2: Low Volatility with Poor Performance
```
Market Conditions:
├ Regime: Low Volatility (ATR 0.4x normal)
├ Win Rate: 42%
├ Spread: 0.48 pips
└ H1 Bias: NEUTRAL

Calculation:
├ Vol Factor: 0.2 (low volatility)
├ Perf Factor: 0.1 (poor performance)
├ Regime Factor: 0.35 (ranging)
├ Spread Penalty: 0.15
└ Combined: 0.28 → Very Conservative

Result Thresholds:
├ ML: 74% ↑ (from 65%)
├ SMC: 74% ↑ (from 65%)
├ Quality: 53/100
└ Confidence: 52%

Strategy: Skip trades, wait for better setup
```

### Scenario 3: Trending Market with Good Performance
```
Market Conditions:
├ Regime: Strong Trend
├ Win Rate: 68%
├ Spread: 0.32 pips
└ H1 Bias: BEARISH

Calculation:
├ Vol Factor: 0.65 (medium-high)
├ Perf Factor: 0.95 (excellent performance)
├ Regime Factor: 0.95 (strong trend + aligned)
├ Spread Penalty: 0.05
└ Combined: 0.85 → Maximum Aggressive

Result Thresholds:
├ ML: 54% ↓↓ (from 65%)
├ SMC: 54% ↓↓ (from 65%)
├ Quality: 64/100
└ Confidence: 93%

Strategy: Trade aggressively with trend
```

---

## Threshold History

All threshold calculations are saved to `data/dynamic_thresholds_history.json`:

```json
{
  "2026-06-16T15:30:42.123456+07:00": {
    "ml_threshold": 0.62,
    "smc_threshold": 0.63,
    "ai_quality_threshold": 68,
    "confidence": 75,
    "reason": "Trending (75% confidence) | Strong performance (WR: 58%)",
    "timestamp": "2026-06-16T15:30:42.123456+07:00"
  },
  ...
}
```

Query history:
```python
# Get last 24 hours of threshold changes
history = dynamic_mode.get_threshold_history(hours=24)
for timestamp, data in history.items():
    print(f"{timestamp}: ML={data['ml_threshold']:.0%}, Confidence={data['confidence']}%")
```

---

## Best Practices

### 1. Start with DYNAMIC Mode
```python
# In initialization
mode_manager.set_mode("DYNAMIC")
```

### 2. Monitor Threshold Changes
- Check Telegram logs for threshold updates
- Review history weekly
- Adjust base parameters if needed

### 3. Fallback to Fixed Modes
If DYNAMIC performs poorly:
```python
# Switch to NORMAL mode
/setmode NORMAL

# Or CONSERVATIVE if system is losing
/setmode CONSERVATIVE
```

### 4. Combine with Manual Override
Allow Telegram command to force thresholds:
```python
@dp.message_handler(commands=['override_threshold'])
async def cmd_override(message: Message, args):
    ml = float(args[0])
    smc = float(args[1])
    # Update manually
```

### 5. Regular Performance Review
Check weekly:
- How often thresholds change
- Which factors drive most changes
- Whether mode is profitable long-term

---

## Troubleshooting

### Problem: Thresholds not updating
**Solution:**
1. Check mode: `/mode_info DYNAMIC`
2. Verify calculator interval: Check `recalc_interval` in code
3. Check logs: `tail -f logs/xaubot.log | grep Dynamic`

### Problem: Thresholds too aggressive
**Solution:**
1. Increase base thresholds in `_combine_factors()`
2. Lower volatility factor weight
3. Switch to NORMAL mode temporarily

### Problem: Too many false signals
**Solution:**
1. Increase AI quality threshold
2. Lower volatility factor
3. Require stronger regime confirmation

---

## Monitoring Dashboard

Add to your Telegram bot dashboard:

```python
async def get_dynamic_dashboard() -> str:
    thresholds = dynamic_mode.get_current_thresholds()
    history = dynamic_mode.get_threshold_history(hours=1)
    
    return f"""
<b>DYNAMIC MODE DASHBOARD</b>

Current:
{dynamic_mode.format_for_telegram(thresholds)}

1h Change:
  ML: {old_ml:.0%} → {thresholds.ml_threshold:.0%}
  SMC: {old_smc:.0%} → {thresholds.smc_threshold:.0%}
"""
```

---

## Advanced: Customizing Calculation

Edit `src/dynamic_threshold_calculator.py`:

### Change Weights
```python
# In _combine_factors()
combined_factor = (
    (regime_factor * 0.50) +    # ← Increase
    (perf_factor * 0.30) +      # ← Decrease
    (vol_factor * 0.20)         # ← Decrease
)
```

### Add New Factor
```python
def _calculate_custom_factor(self, data: Dict) -> float:
    # Your logic
    return factor

# In calculate_thresholds():
custom_factor = self._calculate_custom_factor(market_data)

# In _combine_factors():
combined_factor = (
    ... existing weights ...
    + (custom_factor * 0.15)  # ← Add new factor
)
```

---

## References

- `src/dynamic_threshold_calculator.py` — Core calculation engine
- `src/dynamic_mode_integration.py` — Integration with main loop
- `src/trading_modes.py` — Mode management
- `data/dynamic_thresholds_history.json` — Historical data

