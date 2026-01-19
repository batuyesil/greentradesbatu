# -*- coding: utf-8 -*-
"""Balance Manager - Bakiye yönetimi"""
from src.utils.logger import get_logger


class BalanceManager:
    def __init__(self, config, exchange_manager, mode):
        self.config = config
        self.exchange_manager = exchange_manager
        self.mode = mode
        self.logger = get_logger("balance_manager")
        self.balances = {}

    async def initialize(self):
        """Bakiyeleri yükle"""
        if self.mode == "fake_money":
            fake_config = self.config.get("balance.fake_money", {})

            if isinstance(fake_config, (int, float)):
                total = float(fake_config)
                fake_config = {"total": total}
            else:
                total = float(fake_config.get("total", 1000))

            num_exchanges = len(self.exchange_manager.exchanges)
            per_exchange_config = fake_config.get("per_exchange", "auto")

            if per_exchange_config == "auto":
                per_exchange = total / num_exchanges if num_exchanges > 0 else total
            else:
                per_exchange = float(per_exchange_config)

            for exchange_id in self.exchange_manager.exchanges.keys():
                self.balances[exchange_id] = {
                    "USDT": {"free": per_exchange, "used": 0.0, "total": per_exchange}
                }

            self.logger.info(f"💰 Fake money başlatıldı: ${total:.2f} toplam")
            self.logger.info(f"   📊 {num_exchanges} borsa × ${per_exchange:.2f} = ${total:.2f}")
            return

        # REAL MONEY
        real_config = self.config.get("balance.real_money", {})
        if isinstance(real_config, (int, float)):
            max_usage = float(real_config) if float(real_config) > 0 else 0.0
            use_percentage = False
            percentage = 100.0
            min_reserve = 0.0
        else:
            max_usage = float(real_config.get("max_total_usage", 0) or 0)
            use_percentage = bool(real_config.get("use_percentage", False))
            percentage = float(real_config.get("percentage", 100) or 100)
            min_reserve = float(real_config.get("min_reserve_per_exchange", 0) or 0)

        total_available = 0.0
        for exchange_id, exchange in self.exchange_manager.exchanges.items():
            try:
                balance = await exchange.fetch_balance()
                usdt_balance = balance.get("USDT", {})
                available = float(usdt_balance.get("free", 0) or 0)

                available = max(0.0, available - min_reserve)
                if use_percentage:
                    available *= percentage / 100.0

                self.balances[exchange_id] = balance
                total_available += available
                self.logger.info(f"✅ {exchange_id}: ${available:.2f} kullanılabilir")

            except Exception as e:
                self.logger.error(f"❌ {exchange_id} bakiye hatası: {e}")

        if max_usage and total_available > max_usage:
            self.logger.warning(f"⚠️ Kullanılabilir ${total_available:.2f}, limit ${max_usage:.2f}")

        self.logger.info(f"💰 Real money toplam kullanılabilir: ${total_available:.2f}")

    # ---------------------------
    # TradeExecutor'ın beklediği fonksiyonlar
    # ---------------------------
    async def get_available_balance(self, exchange_id: str, asset: str = "USDT") -> float:
        """
        Fake: RAM içindeki balances'tan free döndürür.
        Real: cache varsa kullanır; yoksa borsadan çekmeyi dener.
        """
        if self.mode == "fake_money":
            return self.get_free(exchange_id, asset)

        # real_money
        b = self.balances.get(exchange_id)
        if isinstance(b, dict) and asset in b and isinstance(b.get(asset), dict):
            return float(b[asset].get("free", 0.0) or 0.0)

        ex = self.exchange_manager.exchanges.get(exchange_id)
        if not ex:
            return 0.0
        try:
            bal = await ex.fetch_balance()
            self.balances[exchange_id] = bal
            a = bal.get(asset, {})
            return float(a.get("free", 0.0) or 0.0) if isinstance(a, dict) else 0.0
        except Exception:
            return 0.0

    async def update_balance(self, exchange_id: str, delta_usdt: float, asset: str = "USDT") -> None:
        """
        Fake mode: free/total günceller.
        Real mode: burada “gerçek bakiye”yi değiştiremeyiz; en fazla cache’i yenileriz.
        """
        delta = float(delta_usdt)

        if self.mode != "fake_money":
            # real_money: cache yenilemeye çalış
            ex = self.exchange_manager.exchanges.get(exchange_id)
            if not ex:
                return
            try:
                self.balances[exchange_id] = await ex.fetch_balance()
            except Exception:
                pass
            return

        # fake_money
        if exchange_id not in self.balances:
            self.balances[exchange_id] = {asset: {"free": 0.0, "used": 0.0, "total": 0.0}}

        if asset not in self.balances[exchange_id]:
            self.balances[exchange_id][asset] = {"free": 0.0, "used": 0.0, "total": 0.0}

        a = self.balances[exchange_id][asset]
        free = float(a.get("free", 0.0) or 0.0)
        used = float(a.get("used", 0.0) or 0.0)
        total = float(a.get("total", 0.0) or (free + used))

        free += delta
        if free < 0:
            free = 0.0

        total = free + used
        a["free"] = free
        a["total"] = total

    # ---------------------------
    # Mevcut yardımcılar (sende vardı)
    # ---------------------------
    def get_free(self, exchange_id: str, asset: str = "USDT") -> float:
        b = self.balances.get(exchange_id, {})
        if not isinstance(b, dict):
            return 0.0
        a = b.get(asset, {})
        if isinstance(a, dict):
            return float(a.get("free", 0.0) or 0.0)
        return 0.0

    def reserve(self, exchange_id: str, asset: str, amount: float) -> bool:
        if self.mode != "fake_money":
            return True

        amount = float(amount)
        b = self.balances.get(exchange_id, {})
        if asset not in b:
            return False
        free = float(b[asset].get("free", 0.0) or 0.0)
        if free < amount:
            return False

        b[asset]["free"] = free - amount
        b[asset]["used"] = float(b[asset].get("used", 0.0) or 0.0) + amount
        b[asset]["total"] = float(b[asset].get("total", 0.0) or 0.0)
        return True

    def release(self, exchange_id: str, asset: str, amount: float) -> None:
        if self.mode != "fake_money":
            return
        amount = float(amount)
        b = self.balances.get(exchange_id, {})
        if asset not in b:
            return
        used = float(b[asset].get("used", 0.0) or 0.0)
        freed = min(used, amount)
        b[asset]["used"] = used - freed
        b[asset]["free"] = float(b[asset].get("free", 0.0) or 0.0) + freed

    async def get_total_balance(self):
        total = 0.0
        for exchange_balances in self.balances.values():
            if isinstance(exchange_balances, dict) and "USDT" in exchange_balances:
                usdt = exchange_balances.get("USDT", {})
                if isinstance(usdt, dict):
                    total += float(usdt.get("total", 0.0) or 0.0)
        return total

    def get_summary(self, asset: str = "USDT") -> dict:
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
        self.logger.info("Rebalancing çalıştırıldı (placeholder)")
        return {"rebalanced": False, "total_moved": 0}
    
    
    async def rebalance_between_exchanges(self, buy_ex: str, sell_ex: str, method: str = "equal") -> dict:
        """
        FAKE: USDT'yi borsalar arasında tekrar dengele (transfer simülasyonu)
        REAL: burada gerçek transfer yapmayacağız (withdraw tehlikeli) -> sadece cache yenilemeye çalışır.
        """
        try:
            method = str(method or "equal").lower()

            if self.mode != "fake_money":
                # real_money: sadece cache yenile
                try:
                    ex1 = self.exchange_manager.exchanges.get(buy_ex)
                    ex2 = self.exchange_manager.exchanges.get(sell_ex)
                    if ex1:
                        self.balances[buy_ex] = await ex1.fetch_balance()
                    if ex2:
                        self.balances[sell_ex] = await ex2.fetch_balance()
                except Exception:
                    pass
                return {"rebalanced": False, "mode": "real_money", "moved": 0.0}

            # fake_money: mevcut USDT free değerlerini al
            buy_free = float(self.get_free(buy_ex, "USDT") or 0.0)
            sell_free = float(self.get_free(sell_ex, "USDT") or 0.0)

            # Basit ve sağlam yaklaşım:
            # - Equal: ikisini ortala
            # - Proportional: şimdilik equal gibi davran (gerekirse sonra genişletiriz)
            target = (buy_free + sell_free) / 2.0

            # buy tarafı düşükse sell'den buy'a transfer
            moved = 0.0
            if buy_free < target and sell_free > target:
                need = target - buy_free
                can_give = sell_free - target
                moved = min(need, can_give)
            elif sell_free < target and buy_free > target:
                need = target - sell_free
                can_give = buy_free - target
                moved = min(need, can_give)
                # bu sefer ters yönde
                if moved > 0:
                    await self.update_balance(buy_ex, -moved, "USDT")
                    await self.update_balance(sell_ex, +moved, "USDT")
                    self.logger.info(f"[FAKE REBALANCE] {buy_ex} -> {sell_ex} moved ${moved:.2f}")
                    return {"rebalanced": True, "mode": "fake_money", "moved": moved, "from": buy_ex, "to": sell_ex, "target_each": target}

            if moved > 0:
                await self.update_balance(sell_ex, -moved, "USDT")
                await self.update_balance(buy_ex, +moved, "USDT")
                self.logger.info(f"[FAKE REBALANCE] {sell_ex} -> {buy_ex} moved ${moved:.2f}")
                return {"rebalanced": True, "mode": "fake_money", "moved": moved, "from": sell_ex, "to": buy_ex, "target_each": target}

            return {"rebalanced": False, "mode": "fake_money", "moved": 0.0, "target_each": target}

        except Exception as e:
            self.logger.error(f"rebalance_between_exchanges error: {e}")
            return {"rebalanced": False, "error": str(e)}
