import shutil
from typing import Union
from decimal import Decimal, ROUND_HALF_UP

from django.db.models.fields.files import ImageFieldFile, FileField
from django.http.request import QueryDict
from django.core.handlers.wsgi import WSGIRequest
from django.utils.functional import SimpleLazyObject

from .models import Portfolio, PortfolioItem
from .forms import SecuritiesCreateForm, SecuritiesDeleteForm, SecuritiesIncreaseQuantityForm
from .forms import PortfolioCreateForm
from .graph import MarketGraphDrawer, CountryGraphDrawer, SecurityGraphDrawer, CurrencyGraphDrawer, SectorGraphDrawer
from .graph import GraphPath
from .utils import get_current_portfolio_items, get_today
# TODO: hide all graphs funcs in class Graph


def get_user_portfolios_list(user: SimpleLazyObject) -> list[Portfolio]:
    return user.portfolio_set.all().order_by('pk')


def get_empty_creating_portfolio_form() -> PortfolioCreateForm:
    return PortfolioCreateForm()


def create_portfolio(request: WSGIRequest):
    form_creating = PortfolioCreateForm(request.POST)
    if form_creating.is_valid():
        new_portfolio = form_creating.save(commit=False)
        new_portfolio.investor = request.user
        new_portfolio.save()
        update_portfolio_graphs(new_portfolio)


def update_portfolio_graphs_path(portfolio: Portfolio):
    graph_path_security = GraphPath(portfolio.pk, 'security').graph_path
    graph_path_sector = GraphPath(portfolio.pk, 'sector').graph_path
    graph_path_country = GraphPath(portfolio.pk, 'country').graph_path
    graph_path_market = GraphPath(portfolio.pk, 'market').graph_path
    graph_path_currency = GraphPath(portfolio.pk, 'currency').graph_path

    portfolio.securities_graph = ImageFieldFile(instance=None, name=graph_path_security, field=FileField())
    portfolio.sector_graph = ImageFieldFile(instance=None, name=graph_path_sector, field=FileField())
    portfolio.country_graph = ImageFieldFile(instance=None, name=graph_path_country, field=FileField())
    portfolio.market_graph = ImageFieldFile(instance=None, name=graph_path_market, field=FileField())
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
        update_portfolio_graphs(portfolio)


def delete_security(portfolio: Portfolio, post: QueryDict):
    form_deleting = SecuritiesDeleteForm(portfolio, post)
    if form_deleting.is_valid():
        item = form_deleting.cleaned_data['field']
        item.delete()
        update_portfolio_graphs(portfolio)


def increase_security(portfolio: Portfolio, post: QueryDict):
    form_increasing = SecuritiesIncreaseQuantityForm(portfolio, post)
    if form_increasing.is_valid():
        item = form_increasing.cleaned_data['field']
        increment = int(form_increasing.cleaned_data['quantity'])
        if item.quantity + increment > 0:
            item.quantity += increment
        item.save()
        update_portfolio_graphs(portfolio)


def get_formatted_securities_list(portfolio: Portfolio) -> list[tuple[str, Decimal, str]]:
    items = get_current_portfolio_items(portfolio)
    securities = []
    for row in items:
        cost = Decimal(row.security.price * row.quantity).quantize(Decimal('1.01'), rounding=ROUND_HALF_UP)
        securities.append((row.security.name, cost, row.security.currency))
    return securities


def update_graphs_if_outdated(portfolio: Portfolio):
    if portfolio.last_updated != get_today():
        update_portfolio_graphs(portfolio)


def update_portfolio_graphs(portfolio: Portfolio):
    # plt.switch_backend('AGG')
    # TODO: research change graphs type to .svg
    SecurityGraphDrawer(portfolio).update_graph()
    SectorGraphDrawer(portfolio).update_graph()
    CountryGraphDrawer(portfolio).update_graph()
    MarketGraphDrawer(portfolio).update_graph()
    CurrencyGraphDrawer(portfolio).update_graph()
    
    update_portfolio_graphs_path(portfolio)
    # update urls path because without updating browser will use old graphs (??cookie??)

# countries = Security.objects.order_by('country').distinct('country')
# for i in countries:
#     print(i.country)
