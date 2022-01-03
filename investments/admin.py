from django.contrib import admin
from .models import Security, ExchangeRate, Portfolio, PortfolioItem


class SecurityAdmin(admin.ModelAdmin):
    list_display = ('name', 'ticker', 'not_found_on_market')

    list_filter = ['not_found_on_market']


class ExchangeRateAdmin(admin.ModelAdmin):
    list_display = ('last_updated', 'eur_rate', 'rub_rate')


class PortfolioAdmin(admin.ModelAdmin):
    list_display = ('investor', 'name')


admin.site.register(Security, SecurityAdmin)
admin.site.register(ExchangeRate, ExchangeRateAdmin)
admin.site.register(Portfolio, PortfolioAdmin)
admin.site.register(PortfolioItem)
