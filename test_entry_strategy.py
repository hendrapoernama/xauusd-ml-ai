#!/usr/bin/env python3
"""
Test Entry Strategy Manager
============================
Test entry strategy configuration system.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.entry_strategy import (
    get_entry_strategy_manager,
    EntryStrategyType,
    STRATEGY_CONFIGS,
)


def main():
    """Test entry strategy manager."""
    print("\n" + "="*70)
    print("🎯 ENTRY STRATEGY MANAGER TEST")
    print("="*70 + "\n")

    manager = get_entry_strategy_manager()

    print(f"Current Strategy: {manager.get_current_strategy().value}\n")

    # List all strategies
    print("=" * 70)
    print("📝 AVAILABLE STRATEGIES:")
    print("=" * 70 + "\n")

    strategies = manager.list_strategies()
    for name, config in strategies.items():
        print(f"{config['emoji']} {name}")
        print(f"   {config['description']}")
        if config['current']:
            print(f"   ✅ CURRENT")
        print()

    # Test each strategy info
    print("=" * 70)
    print("📋 STRATEGY DETAILS:")
    print("=" * 70 + "\n")

    for strategy in EntryStrategyType:
        print(manager.get_strategy_info(strategy))
        print("\n" + "-" * 70 + "\n")

    # Test changing strategy
    print("=" * 70)
    print("🔄 TEST CHANGING STRATEGY:")
    print("=" * 70 + "\n")

    current = manager.get_current_strategy()
    print(f"Current: {current.value}")

    # Change to AI_PRIMARY
    print(f"\nChanging to: {EntryStrategyType.AI_PRIMARY.value}")
    success = manager.set_strategy(EntryStrategyType.AI_PRIMARY)
    print(f"Success: {success}")
    print(f"New current: {manager.get_current_strategy().value}")

    # Change back
    print(f"\nChanging back to: {current.value}")
    success = manager.set_strategy(current)
    print(f"Success: {success}")
    print(f"Current again: {manager.get_current_strategy().value}")

    print("\n" + "="*70)
    print("✅ Test Complete!")
    print("="*70 + "\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
