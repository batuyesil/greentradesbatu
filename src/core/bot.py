# -*- coding: utf-8 -*-
"""
GreenTrades Core Bot
Ana bot sınıfı - tüm bileşenleri koordine eder
"""

import asyncio
from typing import Dict
from datetime import datetime

from src.core.exchange_manager import ExchangeManager
from src.core.balance_manager import BalanceManager
from src.core.orderbook_manager import OrderBookManager
from src.core.trade_executor import TradeExecutor
from src.strategies.spot_arbitrage import SpotArbitrageStrategy
from src.strategies.triangular_arbitrage import TriangularArbitrageStrategy
from src.utils.logger import get_logger
from src.utils.performance_tracker import PerformanceTracker
from src.utils.risk_manager import RiskManager
from src.data.database import Database


class GreenTradesBot:
    def __init__(self, config, telegram=None):
        self.config = config
        self.telegram = telegram
        self.logger = get_logger('bot')

        self.is_running = False
        self.is_paused = False
        self.start_time = None

        self.mode = config.get('mode')
        self.logger.info(f"Bot modu: {self.mode}")

        self.exchange_manager = None
        self.balance_manager = None
        self.orderbook_manager = None
        self.trade_executor = None
        self.risk_manager = None
        self.performance_tracker = None
        self.database = None

        self.strategies = []

        self.stats = {
            'total_trades': 0,
            'successful_trades': 0,
            'failed_trades': 0,
            'total_profit': 0.0,
            'total_fees': 0.0,
            'opportunities_found': 0,
            'opportunities_executed': 0,
        }

        self.quote = self.config.get('strategy.spot_arbitrage.quote', 'USDT')

    async def start(self):
        self.logger.info("Bot baslatiliyor...")

        try:
            self.logger.info("Database baslatiliyor...")
            self.database = Database(self.config)
            await self.database.initialize()

            self.logger.info("Borsalar baglaniyor...")
            self.exchange_manager = ExchangeManager(self.config, self.mode)
            await self.exchange_manager.initialize()

            self.logger.info("Bakiyeler yukleniyor...")
            self.balance_manager = BalanceManager(self.config, self.exchange_manager, self.mode)
            await self.balance_manager.initialize()

            self.logger.info("Orderbook yoneticisi baslatiliyor...")
            self.orderbook_manager = OrderBookManager(self.config, self.exchange_manager)
            await self.orderbook_manager.start()

            self.logger.info("Islem executor'i hazirlaniyor...")
            self.trade_executor = TradeExecutor(self.config, self.exchange_manager, self.balance_manager, self.mode)

            self.logger.info("Risk yoneticisi baslatiliyor...")
            self.risk_manager = RiskManager(self.config, self.balance_manager)

            self.logger.info("Performans takipcisi baslatiliyor...")
            self.performance_tracker = PerformanceTracker(self.config, self.database)

            self.logger.info("Stratejiler yukleniyor...")
            await self._load_strategies()

            initial_balance = await self.balance_manager.get_total_balance()
            self.logger.info(f"Baslangic bakiyesi: ${initial_balance:.2f}")

            self.is_running = True
            self.start_time = datetime.now()
            self.logger.info("Bot basariyla baslatildi!")

        except Exception as e:
            self.logger.error(f"Bot baslatma hatasi: {e}", exc_info=True)
            if self.telegram:
                try:
                    await self.telegram.send_error(f"Bot baslatma hatasi: {e}")
                except Exception:
                    pass
            raise

    async def _load_strategies(self):
        if self.config.get('strategy.spot_arbitrage.enabled'):
            self.logger.info("  Spot Arbitrage stratejisi aktif")
            self.strategies.append(SpotArbitrageStrategy(self.config, self.orderbook_manager, self.balance_manager))

        if self.config.get('strategy.triangular_arbitrage.enabled'):
            self.logger.info("  Triangular Arbitrage stratejisi aktif")
            self.strategies.append(TriangularArbitrageStrategy(self.config, self.orderbook_manager, self.balance_manager))

        if not self.strategies:
            self.logger.warning("Hic strateji aktif degil!")

    async def run(self):
        self.logger.info("ANA DONGU BASLADI!")
        try:
            await self._main_loop()
        except Exception as e:
            self.logger.error(f"Run hatasi: {e}", exc_info=True)
            raise

    async def _heartbeat(self):
        try:
            if not self.exchange_manager or not self.exchange_manager.exchanges:
                return

            coins = self.config.get('coins.priority_list', [])[:10]
            symbols = []
            for c in coins:
                c = str(c).strip()
                if not c:
                    continue
                if "/" in c:
                    symbols.append(c)
                else:
                    symbols.append(f"{c}/{self.quote}")

            ex_id, sym = self.exchange_manager.pick_first_available_symbol(symbols)
            if not ex_id or not sym:
                self.logger.info("HEARTBEAT: coins listesinden hicbir symbol markets icinde bulunamadi")
                return

            ex = self.exchange_manager.exchanges.get(ex_id)
            if not ex:
                return

            t = await ex.fetch_ticker(sym)
            bid = t.get("bid")
            ask = t.get("ask")
            last = t.get("last")
            self.logger.info(f"HEARTBEAT {ex_id} {sym} bid={bid} ask={ask} last={last}")

        except Exception as e:
            self.logger.info(f"HEARTBEAT hata: {str(e)[:160]}")

    async def _main_loop(self):
        self.logger.info("MAIN LOOP ICINDEYIM!")

        loop_count = 0
        while self.is_running:
            try:
                loop_count += 1
                self.logger.info(f"========== DONGU #{loop_count} ==========")
                
                if self.is_paused:
                    await asyncio.sleep(5)
                    continue
                
                # Heartbeat
                if loop_count % 10 == 0:
                    await self._heartbeat()
                
                # Stratejileri çalıştır
                for strategy in self.strategies:
                    try:
                        opportunities = await strategy.find_opportunities()
                        
                        if opportunities:
                            self.stats['opportunities_found'] += len(opportunities)
                            self.logger.info(f"  {len(opportunities)} firsat bulundu")
                            
                            # En iyi fırsatı seç
                            best_opp = max(opportunities, key=lambda x: x.get('profit_score', 0))
                            
                            # Risk kontrolü
                            if self.risk_manager and not self.risk_manager.check_trade_allowed(best_opp):
                                self.logger.warning("  Risk yoneticisi islemi engelledi")
                                continue
                            
                            # İşlemi gerçekleştir
                            result = await self.trade_executor.execute_arbitrage(best_opp)
                            
                            if result.get('success'):
                                self.stats['total_trades'] += 1
                                self.stats['successful_trades'] += 1
                                self.stats['opportunities_executed'] += 1
                                profit = result.get('net_profit', 0)
                                self.stats['total_profit'] += profit
                                
                                self.logger.info(f"✅ Islem basarili! Net kar: ${profit:.4f}")
                                
                                # Telegram bildirimi
                                if self.telegram:
                                    try:
                                        await self.telegram.send_trade_success(result)
                                    except:
                                        pass
                            else:
                                self.stats['failed_trades'] += 1
                                self.logger.warning(f"❌ Islem basarisiz: {result.get('error')}")
                    
                    except Exception as e:
                        self.logger.error(f"Strateji hatasi: {e}", exc_info=True)
                
                # Bekleme
                await asyncio.sleep(self.config.get('strategy.scan_interval', 10))
            
            except Exception as e:
                self.logger.error(f"Ana dongu hatasi: {e}", exc_info=True)
                await asyncio.sleep(5)
    
    async def stop(self):
        self.logger.info("Bot durduruluyor...")
        self.is_running = False
        
        if self.orderbook_manager:
            await self.orderbook_manager.stop()
        
        if self.exchange_manager:
            await self.exchange_manager.close()
        
        if self.database:
            await self.database.close()
        
        self.logger.info("Bot durduruldu")
    
    async def pause(self):
        self.is_paused = True
        self.logger.info("Bot duraklat")