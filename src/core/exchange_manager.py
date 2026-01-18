# -*- coding: utf-8 -*-
"""Exchange Manager - Borsa baÄŸlantÄ±larÄ±nÄ± yÃ¶netir"""

import asyncio
import ssl
import certifi
import aiohttp
from aiohttp.resolver import ThreadedResolver

import ccxt.async_support as ccxt
from src.utils.logger import get_logger


class ExchangeManager:
    def __init__(self, config, mode):
        self.config = config
        self.mode = mode
        self.logger = get_logger('exchange_manager')
        self.exchanges = {}

        # tek bir shared aiohttp session (CCXT hepsinde bunu kullanacak)
        self._session: aiohttp.ClientSession | None = None

    def _get_exchange_cfg(self, exchange_id: str) -> dict:
        # config'te iki farklÄ± yerde arÄ±yoruz (senin projende ikisi de gÃ¶rÃ¼ldÃ¼)
        for key in (exchange_id, f"exchanges.{exchange_id}"):
            try:
                cfg = self.config.get(key, {}) or {}
                if isinstance(cfg, dict) and cfg:
                    return cfg
            except Exception:
                pass
        return {}

    def _fmt_exc(self, e: Exception) -> str:
        msg = f"{type(e).__name__}: {repr(e)}"
        if getattr(e, "__cause__", None):
            msg += f" | cause={type(e.__cause__).__name__}: {repr(e.__cause__)}"
        if getattr(e, "__context__", None):
            msg += f" | context={type(e.__context__).__name__}: {repr(e.__context__)}"
        return msg

    def _make_ssl_context(self) -> ssl.SSLContext:
        # Windows'ta cert store bazen gariplik yapabiliyor â†’ certifi ile sabitle
        return ssl.create_default_context(cafile=certifi.where())

    async def _ensure_http_session(self) -> None:
        """
        aiodns KULLANMIYORUZ.
        ThreadedResolver = Windows sistem DNS'i (Invoke-WebRequest gibi) kullanÄ±r.
        """
        if self._session and not self._session.closed:
            return

        resolver = ThreadedResolver()

        connector = aiohttp.TCPConnector(
            resolver=resolver,
            ssl=self._make_ssl_context(),
            use_dns_cache=True,
            ttl_dns_cache=300,
            limit=100,
            enable_cleanup_closed=True,
        )

        # trust_env=True: eÄŸer sistemde proxy/vpn env varsa dikkate al
        self._session = aiohttp.ClientSession(connector=connector, trust_env=True)
        self.logger.debug("Shared aiohttp session hazir (ThreadedResolver)")

    async def _load_markets_with_retry(self, exchange, exchange_id: str, retries: int = 3) -> bool:
        last_err = None
        for attempt in range(1, retries + 1):
            try:
                await exchange.load_markets()
                mcount = len(getattr(exchange, "markets", {}) or {})
                self.logger.info(f"OK {exchange_id} markets yÃ¼klendi ({mcount} market)")
                return True
            except Exception as e:
                last_err = e
                self.logger.warning(f"! {exchange_id} load_markets deneme {attempt}/{retries} basarisiz: {self._fmt_exc(e)}")
                await asyncio.sleep(1.0)

        self.logger.error(f"X {exchange_id} markets yÃ¼klenemedi: {self._fmt_exc(last_err)}")
        return False

    async def initialize(self):
        enabled_exchanges = self.config.get('exchanges.enabled', [])
        self.logger.info(f"Borsalar yukleniyor: {', '.join(enabled_exchanges)}")

        if not enabled_exchanges:
            raise Exception("exchanges.enabled boÅŸ! config'te borsa yok.")

        await self._ensure_http_session()

        # CCXT instance'larÄ± yarat
        for exchange_id in enabled_exchanges:
            try:
                ex_config = self._get_exchange_cfg(exchange_id)

                if not hasattr(ccxt, exchange_id):
                    self.logger.error(f"X {exchange_id} ccxt'te yok (id hatalÄ± olabilir)")
                    continue

                exchange_class = getattr(ccxt, exchange_id)

                params = {
                    'enableRateLimit': True,
                    'timeout': 60000,
                    'options': {
                        'defaultType': 'spot',
                        'adjustForTimeDifference': True,
                    },
                    # kritik: bizim session'Ä± ccxt'ye veriyoruz
                    'session': self._session,
                    # trust_env: proxy/vpn varsa
                    'aiohttp_trust_env': True,
                }

                # Real money keys
                if self.mode == 'real_money' and ex_config.get('apiKey'):
                    params['apiKey'] = ex_config.get('apiKey')
                    params['secret'] = ex_config.get('secret')
                    if ex_config.get('password'):
                        params['password'] = ex_config.get('password')

                exchange = exchange_class(params)

                ok = await self._load_markets_with_retry(exchange, exchange_id, retries=3)
                if not ok:
                    try:
                        await exchange.close()
                    except Exception:
                        pass
                    continue

                self.exchanges[exchange_id] = exchange

            except Exception as e:
                self.logger.error(f"X {exchange_id} kurulum HATA: {self._fmt_exc(e)}")

        if len(self.exchanges) == 0:
            self.logger.error("HICBIR BORSA BAGLANAMADI!")
            raise Exception("No exchanges connected!")
        else:
            self.logger.info(f"Toplam {len(self.exchanges)} borsa hazir")

    async def close_all(self):
        # Ã¶nce ccxt exchange'leri kapat
        for exchange_id, exchange in list(self.exchanges.items()):
            try:
                await exchange.close()
            except Exception as e:
                self.logger.debug(f"{exchange_id} kapatma hatasi: {self._fmt_exc(e)}")

        self.exchanges.clear()

        # sonra shared session kapat
        if self._session and not self._session.closed:
            try:
                await self._session.close()
            except Exception:
                pass
        self._session = None







    def pick_first_available_symbol(self, preferred_quote: str = "USDT") -> str | None:
        """
        Heartbeat/test amaÃ§lÄ±:
        Marketler yÃ¼klendikten sonra sistemin gerÃ§ekten hazÄ±r olduÄŸunu gÃ¶rmek iÃ§in
        'ilk uygun symbol' dÃ¶ndÃ¼rÃ¼r.

        Ã–rn: 'BTC/USDT' gibi bir ÅŸey dÃ¶nebilir.
        """
        for ex_id, ex in self.exchanges.items():
            markets = getattr(ex, "markets", None) or {}
            if not markets:
                continue

            # Ã¶nce USDT olanlarÄ± dene
            if preferred_quote:
                for symbol, m in markets.items():
                    try:
                        if symbol and f"/{preferred_quote}" in symbol and m.get("active", True):
                            return symbol
                    except Exception:
                        continue

            # fallback: aktif ilk symbol
            for symbol, m in markets.items():
                try:
                    if symbol and m.get("active", True):
                        return symbol
                except Exception:
                    continue

        return None




