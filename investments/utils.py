import datetime
from .models import Portfolio, PortfolioItem
from .tinkoff_client import update_security_price


def get_current_portfolio_items(portfolio: Portfolio) -> list[PortfolioItem]:
    items = _get_portfolio_items(portfolio)
    for item in items:
        if item.security.last_updated != get_today():
            update_security_price(item.security)
    return items


def _get_portfolio_items(portfolio: Portfolio) -> list[PortfolioItem]:
    return portfolio.portfolioitem_set.all()


def get_today() -> datetime.date:
    return datetime.datetime.utcnow().date()
