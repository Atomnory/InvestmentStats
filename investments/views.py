from django.shortcuts import render
from .models import Portfolio
import matplotlib.pyplot as plt


def index_page(request):
    portfolio_list = Portfolio.objects.all()

    index_page_data = {
        'portfolio': portfolio_list,
        'is_graph_exist': False
    }

    return render(request, 'investments/index.html', index_page_data)


def load_graph(request):
    get_graph()
    return index_page(request)


def get_graph():
    portfolio_list = Portfolio.objects.all()
    data = [x.price * x.quantity for x in portfolio_list]
    labels = [x.ticker for x in portfolio_list]

    plt.pie(data, labels=labels, autopct='%1.1f%%')
    # fig, ax = plt.subplots()
    # ax.pie()
    plt.savefig('portfolio_pie.png')
    # plt.show()

