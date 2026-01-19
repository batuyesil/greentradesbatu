# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Any, Dict, List

from telegram import Bot, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.error import TelegramError

from src.utils.logger import get_logger


@dataclass
class RuntimeState:
    started: bool = False


class TelegramNotifier:
    def __init__(self, config):
        self.config = config
        self.logger = get_logger("telegram")

        self.bot_token = config.get("telegram.bot_token")
        self.chat_id = str(config.get("telegram.chat_id") or "")
        self.enabled = bool(config.get("telegram.enabled", False))

        self.additional_chat_ids = [
            str(x) for x in (config.get("telegram.additional_chat_ids") or []) if str(x).strip()
        ]

        self.authorized_users_only = bool(config.get("security.authorized_users_only", True))
        self.authorized_users = set(
            str(x) for x in (config.get("security.authorized_users") or []) if str(x).strip()
        )
        if self.chat_id:
            self.authorized_users.add(self.chat_id)

        self.bot: Optional[Bot] = None
        self.application: Optional[Application] = None
        self.core_bot: Optional[Any] = None
        self.state = RuntimeState()

        self._pending_confirm: Dict[str, bool] = {}

    def attach_core(self, core_bot: Any):
        self.core_bot = core_bot

    # ---------------- utils ----------------
    def _num(self, v, default: float = 0.0) -> float:
        try:
            if v is None:
                return default
            return float(v)
        except Exception:
            return default

    def _pick(self, d: Dict[str, Any], keys: List[str], default=None):
        for k in keys:
            if k in d and d.get(k) is not None:
                return d.get(k)
        return default

    # ---------------- lifecycle ----------------
    async def start(self):
        if not self.enabled:
            self.logger.warning("Telegram devre dışı")
            return
        if not self.bot_token:
            self.logger.warning("Telegram bot_token eksik")
            return
        if not self.chat_id:
            self.logger.warning("Telegram chat_id eksik")
            return

        try:
            self.bot = Bot(token=self.bot_token)
            self.application = Application.builder().token(self.bot_token).build()

            self._register(self.application)

            await self.application.initialize()
            await self.application.start()

            if not self.application.updater:
                raise RuntimeError("Application.updater yok. python-telegram-bot sürümünü kontrol et.")
            await self.application.updater.start_polling(drop_pending_updates=True)

            self.state.started = True
            self.logger.info("✅ Telegram bot polling aktif")

            await self.send_message(
                "🟢 <b>GreenTrades Panel</b>\n"
                "Komutlar hazır.\n\n"
                "⚡ /help ile menüyü aç."
            )

        except Exception as e:
            self.logger.error(f"Telegram başlatma hatası: {e}", exc_info=True)

    async def stop(self):
        try:
            if self.application:
                if self.application.updater:
                    await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()
            self.state.started = False
        except Exception as e:
            self.logger.error(f"Telegram stop hatası: {e}", exc_info=True)

    def _register(self, app: Application):
        app.add_handler(CommandHandler("start", self.cmd_start))
        app.add_handler(CommandHandler("help", self.cmd_help))

        app.add_handler(CommandHandler("balance", self.cmd_balance))
        app.add_handler(CommandHandler("stats", self.cmd_stats))
        app.add_handler(CommandHandler("profit", self.cmd_profit))
        app.add_handler(CommandHandler("positions", self.cmd_positions))
        app.add_handler(CommandHandler("config", self.cmd_config))
        app.add_handler(CommandHandler("status", self.cmd_status))
        app.add_handler(CommandHandler("trades", self.cmd_trades))

        app.add_handler(CommandHandler("pause", self.cmd_pause))
        app.add_handler(CommandHandler("resume", self.cmd_resume))
        app.add_handler(CommandHandler("stop", self.cmd_stop))
        app.add_handler(CommandHandler("rebalance", self.cmd_rebalance))

    def _is_authorized(self, update: Update) -> bool:
        if not self.authorized_users_only:
            return True
        cid = str(update.effective_chat.id) if update.effective_chat else ""
        return cid in self.authorized_users

    async def _deny(self, update: Update):
        if update.message:
            await update.message.reply_text("❌ Yetkin yok.")

    async def _send_to(self, chat_id: str, text: str):
        text = (text or "").strip()
        if not text:
            self.logger.warning("Telegram: boş mesaj gönderimi engellendi (template boş geliyor olabilir).")
            return
        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )
        except TelegramError as e:
            self.logger.error(f"Telegram mesaj hatası: {e}", exc_info=True)

    async def send_message(self, text: str):
        if not self.enabled or not self.bot:
            return
        await self._send_to(self.chat_id, text)
        for cid in self.additional_chat_ids:
            await self._send_to(cid, text)

    async def send_error(self, error_msg: str):
        await self.send_message(f"⚠️ <b>Hata</b>\n\n{error_msg}")

    async def send_opportunity(self, opp: Dict[str, Any]):
        template = self.config.get_template(
            "opportunity_found",
            coin=opp.get("coin", "-"),
            spread=f"{self._num(opp.get('spread', 0)):.2f}",
            buy_exchange=opp.get("buy_exchange", "-"),
            sell_exchange=opp.get("sell_exchange", "-"),
            buy_price=f"{self._num(opp.get('buy_price', 0)):.6f}",
            sell_price=f"{self._num(opp.get('sell_price', 0)):.6f}",
            estimated_profit=f"{self._num(opp.get('estimated_profit', 0)):.2f}",
        )

        if not template.strip():
            template = (
                "🟡 <b>Fırsat</b>\n"
                f"🪙 {opp.get('coin','-')} | Spread: {self._num(opp.get('spread',0)):.2f}%\n"
                f"🛒 {opp.get('buy_exchange','-')} @ {self._num(opp.get('buy_price',0)):.6f}\n"
                f"💸 {opp.get('sell_exchange','-')} @ {self._num(opp.get('sell_price',0)):.6f}\n"
            )

        await self.send_message(template)

    async def send_trade_executed(self, result: Dict[str, Any]):
        # ✅ burada “alan adı uyuşmazlığı”nı çözüyoruz (fake/real sonuçları tek formatta göster)
        coin = result.get("coin", "-")
        buy_exchange = result.get("buy_exchange", "-")
        sell_exchange = result.get("sell_exchange", "-")

        spread = self._num(self._pick(result, ["spread", "spread_percent", "spread_percent"], 0.0))
        buy_price = self._num(self._pick(result, ["buy_price", "avg_buy_price"], 0.0))
        sell_price = self._num(self._pick(result, ["sell_price", "avg_sell_price"], 0.0))

        amount_usd = self._num(self._pick(result, ["amount", "trade_size", "filled_size"], 0.0))
        coin_amount = self._num(self._pick(result, ["coin_amount", "filled_amount", "amount_coin"], 0.0))

        gross = self._num(self._pick(result, ["profit", "gross_profit", "gross"], 0.0))
        fees = self._num(self._pick(result, ["fees", "total_fees", "fee_total"], 0.0))
        slippage_cost = self._num(self._pick(result, ["total_slippage_cost", "slippage_cost"], 0.0))
        net = self._num(self._pick(result, ["net_profit", "net"], gross - fees - slippage_cost))

        profit_percent = self._num(self._pick(result, ["profit_percent"], 0.0))
        exec_time = self._num(self._pick(result, ["execution_time"], 0.0))

        template = self.config.get_template(
            "trade_executed",
            coin=coin,
            spread=f"{spread:.2f}",
            buy_exchange=buy_exchange,
            sell_exchange=sell_exchange,
            buy_price=f"{buy_price:.6f}",
            sell_price=f"{sell_price:.6f}",
            amount=f"{amount_usd:.2f}",
            profit=f"{gross:.2f}",
            fees=f"{fees:.2f}",
            net_profit=f"{net:.2f}",
            profit_percent=f"{profit_percent:.2f}",
            execution_time=f"{exec_time:.2f}",
        )

        if not template.strip():
            template = (
                "✅ <b>İşlem Tamamlandı</b>\n"
                f"🪙 {coin} | Spread: {spread:.2f}%\n"
                f"🛒 {buy_exchange} @ {buy_price:.6f}\n"
                f"💸 {sell_exchange} @ {sell_price:.6f}\n"
                f"💰 İşlem: ${amount_usd:.2f} | Miktar: {coin_amount:.6f}\n\n"
                f"📈 Brüt: ${gross:.2f}\n"
                f"🧾 Komisyon: ${fees:.2f}\n"
                f"🌊 Slippage: ${slippage_cost:.2f}\n"
                f"🏁 Net: ${net:.2f} ({profit_percent:.2f}%)\n"
                + (f"⏱ {exec_time:.2f}s" if exec_time > 0 else "")
            )

        await self.send_message(template)

    def _require_core(self, update: Update) -> bool:
        return bool(self.core_bot)

    async def _confirm_flow(self, update: Update, cmd: str) -> bool:
        if not update.message:
            return False

        need_confirm = set(self.config.get("security.require_confirmation", []) or [])
        if cmd not in need_confirm:
            return True

        if not self._pending_confirm.get(cmd, False):
            self._pending_confirm[cmd] = True
            await update.message.reply_text(f"⚠️ Onay: /{cmd} için tekrar /{cmd} yaz.")
            return False

        self._pending_confirm[cmd] = False
        return True

    # ---------------- commands ----------------
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update):
            return await self._deny(update)

        await update.message.reply_text(
            "🟢 <b>GreenTrades</b>\n"
            "Panel aktif.\n\n"
            "⚡ /help ile komutlar",
            parse_mode=ParseMode.HTML
        )

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update):
            return await self._deny(update)

        help_text = (
            "🧭 <b>GreenTrades Komutlar</b>\n\n"
            "▶️ /start       - Panel\n"
            "💰 /balance     - Bakiye\n"
            "📊 /stats       - İstatistik\n"
            "💹 /profit      - Brüt/Net/Komisyon\n"
            "📌 /positions   - Açık pozisyonlar\n"
            "🧾 /trades      - Son işlemler\n"
            "🟢 /status      - Durum\n"
            "⚙️ /config      - Ayarlar\n\n"
            "⏸ /pause       - Duraklat\n"
            "▶️ /resume      - Devam\n"
            "🔄 /rebalance   - Rebalance\n"
            "🛑 /stop        - Güvenli durdur\n"
        )
        await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)

    async def cmd_balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update):
            return await self._deny(update)
        if not self._require_core(update):
            await update.message.reply_text("⚠️ Core bot bağlı değil.")
            return

        try:
            total = await self.core_bot.balance_manager.get_total_balance()
            total = self._num(total, 0.0)
            await update.message.reply_text(
                f"💰 <b>Bakiye</b>\nToplam: ${total:.2f}",
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            self.logger.error(f"/balance hata: {e}", exc_info=True)
            await update.message.reply_text("⚠️ /balance hata verdi. Log'a bak.", parse_mode=ParseMode.HTML)

    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update):
            return await self._deny(update)
        if not self._require_core(update):
            await update.message.reply_text("⚠️ Core bot bağlı değil.")
            return

        s = getattr(self.core_bot, "stats", {}) or {}
        await update.message.reply_text(
            "📊 <b>İstatistik</b>\n"
            f"Toplam İşlem: {s.get('total_trades', 0)}\n"
            f"Başarılı: {s.get('successful_trades', 0)}\n"
            f"Başarısız: {s.get('failed_trades', 0)}\n"
            f"Bulunan Fırsat: {s.get('opportunities_found', 0)}\n"
            f"Uygulanan: {s.get('opportunities_executed', 0)}\n"
            f"Net Kar: ${self._num(s.get('total_profit', 0.0)):.2f}\n"
            f"Komisyon: ${self._num(s.get('total_fees', 0.0)):.2f}",
            parse_mode=ParseMode.HTML
        )

    async def cmd_profit(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update):
            return await self._deny(update)
        if not self._require_core(update):
            await update.message.reply_text("⚠️ Core bot bağlı değil.")
            return

        s = getattr(self.core_bot, "stats", {}) or {}
        net = self._num(s.get("total_profit", 0.0))
        fees = self._num(s.get("total_fees", 0.0))
        gross = net + fees
        await update.message.reply_text(
            "💹 <b>Kar/Zarar</b>\n"
            f"📈 Brüt: ${gross:.2f}\n"
            f"🧾 Komisyon: ${fees:.2f}\n"
            f"🏁 Net: ${net:.2f}",
            parse_mode=ParseMode.HTML
        )

    async def cmd_positions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update):
            return await self._deny(update)
        await update.message.reply_text("📌 Açık pozisyon: (spot arbitrajda genelde pozisyon tutulmaz)")

    async def cmd_trades(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update):
            return await self._deny(update)
        await update.message.reply_text("🧾 Son işlemler: (DB log bağlanınca gerçek liste gelecek)")

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update):
            return await self._deny(update)
        if not self._require_core(update):
            await update.message.reply_text("⚠️ Core bot bağlı değil.")
            return

        st = self.core_bot.get_status()
        await update.message.reply_text(
            "🟢 <b>Durum</b>\n"
            f"Status: {st.get('status')}\n"
            f"Mode: {st.get('mode')}\n"
            f"Runtime(h): {self._num(st.get('runtime_hours', 0)):.2f}\n"
            f"Aktif Strateji: {st.get('active_strategies', 0)}\n"
            f"Borsa: {st.get('connected_exchanges', 0)}\n"
            f"Paused: {bool(st.get('paused', False))}",
            parse_mode=ParseMode.HTML
        )

    async def cmd_config(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update):
            return await self._deny(update)

        exchanges = self.config.get("exchanges.enabled", []) or []
        min_spread = self.config.get("strategy.spot_arbitrage.min_spread_percent", None)
        mode = self.config.get("mode", "-")
        await update.message.reply_text(
            "⚙️ <b>Config</b>\n"
            f"Mode: {mode}\n"
            f"Borsalar: {', '.join(exchanges)}\n"
            f"Min Spread: {min_spread}",
            parse_mode=ParseMode.HTML
        )

    async def cmd_pause(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update):
            return await self._deny(update)
        if not self._require_core(update):
            await update.message.reply_text("⚠️ Core bot bağlı değil.")
            return

        self.core_bot.is_paused = True
        await update.message.reply_text("⏸ Bot duraklatıldı.")

    async def cmd_resume(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update):
            return await self._deny(update)
        if not self._require_core(update):
            await update.message.reply_text("⚠️ Core bot bağlı değil.")
            return

        self.core_bot.is_paused = False
        await update.message.reply_text("▶️ Bot devam ediyor.")

    async def cmd_rebalance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update):
            return await self._deny(update)
        if not self._require_core(update):
            await update.message.reply_text("⚠️ Core bot bağlı değil.")
            return

        ok = await self._confirm_flow(update, "rebalance")
        if not ok:
            return

        bm = getattr(self.core_bot, "balance_manager", None)
        fn = getattr(bm, "rebalance", None) if bm else None
        if callable(fn):
            await fn()
            await update.message.reply_text("🔄 Rebalance başlatıldı.")
        else:
            await update.message.reply_text("🔄 Rebalance: balance_manager.rebalance() yok (placeholder).")

    async def cmd_stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update):
            return await self._deny(update)
        if not self._require_core(update):
            await update.message.reply_text("⚠️ Core bot bağlı değil.")
            return

        ok = await self._confirm_flow(update, "stop")
        if not ok:
            return

        await self.core_bot.stop()
        await update.message.reply_text("🛑 Bot durduruluyor (güvenli çıkış).")
