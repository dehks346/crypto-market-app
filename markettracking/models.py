from django.db import models

# Create your models here.
class Crypto(models.Model):
    name = models.CharField(max_length=100)
    symbol = models.CharField(max_length=10)
    slug = models.SlugField(unique=True)
    logo_url = models.URLField(blank=True)
    rank = models.IntegerField(null=True, blank=True)
    market_cap = models.DecimalField(max_digits=20, decimal_places=2, default=0)  # Added market cap
    current_price = models.DecimalField(max_digits=20, decimal_places=8, default=0)



class priceInstance(models.Model):
    crypto = models.ForeignKey(Crypto, on_delete=models.CASCADE, related_name='price_history', null=True)
    price = models.DecimalField(max_digits=20, decimal_places=8)
    timestamp = models.DateTimeField(auto_now_add=True)
    volume = models.DecimalField(max_digits=20, decimal_places=8, default=0)  

    
