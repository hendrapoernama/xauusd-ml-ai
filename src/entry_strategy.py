"""
Entry Strategy Manager
======================
Manage entry trading strategy: SMC+ML only vs SMC+ML+AI validation vs AI primary

Entry Strategies:
1. SMC_ML_ONLY - Pure SMC + ML signals (fastest, no AI delay)
2. SMC_ML_AI - SMC+ML + AI validation (balanced, add AI confirmation)
3. AI_PRIMARY - AI sebagai primary, SMC+ML confirmation (AI-first approach)
"""

import json
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
from loguru import logger
from zoneinfo import ZoneInfo

WIB = ZoneInfo("Asia/Jakarta")

# Data directory
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
ENTRY_STRATEGY_FILE = DATA_DIR / "entry_strategy.json"


class EntryStrategyType(str, Enum):
    """Available entry strategies."""
    SMC_ML_ONLY = "SMC_ML_ONLY"
    SMC_ML_AI = "SMC_ML_AI"
    AI_PRIMARY = "AI_PRIMARY"


@dataclass
class StrategyConfig:
    """Configuration untuk setiap entry strategy."""
    name: str
    description: str
    use_smc: bool
    use_ml: bool
    use_ai: bool
    ai_as_primary: bool
    min_ai_confidence: int  # Minimum AI confidence required (0-100)
    require_ai_confirmation: bool  # Apakah AI confirmation wajib?
    max_ai_delay_seconds: int  # Maksimal delay untuk menunggu AI response
    emoji: str


STRATEGY_CONFIGS = {
    EntryStrategyType.SMC_ML_ONLY: StrategyConfig(
        name="SMC_ML_ONLY",
        description="Pure SMC + ML signals (no AI validation)",
        use_smc=True,
        use_ml=True,
        use_ai=False,
        ai_as_primary=False,
        min_ai_confidence=0,
        require_ai_confirmation=False,
        max_ai_delay_seconds=0,
        emoji="⚡",
    ),
    EntryStrategyType.SMC_ML_AI: StrategyConfig(
        name="SMC_ML_AI",
        description="SMC + ML + AI validation (balanced)",
        use_smc=True,
        use_ml=True,
        use_ai=True,
        ai_as_primary=False,
        min_ai_confidence=60,  # AI confidence >= 60%
        require_ai_confirmation=False,  # Optional, not required
        max_ai_delay_seconds=5,
        emoji="⚖️",
    ),
    EntryStrategyType.AI_PRIMARY: StrategyConfig(
        name="AI_PRIMARY",
        description="AI primary entry (SMC+ML confirmation only)",
        use_smc=True,
        use_ml=True,
        use_ai=True,
        ai_as_primary=True,
        min_ai_confidence=70,  # AI confidence >= 70%
        require_ai_confirmation=True,  # AI confirmation REQUIRED
        max_ai_delay_seconds=10,
        emoji="🤖",
    ),
}


class EntryStrategyManager:
    """Manage entry strategy configuration."""

    def __init__(self):
        self.current_strategy = self._load_strategy()

    def _load_strategy(self) -> EntryStrategyType:
        """Load current strategy from file atau default."""
        try:
            if ENTRY_STRATEGY_FILE.exists():
                with open(ENTRY_STRATEGY_FILE, "r") as f:
                    data = json.load(f)
                    strategy_name = data.get("strategy", "SMC_ML_ONLY")
                    return EntryStrategyType(strategy_name)
        except Exception as e:
            logger.warning(f"Failed to load entry strategy: {e}")

        return EntryStrategyType.SMC_ML_ONLY  # Default

    def _save_strategy(self):
        """Save current strategy to file."""
        try:
            with open(ENTRY_STRATEGY_FILE, "w") as f:
                json.dump(
                    {
                        "strategy": self.current_strategy.value,
                        "timestamp": __import__("datetime").datetime.now(WIB).isoformat(),
                    },
                    f,
                    indent=2,
                )
        except Exception as e:
            logger.error(f"Failed to save entry strategy: {e}")

    def get_current_strategy(self) -> EntryStrategyType:
        """Get current active strategy."""
        return self.current_strategy

    def get_strategy_config(self, strategy: EntryStrategyType = None) -> StrategyConfig:
        """Get config untuk strategy."""
        if strategy is None:
            strategy = self.current_strategy
        return STRATEGY_CONFIGS.get(strategy, STRATEGY_CONFIGS[EntryStrategyType.SMC_ML_ONLY])

    def set_strategy(self, strategy: EntryStrategyType) -> bool:
        """Set new entry strategy."""
        try:
            if strategy not in STRATEGY_CONFIGS:
                logger.error(f"Unknown strategy: {strategy}")
                return False

            self.current_strategy = strategy
            self._save_strategy()
            logger.info(f"Entry strategy changed to: {strategy.value}")
            return True
        except Exception as e:
            logger.error(f"Failed to set strategy: {e}")
            return False

    def list_strategies(self) -> dict:
        """List all available strategies dengan details."""
        strategies = {}
        for strategy_type, config in STRATEGY_CONFIGS.items():
            is_current = strategy_type == self.current_strategy
            strategies[strategy_type.value] = {
                "emoji": config.emoji,
                "description": config.description,
                "use_smc": config.use_smc,
                "use_ml": config.use_ml,
                "use_ai": config.use_ai,
                "ai_primary": config.ai_as_primary,
                "min_ai_confidence": config.min_ai_confidence,
                "require_ai_confirmation": config.require_ai_confirmation,
                "current": is_current,
            }
        return strategies

    def get_strategy_info(self, strategy: EntryStrategyType = None) -> str:
        """Get detailed info untuk strategy."""
        if strategy is None:
            strategy = self.current_strategy

        config = self.get_strategy_config(strategy)
        is_current = "✅ CURRENT" if strategy == self.current_strategy else ""

        components = []
        if config.use_smc:
            components.append("📊 SMC")
        if config.use_ml:
            components.append("🤖 ML")
        if config.use_ai:
            if config.ai_as_primary:
                components.append("🎯 AI (PRIMARY)")
            else:
                components.append("🎯 AI (Validation)")

        components_str = " + ".join(components)

        msg = f"""<b>{config.emoji} {strategy.value} {is_current}</b>

<b>Description:</b> {config.description}

<b>Components:</b>
{components_str}

<b>Settings:</b>
  • Min AI Confidence: {config.min_ai_confidence}%
  • AI Confirmation: {'REQUIRED' if config.require_ai_confirmation else 'Optional'}
  • Max AI Delay: {config.max_ai_delay_seconds}s

<b>Behavior:</b>"""

        if strategy == EntryStrategyType.SMC_ML_ONLY:
            msg += """
  1. Calculate SMC signals (Order Block, FVG, BOS, CHoCH)
  2. Get ML prediction confidence
  3. Entry jika SMC + ML aligned (no AI delay)
  4. Fastest execution, no AI overhead"""

        elif strategy == EntryStrategyType.SMC_ML_AI:
            msg += """
  1. Calculate SMC signals + ML confidence
  2. If SMC+ML signal > threshold:
     a. Call AI untuk validation (optional)
     b. If AI available & confident, use AI insight
     c. Otherwise, entry dengan SMC+ML only
  3. Balanced: ada AI confirmation tanpa mandatory"""

        elif strategy == EntryStrategyType.AI_PRIMARY:
            msg += """
  1. Call AI analysis untuk market condition
  2. Get AI trading recommendation (BUY/SELL/WAIT)
  3. If AI signal = entry direction:
     a. Use SMC+ML confirmation
     b. Proceed only if all aligned (AI + SMC + ML)
  4. Slowest tapi most confident entries"""

        return msg.strip()

    def apply_strategy_to_trading(self, trading_bot):
        """Apply strategy settings ke trading bot config."""
        try:
            strategy = self.current_strategy
            config = self.get_strategy_config(strategy)

            # Store strategy info di bot untuk runtime reference
            trading_bot.entry_strategy = strategy
            trading_bot.entry_strategy_config = config

            logger.info(f"Applied entry strategy: {strategy.value}")
            logger.info(f"  - Use SMC: {config.use_smc}")
            logger.info(f"  - Use ML: {config.use_ml}")
            logger.info(f"  - Use AI: {config.use_ai}")
            logger.info(f"  - AI Primary: {config.ai_as_primary}")

            return True
        except Exception as e:
            logger.error(f"Failed to apply strategy: {e}")
            return False


def get_entry_strategy_manager() -> EntryStrategyManager:
    """Factory function untuk create manager singleton."""
    return EntryStrategyManager()
