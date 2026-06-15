"""
Telegram Bot Commands Module
============================
Command handlers untuk monitoring trading bot via Telegram.

Commands:
- /balance — current balance, equity, drawdown
- /positions — open positions dengan P/L
- /status — bot status (mode, consecutive losses, etc)
- /help — list all commands
"""

from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional, Any
from loguru import logger
import asyncio
import os

WIB = ZoneInfo("Asia/Jakarta")

# Import new modules
from src.trading_modes import get_trading_mode_manager
from src.position_analysis import create_analyzer
from src.professional_analysis import create_professional_analyzer
from src.ai_trading_analysis import get_ai_trading_analysis
from src.scalping_optimizer import create_scalping_optimizer
from src.entry_strategy import get_entry_strategy_manager, EntryStrategyType


def create_balance_command(trading_bot) -> str:
    """
    Handler untuk /balance command.
    Menampilkan: balance, equity, drawdown, daily P/L.
    """
    try:
        # Get account info dari MT5 (using private method)
        account_info = trading_bot.mt5._get_account_info()
        if not account_info:
            return "❌ Tidak bisa ambil account info dari MT5"

        balance = account_info.get("balance", 0)
        equity = account_info.get("equity", 0)
        margin_used = account_info.get("margin", 0)  # key is "margin" not "margin_used"
        margin_free = account_info.get("margin_free", 0)

        # Calculate metrics
        drawdown_usd = balance - equity
        drawdown_pct = (drawdown_usd / balance * 100) if balance > 0 else 0
        profit_factor = equity - balance  # Minus = loss
        margin_pct = (margin_used / (margin_used + margin_free) * 100) if (margin_used + margin_free) > 0 else 0

        # Daily P/L (from smart_risk state — use get_state() method)
        risk_state = trading_bot.smart_risk.get_state()
        daily_loss = getattr(risk_state, 'daily_loss', 0)
        daily_loss_pct = getattr(risk_state, 'daily_loss_percent', 0)

        msg = f"""💰 <b>ACCOUNT BALANCE</b>

<b>Balance:</b> ${balance:,.2f}
<b>Equity:</b> ${equity:,.2f}
<b>Drawdown:</b> ${drawdown_usd:,.2f} ({drawdown_pct:.2f}%)

<b>Margin Used:</b> ${margin_used:,.2f} ({margin_pct:.1f}%)
<b>Margin Free:</b> ${margin_free:,.2f}

<b>Today P/L:</b> ${-daily_loss:,.2f} ({-daily_loss_pct:.2f}%)
<b>Max Daily Loss:</b> ${trading_bot.smart_risk.max_daily_loss_usd:,.2f}

⏰ {datetime.now(WIB).strftime('%H:%M:%S')} WIB
"""
        return msg.strip()

    except Exception as e:
        return f"❌ Error: {e}"


def create_positions_command(trading_bot) -> str:
    """
    Handler untuk /positions command.
    Menampilkan: list semua open positions + P/L + durasi.
    """
    try:
        positions = trading_bot.mt5.get_open_positions(symbol=trading_bot.config.symbol)

        if positions is None or len(positions) == 0:
            return "✅ Tidak ada posisi terbuka"

        msg = """📊 <b>OPEN POSITIONS</b>\n"""

        total_profit = 0
        for row in positions.iter_rows(named=True):
            ticket = row.get("ticket")
            symbol = row.get("symbol", trading_bot.config.symbol)
            order_type = row.get("type", "?")
            volume = row.get("volume", 0)
            price_open = row.get("price_open", 0)
            profit = row.get("profit", 0)

            # Get current price untuk pips
            tick = trading_bot.mt5.get_tick(symbol)
            if tick:
                current_price = tick.bid if order_type == "SELL" else tick.ask
                pips = abs(current_price - price_open) * 100
                if profit < 0:
                    pips = -pips
            else:
                pips = 0

            # Color code
            emoji = "🟢" if profit >= 0 else "🔴"
            sign = "+" if profit >= 0 else ""

            msg += f"{emoji} #{ticket} {order_type} {volume}L @ ${price_open:.2f} | {sign}${profit:.2f} ({sign}{pips:.1f}pips)\n"
            total_profit += profit

        # Summary
        total_emoji = "🟢" if total_profit >= 0 else "🔴"
        msg += f"\n{total_emoji} <b>Total P/L:</b> ${total_profit:,.2f}"
        msg += f"\n⏰ {datetime.now(WIB).strftime('%H:%M:%S')} WIB"

        return msg.strip()

    except Exception as e:
        return f"❌ Error: {e}"


def create_status_command(trading_bot) -> str:
    """
    Handler untuk /status command.
    Menampilkan: bot mode, consecutive losses, last trade, etc.
    """
    try:
        # Use get_state() method for proper access
        risk_state = trading_bot.smart_risk.get_state()

        # Bot status
        # Attribute is 'mode' (TradingMode enum), get value safely
        mode = getattr(risk_state, 'mode', None)
        bot_mode = mode.value if mode else 'UNKNOWN'
        consecutive_losses = getattr(risk_state, 'consecutive_losses', 0)
        daily_loss = getattr(risk_state, 'daily_loss', 0)

        # Last trade info (ensure timezone-aware for safe arithmetic)
        last_trade_time = trading_bot._last_trade_time
        if last_trade_time is None:
            time_since_last = 0
        else:
            # Make sure datetime is timezone-aware
            if last_trade_time.tzinfo is None:
                last_trade_time = last_trade_time.replace(tzinfo=WIB)
            time_since_last = (datetime.now(WIB) - last_trade_time).total_seconds() / 60

        # Open positions count
        open_pos = trading_bot.mt5.get_open_positions(symbol=trading_bot.config.symbol)
        open_count = len(open_pos) if open_pos is not None else 0

        # Get current market condition
        current_price = trading_bot.mt5.get_tick(trading_bot.config.symbol)
        price_str = f"${current_price.bid:.2f}" if current_price else "N/A"

        msg = f"""🤖 <b>BOT STATUS</b>

<b>Trading Mode:</b> {bot_mode}
<b>Warmup Done:</b> {'✅ Yes' if trading_bot._warmup_done else '⏳ Warming up...'}

<b>Consecutive Losses:</b> {consecutive_losses}
<b>Daily Loss:</b> ${daily_loss:,.2f}

<b>Open Positions:</b> {open_count}
<b>Last Trade:</b> {time_since_last:.0f} min ago

<b>Current Price:</b> {price_str}
<b>Loop Count:</b> {trading_bot._loop_count}

⏰ {datetime.now(WIB).strftime('%H:%M:%S')} WIB
"""
        return msg.strip()

    except Exception as e:
        return f"❌ Error: {e}"


def create_closeall_command(trading_bot, telegram_notifier) -> str:
    """
    Handler untuk /closeall command.
    Close SEMUA open positions dengan market order.
    DANGER: Tidak ada konfirmasi, langsung execute.
    """
    try:
        mt5 = trading_bot.mt5
        symbol = trading_bot.config.symbol

        # Get semua open positions
        positions = mt5.positions_get(symbol=symbol)
        if not positions:
            return "✅ Tidak ada posisi terbuka yang perlu ditutup."

        closed_count = 0
        failed_count = 0
        failed_tickets = []

        for position in positions:
            ticket = position.ticket
            position_type = position.type
            volume = position.volume

            try:
                # Determine order type untuk close: opposite dari current position
                # type 0 = BUY, type 1 = SELL
                order_type = 1 if position_type == 0 else 0  # Close BUY dengan SELL, vice versa

                request = {
                    "action": 3,  # TRADE_ACTION_DEAL
                    "symbol": symbol,
                    "volume": volume,
                    "type": order_type,
                    "position": ticket,
                    "magic": 999999,  # Emergency close magic
                    "comment": "Emergency closeall via /closeall command",
                }

                result = mt5.send_order(request)
                if result and result.retcode == 10009:  # TRADE_RETCODE_DONE
                    closed_count += 1
                    logger.info(f"Position {ticket} closed successfully via /closeall")
                else:
                    failed_count += 1
                    failed_tickets.append(ticket)
                    logger.warning(f"Failed to close position {ticket}: {result}")

            except Exception as e:
                failed_count += 1
                failed_tickets.append(ticket)
                logger.error(f"Error closing position {ticket}: {e}")

        # Kirim report ke Telegram
        msg = f"""⚠️ <b>CLOSEALL EXECUTED</b>

<b>Closed:</b> {closed_count} position(s)
<b>Failed:</b> {failed_count} position(s)"""

        if failed_tickets:
            msg += f"\n<b>Failed Tickets:</b> {', '.join(map(str, failed_tickets))}"

        msg += f"\n\n⏰ {datetime.now(WIB).strftime('%H:%M:%S')} WIB"
        return msg.strip()

    except Exception as e:
        logger.error(f"Error in /closeall: {e}")
        return f"❌ Error: {e}"


def create_terminate_command(trading_bot, telegram_notifier) -> str:
    """
    Handler untuk /terminate command.
    Terminate bot program (exit main loop).
    DANGER: Program akan stop, tidak bisa recover tanpa restart manual.
    """
    try:
        # Log termination event
        logger.warning("=" * 60)
        logger.warning("TERMINATE COMMAND RECEIVED VIA TELEGRAM")
        logger.warning("Bot program is shutting down...")
        logger.warning("=" * 60)

        # Send notification
        msg = """🛑 <b>BOT TERMINATED</b>

Perintah /terminate diterima.
Program bot sedang shutdown...

Untuk restart, jalankan kembali:
<code>python main_live.py</code>

⏰ {datetime.now(WIB).strftime('%H:%M:%S')} WIB"""

        # Set flag untuk exit bot (handled dalam main_live.py event loop)
        # Trading bot harus check flag ini di main loop
        if hasattr(trading_bot, '_terminate_requested'):
            trading_bot._terminate_requested = True
        else:
            # Create attribute jika tidak ada
            trading_bot._terminate_requested = True

        return msg.strip()

    except Exception as e:
        logger.error(f"Error in /terminate: {e}")
        return f"❌ Error: {e}"


async def create_news_command(trading_bot) -> str:
    """
    Handler untuk /news command.
    Tampilkan kondisi berita dan economic calendar hari ini.
    """
    try:
        news_agent = trading_bot.news_agent
        if not news_agent:
            return """⚠️ <b>NEWS AGENT DISABLED</b>

News Agent telah di-disable karena backtest menunjukkan:
- Cost: API calls + AI analysis
- Impact: Mengurangi profit (tidak profitable untuk trading decisions)

💡 Alternatif:
- Gunakan /recommend untuk macro sentiment analysis
- Cek economic calendar manual di https://www.forexfactory.com

Status Bot: Aman untuk trading berdasarkan ML/SMC signals saja.

⏰ """ + datetime.now(WIB).strftime('%H:%M:%S') + " WIB"

        # Analyze news conditions
        analysis = news_agent.analyze()

        # Map condition ke emoji
        condition_emoji = {
            "safe": "🟢",
            "caution": "🟡",
            "danger_news": "🔴",
            "danger_sentiment": "⚠️",
            "unknown": "❓",
        }
        emoji = condition_emoji.get(analysis.condition.value, "❓")

        msg = f"""{emoji} <b>NEWS & ECONOMIC CALENDAR</b>

<b>Market Condition:</b> {analysis.condition.value.upper()}
<b>Can Trade:</b> {'✅ Yes' if analysis.can_trade else '❌ NO'}
<b>Lot Multiplier:</b> {analysis.recommended_lot_multiplier:.1f}x

<b>Reason:</b>
{analysis.reason}"""

        # Add upcoming events if any
        if analysis.upcoming_events:
            msg += "\n\n<b>Upcoming Events:</b>"
            for event in analysis.upcoming_events[:3]:  # Show first 3 events
                importance_emoji = "🔴" if event.importance == 3 else "🟡" if event.importance == 2 else "🟢"
                event_time = event.time.strftime("%H:%M %Z") if event.time else "Unknown"
                msg += f"\n{importance_emoji} {event.name} ({event.currency}) @ {event_time}"
                if event.forecast is not None:
                    msg += f"\n   Forecast: {event.forecast} | Prev: {event.previous}"

        # Add sentiment if available
        if analysis.sentiment:
            sentiment_emoji = "📈" if analysis.sentiment.label == "BULLISH" else "📉" if analysis.sentiment.label == "BEARISH" else "➡️"
            msg += f"\n\n<b>Sentiment:</b> {sentiment_emoji} {analysis.sentiment.label}"
            msg += f"\nConfidence: {analysis.sentiment.confidence:.1%}"
            if analysis.sentiment.keywords_found:
                msg += f"\nKeywords: {', '.join(analysis.sentiment.keywords_found[:5])}"

        msg += f"\n\n⏰ {datetime.now(WIB).strftime('%H:%M:%S')} WIB"
        return msg.strip()

    except Exception as e:
        logger.error(f"Error in /news: {e}")
        return f"❌ Error: {e}"


async def create_recommend_command(trading_bot) -> str:
    """
    Handler untuk /recommend command.
    Generate trading recommendation dari AI Agent.
    """
    try:
        ai_provider = trading_bot.ai_provider
        if not ai_provider:
            return "⚠️ AI provider tidak tersedia, gunakan analisis teknikal saja"

        # Get current market data
        mt5 = trading_bot.mt5
        symbol = trading_bot.config.symbol
        df = mt5.get_market_data(
            symbol=symbol,
            timeframe=trading_bot.config.execution_timeframe,
            count=50,
        )

        if df is None or len(df) == 0:
            return "❌ Tidak bisa ambil data market"

        current_price = df["close"].tail(1).item()
        atr = df["atr"].tail(1).item() if "atr" in df.columns else 0

        # Get ML signal
        ml_signal = getattr(trading_bot, '_last_ml_signal', 'UNKNOWN')
        ml_confidence = getattr(trading_bot, '_last_ml_confidence', 0.0)

        # Get SMC signal
        smc_signal = getattr(trading_bot, '_last_raw_smc_signal', 'UNKNOWN')
        smc_confidence = getattr(trading_bot, '_last_raw_smc_confidence', 0.0)

        # Get regime
        try:
            regime_result = trading_bot.regime_detector.detect_regime(df)
            regime = regime_result.get('regime', 'UNKNOWN') if regime_result else 'UNKNOWN'
        except Exception as e:
            regime = 'UNKNOWN'

        # Get account info
        account_info = mt5._get_account_info()
        balance = account_info.get("balance", 0) if account_info else 0
        equity = account_info.get("equity", 0) if account_info else 0
        drawdown_pct = ((balance - equity) / balance * 100) if balance > 0 else 0

        # Call AI provider untuk macro analysis
        try:
            macro_context = await asyncio.wait_for(
                ai_provider.analyze_macro_context(),
                timeout=5.0  # 5 second timeout
            )
        except asyncio.TimeoutError:
            logger.warning("/recommend: AI analysis timeout, using fallback")
            macro_context = ai_provider._fallback_neutral_context()
        except Exception as e:
            logger.warning(f"/recommend: AI analysis error: {e}, using fallback")
            macro_context = ai_provider._fallback_neutral_context()

        # Determine recommendation
        sentiment_emoji = "📈" if macro_context.sentiment > 0.2 else "📉" if macro_context.sentiment < -0.2 else "➡️"
        signal_emoji = "🟢" if ml_signal == "BUY" else "🔴" if ml_signal == "SELL" else "⚪"
        regime_emoji = "📈" if regime == "TRENDING" else "↔️" if regime == "RANGING" else "⚠️"

        # Build recommendation based on multiple signals
        is_bullish = ml_signal == "BUY" or smc_signal == "BUY"
        is_bearish = ml_signal == "SELL" or smc_signal == "SELL"

        if is_bullish and macro_context.sentiment > 0:
            recommendation = "🟢 STRONG BUY — Semua sinyal aligned bullish"
            reason = "ML/SMC bullish + Macro bullish sentiment"
        elif is_bullish and macro_context.sentiment <= 0:
            recommendation = "🟡 BUY (caution) — Bullish teknikal tapi macro headwind"
            reason = f"ML/SMC bullish tapi sentimen makro bearish ({macro_context.sentiment:.1f})"
        elif is_bearish and macro_context.sentiment < 0:
            recommendation = "🔴 STRONG SELL — Semua sinyal aligned bearish"
            reason = "ML/SMC bearish + Macro bearish sentiment"
        elif is_bearish and macro_context.sentiment >= 0:
            recommendation = "🟡 SELL (caution) — Bearish teknikal tapi macro tailwind"
            reason = f"ML/SMC bearish tapi sentimen makro bullish ({macro_context.sentiment:.1f})"
        else:
            recommendation = "⚪ NEUTRAL — Tunggu sinyal lebih jelas"
            reason = "Tidak ada sinyal yang kuat dari ML/SMC"

        # Build message
        msg = f"""<b>TRADING RECOMMENDATION</b>

{recommendation}

<b>Technical Signals:</b>
{signal_emoji} ML: {ml_signal} ({ml_confidence:.1%} confidence)
{signal_emoji} SMC: {smc_signal} ({smc_confidence:.1%} confidence)
{regime_emoji} Regime: {regime}

<b>Macro Analysis:</b>
{sentiment_emoji} Sentiment: {macro_context.sentiment:+.2f} (bullish/bearish)
📊 Reasoning: {macro_context.reasoning[:80]}...

<b>Current Market:</b>
💰 Price: ${current_price:,.2f}
📏 ATR: {atr:.2f} pips
📉 Drawdown: {drawdown_pct:.1f}%

<b>Analysis Summary:</b>
{reason}

⚠️ Disclaimer: AI recommendation informatif saja, bukan jaminan profit.
Validasi dengan risk management rules sebelum entry.

⏰ {datetime.now(WIB).strftime('%H:%M:%S')} WIB"""

        return msg.strip()

    except Exception as e:
        logger.error(f"Error in /recommend: {e}")
        return f"❌ Error: {e}"


async def create_modes_command() -> str:
    """Handler untuk /modes command. List semua trading modes."""
    try:
        mode_manager = get_trading_mode_manager()
        return mode_manager.get_all_modes_summary()
    except Exception as e:
        logger.error(f"Error in /modes: {e}")
        return f"❌ Error: {e}"


async def create_mode_info_command(mode_name: str) -> str:
    """Handler untuk /mode_info <name> command. Tampilkan detail mode spesifik."""
    try:
        mode_manager = get_trading_mode_manager()
        if not mode_name:
            return "❌ Usage: /mode_info <AGGRESSIVE|NORMAL|CONSERVATIVE|RESTRICTED>"
        return mode_manager.get_mode_summary(mode_name.upper())
    except Exception as e:
        logger.error(f"Error in /mode_info: {e}")
        return f"❌ Error: {e}"


async def create_setmode_command(trading_bot, mode_name: Optional[str] = None) -> str:
    """Handler untuk /setmode <name> command. Switch ke mode lain."""
    try:
        if not mode_name:
            return "❌ Usage: /setmode <AGGRESSIVE|NORMAL|CONSERVATIVE|RESTRICTED>"

        mode_manager = get_trading_mode_manager()
        mode_upper = mode_name.upper()

        # Validate mode
        from src.trading_modes import TRADING_MODES
        if mode_upper not in TRADING_MODES:
            return f"❌ Unknown mode: {mode_upper}\nValid modes: AGGRESSIVE, NORMAL, CONSERVATIVE, RESTRICTED"

        # Get old and new config
        old_mode = mode_manager.get_current_mode()
        cfg = TRADING_MODES[mode_upper]

        # Switch mode
        if mode_manager.set_mode(mode_upper):
            # Apply settings to bot immediately
            try:
                # 1. Update config
                if hasattr(trading_bot, "config") and hasattr(trading_bot.config, "risk"):
                    trading_bot.config.risk.max_positions = cfg.max_positions
                    trading_bot.config.risk.max_daily_loss = cfg.max_daily_loss_pct
                    logger.info(f"Updated config: max_pos={cfg.max_positions}, max_loss={cfg.max_daily_loss_pct}%")

                # 2. Update smart risk manager
                if hasattr(trading_bot, "smart_risk"):
                    trading_bot.smart_risk.max_concurrent_positions = cfg.max_positions
                    trading_bot.smart_risk.max_daily_loss_percent = cfg.max_daily_loss_pct
                    # Calculate USD amount for daily loss
                    capital = trading_bot.config.capital if hasattr(trading_bot, "config") else 10000
                    daily_loss_usd = capital * (cfg.max_daily_loss_pct / 100)
                    trading_bot.smart_risk.max_daily_loss_usd = daily_loss_usd
                    logger.info(f"Updated risk manager: max_pos={cfg.max_positions}, daily_loss={cfg.max_daily_loss_pct}% (${daily_loss_usd:.2f})")

                # 3. Update ML threshold
                if hasattr(trading_bot, "dynamic_confidence"):
                    trading_bot.dynamic_confidence.threshold = cfg.ml_threshold
                    logger.info(f"Updated ML threshold: {cfg.ml_threshold:.0%}")

                # 4. Store mode in bot state for display
                if hasattr(trading_bot, "_current_mode"):
                    trading_bot._current_mode = mode_upper

                logger.info(f"✅ Mode switched: {old_mode} → {mode_upper}")
            except Exception as e:
                logger.error(f"Error applying mode settings: {e}")
                return f"⚠️ Mode file saved but config update failed: {e}"

            msg = f"""✅ <b>MODE SWITCHED</b>

{old_mode} → <b>{mode_upper}</b>

<b>New Settings:</b>
  • ML Threshold: <code>{cfg.ml_threshold:.0%}</code>
  • Max Positions: <code>{cfg.max_positions}</code>
  • Max Daily Loss: <code>{cfg.max_daily_loss_pct:.1f}%</code>
  • Risk/Trade: <code>{cfg.risk_per_trade:.1f}%</code>

<i>Settings applied immediately to live trading.</i>

⏰ {datetime.now(WIB).strftime('%H:%M:%S')} WIB"""
            return msg.strip()
        else:
            return f"❌ Failed to switch to {mode_upper}"

    except Exception as e:
        logger.error(f"Error in /setmode: {e}")
        return f"❌ Error: {e}"


async def create_scalping_analysis_command() -> str:
    """
    Handler untuk /scalping command.
    AI scalping optimizer dengan analisa win rate dan rekomendasi.
    """
    try:
        optimizer = create_scalping_optimizer()
        data = optimizer.analyze_scalping_performance(days=5)
        msg = optimizer.format_scalping_analysis(data)
        return msg
    except Exception as e:
        logger.error(f"Error in /scalping: {e}")
        return f"❌ Error: {e}"


async def create_ai_analysis_command(trading_bot) -> str:
    """
    Handler untuk /ai_analysis command.
    AI-powered trading analysis using OpenRouter or other providers.
    """
    try:
        # Get AI provider from bot if available
        ai_provider = trading_bot.ai_provider if hasattr(trading_bot, "ai_provider") else None

        # Call AI analysis
        msg = await get_ai_trading_analysis(ai_provider, days=5)
        return msg

    except Exception as e:
        logger.error(f"Error in /ai_analysis: {e}")
        return f"❌ Error: {e}"


async def create_professional_analysis_command() -> str:
    """
    Handler untuk /pro_analysis command.
    Professional analysis last 5 days with mode recommendations for next week.
    """
    try:
        analyzer = create_professional_analyzer()
        analysis = analyzer.analyze_5_days()

        msg = f"""<b>📊 PROFESSIONAL 5-DAY ANALYSIS</b>
Date: {analysis.analysis_date} | Period: {analysis.period_days} days

<b>📈 MARKET ASSESSMENT:</b>
{analysis.market_assessment}

<b>🔍 KEY FINDINGS:</b>"""

        for finding in analysis.key_findings:
            msg += f"\n  {finding}"

        msg += f"\n\n<b>⚠️ RISK ASSESSMENT:</b>\n{analysis.risk_assessment}"

        msg += "\n\n<b>🎯 MODE RECOMMENDATIONS FOR NEXT WEEK:</b>"
        for i, rec in enumerate(analysis.mode_recommendations, 1):
            conf_emoji = "🔴" if rec.confidence < 60 else "🟡" if rec.confidence < 80 else "🟢"
            msg += f"""

{i}. {conf_emoji} <b>{rec.mode}</b> (Confidence: {rec.confidence}%)
   • {rec.reason}
   • Expected: {rec.expected_performance}
   • Risk Level: {rec.risk_level}"""

        msg += f"\n\n<b>📋 NEXT WEEK STRATEGY:</b>\n{analysis.next_week_strategy}"

        msg += "\n\n<b>✅ ACTION ITEMS:</b>"
        for item in analysis.action_items:
            msg += f"\n  {item}"

        msg += f"\n\n⏰ {datetime.now(WIB).strftime('%H:%M:%S')} WIB"
        return msg.strip()

    except Exception as e:
        logger.error(f"Error in /pro_analysis: {e}")
        return f"❌ Error: {e}"


async def create_analysis_command() -> str:
    """
    Handler untuk /analysis command.
    Analyze why no positions opened in last 3 days.
    """
    try:
        analyzer = create_analyzer()
        result = analyzer.analyze_no_positions(days=3)

        # Build message sections
        msg = f"""<b>📊 POSITION ANALYSIS</b>
(Last {result.days_analyzed} days - {result.analysis_date})

<b>Summary:</b>
  • Total Signals: <code>{result.total_signals}</code>
  • Total Trades: <code>{result.total_trades}</code>
  • Execution Rate: <code>{result.execution_rate:.1f}%</code>
  • Avg Confidence: <code>{result.avg_signal_confidence:.0%}</code>

<b>Signals by Type:</b>
  • BUY: <code>{result.signals_by_type.get('BUY', 0)}</code>
  • SELL: <code>{result.signals_by_type.get('SELL', 0)}</code>
  • NONE: <code>{result.signals_by_type.get('NONE', 0)}</code>

<b>Market Regime:</b>"""

        for regime, count in sorted(
            result.regime_distribution.items(), key=lambda x: x[1], reverse=True
        ):
            msg += f"\n  • {regime}: <code>{count}</code> signals"

        msg += "\n\n<b>Market Quality Breakdown:</b>"
        for quality, count in sorted(
            result.market_quality_breakdown.items(), key=lambda x: x[1], reverse=True
        ):
            msg += f"\n  • {quality}: <code>{count}</code> signals"

        # Top blocking reasons
        if result.top_blocking_reasons:
            msg += "\n\n<b>Top Blocking Factors:</b>"
            for reason, count in result.top_blocking_reasons[:5]:
                pct = (count / result.total_signals * 100) if result.total_signals > 0 else 0
                msg += f"\n  🚫 {reason}: <code>{count}</code> ({pct:.1f}%)"

        # Trade results (if any)
        if result.total_trades > 0:
            msg += f"\n\n<b>Trade Results:</b>"
            if result.win_rate is not None:
                wr_emoji = "✅" if result.win_rate >= 50 else "⚠️"
                msg += f"\n  {wr_emoji} Win Rate: <code>{result.win_rate:.1f}%</code>"
            if result.total_profit is not None:
                profit_emoji = "📈" if result.total_profit > 0 else "📉"
                msg += f"\n  {profit_emoji} Total P/L: <code>${result.total_profit:+.2f}</code>"

        # Key insights
        msg += "\n\n<b>🎯 Key Insights:</b>"
        for insight in result.key_insights:
            msg += f"\n  {insight}"

        msg += f"\n\n⏰ {datetime.now(WIB).strftime('%H:%M:%S')} WIB"
        return msg.strip()

    except Exception as e:
        logger.error(f"Error in /analysis: {e}")
        return f"❌ Error: {e}"


async def create_entries_list_command() -> str:
    """
    Handler untuk /entries command.
    List semua available entry strategies.
    """
    try:
        manager = get_entry_strategy_manager()
        strategies = manager.list_strategies()
        current = manager.get_current_strategy()

        msg = """<b>📝 ENTRY STRATEGIES AVAILABLE</b>

Entry strategy menentukan bagaimana bot validate entry signals:"""

        for strategy_name, config in strategies.items():
            current_marker = " ✅" if config["current"] else ""
            msg += f"""

<b>{config['emoji']} {strategy_name}{current_marker}</b>
  {config['description']}
  • Components: SMC={config['use_smc']}, ML={config['use_ml']}, AI={config['use_ai']}
  • AI Primary: {config['ai_primary']}
  • Min AI Confidence: {config['min_ai_confidence']}%"""

        msg += f"""

<b>Commands:</b>
  /entry_info [STRATEGY] — Detail info strategy
  /setentry [STRATEGY] — Switch to strategy

<b>Current Strategy:</b> <code>{current.value}</code>

⏰ {datetime.now(WIB).strftime('%H:%M:%S')} WIB"""

        return msg.strip()

    except Exception as e:
        logger.error(f"Error in /entries: {e}")
        return f"❌ Error: {e}"


async def create_entry_info_command(strategy_name: str = None) -> str:
    """
    Handler untuk /entry_info command.
    Show detail info tentang specific entry strategy.
    """
    try:
        manager = get_entry_strategy_manager()

        if not strategy_name:
            return await create_entries_list_command()

        # Find strategy
        try:
            strategy = EntryStrategyType(strategy_name)
        except ValueError:
            return f"❌ Unknown strategy: {strategy_name}\n\nUse /entries untuk lihat available strategies"

        msg = manager.get_strategy_info(strategy)
        return msg

    except Exception as e:
        logger.error(f"Error in /entry_info: {e}")
        return f"❌ Error: {e}"


async def create_setentry_command(trading_bot, strategy_name: str = None) -> str:
    """
    Handler untuk /setentry command.
    Switch entry strategy dan update bot config.
    """
    try:
        manager = get_entry_strategy_manager()

        if not strategy_name:
            return f"""❌ No strategy specified!

Usage: /setentry [STRATEGY]

Available:
  • SMC_ML_ONLY — Pure SMC+ML (fastest)
  • SMC_ML_AI — SMC+ML with AI validation
  • AI_PRIMARY — AI primary (most confident)

Example: /setentry AI_PRIMARY"""

        # Validate strategy
        try:
            strategy = EntryStrategyType(strategy_name)
        except ValueError:
            return f"❌ Unknown strategy: {strategy_name}"

        # Set strategy
        success = manager.set_strategy(strategy)
        if not success:
            return f"❌ Failed to set strategy: {strategy_name}"

        # Apply to trading bot
        manager.apply_strategy_to_trading(trading_bot)

        config = manager.get_strategy_config(strategy)
        msg = f"""<b>{config.emoji} ENTRY STRATEGY CHANGED</b>

<b>New Strategy:</b> <code>{strategy.value}</code>

<b>Description:</b> {config.description}

<b>Settings Applied:</b>
  ✅ Use SMC: {config.use_smc}
  ✅ Use ML: {config.use_ml}
  ✅ Use AI: {config.use_ai}
  ✅ AI Primary: {config.ai_as_primary}
  ✅ Min AI Confidence: {config.min_ai_confidence}%
  ✅ Require AI Confirmation: {config.require_ai_confirmation}
  ✅ Max AI Delay: {config.max_ai_delay_seconds}s

Entry strategy akan aktif untuk signal berikutnya!

⏰ {datetime.now(WIB).strftime('%H:%M:%S')} WIB"""

        return msg.strip()

    except Exception as e:
        logger.error(f"Error in /setentry: {e}")
        return f"❌ Error: {e}"


def register_default_commands(trading_bot, telegram_notifier):
    """
    Register semua default commands ke TelegramNotifier.
    Dipanggil dari main_live.py di __init__.
    """
    if not telegram_notifier or not telegram_notifier.enabled:
        return

    # /balance
    async def balance_cmd():
        return create_balance_command(trading_bot)
    balance_cmd._cmd_desc = "Account balance, equity, drawdown"
    telegram_notifier.register_command("balance", balance_cmd)

    # /positions
    async def positions_cmd():
        return create_positions_command(trading_bot)
    positions_cmd._cmd_desc = "List open positions dengan P/L"
    telegram_notifier.register_command("positions", positions_cmd)

    # /status
    async def status_cmd():
        return create_status_command(trading_bot)
    status_cmd._cmd_desc = "Bot status, mode, consecutive losses"
    telegram_notifier.register_command("status", status_cmd)

    # /closeall — close semua posisi trading
    async def closeall_cmd():
        return create_closeall_command(trading_bot, telegram_notifier)
    closeall_cmd._cmd_desc = "Close SEMUA open positions (DANGER!)"
    telegram_notifier.register_command("closeall", closeall_cmd)

    # /terminate — terminate bot program
    async def terminate_cmd():
        return create_terminate_command(trading_bot, telegram_notifier)
    terminate_cmd._cmd_desc = "Terminate bot program (DANGER!)"
    telegram_notifier.register_command("terminate", terminate_cmd)

    # /news — get economic calendar & news conditions
    async def news_cmd():
        return await create_news_command(trading_bot)
    news_cmd._cmd_desc = "Economic calendar & market news conditions"
    telegram_notifier.register_command("news", news_cmd)

    # /recommend — AI trading recommendation
    async def recommend_cmd():
        return await create_recommend_command(trading_bot)
    recommend_cmd._cmd_desc = "AI trading recommendation (ML + SMC + Macro)"
    telegram_notifier.register_command("recommend", recommend_cmd)

    # /modes — list all trading modes
    async def modes_cmd():
        return await create_modes_command()
    modes_cmd._cmd_desc = "List all available trading modes"
    telegram_notifier.register_command("modes", modes_cmd)

    # /mode_info — get info about specific mode
    async def mode_info_cmd(args: str = ""):
        mode_name = args.strip().upper() if args else None
        if not mode_name:
            return await create_modes_command()
        return await create_mode_info_command(mode_name)
    mode_info_cmd._cmd_desc = "Trading mode details (/mode_info AGGRESSIVE, etc)"
    telegram_notifier.register_command("mode_info", mode_info_cmd, supports_args=True)

    # /setmode — switch trading mode
    async def setmode_cmd(args: str = ""):
        mode_name = args.strip().upper() if args else None
        return await create_setmode_command(trading_bot, mode_name)
    setmode_cmd._cmd_desc = "Switch trading mode (AGGRESSIVE|NORMAL|CONSERVATIVE|RESTRICTED)"
    telegram_notifier.register_command("setmode", setmode_cmd, supports_args=True)

    # /analysis — analyze why no positions opened
    async def analysis_cmd():
        return await create_analysis_command()
    analysis_cmd._cmd_desc = "Analyze last 3 days - why no positions opened?"
    telegram_notifier.register_command("analysis", analysis_cmd)

    # /pro_analysis — professional 5-day analysis with mode recommendations
    async def pro_analysis_cmd():
        return await create_professional_analysis_command()
    pro_analysis_cmd._cmd_desc = "Professional 5-day analysis + mode recommendations for next week"
    telegram_notifier.register_command("pro_analysis", pro_analysis_cmd)

    # /ai_analysis — AI-powered analysis using OpenRouter
    async def ai_analysis_cmd():
        return await create_ai_analysis_command(trading_bot)
    ai_analysis_cmd._cmd_desc = "AI analysis from OpenRouter (Deepseek/Claude/GPT)"
    telegram_notifier.register_command("ai_analysis", ai_analysis_cmd)

    # /scalping — AI scalping optimizer dengan 70% win rate analysis
    async def scalping_cmd():
        return await create_scalping_analysis_command()
    scalping_cmd._cmd_desc = "Scalping optimizer analysis - 70% win rate target"
    telegram_notifier.register_command("scalping", scalping_cmd)

    # /entries — list all entry strategies available
    async def entries_cmd():
        return await create_entries_list_command()
    entries_cmd._cmd_desc = "List all entry strategies (SMC_ML_ONLY, SMC_ML_AI, AI_PRIMARY)"
    telegram_notifier.register_command("entries", entries_cmd)

    # /entry_info — get info about specific entry strategy
    async def entry_info_cmd(args: str = ""):
        strategy_name = args.strip().upper() if args else None
        return await create_entry_info_command(strategy_name)
    entry_info_cmd._cmd_desc = "Entry strategy details (/entry_info SMC_ML_ONLY, etc)"
    telegram_notifier.register_command("entry_info", entry_info_cmd, supports_args=True)

    # /setentry — switch entry strategy
    async def setentry_cmd(args: str = ""):
        strategy_name = args.strip().upper() if args else None
        return await create_setentry_command(trading_bot, strategy_name)
    setentry_cmd._cmd_desc = "Switch entry strategy (SMC_ML_ONLY|SMC_ML_AI|AI_PRIMARY)"
    telegram_notifier.register_command("setentry", setentry_cmd, supports_args=True)

    logger.info("Telegram commands registered: /balance, /positions, /status, /closeall, /terminate, /news, /recommend, /modes, /setmode, /entries, /entry_info, /setentry, /analysis, /pro_analysis, /ai_analysis, /scalping")
