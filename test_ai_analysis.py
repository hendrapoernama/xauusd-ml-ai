#!/usr/bin/env python3
"""
Test script untuk AI Trading Analysis
======================================
Test AI analysis tanpa perlu bot running.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.ai_trading_analysis import AITradingAnalyzer
from src.ai_provider import AIProvider
from dotenv import load_dotenv

# Load environment
load_dotenv()


async def test_ai_analysis():
    """Test AI analysis dengan data real dari log files."""
    print("\n" + "="*70)
    print("TEST AI TRADING ANALYSIS")
    print("="*70 + "\n")

    # Check AI Provider config
    ai_provider_name = os.getenv("AI_PROVIDER", "").lower()
    ai_api_key = os.getenv("AI_API_KEY", "")
    ai_model = os.getenv("AI_MODEL", "")

    print("📋 AI PROVIDER CONFIG:")
    print(f"  Provider: {ai_provider_name or '❌ NOT SET'}")
    print(f"  API Key: {'✅ SET' if ai_api_key else '❌ NOT SET'}")
    print(f"  Model: {ai_model or 'default'}")
    print()

    # Initialize AI Provider
    ai_provider = AIProvider(
        provider=ai_provider_name or None,
        api_key=ai_api_key or None,
        model=ai_model or None,
    )

    if not ai_provider.enabled:
        print("⚠️  AI Provider DISABLED!")
        print("\nUntuk enable AI analysis:")
        print("1. Edit .env file:")
        print("   AI_PROVIDER=openrouter")
        print("   AI_API_KEY=sk-or-v1-xxx...")
        print("   AI_MODEL=deepseek/deepseek-chat")
        print("\n2. Dapatkan API key dari:")
        print("   - OpenRouter: https://openrouter.ai (recommended)")
        print("   - DeepSeek: https://platform.deepseek.com")
        print("   - OpenAI: https://platform.openai.com")
        print("\n3. Restart app: python main_live.py")
        return

    print("✅ AI Provider ENABLED!")
    print(f"   Using: {ai_provider.provider_name}/{ai_provider.model}\n")

    # Run AI analysis
    print("🔄 Running AI Trading Analysis (5 days)...\n")
    analyzer = AITradingAnalyzer(ai_provider)

    try:
        result = await analyzer.analyze_with_ai(days=5)

        print("✅ Analysis Complete!\n")
        print("="*70)
        print("AI INSIGHTS:")
        print("="*70 + "\n")
        print(result["ai_insights"])
        print("\n" + "="*70 + "\n")

        # Offer to copy to telegram
        print("📱 COPY OUTPUT UNTUK TELEGRAM:")
        print("Command: /ai_analysis")
        print("\nOutput:")
        print(analyzer.format_ai_response(result["ai_insights"]))

    except asyncio.TimeoutError:
        print("❌ AI API Timeout!")
        print("   API took too long to respond. Check internet connection.")
    except Exception as e:
        print(f"❌ Error: {e}")
        print(f"\nTraceback:")
        import traceback
        traceback.print_exc()


async def main():
    """Main test function."""
    try:
        await test_ai_analysis()
    except KeyboardInterrupt:
        print("\n\n⏹️  Test interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    print("\n🤖 XAUBot AI Analysis Test\n")
    print("Testing AI Trading Analysis module...\n")

    asyncio.run(main())
