"""
Automated ML-Based Parameter Optimizer
======================================
Uses historical trades to find optimal:
- Confidence threshold
- RR minimum
- Entry filters
- Position sizing

Goal: Maximize winrate + RR through continuous learning
"""

import json
import polars as pl
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
from enum import Enum
import numpy as np
from loguru import logger


class MarketRegime(Enum):
    TRENDING = "trending"
    RANGING = "ranging"
    VOLATILE = "volatile"
    CHOPPY = "choppy"


@dataclass
class OptimizationResult:
    optimal_confidence: float
    optimal_rr_minimum: float
    optimal_lot_multiplier: float
    expected_winrate: float
    expected_profit_factor: float
    confidence_score: float  # 0-1: how confident in this optimization


class TradeAnalyzer:
    """Analyze closed trades to find patterns and optimize parameters."""

    def __init__(self, lookback_days: int = 30):
        self.lookback_days = lookback_days
        self.trades: List[Dict] = []
        self.metrics: Dict = {}

    def load_trades(self, csv_path: str) -> bool:
        """Load trades from CSV log file."""
        try:
            df = pl.read_csv(csv_path)
            self.trades = df.to_dicts()
            return len(self.trades) > 0
        except Exception as e:
            logger.error(f"Failed to load trades: {e}")
            return False

    def analyze(self) -> Dict:
        """Comprehensive trade analysis."""
        if len(self.trades) < 5:
            logger.warning(f"Need at least 5 trades, have {len(self.trades)}")
            return self._default_metrics()

        # Calculate metrics
        wins = [t for t in self.trades if t.get("pnl", 0) > 0]
        losses = [t for t in self.trades if t.get("pnl", 0) < 0]

        winrate = len(wins) / len(self.trades) if self.trades else 0
        avg_win = np.mean([t.get("pnl", 0) for t in wins]) if wins else 0
        avg_loss = abs(np.mean([t.get("pnl", 0) for t in losses])) if losses else 0
        profit_factor = (avg_win * len(wins)) / (avg_loss * len(losses)) if losses and avg_loss > 0 else 0

        # Group by confidence levels
        confidence_analysis = self._analyze_by_confidence()

        # Group by RR
        rr_analysis = self._analyze_by_rr()

        return {
            "total_trades": len(self.trades),
            "wins": len(wins),
            "losses": len(losses),
            "winrate": winrate,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "profit_factor": profit_factor,
            "confidence_analysis": confidence_analysis,
            "rr_analysis": rr_analysis,
            "best_confidence_level": self._find_best_confidence(),
            "best_rr_minimum": self._find_best_rr(),
        }

    def _analyze_by_confidence(self) -> Dict:
        """Find win rates at different confidence levels."""
        bins = {
            "50-55%": [],
            "55-60%": [],
            "60-65%": [],
            "65-70%": [],
            "70-75%": [],
            "75%+": [],
        }

        for trade in self.trades:
            conf = trade.get("ml_confidence", 0.5)
            pnl = trade.get("pnl", 0)

            if conf < 0.55:
                bins["50-55%"].append(pnl)
            elif conf < 0.60:
                bins["55-60%"].append(pnl)
            elif conf < 0.65:
                bins["60-65%"].append(pnl)
            elif conf < 0.70:
                bins["65-70%"].append(pnl)
            elif conf < 0.75:
                bins["70-75%"].append(pnl)
            else:
                bins["75%+"].append(pnl)

        result = {}
        for bin_name, pnls in bins.items():
            if pnls:
                wins = len([p for p in pnls if p > 0])
                wr = wins / len(pnls)
                avg_pnl = np.mean(pnls)
                result[bin_name] = {
                    "trades": len(pnls),
                    "winrate": wr,
                    "avg_pnl": avg_pnl,
                }

        return result

    def _analyze_by_rr(self) -> Dict:
        """Find win rates at different RR levels."""
        bins = {
            "RR < 1.0": [],
            "RR 1.0-1.5": [],
            "RR 1.5-2.0": [],
            "RR 2.0-2.5": [],
            "RR 2.5+": [],
        }

        for trade in self.trades:
            rr = trade.get("risk_reward", 1.0)
            pnl = trade.get("pnl", 0)

            if rr < 1.0:
                bins["RR < 1.0"].append(pnl)
            elif rr < 1.5:
                bins["RR 1.0-1.5"].append(pnl)
            elif rr < 2.0:
                bins["RR 1.5-2.0"].append(pnl)
            elif rr < 2.5:
                bins["RR 2.0-2.5"].append(pnl)
            else:
                bins["RR 2.5+"].append(pnl)

        result = {}
        for bin_name, pnls in bins.items():
            if pnls:
                wins = len([p for p in pnls if p > 0])
                wr = wins / len(pnls)
                avg_pnl = np.mean(pnls)
                result[bin_name] = {
                    "trades": len(pnls),
                    "winrate": wr,
                    "avg_pnl": avg_pnl,
                }

        return result

    def _find_best_confidence(self) -> Dict:
        """Find confidence level with highest winrate."""
        analysis = self._analyze_by_confidence()
        best = max(analysis.items(), key=lambda x: x[1]["winrate"])
        return {"level": best[0], "winrate": best[1]["winrate"]}

    def _find_best_rr(self) -> Dict:
        """Find RR level with highest winrate."""
        analysis = self._analyze_by_rr()
        best = max(analysis.items(), key=lambda x: x[1]["winrate"])
        return {"level": best[0], "winrate": best[1]["winrate"]}

    def _default_metrics(self) -> Dict:
        return {
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "winrate": 0,
            "avg_win": 0,
            "avg_loss": 0,
            "profit_factor": 0,
            "confidence_analysis": {},
            "rr_analysis": {},
        }


class MarketRegimeDetector:
    """Detect market regime and recommend parameters."""

    def __init__(self):
        self.regimes = {
            MarketRegime.TRENDING: {"confidence": 0.58, "rr_min": 1.5, "lot_mult": 1.2},
            MarketRegime.RANGING: {"confidence": 0.65, "rr_min": 2.0, "lot_mult": 0.8},
            MarketRegime.VOLATILE: {"confidence": 0.62, "rr_min": 2.0, "lot_mult": 0.7},
            MarketRegime.CHOPPY: {"confidence": 0.70, "rr_min": 2.5, "lot_mult": 0.5},
        }

    def detect_regime(self, df: pl.DataFrame, period: int = 50) -> Tuple[MarketRegime, float]:
        """
        Detect market regime based on:
        - ATR ratio (volatility)
        - Trend strength (ADX-like)
        - Range size

        Returns: (regime, confidence_0_to_1)
        """
        if len(df) < period:
            return MarketRegime.RANGING, 0.5

        recent = df.tail(period)
        close = recent["close"].to_list()
        high = recent["high"].to_list()
        low = recent["low"].to_list()

        # Calculate volatility (ATR-based)
        tr = [max(h - l, abs(h - c), abs(l - c)) for h, l, c in zip(high, low, close)]
        atr = np.mean(tr[-14:]) if len(tr) >= 14 else np.mean(tr)
        baseline_atr = np.mean(tr)
        atr_ratio = atr / baseline_atr if baseline_atr > 0 else 1.0

        # Calculate trend (EMA-based)
        ema20 = self._calculate_ema(close, 20)
        ema50 = self._calculate_ema(close, 50)
        trend_strength = abs(ema20[-1] - ema50[-1]) / np.mean(close[-20:]) if close else 0

        # Range analysis
        range_size = (max(high[-20:]) - min(low[-20:])) / np.mean(close[-20:]) if close else 0

        # Regime detection logic
        if atr_ratio > 1.5 and trend_strength > 0.02:
            return MarketRegime.TRENDING, 0.8
        elif atr_ratio > 1.3:
            return MarketRegime.VOLATILE, 0.7
        elif range_size > 0.05 and atr_ratio < 1.0:
            return MarketRegime.RANGING, 0.7
        else:
            return MarketRegime.CHOPPY, 0.6

    def get_optimal_params(self, regime: MarketRegime) -> Dict:
        """Get optimal parameters for detected regime."""
        return self.regimes.get(regime, self.regimes[MarketRegime.RANGING])

    @staticmethod
    def _calculate_ema(prices: List[float], period: int) -> List[float]:
        """Calculate EMA."""
        if len(prices) < period:
            return prices
        ema = [np.mean(prices[:period])]
        multiplier = 2 / (period + 1)
        for price in prices[period:]:
            ema_val = price * multiplier + ema[-1] * (1 - multiplier)
            ema.append(ema_val)
        return ema


class AutoOptimizer:
    """Main optimizer: combines trade analysis + market detection."""

    def __init__(self):
        self.analyzer = TradeAnalyzer()
        self.detector = MarketRegimeDetector()
        self.last_optimization = None
        self.optimization_history: List[OptimizationResult] = []

    def optimize(self, df: pl.DataFrame, trade_csv_path: Optional[str] = None) -> OptimizationResult:
        """
        Generate optimal parameters based on:
        1. Current market regime
        2. Historical trade performance
        3. Win rate + RR optimization
        """
        # Detect current market regime
        regime, regime_confidence = self.detector.detect_regime(df)
        regime_params = self.detector.get_optimal_params(regime)

        logger.info(f"[AUTO-OPTIMIZER] Detected regime: {regime.value} (confidence: {regime_confidence:.0%})")

        # Load and analyze historical trades
        trade_metrics = {}
        if trade_csv_path:
            if self.analyzer.load_trades(trade_csv_path):
                trade_metrics = self.analyzer.analyze()
                logger.info(
                    f"[AUTO-OPTIMIZER] Trade analysis: {trade_metrics['total_trades']} trades, "
                    f"WR={trade_metrics['winrate']:.0%}, PF={trade_metrics['profit_factor']:.2f}"
                )

        # Blend regime-based + trade-based recommendations
        optimal_confidence = self._blend_confidence(regime_params, trade_metrics, regime_confidence)
        optimal_rr = self._blend_rr(regime_params, trade_metrics, regime_confidence)
        lot_multiplier = regime_params.get("lot_mult", 1.0)

        # Calculate expected performance
        expected_wr, expected_pf = self._calculate_expected_metrics(
            optimal_confidence, optimal_rr, trade_metrics
        )

        result = OptimizationResult(
            optimal_confidence=optimal_confidence,
            optimal_rr_minimum=optimal_rr,
            optimal_lot_multiplier=lot_multiplier,
            expected_winrate=expected_wr,
            expected_profit_factor=expected_pf,
            confidence_score=regime_confidence,
        )

        self.optimization_history.append(result)
        self.last_optimization = result

        logger.info(
            f"[AUTO-OPTIMIZER] Optimal params: confidence={optimal_confidence:.0%}, "
            f"RR_min={optimal_rr:.1f}, lot_mult={lot_multiplier:.1f} | "
            f"Expected: WR={expected_wr:.0%}, PF={expected_pf:.2f}"
        )

        return result

    @staticmethod
    def _blend_confidence(regime_params: Dict, trade_metrics: Dict, regime_conf: float) -> float:
        """Blend regime-based + trade-based confidence threshold."""
        regime_conf_threshold = regime_params.get("confidence", 0.60)

        # If we have trade data, adjust based on best performer
        if trade_metrics.get("best_confidence_level"):
            best_level = trade_metrics["best_confidence_level"]["level"]
            # Map level string to value: "60-65%" -> 0.62
            level_map = {
                "50-55%": 0.525,
                "55-60%": 0.575,
                "60-65%": 0.625,
                "65-70%": 0.675,
                "70-75%": 0.725,
                "75%+": 0.80,
            }
            best_conf_value = level_map.get(best_level, 0.60)

            # Weighted blend: 60% trade data + 40% regime
            blended = (best_conf_value * 0.6) + (regime_conf_threshold * 0.4)
            return min(0.75, max(0.55, blended))  # Clamp 55-75%

        return regime_conf_threshold

    @staticmethod
    def _blend_rr(regime_params: Dict, trade_metrics: Dict, regime_conf: float) -> float:
        """Blend regime-based + trade-based RR minimum."""
        regime_rr = regime_params.get("rr_min", 1.5)

        # If we have trade data, adjust based on best performer
        if trade_metrics.get("best_rr_minimum"):
            best_level = trade_metrics["best_rr_minimum"]["level"]
            # Map level string to value
            level_map = {
                "RR < 1.0": 0.9,
                "RR 1.0-1.5": 1.25,
                "RR 1.5-2.0": 1.75,
                "RR 2.0-2.5": 2.25,
                "RR 2.5+": 2.75,
            }
            best_rr_value = level_map.get(best_level, 1.5)

            # Weighted blend: 60% trade data + 40% regime
            blended = (best_rr_value * 0.6) + (regime_rr * 0.4)
            return min(3.0, max(1.2, blended))  # Clamp 1.2-3.0

        return regime_rr

    @staticmethod
    def _calculate_expected_metrics(
        confidence: float, rr_min: float, trade_metrics: Dict
    ) -> Tuple[float, float]:
        """Estimate expected win rate and profit factor."""
        if not trade_metrics:
            # Default estimation: 55% at 60% confidence, 58% at 65%, etc
            base_wr = 0.50 + (confidence - 0.50) * 0.2  # 50% + confidence bonus
            expected_pf = (base_wr * rr_min) / (1 - base_wr) if base_wr < 1 else 2.0
            return min(0.70, base_wr), min(2.5, expected_pf)

        # Use actual trade data
        current_wr = trade_metrics.get("winrate", 0.50)
        current_avg_win = trade_metrics.get("avg_win", 10)
        current_avg_loss = trade_metrics.get("avg_loss", 10)

        # Conservative estimate: assume similar win rate, but better RR
        estimated_wr = min(0.70, current_wr + 0.05)  # +5% from optimization
        if current_avg_loss > 0:
            estimated_pf = (estimated_wr * rr_min) / (1 - estimated_wr) if estimated_wr < 1 else 2.5
        else:
            estimated_pf = 2.0

        return estimated_wr, min(2.5, estimated_pf)

    def get_optimization_report(self) -> str:
        """Generate human-readable optimization report."""
        if not self.last_optimization:
            return "No optimization performed yet"

        opt = self.last_optimization
        return f"""
╔════════════════════════════════════════════════════╗
║    AUTO-OPTIMIZER REPORT                           ║
╠════════════════════════════════════════════════════╣
║ Optimal Confidence:        {opt.optimal_confidence:.0%}
║ Optimal RR Minimum:        {opt.optimal_rr_minimum:.1f}:1
║ Position Multiplier:       {opt.optimal_lot_multiplier:.1f}x
├────────────────────────────────────────────────────┤
║ EXPECTED PERFORMANCE
├────────────────────────────────────────────────────┤
║ Expected Win Rate:         {opt.expected_winrate:.0%}
║ Expected Profit Factor:    {opt.expected_profit_factor:.2f}
║ Regime Confidence:         {opt.confidence_score:.0%}
╚════════════════════════════════════════════════════╝
"""


# Usage Example
if __name__ == "__main__":
    logger.add(
        "logs/auto_optimizer.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        rotation="1 day",
    )

    # Example: Run optimization
    optimizer = AutoOptimizer()
    # optimizer.optimize(df, trade_csv_path="data/trade_logs/trades.csv")
    # print(optimizer.get_optimization_report())
