# -*- coding: utf-8 -*-
"""Risk yönetimi"""
from src.utils.logger import get_logger


class RiskManager:
    def __init__(self, config, balance_manager):
        self.config = config
        self.balance_manager = balance_manager
        self.logger = get_logger("risk_manager")
        self.daily_loss = 0.0
        self.daily_trades = 0

    # Bot bu ismi çağırıyor → bu yüzden alias şart
    def check_trade_allowed(self, opportunity) -> bool:
        return self.can_trade(opportunity)

    def can_trade(self, opportunity) -> bool:
        """İşlem yapılabilir mi? (günlük limitler)"""
        max_daily_loss = float(self.config.get("risk_management.max_daily_loss", 50))
        if self.daily_loss >= max_daily_loss:
            self.logger.warning("Günlük zarar limiti aşıldı")
            return False

        max_daily_trades = int(self.config.get("risk_management.max_daily_trades", 100))
        if self.daily_trades >= max_daily_trades:
            self.logger.warning("Günlük işlem limiti aşıldı")
            return False

        return True

    def record_trade_result(self, net_profit: float) -> None:
        """Başarılı/başarısız trade sonrası sayaçları güncelle."""
        self.daily_trades += 1
        # net_profit negatifse daily_loss artar
        if net_profit < 0:
            self.daily_loss += abs(float(net_profit))
