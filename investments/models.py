from django.db import models


class Portfolio(models.Model):
    currency_choice = (
        ('EUR', 'EUR'),
        ('RUB', 'RUB'),
        ('USD', 'USD')
    )

    sector_choice = (
        ('BMAT', 'Basic Materials'),
        ('BOND', 'Bonds'),
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

    ticker = models.CharField('Ticker', max_length=10)
    name = models.CharField('Name', max_length=100)
    quantity = models.IntegerField('Quantity')
    price = models.DecimalField('Price', max_digits=12, decimal_places=4)
    currency = models.CharField('Currency', max_length=3, choices=currency_choice)
    sector = models.CharField('Sector', max_length=20, choices=sector_choice)
    country = models.CharField('Country', max_length=20)
