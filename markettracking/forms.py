from django import forms

class CryptoSearchForm(forms.Form):
    query = forms.CharField(max_length=100, required=True, label='Search Cryptocurrency')