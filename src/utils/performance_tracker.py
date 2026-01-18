# -*- coding: utf-8 -*-
"""Performans takibi"""
from src.utils.logger import get_logger

class PerformanceTracker:
    def __init__(self, config, database):
        self.config = config
        self.database = database
        self.logger = get_logger('performance')
    
    async def record_trade(self, trade_result):
        """Ä°ÅŸlemi kaydet"""
        # TODO: Database'e kaydet
        pass
    
    async def update_metrics(self, stats):
        """Metrikleri gÃ¼ncelle"""
        # TODO: Metrik hesaplama
        pass



