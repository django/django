# Common Caching Patterns

This document covers common caching patterns and real-world examples for Django applications.

## Table of Contents

- [Cache-Aside Pattern](#cache-aside-pattern)
- [Write-Through Cache](#write-through-cache)
- [Write-Behind Cache](#write-behind-cache)
- [Read-Through Cache](#read-through-cache)
- [QuerySet Caching](#queryset-caching)
- [Computed Property Caching](#computed-property-caching)
- [API Response Caching](#api-response-caching)
- [Search Result Caching](#search-result-caching)
- [Session Data Caching](#session-data-caching)
- [Rate Limiting with Cache](#rate-limiting-with-cache)

## Cache-Aside Pattern

Also known as "Lazy Loading". Application checks cache first, loads from database on miss, then stores in cache.

### Basic Implementation

```python
from django.core.cache import cache

def get_user_profile(user_id):
    """Cache-aside pattern for user profile"""
    cache_key = f'user:profile:{user_id}'

    # Try to get from cache
    profile = cache.get(cache_key)

    if profile is None:
        # Cache miss - load from database
        profile = UserProfile.objects.select_related('user').get(user_id=user_id)

        # Store in cache
        cache.set(cache_key, profile, timeout=3600)

    return profile
```

### With get_or_set Helper

```python
from django.core.cache import cache

def get_user_profile(user_id):
    """Simpler cache-aside using get_or_set"""
    return cache.get_or_set(
        f'user:profile:{user_id}',
        lambda: UserProfile.objects.select_related('user').get(user_id=user_id),
        timeout=3600
    )
```

### With Error Handling

```python
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

def get_user_profile(user_id):
    """Cache-aside with error handling"""
    cache_key = f'user:profile:{user_id}'

    try:
        profile = cache.get(cache_key)
        if profile is not None:
            return profile
    except Exception as e:
        logger.warning(f"Cache get failed: {e}")

    # Load from database
    profile = UserProfile.objects.select_related('user').get(user_id=user_id)

    # Try to cache
    try:
        cache.set(cache_key, profile, 3600)
    except Exception as e:
        logger.warning(f"Cache set failed: {e}")

    return profile
```

## Write-Through Cache

Update cache and database simultaneously. Ensures cache is always consistent with database.

### Basic Implementation

```python
from django.core.cache import cache
from django.db import transaction

def update_product(product_id, **kwargs):
    """Write-through cache for product updates"""
    with transaction.atomic():
        # Update database
        product = Product.objects.select_for_update().get(id=product_id)
        for key, value in kwargs.items():
            setattr(product, key, value)
        product.save()

        # Update cache immediately
        cache_key = f'product:{product_id}'
        cache.set(cache_key, product, timeout=3600)

    return product
```

### With Multiple Cache Locations

```python
from django.core.cache import cache

def update_article(article_id, **kwargs):
    """Update article and all its cached representations"""
    article = Article.objects.get(id=article_id)

    # Update database
    for key, value in kwargs.items():
        setattr(article, key, value)
    article.save()

    # Update all cache locations
    cache.set_many({
        f'article:{article_id}': article,
        f'article:detail:{article_id}': {
            'id': article.id,
            'title': article.title,
            'content': article.content,
        },
        f'article:summary:{article_id}': {
            'id': article.id,
            'title': article.title,
            'summary': article.summary,
        }
    }, timeout=3600)

    return article
```

## Write-Behind Cache

Update cache immediately but defer database write. Improves write performance but risks data loss.

### Basic Implementation (Use with Caution)

```python
from django.core.cache import cache
from celery import shared_task

def update_view_count(article_id):
    """Update view count in cache, sync to DB later"""
    cache_key = f'article:views:{article_id}'

    # Increment in cache
    try:
        cache.incr(cache_key)
    except ValueError:
        # Key doesn't exist, initialize
        cache.set(cache_key, 1, timeout=None)

    # Schedule database update (every 100 views or 5 minutes)
    views = cache.get(cache_key)
    if views % 100 == 0:
        sync_view_count_to_db.delay(article_id, views)

@shared_task
def sync_view_count_to_db(article_id, view_count):
    """Periodic sync of view counts to database"""
    Article.objects.filter(id=article_id).update(views=view_count)
```

### With Periodic Sync

```python
from celery import shared_task
from django.core.cache import cache

@shared_task
def sync_all_counters():
    """Periodically sync all cached counters to database"""
    # Get all counter keys (Redis-specific)
    if hasattr(cache, 'keys'):
        counter_keys = cache.keys('counter:*')

        for key in counter_keys:
            try:
                # Extract entity info from key
                _, entity_type, entity_id = key.split(':')
                count = cache.get(key)

                if count:
                    # Update database
                    if entity_type == 'article':
                        Article.objects.filter(id=entity_id).update(views=count)
                    elif entity_type == 'user':
                        User.objects.filter(id=entity_id).update(profile_views=count)

            except Exception as e:
                logger.error(f"Failed to sync counter {key}: {e}")
```

## Read-Through Cache

Cache layer intercepts read requests. If not cached, loads from database and caches automatically.

### Custom Cache Manager

```python
from django.core.cache import cache

class CachedManager:
    """Manager that implements read-through caching"""

    def __init__(self, model, timeout=3600):
        self.model = model
        self.timeout = timeout

    def get(self, **kwargs):
        """Get object with read-through caching"""
        # Generate cache key from lookup kwargs
        cache_key = self._make_key(kwargs)

        # Try cache first
        obj = cache.get(cache_key)

        if obj is None:
            # Cache miss - load from database
            obj = self.model.objects.get(**kwargs)

            # Store in cache
            cache.set(cache_key, obj, self.timeout)

        return obj

    def _make_key(self, kwargs):
        """Generate cache key from lookup kwargs"""
        key_parts = [self.model.__name__.lower()]
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}:{v}")
        return ':'.join(key_parts)

# Usage
article_cache = CachedManager(Article, timeout=3600)
article = article_cache.get(id=123)
```

## QuerySet Caching

### Simple QuerySet Cache

```python
from django.core.cache import cache

def get_published_articles():
    """Cache QuerySet results"""
    cache_key = 'articles:published'

    # Force QuerySet evaluation with list()
    return cache.get_or_set(
        cache_key,
        lambda: list(
            Article.objects.filter(published=True)
            .select_related('author')
            .prefetch_related('tags')
            .order_by('-created_at')[:20]
        ),
        timeout=300
    )
```

### Cache Only IDs, Fetch Fresh Objects

```python
from django.core.cache import cache

def get_popular_articles():
    """Cache article IDs, fetch fresh objects"""
    cache_key = 'articles:popular:ids'

    # Cache only IDs
    article_ids = cache.get_or_set(
        cache_key,
        lambda: list(
            Article.objects.filter(views__gt=1000)
            .values_list('id', flat=True)
            .order_by('-views')[:10]
        ),
        timeout=600
    )

    # Fetch fresh objects (gets latest data)
    return Article.objects.filter(id__in=article_ids).select_related('author')
```

### Paginated QuerySet Cache

```python
from django.core.cache import cache
from django.core.paginator import Paginator

def get_articles_page(page_number=1, per_page=20):
    """Cache individual pages of articles"""
    # Cache the queryset IDs
    ids_key = 'articles:all:ids'
    article_ids = cache.get_or_set(
        ids_key,
        lambda: list(Article.objects.values_list('id', flat=True)),
        timeout=300
    )

    # Paginate IDs
    paginator = Paginator(article_ids, per_page)
    page = paginator.get_page(page_number)

    # Fetch objects for this page
    page_ids = page.object_list
    articles = Article.objects.filter(id__in=page_ids).select_related('author')

    return articles, page
```

## Computed Property Caching

### Using @cached_property

```python
from django.utils.functional import cached_property
from django.db import models

class User(models.Model):
    username = models.CharField(max_length=100)

    @cached_property
    def total_orders_value(self):
        """Cached for the lifetime of the instance"""
        return self.orders.aggregate(
            total=Sum('total')
        )['total'] or 0

    @cached_property
    def active_subscriptions(self):
        """Cached query result"""
        return self.subscriptions.filter(
            status='active',
            end_date__gte=timezone.now()
        )

# Usage - computed once per instance
user = User.objects.get(id=123)
total = user.total_orders_value  # Computes and caches
total_again = user.total_orders_value  # Returns cached value
```

### Custom Property Cache Decorator

```python
from functools import wraps
from django.core.cache import cache

def cached_model_property(timeout=3600):
    """Decorator for caching model properties across instances"""
    def decorator(func):
        @wraps(func)
        def wrapper(self):
            cache_key = f'{self.__class__.__name__}:{self.pk}:{func.__name__}'

            value = cache.get(cache_key)
            if value is None:
                value = func(self)
                cache.set(cache_key, value, timeout)

            return value
        return property(wrapper)
    return decorator

class Article(models.Model):
    @cached_model_property(timeout=600)
    def comment_count(self):
        """Cached across different Article instances"""
        return self.comments.count()

    @cached_model_property(timeout=1800)
    def related_articles(self):
        """Expensive computed property"""
        return list(
            Article.objects.filter(tags__in=self.tags.all())
            .exclude(id=self.id)
            .distinct()[:5]
        )
```

## API Response Caching

### External API Call Cache

```python
from django.core.cache import cache
import requests

def get_weather_data(city):
    """Cache external API responses"""
    cache_key = f'weather:{city}'

    data = cache.get(cache_key)

    if data is None:
        # API call
        response = requests.get(
            f'https://api.weather.com/v1/weather',
            params={'city': city}
        )
        data = response.json()

        # Cache for 30 minutes
        cache.set(cache_key, data, timeout=1800)

    return data
```

### REST API Endpoint Cache

```python
from rest_framework.views import APIView
from rest_framework.response import Response
from django.core.cache import cache
import hashlib
import json

class CachedAPIView(APIView):
    """Base view with automatic response caching"""

    cache_timeout = 300

    def dispatch(self, request, *args, **kwargs):
        # Generate cache key from request
        cache_key = self._get_cache_key(request, *args, **kwargs)

        # Try cache
        cached_response = cache.get(cache_key)
        if cached_response:
            return Response(cached_response)

        # Generate response
        response = super().dispatch(request, *args, **kwargs)

        # Cache successful responses
        if 200 <= response.status_code < 300:
            cache.set(cache_key, response.data, self.cache_timeout)

        return response

    def _get_cache_key(self, request, *args, **kwargs):
        """Generate cache key from request parameters"""
        key_data = {
            'path': request.path,
            'method': request.method,
            'query': dict(request.GET),
            'user': request.user.id if request.user.is_authenticated else None,
        }
        key_str = json.dumps(key_data, sort_keys=True)
        key_hash = hashlib.md5(key_str.encode()).hexdigest()
        return f'api:{key_hash}'

class ArticleListAPI(CachedAPIView):
    cache_timeout = 600

    def get(self, request):
        articles = Article.objects.all()
        serializer = ArticleSerializer(articles, many=True)
        return Response(serializer.data)
```

## Search Result Caching

### Basic Search Cache

```python
from django.core.cache import cache
import hashlib

def search_articles(query, filters=None):
    """Cache search results"""
    # Generate cache key from query and filters
    cache_key_data = f"{query}:{filters or {}}"
    cache_key = f"search:{hashlib.md5(cache_key_data.encode()).hexdigest()}"

    results = cache.get(cache_key)

    if results is None:
        # Perform search
        qs = Article.objects.filter(
            title__icontains=query
        ) | Article.objects.filter(
            content__icontains=query
        )

        if filters:
            if 'category' in filters:
                qs = qs.filter(category_id=filters['category'])
            if 'author' in filters:
                qs = qs.filter(author_id=filters['author'])

        results = list(qs.distinct()[:50])

        # Cache for 5 minutes
        cache.set(cache_key, results, timeout=300)

    return results
```

### Search with Elasticsearch/Full-Text Cache

```python
from django.core.cache import cache
from elasticsearch import Elasticsearch

def search_with_cache(query, page=1, per_page=20):
    """Cache Elasticsearch results"""
    cache_key = f'search:es:{query}:page:{page}'

    results = cache.get(cache_key)

    if results is None:
        es = Elasticsearch()
        response = es.search(
            index='articles',
            body={
                'query': {'match': {'content': query}},
                'from': (page - 1) * per_page,
                'size': per_page
            }
        )

        results = {
            'hits': response['hits']['hits'],
            'total': response['hits']['total']['value']
        }

        # Cache for 10 minutes
        cache.set(cache_key, results, timeout=600)

    return results
```

## Session Data Caching

### Cache Expensive Session Computations

```python
from django.core.cache import cache

def get_user_cart(request):
    """Cache user's shopping cart"""
    if not request.user.is_authenticated:
        return None

    cache_key = f'cart:user:{request.user.id}'

    cart = cache.get(cache_key)

    if cart is None:
        # Fetch cart with all items
        cart = {
            'items': list(
                CartItem.objects.filter(user=request.user)
                .select_related('product')
                .values('product__id', 'product__name', 'quantity', 'price')
            ),
            'total': CartItem.objects.filter(user=request.user)
            .aggregate(total=Sum(F('quantity') * F('price')))['total'] or 0
        }

        # Cache for 5 minutes
        cache.set(cache_key, cart, timeout=300)

    return cart

def add_to_cart(user, product, quantity):
    """Add item and invalidate cart cache"""
    cart_item, created = CartItem.objects.get_or_create(
        user=user,
        product=product,
        defaults={'quantity': quantity}
    )

    if not created:
        cart_item.quantity += quantity
        cart_item.save()

    # Invalidate cart cache
    cache.delete(f'cart:user:{user.id}')

    return cart_item
```

## Rate Limiting with Cache

### Simple Rate Limiter

```python
from django.core.cache import cache
from django.http import HttpResponseForbidden

def rate_limit(key, limit=100, period=3600):
    """
    Rate limiter using cache.

    Args:
        key: Unique key for rate limit (e.g., user ID, IP)
        limit: Maximum requests allowed
        period: Time period in seconds

    Returns:
        bool: True if within limit, False if exceeded
    """
    cache_key = f'ratelimit:{key}'

    try:
        current = cache.incr(cache_key)
    except ValueError:
        # Key doesn't exist, create it
        cache.set(cache_key, 1, timeout=period)
        return True

    return current <= limit

# Usage in view
def api_endpoint(request):
    user_key = f'user:{request.user.id}'

    if not rate_limit(user_key, limit=100, period=3600):
        return HttpResponseForbidden("Rate limit exceeded")

    # Process request
    return JsonResponse({'status': 'ok'})
```

### Advanced Rate Limiter with Sliding Window

```python
from django.core.cache import cache
from django.utils import timezone
import time

class SlidingWindowRateLimiter:
    """Sliding window rate limiter"""

    def __init__(self, key, limit, window_seconds):
        self.key = f'ratelimit:sliding:{key}'
        self.limit = limit
        self.window = window_seconds

    def is_allowed(self):
        """Check if request is allowed"""
        now = time.time()
        window_start = now - self.window

        # Get current request timestamps
        timestamps = cache.get(self.key) or []

        # Remove old timestamps outside window
        timestamps = [ts for ts in timestamps if ts > window_start]

        # Check limit
        if len(timestamps) >= self.limit:
            return False

        # Add current timestamp
        timestamps.append(now)

        # Update cache
        cache.set(self.key, timestamps, timeout=self.window)

        return True

    def remaining(self):
        """Get remaining requests in window"""
        now = time.time()
        window_start = now - self.window

        timestamps = cache.get(self.key) or []
        timestamps = [ts for ts in timestamps if ts > window_start]

        return max(0, self.limit - len(timestamps))

# Usage
def api_view(request):
    limiter = SlidingWindowRateLimiter(
        key=f'user:{request.user.id}',
        limit=100,
        window_seconds=3600
    )

    if not limiter.is_allowed():
        return JsonResponse(
            {'error': 'Rate limit exceeded'},
            status=429
        )

    # Add rate limit info to headers
    response = JsonResponse({'data': 'success'})
    response['X-RateLimit-Remaining'] = limiter.remaining()
    return response
```

### Decorator for Rate Limiting

```python
from functools import wraps
from django.http import HttpResponseForbidden
from django.core.cache import cache

def ratelimit(limit=100, period=3600, key_func=None):
    """
    Rate limit decorator.

    Args:
        limit: Max requests
        period: Time window in seconds
        key_func: Function to generate rate limit key from request
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Generate rate limit key
            if key_func:
                key = key_func(request)
            elif request.user.is_authenticated:
                key = f'user:{request.user.id}'
            else:
                key = f'ip:{request.META.get("REMOTE_ADDR")}'

            cache_key = f'ratelimit:{key}'

            # Check rate limit
            try:
                current = cache.incr(cache_key)
                if current > limit:
                    return HttpResponseForbidden("Rate limit exceeded")
            except ValueError:
                cache.set(cache_key, 1, timeout=period)

            return view_func(request, *args, **kwargs)

        return wrapper
    return decorator

# Usage
@ratelimit(limit=50, period=300)  # 50 requests per 5 minutes
def my_api_view(request):
    return JsonResponse({'data': 'success'})

@ratelimit(limit=10, period=60, key_func=lambda r: r.POST.get('email'))
def password_reset_view(request):
    # Rate limited per email address
    return JsonResponse({'status': 'ok'})
```

## Complete E-commerce Example

```python
from django.core.cache import cache
from django.db.models import Sum, F, Count
from django.utils.functional import cached_property

class ProductManager:
    """Manager for product caching operations"""

    @staticmethod
    def get_product(product_id):
        """Get product with cache-aside pattern"""
        return cache.get_or_set(
            f'product:{product_id}',
            lambda: Product.objects.select_related('category', 'brand').get(id=product_id),
            timeout=3600
        )

    @staticmethod
    def get_category_products(category_id):
        """Get products by category (cache IDs only)"""
        cache_key = f'category:{category_id}:product_ids'

        product_ids = cache.get_or_set(
            cache_key,
            lambda: list(
                Product.objects.filter(category_id=category_id, active=True)
                .values_list('id', flat=True)
            ),
            timeout=600
        )

        return Product.objects.filter(id__in=product_ids)

    @staticmethod
    def update_product(product_id, **kwargs):
        """Update product with write-through cache"""
        product = Product.objects.get(id=product_id)

        for key, value in kwargs.items():
            setattr(product, key, value)
        product.save()

        # Update cache immediately
        cache.set(f'product:{product_id}', product, 3600)

        # Invalidate related caches
        cache.delete(f'category:{product.category_id}:product_ids')

        return product

class Product(models.Model):
    name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.ForeignKey('Category', on_delete=models.CASCADE)

    @cached_property
    def average_rating(self):
        """Cached average rating for request duration"""
        return self.reviews.aggregate(avg=Avg('rating'))['avg'] or 0

    def get_cached_review_stats(self):
        """Cached review statistics across instances"""
        return cache.get_or_set(
            f'product:{self.id}:review_stats',
            lambda: {
                'count': self.reviews.count(),
                'average': self.average_rating,
                'distribution': self.reviews.values('rating')
                .annotate(count=Count('id'))
                .order_by('rating')
            },
            timeout=1800
        )

# Usage
product = ProductManager.get_product(123)
print(product.name)

# Update product
ProductManager.update_product(123, price=Decimal('19.99'))

# Get review stats (cached)
stats = product.get_cached_review_stats()
```
