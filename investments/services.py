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

from config.settings import MEDIA_ROOT, EXCHANGE_API_KEY
from .models import ExchangeRate, Portfolio, PortfolioItem
from .forms import SecuritiesCreateForm, SecuritiesDeleteForm, SecuritiesIncreaseQuantityForm
from .forms import PortfolioCreateForm


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
        graph_path = GraphPath(new_portfolio.pk).graph_path
        new_portfolio.graph = ImageFieldFile(instance=None, name=graph_path, field=FileField())
        new_portfolio.save()


def delete_portfolio(portfolio: Portfolio):
    shutil.rmtree(GraphPath(portfolio.pk).graph_full_root, ignore_errors=True)
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
    items = get_all_portfolio_items(portfolio)
    securities = []
    for row in items:
        cost = Decimal(row.security.price * row.quantity).quantize(Decimal('1.01'), rounding=ROUND_HALF_UP)
        securities.append((row.security.ticker, cost, row.security.currency))
    return securities


def get_all_portfolio_items(portfolio: Portfolio) -> list[PortfolioItem]:
    return portfolio.portfolioitem_set.all()


def update_portfolio_graph(portfolio: Portfolio) -> None:
    # TODO: move update price in update_graph
    # TODO: make update graph only once per day and after item changing
    cost, labels = update_graph_data(portfolio)
    plt.switch_backend('AGG')
    plt.pie(cost, labels=labels, autopct='%1.1f%%')
    graph_path = GraphPath(portfolio.pk)
    os.makedirs(graph_path.graph_full_root, exist_ok=True)
    plt.savefig(graph_path.graph_full_path)


def update_graph_data(portfolio: Portfolio) -> tuple[list[Decimal], list[str]]:
    items = get_all_portfolio_items(portfolio)
    rate = get_last_exchange_rate()
    cost = []
    labels = []
    for row in items:
        if row.security.currency == 'USD':
            cost.append(row.security.price * row.quantity)
        elif row.security.currency == 'EUR':
            eur_rate = Decimal(rate.eur_rate).quantize(Decimal('1.01'), rounding=ROUND_HALF_UP)
            cost.append((row.security.price / eur_rate) * row.quantity)
        elif row.security.currency == 'RUB':
            rub_rate = Decimal(rate.rub_rate).quantize(Decimal('1.01'), rounding=ROUND_HALF_UP)
            cost.append((row.security.price / rub_rate) * row.quantity)
        labels.append(row.security.ticker)

    print('$$ update graph')
    return cost, labels


def get_last_exchange_rate() -> ExchangeRate:
    try:
        rate = update_exchange_rate()   # TODO: test if obj does not exist
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
    def __init__(self, pk: int):
        self._pk = pk
        self._graph_name = None
        self._graph_path = None
        self._graph_full_root = None
        self._graph_full_path = None
        self._define_name_and_paths()

    def _define_name_and_paths(self):
        self._graph_name = os.path.join('securities_pie.png')
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
