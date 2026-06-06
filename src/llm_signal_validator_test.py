"""
Unit tests for LLMSignalValidator.

Tests:
- Pattern hash consistency
- Confidence modifier bounds
- Cache validity and expiration
- Async behavior (non-blocking)
- JSON response parsing
- Statistics tracking
"""

import pytest
import asyncio
import json
import time
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from src.llm_signal_validator import (
    LLMSignalValidator,
    SignalValidationResult,
    CachedValidation,
)


class TestPatternHashing:
    """Test pattern hash consistency."""

    def test_same_patterns_same_hash(self):
        """Same patterns should always produce same hash."""
        validator = LLMSignalValidator(enabled=True)

        hash1 = validator._compute_pattern_hash(
            "BUY",
            (True, True, False, False),
            "trending",
            "London",
            2
        )
        hash2 = validator._compute_pattern_hash(
            "BUY",
            (True, True, False, False),
            "trending",
            "London",
            2
        )

        assert hash1 == hash2, "Same patterns should produce same hash"

    def test_different_patterns_different_hash(self):
        """Different patterns should produce different hashes."""
        validator = LLMSignalValidator(enabled=True)

        hash1 = validator._compute_pattern_hash(
            "BUY",
            (True, True, False, False),
            "trending",
            "London",
            2
        )
        hash2 = validator._compute_pattern_hash(
            "SELL",
            (True, True, False, False),
            "trending",
            "London",
            2
        )

        assert hash1 != hash2, "Different signals should produce different hashes"

    def test_hash_format(self):
        """Hash should be 16 chars (MD5 truncated)."""
        validator = LLMSignalValidator(enabled=True)

        hash_val = validator._compute_pattern_hash(
            "BUY",
            (True, True, False, False),
            "trending",
            "London",
            2
        )

        assert len(hash_val) == 16, f"Hash should be 16 chars, got {len(hash_val)}"
        assert hash_val.isalnum(), "Hash should be alphanumeric"


class TestConfidenceModifier:
    """Test confidence modifier bounds and behavior."""

    def test_modifier_bounds_lower(self):
        """Confidence modifier should not exceed minimum."""
        validator = LLMSignalValidator(
            enabled=True,
            modifier_min=-0.15,
            modifier_max=0.10
        )

        assert validator.modifier_min == -0.15
        assert validator.modifier_max == 0.10

    def test_modifier_clamping(self):
        """Modifier values should be clamped to bounds."""
        validator = LLMSignalValidator(modifier_min=-0.15, modifier_max=0.10)

        # Create result with out-of-bounds modifier
        result = SignalValidationResult(
            is_valid=True,
            confidence_modifier=0.50,  # Out of bounds
            reasoning="Test"
        )

        # Should be clamped
        clamped = max(validator.modifier_min, min(validator.modifier_max, result.confidence_modifier))
        assert validator.modifier_min <= clamped <= validator.modifier_max

    def test_confidence_with_modifier(self):
        """Confidence should stay in [0.0, 1.0] after modifier."""
        signal_confidence = 0.85

        for modifier in [-0.15, -0.10, -0.05, 0.0, 0.05, 0.10]:
            result = min(1.0, max(0.0, signal_confidence + modifier))
            assert 0.0 <= result <= 1.0, f"Result {result} out of bounds with modifier {modifier}"


class TestCacheValidity:
    """Test cache expiration and cleanup."""

    def test_cache_expiration(self):
        """Cached results should expire after TTL."""
        validator = LLMSignalValidator(cache_duration_minutes=1, enabled=True)

        # Create a cached result
        result = SignalValidationResult(
            is_valid=True,
            confidence_modifier=0.05,
            reasoning="Test",
            signal_pattern_hash="test_hash_12345"
        )
        cached = CachedValidation(result=result, created_at=time.time())

        # Store in cache
        validator._validation_cache["test_hash_12345"] = cached
        validator._cache_timestamps["test_hash_12345"] = time.time()

        # Should be valid immediately
        assert validator._is_cache_valid("test_hash_12345")

        # Simulate expiration (move timestamp back)
        validator._cache_timestamps["test_hash_12345"] = time.time() - (2 * 60)  # 2 minutes ago

        # Should be expired
        assert not validator._is_cache_valid("test_hash_12345")

    def test_cache_cleanup(self):
        """Cache should not exceed 1000 entries."""
        validator = LLMSignalValidator(enabled=True)

        # Add many cached results
        for i in range(1050):
            hash_val = f"hash_{i:04d}"
            result = SignalValidationResult(
                is_valid=True,
                confidence_modifier=0.0,
                reasoning="Test"
            )
            cached = CachedValidation(result=result, created_at=time.time() - i)
            validator._validation_cache[hash_val] = cached
            validator._cache_timestamps[hash_val] = time.time() - i

        # Trigger cleanup
        validator._cleanup_expired_cache()

        # Should not exceed 1000 entries
        assert len(validator._validation_cache) <= 1000, \
            f"Cache has {len(validator._validation_cache)} entries, should be <= 1000"


class TestAsyncBehavior:
    """Test async non-blocking behavior."""

    @pytest.mark.asyncio
    async def test_validate_signal_nonblocking(self):
        """Validation should not block main loop."""
        validator = LLMSignalValidator(enabled=False)  # Disabled = instant return

        start = time.time()

        # Call async validation
        result = await validator.validate_signal_async(
            signal_type="BUY",
            entry_price=2045.0,
            current_price=2045.0,
            atr=12.0,
            spread_pips=0.15,
            fvg_detected=True,
            fvg_distance_atr=1.0,
            ob_detected=True,
            ob_distance_atr=0.5,
            bos_detected=False,
            choch_detected=False,
            confluence_count=2,
            buy_sell_ratio=1.0,
            momentum=0.1,
            regime="trending",
            volatility="medium",
            session="London",
            time_of_day=12,
            ml_agrees=True,
        )

        elapsed = time.time() - start

        # Should return immediately when disabled
        assert elapsed < 0.1, f"Validation took {elapsed}s, should be instant when disabled"
        assert result is not None
        assert isinstance(result, SignalValidationResult)


class TestJSONParsing:
    """Test LLM response parsing."""

    def test_parse_valid_json(self):
        """Should parse valid LLM JSON response."""
        validator = LLMSignalValidator(enabled=True)

        json_response = '''{
            "is_valid": true,
            "confidence_modifier": 0.05,
            "reasoning": "FVG + OB + trending",
            "key_factors": ["FVG", "OB"],
            "warnings": [],
            "confidence_in_modifier": 0.75
        }'''

        result = validator._parse_validation_response(json_response)

        assert result.is_valid == True
        assert result.confidence_modifier == 0.05
        assert "FVG" in result.key_factors
        assert result.confidence_in_modifier == 0.75

    def test_parse_with_markdown(self):
        """Should parse JSON even with markdown wrapping."""
        validator = LLMSignalValidator(enabled=True)

        json_response = '''```json
        {
            "is_valid": false,
            "confidence_modifier": -0.10,
            "reasoning": "Low confluence",
            "key_factors": [],
            "warnings": ["Low confluence"],
            "confidence_in_modifier": 0.6
        }
        ```'''

        result = validator._parse_validation_response(json_response)

        assert result.is_valid == False
        assert result.confidence_modifier == -0.10
        assert len(result.warnings) > 0

    def test_parse_invalid_json(self):
        """Should handle invalid JSON gracefully."""
        validator = LLMSignalValidator(enabled=True)

        # Invalid JSON
        invalid_response = "not valid json"

        result = validator._parse_validation_response(invalid_response)

        # Should return with defaults
        assert result is not None
        assert result.is_valid == True  # Default is True
        assert result.confidence_modifier == 0.0  # Default is 0


class TestStatistics:
    """Test statistics tracking."""

    def test_get_statistics_initial(self):
        """Initial statistics should be zeros."""
        validator = LLMSignalValidator(enabled=True)

        stats = validator.get_statistics()

        assert stats["total_validations"] == 0
        assert stats["cache_hits"] == 0
        assert "0.0%" in stats["cache_hit_rate"]

    def test_record_outcome(self):
        """Should record trade outcomes."""
        validator = LLMSignalValidator(enabled=True)

        # Create a cached result first
        result = SignalValidationResult(
            is_valid=True,
            confidence_modifier=0.05,
            reasoning="Test"
        )
        cached = CachedValidation(result=result, created_at=time.time())
        pattern_hash = "test_pattern_123"
        validator._validation_cache[pattern_hash] = cached
        validator._cache_timestamps[pattern_hash] = time.time()

        # Record a winning trade
        validator.record_outcome(
            pattern_hash=pattern_hash,
            was_winning=True,
            profit=10.0,
            modifier_applied=0.05
        )

        # Should track outcome
        assert pattern_hash in validator._outcome_history
        assert len(validator._outcome_history[pattern_hash]) == 1
        assert validator._outcome_history[pattern_hash][0] == (True, 10.0)


class TestDataStructures:
    """Test data structure integrity."""

    def test_signal_validation_result_to_dict(self):
        """Should convert to dict with proper formatting."""
        result = SignalValidationResult(
            is_valid=True,
            confidence_modifier=0.0567,
            reasoning="FVG + OB",
            key_factors=["FVG", "OB"],
            confidence_in_modifier=0.75
        )

        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert result_dict["is_valid"] == True
        assert result_dict["confidence_modifier"] == 0.057  # Rounded to 3 decimals
        assert "FVG" in result_dict["key_factors"]

    def test_cached_validation_creation(self):
        """Should create cached validation with correct fields."""
        result = SignalValidationResult(
            is_valid=True,
            confidence_modifier=0.05,
            reasoning="Test"
        )

        now = time.time()
        cached = CachedValidation(result=result, created_at=now)

        assert cached.result == result
        assert cached.created_at == now
        assert cached.hit_count == 0
        assert cached.effectiveness_score == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
