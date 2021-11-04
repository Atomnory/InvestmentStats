from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test

from .models import Portfolio
from .services import get_empty_portfolio_forms, delete_portfolio, fill_portfolio_forms
from .services import get_user_portfolios_list, get_empty_index_form, create_portfolio, get_formatted_securities_list
from .tinkoff_client import get_etfs, get_bonds, define_stock_sector_and_country


def index_page(request):
    if request.user.is_authenticated:
        portfolios_list = get_user_portfolios_list(request.user)
        form_creating = get_empty_index_form()

        if request.method == 'POST':
            return create_portfolio(request)
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
        forms = get_empty_portfolio_forms(portfolio)
        if request.method == 'POST':
            return fill_portfolio_forms(portfolio, request)
        graph = portfolio.graph
        securities = get_formatted_securities_list(portfolio)

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
            return delete_portfolio(portfolio)
        deleting_portfolio_data = {
            'portfolio': portfolio
        }

        return render(request, 'investments/delete_portfolio.html', deleting_portfolio_data)
    else:
        return redirect('index')


@user_passes_test(lambda u: u.is_superuser)
def superuser_dashboard(request):
    # if queryset(not_found_on_market = True):
    # render SecurityFillInformationForm(the Security object from queryset)

    if request.method == 'POST':
        if 'create-etfs' in request.POST:
            get_etfs()
        elif 'create-bonds' in request.POST:
            get_bonds()
        elif 'define-info' in request.POST:
            define_stock_sector_and_country()
        # elif 'fill-info' in request.POST:
            # fill SecurityFillInformationForm()
            # if form.is_valid():
            # obj = the exact Security object from queryset
            # obj.sector = form.cleaned_data['sector']
            # obj.country = form.cleaned_date['country']
            # obj.save()
            # obj delete from queryset
            # TODO: examine possibility to eliminate reloading queryset after post 'fill-info'
            # Every reloading superuser_dashboard will query set of securities not found on market.
        return redirect('superuser_dashboard')

    superuser_dashboard_data = {
        'user': request.user
    }

    return render(request, 'investments/superuser_dashboard.html', superuser_dashboard_data)
