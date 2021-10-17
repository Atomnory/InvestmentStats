from django import forms
from .models import Securities


class SecuritiesCreateForm(forms.ModelForm):
    class Meta:
        model = Securities
        fields = ['ticker', 'name', 'quantity', 'price', 'currency', 'sector', 'country']


class SecuritiesDeleteForm(forms.ModelForm):
    field = forms.ModelChoiceField(queryset=Securities.objects.all(), empty_label='Choose security')

    class Meta:
        model = Securities
        fields = ['field']


class SecuritiesIncreaseQuantityForm(forms.ModelForm):
    field = forms.ModelChoiceField(queryset=Securities.objects.all(), empty_label='Choose security')

    class Meta:
        model = Securities
        fields = ['field', 'quantity']
