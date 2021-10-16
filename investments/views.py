import os
import matplotlib.pyplot as plt
from django.shortcuts import render
import requests
import datetime

from config.settings import MEDIA_ROOT
from .models import Securities, PieGraph, ExchangeRate
from django.db.models.fields.files import ImageFieldFile, FileField
from .forms import SecuritiesCreateForm, SecuritiesDeleteForm


def index_page(request):
    form_creating = SecuritiesCreateForm()
    form_deleting = SecuritiesDeleteForm()

    if request.method == 'POST':
        if 'update_graph' in request.POST:
            graph_name = get_updated_graph()
            try:
                PieGraph.objects.get(pk=1)
                print('$$ PieGraph exists')
            except PieGraph.DoesNotExist:
                graph = PieGraph(pk=1, graph=ImageFieldFile(instance=None, name=graph_name, field=FileField()))
                print('$$ create new PieGraph')
                graph.save()
        elif 'create_security' in request.POST:
            form_creating = SecuritiesCreateForm(request.POST)
            if form_creating.is_valid():
                form_creating.save()
                form_creating = SecuritiesCreateForm()
        elif 'delete_security' in request.POST:
            form_deleting = SecuritiesDeleteForm(request.POST)
            if form_deleting.is_valid():
                security = form_deleting.cleaned_data['field']
                security.delete()
                form_deleting = SecuritiesDeleteForm()

    try:
        graph = PieGraph.objects.get(pk=1).graph
    except PieGraph.DoesNotExist:
        graph = None

    securities_list = Securities.objects.all()

    index_page_data = {
        'securities': securities_list,
        'graph': graph,
        'form_creating': form_creating,
        'form_deleting': form_deleting
    }

    return render(request, 'investments/index.html', index_page_data)


def get_updated_graph():
    securities_list = Securities.objects.all()
    data = [x.price * x.quantity for x in securities_list]
    labels = [x.ticker for x in securities_list]
    print('$$ update graph')
    graph_name = os.path.join('pie_graph', 'securities_pie.png')
    graph_path = os.path.join(MEDIA_ROOT, graph_name)
    plt.switch_backend('AGG')
    plt.pie(data, labels=labels, autopct='%1.1f%%')
    get_last_exchange_rate()

    plt.savefig(graph_path)
    return graph_name


def get_last_exchange_rate():
    today = datetime.datetime.today().date()
    try:
        rate = ExchangeRate.objects.get(pk=1)
    except ExchangeRate.DoesNotExist:
        rates_data = get_exchange_rate()
        rate = ExchangeRate(pk=1, last_update_date=today, eur_rate=rates_data['EUR'], rub_rate=rates_data['RUB'])
        print('$$ create new ExchangeRate')
        rate.save()

    if rate.last_update_date != today:
        print('$$ Exchange rate is expired. Getting update.')
        rates_data = get_exchange_rate()
        rate.eur_rate = rates_data['EUR']
        rate.rub_rate = rates_data['RUB']
        rate.save()
    print(rate.last_update_date, rate.eur_rate, rate.rub_rate)
    return rate


def get_exchange_rate():
    exchange_api_key = os.getenv('EXCHANGE_RATE_API_KEY')
    url = f'https://v6.exchangerate-api.com/v6/{exchange_api_key}/latest/USD'

    response = requests.get(url)
    data = response.json()['conversion_rates']
    return data
