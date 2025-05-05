# markettracking/utils.py
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from typing import Optional
from django.db.models import Sum


from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

def calculate_price_change(crypto) -> float:
    """
    Calculate the 24-hour price change percentage for a cryptocurrency.

    Args:
        crypto: Crypto model instance with price_history relation.

    Returns:
        float: Price change percentage rounded to 2 decimal places, or 0.0 if calculation fails.
    """
    try:
        now = timezone.now()
        one_day_ago = now - timedelta(days=1)

        # Get the latest price
        latest_price = crypto.price_history.order_by('-timestamp').first()
        if not latest_price:
            return 0.0

        # Try to get a price from ~24 hours ago
        old_price = crypto.price_history.filter(timestamp__lte=one_day_ago).order_by('-timestamp').first()
        if not old_price:
            # Fallback to the oldest price if no price from 24 hours ago
            old_price = crypto.price_history.order_by('timestamp').first()
            if not old_price:
                return 0.0

        # Calculate price change percentage using Decimal arithmetic
        price_diff = latest_price.price - old_price.price
        price_change = (price_diff / old_price.price) * Decimal('100')

        # Convert to float and round to 2 decimal places
        return round(float(price_change), 2)

    except ZeroDivisionError:
        return 0.0

def calculate_24hr_volume(crypto):
    # Set the time threshold for 24 hours ago
    time_threshold = timezone.now() - timedelta(hours=24)

    # Aggregate the total volume within the past 24 hours
    volume_24hrs = crypto.price_history.filter(timestamp__gte=time_threshold).aggregate(
        total_volume=Sum('volume')
    )['total_volume']

    # If no data is found, return 0
    return volume_24hrs if volume_24hrs is not None else 0