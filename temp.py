import os
import django
import logging
import requests

# Django setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "markettracker.settings")
django.setup()

from markettracking.models import Crypto
from django.db import transaction

# Logger setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Fetch top 100 coins from CoinGecko
def fetch_top_coins(limit=100):
    url = f"https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": limit,
        "page": 1,
        "sparkline": "false"
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        logger.info(f"✅ Fetched {limit} coins from CoinGecko.")
        return response.json()
    except requests.RequestException as e:
        logger.error(f"❌ Failed to fetch coins: {e}")
        return []

# Save fetched coins to DB
def save_to_db(coins):
    try:
        with transaction.atomic():
            Crypto.objects.all().delete()
            logger.info("🧹 Cleared existing Crypto records.")

            for coin in coins:
                try:
                    Crypto.objects.create(
                        slug=coin["id"],
                        name=coin["name"],
                        symbol=coin["symbol"].upper(),
                        logo_url=coin.get("image") or ""
                    )
                    logger.info(f"✅ Saved {coin['name']} ({coin['symbol'].upper()})")
                except Exception as e:
                    logger.error(f"❌ Error saving coin {coin['id']}: {e}")

    except Exception as e:
        logger.error(f"❌ DB transaction error: {e}")

# Run the script
if __name__ == "__main__":
    coins = fetch_top_coins(limit=100)
    save_to_db(coins)
