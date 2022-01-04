import os
import matplotlib.pyplot as plt

from config.settings import MEDIA_ROOT
from .models import Portfolio
from .exchanger import Exchanger
from .utils import get_portfolio_items


# TODO: One security has not 100% on graph
class AbstractGraphDrawer:
    def __init__(self, portfolio: Portfolio):
        self._portfolio = portfolio
        self._graph_name = None
        self._graph_path = None
        self._fig = None
        self._axe = None
        self._cost = None
        self._labels = None
        self._calculator = AbstractGraphDataCalculator(portfolio)

    def update_graph(self):
        self._set_graph_path()
        self._update_graph_data()
        self._draw_graph()
        self._save_graph()

    def _set_graph_path(self):
        self._graph_path = GraphPath(self._portfolio.pk, self._graph_name)

    def _update_graph_data(self):
        self._cost = self._calculator.costs
        self._labels = self._calculator.labels

    def _draw_graph(self):
        plt.switch_backend('AGG')
        self._fig, self._axe = plt.subplots()
        self._axe.pie(self._cost, labels=self._labels, autopct='%1.1f%%')

    def _save_graph(self):
        os.makedirs(self._graph_path.graph_full_root, exist_ok=True)
        self._fig.savefig(self._graph_path.graph_full_path)


class SecurityGraphDrawer(AbstractGraphDrawer):
    def __init__(self, portfolio: Portfolio):
        super().__init__(portfolio)
        self._graph_name = 'security'
        self._calculator = SecurityGraphDataCalculator(portfolio)


class SectorGraphDrawer(AbstractGraphDrawer):
    def __init__(self, portfolio: Portfolio):
        super().__init__(portfolio)
        self._graph_name = 'sector'
        self._calculator = SectorGraphDataCalculator(portfolio)


class CountryGraphDrawer(AbstractGraphDrawer):
    def __init__(self, portfolio: Portfolio):
        super().__init__(portfolio)
        self._graph_name = 'country'
        self._calculator = CountryGraphDataCalculator(portfolio)


class MarketGraphDrawer(AbstractGraphDrawer):
    def __init__(self, portfolio: Portfolio):
        super().__init__(portfolio)
        self._graph_name = 'market'
        self._calculator = MarketGraphDataCalculator(portfolio)


class CurrencyGraphDrawer(AbstractGraphDrawer):
    def __init__(self, portfolio: Portfolio):
        super().__init__(portfolio)
        self._graph_name = 'currency'
        self._calculator = CurrencyGraphDataCalculator(portfolio)


class AbstractGraphDataCalculator:
    def __init__(self, portfolio: Portfolio):
        self._exchanger = Exchanger()
        self._items = get_portfolio_items(portfolio)
        self._costs = []
        self._labels = []
        self._item = None
        self._currency_divider = None
        self._cost = None

    def _update_graph_data(self):
        for item in self._items:
            self._item = item
            self._get_currency_divider()
            self._process_item()

    def _get_currency_divider(self):
        if self._item.security.currency == 'USD':
            self._currency_divider = 1
        elif self._item.security.currency == 'EUR':
            self._currency_divider = self._exchanger.eur_rate
        elif self._item.security.currency == 'RUB':
            self._currency_divider = self._exchanger.rub_rate

    def _process_item(self):
        pass

    def _calculate_cost(self):
        self._cost = (self._item.security.price / self._currency_divider) * self._item.quantity

    def _increase_existing_item(self, label: str):
        i = self._labels.index(label)
        self._costs[i] += self._cost

    def _append_new_item(self, label: str):
        self._costs.append(self._cost)
        self._labels.append(label)

    def _increase_label_cost_if_in_labels_or_append_new(self, label: str):
        self._calculate_cost()
        if label in self._labels:
            self._increase_existing_item(label)
        else:
            self._append_new_item(label)

    @property
    def costs(self):
        return self._costs

    @property
    def labels(self):
        return self._labels


class SecurityGraphDataCalculator(AbstractGraphDataCalculator):
    def __init__(self, portfolio: Portfolio):
        super().__init__(portfolio)
        self._update_graph_data()

    def _process_item(self):
        self._calculate_cost()
        self._append_new_item(self._item.security.ticker)


class SectorGraphDataCalculator(AbstractGraphDataCalculator):
    def __init__(self, portfolio: Portfolio):
        super().__init__(portfolio)
        self._update_graph_data()

    def _process_item(self):
        if self._item.security.sector is None:
            sector_name = 'Undefined sector'
        else:
            sector_name = self._item.security.get_sector_display()
        self._increase_label_cost_if_in_labels_or_append_new(sector_name)


class CountryGraphDataCalculator(AbstractGraphDataCalculator):
    def __init__(self, portfolio: Portfolio):
        super().__init__(portfolio)
        self._update_graph_data()

    def _process_item(self):
        if self._item.security.country is None:
            country_name = 'Undefined country'
        else:
            country_name = self._item.security.country.capitalize()
        self._increase_label_cost_if_in_labels_or_append_new(country_name)


class MarketGraphDataCalculator(AbstractGraphDataCalculator):
    def __init__(self, portfolio: Portfolio):
        super().__init__(portfolio)
        self._update_graph_data()

    def _process_item(self):
        # Emerging Markets
        # Developed Markets
        # All Country World
        if self._item.security.country == 'United States':
            market_name = self._item.security.country
        elif self._item.security.country == 'Russia':
            market_name = self._item.security.country
        elif self._item.security.country in (
                'Emerging Markets', 'Emerging markets', 'Kazakhstan', 'China', 'Taiwan', 'Brazil',
                'India', 'Mexico', 'Turkey', 'South Africa', 'Uruguay'):
            market_name = 'Emerging Markets'
        elif self._item.security.country in ('Developed Markets', 'Germany', 'Japan', 'France', 'Canada', 'Italy',
                                       'Netherlands', 'Norway', 'Portugal', 'South Korea', 'Spain', 'Belgium',
                                       'Switzerland', 'Israel'
                                                      'United Kingdom', 'Australia', 'Europe', 'Ireland', 'Sweden',
                                       'USA',
                                       'Bermuda'):
            market_name = 'Developed Markets'
        else:
            market_name = 'All Country World'
        self._increase_label_cost_if_in_labels_or_append_new(market_name)


class CurrencyGraphDataCalculator(AbstractGraphDataCalculator):
    def __init__(self, portfolio: Portfolio):
        super().__init__(portfolio)
        self._update_graph_data()

    def _process_item(self):
        self._increase_label_cost_if_in_labels_or_append_new(self._item.security.currency)


class GraphPath:
    def __init__(self, pk: int, graph_type: str):
        self._pk = pk
        self._graph_type = graph_type
        self._graph_name = None
        self._graph_path = None
        self._graph_full_root = None
        self._graph_full_path = None
        self._define_name_and_paths()

    def _define_name_and_paths(self):
        self._graph_name = os.path.join(f'{self._graph_type}_pie.png')
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

