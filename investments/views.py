from django.shortcuts import render, get_object_or_404, redirect

from .services import update_portfolio_graph, GraphPath
    # get_formatted_securities_list, get_graph_if_exist_or_create
# get_index_forms,
from django.contrib.auth.models import User
from .models import Portfolio, PortfolioItem, Securities
from .forms import PortfolioCreateForm, SecuritiesCreateForm
from django.db.models.fields.files import ImageFieldFile, FileField
from django.contrib.auth.decorators import login_required
from decimal import Decimal, ROUND_HALF_UP


def index_page(request):
    if request.user.is_authenticated:
        portfolios_list = request.user.portfolio_set.all()
        form_creating = PortfolioCreateForm()

        if request.method == 'POST':
            form_creating = PortfolioCreateForm(request.POST)
            if form_creating.is_valid():
                new_portfolio = form_creating.save(commit=False)
                new_portfolio.investor = request.user
                new_portfolio.save()
                graph_path = GraphPath(new_portfolio.pk).graph_path
                new_portfolio.graph = ImageFieldFile(instance=None, name=graph_path, field=FileField())
                new_portfolio.save()
                form_creating = PortfolioCreateForm()
    else:
        portfolios_list = None
        form_creating = None

    index_page_data = {
        'portfolios': portfolios_list,
        'form_creating': form_creating
    }

    return render(request, 'investments/index.html', index_page_data)


@login_required(login_url='login')
def portfolio_page(request, portfolio_pk):
    portfolio = get_object_or_404(Portfolio, pk=portfolio_pk)
    if portfolio.investor == request.user:
        form_creating = SecuritiesCreateForm()
        if request.method == 'POST':
            form_creating = SecuritiesCreateForm(request.POST)
            if form_creating.is_valid():
                security = form_creating.cleaned_data['security_select']
                quantity = int(form_creating.cleaned_data['quantity'])
                if quantity > 0:
                    item = PortfolioItem(portfolio=portfolio, security=security, quantity=quantity)
                    item.save()
                form_creating = SecuritiesCreateForm()

        update_portfolio_graph(portfolio)
        graph = portfolio.graph
        items = portfolio.portfolioitem_set.all()
        securities = []
        for row in items:
            cost = Decimal(row.security.price * row.quantity).quantize(Decimal('1.01'), rounding=ROUND_HALF_UP)
            securities.append((row.security.ticker, cost, row.security.currency))

        portfolio_page_data = {
            'securities': securities,
            'graph': graph,
            'form_creating': form_creating,
            # 'form_deleting': forms['form_deleting'],
            # 'form_increasing': forms['form_increasing']
        }

        return render(request, 'investments/portfolio.html', portfolio_page_data)
    else:
        return redirect('index')
