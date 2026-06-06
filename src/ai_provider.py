"""
AI Provider wrapper — multi-provider LLM integration for macro context enrichment.

Supported providers:
- Z.AI (glm-5.1, glm-4v) — https://open.bigmodel.cn
- DeepSeek (deepseek-chat) — https://platform.deepseek.com
- OpenRouter (deepseek/deepseek-chat, etc) — https://openrouter.ai
- OpenAI (gpt-4o-mini, gpt-3.5-turbo) — https://api.openai.com
- Custom HTTP endpoints

Filosofi:
- LLM NEVER blocks trades (Fase 1 enrichment-only, zero risk)
- Always has sensible fallback if API down or timeout
- Cost-bounded: enrichment only per trade notify, not per iteration
- Support multiple providers untuk flexibility & cost optimization
"""

import os
import json
import time
import asyncio
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional, Dict, Any
from loguru import logger

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    logger.warning("httpx not installed — AI enrichment may be limited")

try:
    from anthropic import Anthropic, APIError, APIConnectionError, APITimeoutError
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


@dataclass
class MacroContext:
    """Macro context analyzed by LLM."""
    sentiment: float  # -1.0 (bearish) to +1.0 (bullish), 0.0 = neutral
    reasoning: str    # Narasi 1-2 kalimat kondisi makro
    news_summary: str # Ringkas berita/event relevan hari ini
    confidence: float # 0.0-1.0 — how confident is this analysis
    timestamp: float  # Unix timestamp saat analysis


@dataclass
class TradeRichContext:
    """Rich context untuk Telegram notification."""
    trade_reasoning: str  # "Sinyal SMC karena FVG+BOS, ML agree 72%"
    macro_reasoning: str  # "Fed hawkish → sentimen bearish, jaga lot"
    combined_insight: str # "SMC bullish tapi Fed headwind → moderate confidence"


@dataclass
class SLAnalysis:
    """AI analysis of why Stop Loss was triggered (Lapis 3)."""
    root_cause: str           # "Session salah (off-hours), bid-ask spread lebar"
    avoidance_strategy: str   # "Hindari entry saat off-hours, butuh confidence >75%"
    confidence_modifier: float # -0.15 (reduce confidence 15% next entry), 0.0 (no impact), +0.10 (boost)
    recommendation: str       # "Tighten entry criteria for next trade"
    lessons_learned: str      # "SL ini terjadi karena sinyal lemah (SMC 55%) di regime uncertain"
    timestamp: float          # Unix timestamp saat analysis


class AIProvider:
    """
    Multi-provider LLM analyzer untuk macro context enrichment.

    Fase 1 (active sekarang):
    - Enrichment Telegram notification saja
    - Zero impact ke keputusan trading
    - Cost-optimized: cache + async

    Fase 2 (future):
    - Macro sentiment modifier ke DynamicConfidenceManager
    - Cached setiap 15 menit per candle M15
    """

    # Provider-specific config
    PROVIDERS = {
        "zai": {
            "base_url": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
            "auth_header": "Authorization",
            "auth_format": "Bearer {}",
            "default_model": "glm-4",
            "library": None,  # Uses httpx
        },
        "deepseek": {
            "base_url": "https://api.deepseek.com/chat/completions",
            "auth_header": "Authorization",
            "auth_format": "Bearer {}",
            "default_model": "deepseek-chat",
            "library": None,  # Uses httpx
        },
        "openrouter": {
            "base_url": "https://openrouter.ai/api/v1/chat/completions",
            "auth_header": "Authorization",
            "auth_format": "Bearer {}",
            "default_model": "deepseek/deepseek-chat",
            "library": None,  # Uses httpx
        },
        "openai": {
            "base_url": "https://api.openai.com/v1/chat/completions",
            "auth_header": "Authorization",
            "auth_format": "Bearer {}",
            "default_model": "gpt-4o-mini",
            "library": "openai",
        },
        "anthropic": {
            "base_url": None,  # Uses native SDK
            "auth_header": None,
            "auth_format": None,
            "default_model": "claude-haiku-4-5-20251001",
            "library": "anthropic",
        },
    }

    def __init__(
        self,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        cache_duration_minutes: int = 15,
        timeout_seconds: int = 5,
    ):
        """
        Initialize AI provider (multi-provider support).

        Args:
            provider: Provider name ('zai', 'deepseek', 'openrouter', 'openai', 'anthropic')
            api_key: API key for provider (default from env)
            model: Model to use (default from provider)
            cache_duration_minutes: Cache macro context response untuk X menit
            timeout_seconds: API call timeout (safety)
        """
        self.enabled = False
        self.provider_name = (provider or os.getenv("AI_PROVIDER", "")).lower()
        self.api_key = api_key or os.getenv("AI_API_KEY")
        self.cache_duration = timedelta(minutes=cache_duration_minutes)
        self.timeout = timeout_seconds

        self._client: Optional[Any] = None
        self._cache: Dict[str, MacroContext] = {}
        self._cache_timestamps: Dict[str, float] = {}

        # Validate provider
        if not self.provider_name or self.provider_name not in self.PROVIDERS:
            logger.info(
                f"AI_PROVIDER not set or invalid ({self.provider_name}). "
                f"Set AI_PROVIDER=[zai|deepseek|openrouter|openai|anthropic] in .env"
            )
            return

        if not self.api_key:
            logger.info(f"AI_API_KEY not set — {self.provider_name} enrichment disabled")
            return

        provider_config = self.PROVIDERS[self.provider_name]
        self.model = model or os.getenv("AI_MODEL") or provider_config["default_model"]

        # Initialize provider-specific client
        try:
            if self.provider_name == "anthropic":
                if not ANTHROPIC_AVAILABLE:
                    logger.error("anthropic SDK not installed — install: pip install anthropic")
                    return
                self._client = Anthropic(api_key=self.api_key)
            else:
                # HTTP-based providers (Z.AI, DeepSeek, OpenRouter, OpenAI)
                if not HTTPX_AVAILABLE:
                    logger.error("httpx not installed — install: pip install httpx")
                    return
                self._client = httpx.AsyncClient(timeout=self.timeout)
                self._provider_config = provider_config

            self.enabled = True
            logger.info(f"AI Provider initialized: {self.provider_name}/{self.model} (Fase 1: enrichment-only)")
        except Exception as e:
            logger.error(f"Failed to initialize AI Provider ({self.provider_name}): {e}")

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache entry is still valid."""
        if cache_key not in self._cache_timestamps:
            return False
        age = time.time() - self._cache_timestamps[cache_key]
        return age < self.cache_duration.total_seconds()

    async def analyze_macro_context(
        self,
        news_headline: str = "",
        economic_events: str = "",
        market_narrative: str = "",
    ) -> MacroContext:
        """
        Analyze macro context from news/events (async, non-blocking).

        Args:
            news_headline: Recent top news untuk gold/USD
            economic_events: Jadwal event ekonomi hari ini (NFP, FOMC, dll)
            market_narrative: Konteks pasar saat ini (trend, volatility, dll)

        Returns:
            MacroContext dengan sentiment + reasoning
        """
        if not self.enabled or not self._client:
            return self._fallback_neutral_context()

        # Build cache key
        cache_key = f"macro_{hash((news_headline, economic_events, market_narrative))}"

        # Check cache
        if self._is_cache_valid(cache_key):
            logger.debug(f"Cache hit: {cache_key}")
            return self._cache[cache_key]

        # Call LLM async dengan timeout
        try:
            result = await asyncio.wait_for(
                self._call_llm_async(news_headline, economic_events, market_narrative),
                timeout=self.timeout,
            )
            self._cache[cache_key] = result
            self._cache_timestamps[cache_key] = time.time()
            return result
        except asyncio.TimeoutError:
            logger.warning(f"AI Provider timeout ({self.timeout}s) — using neutral fallback")
            return self._fallback_neutral_context()
        except Exception as e:
            logger.warning(f"AI Provider error: {e} — using neutral fallback")
            return self._fallback_neutral_context()

    async def _call_llm_async(
        self,
        news_headline: str,
        economic_events: str,
        market_narrative: str,
    ) -> MacroContext:
        """Call LLM async (runs in thread pool, non-blocking)."""
        if self.provider_name == "anthropic":
            # Anthropic uses async via executor
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                self._call_anthropic_sync,
                news_headline,
                economic_events,
                market_narrative,
            )
        else:
            # HTTP-based providers (Z.AI, DeepSeek, OpenRouter, OpenAI)
            return await self._call_http_async(news_headline, economic_events, market_narrative)

    def _call_anthropic_sync(
        self,
        news_headline: str,
        economic_events: str,
        market_narrative: str,
    ) -> MacroContext:
        """Call Anthropic API synchronously (runs in thread pool)."""
        if not self._client:
            return self._fallback_neutral_context()

        context_lines = []
        if news_headline:
            context_lines.append(f"Recent news: {news_headline}")
        if economic_events:
            context_lines.append(f"Today's economic events: {economic_events}")
        if market_narrative:
            context_lines.append(f"Market context: {market_narrative}")

        context_str = "\n".join(context_lines) if context_lines else "No specific context provided"

        prompt = f"""Analyze macro context for XAUUSD (gold) trading. Be concise and decisive.

{context_str}

Respond in JSON format (single line, no markdown):
{{"sentiment": <float -1.0 to 1.0>, "reasoning": "<1-2 sentence>", "news_summary": "<1 sentence>", "confidence": <float 0.0 to 1.0>}}"""

        try:
            response = self._client.messages.create(
                model=self.model,
                max_tokens=150,
                messages=[{"role": "user", "content": prompt}],
            )
            return self._parse_json_response(response.content[0].text)
        except Exception as e:
            logger.warning(f"Anthropic call failed: {e}")
            return self._fallback_neutral_context()

    async def _call_http_async(
        self,
        news_headline: str,
        economic_events: str,
        market_narrative: str,
    ) -> MacroContext:
        """Call HTTP-based providers (Z.AI, DeepSeek, OpenRouter, OpenAI)."""
        if not self._client or not isinstance(self._client, httpx.AsyncClient):
            return self._fallback_neutral_context()

        context_lines = []
        if news_headline:
            context_lines.append(f"Recent news: {news_headline}")
        if economic_events:
            context_lines.append(f"Today's economic events: {economic_events}")
        if market_narrative:
            context_lines.append(f"Market context: {market_narrative}")

        context_str = "\n".join(context_lines) if context_lines else "No specific context provided"

        prompt = f"""Analyze macro context for XAUUSD (gold) trading. Be concise and decisive.

{context_str}

Respond in JSON format (single line, no markdown):
{{"sentiment": <float -1.0 to 1.0>, "reasoning": "<1-2 sentence>", "news_summary": "<1 sentence>", "confidence": <float 0.0 to 1.0>}}"""

        try:
            config = self._provider_config
            headers = {
                "Content-Type": "application/json",
                config["auth_header"]: config["auth_format"].format(self.api_key),
            }

            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 150,
            }

            response = await self._client.post(
                config["base_url"],
                json=payload,
                headers=headers,
            )

            if response.status_code == 200:
                data = response.json()
                # Handle different response formats
                if "choices" in data:  # OpenAI-compatible format
                    text = data["choices"][0]["message"]["content"]
                    return self._parse_json_response(text)
                else:
                    logger.warning(f"Unexpected response format from {self.provider_name}")
                    return self._fallback_neutral_context()
            else:
                logger.warning(f"API error {response.status_code}: {response.text}")
                return self._fallback_neutral_context()

        except Exception as e:
            logger.warning(f"HTTP call failed: {e}")
            return self._fallback_neutral_context()

    def _parse_json_response(self, text: str) -> MacroContext:
        """Parse JSON response from LLM."""
        try:
            text = text.strip()
            # Extract JSON if wrapped in markdown code blocks
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()
            data = json.loads(text)
            return MacroContext(
                sentiment=float(data.get("sentiment", 0.0)),
                reasoning=str(data.get("reasoning", "No analysis")),
                news_summary=str(data.get("news_summary", "N/A")),
                confidence=float(data.get("confidence", 0.5)),
                timestamp=time.time(),
            )
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning(f"Failed to parse LLM response: {e}")
            return self._fallback_neutral_context()

    def _fallback_neutral_context(self) -> MacroContext:
        """Return neutral fallback context when LLM unavailable."""
        return MacroContext(
            sentiment=0.0,
            reasoning="AI Provider unavailable — neutral sentiment",
            news_summary="N/A",
            confidence=0.0,
            timestamp=time.time(),
        )

    async def enrich_trade_notification(
        self,
        signal_reason: str,  # "SMC-ONLY: FVG+BOS | ML BOOST: BUY (72%)"
        smc_confidence: float,  # SMC confidence level
        macro_context: Optional[MacroContext] = None,  # dari analyze_macro_context()
    ) -> TradeRichContext:
        """
        Enrich trade notification dengan narasi makro + combined insight.

        Args:
            signal_reason: Deskripsi SMC/ML signal
            smc_confidence: Confidence level signal
            macro_context: Macro context dari analyze_macro_context()

        Returns:
            TradeRichContext dengan naratif enriched untuk Telegram
        """
        if macro_context is None:
            macro_context = self._fallback_neutral_context()

        # Trade reasoning (dari signal)
        trade_reasoning = f"{signal_reason} (confidence: {smc_confidence:.0%})"

        # Macro reasoning (dari LLM)
        macro_reasoning = macro_context.reasoning
        if macro_context.confidence < 0.3:
            macro_reasoning += " [low confidence]"

        # Combined insight (synthesis)
        if macro_context.sentiment > 0.3:
            alignment = "aligned with" if smc_confidence > 0.65 else "opposed to"
            combined_insight = (
                f"Signal {alignment} bullish macro sentiment "
                f"({macro_context.news_summary})"
            )
        elif macro_context.sentiment < -0.3:
            alignment = "aligned with" if smc_confidence < 0.50 else "opposed to"
            combined_insight = (
                f"Signal {alignment} bearish macro sentiment "
                f"({macro_context.news_summary})"
            )
        else:
            combined_insight = f"Neutral macro backdrop: {macro_context.news_summary}"

        return TradeRichContext(
            trade_reasoning=trade_reasoning,
            macro_reasoning=macro_reasoning,
            combined_insight=combined_insight,
        )

    async def analyze_sl_event(
        self,
        entry_price: float,
        sl_price: float,
        exit_price: float,
        profit_usd: float,
        profit_pips: float,
        duration_minutes: int,
        session: str,
        regime: str,
        smc_confidence: float,
        ml_confidence: float,
        smc_reason: str,
    ) -> SLAnalysis:
        """
        Analyze why a Stop Loss was triggered (Lapis 3 — AI SL Analysis).

        Sends SL context to LLM for narrative analysis. Output is used for:
        1. Telegram notification enrichment (informational)
        2. Optional: confidence_modifier for next trade (if SL_ANALYSIS_IMPACT_ENABLED=true)

        Args:
            entry_price: Order entry price
            sl_price: Stop loss level set
            exit_price: Actual exit price (where SL hit)
            profit_usd: Profit/loss in dollars
            profit_pips: Profit/loss in pips
            duration_minutes: How long trade was open
            session: Trading session (Sydney, London, NY, etc)
            regime: Market regime (TRENDING, RANGING, VOLATILE)
            smc_confidence: SMC signal confidence (0-1)
            ml_confidence: ML signal confidence (0-1)
            smc_reason: SMC signal reason (FVG, BOS, OB, etc)

        Returns:
            SLAnalysis dengan root cause, lessons learned, dan confidence_modifier
        """
        if not self.enabled or not self._client:
            return self._fallback_sl_analysis()

        # Build analysis context
        sl_distance_pips = abs(exit_price - sl_price) * 100
        breakeven = entry_price
        distance_to_breakeven = abs(exit_price - breakeven) * 100

        context = f"""
Analyze why this SL was hit. Provide root cause analysis and lessons.

Trade Context:
- Entry: ${entry_price:.2f}
- SL Level: ${sl_price:.2f} (distance: {sl_distance_pips:.1f} pips)
- Exit: ${exit_price:.2f}
- P/L: ${profit_usd:.2f} ({profit_pips:.1f} pips)
- Duration: {duration_minutes} minutes
- Session: {session}
- Regime: {regime}

Signal Quality:
- SMC: {smc_confidence:.0%} confidence ({smc_reason})
- ML: {ml_confidence:.0%} confidence

Root Cause Question:
Why did price hit SL so quickly/at that level? Was it:
1. Entry signal too weak (confidence borderline)?
2. Wrong session/regime for entry?
3. Spread/slippage too wide (entry filled badly)?
4. Unexpected market move (geopolitics, news)?
5. Over-leveraged position size vs volatility?

Respond in JSON (single line):
{{
    "root_cause": "<1 sentence diagnosis>",
    "avoidance_strategy": "<How to avoid this next time>",
    "confidence_modifier": <float -0.5 to +0.5, e.g. -0.15 to reduce confidence 15% next trade>,
    "recommendation": "<Action for next trade entry>",
    "lessons_learned": "<Brief lesson from this SL>"
}}

Be specific: reference the session, regime, signal strength, etc.
"""

        try:
            result = await asyncio.wait_for(
                self._call_sl_analysis_async(context),
                timeout=self.timeout,
            )
            return result
        except asyncio.TimeoutError:
            logger.warning(f"SL analysis timeout ({self.timeout}s) — using fallback")
            return self._fallback_sl_analysis()
        except Exception as e:
            logger.warning(f"SL analysis error: {e} — using fallback")
            return self._fallback_sl_analysis()

    async def _call_sl_analysis_async(self, context: str) -> SLAnalysis:
        """Call LLM SL analysis async."""
        if self.provider_name == "anthropic":
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                self._call_sl_analysis_sync,
                context,
            )
        else:
            return await self._call_sl_analysis_http(context)

    def _call_sl_analysis_sync(self, context: str) -> SLAnalysis:
        """Call Anthropic API synchronously."""
        if not self._client:
            return self._fallback_sl_analysis()

        try:
            response = self._client.messages.create(
                model=self.model,
                max_tokens=200,
                messages=[{"role": "user", "content": context}],
            )
            return self._parse_sl_analysis_response(response.content[0].text)
        except Exception as e:
            logger.warning(f"Anthropic SL analysis failed: {e}")
            return self._fallback_sl_analysis()

    async def _call_sl_analysis_http(self, context: str) -> SLAnalysis:
        """Call HTTP-based provider SL analysis."""
        if not self._client or not isinstance(self._client, httpx.AsyncClient):
            return self._fallback_sl_analysis()

        try:
            config = self._provider_config
            headers = {
                "Content-Type": "application/json",
                config["auth_header"]: config["auth_format"].format(self.api_key),
            }

            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": context}],
                "temperature": 0.7,
                "max_tokens": 200,
            }

            response = await self._client.post(
                config["base_url"],
                json=payload,
                headers=headers,
            )

            if response.status_code == 200:
                data = response.json()
                if "choices" in data:
                    text = data["choices"][0]["message"]["content"]
                    return self._parse_sl_analysis_response(text)

            logger.warning(f"SL analysis API error {response.status_code}")
            return self._fallback_sl_analysis()

        except Exception as e:
            logger.warning(f"SL analysis HTTP call failed: {e}")
            return self._fallback_sl_analysis()

    def _parse_sl_analysis_response(self, text: str) -> SLAnalysis:
        """Parse SL analysis JSON response."""
        try:
            text = text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()
            data = json.loads(text)

            return SLAnalysis(
                root_cause=str(data.get("root_cause", "Unknown")),
                avoidance_strategy=str(data.get("avoidance_strategy", "Tighten entry criteria")),
                confidence_modifier=float(data.get("confidence_modifier", 0.0)),
                recommendation=str(data.get("recommendation", "Review entry logic")),
                lessons_learned=str(data.get("lessons_learned", "SL analysis incomplete")),
                timestamp=time.time(),
            )
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning(f"Failed to parse SL analysis: {e}")
            return self._fallback_sl_analysis()

    def _fallback_sl_analysis(self) -> SLAnalysis:
        """Return neutral fallback SL analysis."""
        return SLAnalysis(
            root_cause="AI Provider unavailable",
            avoidance_strategy="Continue with default entry criteria",
            confidence_modifier=0.0,  # No impact if AI unavailable
            recommendation="No specific recommendation",
            lessons_learned="Unable to analyze SL event",
            timestamp=time.time(),
        )

    async def analyze_signal_async(
        self,
        signal_data: Dict[str, Any],
    ) -> str:
        """
        Analyze trading signal for validation (Phase 1+).

        Args:
            signal_data: Dict with 'prompt' and optionally 'max_tokens'

        Returns:
            LLM response string (JSON format expected)
        """
        if not self.enabled or not self._client:
            return '{"is_valid": true, "confidence_modifier": 0.0, "reasoning": "AI disabled"}'

        prompt = signal_data.get("prompt", "Validate this signal")
        max_tokens = signal_data.get("max_tokens", 200)

        try:
            result = await asyncio.wait_for(
                self._call_llm_signal_async(prompt, max_tokens),
                timeout=self.timeout,
            )
            return result
        except asyncio.TimeoutError:
            logger.warning(f"Signal validation timeout ({self.timeout}s)")
            return '{"is_valid": true, "confidence_modifier": 0.0, "reasoning": "LLM timeout"}'
        except Exception as e:
            logger.warning(f"Signal validation error: {e}")
            return '{"is_valid": true, "confidence_modifier": 0.0, "reasoning": "LLM error"}'

    async def _call_llm_signal_async(self, prompt: str, max_tokens: int) -> str:
        """Call LLM for signal validation."""
        if self.provider_name == "anthropic":
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                self._call_anthropic_signal_sync,
                prompt,
                max_tokens,
            )
        else:
            return await self._call_http_signal_async(prompt, max_tokens)

    def _call_anthropic_signal_sync(self, prompt: str, max_tokens: int) -> str:
        """Call Anthropic API for signal validation."""
        if not self._client:
            return '{"is_valid": true, "confidence_modifier": 0.0, "reasoning": "No client"}'

        try:
            response = self._client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        except Exception as e:
            logger.warning(f"Anthropic signal validation failed: {e}")
            return '{"is_valid": true, "confidence_modifier": 0.0, "reasoning": "API error"}'

    async def _call_http_signal_async(self, prompt: str, max_tokens: int) -> str:
        """Call HTTP-based LLM for signal validation."""
        if not HTTPX_AVAILABLE or not self._client:
            return '{"is_valid": true, "confidence_modifier": 0.0}'

        # Implement for HTTP providers (Z.AI, DeepSeek, etc) if needed
        # For now, return neutral fallback
        return '{"is_valid": true, "confidence_modifier": 0.0, "reasoning": "HTTP provider not configured"}'

    async def shutdown(self):
        """Graceful shutdown."""
        if isinstance(self._client, httpx.AsyncClient):
            await self._client.aclose()
        self._cache.clear()
        self._cache_timestamps.clear()


# Module-level instance (created/managed by TradingBot)
_ai_provider: Optional[AIProvider] = None


def get_ai_provider() -> Optional[AIProvider]:
    """Get global AI provider instance."""
    return _ai_provider


def init_ai_provider(**kwargs) -> Optional[AIProvider]:
    """Initialize global AI provider instance."""
    global _ai_provider
    enabled = os.getenv("AI_ENABLED", "true").lower() in ("true", "1", "yes")
    if not enabled:
        logger.info("AI Provider disabled (AI_ENABLED=false)")
        return None
    _ai_provider = AIProvider(**kwargs)
    return _ai_provider
