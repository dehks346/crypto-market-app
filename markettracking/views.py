import os
import django
import requests
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from .models import priceInstance, Crypto
from django.http import JsonResponse
from .forms import CryptoSearchForm
from django.core.cache import cache
import time
import plotly.express as px
from django.urls import reverse
from django.db import transaction
from django.views.generic import ListView
from django.core.cache import cache
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.db.models import Prefetch
from typing import List, Dict, Any
import logging
from .models import Crypto, priceInstance
from .utils import calculate_price_change, calculate_24hr_volume


def home(request):
    if request.method == 'GET':
        form = CryptoSearchForm(request.GET)
        if form.is_valid():
            query = form.cleaned_data['query']
            try:
                cryptos = Crypto.objects.filter(name__icontains=query)
                if cryptos.exists():
                    return redirect('crypto-page', slug=cryptos.first().slug)
            except Crypto.DoesNotExist:
                return render(request, 'search.html', {
                    'form': form,
                    'error': f"No cryptocurrency found with name '{query}'"
                })
    else:
        form = CryptoSearchForm()

    # Dynamically generate the URL for the API endpoint
    api_url = reverse('api_ranked_cryptos')  # This resolves to '/api/ranked-cryptos/'

    # Fetch the top 3 ranked cryptocurrencies from the API
    response = requests.get(f'http://127.0.0.1:8000{api_url}')
    ranked_cryptos = response.json()['cryptos'][:3]  # Get the top 3

    return render(request, 'markettracking/home.html', {
        'form': form,
        'top_cryptos': ranked_cryptos,
    })



from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.core.cache import cache
import plotly.express as px
from django.views.generic import ListView
from django.core.paginator import Paginator
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.db.models import Prefetch
from typing import List, Dict, Any
import logging
from .models import Crypto, priceInstance
from .utils import calculate_price_change, calculate_24hr_volume
from decimal import Decimal

logger = logging.getLogger(__name__)

def crypto_page(request, slug):
    crypto = get_object_or_404(Crypto, slug=slug)

    # Try to get the price from Redis
    price = cache.get(f"price:{crypto.symbol.upper()}")
    last_updated = cache.get(f"last_updated:{crypto.symbol.upper()}")

    # If there's no price in Redis, fetch the latest from the database
    if not price or not last_updated:
        latest_price_instance = crypto.price_history.order_by('-timestamp').first()
        price = latest_price_instance.price if latest_price_instance else None
        last_updated = latest_price_instance.timestamp if latest_price_instance else None

    # Fetch historical price data
    price_instances = crypto.price_history.all().order_by('timestamp')
    timestamps = [pi.timestamp for pi in price_instances]
    prices = [pi.price for pi in price_instances]

    # Create the Plotly graph with dark mode style
    fig = px.line(x=timestamps, y=prices, labels={'x': 'Timestamp', 'y': 'Price'})
    fig.update_layout(
        plot_bgcolor='rgba(0, 0, 0, 1)',
        paper_bgcolor='rgba(0, 0, 0, 1)',
        font=dict(color='white'),
        xaxis=dict(showgrid=True, gridcolor='rgba(255, 255, 255, 0.2)'),
        yaxis=dict(showgrid=True, gridcolor='rgba(255, 255, 255, 0.2)'),
    )

    # Get the HTML div for the graph
    graph_html = fig.to_html(full_html=False)

    # Calculate the 24-hour price change
    price_change_24h = calculate_price_change(crypto)

    # Calculate the 24-hour volume
    volume_24h = calculate_24hr_volume(crypto)

    return render(request, 'markettracking/crypto-page.html', {
        'crypto': crypto,
        'price': price,
        'last_updated': last_updated,
        'graph_html': graph_html,
        'price_change_24h': price_change_24h,
        'volume_24h': volume_24h,
        'market_cap': crypto.market_cap,  # Add market cap to context
    })

class MarketView(ListView):
    """
    Displays a paginated list of cryptocurrencies with sorting and filtering options.

    Supports sorting by rank, market cap, 24h price change, and name via query parameters.
    Caches results to improve performance. Provides AJAX support for dynamic updates.
    """
    template_name = 'markettracking/market.html'
    context_object_name = 'cryptos'
    paginate_by = 20
    allowed_sorts = {
        'rank_asc': ('rank', False),
        'rank_desc': ('rank', True),
        'market_cap_asc': ('market_cap', False),
        'market_cap_desc': ('market_cap', True),
        'price_change_asc': None,
        'price_change_desc': None,
        'name_asc': ('name', False),
        'name_desc': ('name', True),
    }

    def get_queryset(self) -> List[Dict[str, Any]]:
        cache_key = f'market_cryptos_{self.request.GET.get("sort", "rank_asc")}'
        cached_data = cache.get(cache_key)
        if cached_data:
            return cached_data

        try:
            queryset = Crypto.objects.prefetch_related(
                Prefetch('price_history', queryset=priceInstance.objects.order_by('-timestamp'))
            ).all()
            crypto_list = [
                {
                    'name': crypto.name,
                    'symbol': crypto.symbol,
                    'slug': crypto.slug,
                    'logo_url': crypto.logo_url,
                    'rank': crypto.rank,
                    'market_cap': crypto.market_cap,
                    'current_price': crypto.current_price,  # Use stored current_price
                    'price_change_24h': calculate_price_change(crypto),
                } for crypto in queryset
            ]
            cache.set(cache_key, crypto_list, timeout=300)
            return crypto_list
        except Exception as e:
            logger.error(f"Error fetching cryptocurrencies: {e}")
            return []

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['current_sort'] = self.request.GET.get('sort', 'rank_asc')
        return context

    def get(self, request, *args, **kwargs):
        sort = request.GET.get('sort', 'rank_asc')
        if sort not in self.allowed_sorts:
            sort = 'rank_asc'

        crypto_list = self.get_queryset()
        if sort in ['price_change_asc', 'price_change_desc']:
            crypto_list.sort(
                key=lambda x: x['price_change_24h'],
                reverse=(sort == 'price_change_desc')
            )
        elif sort in ['rank_asc', 'rank_desc']:
            crypto_list.sort(
                key=lambda x: (x['rank'] is None, x['rank']),
                reverse=(sort == 'rank_desc')
            )
        else:
            field, reverse = self.allowed_sorts[sort]
            crypto_list.sort(
                key=lambda x: x[field],
                reverse=reverse
            )

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            paginator = Paginator(crypto_list, self.paginate_by)
            page_number = request.GET.get('page', 1)
            page_obj = paginator.get_page(page_number)
            return JsonResponse({
                'cryptos': list(page_obj.object_list),
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
                'page_number': page_obj.number,
                'num_pages': paginator.num_pages,
            })

        self.object_list = crypto_list
        return super().get(request, *args, **kwargs)

    @method_decorator(cache_page(60 * 5))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)




def crypto_autocomplete(request):
    query = request.GET.get('query', '').strip()
    results = []

    if query:
        matches = Crypto.objects.filter(name__icontains=query)[:10]
        results = [
            {
                'name': c.name,
                'slug': c.slug,
                'logo_url': c.logo_url
            }
            for c in matches
        ]

    return JsonResponse({'results': results})

def latest_price_json(request):
    latest_price = priceInstance.objects.latest('timestamp')
    return JsonResponse({
        'price': str(latest_price.price),
        'timestamp': latest_price.timestamp.strftime('%Y-%m-%d %H:%M:%S')
    })



def get_latest_price(request, slug):
    crypto = get_object_or_404(Crypto, slug=slug)
    price = cache.get(f"price:{crypto.symbol.upper()}")
    last_updated = cache.get(f"last_updated:{crypto.symbol.upper()}")

    if not price or not last_updated:
        latest_price_instance = crypto.price_history.order_by('-timestamp').first()
        price = latest_price_instance.price if latest_price_instance else None
        last_updated = latest_price_instance.timestamp if latest_price_instance else None

    # Send price and timestamp back as JSON for the AJAX request
    return JsonResponse({
        'price': float(price) if price else None,
        'last_updated': time.mktime(last_updated.timetuple()) if last_updated else None
    })




def api_ranked_cryptos(request):
    # Fetch all cryptocurrencies from the database
    cryptos = Crypto.objects.all()

    ranked_cryptos = []

    # Calculate price change for each crypto
    for crypto in cryptos:
        price_change = calculate_price_change(crypto)  # Assumes this function exists
        ranked_cryptos.append({
            'id': crypto.id,  # Store ID for updating later
            'name': crypto.name,
            'symbol': crypto.symbol,
            'slug': crypto.slug,
            'logo_url': crypto.logo_url,
            'price_change_24h': price_change,
            'market_cap': float(crypto.market_cap),  # Convert Decimal to float for JSON
            'rank': None,  # Placeholder for rank
            'current_price': crypto.current_price
        })

    # Sort by price change (descending) and market cap (descending)
    ranked_cryptos.sort(key=lambda x: (x['price_change_24h'], x['market_cap']), reverse=True)

    # Assign ranks and prepare for database update
    cryptos_to_update = []
    for index, crypto_data in enumerate(ranked_cryptos, start=1):
        crypto_data['rank'] = index  # Assign rank (1-based)
        # Get the Crypto instance for updating
        crypto_instance = Crypto.objects.get(id=crypto_data['id'])
        crypto_instance.rank = index
        cryptos_to_update.append(crypto_instance)

    # Update ranks in the database atomically
    with transaction.atomic():
        Crypto.objects.bulk_update(cryptos_to_update, ['rank'])

    # Return the response
    return JsonResponse({'cryptos': ranked_cryptos})

logger = logging.getLogger(__name__)
