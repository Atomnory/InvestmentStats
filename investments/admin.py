from django.contrib import admin
from .models import Security, ExchangeRate, Portfolio, PortfolioItem


admin.site.register(Security)
admin.site.register(ExchangeRate)
admin.site.register(Portfolio)
admin.site.register(PortfolioItem)
