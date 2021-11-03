from django.db import models
from django.contrib.auth.models import User


class Security(models.Model):
    currency_choice = (
        ('EUR', 'EUR'),
        ('RUB', 'RUB'),
        ('USD', 'USD')
    )

    sector_choice = (
        ('BMAT', 'Basic Materials'),
        ('BOND', 'Bonds'),
        ('CASH', 'Cash'),
        ('COM', 'Communication Services'),
        ('CYCL', 'Consumer Cyclical'),
        ('DEF', 'Consumer Defensive'),
        ('ENER', 'Energy'),
        ('ETF', 'ETF'),
        ('FIN', 'Financial Services'),
        ('GOLD', 'Gold'),
        ('HEAL', 'Healthcare'),
        ('IND', 'Industrials'),
        ('EST', 'Real Estate'),
        ('TECH', 'Technology'),
        ('UTIL', 'Utilities')
    )

    ticker = models.CharField('Ticker', max_length=16, unique=True)
    name = models.CharField('Name', max_length=100)
    price = models.DecimalField('Price', max_digits=12, decimal_places=4)
    currency = models.CharField('Currency', max_length=3, choices=currency_choice)
    sector = models.CharField('Sector', max_length=20, choices=sector_choice, null=True)
    country = models.CharField('Country', max_length=20, null=True)
    update_date = models.DateField('Last update', auto_now=True)

    class Meta:
        ordering = ['ticker']

    def __str__(self):
        return self.name

    def get_full_name(self):
        return self.name


class ExchangeRate(models.Model):
    last_update_date = models.DateField('Last update', auto_now=True)
    eur_rate = models.DecimalField('EUR rate', max_digits=10, decimal_places=4)
    rub_rate = models.DecimalField('RUB rate', max_digits=10, decimal_places=4)


class Portfolio(models.Model):
    investor = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField('Portfolio name', max_length=100)
    graph = models.ImageField('Portfolio pie graph', upload_to='portfolio_graph', null=True)

    def __str__(self):
        return self.name


class PortfolioItem(models.Model):
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE)
    security = models.ForeignKey(Security, on_delete=models.CASCADE)
    quantity = models.IntegerField('Quantity')

    def __str__(self):
        return self.security.name
