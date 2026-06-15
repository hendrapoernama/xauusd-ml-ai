"""
Dynamic Mode Integration
========================
Integrates dynamic threshold calculation into the main trading loop.

Usage in main_live.py:
```python
from src.dynamic_mode_integration import DynamicModeIntegration

dynamic_mode = DynamicModeIntegration(trading_mode_manager, data_dir="data")

# In main loop, every hour:
if dynamic_mode.should_update():
    await dynamic_mode.update_thresholds(
        market_data=market_data,
        atr_values=recent_atr_values,
        regime=current_regime,
        h1_bias=h1_bias,
        db=db_connection
    )
```
"""

from datetime import datetime
from typing import Optional, Dict, List
from zoneinfo import ZoneInfo
from pathlib import Path
import json

from loguru import logger

from src.dynamic_threshold_calculator import (
    DynamicThresholdCalculator,
    DynamicThresholds,
)
from src.trading_modes import TradingModeManager

WIB = ZoneInfo("Asia/Jakarta")


class DynamicModeIntegration:
    """Manages dynamic threshold updates in the trading system."""

    def __init__(self, mode_manager: TradingModeManager, data_dir: str = "data"):
        self.mode_manager = mode_manager
        self.data_dir = Path(data_dir)
        self.calculator = DynamicThresholdCalculator()
        self.threshold_history_file = self.data_dir / "dynamic_thresholds_history.json"

    def should_update(self) -> bool:
        """Check if dynamic thresholds should be updated."""
        if self.mode_manager.get_current_mode() != "DYNAMIC":
            return False

        return self.calculator.should_recalculate()

    async def update_thresholds(
        self,
        market_data: Dict,
        atr_values: List[float],
        regime: str,
        h1_bias: str,
        db=None,
    ) -> Optional[DynamicThresholds]:
        """
        Update dynamic thresholds based on current market conditions.

        Args:
            market_data: Dict with keys: atr, spread, volatility
            atr_values: List of recent ATR values (for average calculation)
            regime: Current market regime (trending, ranging, volatile, etc.)
            h1_bias: H1 bias (BULLISH, BEARISH, NEUTRAL)
            db: Database connection to fetch recent trades

        Returns:
            DynamicThresholds if updated, None otherwise
        """
        try:
            if not self.should_update():
                return None

            # 1. Enhance market data with ATR average
            if atr_values:
                market_data["atr_avg"] = sum(atr_values) / len(atr_values)

            # 2. Fetch recent trades if database available
            recent_trades = []
            if db:
                try:
                    recent_trades = await self._fetch_recent_trades(db)
                except Exception as e:
                    logger.warning(f"Could not fetch recent trades: {e}")

            # 3. Calculate new thresholds
            thresholds = self.calculator.calculate_thresholds(
                market_data=market_data,
                recent_trades=recent_trades,
                current_regime=regime,
                h1_bias=h1_bias,
            )

            # 4. Update trading mode
            self.mode_manager.update_dynamic_thresholds(thresholds)

            # 5. Save to history
            self._save_to_history(thresholds)

            logger.info(
                f"✅ Dynamic thresholds updated: "
                f"ML={thresholds.ml_threshold:.0%} | "
                f"SMC={thresholds.smc_threshold:.0%} | "
                f"Quality={thresholds.ai_quality_threshold:.0f} | "
                f"Confidence: {thresholds.confidence}%"
            )

            return thresholds

        except Exception as e:
            logger.error(f"Error updating dynamic thresholds: {e}")
            return None

    async def _fetch_recent_trades(self, db, limit: int = 50) -> List[Dict]:
        """Fetch recent trades from database."""
        try:
            query = """
                SELECT profit, loss, status
                FROM trades
                ORDER BY entry_time DESC
                LIMIT ?
            """
            trades = await db.fetch_all(query, (limit,))

            return [
                {
                    "profit": t.get("profit", 0),
                    "status": t.get("status", "closed"),
                }
                for t in trades
            ]

        except Exception as e:
            logger.error(f"Error fetching recent trades: {e}")
            return []

    def _save_to_history(self, thresholds: DynamicThresholds):
        """Save threshold calculation to history."""
        try:
            history = {}

            # Load existing history
            if self.threshold_history_file.exists():
                with open(self.threshold_history_file, "r") as f:
                    history = json.load(f)

            # Add new entry
            history[thresholds.timestamp.isoformat()] = thresholds.to_dict()

            # Keep only last 100 entries
            if len(history) > 100:
                # Remove oldest entries
                sorted_keys = sorted(history.keys())
                for key in sorted_keys[:-100]:
                    del history[key]

            # Save back
            with open(self.threshold_history_file, "w") as f:
                json.dump(history, f, indent=2)

        except Exception as e:
            logger.error(f"Error saving threshold history: {e}")

    def get_current_thresholds(self) -> Optional[DynamicThresholds]:
        """Get currently active thresholds."""
        return self.calculator.get_last_thresholds()

    def format_for_telegram(self, thresholds: Optional[DynamicThresholds] = None) -> str:
        """Format threshold info for Telegram."""
        if not thresholds:
            thresholds = self.get_current_thresholds()

        if not thresholds:
            return "❌ No dynamic thresholds calculated yet"

        return f"""
<b>🔄 DYNAMIC MODE - CURRENT THRESHOLDS</b>

<b>Adaptive Thresholds:</b>
  • ML: <code>{thresholds.ml_threshold:.0%}</code>
  • SMC: <code>{thresholds.smc_threshold:.0%}</code>
  • AI Quality: <code>{thresholds.ai_quality_threshold:.0f}/100</code>

<b>Confidence:</b> <code>{thresholds.confidence}%</code>

<b>Reason:</b> <i>{thresholds.reason}</i>

<b>Updated:</b> <code>{thresholds.timestamp.strftime('%H:%M:%S %Z')}</code>
<i>Next update: Hourly</i>
""".strip()

    def get_threshold_history(self, hours: int = 24) -> Dict:
        """Get threshold history for the last N hours."""
        try:
            if not self.threshold_history_file.exists():
                return {}

            with open(self.threshold_history_file, "r") as f:
                history = json.load(f)

            # Filter by time
            cutoff = datetime.now(WIB).timestamp() - (hours * 3600)
            filtered = {
                k: v
                for k, v in history.items()
                if datetime.fromisoformat(k).timestamp() > cutoff
            }

            return filtered

        except Exception as e:
            logger.error(f"Error getting threshold history: {e}")
            return {}
