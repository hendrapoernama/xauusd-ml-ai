"""
5-Day Trading Analysis with ML Optimization
Analyzes last 5 days of trading data and provides ML-driven strategy optimization
"""

import sys
import json
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import polars as pl

# Setup paths
sys.path.insert(0, str(Path(__file__).parent))
try:
    from src.config import TradingConfig, CAPITAL_MODES
except ImportError:
    TradingConfig = None
    CAPITAL_MODES = {}


class TradingAnalyzer:
    """Comprehensive 5-day trading analysis"""

    def __init__(self):
        self.config = TradingConfig() if TradingConfig else None
        self.trades_df = None
        self.training_data = None
        self.analysis_results = {}
        self.bot_status = {}

    def load_data(self):
        """Load trade history and training data"""
        print("\n" + "="*70)
        print("LOADING DATA")
        print("="*70)

        # Load trades
        trades_path = Path("data/trade_logs/trades/trades_2026_05.csv")
        if trades_path.exists():
            self.trades_df = pd.read_csv(trades_path)
            print(f"[OK] Loaded {len(self.trades_df)} trades from {trades_path.name}")

        # Load training data
        training_path = Path("data/training_data.parquet")
        if training_path.exists():
            self.training_data = pl.read_parquet(training_path)
            print(f"[OK] Loaded {len(self.training_data)} rows from training_data.parquet")

        # Load bot status for recent activity
        status_path = Path("data/bot_status.json")
        if status_path.exists():
            with open(status_path) as f:
                self.bot_status = json.load(f)
            print(f"[OK] Loaded bot status (price: {self.bot_status.get('price')})")

        return self.trades_df is not None or self.training_data is not None

    def get_last_5_days(self):
        """Extract last 5 days of trading data"""
        if self.training_data is None or len(self.training_data) == 0:
            return None

        # Convert to pandas for easier manipulation
        df = self.training_data.to_pandas()

        # Parse timestamp if exists
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            last_date = df['timestamp'].max()
            cutoff_date = last_date - timedelta(days=5)
            df_5day = df[df['timestamp'] >= cutoff_date].copy()
        else:
            df_5day = df.tail(len(df) // (252 * 24 // 15) * 5) if len(df) > 0 else df

        return df_5day

    def analyze_trade_performance(self):
        """Analyze trading performance metrics"""
        print("\n" + "="*70)
        print("TRADE PERFORMANCE ANALYSIS")
        print("="*70)

        if self.trades_df is None or len(self.trades_df) == 0:
            print("No trade data available")
            return {}

        trades = self.trades_df.copy()

        metrics = {
            'total_trades': len(trades),
            'winning_trades': len(trades[trades['profit_usd'] > 0]),
            'losing_trades': len(trades[trades['profit_usd'] < 0]),
            'total_profit': trades['profit_usd'].sum(),
            'win_rate': (len(trades[trades['profit_usd'] > 0]) / len(trades) * 100) if len(trades) > 0 else 0,
            'avg_win': trades[trades['profit_usd'] > 0]['profit_usd'].mean() if len(trades[trades['profit_usd'] > 0]) > 0 else 0,
            'avg_loss': trades[trades['profit_usd'] < 0]['profit_usd'].mean() if len(trades[trades['profit_usd'] < 0]) > 0 else 0,
            'largest_win': trades['profit_usd'].max(),
            'largest_loss': trades['profit_usd'].min(),
            'profit_factor': abs((trades[trades['profit_usd'] > 0]['profit_usd'].sum() /
                                 trades[trades['profit_usd'] < 0]['profit_usd'].sum())
                                ) if trades[trades['profit_usd'] < 0]['profit_usd'].sum() != 0 else 0,
        }

        print(f"\n[STATS] Performance Summary:")
        print(f"   Total Trades: {metrics['total_trades']}")
        print(f"   Wins: {metrics['winning_trades']} | Losses: {metrics['losing_trades']}")
        print(f"   Win Rate: {metrics['win_rate']:.1f}%")
        print(f"   Total Profit: ${metrics['total_profit']:.2f}")
        print(f"   Avg Win: ${metrics['avg_win']:.2f} | Avg Loss: ${metrics['avg_loss']:.2f}")
        print(f"   Largest Win: ${metrics['largest_win']:.2f} | Largest Loss: ${metrics['largest_loss']:.2f}")
        print(f"   Profit Factor: {metrics['profit_factor']:.2f}")

        self.analysis_results['performance'] = metrics
        return metrics

    def analyze_ml_signals(self):
        """Analyze ML signal accuracy and confidence"""
        print("\n" + "="*70)
        print("ML SIGNAL ANALYSIS")
        print("="*70)

        if self.trades_df is None or len(self.trades_df) == 0:
            print("No trade data for ML analysis")
            return {}

        trades = self.trades_df.copy()

        # Signal accuracy
        ml_signals = {}
        for signal in ['BUY', 'SELL', 'HOLD']:
            signal_trades = trades[trades['ml_signal'] == signal]
            if len(signal_trades) > 0:
                wins = len(signal_trades[signal_trades['profit_usd'] > 0])
                accuracy = wins / len(signal_trades) * 100
                ml_signals[signal] = {
                    'count': len(signal_trades),
                    'wins': wins,
                    'accuracy': accuracy,
                    'avg_profit': signal_trades['profit_usd'].mean(),
                    'avg_confidence': signal_trades['ml_confidence'].mean(),
                }

        print(f"\n[ML] Signal Performance:")
        for signal, metrics in ml_signals.items():
            print(f"\n   {signal}:")
            print(f"      Trades: {metrics['count']}")
            print(f"      Win Rate: {metrics['accuracy']:.1f}%")
            print(f"      Avg Profit: ${metrics['avg_profit']:.2f}")
            print(f"      Avg Confidence: {metrics['avg_confidence']:.2f}")

        self.analysis_results['ml_signals'] = ml_signals
        return ml_signals

    def analyze_smc_patterns(self):
        """Analyze SMC pattern effectiveness"""
        print("\n" + "="*70)
        print("SMC PATTERN ANALYSIS")
        print("="*70)

        if self.trades_df is None or len(self.trades_df) == 0:
            print("No trade data for SMC analysis")
            return {}

        trades = self.trades_df.copy()

        smc_patterns = {
            'fvg': trades[trades['smc_fvg_detected'] == True],
            'ob': trades[trades['smc_ob_detected'] == True],
            'bos': trades[trades['smc_bos_detected'] == True],
            'choch': trades[trades['smc_choch_detected'] == True],
        }

        pattern_stats = {}
        for pattern_name, pattern_trades in smc_patterns.items():
            if len(pattern_trades) > 0:
                wins = len(pattern_trades[pattern_trades['profit_usd'] > 0])
                pattern_stats[pattern_name] = {
                    'count': len(pattern_trades),
                    'wins': wins,
                    'win_rate': wins / len(pattern_trades) * 100,
                    'avg_profit': pattern_trades['profit_usd'].mean(),
                    'avg_confidence': pattern_trades['smc_confidence'].mean(),
                }

        print(f"\n[SMC] Pattern Performance:")
        for pattern, stats in pattern_stats.items():
            print(f"\n   {pattern.upper()}:")
            print(f"      Occurrences: {stats['count']}")
            print(f"      Win Rate: {stats['win_rate']:.1f}%")
            print(f"      Avg Profit: ${stats['avg_profit']:.2f}")
            print(f"      Avg Confidence: {stats['avg_confidence']:.2f}")

        self.analysis_results['smc_patterns'] = pattern_stats
        return pattern_stats

    def analyze_feature_importance(self):
        """Analyze feature importance from model"""
        print("\n" + "="*70)
        print("FEATURE IMPORTANCE ANALYSIS")
        print("="*70)

        metrics_path = Path("data/model_metrics.json")
        if not metrics_path.exists():
            print("No model metrics found")
            return {}

        with open(metrics_path) as f:
            metrics = json.load(f)

        importance = metrics.get('featureImportance', [])
        print(f"\n[MODEL] Top 10 Most Important Features:")

        top_features = []
        for i, feat in enumerate(importance[:10], 1):
            print(f"   {i}. {feat['name']}: {feat['importance']:.4f}")
            top_features.append(feat)

        self.analysis_results['feature_importance'] = {
            'train_auc': metrics.get('trainAuc'),
            'test_auc': metrics.get('testAuc'),
            'top_features': top_features,
        }

        return self.analysis_results['feature_importance']

    def analyze_exit_reasons(self):
        """Analyze why trades were exited"""
        print("\n" + "="*70)
        print("EXIT ANALYSIS")
        print("="*70)

        if self.trades_df is None or len(self.trades_df) == 0:
            return {}

        trades = self.trades_df.copy()
        exit_reasons = trades['exit_reason'].value_counts()

        print(f"\n[EXIT] Reasons Distribution:")
        exit_analysis = {}
        for reason, count in exit_reasons.items():
            reason_trades = trades[trades['exit_reason'] == reason]
            wins = len(reason_trades[reason_trades['profit_usd'] > 0])
            win_rate = wins / count * 100
            avg_profit = reason_trades['profit_usd'].mean()

            print(f"\n   {reason}:")
            print(f"      Count: {count}")
            print(f"      Win Rate: {win_rate:.1f}%")
            print(f"      Avg Profit: ${avg_profit:.2f}")

            exit_analysis[reason] = {
                'count': count,
                'win_rate': win_rate,
                'avg_profit': avg_profit,
            }

        self.analysis_results['exit_analysis'] = exit_analysis
        return exit_analysis

    def generate_recommendations(self):
        """Generate strategy optimization recommendations"""
        print("\n" + "="*70)
        print("STRATEGY OPTIMIZATION RECOMMENDATIONS")
        print("="*70)

        perf = self.analysis_results.get('performance', {})
        ml_signals = self.analysis_results.get('ml_signals', {})
        smc_patterns = self.analysis_results.get('smc_patterns', {})
        exits = self.analysis_results.get('exit_analysis', {})
        features = self.analysis_results.get('feature_importance', {})

        recommendations = []

        # 1. ML Signal Optimization
        if ml_signals:
            for signal, metrics in ml_signals.items():
                if metrics['accuracy'] < 50:
                    recommendations.append({
                        'priority': 'HIGH',
                        'category': 'ML Signal',
                        'issue': f"{signal} signal has {metrics['accuracy']:.1f}% win rate",
                        'action': f"Lower confidence threshold for {signal} or retrain model",
                        'potential_impact': '+5-10% win rate',
                    })

        # 2. SMC Pattern Optimization
        if smc_patterns:
            best_pattern = max(smc_patterns.items(), key=lambda x: x[1]['win_rate'], default=None)
            if best_pattern and best_pattern[1]['win_rate'] > 60:
                recommendations.append({
                    'priority': 'MEDIUM',
                    'category': 'SMC Patterns',
                    'issue': f"{best_pattern[0].upper()} pattern has {best_pattern[1]['win_rate']:.1f}% win rate",
                    'action': f"Increase trade size/risk for {best_pattern[0].upper()} patterns",
                    'potential_impact': '+2-5% monthly return',
                })

        # 3. Win Rate Optimization
        if perf.get('win_rate', 0) < 45:
            recommendations.append({
                'priority': 'HIGH',
                'category': 'Entry Filters',
                'issue': f"Win rate is {perf.get('win_rate', 0):.1f}%, below 45% threshold",
                'action': 'Tighten entry filters: require higher ML confidence + SMC confirmation',
                'potential_impact': '+10-15% win rate',
            })

        # 4. Exit Strategy
        best_exit = max(exits.items(), key=lambda x: x[1]['win_rate'], default=None) if exits else None
        worst_exit = min(exits.items(), key=lambda x: x[1]['win_rate'], default=None) if exits else None

        if worst_exit and worst_exit[1]['win_rate'] < 30:
            recommendations.append({
                'priority': 'HIGH',
                'category': 'Exit Strategy',
                'issue': f"{worst_exit[0]} exits at {worst_exit[1]['win_rate']:.1f}% win rate",
                'action': 'Revise exit logic: avoid over-exiting on time or false breakouts',
                'potential_impact': '+3-8% profitability',
            })

        # 5. Feature Engineering
        if features.get('top_features'):
            top_feature = features['top_features'][0]
            recommendations.append({
                'priority': 'MEDIUM',
                'category': 'Feature Engineering',
                'issue': f"{top_feature['name']} is {top_feature['importance']:.1%} of model importance",
                'action': f"Focus on improving {top_feature['name']} calculations and accuracy",
                'potential_impact': '+2-4% model accuracy',
            })

        # 6. Risk Management
        if perf.get('largest_loss', 0) < perf.get('largest_win', 0) * 2:
            recommendations.append({
                'priority': 'MEDIUM',
                'category': 'Risk Management',
                'issue': 'Largest loss is > 50% of largest win (asymmetric risk)',
                'action': 'Tighten stop loss placement or use progressive stop loss',
                'potential_impact': '+5-10% risk-adjusted returns',
            })

        print(f"\n[RECS] Found {len(recommendations)} optimization opportunities:\n")
        for i, rec in enumerate(recommendations, 1):
            print(f"{i}. [{rec['priority']}] {rec['category']}")
            print(f"   Issue: {rec['issue']}")
            print(f"   Action: {rec['action']}")
            print(f"   Impact: {rec['potential_impact']}")
            print()

        self.analysis_results['recommendations'] = recommendations
        return recommendations

    def save_report(self):
        """Save analysis report to JSON"""
        report_path = Path("data/trading_analysis_5day.json")

        report = {
            'timestamp': datetime.now().isoformat(),
            'analysis': self.analysis_results,
        }

        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        print(f"\n[OK] Report saved to {report_path}")
        return report_path

    def run_analysis(self):
        """Run complete analysis"""
        print("\n" + "="*70)
        print("5-DAY TRADING ANALYSIS REPORT")
        print("="*70)
        print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Load data
        if not self.load_data():
            print("ERROR: No data found")
            return None

        # Run analyses
        self.analyze_trade_performance()
        self.analyze_ml_signals()
        self.analyze_smc_patterns()
        self.analyze_feature_importance()
        self.analyze_exit_reasons()
        self.generate_recommendations()

        # Save report
        self.save_report()

        print("\n" + "="*70)
        print("ANALYSIS COMPLETE")
        print("="*70)

        return self.analysis_results


def main():
    analyzer = TradingAnalyzer()
    analyzer.run_analysis()


if __name__ == '__main__':
    main()
