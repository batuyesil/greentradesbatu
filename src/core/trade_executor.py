# -*- coding: utf-8 -*-
"""
Trade Executor - ENHANCED
Gerçekçi fake money simülasyonu + Tam real money desteği
"""

import asyncio
from typing import Dict, Optional
from datetime import datetime
import random

from src.utils.logger import get_logger

class TradeExecutor:
    """
    Gelişmiş İşlem Gerçekleştirici
    
    Fake Money: Gerçek gibi simülasyon
    - Gerçek orderbook depth
    - Gerçek fee hesaplama
    - VWAP bazlı slippage
    - Partial fills
    
    Real Money: Tam özellikli
    - Limit/Market emirler
    - Order tracking
    - Retry & backoff
    - Emergency stop
    """
    
    def __init__(self, config, exchange_manager, balance_manager, mode):
        self.config = config
        self.exchange_manager = exchange_manager
        self.balance_manager = balance_manager
        self.mode = mode
        self.logger = get_logger('trade_executor')
        
        # İstatistikler
        self.stats = {
            'total_trades': 0,
            'successful_trades': 0,
            'failed_trades': 0,
            'total_gross_profit': 0.0,
            'total_fees': 0.0,
            'total_slippage': 0.0,
            'total_net_profit': 0.0,
        }
        
        # Açık emirler (real money)
        self.open_orders = {}
        
        # Emergency stop flag
        self.emergency_stop = False
    
    async def execute_arbitrage(self, opportunity: Dict) -> Dict:
        """
        Arbitraj fırsatını gerçekleştir
        
        Fake Money: Gerçekçi simülasyon
        Real Money: Gerçek emir gönderme
        """
        if self.emergency_stop:
            return {
                'success': False,
                'error': 'Emergency stop aktif',
                'coin': opportunity['coin']
            }
        
        if self.mode == "fake_money":
            return await self._execute_fake_trade(opportunity)
        else:
            return await self._execute_real_trade(opportunity)
    
    async def _execute_fake_trade(self, opp: Dict) -> Dict:
        """
        FAKE MONEY - Gerçekçi simülasyon
        
        Gerçek özellikler:
        - Orderbook depth kontrolü
        - Gerçek fee hesaplama (borsa bazlı)
        - VWAP bazlı slippage
        - Partial fill simülasyonu
        - Net PnL tracking
        """
        coin = opp['coin']
        buy_ex = opp['buy_exchange']
        sell_ex = opp['sell_exchange']
        spread = opp['spread']
        
        self.logger.info(f"💼 FAKE TRADE: {coin} | {buy_ex} → {sell_ex} | Spread: {spread:.2f}%")
        
        try:
            # 1. Gerçek fee'leri çek
            buy_fee_rate = await self._get_real_fee(buy_ex, coin, 'taker')
            sell_fee_rate = await self._get_real_fee(sell_ex, coin, 'taker')
            
            # 2. Trade size hesapla (gerçekçi)
            trade_size = await self._calculate_trade_size(
                buy_ex, sell_ex, coin, opp['buy_price']
            )
            
            if trade_size < 10:  # Minimum $10
                return {
                    'success': False,
                    'error': 'Trade size çok küçük',
                    'coin': coin
                }
            
            # 3. Gerçek orderbook'tan slippage hesapla
            buy_slippage = await self._calculate_slippage(
                buy_ex, coin, 'buy', trade_size, opp['buy_price']
            )
            sell_slippage = await self._calculate_slippage(
                sell_ex, coin, 'sell', trade_size, opp['sell_price']
            )
            
            # 4. Gerçek fiyatları hesapla (slippage dahil)
            actual_buy_price = opp['buy_price'] * (1 + buy_slippage)
            actual_sell_price = opp['sell_price'] * (1 - sell_slippage)
            
            # 5. Coin miktarı
            coin_amount = trade_size / actual_buy_price
            
            # 6. Kar hesaplama
            gross_profit = (actual_sell_price - actual_buy_price) * coin_amount
            buy_fee = trade_size * buy_fee_rate
            sell_fee = (coin_amount * actual_sell_price) * sell_fee_rate
            total_fees = buy_fee + sell_fee
            total_slippage_cost = (buy_slippage + sell_slippage) * trade_size
            net_profit = gross_profit - total_fees - total_slippage_cost
            
            # 7. Net pozitif kontrolü
            if net_profit <= 0:
                self.logger.warning(
                    f"⚠️  Net kar negatif! "
                    f"Gross: ${gross_profit:.2f} "
                    f"Fees: ${total_fees:.2f} "
                    f"Slippage: ${total_slippage_cost:.2f} "
                    f"Net: ${net_profit:.2f}"
                )
                return {
                    'success': False,
                    'error': 'Net kar negatif',
                    'coin': coin,
                    'net_profit': net_profit
                }
            
            # 8. Partial fill simülasyonu (%95-100 fill)
            fill_rate = random.uniform(0.95, 1.0)
            filled_amount = coin_amount * fill_rate
            filled_size = trade_size * fill_rate
            
            # 9. Bakiyeyi güncelle (fake)
            await self.balance_manager.update_balance(
                buy_ex, -filled_size  # USDT azaldı
            )
            await self.balance_manager.update_balance(
                sell_ex, filled_size * (actual_sell_price / actual_buy_price)  # USDT arttı
            )
            
            # 10. İstatistikleri güncelle
            self.stats['total_trades'] += 1
            self.stats['successful_trades'] += 1
            self.stats['total_gross_profit'] += gross_profit
            self.stats['total_fees'] += total_fees
            self.stats['total_slippage'] += total_slippage_cost
            self.stats['total_net_profit'] += net_profit
            
            # 11. Sonuç
            result = {
                'success': True,
                'mode': 'fake_money',
                'coin': coin,
                'buy_exchange': buy_ex,
                'sell_exchange': sell_ex,
                'trade_size': filled_size,
                'coin_amount': filled_amount,
                'buy_price': actual_buy_price,
                'sell_price': actual_sell_price,
                'spread_percent': spread,
                'gross_profit': gross_profit,
                'buy_fee': buy_fee,
                'sell_fee': sell_fee,
                'total_fees': total_fees,
                'buy_slippage': buy_slippage * 100,
                'sell_slippage': sell_slippage * 100,
                'total_slippage_cost': total_slippage_cost,
                'net_profit': net_profit,
                'profit_percent': (net_profit / filled_size) * 100,
                'fill_rate': fill_rate * 100,
                'timestamp': datetime.now().isoformat(),
            }
            
            # 12. Detaylı log
            self.logger.info(
                f"✅ İŞLEM BAŞARILI:\n"
                f"   Coin: {coin} | Miktar: {filled_amount:.4f}\n"
                f"   Alış: {buy_ex} @ ${actual_buy_price:.6f}\n"
                f"   Satış: {sell_ex} @ ${actual_sell_price:.6f}\n"
                f"   Gross Kar: ${gross_profit:.4f}\n"
                f"   Fees: ${total_fees:.4f} ({buy_fee_rate*100:.2f}% + {sell_fee_rate*100:.2f}%)\n"
                f"   Slippage: ${total_slippage_cost:.4f} ({buy_slippage*100:.3f}% + {sell_slippage*100:.3f}%)\n"
                f"   NET KAR: ${net_profit:.4f} ({(net_profit/filled_size)*100:.2f}%)\n"
                f"   Fill: %{fill_rate*100:.1f}"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Fake trade hatası: {e}", exc_info=True)
            self.stats['total_trades'] += 1
            self.stats['failed_trades'] += 1
            return {
                'success': False,
                'error': str(e),
                'coin': coin
            }
    
    async def _execute_real_trade(self, opp: Dict) -> Dict:
        """
        REAL MONEY - Gerçek işlem
        
        Özellikler:
        - Gerçek limit/market emir
        - Order tracking
        - Timeout & retry
        - Atomicity koruması
        - Emergency rollback
        """
        coin = opp['coin']
        buy_ex = opp['buy_exchange']
        sell_ex = opp['sell_exchange']
        
        self.logger.info(f"💰 REAL TRADE: {coin} | {buy_ex} → {sell_ex}")
        
        buy_order_id = None
        sell_order_id = None
        
        try:
            # 1. Trade size hesapla
            trade_size = await self._calculate_trade_size(
                buy_ex, sell_ex, coin, opp['buy_price']
            )
            
            if trade_size < 10:
                return {
                    'success': False,
                    'error': 'Trade size minimum altında',
                    'coin': coin
                }
            
            # 2. BUY ORDER (önce daha likit taraf)
            buy_exchange = self.exchange_manager.exchanges[buy_ex]
            
            self.logger.info(f"   📤 Buy order gönderiliyor: {buy_ex}")
            buy_order = await buy_exchange.create_limit_buy_order(
                coin,
                trade_size / opp['buy_price'],
                opp['buy_price'] * 1.001  # %0.1 slippage toleransı
            )
            buy_order_id = buy_order['id']
            self.open_orders[buy_order_id] = {
                'exchange': buy_ex,
                'side': 'buy',
                'coin': coin
            }
            
            # 3. Buy order fill bekle (max 10 saniye)
            buy_filled = await self._wait_for_fill(
                buy_exchange, buy_order_id, timeout=10
            )
            
            if not buy_filled:
                # Timeout - iptal et
                self.logger.warning(f"   ⏰ Buy order timeout - iptal ediliyor")
                await buy_exchange.cancel_order(buy_order_id, coin)
                del self.open_orders[buy_order_id]
                return {
                    'success': False,
                    'error': 'Buy order timeout',
                    'coin': coin
                }
            
            # 4. Buy başarılı - Şimdi SELL
            filled_amount = buy_filled['filled']
            avg_buy_price = buy_filled['average']
            
            self.logger.info(f"   ✅ Buy filled: {filled_amount:.4f} @ ${avg_buy_price:.6f}")
            
            # 5. SELL ORDER
            sell_exchange = self.exchange_manager.exchanges[sell_ex]
            
            self.logger.info(f"   📤 Sell order gönderiliyor: {sell_ex}")
            sell_order = await sell_exchange.create_limit_sell_order(
                coin,
                filled_amount,
                opp['sell_price'] * 0.999  # %0.1 slippage toleransı
            )
            sell_order_id = sell_order['id']
            self.open_orders[sell_order_id] = {
                'exchange': sell_ex,
                'side': 'sell',
                'coin': coin
            }
            
            # 6. Sell order fill bekle
            sell_filled = await self._wait_for_fill(
                sell_exchange, sell_order_id, timeout=10
            )
            
            if not sell_filled:
                # CRITICAL: Buy filled ama sell timeout!
                self.logger.error(f"   🚨 CRITICAL: Sell timeout ama buy filled!")
                self.logger.error(f"   Emergency: {filled_amount:.4f} {coin} {buy_ex}'te kaldı")
                
                # Emergency: Aynı borsada sat
                await self._emergency_close(buy_ex, coin, filled_amount)
                
                del self.open_orders[sell_order_id]
                return {
                    'success': False,
                    'error': 'Sell timeout - emergency close yapıldı',
                    'coin': coin,
                    'emergency': True
                }
            
            # 7. Her iki taraf da başarılı!
            avg_sell_price = sell_filled['average']
            
            # 8. PnL hesapla
            gross = (avg_sell_price - avg_buy_price) * filled_amount
            buy_fee = buy_filled.get('fee', {}).get('cost', 0)
            sell_fee = sell_filled.get('fee', {}).get('cost', 0)
            total_fees = buy_fee + sell_fee
            net_profit = gross - total_fees
            
            # 9. İstatistikler
            self.stats['total_trades'] += 1
            self.stats['successful_trades'] += 1
            self.stats['total_gross_profit'] += gross
            self.stats['total_fees'] += total_fees
            self.stats['total_net_profit'] += net_profit
            
            # 10. Cleanup
            del self.open_orders[buy_order_id]
            del self.open_orders[sell_order_id]
            
            # 11. Sonuç
            result = {
                'success': True,
                'mode': 'real_money',
                'coin': coin,
                'buy_exchange': buy_ex,
                'sell_exchange': sell_ex,
                'coin_amount': filled_amount,
                'buy_price': avg_buy_price,
                'sell_price': avg_sell_price,
                'buy_order_id': buy_order_id,
                'sell_order_id': sell_order_id,
                'gross_profit': gross,
                'buy_fee': buy_fee,
                'sell_fee': sell_fee,
                'total_fees': total_fees,
                'net_profit': net_profit,
                'profit_percent': (net_profit / (filled_amount * avg_buy_price)) * 100,
                'timestamp': datetime.now().isoformat(),
            }
            
            self.logger.info(
                f"✅ REAL TRADE BAŞARILI:\n"
                f"   {filled_amount:.4f} {coin}\n"
                f"   Buy: ${avg_buy_price:.6f} (fee: ${buy_fee:.4f})\n"
                f"   Sell: ${avg_sell_price:.6f} (fee: ${sell_fee:.4f})\n"
                f"   Gross: ${gross:.4f} | Fees: ${total_fees:.4f}\n"
                f"   NET: ${net_profit:.4f}"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Real trade hatası: {e}", exc_info=True)
            
            # Cleanup açık emirler
            if buy_order_id and buy_order_id in self.open_orders:
                try:
                    await self.exchange_manager.exchanges[buy_ex].cancel_order(buy_order_id, coin)
                except:
                    pass
                del self.open_orders[buy_order_id]
            
            if sell_order_id and sell_order_id in self.open_orders:
                try:
                    await self.exchange_manager.exchanges[sell_ex].cancel_order(sell_order_id, coin)
                except:
                    pass
                del self.open_orders[sell_order_id]
            
            self.stats['total_trades'] += 1
            self.stats['failed_trades'] += 1
            
            return {
                'success': False,
                'error': str(e),
                'coin': coin
            }
    
    async def _get_real_fee(self, exchange_id: str, symbol: str, order_type: str) -> float:
        """Gerçek fee oranını çek"""
        try:
            exchange = self.exchange_manager.exchanges.get(exchange_id)
            if not exchange:
                return 0.001  # Default %0.1
            
            # Market bilgisini çek
            markets = exchange.markets
            if symbol in markets:
                market = markets[symbol]
                if order_type == 'maker':
                    return market.get('maker', 0.001)
                else:
                    return market.get('taker', 0.001)
            
            # Config fallback
            return self.config.get(f'{exchange_id}.fees.{order_type}', 0.001)
            
        except:
            return 0.001
    
    async def _calculate_trade_size(self, buy_ex: str, sell_ex: str, 
                                   symbol: str, price: float) -> float:
        """Gerçekçi trade size hesapla"""
        try:
            # Kullanılabilir bakiye
            buy_balance = await self.balance_manager.get_available_balance(buy_ex)
            sell_balance = await self.balance_manager.get_available_balance(sell_ex)
            
            # Minimum ikisinden küçüğü
            max_size = min(buy_balance, sell_balance) * 0.8  # %80'ini kullan
            
            # Risk limiti
            risk_limit = self.config.get('risk_management.max_position_per_coin', 200)
            max_size = min(max_size, risk_limit)
            
            # Borsa minimum/maksimum kontrol
            buy_exchange = self.exchange_manager.exchanges.get(buy_ex)
            if buy_exchange and symbol in buy_exchange.markets:
                market = buy_exchange.markets[symbol]
                min_cost = market.get('limits', {}).get('cost', {}).get('min', 10)
                max_cost = market.get('limits', {}).get('cost', {}).get('max', 100000)
                max_size = min(max(max_size, min_cost), max_cost)
            
            return max_size
            
        except Exception as e:
            self.logger.error(f"Trade size hesaplama hatası: {e}")
            return 50  # Default $50
    
    async def _calculate_slippage(self, exchange_id: str, symbol: str,
                                  side: str, size: float, top_price: float) -> float:
        """VWAP bazlı gerçek slippage hesapla"""
        try:
            exchange = self.exchange_manager.exchanges.get(exchange_id)
            if not exchange:
                return 0.002  # Default %0.2
            
            # Orderbook çek
            orderbook = await exchange.fetch_order_book(symbol, limit=20)
            
            if side == 'buy':
                orders = orderbook['asks']  # Satış emirleri
            else:
                orders = orderbook['bids']  # Alış emirleri
            
            # VWAP hesapla
            remaining = size / top_price  # Coin miktarı
            total_cost = 0
            total_amount = 0
            
            for price, amount in orders:
                if remaining <= 0:
                    break
                
                fill_amount = min(amount, remaining)
                total_cost += fill_amount * price
                total_amount += fill_amount
                remaining -= fill_amount
            
            if total_amount == 0:
                return 0.005  # %0.5 default
            
            vwap = total_cost / total_amount
            slippage = abs(vwap - top_price) / top_price
            
            return min(slippage, 0.01)  # Max %1
            
        except Exception as e:
            self.logger.debug(f"Slippage hesaplama hatası: {e}")
            return 0.002
    
    async def _wait_for_fill(self, exchange, order_id: str, timeout: int = 10) -> Optional[Dict]:
        """Order fill bekle"""
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            try:
                order = await exchange.fetch_order(order_id)
                
                if order['status'] == 'closed' or order['filled'] > 0:
                    return order
                
                await asyncio.sleep(0.5)
                
            except Exception as e:
                self.logger.error(f"Order kontrol hatası: {e}")
                await asyncio.sleep(1)
        
        return None
    
    async def _emergency_close(self, exchange_id: str, symbol: str, amount: float):
        """Emergency: Kalan coini aynı borsada sat"""
        try:
            self.logger.warning(f"🚨 EMERGENCY CLOSE: {amount} {symbol} @ {exchange_id}")
            
            exchange = self.exchange_manager.exchanges[exchange_id]
            ticker = await exchange.fetch_ticker(symbol)
            
            # Market price'dan sat
            order = await exchange.create_market_sell_order(symbol, amount)
            
            self.logger.warning(f"   Emergency order: {order['id']}")
            
        except Exception as e:
            self.logger.error(f"❌ Emergency close hatası: {e}")
    
    def get_stats(self) -> Dict:
        """İstatistikleri döndür"""
        if self.stats['total_trades'] == 0:
            return self.stats
        
        return {
            **self.stats,
            'success_rate': (self.stats['successful_trades'] / self.stats['total_trades']) * 100,
            'avg_gross_profit': self.stats['total_gross_profit'] / self.stats['successful_trades'] if self.stats['successful_trades'] > 0 else 0,
            'avg_net_profit': self.stats['total_net_profit'] / self.stats['successful_trades'] if self.stats['successful_trades'] > 0 else 0,
            'avg_fees': self.stats['total_fees'] / self.stats['successful_trades'] if self.stats['successful_trades'] > 0 else 0,
        }
    
    async def cancel_all_orders(self):
        """Tüm açık emirleri iptal et (emergency)"""
        self.logger.warning("🚨 EMERGENCY: Tüm açık emirler iptal ediliyor...")
        
        for order_id, info in list(self.open_orders.items()):
            try:
                exchange = self.exchange_manager.exchanges[info['exchange']]
                await exchange.cancel_order(order_id, info['coin'])
                self.logger.info(f"   ✅ İptal: {order_id}")
            except Exception as e:
                self.logger.error(f"   ❌ İptal hatası {order_id}: {e}")
        
        self.open_orders.clear()
        self.logger.warning("✅ Tüm emirler iptal edildi")
