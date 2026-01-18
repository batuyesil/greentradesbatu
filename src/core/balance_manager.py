# -*- coding: utf-8 -*-
"""Balance Manager - Bakiye yÃ¶netimi"""
from src.utils.logger import get_logger


class BalanceManager:
    def __init__(self, config, exchange_manager, mode):
        self.config = config
        self.exchange_manager = exchange_manager
        self.mode = mode
        self.logger = get_logger('balance_manager')
        self.balances = {}

    async def initialize(self):
        """Bakiyeleri yÃ¼kle"""
        if self.mode == 'fake_money':
            fake_config = self.config.get('balance.fake_money', {})

            if isinstance(fake_config, (int, float)):
                total = float(fake_config)
                fake_config = {'total': total}
            else:
                total = float(fake_config.get('total', 1000))

            num_exchanges = len(self.exchange_manager.exchanges)
            per_exchange_config = fake_config.get('per_exchange', 'auto')

            if per_exchange_config == 'auto':
                per_exchange = total / num_exchanges if num_exchanges > 0 else total
            else:
                per_exchange = float(per_exchange_config)

            for exchange_id in self.exchange_manager.exchanges.keys():
                self.balances[exchange_id] = {
                    'USDT': {'free': per_exchange, 'used': 0, 'total': per_exchange}
                }

            self.logger.info(f"ğŸ’° Fake money baÅŸlatÄ±ldÄ±: ${total:.2f} toplam")
            self.logger.info(f"   ğŸ“Š {num_exchanges} borsa Ã— ${per_exchange:.2f} = ${total:.2f}")

        else:
            real_config = self.config.get('balance.real_money', {})
            if isinstance(real_config, (int, float)):
                max_usage = real_config if real_config > 0 else None
                use_percentage = False
                percentage = 100
                min_reserve = 0
            else:
                max_usage = real_config.get('max_total_usage', 0)
                use_percentage = real_config.get('use_percentage', False)
                percentage = real_config.get('percentage', 100)
                min_reserve = real_config.get('min_reserve_per_exchange', 0)

            total_available = 0
            for exchange_id, exchange in self.exchange_manager.exchanges.items():
                try:
                    balance = await exchange.fetch_balance()
                    usdt_balance = balance.get('USDT', {})
                    available = float(usdt_balance.get('free', 0))

                    available = max(0.0, available - float(min_reserve))
                    if use_percentage:
                        available *= float(percentage) / 100.0

                    self.balances[exchange_id] = balance
                    total_available += available
                    self.logger.info(f"âœ… {exchange_id}: ${available:.2f} kullanÄ±labilir")

                except Exception as e:
                    self.logger.error(f"âŒ {exchange_id} bakiye hatasÄ±: {e}")

            if max_usage and max_usage > 0 and total_available > max_usage:
                self.logger.warning(f"âš ï¸  KullanÄ±labilir ${total_available:.2f}, limit ${max_usage:.2f}")

            self.logger.info(f"ğŸ’° Real money toplam kullanÄ±labilir: ${total_available:.2f}")

    def get_free(self, exchange_id: str, asset: str = "USDT") -> float:
        """Exchange Ã¼zerinde free bakiyeyi dÃ¶ndÃ¼rÃ¼r."""
        b = self.balances.get(exchange_id, {})
        if not isinstance(b, dict):
            return 0.0
        a = b.get(asset, {})
        if isinstance(a, dict):
            return float(a.get('free', 0.0) or 0.0)
        return 0.0

    def reserve(self, exchange_id: str, asset: str, amount: float) -> bool:
        """
        Fake money modunda iÅŸlem simÃ¼lasyonu iÃ§in basit rezerv.
        Real money'de gerÃ§ek order/transfer gelince burasÄ± deÄŸiÅŸecek.
        """
        if self.mode != 'fake_money':
            return True

        amount = float(amount)
        b = self.balances.get(exchange_id, {})
        if asset not in b:
            return False
        free = float(b[asset].get('free', 0.0))
        if free < amount:
            return False

        b[asset]['free'] = free - amount
        b[asset]['used'] = float(b[asset].get('used', 0.0)) + amount
        b[asset]['total'] = float(b[asset].get('total', 0.0))
        return True

    def release(self, exchange_id: str, asset: str, amount: float) -> None:
        """Fake money rezervini geri bÄ±rak."""
        if self.mode != 'fake_money':
            return
        amount = float(amount)
        b = self.balances.get(exchange_id, {})
        if asset not in b:
            return
        used = float(b[asset].get('used', 0.0))
        freed = min(used, amount)
        b[asset]['used'] = used - freed
        b[asset]['free'] = float(b[asset].get('free', 0.0)) + freed

    async def get_total_balance(self):
        """
        Fake mode: USDT totalâ€™larÄ± topla.
        Real mode: burada da USDT Ã¼zerinden topluyoruz (ÅŸimdilik).
        """
        total = 0.0
        for exchange_balances in self.balances.values():
            if isinstance(exchange_balances, dict) and 'USDT' in exchange_balances:
                usdt = exchange_balances.get('USDT', {})
                if isinstance(usdt, dict):
                    total += float(usdt.get('total', 0.0) or 0.0)
        return total

    def get_summary(self, asset: str = "USDT") -> dict:
        """Telegram /balance vb. iÃ§in hÄ±zlÄ± Ã¶zet."""
        out = {}
        total_free = 0.0
        total_used = 0.0
        total_total = 0.0

        for ex_id, bal in self.balances.items():
            a = bal.get(asset, {}) if isinstance(bal, dict) else {}
            free = float(a.get("free", 0.0) or 0.0) if isinstance(a, dict) else 0.0
            used = float(a.get("used", 0.0) or 0.0) if isinstance(a, dict) else 0.0
            tot = float(a.get("total", 0.0) or (free + used)) if isinstance(a, dict) else 0.0

            out[ex_id] = {"free": free, "used": used, "total": tot}
            total_free += free
            total_used += used
            total_total += tot

        return {
            "asset": asset,
            "by_exchange": out,
            "total_free": total_free,
            "total_used": total_used,
            "total_total": total_total,
        }

    async def rebalance(self):
        self.logger.info("Rebalancing Ã§alÄ±ÅŸtÄ±rÄ±ldÄ± (placeholder)")
        return {'rebalanced': False, 'total_moved': 0}



