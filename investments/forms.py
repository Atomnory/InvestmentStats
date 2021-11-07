from django import forms
from .models import PortfolioItem, Portfolio, Security


class SecuritiesCreateForm(forms.ModelForm):
    security_select = forms.ModelChoiceField(queryset=Security.objects.all(), empty_label='Choose security')

    def __init__(self, portfolio: Portfolio, *args, **kwargs):
        super().__init__(*args, **kwargs)
        exclusion_list = [x.security.pk for x in PortfolioItem.objects.filter(portfolio=portfolio)]
        self.fields['security_select'].queryset = Security.objects.all().exclude(pk__in=exclusion_list)

    class Meta:
        model = PortfolioItem
        fields = ['security_select', 'quantity']


class SecuritiesDeleteForm(forms.ModelForm):
    field = forms.ModelChoiceField(queryset=PortfolioItem.objects.all(), empty_label='Choose security')

    def __init__(self, portfolio: Portfolio, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['field'].queryset = PortfolioItem.objects.filter(portfolio=portfolio)

    class Meta:
        model = PortfolioItem
        fields = ['field']


class SecuritiesIncreaseQuantityForm(forms.ModelForm):
    field = forms.ModelChoiceField(queryset=PortfolioItem.objects.all(), empty_label='Choose security')

    def __init__(self, portfolio: Portfolio, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['field'].queryset = PortfolioItem.objects.filter(portfolio=portfolio)

    class Meta:
        model = PortfolioItem
        fields = ['field', 'quantity']


class PortfolioCreateForm(forms.ModelForm):
    class Meta:
        model = Portfolio
        fields = ['name']


# TODO: research formset using
class SecurityFillInformationForm(forms.ModelForm):
    ticker_custom = forms.CharField(max_length=16)

    def __init__(self, security: Security, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['ticker_custom'].initial = security.ticker
        self.fields['ticker_custom'].disabled = True
        self.fields['name'].initial = security.name
        self.fields['name'].disabled = True
        self.fields['sector'].required = True
        self.fields['sector'].initial = security.sector
        self.fields['country'].required = True

    class Meta:
        model = Security
        fields = ['ticker_custom', 'name', 'sector', 'country']
