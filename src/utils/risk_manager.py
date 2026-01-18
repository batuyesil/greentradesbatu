# -*- coding: utf-8 -*-
"""Risk yÃ¶netimi"""
from src.utils.logger import get_logger

class RiskManager:
    def __init__(self, config, balance_manager):
        self.config = config
        self.balance_manager = balance_manager
        self.logger = get_logger('risk_manager')
        self.daily_loss = 0
        self.daily_trades = 0
    
    def can_trade(self, opportunity):
        """Ä°ÅŸlem yapÄ±labilir mi?"""
        # GÃ¼nlÃ¼k limit kontrolÃ¼
        max_daily_loss = self.config.get('risk_management.max_daily_loss', 50)
        if self.daily_loss >= max_daily_loss:
            self.logger.warning("GÃ¼nlÃ¼k zarar limiti aÅŸÄ±ldÄ±")
            return False
        
        max_daily_trades = self.config.get('risk_management.max_daily_trades', 100)
        if self.daily_trades >= max_daily_trades:
            self.logger.warning("GÃ¼nlÃ¼k iÅŸlem limiti aÅŸÄ±ldÄ±")
            return False
        
        return True



