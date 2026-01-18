# -*- coding: utf-8 -*-
"""OrderBook Manager - Orderbook verilerini yÃ¶netir"""
import asyncio
from src.utils.logger import get_logger


class OrderBookManager:
    def __init__(self, config, exchange_manager):
        self.config = config
        self.exchange_manager = exchange_manager
        self.logger = get_logger('orderbook_manager')

        # orderbooks: {exchange_id: {symbol: orderbook}}
        self.orderbooks = {}

        self.is_running = False

        # cache: { "ex:symbol": {"data":..., "timestamp":...} }
        self.cache = {}

        # basit TTL (saniye): aynÄ± anda 6 borsaya abanmayÄ± keser
        self.cache_ttl_seconds = float(
            self.config.get('advanced.orderbook_cache_ttl_seconds', 2.0)
            if hasattr(self.config, "get") else 2.0
        )

        # arka plan preload ister misin?
        self.preload_enabled = bool(
            self.config.get('advanced.orderbook_preload', False)
            if hasattr(self.config, "get") else False
        )
        self.preload_interval = float(
            self.config.get('advanced.orderbook_preload_interval_seconds', 5.0)
            if hasattr(self.config, "get") else 5.0
        )

        self._task = None

    async def start(self):
        """Orderbook yÃ¶neticisini baÅŸlat"""
        self.is_running = True
        self.logger.info("OrderBook Manager baslatildi")

        # Ä°steÄŸe baÄŸlÄ± preload task
        if self.preload_enabled and self._task is None:
            self._task = asyncio.create_task(self._preload_loop())
            self.logger.info("OrderBook preload loop baslatildi")

    def _now(self) -> float:
        return asyncio.get_event_loop().time()

    def _cache_get(self, exchange_id: str, symbol: str):
        key = f"{exchange_id}:{symbol}"
        item = self.cache.get(key)
        if not item:
            return None
        if self._now() - item["timestamp"] <= self.cache_ttl_seconds:
            return item["data"]
        return None

    def _cache_set(self, exchange_id: str, symbol: str, orderbook):
        key = f"{exchange_id}:{symbol}"
        self.cache[key] = {"data": orderbook, "timestamp": self._now()}

    def _store(self, exchange_id: str, symbol: str, orderbook):
        self.orderbooks.setdefault(exchange_id, {})
        self.orderbooks[exchange_id][symbol] = orderbook

    async def get_orderbook(self, exchange_id, symbol):
        """Bir symbol iÃ§in orderbook al"""
        try:
            exchange = self.exchange_manager.exchanges.get(exchange_id)
            if not exchange:
                return None

            # 1) cache varsa direkt dÃ¶n (API yÃ¼kÃ¼nÃ¼ azaltÄ±r)
            cached = self._cache_get(exchange_id, symbol)
            if cached is not None:
                return cached

            # 2) API'den Ã§ek
            orderbook = await exchange.fetch_order_book(symbol, limit=5)

            # 3) cache + store
            self._cache_set(exchange_id, symbol, orderbook)
            self._store(exchange_id, symbol, orderbook)

            # 4) HEARTBEAT: bid/ask log (API Ã§ekiyor mu kanÄ±tÄ±)
            bid = orderbook.get("bids", [[None]])[0][0] if orderbook else None
            ask = orderbook.get("asks", [[None]])[0][0] if orderbook else None
            self.logger.info(f"OB {exchange_id} {symbol} bid={bid} ask={ask}")

            return orderbook

        except Exception as e:
            # INFO deÄŸil DEBUG: konsolu boÄŸmayalÄ±m ama gÃ¶rmek istersen verbose ile aÃ§arsÄ±n
            error_msg = str(e)[:120]
            self.logger.debug(f"Orderbook hata: {exchange_id} {symbol}: {error_msg}")
            return None

    async def _preload_loop(self):
        """
        Ä°steÄŸe baÄŸlÄ±: config'teki borsa+coin listesine gÃ¶re orderbook'larÄ± arka planda doldurur.
        Strateji hazÄ±r veriyi okursa Ã§ok hÄ±zlanÄ±r.
        """
        try:
            while self.is_running:
                exchanges = []
                coins = []
                try:
                    # ConfigLoader sÄ±nÄ±fÄ±ndaysa .get vardÄ±r
                    exchanges = self.config.get('exchanges.enabled') or []
                    coins = self.config.get('coins.priority_list') or []
                except Exception:
                    pass

                # coin listesi BTC gibi gelirse symbol'a Ã§evirelim
                # VarsayÄ±m: USDT bazlÄ± izlemek istiyoruz
                symbols = []
                for c in coins:
                    c = str(c).strip()
                    if not c:
                        continue
                    if "/" in c:
                        symbols.append(c)
                    else:
                        symbols.append(f"{c}/USDT")

                for ex_id in exchanges:
                    for sym in symbols[:10]:  # preload sÄ±nÄ±r (rate limit yemeyelim)
                        await self.get_orderbook(ex_id, sym)

                await asyncio.sleep(self.preload_interval)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.logger.error(f"Preload loop hata: {e}", exc_info=True)

    async def stop(self):
        """Orderbook yÃ¶neticisini durdur"""
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except Exception:
                pass
            self._task = None
        self.logger.info("OrderBook Manager durduruldu")



