# -*- coding: utf-8 -*-
"""Spot Arbitrage Strategy"""
from src.utils.logger import get_logger


class SpotArbitrageStrategy:
    def __init__(self, config, orderbook_manager, balance_manager):
        self.config = config
        self.orderbook_manager = orderbook_manager
        self.balance_manager = balance_manager
        self.logger = get_logger('spot_arbitrage')

        # Spread filtresi
        self.min_spread = float(config.get('strategy.spot_arbitrage.min_spread_percent', 0.8))

        # Quote
        self.quote = str(config.get('strategy.spot_arbitrage.quote', 'USDT')).upper()

        # --- AUTO sizing parametreleri (elle ayar gerekmesin diye default'lar mantÄ±klÄ± seÃ§ildi) ---
        # Minimum iÅŸlem (borsa min notional iÃ§in de iÅŸe yarar)
        self.min_amount_quote = float(config.get('strategy.spot_arbitrage.min_amount_usdt', 10.0))

        # Tek iÅŸlemde â€œusableâ€ bakiyenin kaÃ§Ä±nÄ± kullansÄ±n
        self.entry_fraction = float(config.get('strategy.spot_arbitrage.entry_fraction', 0.25))  # %25

        # Tek iÅŸlemde max usable yÃ¼zdesi (asla tÃ¼m parayÄ± basmasÄ±n)
        self.max_usable_fraction = float(config.get('strategy.spot_arbitrage.max_usable_fraction', 0.60))  # %60

        # Reserve: hem sabit hem yÃ¼zde (bÃ¼yÃ¼yen bakiyede otomatik artsÄ±n)
        self.reserve_min = float(config.get('strategy.spot_arbitrage.reserve_min_usdt', 5.0))    # en az 5$
        self.reserve_pct = float(config.get('strategy.spot_arbitrage.reserve_pct', 0.10))       # free'Ä±n %10'u

        # Soft cap: bakiyen bÃ¼yÃ¼yÃ¼nce tek iÅŸlem abartmasÄ±n (tamamen otomatik)
        self.soft_cap_min = float(config.get('strategy.spot_arbitrage.soft_cap_min_usdt', 25.0))  # en az 25$
        self.soft_cap_pct = float(config.get('strategy.spot_arbitrage.soft_cap_pct', 0.40))       # usableâ€™Ä±n %40â€™Ä±

    def _to_symbol(self, coin: str) -> str:
        coin = str(coin).strip()
        if not coin:
            return coin
        if "/" in coin:
            return coin
        return f"{coin}/{self.quote}"

    def _pick_amount(self, buy_exchange_id: str) -> float:
        """
        Tam auto sizing:
        - Reserve = max(reserve_min, free * reserve_pct)
        - usable = free - reserve
        - amount = usable * entry_fraction
        - clamp: min_amount <= amount <= min(usable*max_usable_fraction, soft_cap)
        """
        free_quote = self.balance_manager.get_free(buy_exchange_id, self.quote)
        if free_quote <= 0:
            return 0.0

        reserve = max(self.reserve_min, free_quote * self.reserve_pct)
        usable = max(0.0, free_quote - reserve)
        if usable < self.min_amount_quote:
            return 0.0

        amount = usable * self.entry_fraction

        max_by_usable = usable * self.max_usable_fraction
        soft_cap = max(self.soft_cap_min, usable * self.soft_cap_pct)

        amount = max(self.min_amount_quote, amount)
        amount = min(amount, max_by_usable, soft_cap)

        return float(round(amount, 2))

    async def find_opportunities(self):
        opportunities = []

        try:
            coins = self.config.get('coins.priority_list', [])[:10]
            exchanges = list(self.orderbook_manager.exchange_manager.exchanges.keys())

            if len(exchanges) < 2:
                self.logger.warning("En az 2 borsa gerekli")
                return opportunities

            for coin in coins:
                symbol = self._to_symbol(coin)
                if not symbol:
                    continue

                prices = {}
                for exchange_id in exchanges:
                    try:
                        orderbook = await self.orderbook_manager.get_orderbook(exchange_id, symbol)
                        if (
                            orderbook
                            and orderbook.get('asks')
                            and orderbook.get('bids')
                            and orderbook['asks']
                            and orderbook['bids']
                        ):
                            prices[exchange_id] = {
                                'ask': float(orderbook['asks'][0][0]),
                                'bid': float(orderbook['bids'][0][0]),
                            }
                    except Exception:
                        pass

                if len(prices) < 2:
                    continue

                for buy_ex in prices:
                    for sell_ex in prices:
                        if buy_ex == sell_ex:
                            continue

                        buy_price = prices[buy_ex]['ask']
                        sell_price = prices[sell_ex]['bid']
                        if buy_price <= 0:
                            continue

                        spread = ((sell_price - buy_price) / buy_price) * 100.0
                        if spread < self.min_spread:
                            continue

                        amount = self._pick_amount(buy_ex)
                        if amount <= 0:
                            continue

                        opportunities.append({
                            'coin': symbol,
                            'buy_exchange': buy_ex,
                            'sell_exchange': sell_ex,
                            'buy_price': buy_price,
                            'sell_price': sell_price,
                            'spread': spread,
                            'profit_score': spread,
                            'amount': amount,
                            'estimated_profit': amount * (spread / 100.0),
                        })

        except Exception as e:
            self.logger.error(f"Firsat tarama hatasi: {e}")

        return opportunities



