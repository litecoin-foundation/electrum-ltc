import os.path
from decimal import Decimal

from electrum.exchange_rate import CoinGecko, ExchangeBase, HISTORY_CACHE_ASSET

from . import ElectrumTestCase


class TestExchangeRate(ElectrumTestCase):

    async def test_coingecko_uses_litecoin_spot_and_history_endpoints(self):
        requests = []
        exchange = CoinGecko(None, None)

        async def get_json(site, path):
            requests.append((site, path))
            if 'market_chart' in path:
                return {'prices': [[0, 42.5]]}
            return {'market_data': {'current_price': {'usd': 84.25, 'eur': 77.5}}}

        exchange.get_json = get_json

        self.assertEqual({'USD': Decimal('84.25'), 'EUR': Decimal('77.5')},
                         await exchange.request_spot_rates('USD'))
        self.assertEqual({'1970-01-01': Decimal('42.5')}, await exchange.request_history('USD'))
        self.assertEqual([
            ('api.coingecko.com',
             '/api/v3/coins/litecoin?localization=false&tickers=false&'
             'community_data=false&developer_data=false&sparkline=false'),
            ('api.coingecko.com', '/api/v3/coins/litecoin/market_chart?vs_currency=USD&days=365'),
        ], requests)

    def test_ltc_is_the_base_currency(self):
        exchange = ExchangeBase(None, None)
        exchange._quotes = {'BTC': Decimal('123456')}
        exchange._quotes_timestamp = float('inf')

        self.assertEqual(Decimal(1), exchange.get_cached_spot_quote('LTC'))
        self.assertEqual(Decimal('123456'), exchange.get_cached_spot_quote('BTC'))

    def test_historical_cache_is_separate_from_bitcoin_cache(self):
        legacy_filename = os.path.join(self.electrum_path, 'CoinGecko_USD')
        with open(legacy_filename, 'w', encoding='utf-8') as f:
            f.write('{"2025-01-01": "100000"}')

        history, timestamp = ExchangeBase._read_historical_rates_from_file(
            exchange_name='CoinGecko', ccy='USD', cache_dir=self.electrum_path)

        self.assertIsNone(history)
        self.assertIsNone(timestamp)
        self.assertFalse(os.path.exists(
            os.path.join(self.electrum_path, f'CoinGecko_{HISTORY_CACHE_ASSET}_USD')))

        ExchangeBase._write_historical_rates_to_file(
            exchange_name='CoinGecko', ccy='USD', cache_dir=self.electrum_path,
            history={'2025-01-01': '42.50'})

        history, timestamp = ExchangeBase._read_historical_rates_from_file(
            exchange_name='CoinGecko', ccy='USD', cache_dir=self.electrum_path)

        self.assertEqual({'2025-01-01': '42.50'}, history)
        self.assertIsNotNone(timestamp)
