# -*- coding: utf-8 -*-
"""Triangular Arbitrage Strategy"""
from src.utils.logger import get_logger

class TriangularArbitrageStrategy:
    def __init__(self, config, orderbook_manager, balance_manager):
        self.config = config
        self.orderbook_manager = orderbook_manager
        self.balance_manager = balance_manager
        self.logger = get_logger('triangular_arbitrage')
    
    async def find_opportunities(self):
        """Triangular arbitrage fÄ±rsatlarÄ±nÄ± bul"""
        # TODO: Ä°mplement triangular arbitrage
        return []



