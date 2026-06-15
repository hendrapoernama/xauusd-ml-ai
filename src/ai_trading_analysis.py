"""
AI Trading Analysis Module
==========================
Uses OpenRouter AI to analyze trading data and provide intelligent insights.

Features:
- AI-powered trading analysis
- Professional insights and recommendations
- Market assessment from AI perspective
- Risk analysis and suggestions
- Multiple AI providers support
"""

import asyncio
import json
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from loguru import logger
from src.position_analysis import PositionAnalyzer, AnalysisResult
from src.ai_provider import AIProvider

WIB = ZoneInfo("Asia/Jakarta")


class AITradingAnalyzer:
    """Use AI to analyze trading data and provide insights."""

    def __init__(self, ai_provider: Optional[AIProvider] = None):
        """
        Initialize AI Trading Analyzer.

        Args:
            ai_provider: AIProvider instance (if None, creates new one from env)
        """
        if ai_provider:
            self.ai = ai_provider
        else:
            self.ai = AIProvider()

        self.position_analyzer = PositionAnalyzer()

    async def analyze_with_ai(self, days: int = 5) -> dict:
        """
        Analyze trading data using AI.

        Returns:
            Dict with AI analysis insights
        """
        logger.info(f"Starting AI trading analysis for {days} days...")

        # Get basic analysis
        analysis = self.position_analyzer.analyze_no_positions(days=days)

        # Prepare data for AI
        ai_prompt = self._build_ai_prompt(analysis, days)

        # Call AI for analysis
        if not self.ai.enabled:
            logger.warning("AI Provider not enabled — returning basic analysis")
            return {
                "ai_enabled": False,
                "analysis": analysis,
                "ai_insights": "AI Provider tidak tersedia. Gunakan /analysis untuk analisa dasar.",
            }

        try:
            # Call AI via analyze_macro_context with custom prompt
            ai_response = await self._call_ai_analysis(ai_prompt)
            return {
                "ai_enabled": True,
                "analysis": analysis,
                "ai_insights": ai_response,
            }
        except Exception as e:
            logger.error(f"AI analysis error: {e}")
            return {
                "ai_enabled": True,
                "analysis": analysis,
                "ai_insights": f"Gagal mendapat AI insights: {e}",
            }

    def _build_ai_prompt(self, analysis: AnalysisResult, days: int) -> str:
        """Build comprehensive prompt for AI analysis."""
        signal_details = ""
        if analysis.signals_by_type:
            signal_details = f"Tipe sinyal: BUY={analysis.signals_by_type.get('BUY', 0)}, SELL={analysis.signals_by_type.get('SELL', 0)}"

        blocking_details = ""
        if analysis.top_blocking_reasons:
            top_reason, count = analysis.top_blocking_reasons[0]
            pct = (count / analysis.total_signals * 100) if analysis.total_signals > 0 else 0
            blocking_details = f"\nAlasan blok utama: {top_reason} ({pct:.1f}% sinyal)"

        regime_details = ""
        if analysis.regime_distribution:
            regimes = ", ".join(
                [f"{k}={v}" for k, v in analysis.regime_distribution.items()]
            )
            regime_details = f"\nRegim pasar: {regimes}"

        win_rate_str = (
            f"Win rate: {analysis.win_rate:.1f}%"
            if analysis.win_rate is not None
            else "Belum ada trade"
        )
        profit_str = (
            f"Total P/L: ${analysis.total_profit:+.2f}"
            if analysis.total_profit is not None
            else "N/A"
        )
        avg_confidence = analysis.avg_signal_confidence if analysis.avg_signal_confidence is not None else 0
        execution_rate = analysis.execution_rate if analysis.execution_rate is not None else 0

        prompt = f"""Anda adalah expert trader XAUUSD dengan 20 tahun pengalaman. Analisa data trading 5 hari terakhir dan berikan insights + BUY/SELL RECOMMENDATION:

DATA TRADING ({days} HARI):
- Total Sinyal: {analysis.total_signals}
- Total Trade Executed: {analysis.total_trades}
- Execution Rate: {execution_rate:.1f}%
- Rata-rata Confidence Sinyal: {avg_confidence:.1f}%
{signal_details}
{blocking_details}
{regime_details}
- {win_rate_str}
- {profit_str}

INSTRUKSI PENTING:
Setelah analisa pasar, BERIKAN BUY/SELL RECOMMENDATION untuk minggu depan DENGAN FORMAT JELAS:

🎯 TRADING SIGNAL: [BUY atau SELL, bukan NEUTRAL]
📊 CONFIDENCE: [1-100]%
📍 ENTRY PRICE: [$X - $Y range]
🎁 TAKE PROFIT: [$Z level]
🛑 STOP LOSS: [$W level]
💡 ALASAN: [1-2 baris singkat]

PERTANYAAN:
1. Apa assessment kondisi pasar 5 hari ini? (1-2 kalimat)
2. Mengapa execution rate hanya {execution_rate:.1f}%? (root cause)
3. Apakah strategi masih efektif? (based on {(analysis.win_rate if analysis.win_rate is not None else 0):.1f}% win rate)
4. Mode trading apa yang cocok minggu depan?
5. ⚡ BUY atau SELL untuk minggu depan? (DENGAN FORMAT DI ATAS)

BERIKAN JAWABAN SINGKAT, PROFESIONAL, DAN ACTIONABLE DENGAN SIGNAL YANG JELAS!"""

        return prompt

    async def _call_ai_analysis(self, prompt: str) -> str:
        """Call AI with custom prompt for trading analysis."""
        try:
            # Use httpx to call OpenRouter directly with streaming
            import httpx

            if not self.ai.enabled or not hasattr(self.ai, "_client"):
                return "AI Provider tidak tersedia"

            headers = {
                "Authorization": f"Bearer {self.ai.api_key}",
                "HTTP-Referer": "https://xaubot-ai.local",
                "X-Title": "XAUBot Trading Analysis",
            }

            payload = {
                "model": self.ai.model or "deepseek/deepseek-chat",
                "messages": [
                    {
                        "role": "system",
                        "content": "Anda adalah expert trader emas (XAUUSD) dengan pengalaman 20 tahun. Analisa data trading dan berikan insights yang actionable dan profesional.",
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.7,
                "max_tokens": 1500,
            }

            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    self.ai._provider_config["base_url"],
                    json=payload,
                    headers=headers,
                )

                if response.status_code == 200:
                    data = response.json()
                    if "choices" in data and len(data["choices"]) > 0:
                        return data["choices"][0]["message"]["content"]
                    return "Respon AI kosong"
                else:
                    logger.error(f"AI API error: {response.status_code}")
                    return f"Error API: {response.status_code}"

        except Exception as e:
            logger.error(f"AI call error: {e}")
            return f"Gagal call AI: {e}"

    @staticmethod
    def format_ai_response(ai_insights: str) -> str:
        """Format AI response for Telegram dengan highlight BUY/SELL signal."""
        msg = """<b>🤖 AI TRADING ANALYSIS</b>

"""
        # Extract and highlight TRADING SIGNAL
        lines = ai_insights.split("\n")
        signal_found = False

        for i, line in enumerate(lines):
            # Highlight BUY/SELL signals
            if "TRADING SIGNAL:" in line.upper() or "SIGNAL:" in line.upper():
                signal_found = True
                msg += f"\n<b>{'='*50}</b>\n"
                if "BUY" in line.upper():
                    msg += f"🟢 <b>BUY SIGNAL</b>\n"
                elif "SELL" in line.upper():
                    msg += f"🔴 <b>SELL SIGNAL</b>\n"
                else:
                    msg += f"⚪ <b>{line}</b>\n"
                msg += f"<b>{'='*50}</b>\n"
                signal_found = True

            # Highlight confidence
            elif "CONFIDENCE:" in line.upper():
                # Extract confidence percentage
                if "%" in line:
                    msg += f"\n📊 {line}\n"
                else:
                    msg += f"\n📊 {line}"

            # Highlight Entry/TP/SL
            elif any(x in line.upper() for x in ["ENTRY PRICE:", "ENTRY:", "TAKE PROFIT:", "TP:", "STOP LOSS:", "SL:"]):
                msg += f"📍 {line}\n"

            # Highlight reason
            elif "ALASAN:" in line.upper() or "REASON:" in line.upper():
                msg += f"💡 {line}\n"

            # Format numbered points
            elif any(line.strip().startswith(f"{i}.") for i in range(1, 10)):
                msg += f"\n<b>{line}</b>"

            # Format regular content
            elif line.strip():
                if line.startswith("-"):
                    msg += f"  {line}\n"
                else:
                    msg += f"{line}\n"

        # Add footer
        msg += f"\n<b>{'='*50}</b>"
        msg += f"\n⏰ {datetime.now(WIB).strftime('%H:%M:%S')} WIB"
        msg += f"\n<i>Analysis by OpenRouter AI</i>"

        return msg.strip()


async def get_ai_trading_analysis(ai_provider: Optional[AIProvider] = None, days: int = 5) -> str:
    """
    Get AI trading analysis and return formatted Telegram message.

    Args:
        ai_provider: AIProvider instance
        days: Number of days to analyze (default 5)

    Returns:
        Formatted Telegram message string
    """
    analyzer = AITradingAnalyzer(ai_provider)
    result = await analyzer.analyze_with_ai(days=days)

    if not result["ai_enabled"]:
        return f"""⚠️ <b>AI NOT CONFIGURED</b>

AI Provider tidak aktif. Untuk mengaktifkan:

1. Set environment variables di .env:
   <code>AI_PROVIDER=openrouter</code>
   <code>AI_API_KEY=sk-...</code>
   <code>AI_MODEL=deepseek/deepseek-chat</code>

2. Restart bot: python main_live.py

3. Jalankan ulang: /ai_analysis

<i>Supported providers: openrouter, deepseek, openai, anthropic, zai</i>"""

    msg = AITradingAnalyzer.format_ai_response(result["ai_insights"])
    return msg
