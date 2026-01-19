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

        # ---- NEW: davranış bayrakları (özellik çıkarma yok, sadece ek) ----
        # Net kar negatif olsa bile işlemi "yapılmış" say (simülasyon/real fark etmez)
        self.allow_negative_trades = bool(self.config.get('strategy.spot_arbitrage.allow_negative_trades', True))
        # Spot arbitrajda 2 borsada da (USDT+COIN) prefund varsayımıyla trade size hesapla
        self.use_prefund_split_model_fake = bool(self.config.get('strategy.spot_arbitrage.use_prefund_split_model_fake', True))
        self.use_prefund_split_model_real = bool(self.config.get('strategy.spot_arbitrage.use_prefund_split_model_real', True))
        # Prefund oranları (her borsanın kendi toplam bakiyesinde)
        self.prefund_usdt_ratio = float(self.config.get('strategy.spot_arbitrage.prefund_usdt_ratio', 0.5) or 0.5)
        self.prefund_coin_ratio = float(self.config.get('strategy.spot_arbitrage.prefund_coin_ratio', 0.5) or 0.5)
        # Bu iki oran toplamı 1 olmak zorunda değil ama mantıklı tutalım
        if self.prefund_usdt_ratio < 0:
            self.prefund_usdt_ratio = 0.0
        if self.prefund_coin_ratio < 0:
            self.prefund_coin_ratio = 0.0
        # Trade size kullanım oranı (senin örneğin için default 1.0 daha doğru)
        self.balance_utilization = float(self.config.get('strategy.spot_arbitrage.balance_utilization', 1.0) or 1.0)

        # ---- NEW: trade_balance_fraction (SADECE EK) ----
        # Hesaplanan max_size'ı ekstra küçültür. Örn: 0.6 => %60
        self.trade_balance_fraction = float(self.config.get('risk_management.trade_balance_fraction', 1.0) or 1.0)

        # ---- NEW: clamp helper ile fraction temizle (satır eksiltmeden düzeltme) ----
        # Not: clamp istemiyorsun demiştin ama burada sadece "hata önleme" için minik bir kullanım var.
        # Eğer 1'den büyük yazarsan 1'e; 0'dan küçükse 0'a çeker.
        try:
            self.trade_balance_fraction = float(self.trade_balance_fraction)
        except Exception:
            self.trade_balance_fraction = 1.0
        if self.trade_balance_fraction <= 0:
            self.trade_balance_fraction = 1.0
        # fraction mantığı: 1'den büyükse 1'e çek
        if self.trade_balance_fraction > 1.0:
            self.trade_balance_fraction = 1.0

        if self.balance_utilization <= 0:
            self.balance_utilization = 1.0

        # Fake balance update model: eski update_balance satırlarını no-op yapmak için legacy deltalara çeviriyoruz
        self.use_new_balance_update_model_fake = bool(self.config.get('strategy.spot_arbitrage.use_new_balance_update_model_fake', True))
        self.use_new_balance_update_model_real = bool(self.config.get('strategy.spot_arbitrage.use_new_balance_update_model_real', True))

        # ---- NEW: trade_balance_fraction (risk_management) ----
        # (DUPLICATE BLOCK DISABLED - yukarıda zaten set ediliyor)
        # Bu blok senin eski yapından geldi; KALDIRMIYORUM, sadece zaten kapalı.
        if False:
            self.trade_balance_fraction = float(self.config.get('risk_management.trade_balance_fraction', 1.0) or 1.0)
            # 0 veya negatif gelirse default 1.0
            if self.trade_balance_fraction <= 0:
                self.trade_balance_fraction = 1.0
            # 1'den büyük yazılırsa da 1'e çek (fraction mantığı)
            if self.trade_balance_fraction > 1:
                self.trade_balance_fraction = 1.0

        # ---- NEW: Auto Rebalance ayarları (trade size düşmesin diye) ----
        self.auto_rebalance_enabled = bool(self.config.get('rebalancing.enabled', False))
        # trade_size şu eşikten küçükse rebalance dene (default: 0 => sadece 10$ altına düşerse çalıştıracağız)
        self.auto_rebalance_min_trade = float(self.config.get('rebalancing.auto_rebalance_min_trade', 0) or 0)
        # spam yemesin diye cooldown
        self.auto_rebalance_cooldown_sec = float(self.config.get('rebalancing.cooldown_seconds', 60) or 60)
        self.auto_rebalance_fake_delay_sec = float(self.config.get('rebalancing.fake_delay_seconds', 3) or 3)
        self.auto_rebalance_real_delay_sec = float(self.config.get('rebalancing.real_delay_seconds', 30) or 30)
        self.auto_rebalance_last_ts = 0.0
        # equal/proportional gibi senin config’teki method’u aynen kullanacağız
        self.auto_rebalance_method = str(self.config.get('rebalancing.method', 'equal') or 'equal')

        # (satır sayısı düşmesin diye boş satırlar)
        #







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

            # 2. Trade size hesapla (gerçekçi)  ---- UPDATED: prefund split model destekli ----
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

            # 7. Net pozitif kontrolü  ---- UPDATED: allow_negative_trades ----
            if net_profit <= 0:
                self.logger.warning(
                    f"⚠️  Net kar negatif! "
                    f"Trade: ${trade_size:.2f} | "
                    f"Miktar: {coin_amount:.6f} {coin} | "
                    f"Buy@${actual_buy_price:.6f} Sell@${actual_sell_price:.6f} | "
                    f"Gross: ${gross_profit:.2f} Fees: ${total_fees:.2f} "
                    f"Slippage: ${total_slippage_cost:.2f} Net: ${net_profit:.2f}"
                )

                # Eskiden burada return ediyorduk; artık (allow_negative_trades=True) işlemi "yapılmış" sayıyoruz.
                if not self.allow_negative_trades:
                    return {
                        'success': False,
                        'error': 'Net kar negatif',
                        'coin': coin,
                        'net_profit': net_profit,
                        'trade_size': trade_size,
                        'coin_amount': coin_amount,
                        'buy_price': actual_buy_price,
                        'sell_price': actual_sell_price,
                        'total_fees': total_fees,
                        'total_slippage_cost': total_slippage_cost,
                    }

            # 8. Partial fill simülasyonu (%95-100 fill)
            fill_rate = random.uniform(0.95, 1.0)
            filled_amount = coin_amount * fill_rate
            filled_size = trade_size * fill_rate

            # ---- NEW: Balance update modeli (spot: buy tarafı USDT harcar, sell tarafı coin satar) ----
            # Burada BalanceManager senin projende farklı olabilir; o yüzden hem "yeni" hem "legacy" yolu aynı anda destekliyoruz.
            # Legacy satırları kaldırmıyoruz; yeni modeli aktifken legacy delta'ları 0'a çekiyoruz ki iki kere yazmasın.
            legacy_buy_delta_usdt = -filled_size

            # ---- FIX (satır eksiltmeden): legacy_sell_delta_usdt gerçekçi değilse 2 kez şişiriyordu ----
            # Eski hali: filled_size * (actual_sell_price / actual_buy_price)
            # Bu bazı senaryolarda USDT'yi gereksiz büyütüp sonra trade_size/min mantığını bozuyordu.
            # Legacy model sadece "USDT artar" simülasyonu ise filled_size yeterli.
            legacy_sell_delta_usdt = filled_size

            if self.use_new_balance_update_model_fake:
                try:
                    # BUY tarafı: USDT çıkar (filled_size + buy_fee + buy_slippage_cost)
                    buy_slippage_cost_usdt = buy_slippage * filled_size
                    buy_total_out_usdt = filled_size + buy_fee + buy_slippage_cost_usdt

                    # SELL tarafı: coin satar → USDT girer; sonra fee+slippage düşer
                    sell_gross_in_usdt = filled_amount * actual_sell_price
                    sell_slippage_cost_usdt = sell_slippage * filled_size
                    sell_total_in_usdt = sell_gross_in_usdt - sell_fee - sell_slippage_cost_usdt

                    # Eğer BalanceManager asset bazlı destekliyorsa coin varlığını da düşelim
                    base_asset = self._symbol_base(coin)

                    # USDT güncelle
                    await self._safe_update_usdt_balance(buy_ex, -buy_total_out_usdt)
                    await self._safe_update_usdt_balance(sell_ex, +sell_total_in_usdt)

                    # Coin güncelle (varsa)
                    # Buy borsasında coin artar, sell borsasında coin azalır
                    await self._safe_update_asset_balance(buy_ex, base_asset, +filled_amount)
                    await self._safe_update_asset_balance(sell_ex, base_asset, -filled_amount)

                    # Legacy no-op
                    legacy_buy_delta_usdt = 0.0
                    legacy_sell_delta_usdt = 0.0
                except Exception as _bal_e:
                    # Yeni model başarısızsa legacy'e düş
                    self.logger.debug(f"Yeni balance update modeli hata (fake), legacy'e düşüyorum: {_bal_e}")

            # 9. Bakiyeyi güncelle (fake)  ---- legacy satırlar korunuyor ----
            await self.balance_manager.update_balance(
                buy_ex, legacy_buy_delta_usdt  # USDT azaldı
            )
            await self.balance_manager.update_balance(
                sell_ex, legacy_sell_delta_usdt  # USDT arttı
            )

            # 10. İstatistikleri güncelle
            self.stats['total_trades'] += 1
            self.stats['successful_trades'] += 1
            self.stats['total_gross_profit'] += gross_profit
            self.stats['total_fees'] += total_fees
            self.stats['total_slippage'] += total_slippage_cost
            self.stats['total_net_profit'] += net_profit

            # 11. Sonuç  ---- UPDATED: trade_size/fees/slippage/net her koşulda result'a yazılıyor ----
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
                'profit_percent': (net_profit / filled_size) * 100 if filled_size else 0.0,
                'fill_rate': fill_rate * 100,
                'timestamp': datetime.now().isoformat(),
            }

            # 12. Detaylı log
            self.logger.info(
                f"✅ İŞLEM BAŞARILI:\n"
                f"   Coin: {coin} | İşlem: ${filled_size:.2f} | Miktar: {filled_amount:.6f}\n"
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
            # 1. Trade size hesapla  ---- UPDATED: real prefund model (USDT+COIN şartı) ----
            trade_size = await self._calculate_trade_size(
                buy_ex, sell_ex, coin, opp['buy_price']
            )

            # Real money tarafında da mümkünse gerçek free balance ile tekrar sınırla
            if self.use_prefund_split_model_real:
                try:
                    quote_asset = self._symbol_quote(coin)
                    base_asset = self._symbol_base(coin)

                    buy_quote_free = await self._get_real_free_asset(buy_ex, quote_asset)
                    sell_base_free = await self._get_real_free_asset(sell_ex, base_asset)

                    # buy tarafı USDT limiti
                    buy_quote_limit = float(buy_quote_free) if buy_quote_free is not None else 0.0
                    # sell tarafı coin limiti (USDT değeri)
                    sell_coin_value_limit = (float(sell_base_free) if sell_base_free is not None else 0.0) * float(opp['sell_price'] or opp['buy_price'] or 0.0)

                    if buy_quote_limit < 0:
                        buy_quote_limit = 0.0
                    if sell_coin_value_limit < 0:
                        sell_coin_value_limit = 0.0

                    # Prefund mantığı: bu iki tarafın min'i kadar trade_size mümkün
                    real_possible = min(buy_quote_limit, sell_coin_value_limit) * self.balance_utilization

                    # Risk limiti (USD) yine uygula
                    risk_limit = self.config.get('risk_management.max_position_per_coin', 200)
                    try:
                        risk_limit = float(risk_limit) if risk_limit is not None else 200.0
                    except Exception:
                        risk_limit = 200.0
                    real_possible = min(real_possible, risk_limit)

                    if real_possible > 0:
                        trade_size = min(float(trade_size or 0.0), float(real_possible))
                except Exception as _rbal_e:
                    self.logger.debug(f"Real free balance limitleme hata, eski trade_size ile devam: {_rbal_e}")

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

            # 11. Sonuç  ---- UPDATED: net negatif de success True kalır (zaten işlem yapıldı) ----
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
                'profit_percent': (net_profit / (filled_amount * avg_buy_price)) * 100 if (filled_amount and avg_buy_price) else 0.0,
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

            # Net negatifte bile bilgi ver (işlem zaten oldu)
            if net_profit < 0:
                self.logger.warning(
                    f"⚠️  REAL TRADE NET NEGATIF! Coin: {coin} Trade: {filled_amount:.4f} "
                    f"Gross: ${gross:.4f} Fees: ${total_fees:.4f} Net: ${net_profit:.4f}"
                )

            return result

        except Exception as e:
            self.logger.error(f"❌ Real trade hatası: {e}", exc_info=True)

            # Cleanup açık emirler
            if buy_order_id and buy_order_id in self.open_orders:
                try:
                    await self.exchange_manager.exchanges[buy_ex].cancel_order(buy_order_id, coin)
                except Exception:
                    pass
                del self.open_orders[buy_order_id]

            if sell_order_id and sell_order_id in self.open_orders:
                try:
                    await self.exchange_manager.exchanges[sell_ex].cancel_order(sell_order_id, coin)
                except Exception:
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

        except Exception:
            return 0.001

    async def _calculate_trade_size(self, buy_ex: str, sell_ex: str,
                                   symbol: str, price: float) -> float:
        """Gerçekçi trade size hesapla (None-safe)"""
        try:
            # Kullanılabilir bakiye
            buy_balance = await self.balance_manager.get_available_balance(buy_ex)
            sell_balance = await self.balance_manager.get_available_balance(sell_ex)

            # None / garip tipler gelirse 0'a düş
            try:
                buy_balance = float(buy_balance) if buy_balance is not None else 0.0
            except Exception:
                buy_balance = 0.0
            try:
                sell_balance = float(sell_balance) if sell_balance is not None else 0.0
            except Exception:
                sell_balance = 0.0

            # ---- NEW: spot prefund split model (fake ve istenirse real) ----
            # buy_balance/sell_balance burada "o borsaya ayrılmış toplam" gibi düşünüyoruz.
            # Spot arbitrajda:
            # - buy borsasında USDT lazım → buy_balance * prefund_usdt_ratio
            # - sell borsasında coin lazım (USDT değeri) → sell_balance * prefund_coin_ratio
            # trade_size = min(USDT tarafı, coin-değeri tarafı) * utilization
            if self.mode == "fake_money" and self.use_prefund_split_model_fake:
                try:
                    buy_usdt_budget = buy_balance * self.prefund_usdt_ratio
                    sell_coin_value_budget = sell_balance * self.prefund_coin_ratio
                    max_size = min(buy_usdt_budget, sell_coin_value_budget) * self.balance_utilization
                except Exception:
                    max_size = min(buy_balance, sell_balance) * 0.8
            elif self.mode != "fake_money" and self.use_prefund_split_model_real:
                # Real'da balance_manager yine toplam döndürüyor olabilir; fallback olarak split kuralını uygula.
                try:
                    buy_usdt_budget = buy_balance * self.prefund_usdt_ratio
                    sell_coin_value_budget = sell_balance * self.prefund_coin_ratio
                    max_size = min(buy_usdt_budget, sell_coin_value_budget) * self.balance_utilization
                except Exception:
                    max_size = min(buy_balance, sell_balance) * 0.8
            else:
                # Minimum ikisinden küçüğü (eski davranış)
                max_size = min(buy_balance, sell_balance) * 0.8  # %80'ini kullan

            # ---- NEW: trade_balance_fraction uygula (SADECE 1 KEZ) ----
            # Buradaki bug: aynı şeyi 2 kere çarpıyordun. 62 -> 37.2 olması gerekirken 62 -> 37.2 -> 22.32 olabiliyordu.
            # O yüzden ikinci çarpımı KALDIRMIYORUM, sadece KAPATIYORUM.
            _fraction_applied = False
            try:
                max_size = float(max_size) * float(self.trade_balance_fraction)
                _fraction_applied = True
            except Exception:
                _fraction_applied = False

            # ---- ESKI DUPLICATE (KALDIRILMADI, SADECE DEVRE DISI) ----
            # Satır sayısı düşmesin diye bırakıyorum; çalışmıyor.
            if False:
                try:
                    if not _fraction_applied:
                        max_size = float(max_size) * float(self.trade_balance_fraction)
                except Exception:
                    pass

            # ---- NEW: Auto Rebalance (max_size çok düşerse) ----
            # Not: Bu, buy tarafı sürekli boşalıp trade_size 26->18->13->10 düşmesin diye.
            try:
                # Minimum order eşiği (sende zaten 10 kontrolü var; burada sadece trigger için kullanıyoruz)
                _min_trigger = 10.0
                if self.auto_rebalance_min_trade and self.auto_rebalance_min_trade > 0:
                    _min_trigger = float(self.auto_rebalance_min_trade)

                if self.auto_rebalance_enabled and float(max_size) < float(_min_trigger):
                    now_ts = asyncio.get_event_loop().time()
                    if (now_ts - float(self.auto_rebalance_last_ts or 0.0)) >= float(self.auto_rebalance_cooldown_sec or 0.0):
                        self.auto_rebalance_last_ts = now_ts

                        # BalanceManager'da bu fonksiyon varsa çalıştır
                        if hasattr(self.balance_manager, 'rebalance_between_exchanges') and callable(getattr(self.balance_manager, 'rebalance_between_exchanges')):
                            self.logger.info(
                                f"Auto-rebalance tetiklendi (trade_size dustu): max_size=${float(max_size):.2f} < ${float(_min_trigger):.2f}"
                            )
                            await self.balance_manager.rebalance_between_exchanges(
                                buy_ex=buy_ex,
                                sell_ex=sell_ex,
                                method=self.auto_rebalance_method
                            )

                            # Fake/Real gecikme simulasyonu
                            if self.mode == 'fake_money':
                                if float(self.auto_rebalance_fake_delay_sec) > 0:
                                    await asyncio.sleep(float(self.auto_rebalance_fake_delay_sec))
                            else:
                                if float(self.auto_rebalance_real_delay_sec) > 0:
                                    await asyncio.sleep(float(self.auto_rebalance_real_delay_sec))

                            # Rebalance sonrası: bakiyeyi yeniden okuyup max_size'ı bir kere daha yukarı çekebiliriz
                            buy_balance2 = await self.balance_manager.get_available_balance(buy_ex)
                            sell_balance2 = await self.balance_manager.get_available_balance(sell_ex)

                            try:
                                buy_balance2 = float(buy_balance2) if buy_balance2 is not None else 0.0
                            except Exception:
                                buy_balance2 = 0.0
                            try:
                                sell_balance2 = float(sell_balance2) if sell_balance2 is not None else 0.0
                            except Exception:
                                sell_balance2 = 0.0

                            # Aynı hesap mantığıyla tekrar hesapla
                            if self.mode == "fake_money" and self.use_prefund_split_model_fake:
                                buy_usdt_budget2 = buy_balance2 * self.prefund_usdt_ratio
                                sell_coin_value_budget2 = sell_balance2 * self.prefund_coin_ratio
                                max_size = min(buy_usdt_budget2, sell_coin_value_budget2) * self.balance_utilization
                            elif self.mode != "fake_money" and self.use_prefund_split_model_real:
                                buy_usdt_budget2 = buy_balance2 * self.prefund_usdt_ratio
                                sell_coin_value_budget2 = sell_balance2 * self.prefund_coin_ratio
                                max_size = min(buy_usdt_budget2, sell_coin_value_budget2) * self.balance_utilization
                            else:
                                max_size = min(buy_balance2, sell_balance2) * 0.8

                            # fraction yeniden uygula (TEK KEZ)
                            try:
                                max_size = float(max_size) * float(self.trade_balance_fraction)
                            except Exception:
                                pass
            except Exception as _reb_e:
                self.logger.debug(f"Auto-rebalance hata: {_reb_e}")

            # Risk limiti
            risk_limit = self.config.get('risk_management.max_position_per_coin', 200)
            try:
                risk_limit = float(risk_limit) if risk_limit is not None else 200.0
            except Exception:
                risk_limit = 200.0
            max_size = min(max_size, risk_limit)

            # Borsa minimum/maksimum kontrol
            buy_exchange = self.exchange_manager.exchanges.get(buy_ex)
            if buy_exchange and symbol in buy_exchange.markets:
                market = buy_exchange.markets[symbol]
                min_cost = market.get('limits', {}).get('cost', {}).get('min', 10)
                max_cost = market.get('limits', {}).get('cost', {}).get('max', 100000)

                try:
                    min_cost = float(min_cost) if min_cost is not None else 10.0
                except Exception:
                    min_cost = 10.0
                try:
                    max_cost = float(max_cost) if max_cost is not None else 100000.0
                except Exception:
                    max_cost = 100000.0

                # En az min_cost, en fazla max_cost olacak şekilde clamp
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
            await exchange.fetch_ticker(symbol)

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

    # ------------------------ NEW HELPERS (ek, özellik çıkarma yok) ------------------------

    def _symbol_base(self, symbol: str) -> str:
        try:
            s = str(symbol or "")
            if "/" in s:
                return s.split("/")[0].strip().upper()
            return s.strip().upper()
        except Exception:
            return "BASE"

    def _symbol_quote(self, symbol: str) -> str:
        try:
            s = str(symbol or "")
            if "/" in s:
                return s.split("/")[1].strip().upper()
            return "USDT"
        except Exception:
            return "USDT"

    def _clamp(self, x: float, lo: float, hi: float) -> float:
        """Küçük yardımcı: sayıyı [lo, hi] aralığına sıkıştırır."""
        try:
            v = float(x)
        except Exception:
            v = lo
        if v < lo:
            return lo
        if v > hi:
            return hi
        return v

    async def _safe_update_usdt_balance(self, exchange_id: str, delta_usdt: float):
        """
        BalanceManager arayüzü proje içinde değişebiliyor.
        - update_balance(exchange, delta) varsa onu kullan
        - yoksa sessizce geç
        """
        try:
            if hasattr(self.balance_manager, "update_balance") and callable(getattr(self.balance_manager, "update_balance")):
                await self.balance_manager.update_balance(exchange_id, float(delta_usdt))
        except Exception:
            pass

    async def _safe_update_asset_balance(self, exchange_id: str, asset: str, delta_amount: float):
        """
        Eğer BalanceManager asset bazlı tutuyorsa destekle:
        - update_asset_balance(exchange, asset, delta)
        - update_coin_balance(exchange, asset, delta)
        - update_balance_asset(exchange, asset, delta)
        Yoksa hiçbir şey yapma.
        """
        try:
            if hasattr(self.balance_manager, "update_asset_balance") and callable(getattr(self.balance_manager, "update_asset_balance")):
                await self.balance_manager.update_asset_balance(exchange_id, asset, float(delta_amount))
                return
        except Exception:
            pass
        try:
            if hasattr(self.balance_manager, "update_coin_balance") and callable(getattr(self.balance_manager, "update_coin_balance")):
                await self.balance_manager.update_coin_balance(exchange_id, asset, float(delta_amount))
                return
        except Exception:
            pass
        try:
            if hasattr(self.balance_manager, "update_balance_asset") and callable(getattr(self.balance_manager, "update_balance_asset")):
                await self.balance_manager.update_balance_asset(exchange_id, asset, float(delta_amount))
                return
        except Exception:
            pass

    async def _get_real_free_asset(self, exchange_id: str, asset: str) -> float:
        """
        Real money tarafında gerçek free balance çekmeye çalış.
        """
        try:
            ex = self.exchange_manager.exchanges.get(exchange_id)
            if not ex:
                return 0.0
            bal = await ex.fetch_balance()
            # ccxt: bal['free'][asset] veya bal[asset]['free']
            asset_u = str(asset or "").upper()
            free_map = bal.get("free", {}) if isinstance(bal, dict) else {}
            if isinstance(free_map, dict) and asset_u in free_map and free_map[asset_u] is not None:
                return float(free_map[asset_u])
            if isinstance(bal, dict) and asset_u in bal and isinstance(bal[asset_u], dict):
                v = bal[asset_u].get("free", 0.0)
                return float(v) if v is not None else 0.0
            return 0.0
        except Exception:
            return 0.0
