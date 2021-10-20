from django.contrib import admin
from .models import Securities, ExchangeRate, Portfolio, PortfolioItem


admin.site.register(Securities)
admin.site.register(ExchangeRate)
admin.site.register(Portfolio)
admin.site.register(PortfolioItem)
