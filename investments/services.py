import datetime
from typing import Union
from decimal import Decimal, ROUND_HALF_UP

import matplotlib.pyplot as plt
import requests
from django.db.models.fields.files import ImageFieldFile, FileField
from django.http.request import QueryDict
from django.core.handlers.wsgi import WSGIRequest

from config.settings import GRAPH_NAME, GRAPH_PATH, EXCHANGE_API_KEY
from .models import Securities, PieGraph, ExchangeRate
from .forms import SecuritiesCreateForm, SecuritiesDeleteForm, SecuritiesIncreaseQuantityForm


def get_index_forms(request: WSGIRequest) -> \
        dict[str, Union[SecuritiesCreateForm, SecuritiesDeleteForm, SecuritiesIncreaseQuantityForm]]:
    form_creating = SecuritiesCreateForm()
    form_deleting = SecuritiesDeleteForm()
    form_increasing = SecuritiesIncreaseQuantityForm()

    if request.method == 'POST':
        if 'update_graph' in request.POST:
            update_graph()
        elif 'create_security' in request.POST:
            form_creating = create_security(request.POST)
        elif 'delete_security' in request.POST:
            form_deleting = delete_security(request.POST)
        elif 'increase_security' in request.POST:
            form_increasing = increase_security(request.POST)

    return {'form_creating': form_creating, 'form_deleting': form_deleting, 'form_increasing': form_increasing}


def create_security(post: QueryDict) -> SecuritiesCreateForm:
    form_creating = SecuritiesCreateForm(post)
    if form_creating.is_valid():
        form_creating.save()
        form_creating = SecuritiesCreateForm()
    return form_creating


def delete_security(post: QueryDict) -> SecuritiesDeleteForm:
    form_deleting = SecuritiesDeleteForm(post)
    if form_deleting.is_valid():
        security = form_deleting.cleaned_data['field']
        security.delete()
        form_deleting = SecuritiesDeleteForm()
    return form_deleting


def increase_security(post: QueryDict) -> SecuritiesIncreaseQuantityForm:
    form_increasing = SecuritiesIncreaseQuantityForm(post)
    if form_increasing.is_valid():
        security = form_increasing.cleaned_data['field']
        increment = int(form_increasing.cleaned_data['quantity'])
        if security.quantity + increment > 0:
            security.quantity += increment
        security.save()
        form_increasing = SecuritiesIncreaseQuantityForm()
    return form_increasing


def get_graph_if_exist_or_create() -> ImageFieldFile:
    try:
        graph = PieGraph.objects.get(pk=1).graph
    except PieGraph.DoesNotExist:
        update_graph()
        graph = PieGraph(pk=1, graph=ImageFieldFile(instance=None, name=GRAPH_NAME, field=FileField()))
        graph.save()
        print('$$ create new PieGraph')
    return graph


def get_formatted_securities_list() -> list[tuple[str, Decimal, str]]:
    securities_list = get_all_securities()
    result = []
    for row in securities_list:
        cost = Decimal(row.price * row.quantity).quantize(Decimal('1.01'), rounding=ROUND_HALF_UP)
        result.append((row.ticker, cost, row.currency))
    return result


def update_graph() -> None:
    cost, labels = update_graph_data()
    plt.switch_backend('AGG')
    plt.pie(cost, labels=labels, autopct='%1.1f%%')
    plt.savefig(GRAPH_PATH)


def get_all_securities() -> list[Securities]:
    return Securities.objects.all()


def update_graph_data() -> tuple[list[Decimal], list[str]]:
    securities_list = get_all_securities()
    rate = get_last_exchange_rate()
    cost = []
    for row in securities_list:
        if row.currency == 'USD':
            cost.append(row.price * row.quantity)
        elif row.currency == 'EUR':
            cost.append((row.price / rate.eur_rate) * row.quantity)
        elif row.currency == 'RUB':
            cost.append((row.price / rate.rub_rate) * row.quantity)

    labels = [x.ticker for x in securities_list]
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
