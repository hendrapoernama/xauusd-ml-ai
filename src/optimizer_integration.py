"""
Integration Layer: Auto-Optimizer ↔ Trading Bot
================================================
Bridges auto_optimizer outputs to live trading parameters.
Updates thresholds dynamically based on market regime + trade history.
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple
from loguru import logger
import polars as pl

from src.auto_optimizer import AutoOptimizer, OptimizationResult


class OptimizerIntegration:
    """Manages optimizer integration with trading bot."""

    def __init__(self, trade_csv_path: str = "data/trade_logs/trades.csv", cache_dir: str = "data"):
        self.optimizer = AutoOptimizer()
        self.trade_csv_path = trade_csv_path
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.cache_file = self.cache_dir / "optimizer_cache.json"
        self.last_optimization_time = None
        self.optimization_interval_hours = 1  # Update parameters every hour

    def should_optimize(self) -> bool:
        """Check if it's time to run optimization."""
        if self.last_optimization_time is None:
            return True

        elapsed = datetime.now() - self.last_optimization_time
        return elapsed >= timedelta(hours=self.optimization_interval_hours)

    def run_optimization(self, df: pl.DataFrame) -> Optional[OptimizationResult]:
        """
        Run optimization and return results.

        Args:
            df: Current market data (OHLCV DataFrame with 50+ bars)

        Returns:
            OptimizationResult with recommended parameters
        """
        if len(df) < 50:
            logger.debug(f"[OPTIMIZER] Insufficient data ({len(df)} bars), skipping optimization")
            return None

        try:
            result = self.optimizer.optimize(df, self.trade_csv_path)
            self.last_optimization_time = datetime.now()
            self._cache_result(result)
            return result
        except Exception as e:
            logger.error(f"[OPTIMIZER] Optimization failed: {e}")
            return self._load_cached_result()

    def get_dynamic_parameters(self, df: pl.DataFrame) -> Dict[str, float]:
        """
        Get current optimal parameters.
        Updates from optimizer if interval passed.

        Returns:
            {
                "confidence_threshold": 0.60,
                "min_rr": 1.5,
                "lot_multiplier": 1.0,
            }
        """
        # Try to optimize if interval passed
        if self.should_optimize():
            result = self.run_optimization(df)
            if result:
                return self._result_to_params(result)

        # Fall back to cached result
        cached = self._load_cached_result()
        if cached:
            return self._result_to_params(cached)

        # Default fallback
        return {
            "confidence_threshold": 0.60,
            "min_rr": 1.5,
            "lot_multiplier": 1.0,
        }

    @staticmethod
    def _result_to_params(result: OptimizationResult) -> Dict[str, float]:
        """Convert OptimizationResult to parameter dict."""
        return {
            "confidence_threshold": result.optimal_confidence,
            "min_rr": result.optimal_rr_minimum,
            "lot_multiplier": result.optimal_lot_multiplier,
            "expected_winrate": result.expected_winrate,
            "expected_profit_factor": result.expected_profit_factor,
        }

    def _cache_result(self, result: OptimizationResult):
        """Save optimization result to cache file."""
        try:
            cache_data = {
                "timestamp": datetime.now().isoformat(),
                "optimal_confidence": result.optimal_confidence,
                "optimal_rr_minimum": result.optimal_rr_minimum,
                "optimal_lot_multiplier": result.optimal_lot_multiplier,
                "expected_winrate": result.expected_winrate,
                "expected_profit_factor": result.expected_profit_factor,
                "confidence_score": result.confidence_score,
            }
            with open(self.cache_file, "w") as f:
                json.dump(cache_data, f, indent=2)
        except Exception as e:
            logger.warning(f"[OPTIMIZER] Failed to cache result: {e}")

    def _load_cached_result(self) -> Optional[OptimizationResult]:
        """Load last optimization result from cache."""
        try:
            if not self.cache_file.exists():
                return None

            with open(self.cache_file, "r") as f:
                data = json.load(f)

            # Check if cache is fresh (< 2 hours old)
            ts = datetime.fromisoformat(data["timestamp"])
            if datetime.now() - ts > timedelta(hours=2):
                return None

            return OptimizationResult(
                optimal_confidence=data["optimal_confidence"],
                optimal_rr_minimum=data["optimal_rr_minimum"],
                optimal_lot_multiplier=data["optimal_lot_multiplier"],
                expected_winrate=data["expected_winrate"],
                expected_profit_factor=data["expected_profit_factor"],
                confidence_score=data["confidence_score"],
            )
        except Exception as e:
            logger.warning(f"[OPTIMIZER] Failed to load cached result: {e}")
            return None

    def get_optimization_report(self) -> str:
        """Get human-readable optimization report."""
        return self.optimizer.get_optimization_report()


class DynamicParameterManager:
    """Manages dynamic parameter updates in trading bot."""

    def __init__(self, optimizer_integration: OptimizerIntegration):
        self.optimizer = optimizer_integration
        self.current_params: Dict[str, float] = {}
        self.update_history: list = []

    def update_parameters(self, df: pl.DataFrame) -> bool:
        """
        Update trading parameters based on optimizer.

        Returns:
            True if parameters changed
        """
        new_params = self.optimizer.get_dynamic_parameters(df)

        # Check if changed
        if self.current_params == new_params:
            return False

        # Log change
        logger.info(
            f"[PARAM UPDATE] Confidence: {self.current_params.get('confidence_threshold', 0.60):.0%} "
            f"→ {new_params['confidence_threshold']:.0%} | "
            f"RR: {self.current_params.get('min_rr', 1.5):.1f} "
            f"→ {new_params['min_rr']:.1f} | "
            f"Expected WR: {new_params.get('expected_winrate', 0):.0%}"
        )

        self.current_params = new_params
        self.update_history.append({
            "timestamp": datetime.now().isoformat(),
            "params": new_params,
        })

        return True

    def get_confidence_threshold(self) -> float:
        """Get current confidence threshold."""
        return self.current_params.get("confidence_threshold", 0.60)

    def get_min_rr(self) -> float:
        """Get current minimum RR."""
        return self.current_params.get("min_rr", 1.5)

    def get_lot_multiplier(self) -> float:
        """Get current lot size multiplier."""
        return self.current_params.get("lot_multiplier", 1.0)

    def get_expected_metrics(self) -> Tuple[float, float]:
        """Get expected winrate and profit factor."""
        wr = self.current_params.get("expected_winrate", 0.55)
        pf = self.current_params.get("expected_profit_factor", 1.5)
        return wr, pf


# Global instance (lazy initialized)
_optimizer_integration: Optional[OptimizerIntegration] = None
_parameter_manager: Optional[DynamicParameterManager] = None


def get_optimizer_integration() -> OptimizerIntegration:
    """Get or create optimizer integration instance."""
    global _optimizer_integration
    if _optimizer_integration is None:
        _optimizer_integration = OptimizerIntegration()
    return _optimizer_integration


def get_parameter_manager() -> DynamicParameterManager:
    """Get or create parameter manager instance."""
    global _parameter_manager
    if _parameter_manager is None:
        _parameter_manager = DynamicParameterManager(get_optimizer_integration())
    return _parameter_manager


def init_optimizer_integration(trade_csv_path: str = "data/trade_logs/trades.csv"):
    """Initialize optimizer integration with custom paths."""
    global _optimizer_integration, _parameter_manager
    _optimizer_integration = OptimizerIntegration(trade_csv_path)
    _parameter_manager = DynamicParameterManager(_optimizer_integration)
