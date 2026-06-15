#!/usr/bin/env python3
"""
Test Scalping Optimizer
=======================
Test scalping analysis dengan 70% win rate target.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.scalping_optimizer import create_scalping_optimizer


def main():
    """Test scalping optimizer."""
    print("\n" + "="*70)
    print("🏃 SCALPING OPTIMIZER TEST")
    print("="*70 + "\n")

    optimizer = create_scalping_optimizer()
    print("Analyzing scalping performance...\n")

    try:
        data = optimizer.analyze_scalping_performance(days=5)

        print(optimizer.format_scalping_analysis(data))

        print("\n" + "="*70)
        print("✅ Test Complete!")
        print("="*70 + "\n")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
