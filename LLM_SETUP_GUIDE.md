# XAUBot AI - LLM Signal Validator Setup Guide

## Overview

Claude LLM integration for signal validation with SMC and ML. Three-phase rollout:
- **Phase 1:** Monitoring & caching (Week 1) - Zero risk
- **Phase 2:** Confidence modifiers (Week 2) - Improve entry quality
- **Phase 3:** Macro-aware validation (Week 3) - Add sentiment context

---

## Quick Start

### Phase 1: Enable Monitoring (Default)

```env
# Copy to .env
LLM_ENABLED=true
LLM_MONITORING_ENABLED=true
LLM_MODIFIER_ENABLED=false
LLM_MACRO_ENABLED=false
```

**What it does:**
- Validates every signal asynchronously after trade execution
- Caches patterns (no API call on repeated patterns)
- Tracks validation accuracy and cache hit rate
- **Zero impact on trading** (async, non-blocking)

**Success criteria:**
- Validation accuracy > 60% → Proceed to Phase 2
- Cache hit rate > 40% → API costs low ($0.01/day)
- Main loop latency <50ms → No performance impact

---

### Phase 2: Apply Modifiers (Week 2)

```env
# Add to Phase 1 settings:
LLM_MODIFIER_ENABLED=true
LLM_MODIFIER_START_RATIO=0.10
```

**What it does:**
- Applies cached LLM insights to future similar signals
- Confidence boost (+0.05 to +0.10) for strong setups
- Confidence penalty (-0.10 to -0.15) for weak setups
- Scales from 10% → 50% → 100% of signals

**Success criteria:**
- Modifier effectiveness > 60% → Continue Phase 2
- Win rate improvement +3-5% → Target 60-65%
- Confidence calibration ±5% → Modifiers well-tuned

---

### Phase 3: Macro-Aware (Week 3)

```env
# Add to Phase 1+2 settings:
LLM_MACRO_ENABLED=true
```

**What it does:**
- Adds Fed sentiment, economic news, events to validation
- Macro-aware confidence modifiers
- Better signal validation in news-heavy periods

**Success criteria:**
- Win rate improvement +5-10% cumulative → Target 65-70%+
- Profit factor > 1.5 → Sustainable profitability
- Stable across sessions → Ready for production

---

## Environment Variables Reference

### Phase Control

```env
# Master enable/disable (true/false)
LLM_ENABLED=true

# Phase 1: Monitoring & caching
LLM_MONITORING_ENABLED=true

# Phase 2: Apply confidence modifiers
LLM_MODIFIER_ENABLED=false

# Phase 3: Add macro sentiment
LLM_MACRO_ENABLED=false
```

### Integration with SMC & ML

```env
# Include SMC patterns in validation
LLM_WITH_SMC=true

# Include ML predictions in validation
LLM_WITH_ML=true
```

### Caching

```env
# Cache duration (minutes) - same patterns reuse cached result
LLM_CACHE_DURATION_MIN=30

# Max cache entries before cleanup
LLM_CACHE_MAX_ENTRIES=1000
```

### Confidence Modifiers (Phase 2+)

```env
# Penalty for poor setups (range: -0.20 to -0.05)
LLM_MODIFIER_MIN=-0.15

# Boost for strong setups (range: +0.05 to +0.20)
LLM_MODIFIER_MAX=0.10

# Start ratio (10% → 100% of signals)
LLM_MODIFIER_START_RATIO=0.10
```

### Thresholds

```env
# Min accuracy to proceed Phase 1→2 (0.50-0.70)
LLM_ACCURACY_THRESHOLD=0.60

# Min effectiveness to keep Phase 2 (0.50-0.70)
LLM_EFFECTIVENESS_THRESHOLD=0.60

# Target cache hit rate (informational)
LLM_CACHE_HIT_RATE_TARGET=0.40
```

### API & Cost Control

```env
# API timeout in seconds (2-10)
LLM_API_TIMEOUT_SEC=5

# Daily cost limit in USD
LLM_DAILY_COST_LIMIT=1.0
```

### Logging

```env
# Log every validation call (true/false)
LLM_LOG_ALL_VALIDATIONS=true
```

---

## Monitoring & Metrics

### Phase 1 Metrics

Track in bot logs and `bot_status.json`:

```
Signal Validation Rate: Should be 100%
Cache Hit Rate: Should reach 40%+ after 50 signals
Validation Accuracy: Must exceed 60%
Daily API Cost: Should be < $0.01
Main Loop Latency: Should stay < 50ms
```

### Phase 2 Metrics

```
Modifier Applied Ratio: 10% → 50% → 100%
Modifier Effectiveness: Must exceed 60%
Win Rate Improvement: Target +3-5%
Confidence Calibration: ±5% accurate
```

### Phase 3 Metrics

```
Macro Sentiment Accuracy: Improves signal quality
Macro-Aligned Win Rate: Should be > 70%
Cumulative Win Rate: Target 65-70%+
Profit Factor: Target > 1.5
```

---

## Troubleshooting

### LLM Not Working

**Check:**
```bash
# See LLM initialization in logs
grep -i "LLM VALIDATOR" logs/*.log

# Verify environment variables
echo $LLM_ENABLED
echo $LLM_WITH_SMC
echo $LLM_WITH_ML
```

**Common issues:**

1. **API timeouts** → Increase `LLM_API_TIMEOUT_SEC`
2. **High costs** → Check cache hit rate, reduce `LLM_MODIFIER_START_RATIO`
3. **Low accuracy** → Adjust `LLM_ACCURACY_THRESHOLD` or debug SMC/ML signals
4. **Modifier not helping** → Disable `LLM_MODIFIER_ENABLED`, stay in Phase 1

---

## Rollback Procedure

### Emergency Disable (Phase 1→ SMC+ML)

```env
# Disables all LLM validation
LLM_ENABLED=false
```

**Result:** Bot falls back to pure SMC+ML signals. Zero risk.

### Phase 2 Rollback (Modifiers→ Monitoring)

```env
# Keeps monitoring, disables modifier application
LLM_MODIFIER_ENABLED=false
```

**Result:** Returns to Phase 1 (monitoring-only).

### Phase 3 Rollback (Macro→ Modifiers)

```env
# Removes macro sentiment, keeps modifiers
LLM_MACRO_ENABLED=false
```

**Result:** Returns to Phase 2 (pattern-based modifiers).

---

## Cost Analysis

### Expected Costs

| Phase | Signals/Day | Cache Hit % | API Calls/Day | Daily Cost |
|-------|-------------|------------|---------------|-----------|
| Phase 1 | 50-100 | 40% | 30-60 | <$0.01 |
| Phase 2 | 50-100 | 40% | 30-60 | <$0.01 |
| Phase 3 | 50-100 | 40% | 30-60 | <$0.02 |

**Formula:**
- API call cost: ~$0.0003 (Claude Haiku)
- 50 calls/day = ~$0.015/day
- **Monthly: ~$0.45** (negligible)

**ROI if +5% win rate:**
- Monthly trades: ~1,200 (50/day × 24 days)
- Extra profit per 1% WR improvement: ~$500/month
- **ROI: 1000x+**

---

## Examples

### Example 1: Safe Phase 1 Rollout

```env
# .env configuration
LLM_ENABLED=true
LLM_MONITORING_ENABLED=true
LLM_MODIFIER_ENABLED=false
LLM_MACRO_ENABLED=false
LLM_WITH_SMC=true
LLM_WITH_ML=true
LLM_CACHE_DURATION_MIN=30
LLM_ACCURACY_THRESHOLD=0.60
```

**Timeline:**
- Week 1: Run Phase 1, monitor metrics
- If accuracy > 60%: Enable Phase 2

### Example 2: Progressive Phase 2

```env
# Week 2 - Start small
LLM_MODIFIER_ENABLED=true
LLM_MODIFIER_START_RATIO=0.10

# After 5 trades - if effectiveness > 60%
LLM_MODIFIER_START_RATIO=0.50

# After 20 trades - if still effective
LLM_MODIFIER_START_RATIO=1.00
```

### Example 3: Disabled (Fallback)

```env
# Emergency disable - revert to SMC+ML
LLM_ENABLED=false
```

Result: No LLM validation, pure SMC+ML signals.

---

## FAQ

### Q: Will LLM block my trades?
**A:** No. Phase 1-3 validation runs **asynchronously after** order execution. Zero latency impact.

### Q: How much does it cost?
**A:** ~$0.01-0.02/day (40% cache hit rate). ROI is 1000x+ if +5% win rate.

### Q: Can I disable it?
**A:** Yes. Set `LLM_ENABLED=false` in `.env`. Falls back to SMC+ML instantly.

### Q: What if accuracy is low?
**A:** Stay in Phase 1 (monitoring). Adjust thresholds or debug SMC/ML signals.

### Q: Can I skip Phase 1?
**A:** Not recommended. Phase 1 validates the LLM accuracy before Phase 2 modifiers apply.

### Q: How long to reach Phase 3?
**A:** 3 weeks (1 week per phase). Each phase has success gates before proceeding.

---

## Next Steps

1. **Copy `.env.llm.example` settings to `.env`**
2. **Start bot with Phase 1 defaults**
3. **Monitor metrics for 1 week**
4. **If accuracy > 60%: Enable Phase 2**
5. **If effectiveness > 60%: Enable Phase 3**

---

## Support

See `/docs` for additional documentation:
- `TRADING_OPTIMIZATION_STRATEGY.md` - Full optimization plan
- `IMPLEMENTATION_PLAN.md` - Step-by-step guide
- `.env.llm.example` - All configuration options with examples
