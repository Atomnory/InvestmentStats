from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test

from .models import Portfolio
from .services import get_empty_portfolio_forms, delete_portfolio, fill_portfolio_forms, update_portfolio_graph
from .services import get_user_portfolios_list, get_empty_creating_portfolio_form, create_portfolio
from .services import get_formatted_securities_list
from .tinkoff_client import save_tinvest_etfs, save_tinvest_bonds, auto_define_stock_info, save_tinvest_stocks
from .tinkoff_client import get_not_found_stock, get_empty_fill_info_form_or_none, save_not_found_stock_info


def index_page(request):
    if request.user.is_authenticated:
        portfolios_list = get_user_portfolios_list(request.user)
        form_creating = get_empty_creating_portfolio_form()

        if request.method == 'POST':
            create_portfolio(request)
            return redirect('index')
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
        if request.method == 'POST':
            fill_portfolio_forms(portfolio, request.POST)
            return redirect('portfolio', portfolio_pk=portfolio.pk)

        forms = get_empty_portfolio_forms(portfolio)
        # TODO: add Select2 plugin
        securities = get_formatted_securities_list(portfolio)
        update_portfolio_graph(portfolio)
        graph = portfolio.graph

        portfolio_page_data = {
            'securities': securities,
            'graph': graph,
            'form_creating': forms['form_creating'],
            'form_deleting': forms['form_deleting'],
            'form_increasing': forms['form_increasing'],
            'portfolio_pk': portfolio.pk
        }

        return render(request, 'investments/portfolio.html', portfolio_page_data)
    else:
        return redirect('index')


@login_required(login_url='login')
def delete_portfolio_page(request, portfolio_pk):
    portfolio = get_object_or_404(Portfolio, pk=portfolio_pk)
    if portfolio.investor == request.user:
        if request.method == 'POST' and 'delete-portfolio' in request.POST:
            delete_portfolio(portfolio)
            return redirect('index')

        deleting_portfolio_data = {
            'portfolio': portfolio
        }

        return render(request, 'investments/delete_portfolio.html', deleting_portfolio_data)
    else:
        return redirect('index')


@user_passes_test(lambda u: u.is_superuser)
def superuser_dashboard(request):
    not_found = get_not_found_stock()
    form_filling = get_empty_fill_info_form_or_none(not_found)

    if request.method == 'POST':
        if 'create-etfs' in request.POST:
            save_tinvest_etfs()
        elif 'create-bonds' in request.POST:
            save_tinvest_bonds()
        elif 'create-stocks' in request.POST:
            save_tinvest_stocks()
        elif 'define-info' in request.POST:
            auto_define_stock_info()
        elif 'fill-info' in request.POST:
            save_not_found_stock_info(not_found, request.POST)
        return redirect('superuser_dashboard')

    superuser_dashboard_data = {
        'user': request.user,
        'form_filling': form_filling
    }

    return render(request, 'investments/superuser_dashboard.html', superuser_dashboard_data)
