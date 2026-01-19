# -*- coding: utf-8 -*-
"""GreenTrades - Arbitrage Bot - ENHANCED"""
import asyncio, sys, signal, argparse, os
from pathlib import Path
from datetime import datetime
from src.utils.config_loader import ConfigLoader
from src.utils.logger import get_logger, setup_logger
from src.core.bot import GreenTradesBot

try:
    from src.utils.telegram_bot import TelegramNotifier
except:
    TelegramNotifier = None

logger = None
bot = None
LOCK_FILE = Path("greentrades.lock")


def signal_handler(signum, frame):
    global bot
    if logger:
        logger.info("\n🛑 Durduruluyor...")
    if bot:
        try:
            asyncio.run(bot.stop())
        except:
            pass
    if LOCK_FILE.exists():
        LOCK_FILE.unlink()
    sys.exit(0)


def check_single_instance():
    if LOCK_FILE.exists():
        try:
            with open(LOCK_FILE, 'r') as f:
                pid = int(f.read().strip())
            try:
                os.kill(pid, 0)
                print(f"\n❌ Bot zaten çalışıyor! (PID: {pid})\n")
                sys.exit(1)
            except OSError:
                LOCK_FILE.unlink()
        except:
            LOCK_FILE.unlink()
    with open(LOCK_FILE, 'w') as f:
        f.write(str(os.getpid()))


def get_interactive_config():
    print("\n" + "="*70)
    print("   🚀 GREENTRADES - ARBITRAGE BOT")
    print("="*70 + "\n")
    print("📊 MOD SEÇ:\n")
    print("  [1] FAKE MONEY  - Gerçek simülasyon")
    print("  [2] REAL MONEY  - Canlı trading\n")

    mode = None
    while True:
        choice = input("Seçim [1/2]: ").strip()
        if choice == "1":
            mode = "fake_money"
            print("\n✅ FAKE MONEY MODU")
            break
        elif choice == "2":
            mode = "real_money"
            print("\n⚠️  REAL MONEY!")
            confirm = input("Emin misiniz? (EVET/hayır): ").strip()
            if confirm.upper() in ['EVET', 'YES']:
                break
            mode = "fake_money"
            break
        print("❌ 1 veya 2!\n")

    balance = None
    if mode == "fake_money":
        print("\n💵 BAKİYE:\n")
        while True:
            try:
                inp = input("Bakiye ($) [1000]: ").strip()
                balance = float(inp) if inp else 1000
                if balance < 100:
                    print("❌ Min $100!\n")
                    continue
                print(f"\n✅ ${balance:,.2f}")
                break
            except:
                print("❌ Geçersiz!\n")
    else:
        print("\n💰 REAL MONEY:")
        while True:
            try:
                inp = input("% [50]: ").strip()
                balance = float(inp) if inp else 50
                if balance <= 0 or balance > 100:
                    print("❌ 0-100!\n")
                    continue
                print(f"\n✅ %{balance:.0f}")
                break
            except:
                print("❌ Geçersiz!\n")

    input("\n⏎ ENTER...")
    return mode, balance


async def main():
    global logger, bot

    signal.signal(signal.SIGINT, signal_handler)
    check_single_instance()

    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['fake_money', 'real_money'])
    parser.add_argument('--balance', type=float)
    parser.add_argument('--telegram', action='store_true')
    parser.add_argument('--verbose', action='store_true')
    parser.add_argument('--no-interactive', action='store_true')
    args = parser.parse_args()

    telegram = None

    try:
        print("\n🚀 GREENTRADES - Enhanced Edition\n")

        if not args.no_interactive and not args.mode:
            mode, balance = get_interactive_config()
        else:
            mode = args.mode or "fake_money"
            balance = args.balance or 1000

        logger = setup_logger('main', 'DEBUG' if args.verbose else 'INFO')

        logger.info("="*70)
        logger.info("🚀 GreenTrades Başlatılıyor...")
        logger.info(f"🎯 Mod: {mode.upper()}")
        if mode == "fake_money":
            logger.info(f"💵 Bakiye: ${balance:,.2f}")
        else:
            logger.info(f"💰 API Bakiye: %{balance:.0f}")

        config = ConfigLoader()
        config.set('mode', mode)
        if mode == "fake_money":
            config.set('balance.fake_money.total', balance)
        else:
            config.set('balance.real_money.percentage', balance)

        # Telegram'ı sadece --telegram'a bağlama: config'te enabled ise otomatik başlat
        telegram_should_start = bool(config.get("telegram.enabled", False)) or bool(args.telegram)

        if telegram_should_start and TelegramNotifier:
            try:
                telegram = TelegramNotifier(config)
                await telegram.start()
                logger.info("✅ Telegram aktif!")
            except Exception as e:
                logger.warning(f"⚠️  Telegram: {e}")
                telegram = None

        bot = GreenTradesBot(config, telegram)

        # Telegram komutlarının /balance /status vs çalışması için core'u attach et
        if telegram:
            try:
                telegram.attach_core(bot)
            except Exception:
                pass

        await bot.start()

        logger.info("✅ Bot başladı!")
        logger.info("🛑 Ctrl+C ile durdur")
        logger.info("="*70)

        await bot.run()

    except KeyboardInterrupt:
        if logger:
            logger.info("\n🛑 Durduruldu")
    except Exception as e:
        if logger:
            logger.error(f"❌ Hata: {e}", exc_info=True)
        else:
            print(f"\n❌ Hata: {e}")
        raise
    finally:
        if bot:
            try:
                await bot.stop()
            except:
                pass
        if telegram:
            try:
                await telegram.stop()
            except:
                pass
        if LOCK_FILE.exists():
            LOCK_FILE.unlink()


if __name__ == "__main__":
    asyncio.run(main())
