"""
Trading Modes System
====================
Define and manage different trading modes (AGGRESSIVE, NORMAL, CONSERVATIVE, RESTRICTED)
each with different risk parameters. Configurable via Telegram commands.

Modes control:
- ML confidence threshold (entry signal strength required)
- Max concurrent positions
- Max daily loss limit
- Risk per trade
"""

import json
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List
from zoneinfo import ZoneInfo

from loguru import logger
from src.dynamic_threshold_calculator import DynamicThresholds

WIB = ZoneInfo("Asia/Jakarta")


class TradeModeType(Enum):
    """Trading mode types."""
    AGGRESSIVE = "aggressive"
    NORMAL = "normal"
    CONSERVATIVE = "conservative"
    RESTRICTED = "restricted"


@dataclass
class ModeConfig:
    """Configuration for a trading mode."""
    name: str
    ml_threshold: float  # ML confidence required for entry
    max_positions: int  # Max concurrent open positions
    max_daily_loss_pct: float  # Max daily loss as % of capital
    risk_per_trade: float  # Risk per trade as % of capital
    max_loss_per_position_usd: float  # Hard cap on position loss
    description: str = ""
    is_dynamic: bool = False  # Whether this mode uses dynamic thresholds


# Define all trading modes
TRADING_MODES: Dict[str, ModeConfig] = {
    "DYNAMIC": ModeConfig(
        name="DYNAMIC",
        ml_threshold=0.65,  # Will be updated hourly by calculator
        max_positions=4,
        max_daily_loss_pct=3.5,
        risk_per_trade=1.25,
        max_loss_per_position_usd=35.0,
        description="AI-adaptive mode. Thresholds adjust hourly based on market regime, volatility, and recent performance.",
        is_dynamic=True,
    ),
    "SCALPING": ModeConfig(
        name="SCALPING",
        ml_threshold=0.55,
        max_positions=5,
        max_daily_loss_pct=4.0,
        risk_per_trade=1.0,
        max_loss_per_position_usd=20.0,
        description="Ultra-fast micro trades. Multiple quick positions, tight stops. For highly volatile markets.",
    ),
    "AGGRESSIVE": ModeConfig(
        name="AGGRESSIVE",
        ml_threshold=0.60,
        max_positions=4,
        max_daily_loss_pct=5.0,
        risk_per_trade=2.0,
        max_loss_per_position_usd=50.0,
        description="High risk, high reward. Ideal for volatile markets and experienced traders.",
    ),
    "NORMAL": ModeConfig(
        name="NORMAL",
        ml_threshold=0.65,
        max_positions=3,
        max_daily_loss_pct=3.0,
        risk_per_trade=1.5,
        max_loss_per_position_usd=40.0,
        description="Balanced risk/reward. Default mode for consistent trading.",
    ),
    "CONSERVATIVE": ModeConfig(
        name="CONSERVATIVE",
        ml_threshold=0.70,
        max_positions=2,
        max_daily_loss_pct=2.0,
        risk_per_trade=1.0,
        max_loss_per_position_usd=25.0,
        description="Low risk, capital preservation. For quiet markets.",
    ),
    "RESTRICTED": ModeConfig(
        name="RESTRICTED",
        ml_threshold=0.75,
        max_positions=1,
        max_daily_loss_pct=1.0,
        risk_per_trade=0.5,
        max_loss_per_position_usd=10.0,
        description="Minimal trading. Recovery mode or low confidence periods.",
    ),
}


class TradingModeManager:
    """Manage trading modes - load, save, and apply settings."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.mode_file = self.data_dir / "current_mode.json"

        # Load current mode (default to NORMAL)
        self._current_mode = self._load_mode_from_file() or "NORMAL"
        logger.info(f"TradingModeManager initialized with mode: {self._current_mode}")

    def _load_mode_from_file(self) -> Optional[str]:
        """Load current mode from file."""
        try:
            if self.mode_file.exists():
                with open(self.mode_file, "r") as f:
                    data = json.load(f)
                    mode = data.get("mode", "NORMAL")
                    if mode in TRADING_MODES:
                        logger.info(f"Loaded mode from file: {mode}")
                        return mode
        except Exception as e:
            logger.error(f"Error loading mode file: {e}")
        return None

    def _save_mode_to_file(self, mode: str):
        """Save current mode to file."""
        try:
            data = {
                "mode": mode,
                "timestamp": datetime.now(WIB).isoformat(),
            }
            with open(self.mode_file, "w") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved mode to file: {mode}")
        except Exception as e:
            logger.error(f"Error saving mode file: {e}")

    def get_current_mode(self) -> str:
        """Get currently active mode name."""
        return self._current_mode

    def get_mode_config(self, mode: Optional[str] = None) -> ModeConfig:
        """Get mode configuration."""
        mode_name = mode or self._current_mode
        if mode_name not in TRADING_MODES:
            logger.warning(f"Unknown mode: {mode_name}, defaulting to NORMAL")
            mode_name = "NORMAL"
        return TRADING_MODES[mode_name]

    def set_mode(self, mode: str) -> bool:
        """Set trading mode."""
        if mode not in TRADING_MODES:
            logger.error(f"Invalid mode: {mode}")
            return False

        old_mode = self._current_mode
        self._current_mode = mode
        self._save_mode_to_file(mode)
        logger.info(f"Trading mode changed: {old_mode} → {mode}")
        return True

    def list_modes(self) -> List[Dict]:
        """List all available modes with details."""
        modes = []
        for mode_name, config in TRADING_MODES.items():
            modes.append({
                "name": mode_name,
                "ml_threshold": config.ml_threshold,
                "max_positions": config.max_positions,
                "max_daily_loss_pct": config.max_daily_loss_pct,
                "risk_per_trade": config.risk_per_trade,
                "description": config.description,
                "current": mode_name == self._current_mode,
            })
        return modes

    def get_mode_summary(self, mode: Optional[str] = None) -> str:
        """Get formatted mode summary for Telegram."""
        mode_name = mode or self._current_mode
        if mode_name not in TRADING_MODES:
            return f"❌ Mode '{mode_name}' not found"

        cfg = TRADING_MODES[mode_name]
        current_marker = "✅ ACTIVE" if mode_name == self._current_mode else ""

        return f"""
<b>{cfg.name}</b> {current_marker}

{cfg.description}

<b>Settings:</b>
  • ML Threshold: <code>{cfg.ml_threshold:.0%}</code>
  • Max Positions: <code>{cfg.max_positions}</code>
  • Max Daily Loss: <code>{cfg.max_daily_loss_pct:.1f}%</code>
  • Risk/Trade: <code>{cfg.risk_per_trade:.1f}%</code>
  • Max Loss/Position: <code>${cfg.max_loss_per_position_usd:.0f}</code>
""".strip()

    def get_all_modes_summary(self) -> str:
        """Get formatted summary of all modes for Telegram."""
        lines = ["<b>📊 TRADING MODES</b>\n"]

        for mode_name, cfg in TRADING_MODES.items():
            current = "✅" if mode_name == self._current_mode else "  "
            lines.append(
                f"{current} <b>{cfg.name}</b> "
                f"(Threshold: {cfg.ml_threshold:.0%}, "
                f"Max Pos: {cfg.max_positions}, "
                f"Max Loss: {cfg.max_daily_loss_pct:.1f}%)"
            )

        lines.append("\n<i>Use /mode_info <name> to see full details</i>")
        return "\n".join(lines)

    def apply_mode_to_config(self, config_obj) -> bool:
        """
        Apply current mode settings to a config object.
        Config object should have: risk.max_positions, risk.max_daily_loss_usd, etc.
        """
        try:
            cfg = self.get_mode_config()

            # Apply to risk config if available
            if hasattr(config_obj, "risk"):
                if hasattr(config_obj.risk, "max_positions"):
                    config_obj.risk.max_positions = cfg.max_positions
                if hasattr(config_obj.risk, "max_daily_loss"):
                    config_obj.risk.max_daily_loss = cfg.max_daily_loss_pct

            # Apply ML threshold if available
            if hasattr(config_obj, "ml_threshold"):
                config_obj.ml_threshold = cfg.ml_threshold

            logger.info(f"Applied {self._current_mode} mode settings to config")
            return True
        except Exception as e:
            logger.error(f"Error applying mode to config: {e}")
            return False

    def get_mode_stats(self) -> Dict:
        """Get stats about mode and performance."""
        cfg = self.get_mode_config()
        return {
            "current_mode": self._current_mode,
            "ml_threshold": cfg.ml_threshold,
            "max_positions": cfg.max_positions,
            "max_daily_loss_pct": cfg.max_daily_loss_pct,
            "risk_per_trade": cfg.risk_per_trade,
            "max_loss_per_position": cfg.max_loss_per_position_usd,
            "is_dynamic": cfg.is_dynamic,
        }

    def update_dynamic_thresholds(self, dynamic_thresholds: DynamicThresholds) -> bool:
        """
        Update thresholds for DYNAMIC mode based on market analysis.

        Args:
            dynamic_thresholds: DynamicThresholds object with calculated values

        Returns:
            True if updated successfully
        """
        try:
            if self._current_mode != "DYNAMIC":
                logger.warning(f"Not in DYNAMIC mode (current: {self._current_mode}), ignoring update")
                return False

            cfg = TRADING_MODES["DYNAMIC"]
            cfg.ml_threshold = dynamic_thresholds.ml_threshold

            logger.info(
                f"Updated DYNAMIC mode thresholds: "
                f"ML={dynamic_thresholds.ml_threshold:.2%}, "
                f"SMC={dynamic_thresholds.smc_threshold:.2%}, "
                f"Quality={dynamic_thresholds.ai_quality_threshold:.0f} "
                f"(confidence: {dynamic_thresholds.confidence}%)"
            )
            return True

        except Exception as e:
            logger.error(f"Error updating dynamic thresholds: {e}")
            return False

    def is_dynamic_mode(self) -> bool:
        """Check if current mode is DYNAMIC."""
        cfg = self.get_mode_config()
        return cfg.is_dynamic


# Global instance
_mode_manager: Optional[TradingModeManager] = None


def get_trading_mode_manager() -> TradingModeManager:
    """Get or create global trading mode manager."""
    global _mode_manager
    if _mode_manager is None:
        _mode_manager = TradingModeManager()
    return _mode_manager


if __name__ == "__main__":
    # Test the mode manager
    manager = get_trading_mode_manager()

    print("=== Current Mode ===")
    print(manager.get_mode_summary())

    print("\n=== All Modes ===")
    print(manager.get_all_modes_summary())

    print("\n=== Switch to AGGRESSIVE ===")
    manager.set_mode("AGGRESSIVE")
    print(manager.get_mode_summary())

    print("\n=== Mode Stats ===")
    print(manager.get_mode_stats())
