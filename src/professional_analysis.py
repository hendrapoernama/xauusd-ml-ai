"""
Professional Trading Analysis Module
====================================
Analyzes last N days of trading data and provides professional recommendations
for optimal trading mode and strategy for the coming week.

Features:
- 5-day detailed analysis
- Market condition assessment
- Mode recommendations with confidence levels
- Risk/reward analysis
- Trend identification
- Next week strategy suggestions
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo
from dataclasses import dataclass

from loguru import logger
from src.position_analysis import PositionAnalyzer, AnalysisResult

WIB = ZoneInfo("Asia/Jakarta")


@dataclass
class ModeRecommendation:
    """Recommended trading mode with confidence."""
    mode: str
    confidence: float  # 0-100
    reason: str
    expected_performance: str
    risk_level: str


@dataclass
class ProfessionalAnalysis:
    """Complete professional trading analysis."""
    analysis_date: str
    period_days: int
    analysis: AnalysisResult
    market_assessment: str
    key_findings: List[str]
    risk_assessment: str
    mode_recommendations: List[ModeRecommendation]
    next_week_strategy: str
    action_items: List[str]


class ProfessionalAnalyzer:
    """Professional trading analysis with mode recommendations."""

    def __init__(self):
        self.position_analyzer = PositionAnalyzer()

    def analyze_5_days(self) -> ProfessionalAnalysis:
        """Generate professional analysis for last 5 days."""
        logger.info("Starting 5-day professional analysis...")

        # Get basic analysis
        result = self.position_analyzer.analyze_no_positions(days=5)

        # Assess market conditions
        market_assessment = self._assess_market_conditions(result)

        # Identify key findings
        key_findings = self._identify_key_findings(result)

        # Assess risks
        risk_assessment = self._assess_risks(result)

        # Get mode recommendations
        mode_recommendations = self._recommend_modes(result, market_assessment)

        # Strategy for next week
        next_week_strategy = self._generate_next_week_strategy(
            result, mode_recommendations, market_assessment
        )

        # Action items
        action_items = self._generate_action_items(
            result, mode_recommendations, market_assessment
        )

        analysis = ProfessionalAnalysis(
            analysis_date=datetime.now(WIB).strftime("%Y-%m-%d"),
            period_days=5,
            analysis=result,
            market_assessment=market_assessment,
            key_findings=key_findings,
            risk_assessment=risk_assessment,
            mode_recommendations=mode_recommendations,
            next_week_strategy=next_week_strategy,
            action_items=action_items,
        )

        return analysis

    def _assess_market_conditions(self, result: AnalysisResult) -> str:
        """Assess market conditions from analysis."""
        if result.total_signals == 0:
            return "🟡 CONSOLIDATION PHASE — Market lacks clear direction. Low signal generation indicates indecision."

        execution_rate = result.execution_rate
        avg_confidence = result.avg_signal_confidence

        # Assess based on execution rate
        if execution_rate == 0:
            return "🔴 SIGNAL GENERATION PROBLEM — Signals generated but blocked. Filters too strict or threshold too high."
        elif execution_rate < 20:
            return "🟡 LOW EXECUTION — Market has signals but few are being traded. Quality filtering may be too strict."
        elif execution_rate < 50:
            return "🟠 MODERATE EXECUTION — Some trades executing but many blocked. Market quality varies."
        elif execution_rate < 80:
            return "🟢 GOOD EXECUTION — Most signals being traded. Market is active and clear."
        else:
            return "🟢 EXCELLENT EXECUTION — Almost all signals becoming trades. Market is very active and liquid."

    def _identify_key_findings(self, result: AnalysisResult) -> List[str]:
        """Identify key patterns and findings."""
        findings = []

        # Finding 1: Signal volume
        if result.total_signals == 0:
            findings.append(
                "📉 ZERO SIGNALS: Market completely consolidating. No clear trading opportunities."
            )
        elif result.total_signals < 10:
            findings.append(
                f"📊 LOW SIGNAL VOLUME: Only {result.total_signals} signals in 5 days. Market is quiet."
            )
        elif result.total_signals < 30:
            findings.append(
                f"📈 MODERATE SIGNALS: {result.total_signals} signals. Market has activity but selective."
            )
        else:
            findings.append(
                f"📈 HIGH SIGNAL VOLUME: {result.total_signals} signals. Market is active and opportunity-rich."
            )

        # Finding 2: Execution rate
        if result.execution_rate == 0 and result.total_signals > 0:
            findings.append(
                f"🚫 ZERO EXECUTION: {result.total_signals} signals generated but NONE executed. "
                "Major filtering issue — threshold or market quality filter too strict."
            )
        elif result.execution_rate > 0:
            findings.append(
                f"✅ EXECUTION RATE: {result.execution_rate:.1f}% of signals executed. "
                f"({result.total_trades} of {result.total_signals} signals became trades)"
            )

        # Finding 3: Trade quality
        if result.total_trades > 0:
            if result.win_rate is not None:
                if result.win_rate >= 70:
                    findings.append(
                        f"⭐ EXCELLENT WIN RATE: {result.win_rate:.1f}%. Trades that execute are high quality."
                    )
                elif result.win_rate >= 50:
                    findings.append(
                        f"✅ GOOD WIN RATE: {result.win_rate:.1f}%. Trading strategy is working."
                    )
                else:
                    findings.append(
                        f"⚠️ LOW WIN RATE: {result.win_rate:.1f}%. Executed trades are unprofitable."
                    )

            if result.total_profit is not None:
                if result.total_profit > 0:
                    findings.append(
                        f"💰 PROFITABLE PERIOD: +${result.total_profit:.2f} net. Positive despite low volume."
                    )
                else:
                    findings.append(
                        f"📉 LOSS PERIOD: -${abs(result.total_profit):.2f} net. Strategy underperforming."
                    )

        # Finding 4: Blocking factors
        if result.top_blocking_reasons:
            top_reason, top_count = result.top_blocking_reasons[0]
            pct = (top_count / result.total_signals * 100) if result.total_signals > 0 else 0
            findings.append(
                f"🚫 TOP BLOCKER: '{top_reason}' blocks {pct:.1f}% of signals."
            )

        # Finding 5: Market regime
        if result.regime_distribution:
            dominant_regime = max(
                result.regime_distribution.items(), key=lambda x: x[1]
            )[0]
            findings.append(
                f"📊 DOMINANT REGIME: {dominant_regime}. Market character affects signal quality."
            )

        return findings

    def _assess_risks(self, result: AnalysisResult) -> str:
        """Assess trading risks."""
        if result.total_signals == 0:
            return (
                "🟡 LOW IMMEDIATE RISK but HIGH OPPORTUNITY RISK\n"
                "  • No trades = no loss, but missing opportunity cost\n"
                "  • Risk: Waiting too long for breakout\n"
                "  • Opportunity cost: Potential profits missed"
            )

        if result.execution_rate == 0:
            return (
                "🔴 FILTERING RISK — High False Negative Risk\n"
                "  • Good signals being rejected\n"
                "  • Risk: Missing winning trades\n"
                "  • Opportunity cost: Significant"
            )

        if result.total_trades > 0:
            if result.win_rate is not None and result.win_rate < 50:
                return (
                    "🔴 STRATEGY RISK — Losing More Than Winning\n"
                    "  • Win rate < 50%\n"
                    "  • Risk: Each trade likely to lose\n"
                    "  • Recommendation: Review exit strategy"
                )

        return (
            "🟢 MODERATE RISK — Acceptable\n"
            "  • Signals are executing\n"
            "  • Win rate is reasonable\n"
            "  • Risk management in place"
        )

    def _recommend_modes(
        self, result: AnalysisResult, market_assessment: str
    ) -> List[ModeRecommendation]:
        """Recommend trading modes for next week."""
        recommendations = []

        # Case 1: Zero signals
        if result.total_signals == 0:
            recommendations.append(
                ModeRecommendation(
                    mode="RESTRICTED",
                    confidence=85,
                    reason="Market consolidating with zero signals. RESTRICTED filters noise.",
                    expected_performance="Safe but low opportunity.",
                    risk_level="Very Low",
                )
            )
            recommendations.append(
                ModeRecommendation(
                    mode="CONSERVATIVE",
                    confidence=70,
                    reason="Slightly higher threshold to catch any emerging signals.",
                    expected_performance="Few trades but selective quality.",
                    risk_level="Low",
                )
            )
            return recommendations

        # Case 2: Zero execution (signals blocked)
        if result.execution_rate == 0 and result.total_signals > 0:
            recommendations.append(
                ModeRecommendation(
                    mode="SCALPING",
                    confidence=90,
                    reason="Lowest threshold (60%) will execute blocked signals. Tight risk control.",
                    expected_performance="More trades, tighter stops, scalp micro-moves.",
                    risk_level="High but Controlled",
                )
            )
            recommendations.append(
                ModeRecommendation(
                    mode="AGGRESSIVE",
                    confidence=80,
                    reason="Same 60% threshold but larger per-trade risk. Good if market moves.",
                    expected_performance="More quantity, larger gains if right.",
                    risk_level="High",
                )
            )
            return recommendations

        # Case 3: Low execution rate
        if result.execution_rate < 30:
            recommendations.append(
                ModeRecommendation(
                    mode="SCALPING",
                    confidence=85,
                    reason="Lowest threshold accepts more signals. Max 5 positions for scalping micro-moves.",
                    expected_performance="Increase signal count, manage with tight stops.",
                    risk_level="Moderate-High",
                )
            )
            recommendations.append(
                ModeRecommendation(
                    mode="AGGRESSIVE",
                    confidence=75,
                    reason="60% threshold same as SCALPING but with larger per-trade risk.",
                    expected_performance="Fewer positions but larger profit potential.",
                    risk_level="High",
                )
            )
            recommendations.append(
                ModeRecommendation(
                    mode="NORMAL",
                    confidence=60,
                    reason="65% threshold between AGGRESSIVE and CONSERVATIVE. Balanced approach.",
                    expected_performance="More conservative than AGGRESSIVE.",
                    risk_level="Moderate",
                )
            )
            return recommendations

        # Case 4: Good execution rate (>50%)
        if result.execution_rate >= 50:
            if result.win_rate is not None and result.win_rate >= 60:
                # Winning strategy, increase opportunity capture
                recommendations.append(
                    ModeRecommendation(
                        mode="AGGRESSIVE",
                        confidence=90,
                        reason="High win rate + good execution. Increase position count to 4 for more captures.",
                        expected_performance="Maximize profitable trade frequency.",
                        risk_level="Moderate-High",
                    )
                )
                recommendations.append(
                    ModeRecommendation(
                        mode="SCALPING",
                        confidence=85,
                        reason="Same 60% threshold but max 5 positions. Scalp more opportunities.",
                        expected_performance="High frequency, controlled risk.",
                        risk_level="Moderate",
                    )
                )
            else:
                # Just good execution, stay balanced
                recommendations.append(
                    ModeRecommendation(
                        mode="NORMAL",
                        confidence=85,
                        reason="Good execution + balanced risk. Standard operating mode.",
                        expected_performance="Consistent profitable trading.",
                        risk_level="Moderate",
                    )
                )
                recommendations.append(
                    ModeRecommendation(
                        mode="AGGRESSIVE",
                        confidence=70,
                        reason="Increase opportunity capture if confident.",
                        expected_performance="More positions = more opportunity.",
                        risk_level="Moderate-High",
                    )
                )
            return recommendations

        # Default: balanced recommendation
        recommendations.append(
            ModeRecommendation(
                mode="NORMAL",
                confidence=80,
                reason="Balanced approach for moderate conditions.",
                expected_performance="Stable, consistent trading.",
                risk_level="Moderate",
            )
        )
        return recommendations

    def _generate_next_week_strategy(
        self, result: AnalysisResult, recommendations: List[ModeRecommendation], market_assessment: str
    ) -> str:
        """Generate trading strategy for next week."""
        if result.total_signals == 0:
            return (
                "⏳ WAIT & PREPARE STRATEGY\n\n"
                "1. CONSOLIDATION PERIOD — Market lacks signals\n"
                "2. USE RESTRICTIVE MODE — RESTRICTED or CONSERVATIVE\n"
                "3. MONITOR FOR BREAKOUT — Watch for sudden signal surge\n"
                "4. PREPARE SCALP SETUP — Keep SCALPING ready for volatility spike\n"
                "5. REVIEW SYSTEM — Ensure thresholds will catch breakout signals\n\n"
                "✅ Action: Stay patient. First sign of signals → escalate mode."
            )

        if result.execution_rate == 0:
            return (
                "🎯 FILTER ADJUSTMENT STRATEGY\n\n"
                "1. THRESHOLD TOO HIGH — Signals generated but not executed\n"
                "2. ACTIVATE SCALPING MODE — 60% threshold will capture signals\n"
                "3. TIGHT RISK MANAGEMENT — $20/position stops keeps losses small\n"
                "4. EXPECT HIGHER VOLUME — More trades but managed tightly\n"
                "5. MONITOR WIN RATE — Track if executed trades are profitable\n\n"
                "✅ Action: Switch to SCALPING, watch first day results."
            )

        if result.execution_rate < 30:
            top_rec = recommendations[0] if recommendations else None
            mode_name = top_rec.mode if top_rec else "SCALPING"
            return (
                f"📊 SELECTIVE TRADING STRATEGY — Use {mode_name} Mode\n\n"
                "1. INCREASE SIGNAL CAPTURE — Lower ML threshold to 60%\n"
                "2. SELECTIVE ENTRY — Focus on highest-confidence signals\n"
                "3. TIGHT RISK CONTROL — Smaller per-trade risk for safety\n"
                "4. MONITOR EXECUTION — Track which signals execute vs block\n"
                "5. ADJUST FILTERS — May need to relax market quality filter\n\n"
                f"✅ Action: Switch to {mode_name}, monitor execution rate daily."
            )

        if result.execution_rate >= 70 and result.win_rate is not None and result.win_rate >= 60:
            return (
                "🚀 AGGRESSIVE GROWTH STRATEGY\n\n"
                "1. WINNING SETUP — High execution + good win rate\n"
                "2. INCREASE POSITION COUNT — Move to AGGRESSIVE (4 pos) or SCALPING (5 pos)\n"
                "3. CAPTURE MORE OPPORTUNITIES — Current strategy is working\n"
                "4. MAINTAIN DISCIPLINE — Keep same risk per trade\n"
                "5. SCALE CAREFULLY — Don't over-leverage despite winning streak\n\n"
                "✅ Action: Increase position limit, capture 4-5 trades per setup."
            )

        return (
            "⚖️ BALANCED STRATEGY — Continue with NORMAL Mode\n\n"
            "1. MODERATE EXECUTION — Strategy executing at acceptable rate\n"
            "2. STEADY APPROACH — NORMAL mode is appropriate\n"
            "3. CONSISTENT RESULTS — Maintain current settings\n"
            "4. MONITOR DAILY — Adjust if conditions change\n"
            "5. REVIEW WEEKLY — Check win rate and profitability\n\n"
            "✅ Action: Stay in NORMAL mode, execute consistently."
        )

    def _generate_action_items(
        self, result: AnalysisResult, recommendations: List[ModeRecommendation], market_assessment: str
    ) -> List[str]:
        """Generate actionable next steps."""
        items = []

        # Action 1: Mode switch
        if recommendations:
            top_rec = recommendations[0]
            items.append(f"✅ SWITCH MODE: /setmode {top_rec.mode}")

        # Action 2: Based on execution
        if result.total_signals > 0 and result.execution_rate == 0:
            items.append(
                "✅ CHECK FILTERS: Verify ML threshold and market quality filter aren't too strict"
            )

        # Action 3: Based on win rate
        if result.total_trades > 0 and result.win_rate is not None:
            if result.win_rate < 50:
                items.append("✅ REVIEW EXITS: Win rate < 50% — Check exit strategy")
            elif result.win_rate >= 70:
                items.append("✅ CAPITALIZE: Win rate > 70% — Increase position count")

        # Action 4: Daily monitoring
        items.append("✅ MONITOR DAILY: Check /analysis every 24h for pattern changes")

        # Action 5: Weekly review
        items.append("✅ WEEKLY REVIEW: Re-run /analysis at end of week to adjust mode")

        # Action 6: Based on signals
        if result.total_signals == 0:
            items.append("✅ WAIT FOR BREAKOUT: Market consolidating, no trades expected yet")
        elif result.total_signals < 10:
            items.append("✅ PREPARE FOR ACTIVITY: Low signals now, watch for increase")

        return items


def create_professional_analyzer() -> ProfessionalAnalyzer:
    """Factory function."""
    return ProfessionalAnalyzer()


if __name__ == "__main__":
    analyzer = create_professional_analyzer()
    analysis = analyzer.analyze_5_days()

    print(f"\n{'='*70}")
    print(f"PROFESSIONAL 5-DAY TRADING ANALYSIS")
    print(f"Date: {analysis.analysis_date}")
    print(f"{'='*70}\n")

    print(f"MARKET ASSESSMENT:\n{analysis.market_assessment}\n")

    print(f"KEY FINDINGS:")
    for finding in analysis.key_findings:
        print(f"  {finding}")

    print(f"\nRISK ASSESSMENT:\n{analysis.risk_assessment}\n")

    print(f"MODE RECOMMENDATIONS:")
    for i, rec in enumerate(analysis.mode_recommendations, 1):
        print(f"\n  {i}. {rec.mode} (Confidence: {rec.confidence}%)")
        print(f"     Reason: {rec.reason}")
        print(f"     Expected: {rec.expected_performance}")
        print(f"     Risk: {rec.risk_level}")

    print(f"\nNEXT WEEK STRATEGY:\n{analysis.next_week_strategy}\n")

    print(f"ACTION ITEMS:")
    for item in analysis.action_items:
        print(f"  {item}")

    print(f"\n{'='*70}\n")
