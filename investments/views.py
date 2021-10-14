from django.shortcuts import render
from .models import Portfolio


def index_page(request):
    portfolio_list = Portfolio.objects.all()

    index_page_data = {
        'portfolio': portfolio_list
    }

    return render(request, 'investments/index.html', index_page_data)
