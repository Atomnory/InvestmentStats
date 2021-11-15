import datetime
from .models import Portfolio, PortfolioItem


def get_portfolio_items(portfolio: Portfolio) -> list[PortfolioItem]:
    return portfolio.portfolioitem_set.all()


def get_today() -> datetime.date:
    return datetime.datetime.utcnow().date()
