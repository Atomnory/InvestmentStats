from django import forms
from .models import PortfolioItem, Portfolio, Securities


class SecuritiesCreateForm(forms.ModelForm):
    security_select = forms.ModelChoiceField(queryset=Securities.objects.all(), empty_label='Choose security')

    class Meta:
        model = PortfolioItem
        fields = ['security_select', 'quantity']


class SecuritiesDeleteForm(forms.ModelForm):
    field = forms.ModelChoiceField(queryset=PortfolioItem.objects.all(), empty_label='Choose security')

    def __init__(self, portfolio, *args, **kwargs):
        super(SecuritiesDeleteForm, self).__init__(*args, **kwargs)
        self.fields['field'].queryset = PortfolioItem.objects.filter(portfolio=portfolio)

    class Meta:
        model = PortfolioItem
        fields = ['field']


class SecuritiesIncreaseQuantityForm(forms.ModelForm):
    field = forms.ModelChoiceField(queryset=PortfolioItem.objects.all(), empty_label='Choose security')

    def __init__(self, portfolio, *args, **kwargs):
        super(SecuritiesIncreaseQuantityForm, self).__init__(*args, **kwargs)
        self.fields['field'].queryset = PortfolioItem.objects.filter(portfolio=portfolio)

    class Meta:
        model = PortfolioItem
        fields = ['field', 'quantity']


class PortfolioCreateForm(forms.ModelForm):
    class Meta:
        model = Portfolio
        fields = ['name']

