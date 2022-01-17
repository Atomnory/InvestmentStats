import shutil
from typing import Union
from decimal import Decimal, ROUND_HALF_UP

from django.db.models.fields.files import ImageFieldFile, FileField
from django.http.request import QueryDict
from django.core.handlers.wsgi import WSGIRequest
from django.utils.functional import SimpleLazyObject

from .models import Portfolio, PortfolioItem
from .forms import PortfolioItemsCreateForm, PortfolioItemsDeleteForm, PortfolioItemsIncreaseQuantityForm
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
    graphs_name = ('security', 'sector', 'country', 'market', 'currency')
    graphs_path = [GraphPath(portfolio.pk, x).graph_path for x in graphs_name]
    graphs = [portfolio.securities_graph, portfolio.sector_graph, portfolio.country_graph, portfolio.market_graph, portfolio.currency_graph]
    for i, graph in enumerate(graphs):
        graph = ImageFieldFile(instance=None, name=graphs_path[i], field=FileField())
    portfolio.save()


def delete_portfolio(portfolio: Portfolio):
    shutil.rmtree(GraphPath(portfolio.pk, 'security').graph_full_root, ignore_errors=True)
    portfolio.delete()


class PortfolioItemFormsHandler:
    def __init__(self, portfolio: Portfolio) -> None:
        if not isinstance(portfolio, Portfolio):
            raise TypeError('PortfolioItemFormsHandler accepts only Portfolio')
        self._portfolio = portfolio

    def fill_portfolio_forms(self, post: QueryDict):
        if 'create_security' in post:
            self._create_portfolio_item(post)
        elif 'delete_security' in post:
            self._delete_portfolio_item(post)
        elif 'increase_security' in post:
            self._increase_portfolio_item(post)

    def _create_portfolio_item(self, post: QueryDict):
        form_creating = PortfolioItemsCreateForm(self._portfolio, post)
        if form_creating.is_valid():
            security = form_creating.cleaned_data['security_select']
            quantity = int(form_creating.cleaned_data['quantity'])
            if quantity > 0:
                item = PortfolioItem(portfolio=self._portfolio, security=security, quantity=quantity)
                item.save()
            update_portfolio_graphs(self._portfolio)

    def _delete_portfolio_item(self, post: QueryDict):
        form_deleting = PortfolioItemsDeleteForm(self._portfolio, post)
        if form_deleting.is_valid():
            item = form_deleting.cleaned_data['field']
            item.delete()
            update_portfolio_graphs(self._portfolio)

    def _increase_portfolio_item(self, post: QueryDict):
        form_increasing = PortfolioItemsIncreaseQuantityForm(self._portfolio, post)
        if form_increasing.is_valid():
            item = form_increasing.cleaned_data['field']
            increment = int(form_increasing.cleaned_data['quantity'])
            if item.quantity + increment > 0:
                item.quantity += increment
            item.save()
            update_portfolio_graphs(self._portfolio)

    def _form_items_list(self) -> list[tuple[str, Decimal, str]]:
        items = get_current_portfolio_items(self._portfolio)
        securities = []
        for row in items:
            cost = Decimal(row.security.price * row.quantity).quantize(Decimal('1.01'), rounding=ROUND_HALF_UP)
            securities.append((row.security.name, cost, row.security.currency))
        return securities

    @property
    def items_list(self) -> list[tuple[str, Decimal, str]]:
        items = self._form_items_list()
        return items 

    @property
    def empty_forms(self) \
            -> dict[str, Union[PortfolioItemsCreateForm, PortfolioItemsDeleteForm, PortfolioItemsIncreaseQuantityForm]]:
        return {'form_creating': PortfolioItemsCreateForm(self._portfolio),
                'form_deleting': PortfolioItemsDeleteForm(self._portfolio),
                'form_increasing': PortfolioItemsIncreaseQuantityForm(self._portfolio)}


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
