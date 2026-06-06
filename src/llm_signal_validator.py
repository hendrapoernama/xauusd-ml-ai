"""
LLM-Based Signal Validator for XAUBot AI
=========================================

Validates trading signals using Claude LLM to improve confidence calibration.

Architecture:
- Async validation (fire-and-forget, runs after trade execution)
- Pattern-based caching (learn which setups work best)
- Confidence modifier feedback (improve future similar signals)
- Phase 1: Monitoring only (zero impact on trading)
- Phase 2: Apply cached modifiers (+0.05 to +0.10 confidence boosts)
- Phase 3: Macro-aware validation (add sentiment context)
"""

import asyncio
import hashlib
import json
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple
from datetime import datetime, timedelta
from loguru import logger

try:
    from src.ai_provider import AIProvider
except ImportError:
    AIProvider = None


@dataclass
class SignalValidationResult:
    """Result of LLM signal validation."""
    is_valid: bool                      # True = likely profitable signal
    confidence_modifier: float          # -0.15 to +0.10 adjustment
    reasoning: str                      # "FVG + OB + trending regime"
    key_factors: List[str] = field(default_factory=list)   # ["FVG confirmed", "OB nearby"]
    warnings: List[str] = field(default_factory=list)      # ["Low spread", "Off-hours"]
    signal_pattern_hash: str = ""       # Hash of signal pattern for caching
    timestamp: float = 0.0              # When validated
    confidence_in_modifier: float = 0.0 # How confident in this modifier (0.0-1.0)

    def to_dict(self) -> Dict:
        """Convert to dictionary for logging."""
        return {
            "is_valid": self.is_valid,
            "confidence_modifier": round(self.confidence_modifier, 3),
            "reasoning": self.reasoning,
            "key_factors": self.key_factors,
            "warnings": self.warnings,
            "confidence_in_modifier": round(self.confidence_in_modifier, 2),
        }


@dataclass
class CachedValidation:
    """Cached validation result with TTL."""
    result: SignalValidationResult
    created_at: float
    hit_count: int = 0
    effectiveness_score: float = 0.0  # Track if modifier helped (0-1)


class LLMSignalValidator:
    """
    Validates trading signals using Claude LLM.

    Philosophy:
    - LLM doesn't DECIDE, it VALIDATES
    - Provides confidence modifiers for similar future signals
    - Caches results by signal pattern to reduce API calls
    - Learns from trade outcomes over time
    """

    def __init__(
        self,
        ai_provider: Optional[AIProvider] = None,
        cache_duration_minutes: int = 30,
        modifier_min: float = -0.15,
        modifier_max: float = 0.10,
        enabled: bool = True,
    ):
        """
        Initialize validator.

        Args:
            ai_provider: Anthropic AI provider instance
            cache_duration_minutes: TTL for cached validations
            modifier_min: Minimum confidence modifier (-0.15)
            modifier_max: Maximum confidence modifier (+0.10)
            enabled: Enable/disable validator
        """
        self.ai_provider = ai_provider
        self.cache_duration_seconds = cache_duration_minutes * 60
        self.modifier_min = modifier_min
        self.modifier_max = modifier_max
        self.enabled = enabled

        # Cache storage: pattern_hash → CachedValidation
        self._validation_cache: Dict[str, CachedValidation] = {}
        self._cache_timestamps: Dict[str, float] = {}

        # Outcome tracking: pattern_hash → list of (was_winning, profit)
        self._outcome_history: Dict[str, List[Tuple[bool, float]]] = {}

        # Statistics
        self._total_validations = 0
        self._cache_hits = 0
        self._validation_accuracy = 0.0
        self._modifier_effectiveness = 0.0

        logger.info(
            f"[LLM VALIDATOR] Initialized (enabled={enabled}, cache={cache_duration_minutes}min, "
            f"modifier_range=[{modifier_min:.2f}, {modifier_max:.2f}])"
        )

    def _compute_pattern_hash(
        self,
        signal_type: str,               # BUY/SELL
        smc_patterns: Tuple[bool, ...], # (fvg, ob, bos, choch)
        regime: str,                    # trending/ranging
        session: str,                   # London/NY/Asian
        confluence_count: int,          # 1-4 patterns combined
    ) -> str:
        """
        Compute pattern hash for caching.

        Same patterns → same hash → use cached validation
        Example: "BUY_FVG+OB_trending_London_2" → cached modifier
        """
        patterns_str = "_".join([str(p) for p in smc_patterns])
        pattern_key = f"{signal_type}_{patterns_str}_{regime}_{session}_{confluence_count}"
        return hashlib.md5(pattern_key.encode()).hexdigest()[:16]

    def _is_cache_valid(self, pattern_hash: str) -> bool:
        """Check if cached result is still valid (not expired)."""
        if pattern_hash not in self._cache_timestamps:
            return False

        age = datetime.now().timestamp() - self._cache_timestamps[pattern_hash]
        return age < self.cache_duration_seconds

    async def validate_signal_async(
        self,
        signal_type: str,               # "BUY" or "SELL"
        entry_price: float,
        current_price: float,
        atr: float,
        spread_pips: float,

        # SMC Patterns
        fvg_detected: bool,
        fvg_distance_atr: float,
        ob_detected: bool,
        ob_distance_atr: float,
        bos_detected: bool,
        choch_detected: bool,
        confluence_count: int,

        # Momentum
        buy_sell_ratio: float,
        momentum: float,

        # Market Context
        regime: str,                   # "trending", "ranging", "volatile"
        volatility: str,               # "low", "medium", "high"
        session: str,                  # "London", "NY", "Asian"
        time_of_day: int,              # WIB hour (0-23)
        ml_agrees: bool,               # ML signal agrees with SMC

        # Optional: confidence scores
        smc_confidence: float = 0.0,
        ml_confidence: float = 0.0,
    ) -> SignalValidationResult:
        """
        Validate signal using LLM (async, non-blocking).

        Returns:
            SignalValidationResult with confidence modifier and reasoning
        """
        if not self.enabled or self.ai_provider is None:
            # Return neutral result if disabled
            return SignalValidationResult(
                is_valid=True,
                confidence_modifier=0.0,
                reasoning="Validator disabled",
                signal_pattern_hash="",
                timestamp=datetime.now().timestamp(),
            )

        # Compute pattern hash
        pattern_hash = self._compute_pattern_hash(
            signal_type,
            (fvg_detected, ob_detected, bos_detected, choch_detected),
            regime,
            session,
            confluence_count,
        )

        # Check cache first
        if self._is_cache_valid(pattern_hash):
            cached = self._validation_cache.get(pattern_hash)
            if cached:
                cached.hit_count += 1
                self._cache_hits += 1
                logger.debug(f"[LLM CACHE HIT] Pattern: {pattern_hash}, Hit #{cached.hit_count}")
                cached.result.signal_pattern_hash = pattern_hash
                cached.result.timestamp = datetime.now().timestamp()
                return cached.result

        # Cache miss - call LLM
        self._total_validations += 1
        try:
            result = await self._call_llm_validation(
                signal_type=signal_type,
                entry_price=entry_price,
                current_price=current_price,
                atr=atr,
                spread_pips=spread_pips,
                fvg_detected=fvg_detected,
                fvg_distance_atr=fvg_distance_atr,
                ob_detected=ob_detected,
                ob_distance_atr=ob_distance_atr,
                bos_detected=bos_detected,
                choch_detected=choch_detected,
                confluence_count=confluence_count,
                buy_sell_ratio=buy_sell_ratio,
                momentum=momentum,
                regime=regime,
                volatility=volatility,
                session=session,
                time_of_day=time_of_day,
                ml_agrees=ml_agrees,
                smc_confidence=smc_confidence,
                ml_confidence=ml_confidence,
            )

            # Store in cache
            result.signal_pattern_hash = pattern_hash
            cached = CachedValidation(result=result, created_at=datetime.now().timestamp())
            self._validation_cache[pattern_hash] = cached
            self._cache_timestamps[pattern_hash] = datetime.now().timestamp()

            # Cleanup old cache entries
            self._cleanup_expired_cache()

            logger.debug(f"[LLM VALIDATION] {signal_type} - Valid: {result.is_valid}, "
                        f"Modifier: {result.confidence_modifier:+.3f}, Confidence: {result.confidence_in_modifier:.2f}")
            return result

        except asyncio.TimeoutError:
            logger.warning(f"[LLM TIMEOUT] Signal validation timed out for {signal_type}")
            return SignalValidationResult(
                is_valid=True,
                confidence_modifier=0.0,
                reasoning="LLM timeout (API unreachable)",
                signal_pattern_hash=pattern_hash,
                timestamp=datetime.now().timestamp(),
                confidence_in_modifier=0.0,
            )
        except Exception as e:
            logger.warning(f"[LLM ERROR] Signal validation failed: {e}")
            return SignalValidationResult(
                is_valid=True,
                confidence_modifier=0.0,
                reasoning=f"LLM error: {str(e)[:50]}",
                signal_pattern_hash=pattern_hash,
                timestamp=datetime.now().timestamp(),
                confidence_in_modifier=0.0,
            )

    async def _call_llm_validation(self, **kwargs) -> SignalValidationResult:
        """Call Claude LLM for signal validation."""

        # Build context string
        context = self._build_validation_context(**kwargs)

        # LLM Prompt
        prompt = f"""You are an expert gold (XAUUSD) trading signal validator.
Rate this trading signal for quality and profitability.

{context}

RESPOND WITH ONLY A SINGLE-LINE JSON (no markdown formatting):
{{"is_valid": <bool>, "confidence_modifier": <float between -0.15 and 0.10>, "reasoning": "<1-2 sentence>", "key_factors": [<list of strings>], "warnings": [<list of strings>], "confidence_in_modifier": <float 0.0-1.0>}}

Be conservative in your assessment. Only increase confidence if the setup is VERY strong."""

        # Call AI provider
        try:
            response = await asyncio.wait_for(
                self.ai_provider.analyze_signal_async(
                    signal_data={
                        "prompt": prompt,
                        "max_tokens": 200,
                    }
                ),
                timeout=5.0,  # 5 second timeout
            )

            # Parse response
            result = self._parse_validation_response(response)
            return result

        except asyncio.TimeoutError:
            raise asyncio.TimeoutError("LLM API timeout")
        except Exception as e:
            raise Exception(f"LLM API error: {e}")

    def _build_validation_context(self, **kwargs) -> str:
        """Build detailed context for LLM validation."""

        signal_type = kwargs.get("signal_type", "UNKNOWN")
        confluence_count = kwargs.get("confluence_count", 0)
        regime = kwargs.get("regime", "unknown")
        volatility = kwargs.get("volatility", "unknown")
        session = kwargs.get("session", "unknown")
        time_of_day = kwargs.get("time_of_day", 0)
        ml_agrees = kwargs.get("ml_agrees", False)
        smc_confidence = kwargs.get("smc_confidence", 0.0)
        ml_confidence = kwargs.get("ml_confidence", 0.0)
        atr = kwargs.get("atr", 0.0)
        spread_pips = kwargs.get("spread_pips", 0.0)

        fvg_detected = kwargs.get("fvg_detected", False)
        ob_detected = kwargs.get("ob_detected", False)
        bos_detected = kwargs.get("bos_detected", False)
        choch_detected = kwargs.get("choch_detected", False)

        # Build pattern description
        patterns = []
        if fvg_detected:
            patterns.append(f"FVG ({kwargs.get('fvg_distance_atr', 0):.1f} ATR)")
        if ob_detected:
            patterns.append(f"OB ({kwargs.get('ob_distance_atr', 0):.1f} ATR)")
        if bos_detected:
            patterns.append("BOS")
        if choch_detected:
            patterns.append("CHoCH")

        patterns_str = " + ".join(patterns) if patterns else "No SMC patterns"

        context = f"""SIGNAL: {signal_type}
SMC Patterns: {patterns_str} (Confluence: {confluence_count}/4)
SMC Confidence: {smc_confidence:.0%}
ML Confidence: {ml_confidence:.0%}
ML Agrees: {'Yes' if ml_agrees else 'No'}

MARKET CONDITIONS:
- Regime: {regime}
- Volatility: {volatility}
- Session: {session} ({time_of_day}:00 WIB)
- ATR: {atr:.2f}
- Spread: {spread_pips:.1f}p

HISTORICAL CONTEXT:
- Similar setups win ~{self._get_pattern_effectiveness(kwargs.get('confluence_count', 0)):.0%} of time
- Market is {'trending' if regime == 'trending' else 'not trending'}
- ML and SMC agreement: {'Strong' if ml_agrees else 'Weak'}"""

        return context

    def _parse_validation_response(self, response: str) -> SignalValidationResult:
        """Parse LLM JSON response."""
        try:
            # Extract JSON from response
            json_str = response.strip()
            if json_str.startswith("```"):
                json_str = json_str.split("```")[1].strip()
                if json_str.startswith("json"):
                    json_str = json_str[4:].strip()

            data = json.loads(json_str)

            # Clamp confidence modifier to bounds
            modifier = float(data.get("confidence_modifier", 0.0))
            modifier = max(self.modifier_min, min(self.modifier_max, modifier))

            return SignalValidationResult(
                is_valid=bool(data.get("is_valid", True)),
                confidence_modifier=modifier,
                reasoning=str(data.get("reasoning", "")),
                key_factors=data.get("key_factors", []),
                warnings=data.get("warnings", []),
                timestamp=datetime.now().timestamp(),
                confidence_in_modifier=float(data.get("confidence_in_modifier", 0.5)),
            )
        except json.JSONDecodeError as e:
            logger.warning(f"[LLM PARSE ERROR] Failed to parse JSON: {response[:100]}")
            return SignalValidationResult(
                is_valid=True,
                confidence_modifier=0.0,
                reasoning="Failed to parse LLM response",
                timestamp=datetime.now().timestamp(),
            )

    def get_confidence_modifier(self, pattern_hash: str) -> float:
        """Get cached confidence modifier for pattern (Phase 2+)."""
        if not self._is_cache_valid(pattern_hash):
            return 0.0

        cached = self._validation_cache.get(pattern_hash)
        if cached:
            return cached.result.confidence_modifier
        return 0.0

    def record_outcome(
        self,
        pattern_hash: str,
        was_winning: bool,
        profit: float,
        modifier_applied: float = 0.0,
    ) -> None:
        """Record trade outcome to track modifier effectiveness."""
        if pattern_hash not in self._outcome_history:
            self._outcome_history[pattern_hash] = []

        self._outcome_history[pattern_hash].append((was_winning, profit))

        # Update cached result's effectiveness score
        if pattern_hash in self._validation_cache:
            cached = self._validation_cache[pattern_hash]
            # Effectiveness: did modifier help? (rough estimate)
            if was_winning and modifier_applied > 0:
                cached.effectiveness_score = 1.0  # Modifier helped
            elif not was_winning and modifier_applied < 0:
                cached.effectiveness_score = 1.0  # Modifier helped
            else:
                cached.effectiveness_score = 0.0  # Modifier didn't help

    def get_statistics(self) -> Dict:
        """Get validation statistics."""
        total = max(1, self._total_validations)
        hit_rate = self._cache_hits / total if total > 0 else 0

        # Calculate validation accuracy
        valid_signals_winning = 0
        valid_signals_total = 0
        for outcomes in self._outcome_history.values():
            for was_winning, _ in outcomes:
                valid_signals_total += 1
                if was_winning:
                    valid_signals_winning += 1

        accuracy = (valid_signals_winning / valid_signals_total * 100) if valid_signals_total > 0 else 0

        return {
            "total_validations": self._total_validations,
            "cache_hits": self._cache_hits,
            "cache_hit_rate": f"{hit_rate * 100:.1f}%",
            "validation_accuracy": f"{accuracy:.1f}%",
            "cached_patterns": len(self._validation_cache),
            "pattern_outcomes_tracked": len(self._outcome_history),
            "enabled": self.enabled,
        }

    def _cleanup_expired_cache(self) -> None:
        """Remove expired cache entries (keep only 1000 max)."""
        now = datetime.now().timestamp()

        # Remove expired entries
        expired = [
            k for k, t in self._cache_timestamps.items()
            if now - t > self.cache_duration_seconds
        ]
        for k in expired:
            del self._validation_cache[k]
            del self._cache_timestamps[k]

        # Keep only 1000 most recent entries
        if len(self._validation_cache) > 1000:
            # Sort by timestamp and keep newest 1000
            sorted_patterns = sorted(
                self._cache_timestamps.items(),
                key=lambda x: x[1],
                reverse=True
            )[:1000]
            keep_patterns = {k for k, _ in sorted_patterns}

            to_delete = set(self._validation_cache.keys()) - keep_patterns
            for k in to_delete:
                del self._validation_cache[k]
                del self._cache_timestamps[k]

    def _get_pattern_effectiveness(self, confluence_count: int) -> float:
        """Estimate pattern effectiveness based on historical data."""
        # Placeholder: will be calculated from outcomes after Phase 1
        effectiveness_map = {
            1: 0.45,
            2: 0.55,
            3: 0.65,
            4: 0.75,
        }
        return effectiveness_map.get(confluence_count, 0.50)
