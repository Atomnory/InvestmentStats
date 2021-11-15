import requests
from decimal import Decimal, ROUND_HALF_UP

from config.settings import EXCHANGE_API_KEY
from .models import ExchangeRate
from .utils import get_today


class Exchanger:
    def __init__(self):
        self._rates_data = None
        self._exr_obj = None
        self._today = get_today()
        self._update_rates()

    def _update_rates(self):
        self._try_get_exchange_rate()
        if self._is_exchange_rate_object_expired():
            self._request_conversion_rates_data()
            self._update_exchange_rate_object()

    def _try_get_exchange_rate(self):
        try:
            self._get_exchange_rate_object()
        except ExchangeRate.DoesNotExist:
            self._create_exchange_rate_object()

    def _is_exchange_rate_object_expired(self) -> bool:
        return True if self._exr_obj.last_updated != self._today else False

    def _update_exchange_rate_object(self):
        self._exr_obj.eur_rate = self._rates_data['EUR']
        self._exr_obj.rub_rate = self._rates_data['RUB']
        self._exr_obj.save()
        print('$$ Exchange rate is expired. Getting update.')

    def _get_exchange_rate_object(self):
        self._exr_obj = ExchangeRate.objects.get(pk=1)

    def _create_exchange_rate_object(self):
        self._request_conversion_rates_data()
        self._create_exchange_rate()
        print('$$ Create new ExchangeRate')

    def _request_conversion_rates_data(self):
        url = f'https://v6.exchangerate-api.com/v6/{EXCHANGE_API_KEY}/latest/USD'
        response = requests.get(url)
        self._rates_data = response.json()['conversion_rates']

    def _create_exchange_rate(self):
        self._exr_obj = ExchangeRate(pk=1, last_updated=self._today, eur_rate=self._rates_data['EUR'],
                                     rub_rate=self._rates_data['RUB'])
        self._exr_obj.save()

    @property
    def eur_rate(self) -> Decimal:
        return Decimal(self._exr_obj.eur_rate).quantize(Decimal('1.01'), rounding=ROUND_HALF_UP)

    @property
    def rub_rate(self) -> Decimal:
        return Decimal(self._exr_obj.rub_rate).quantize(Decimal('1.01'), rounding=ROUND_HALF_UP)
