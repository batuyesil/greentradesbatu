# -*- coding: utf-8 -*-
"""Database yÃ¶netimi"""
import aiosqlite
from src.utils.logger import get_logger

class Database:
    def __init__(self, config):
        self.config = config
        self.logger = get_logger('database')
        self.db_path = config.get('advanced.database.path', 'data/greentrades.db')
        self.conn = None
    
    async def initialize(self):
        """Database'i baÅŸlat"""
        self.conn = await aiosqlite.connect(self.db_path)
        
        # TablolarÄ± oluÅŸtur
        await self.conn.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                coin TEXT,
                buy_exchange TEXT,
                sell_exchange TEXT,
                spread REAL,
                profit REAL,
                mode TEXT
            )
        ''')
        await self.conn.commit()
        
        self.logger.info("Database baÅŸlatÄ±ldÄ±")
    
    async def close(self):
        """Database'i kapat"""
        if self.conn:
            await self.conn.close()



