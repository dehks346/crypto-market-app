from django.urls import path
from .views import home, crypto_page, crypto_autocomplete, get_latest_price, api_ranked_cryptos, MarketView

urlpatterns = [
    path('', home, name='home'),
    path('crypto/<slug:slug>/', crypto_page, name='crypto-page'),
    path('api/price/<slug:slug>/', get_latest_price, name='get_latest_price'),
    path('market/', MarketView.as_view(), name='market'),
    path('api/ranked-cryptos/', api_ranked_cryptos, name='api_ranked_cryptos'),
    path('autocomplete/', crypto_autocomplete, name='crypto_autocomplete'),
    ]