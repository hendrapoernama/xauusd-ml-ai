"""Close all open positions with Telegram notification."""
# Run from project root: python scripts/close_positions.py
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import MetaTrader5 as mt5
import asyncio
from src.telegram_notifier import TelegramNotifier, create_telegram_notifier

# Connect
mt5.initialize(
    login=int(os.getenv("MT5_LOGIN")),
    password=os.getenv("MT5_PASSWORD"),
    server=os.getenv("MT5_SERVER"),
    path=os.getenv("MT5_PATH"),
)

# Initialize Telegram notifier
async def close_all_positions():
    """Close all positions with Telegram notifications."""
    telegram = create_telegram_notifier()

    # Get open positions
    positions = mt5.positions_get()
    closed_count = 0
    failed_count = 0
    total_profit = 0

    if positions:
        print(f"\n🔴 Found {len(positions)} open position(s). Closing all...")
        await telegram.send_alert(f"🔴 CLOSING ALL POSITIONS\nFound {len(positions)} open position(s)")

        for pos in positions:
            direction = 'BUY' if pos.type == 0 else 'SELL'
            print(f"\nClosing #{pos.ticket} | {direction} {pos.volume} {pos.symbol}")
            print(f"   Open: {pos.price_open:.2f} | Current: {pos.price_current:.2f}")
            print(f"   Profit: ${pos.profit:,.2f}")

            # Close position
            tick = mt5.symbol_info_tick(pos.symbol)
            close_price = tick.bid if pos.type == 0 else tick.ask

            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": pos.symbol,
                "volume": pos.volume,
                "type": mt5.ORDER_TYPE_SELL if pos.type == 0 else mt5.ORDER_TYPE_BUY,
                "position": pos.ticket,
                "price": close_price,
                "deviation": 20,
                "magic": 123456,
                "comment": "Manual close",
                "type_time": mt5.ORDER_TIME_GTC,
            }

            result = mt5.order_send(request)
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                print(f"   ✅ CLOSED successfully! Profit: ${pos.profit:,.2f}")
                closed_count += 1
                total_profit += pos.profit

                # Notify Telegram
                emoji = "💚" if pos.profit >= 0 else "❌"
                await telegram.send_alert(
                    f"{emoji} Position #{pos.ticket} Closed\n"
                    f"Type: {direction}\n"
                    f"Entry: {pos.price_open:.2f}\n"
                    f"Exit: {close_price:.2f}\n"
                    f"P/L: ${pos.profit:+.2f}"
                )
            else:
                print(f"   ❌ Failed: {result.comment} (code: {result.retcode})")
                failed_count += 1
                await telegram.send_alert(
                    f"❌ Failed to close #{pos.ticket}\n"
                    f"Error: {result.comment}"
                )
    else:
        print("✅ No open positions to close")
        await telegram.send_alert("✅ No open positions to close")

    # Check final balance
    account = mt5.account_info()
    print(f"\n{'='*50}")
    print(f"✅ Closed: {closed_count} | ❌ Failed: {failed_count}")
    print(f"Total P/L: ${total_profit:+.2f}")
    print(f"Final Balance: ${account.balance:,.2f}")
    print(f"Final Equity: ${account.equity:,.2f}")

    # Final summary to Telegram
    summary = (
        f"📊 CLOSE POSITIONS SUMMARY\n"
        f"✅ Closed: {closed_count}/{len(positions) if positions else 0}\n"
        f"Total P/L: ${total_profit:+.2f}\n"
        f"Balance: ${account.balance:,.2f}\n"
        f"Equity: ${account.equity:,.2f}"
    )
    await telegram.send_alert(summary)

    mt5.shutdown()

# Run async function
asyncio.run(close_all_positions())
