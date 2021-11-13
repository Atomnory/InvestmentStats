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
from .models import ExchangeRate, Portfolio, PortfolioItem, Security
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


def update_portfolio_graphs(portfolio: Portfolio) -> None:
    # TODO: make update graph only once per day and after item changing
    plt.switch_backend('AGG')
    update_securities_graph(portfolio)
    update_sector_graph(portfolio)
    update_country_graph(portfolio)
    update_market_graph(portfolio)
    update_currency_graph(portfolio)


def update_securities_graph(portfolio: Portfolio):
    fig_sec, ax_sec = plt.subplots()
    cost, labels = update_securities_graph_data(portfolio)
    ax_sec.pie(cost, labels=labels, autopct='%1.1f%%')
    graph_path = GraphPath(portfolio.pk, 'security')
    os.makedirs(graph_path.graph_full_root, exist_ok=True)
    fig_sec.savefig(graph_path.graph_full_path)


def update_sector_graph(portfolio: Portfolio):
    fig_sct, ax_sct = plt.subplots()
    cost, labels = update_sector_graph_data(portfolio)
    ax_sct.pie(cost, labels=labels, autopct='%1.1f%%')
    graph_path = GraphPath(portfolio.pk, 'sector')
    os.makedirs(graph_path.graph_full_root, exist_ok=True)
    fig_sct.savefig(graph_path.graph_full_path)


def update_country_graph(portfolio: Portfolio):
    fig_cnt, ax_cnt = plt.subplots()
    cost, labels = update_country_graph_data(portfolio)
    ax_cnt.pie(cost, labels=labels, autopct='%1.1f%%')
    graph_path = GraphPath(portfolio.pk, 'country')
    os.makedirs(graph_path.graph_full_root, exist_ok=True)
    fig_cnt.savefig(graph_path.graph_full_path)


def update_market_graph(portfolio: Portfolio):
    fig_mrk, ax_mrk = plt.subplots()
    cost, labels = update_market_graph_data(portfolio)
    ax_mrk.pie(cost, labels=labels, autopct='%1.1f%%')
    graph_path = GraphPath(portfolio.pk, 'market')
    os.makedirs(graph_path.graph_full_root, exist_ok=True)
    fig_mrk.savefig(graph_path.graph_full_path)


def update_currency_graph(portfolio: Portfolio):
    fig_cur, ax_cur = plt.subplots()
    cost, labels = update_currency_graph_data(portfolio)
    ax_cur.pie(cost, labels=labels, autopct='%1.1f%%')
    graph_path = GraphPath(portfolio.pk, 'currency')
    os.makedirs(graph_path.graph_full_root, exist_ok=True)
    fig_cur.savefig(graph_path.graph_full_path)


def get_eur_rate() -> Decimal:
    rate = get_last_exchange_rate()
    eur_rate = Decimal(rate.eur_rate).quantize(Decimal('1.01'), rounding=ROUND_HALF_UP)
    return eur_rate


def get_rub_rate() -> Decimal:
    rate = get_last_exchange_rate()
    rub_rate = Decimal(rate.rub_rate).quantize(Decimal('1.01'), rounding=ROUND_HALF_UP)
    return rub_rate


def update_securities_graph_data(portfolio: Portfolio) -> tuple[list[Decimal], list[str]]:
    items = get_portfolio_items(portfolio)
    cost = []
    labels = []
    for row in items:
        if row.security.currency == 'USD':
            cost.append(row.security.price * row.quantity)
        elif row.security.currency == 'EUR':
            eur_rate = get_eur_rate()
            cost.append((row.security.price / eur_rate) * row.quantity)
        elif row.security.currency == 'RUB':
            rub_rate = get_rub_rate()
            cost.append((row.security.price / rub_rate) * row.quantity)
        labels.append(row.security.ticker)

    print('$$ update security graph')
    return cost, labels


def update_sector_graph_data(portfolio: Portfolio) -> tuple[list[Decimal], list[str]]:
    items = get_portfolio_items(portfolio)
    cost = []
    labels_names = []
    for row in items:
        currency_divider = 1
        if row.security.currency == 'EUR':
            currency_divider = get_eur_rate()
        elif row.security.currency == 'RUB':
            currency_divider = get_rub_rate()

        if row.security.sector is None:
            sector_name = 'Undefined sector'
        else:
            sector_name = row.security.get_sector_display()

        if sector_name in labels_names:
            i = labels_names.index(sector_name)
            cost[i] += (row.security.price / currency_divider) * row.quantity
        else:
            labels_names.append(sector_name)
            cost.append((row.security.price / currency_divider) * row.quantity)

    print('$$ update sector graph')
    return cost, labels_names


def update_country_graph_data(portfolio: Portfolio) -> tuple[list[Decimal], list[str]]:
    items = get_portfolio_items(portfolio)
    countries = Security.objects.order_by('country').distinct('country')
    # for i in countries:
    #     print(i.country)

    cost = []
    labels_names = []
    for row in items:
        currency_divider = 1
        if row.security.currency == 'EUR':
            currency_divider = get_eur_rate()
        elif row.security.currency == 'RUB':
            currency_divider = get_rub_rate()

        if row.security.country is None:
            country_name = 'Undefined country'
        else:
            country_name = row.security.country.capitalize()

        if country_name in labels_names:
            i = labels_names.index(country_name)
            cost[i] += (row.security.price / currency_divider) * row.quantity
        else:
            labels_names.append(country_name)
            cost.append((row.security.price / currency_divider) * row.quantity)

    print('$$ update country graph')
    return cost, labels_names


def update_market_graph_data(portfolio: Portfolio) -> tuple[list[Decimal], list[str]]:
    items = get_portfolio_items(portfolio)

    cost = []
    labels_names = []
    for row in items:
        currency_divider = 1
        if row.security.currency == 'EUR':
            currency_divider = get_eur_rate()
        elif row.security.currency == 'RUB':
            currency_divider = get_rub_rate()

        # Emerging Markets
        # Developed Markets
        # All Country World

        if row.security.country == 'United States':
            market_name = row.security.country
        elif row.security.country == 'Russia':
            market_name = row.security.country
        elif row.security.country in ('Emerging Markets', 'Emerging markets', 'Kazakhstan', 'China', 'Taiwan', 'Brazil',
                                      'India', 'Mexico', 'Turkey', 'South Africa'):
            market_name = 'Emerging Markets'
        elif row.security.country in ('Developed Markets', 'Germany', 'Japan', 'France', 'Canada', 'Italy',
                                      'Netherlands', 'Norway', 'Portugal', 'South Korea', 'Spain', 'Belgium',
                                      'Switzerland',
                                      'United Kingdom', 'Australia', 'Europe', 'Ireland', 'Sweden', 'USA', 'Bermuda'):
            market_name = 'Developed Markets'
        else:
            market_name = 'All Country World'

        if market_name in labels_names:
            i = labels_names.index(market_name)
            cost[i] += (row.security.price / currency_divider) * row.quantity
        else:
            labels_names.append(market_name)
            cost.append((row.security.price / currency_divider) * row.quantity)

    print('$$ update market graph')
    return cost, labels_names


def update_currency_graph_data(portfolio: Portfolio) -> tuple[list[Decimal], list[str]]:
    items = get_portfolio_items(portfolio)
    cost = [0, 0, 0]
    labels = ('USD', 'EUR', 'RUB')
    for row in items:
        if row.security.currency == 'USD':
            cost[0] += row.security.price * row.quantity
        elif row.security.currency == 'EUR':
            eur_rate = get_eur_rate()
            cost[1] += (row.security.price / eur_rate) * row.quantity
        elif row.security.currency == 'RUB':
            rub_rate = get_rub_rate()
            cost[2] += (row.security.price / rub_rate) * row.quantity

    res_cost = []
    res_labels = []
    for i, data in enumerate(cost):
        if data > 0:
            res_cost.append(data)
            res_labels.append(labels[i])

    print('$$ update currency graph')
    return res_cost, res_labels


def get_last_exchange_rate() -> ExchangeRate:
    try:
        rate = update_exchange_rate()
    except ExchangeRate.DoesNotExist:
        rate = create_exchange_rate()
    return rate


def get_exchange_rate_object() -> ExchangeRate:
    return ExchangeRate.objects.get(pk=1)


def create_exchange_rate() -> ExchangeRate:
    today = get_today()
    rates_data = get_conversion_rates()
    rate = ExchangeRate(pk=1, last_updated=today, eur_rate=rates_data['EUR'], rub_rate=rates_data['RUB'])
    print('$$ create new ExchangeRate')
    rate.save()
    return rate


def update_exchange_rate() -> ExchangeRate:
    rate = get_exchange_rate_object()
    if rate.last_updated != get_today():
        print('$$ Exchange rate is expired. Getting update.')
        rates_data = get_conversion_rates()
        rate.eur_rate = rates_data['EUR']
        rate.rub_rate = rates_data['RUB']
        rate.save()
    return rate


def get_today() -> datetime.date:
    return datetime.datetime.utcnow().date()


def get_conversion_rates() -> dict:
    url = f'https://v6.exchangerate-api.com/v6/{EXCHANGE_API_KEY}/latest/USD'
    response = requests.get(url)
    data = response.json()['conversion_rates']
    return data


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
            self._graph_name = os.path.join('securities_pie.png')
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
