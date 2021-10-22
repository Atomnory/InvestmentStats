import datetime
from typing import Union
from decimal import Decimal, ROUND_HALF_UP
from django.shortcuts import redirect

import matplotlib.pyplot as plt
import requests
from django.db.models.fields.files import ImageFieldFile, FileField
from django.http.request import QueryDict
from django.core.handlers.wsgi import WSGIRequest

from .models import Securities, ExchangeRate, Portfolio, PortfolioItem
from .forms import SecuritiesCreateForm, SecuritiesDeleteForm, SecuritiesIncreaseQuantityForm
import os
from config.settings import MEDIA_ROOT, EXCHANGE_API_KEY


def get_empty_portfolio_forms(portfolio: Portfolio) -> \
        dict[str, Union[SecuritiesCreateForm, SecuritiesDeleteForm, SecuritiesIncreaseQuantityForm]]:
    form_creating = SecuritiesCreateForm()
    form_deleting = SecuritiesDeleteForm(portfolio)
    form_increasing = SecuritiesIncreaseQuantityForm(portfolio)

    return {'form_creating': form_creating,
            'form_deleting': form_deleting,
            'form_increasing': form_increasing}


def fill_portfolio_forms(portfolio: Portfolio, request: WSGIRequest):
    if 'create_security' in request.POST:
        return create_security(portfolio, request.POST)
    elif 'delete_security' in request.POST:
        return delete_security(portfolio, request.POST)
    elif 'increase_security' in request.POST:
        return increase_security(portfolio, request.POST)


def create_security(portfolio: Portfolio, post: QueryDict):
    # TODO: bug: can add security to portfolio item if it in already.
    # But adding create other object and it will displaying as other part of pie.
    # Need to delete possibility adding existing security to portfolio
    form_creating = SecuritiesCreateForm(post)
    if form_creating.is_valid():
        security = form_creating.cleaned_data['security_select']
        quantity = int(form_creating.cleaned_data['quantity'])
        if quantity > 0:
            item = PortfolioItem(portfolio=portfolio, security=security, quantity=quantity)
            item.save()
        return redirect('portfolio', portfolio_pk=portfolio.pk)


def delete_security(portfolio: Portfolio, post: QueryDict):
    form_deleting = SecuritiesDeleteForm(portfolio, post)
    if form_deleting.is_valid():
        item = form_deleting.cleaned_data['field']
        item.delete()
        return redirect('portfolio', portfolio_pk=portfolio.pk)


def increase_security(portfolio: Portfolio, post: QueryDict):
    form_increasing = SecuritiesIncreaseQuantityForm(portfolio, post)
    if form_increasing.is_valid():
        item = form_increasing.cleaned_data['field']
        increment = int(form_increasing.cleaned_data['quantity'])
        if item.quantity + increment > 0:
            item.quantity += increment
        item.save()
        return redirect('portfolio', portfolio_pk=portfolio.pk)


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
            cost.append((row.security.price / rate.eur_rate) * row.quantity)
        elif row.security.currency == 'RUB':
            cost.append((row.security.price / rate.rub_rate) * row.quantity)
        labels.append(row.security.ticker)

    print('$$ update graph')
    return cost, labels


def get_last_exchange_rate() -> ExchangeRate:
    try:
        rate = get_exchange_rate_object()
    except ExchangeRate.DoesNotExist:
        rate = create_exchange_rate()
    else:
        rate = update_exchange_rate(rate)
    return rate


def get_exchange_rate_object() -> ExchangeRate:
    return ExchangeRate.objects.get(pk=1)


def create_exchange_rate() -> ExchangeRate:
    today = get_today()
    rates_data = get_conversion_rates()
    rate = ExchangeRate(pk=1, last_update_date=today, eur_rate=rates_data['EUR'], rub_rate=rates_data['RUB'])
    print('$$ create new ExchangeRate')
    rate.save()
    return rate


def update_exchange_rate(ex_rate: ExchangeRate) -> ExchangeRate:
    if ex_rate.last_update_date != get_today():
        print('$$ Exchange rate is expired. Getting update.')
        rates_data = get_conversion_rates()
        ex_rate.eur_rate = rates_data['EUR']
        ex_rate.rub_rate = rates_data['RUB']
        ex_rate.save()
    return ex_rate


def get_today() -> datetime.date:
    return datetime.datetime.today().date()


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
