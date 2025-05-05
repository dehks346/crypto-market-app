import os
import django
import requests
from decimal import Decimal
from django.utils import timezone
import time

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "markettracker.settings")
django.setup()

from markettracking.models import Crypto, priceInstance

COINGECKO_API = "https://api.coingecko.com/api/v3/coins/markets"
CURRENCY = "usd"
UPDATE_INTERVAL = 900

def fetch_prices(slugs):
    params = {
        "vs_currency": CURRENCY,
        "ids": ','.join(slugs),
        "order": "market_cap_desc",
        "per_page": len(slugs),
        "page": 1,
        "sparkline": False
    }
    try:
        response = requests.get(COINGECKO_API, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching prices: {e}")
        return []

def update_price_instances():
    coins = list(Crypto.objects.all())
    slug_map = {coin.slug: coin for coin in coins}
    slugs = list(slug_map.keys())

    print(f"Fetching prices for {len(slugs)} coins...")
    data = fetch_prices(slugs)
    if not data:
        print("No data returned.")
        return

    timestamp = timezone.now()
    new_prices = []
    updated_cryptos = []

    for coin_data in data:
        slug = coin_data['id']
        crypto = slug_map.get(slug)
        if crypto:
            price = Decimal(str(coin_data.get("current_price", 0)))
            market_cap = Decimal(str(coin_data.get("market_cap", 0)))
            new_prices.append(priceInstance(crypto=crypto, price=price, timestamp=timestamp))
            crypto.current_price = price
            crypto.market_cap = market_cap
            updated_cryptos.append(crypto)
            print(f"Adding price for {crypto.name}: ${price}, Market Cap: ${market_cap}")

    priceInstance.objects.bulk_create(new_prices)
    Crypto.objects.bulk_update(updated_cryptos, ['current_price', 'market_cap'])
    print(f"{len(new_prices)} price entries created, {len(updated_cryptos)} Crypto entries updated.")

def run_continuous_update():
    while True:
        update_price_instances()
        print(f"Sleeping for {UPDATE_INTERVAL} seconds...\n")
        time.sleep(UPDATE_INTERVAL)

if __name__ == "__main__":
    run_continuous_update()