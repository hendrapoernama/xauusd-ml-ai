"""
Position Analysis Module
========================
Analyze why no positions opened in the last N days using ML-driven insights.

Analyzes:
1. Signal generation (how many signals were generated)
2. Execution rate (what % of signals became trades)
3. Blocking factors (why signals weren't executed)
4. Market patterns (regime, volatility, session effects)
5. Threshold analysis (is ML threshold too high?)
"""

import csv
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from zoneinfo import ZoneInfo
from dataclasses import dataclass

from loguru import logger

WIB = ZoneInfo("Asia/Jakarta")


@dataclass
class SignalRecord:
    """Record of a signal."""
    timestamp: str
    signal_type: str  # BUY, SELL, NONE
    signal_source: str  # SMC, ML, COMBINED
    confidence: float
    ml_confidence: float
    smc_confidence: float
    market_score: int
    regime: str
    session: str
    volatility: str
    trade_executed: bool
    execution_reason: str


@dataclass
class AnalysisResult:
    """Result of position analysis."""
    analysis_date: str
    days_analyzed: int
    total_signals: int
    total_trades: int
    execution_rate: float
    top_blocking_reasons: List[Tuple[str, int]]
    signals_by_type: Dict[str, int]
    trades_by_type: Dict[str, int]
    regime_distribution: Dict[str, int]
    market_quality_breakdown: Dict[str, int]
    avg_signal_confidence: float
    win_rate: Optional[float]
    total_profit: Optional[float]
    key_insights: List[str]


class PositionAnalyzer:
    """Analyze position data and signals from trade logs."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.trade_logs_dir = self.data_dir / "trade_logs"
        self.signals_dir = self.trade_logs_dir / "signals"
        self.trades_dir = self.trade_logs_dir / "trades"

    def analyze_no_positions(self, days: int = 3) -> AnalysisResult:
        """
        Analyze why no positions opened in the last N days.
        Returns detailed analysis with blocking factors.
        """
        logger.info(f"Analyzing position data for last {days} days")

        signals = self._load_signals_last_days(days)
        trades = self._load_trades_last_days(days)

        analysis = AnalysisResult(
            analysis_date=datetime.now(WIB).strftime("%Y-%m-%d"),
            days_analyzed=days,
            total_signals=len(signals),
            total_trades=len(trades),
            execution_rate=(len(trades) / len(signals) * 100) if signals else 0,
            top_blocking_reasons=[],
            signals_by_type={},
            trades_by_type={},
            regime_distribution={},
            market_quality_breakdown={},
            avg_signal_confidence=0,
            win_rate=None,
            total_profit=None,
            key_insights=[],
        )

        if not signals:
            analysis.key_insights.append(
                "⚠️ No signals generated in the last {days} days. Market may be in ranging/low-conviction regime."
            )
            return analysis

        # Analyze signals
        analysis.signals_by_type = self._analyze_signal_types(signals)
        analysis.regime_distribution = self._analyze_regimes(signals)
        analysis.market_quality_breakdown = self._analyze_market_quality(signals)
        analysis.avg_signal_confidence = sum(
            s.confidence for s in signals
        ) / len(signals)

        # Analyze blocking factors
        blocking_reasons = self._analyze_blocking_factors(signals)
        analysis.top_blocking_reasons = sorted(
            blocking_reasons.items(), key=lambda x: x[1], reverse=True
        )

        # Analyze trades (if any)
        if trades:
            analysis.trades_by_type = self._analyze_trade_types(trades)
            analysis.win_rate = self._calculate_win_rate(trades)
            analysis.total_profit = self._calculate_total_profit(trades)

        # Generate insights
        analysis.key_insights = self._generate_insights(analysis, signals)

        logger.info(
            f"Analysis complete: {analysis.total_signals} signals, "
            f"{analysis.total_trades} trades, "
            f"{analysis.execution_rate:.1f}% execution rate"
        )
        return analysis

    def _load_signals_last_days(self, days: int) -> List[SignalRecord]:
        """Load signal records from CSV files for last N days."""
        signals = []

        # Get current and recent month files
        now = datetime.now(WIB)
        for i in range(days):
            check_date = now - timedelta(days=i)
            filename = f"signals_{check_date.strftime('%Y_%m')}.csv"
            filepath = self.signals_dir / filename

            if filepath.exists():
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            # Parse timestamp and check if within range
                            try:
                                ts = datetime.fromisoformat(row.get("timestamp", ""))
                                ts_wib = ts.astimezone(WIB)
                                if ts_wib > (now - timedelta(days=days)):
                                    signal = SignalRecord(
                                        timestamp=row.get("timestamp", ""),
                                        signal_type=row.get("signal_type", "NONE"),
                                        signal_source=row.get("signal_source", "UNKNOWN"),
                                        confidence=float(
                                            row.get("confidence", 0)
                                        ),
                                        ml_confidence=float(
                                            row.get("ml_confidence", 0)
                                        ),
                                        smc_confidence=float(
                                            row.get("smc_confidence", 0)
                                        ),
                                        market_score=int(
                                            row.get("market_score", 0)
                                        ),
                                        regime=row.get("regime", "unknown"),
                                        session=row.get("session", "unknown"),
                                        volatility=row.get("volatility", "unknown"),
                                        trade_executed=(
                                            row.get("trade_executed", "False")
                                            == "True"
                                        ),
                                        execution_reason=row.get(
                                            "execution_reason", "unknown"
                                        ),
                                    )
                                    signals.append(signal)
                            except ValueError:
                                continue
                except Exception as e:
                    logger.warning(f"Error reading {filepath}: {e}")

        return signals

    def _load_trades_last_days(self, days: int) -> List[Dict]:
        """Load trade records from CSV files for last N days."""
        trades = []

        # Get current and recent month files
        now = datetime.now(WIB)
        for i in range(days):
            check_date = now - timedelta(days=i)
            filename = f"trades_{check_date.strftime('%Y_%m')}.csv"
            filepath = self.trades_dir / filename

            if filepath.exists():
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            # Parse open_time and check if within range
                            try:
                                ts = datetime.fromisoformat(row.get("open_time", ""))
                                ts_wib = ts.astimezone(WIB)
                                if ts_wib > (now - timedelta(days=days)):
                                    trades.append(row)
                            except ValueError:
                                continue
                except Exception as e:
                    logger.warning(f"Error reading {filepath}: {e}")

        return trades

    def _analyze_signal_types(self, signals: List[SignalRecord]) -> Dict[str, int]:
        """Count signals by type."""
        counts = {"BUY": 0, "SELL": 0, "NONE": 0}
        for signal in signals:
            counts[signal.signal_type] = counts.get(signal.signal_type, 0) + 1
        return counts

    def _analyze_regimes(self, signals: List[SignalRecord]) -> Dict[str, int]:
        """Analyze market regime distribution."""
        regimes = {}
        for signal in signals:
            regime = signal.regime
            regimes[regime] = regimes.get(regime, 0) + 1
        return regimes

    def _analyze_market_quality(self, signals: List[SignalRecord]) -> Dict[str, int]:
        """Analyze market quality distribution."""
        quality_map = {}
        for signal in signals:
            # Classify quality based on market_score
            score = signal.market_score
            if score >= 70:
                quality = "EXCELLENT"
            elif score >= 60:
                quality = "GOOD"
            elif score >= 50:
                quality = "MODERATE"
            else:
                quality = "POOR"
            quality_map[quality] = quality_map.get(quality, 0) + 1
        return quality_map

    def _analyze_blocking_factors(self, signals: List[SignalRecord]) -> Dict[str, int]:
        """Analyze why signals weren't executed."""
        blocking_reasons = {}
        for signal in signals:
            if not signal.trade_executed:
                reason = signal.execution_reason or "unknown"
                blocking_reasons[reason] = blocking_reasons.get(reason, 0) + 1
        return blocking_reasons

    def _analyze_trade_types(self, trades: List[Dict]) -> Dict[str, int]:
        """Count trades by type."""
        counts = {}
        for trade in trades:
            direction = trade.get("direction", "unknown")
            counts[direction] = counts.get(direction, 0) + 1
        return counts

    def _calculate_win_rate(self, trades: List[Dict]) -> float:
        """Calculate win rate from trades."""
        if not trades:
            return 0
        wins = sum(1 for t in trades if float(t.get("profit_usd", 0)) > 0)
        return (wins / len(trades)) * 100

    def _calculate_total_profit(self, trades: List[Dict]) -> float:
        """Calculate total profit from trades."""
        return sum(float(t.get("profit_usd", 0)) for t in trades)

    def _generate_insights(
        self, analysis: AnalysisResult, signals: List[SignalRecord]
    ) -> List[str]:
        """Generate AI-driven insights based on analysis."""
        insights = []

        # Insight 1: Execution rate
        if analysis.execution_rate == 0:
            insights.append(
                "🔴 CRITICAL: 0% execution rate. "
                "Every signal is blocked. Check ML threshold and market quality filters."
            )
        elif analysis.execution_rate < 10:
            insights.append(
                f"⚠️ Very low execution: {analysis.execution_rate:.1f}%. "
                "Most signals are blocked by filters."
            )
        elif analysis.execution_rate < 30:
            insights.append(
                f"📊 Low execution rate: {analysis.execution_rate:.1f}%. "
                "Consider lowering ML threshold or relaxing market quality requirements."
            )

        # Insight 2: Blocking factors
        if analysis.top_blocking_reasons:
            top_reason, top_count = analysis.top_blocking_reasons[0]
            pct = (top_count / analysis.total_signals) * 100
            insights.append(
                f"🚫 Top blocker: {top_reason} ({pct:.1f}% of signals)"
            )

            # Specific recommendations based on blocking reason
            if "threshold" in top_reason.lower():
                insights.append(
                    "💡 Suggestion: ML threshold too high. "
                    f"Consider lowering from 0.65 to 0.60 or switch to AGGRESSIVE mode."
                )
            elif "market_score" in top_reason.lower() or "quality" in top_reason.lower():
                insights.append(
                    "💡 Suggestion: Market quality filter too strict. "
                    "Market may be ranging. Try NORMAL or AGGRESSIVE mode."
                )
            elif "position" in top_reason.lower():
                insights.append(
                    "💡 Suggestion: Max positions reached. "
                    "Close profitable positions to free up slots."
                )

        # Insight 3: Average confidence
        if analysis.avg_signal_confidence > 0:
            insights.append(
                f"📈 Avg signal confidence: {analysis.avg_signal_confidence:.0%}. "
                f"Signals are {'strong' if analysis.avg_signal_confidence > 0.65 else 'weak'}."
            )

        # Insight 4: Regime analysis
        if analysis.regime_distribution:
            dominant_regime = max(
                analysis.regime_distribution.items(), key=lambda x: x[1]
            )[0]
            insights.append(
                f"📊 Market regime: {dominant_regime}. "
                "Volatility and trend character affects entry opportunities."
            )

        # Insight 5: Win rate (if trades exist)
        if analysis.win_rate is not None:
            if analysis.win_rate >= 60:
                insights.append(
                    f"✅ Good win rate: {analysis.win_rate:.1f}%. "
                    "The trades that do execute are profitable."
                )
            elif analysis.win_rate >= 40:
                insights.append(
                    f"📊 Moderate win rate: {analysis.win_rate:.1f}%. "
                    "Consider tightening entry filters."
                )
            else:
                insights.append(
                    f"❌ Low win rate: {analysis.win_rate:.1f}%. "
                    "Check signal quality or exit strategy."
                )

        # Insight 6: No activity
        if analysis.total_signals == 0:
            insights.append(
                "🟡 No signals generated. Market may be in consolidation/no clear bias. "
                "Wait for breakout or switch to RESTRICTED mode."
            )

        # Insight 7: Total profit
        if analysis.total_profit is not None:
            if analysis.total_profit > 0:
                insights.append(
                    f"💰 Session profit: +${analysis.total_profit:.2f}. "
                    "Profitable despite low signal volume."
                )
            elif analysis.total_profit < 0:
                insights.append(
                    f"📉 Session loss: -${abs(analysis.total_profit):.2f}. "
                    "Consider lowering risk or reviewing exit strategy."
                )

        return insights


def create_analyzer() -> PositionAnalyzer:
    """Factory function to create analyzer."""
    return PositionAnalyzer()


if __name__ == "__main__":
    # Test the analyzer
    analyzer = create_analyzer()
    result = analyzer.analyze_no_positions(days=3)

    print(f"=== Position Analysis ({result.analysis_date}) ===")
    print(f"Days analyzed: {result.days_analyzed}")
    print(f"Total signals: {result.total_signals}")
    print(f"Total trades: {result.total_trades}")
    print(f"Execution rate: {result.execution_rate:.1f}%")
    print(f"\nSignals by type: {result.signals_by_type}")
    print(f"Top blocking reasons: {result.top_blocking_reasons}")
    print(f"Regime distribution: {result.regime_distribution}")
    print(f"Market quality: {result.market_quality_breakdown}")
    print(f"\nKey Insights:")
    for insight in result.key_insights:
        print(f"  {insight}")
