import os
import datetime
import shutil
import requests
from typing import Union
from decimal import Decimal, ROUND_HALF_UP

import matplotlib.pyplot as plt
from django.db.models.fields.files import ImageFieldFile, FileField
from django.http.request import QueryDict
from django.core.handlers.wsgi import WSGIRequest
from django.utils.functional import SimpleLazyObject
from django.db.models import Count

from config.settings import MEDIA_ROOT, EXCHANGE_API_KEY
from .models import ExchangeRate, Portfolio, PortfolioItem
from .forms import SecuritiesCreateForm, SecuritiesDeleteForm, SecuritiesIncreaseQuantityForm
from .forms import PortfolioCreateForm
from .tinkoff_client import update_security_price
# TODO: add sector, country, currency graphs creating and updating
# TODO: hide all graphs funcs in class Graph


def get_user_portfolios_list(user: SimpleLazyObject) -> list[Portfolio]:
    return user.portfolio_set.all()


def get_empty_creating_portfolio_form() -> PortfolioCreateForm:
    return PortfolioCreateForm()


def create_portfolio(request: WSGIRequest):
    form_creating = PortfolioCreateForm(request.POST)
    if form_creating.is_valid():
        new_portfolio = form_creating.save(commit=False)
        new_portfolio.investor = request.user
        new_portfolio.save()
        update_portfolio_graphs_path(new_portfolio)


def update_portfolio_graphs_path(portfolio: Portfolio):
    graph_path_security = GraphPath(portfolio.pk, 'security').graph_path
    portfolio.securities_graph = ImageFieldFile(instance=None, name=graph_path_security, field=FileField())
    graph_path_sector = GraphPath(portfolio.pk, 'sector').graph_path
    portfolio.sector_graph = ImageFieldFile(instance=None, name=graph_path_sector, field=FileField())
    graph_path_country = GraphPath(portfolio.pk, 'country').graph_path
    portfolio.country_graph = ImageFieldFile(instance=None, name=graph_path_country, field=FileField())
    graph_path_market = GraphPath(portfolio.pk, 'market').graph_path
    portfolio.market_graph = ImageFieldFile(instance=None, name=graph_path_market, field=FileField())
    graph_path_currency = GraphPath(portfolio.pk, 'currency').graph_path
    portfolio.currency_graph = ImageFieldFile(instance=None, name=graph_path_currency, field=FileField())
    portfolio.save()


def delete_portfolio(portfolio: Portfolio):
    shutil.rmtree(GraphPath(portfolio.pk, 'security').graph_full_root, ignore_errors=True)
    portfolio.delete()


def get_empty_portfolio_forms(portfolio: Portfolio) \
        -> dict[str, Union[SecuritiesCreateForm, SecuritiesDeleteForm, SecuritiesIncreaseQuantityForm]]:
    form_creating = SecuritiesCreateForm(portfolio)
    form_deleting = SecuritiesDeleteForm(portfolio)
    form_increasing = SecuritiesIncreaseQuantityForm(portfolio)

    return {'form_creating': form_creating,
            'form_deleting': form_deleting,
            'form_increasing': form_increasing}


def fill_portfolio_forms(portfolio: Portfolio, post: QueryDict):
    if 'create_security' in post:
        create_security(portfolio, post)
    elif 'delete_security' in post:
        delete_security(portfolio, post)
    elif 'increase_security' in post:
        increase_security(portfolio, post)


def create_security(portfolio: Portfolio, post: QueryDict):
    form_creating = SecuritiesCreateForm(portfolio, post)
    if form_creating.is_valid():
        security = form_creating.cleaned_data['security_select']
        quantity = int(form_creating.cleaned_data['quantity'])
        if quantity > 0:
            item = PortfolioItem(portfolio=portfolio, security=security, quantity=quantity)
            item.save()


def delete_security(portfolio: Portfolio, post: QueryDict):
    form_deleting = SecuritiesDeleteForm(portfolio, post)
    if form_deleting.is_valid():
        item = form_deleting.cleaned_data['field']
        item.delete()


def increase_security(portfolio: Portfolio, post: QueryDict):
    form_increasing = SecuritiesIncreaseQuantityForm(portfolio, post)
    if form_increasing.is_valid():
        item = form_increasing.cleaned_data['field']
        increment = int(form_increasing.cleaned_data['quantity'])
        if item.quantity + increment > 0:
            item.quantity += increment
        item.save()


def get_formatted_securities_list(portfolio: Portfolio) -> list[tuple[str, Decimal, str]]:
    items = get_updated_portfolio_items(portfolio)
    securities = []
    for row in items:
        cost = Decimal(row.security.price * row.quantity).quantize(Decimal('1.01'), rounding=ROUND_HALF_UP)
        securities.append((row.security.ticker, cost, row.security.currency))
    return securities


def get_updated_portfolio_items(portfolio: Portfolio) -> list[PortfolioItem]:
    items = get_portfolio_items(portfolio)
    for item in items:
        if item.security.last_updated != get_today():
            update_security_price(item.security)
    return items


def get_portfolio_items(portfolio: Portfolio) -> list[PortfolioItem]:
    return portfolio.portfolioitem_set.all()


def update_portfolio_graphs(portfolio: Portfolio):
    # TODO: make update graph only once per day and after item changing
    # plt.switch_backend('AGG')
    SecurityGraphDrawer(portfolio).update_graph()
    SectorGraphDrawer(portfolio).update_graph()
    CountryGraphDrawer(portfolio).update_graph()
    MarketGraphDrawer(portfolio).update_graph()
    CurrencyGraphDrawer(portfolio).update_graph()

# countries = Security.objects.order_by('country').distinct('country')
# for i in countries:
#     print(i.country)


class AbstractGraphDrawer:
    def __init__(self, portfolio: Portfolio):
        self._portfolio = portfolio
        self._graph_name = None
        self._graph_path = None
        self._fig = None
        self._axe = None
        self._cost = None
        self._labels = None
        self._calculator = AbstractGraphDataCalculator(portfolio)

    def update_graph(self):
        self._set_graph_path()
        self._update_graph_data()
        self._draw_graph()
        self._save_graph()

    def _set_graph_path(self):
        self._graph_path = GraphPath(self._portfolio.pk, self._graph_name)

    def _update_graph_data(self):
        self._cost = self._calculator.costs
        self._labels = self._calculator.labels

    def _draw_graph(self):
        plt.switch_backend('AGG')
        self._fig, self._axe = plt.subplots()
        self._axe.pie(self._cost, labels=self._labels, autopct='%1.1f%%')

    def _save_graph(self):
        os.makedirs(self._graph_path.graph_full_root, exist_ok=True)
        self._fig.savefig(self._graph_path.graph_full_path)


class SecurityGraphDrawer(AbstractGraphDrawer):
    def __init__(self, portfolio: Portfolio):
        super().__init__(portfolio)
        self._graph_name = 'security'
        self._calculator = SecurityGraphDataCalculator(portfolio)


class SectorGraphDrawer(AbstractGraphDrawer):
    def __init__(self, portfolio: Portfolio):
        super().__init__(portfolio)
        self._graph_name = 'sector'
        self._calculator = SectorGraphDataCalculator(portfolio)


class CountryGraphDrawer(AbstractGraphDrawer):
    def __init__(self, portfolio: Portfolio):
        super().__init__(portfolio)
        self._graph_name = 'country'
        self._calculator = CountryGraphDataCalculator(portfolio)


class MarketGraphDrawer(AbstractGraphDrawer):
    def __init__(self, portfolio: Portfolio):
        super().__init__(portfolio)
        self._graph_name = 'market'
        self._calculator = MarketGraphDataCalculator(portfolio)


class CurrencyGraphDrawer(AbstractGraphDrawer):
    def __init__(self, portfolio: Portfolio):
        super().__init__(portfolio)
        self._graph_name = 'currency'
        self._calculator = CurrencyGraphDataCalculator(portfolio)


class AbstractGraphDataCalculator:
    def __init__(self, portfolio: Portfolio):
        self._exchanger = Exchanger()
        self._items = get_portfolio_items(portfolio)
        self._costs = []
        self._labels = []
        self._item = None
        self._currency_divider = None
        self._cost = None

    def _update_graph_data(self):
        for item in self._items:
            self._item = item
            self._get_currency_divider()
            self._process_item()

    def _get_currency_divider(self):
        if self._item.security.currency == 'USD':
            self._currency_divider = 1
        elif self._item.security.currency == 'EUR':
            self._currency_divider = self._exchanger.eur_rate
        elif self._item.security.currency == 'RUB':
            self._currency_divider = self._exchanger.rub_rate

    def _process_item(self):
        pass

    def _calculate_cost(self):
        self._cost = (self._item.security.price / self._currency_divider) * self._item.quantity

    def _increase_existing_item(self, label: str):
        i = self._labels.index(label)
        self._costs[i] += self._cost

    def _append_new_item(self, label: str):
        self._costs.append(self._cost)
        self._labels.append(label)

    def _increase_label_cost_if_in_labels_or_append_new(self, label: str):
        self._calculate_cost()
        if label in self._labels:
            self._increase_existing_item(label)
        else:
            self._append_new_item(label)

    @property
    def costs(self):
        return self._costs

    @property
    def labels(self):
        return self._labels


class SecurityGraphDataCalculator(AbstractGraphDataCalculator):
    def __init__(self, portfolio: Portfolio):
        super().__init__(portfolio)
        self._update_graph_data()

    def _process_item(self):
        self._calculate_cost()
        self._append_new_item(self._item.security.ticker)


class SectorGraphDataCalculator(AbstractGraphDataCalculator):
    def __init__(self, portfolio: Portfolio):
        super().__init__(portfolio)
        self._update_graph_data()

    def _process_item(self):
        if self._item.security.sector is None:
            sector_name = 'Undefined sector'
        else:
            sector_name = self._item.security.get_sector_display()
        self._increase_label_cost_if_in_labels_or_append_new(sector_name)


class CountryGraphDataCalculator(AbstractGraphDataCalculator):
    def __init__(self, portfolio: Portfolio):
        super().__init__(portfolio)
        self._update_graph_data()

    def _process_item(self):
        if self._item.security.country is None:
            country_name = 'Undefined country'
        else:
            country_name = self._item.security.country.capitalize()
        self._increase_label_cost_if_in_labels_or_append_new(country_name)


class MarketGraphDataCalculator(AbstractGraphDataCalculator):
    def __init__(self, portfolio: Portfolio):
        super().__init__(portfolio)
        self._update_graph_data()

    def _process_item(self):
        # Emerging Markets
        # Developed Markets
        # All Country World
        if self._item.security.country == 'United States':
            market_name = self._item.security.country
        elif self._item.security.country == 'Russia':
            market_name = self._item.security.country
        elif self._item.security.country in (
                'Emerging Markets', 'Emerging markets', 'Kazakhstan', 'China', 'Taiwan', 'Brazil',
                'India', 'Mexico', 'Turkey', 'South Africa'):
            market_name = 'Emerging Markets'
        elif self._item.security.country in ('Developed Markets', 'Germany', 'Japan', 'France', 'Canada', 'Italy',
                                       'Netherlands', 'Norway', 'Portugal', 'South Korea', 'Spain', 'Belgium',
                                       'Switzerland', 'Israel'
                                                      'United Kingdom', 'Australia', 'Europe', 'Ireland', 'Sweden',
                                       'USA',
                                       'Bermuda'):
            market_name = 'Developed Markets'
        else:
            market_name = 'All Country World'
        self._increase_label_cost_if_in_labels_or_append_new(market_name)


class CurrencyGraphDataCalculator(AbstractGraphDataCalculator):
    def __init__(self, portfolio: Portfolio):
        super().__init__(portfolio)
        self._update_graph_data()

    def _process_item(self):
        self._increase_label_cost_if_in_labels_or_append_new(self._item.security.currency)


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


def get_today() -> datetime.date:
    return datetime.datetime.utcnow().date()


class GraphPath:
    def __init__(self, pk: int, graph_type: str):
        self._pk = pk
        self._graph_type = graph_type
        self._graph_name = None
        self._graph_path = None
        self._graph_full_root = None
        self._graph_full_path = None
        self._define_name_and_paths()

    def _define_name_and_paths(self):
        if self._graph_type == 'security':
            self._graph_name = os.path.join('security_pie.png')
        elif self._graph_type == 'sector':
            self._graph_name = os.path.join('sector_pie.png')
        elif self._graph_type == 'country':
            self._graph_name = os.path.join('country_pie.png')
        elif self._graph_type == 'market':
            self._graph_name = os.path.join('market_pie.png')
        elif self._graph_type == 'currency':
            self._graph_name = os.path.join('currency_pie.png')
        else:
            raise Exception('ERROR: undefined graph type:', self._graph_type)
        portfolio_graph_root = os.path.join('portfolio_graph', f'{self._pk}')
        self._graph_path = os.path.join(portfolio_graph_root, self._graph_name)
        self._graph_full_root = os.path.join(MEDIA_ROOT, portfolio_graph_root)
        self._graph_full_path = os.path.join(self._graph_full_root, self._graph_name)

    @property
    def graph_path(self):
        return self._graph_path

    @property
    def graph_full_path(self):
        return self._graph_full_path

    @property
    def graph_full_root(self):
        return self._graph_full_root
