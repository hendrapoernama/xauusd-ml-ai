"""
Dynamic Threshold Calculator
=============================
Calculates ML, SMC, and AI confidence thresholds dynamically based on hourly market analysis.

Adapts thresholds to market conditions:
- High volatility → Lower thresholds (more opportunities)
- Low volatility → Higher thresholds (fewer but higher quality signals)
- High win rate → Lower thresholds (confidence in system)
- Trending market → Lower thresholds (follow the trend)
- Ranging market → Higher thresholds (selective entries)

Analysis factors:
- Market regime (trending, ranging, volatile)
- ATR (volatility measurement)
- Recent win rate (last 50 trades)
- Spread levels
- Session type
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from zoneinfo import ZoneInfo
from loguru import logger
import statistics

WIB = ZoneInfo("Asia/Jakarta")


@dataclass
class DynamicThresholds:
    """Dynamic threshold values."""
    ml_threshold: float          # ML confidence threshold (0.0-1.0)
    smc_threshold: float         # SMC confidence threshold (0.0-1.0)
    ai_quality_threshold: float  # AI quality score threshold (0.0-100)
    confidence: int              # How confident we are in these thresholds (1-100)
    reason: str                  # Why these thresholds were calculated
    timestamp: datetime

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "ml_threshold": self.ml_threshold,
            "smc_threshold": self.smc_threshold,
            "ai_quality_threshold": self.ai_quality_threshold,
            "confidence": self.confidence,
            "reason": self.reason,
            "timestamp": self.timestamp.isoformat(),
        }


class DynamicThresholdCalculator:
    """Calculate dynamic thresholds based on market analysis."""

    def __init__(self):
        self.last_calculation_time: Optional[datetime] = None
        self.last_thresholds: Optional[DynamicThresholds] = None
        self.recalc_interval = timedelta(hours=1)  # Recalculate every hour

    def should_recalculate(self) -> bool:
        """Check if thresholds should be recalculated."""
        if self.last_calculation_time is None:
            return True
        return datetime.now(WIB) - self.last_calculation_time >= self.recalc_interval

    def calculate_thresholds(
        self,
        market_data: Dict,
        recent_trades: List[Dict],
        current_regime: str,
        h1_bias: str,
    ) -> DynamicThresholds:
        """
        Calculate dynamic thresholds based on market analysis.

        Args:
            market_data: Current market data (ATR, spread, volatility)
            recent_trades: Last 50 trades for win rate calculation
            current_regime: Current market regime (trending, ranging, volatile)
            h1_bias: H1 timeframe bias (BULLISH, BEARISH, NEUTRAL)

        Returns:
            DynamicThresholds with calculated values
        """

        # 1. Calculate volatility factor (0.0-1.0)
        vol_factor = self._calculate_volatility_factor(market_data)

        # 2. Calculate performance factor (0.0-1.0)
        perf_factor = self._calculate_performance_factor(recent_trades)

        # 3. Calculate regime factor (0.0-1.0)
        regime_factor = self._calculate_regime_factor(current_regime, h1_bias)

        # 4. Calculate spread penalty
        spread_penalty = self._calculate_spread_penalty(market_data)

        # 5. Combine factors to get thresholds
        thresholds = self._combine_factors(
            vol_factor,
            perf_factor,
            regime_factor,
            spread_penalty,
            current_regime,
            recent_trades,
        )

        self.last_calculation_time = datetime.now(WIB)
        self.last_thresholds = thresholds

        logger.info(
            f"Dynamic thresholds calculated: "
            f"ML={thresholds.ml_threshold:.2%}, "
            f"SMC={thresholds.smc_threshold:.2%}, "
            f"Quality={thresholds.ai_quality_threshold:.0f}"
        )

        return thresholds

    def _calculate_volatility_factor(self, market_data: Dict) -> float:
        """
        Calculate volatility factor (0.0-1.0).
        Higher volatility = higher factor = lower thresholds needed.

        Returns:
            Factor between 0.0 (low vol) and 1.0 (high vol)
        """
        try:
            atr = market_data.get("atr", 0)
            atr_avg = market_data.get("atr_avg", 3)  # Last 20 candles average

            if atr_avg == 0:
                return 0.5  # Neutral if no data

            # Ratio of current ATR to average
            vol_ratio = min(atr / atr_avg, 2.0)  # Cap at 2.0

            # 0.5x-2.0x ATR maps to 0.0-1.0 factor
            factor = (vol_ratio - 0.5) / 1.5  # Normalize to 0-1
            return max(0.0, min(1.0, factor))

        except Exception as e:
            logger.error(f"Error calculating volatility factor: {e}")
            return 0.5  # Default to neutral

    def _calculate_performance_factor(self, recent_trades: List[Dict]) -> float:
        """
        Calculate performance factor based on recent win rate.
        High win rate = higher factor = lower thresholds (confidence in system).

        Returns:
            Factor between 0.0 (poor) and 1.0 (excellent)
        """
        try:
            if not recent_trades or len(recent_trades) < 5:
                return 0.5  # Neutral if insufficient data

            # Get win rate from last 50 trades
            wins = sum(1 for t in recent_trades if t.get("profit", 0) > 0)
            win_rate = wins / len(recent_trades)

            # Map win rate to factor
            # 40% win rate → 0.0 factor
            # 50% win rate → 0.5 factor
            # 70%+ win rate → 1.0 factor
            if win_rate < 0.40:
                factor = 0.0
            elif win_rate < 0.50:
                factor = (win_rate - 0.40) / 0.10  # 0.0-0.5
            else:
                factor = min((win_rate - 0.40) / 0.30, 1.0)  # 0.5-1.0

            return max(0.0, min(1.0, factor))

        except Exception as e:
            logger.error(f"Error calculating performance factor: {e}")
            return 0.5

    def _calculate_regime_factor(self, regime: str, h1_bias: str) -> float:
        """
        Calculate regime factor (0.0-1.0).
        Trending + aligned bias = higher factor = lower thresholds.
        Ranging = neutral factor.

        Returns:
            Factor between 0.0 (conservative) and 1.0 (aggressive)
        """
        try:
            # Base factor from regime
            regime_map = {
                "trending": 0.8,
                "strong_trend": 0.9,
                "medium_volatility": 0.6,
                "ranging": 0.4,
                "low_volatility": 0.3,
                "high_volatility": 0.7,
                "volatile": 0.7,
            }

            base_factor = regime_map.get(regime.lower(), 0.5)

            # Boost if H1 is trending (aligned)
            if h1_bias in ["BULLISH", "BEARISH"]:
                base_factor = min(base_factor + 0.1, 1.0)

            return max(0.0, min(1.0, base_factor))

        except Exception as e:
            logger.error(f"Error calculating regime factor: {e}")
            return 0.5

    def _calculate_spread_penalty(self, market_data: Dict) -> float:
        """
        Calculate spread penalty (0.0-1.0).
        Wide spread = penalty = higher thresholds needed (fewer bad trades).

        Returns:
            Penalty factor (0.0 = no penalty, 0.5 = high penalty)
        """
        try:
            spread = market_data.get("spread", 0.3)

            # Spread ranges
            # <0.3 pips → no penalty
            # 0.3-0.5 pips → small penalty
            # >0.5 pips → significant penalty

            if spread < 0.3:
                penalty = 0.0
            elif spread < 0.5:
                penalty = (spread - 0.3) / 0.2 * 0.2  # 0.0-0.2
            else:
                penalty = min((spread - 0.5) * 0.5, 0.5)  # 0.2-0.5

            return max(0.0, min(0.5, penalty))

        except Exception as e:
            logger.error(f"Error calculating spread penalty: {e}")
            return 0.1  # Default small penalty

    def _combine_factors(
        self,
        vol_factor: float,
        perf_factor: float,
        regime_factor: float,
        spread_penalty: float,
        current_regime: str,
        recent_trades: List[Dict],
    ) -> DynamicThresholds:
        """
        Combine all factors to calculate final thresholds.

        Logic:
        - Higher combined factor = Lower thresholds (more aggressive)
        - Lower combined factor = Higher thresholds (more selective)
        """

        # Weighted combination
        # Regime = 40%, Performance = 35%, Volatility = 25%
        combined_factor = (
            (regime_factor * 0.40) +
            (perf_factor * 0.35) +
            (vol_factor * 0.25)
        ) - spread_penalty

        combined_factor = max(0.0, min(1.0, combined_factor))

        # Calculate win rate for reason
        if recent_trades and len(recent_trades) > 0:
            wins = sum(1 for t in recent_trades if t.get("profit", 0) > 0)
            win_rate = (wins / len(recent_trades)) * 100
        else:
            win_rate = 0

        # Base thresholds
        base_ml = 0.65
        base_smc = 0.65
        base_quality = 65

        # Adjust based on combined factor
        # Factor 0.0 → add +0.15 (more conservative)
        # Factor 0.5 → no change (baseline)
        # Factor 1.0 → subtract -0.10 (more aggressive)
        adjustment = (0.5 - combined_factor) * 0.25

        # Calculate final thresholds
        ml_threshold = max(0.50, min(0.80, base_ml + adjustment))
        smc_threshold = max(0.50, min(0.80, base_smc + adjustment))
        ai_quality = max(40, min(80, base_quality - (adjustment * 100)))

        # Calculate confidence (how sure we are)
        confidence = int(50 + (combined_factor * 50))  # 50-100%

        # Build reason string
        conditions = []
        if "trend" in current_regime.lower():
            conditions.append(f"Trending ({combined_factor:.0%} confidence)")
        if vol_factor > 0.7:
            conditions.append("High volatility opportunity")
        if perf_factor > 0.6:
            conditions.append(f"Strong performance (WR: {win_rate:.0f}%)")
        if spread_penalty > 0.2:
            conditions.append("Wide spread → higher selectivity")

        reason = " | ".join(conditions) if conditions else f"Regime: {current_regime}, Factor: {combined_factor:.0%}"

        return DynamicThresholds(
            ml_threshold=ml_threshold,
            smc_threshold=smc_threshold,
            ai_quality_threshold=ai_quality,
            confidence=confidence,
            reason=reason,
            timestamp=datetime.now(WIB),
        )

    def get_last_thresholds(self) -> Optional[DynamicThresholds]:
        """Get last calculated thresholds."""
        return self.last_thresholds


# Global instance
_calculator: Optional[DynamicThresholdCalculator] = None


def get_dynamic_calculator() -> DynamicThresholdCalculator:
    """Get or create global dynamic threshold calculator."""
    global _calculator
    if _calculator is None:
        _calculator = DynamicThresholdCalculator()
    return _calculator
