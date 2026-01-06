# View Caching Reference

This document covers all view-level caching strategies in Django, from full-page caching to cache control headers.

## Table of Contents

- [Per-View Cache with @cache_page](#per-view-cache-with-cache_page)
- [Cache Middleware](#cache-middleware)
- [Cache Control with @cache_control](#cache-control-with-cache_control)
- [Vary Headers](#vary-headers)
- [Conditional View Processing](#conditional-view-processing)
- [Custom Cache Keys](#custom-cache-keys)
- [Cache for API Views](#cache-for-api-views)

## Per-View Cache with @cache_page

### Basic Usage

```python
from django.views.decorators.cache import cache_page

@cache_page(60 * 15)  # Cache for 15 minutes
def my_view(request):
    return render(request, 'template.html', context)
```

### With URL Parameters

```python
@cache_page(60 * 15)
def article_detail(request, article_id):
    # Each article_id gets its own cache entry
    article = get_object_or_404(Article, id=article_id)
    return render(request, 'article.html', {'article': article})
```

### With Query Parameters

```python
from django.views.decorators.cache import cache_page

@cache_page(60 * 15)
def search_results(request):
    # WARNING: Different query parameters create different cache entries
    # ?q=python and ?q=django create separate caches
    query = request.GET.get('q', '')
    results = search(query)
    return render(request, 'results.html', {'results': results})
```

### Specifying Cache Backend

```python
# Use specific cache backend
@cache_page(60 * 15, cache='special_cache')
def expensive_view(request):
    return render(request, 'template.html')

# settings.py
CACHES = {
    'default': {...},
    'special_cache': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/2',
    }
}
```

### URL Configuration Cache

```python
# urls.py
from django.views.decorators.cache import cache_page

urlpatterns = [
    path('articles/', cache_page(60 * 15)(views.article_list)),
    path('articles/<int:pk>/', cache_page(60 * 30)(views.article_detail)),
]
```

### Class-Based Views

```python
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from django.views.generic import ListView

# Decorate dispatch method
@method_decorator(cache_page(60 * 15), name='dispatch')
class ArticleListView(ListView):
    model = Article
    template_name = 'articles/list.html'

# Or in urls.py
urlpatterns = [
    path('articles/', cache_page(60 * 15)(ArticleListView.as_view())),
]
```

## Cache Middleware

### Site-Wide Caching

```python
# settings.py
MIDDLEWARE = [
    'django.middleware.cache.UpdateCacheMiddleware',  # MUST be first
    'django.middleware.common.CommonMiddleware',
    # ... other middleware ...
    'django.middleware.cache.FetchFromCacheMiddleware',  # MUST be last
]

# Cache settings
CACHE_MIDDLEWARE_ALIAS = 'default'
CACHE_MIDDLEWARE_SECONDS = 600  # 10 minutes
CACHE_MIDDLEWARE_KEY_PREFIX = 'mysite'
```

### How Cache Middleware Works

1. **UpdateCacheMiddleware** (first): Caches responses on the way out
2. **FetchFromCacheMiddleware** (last): Retrieves cached responses on the way in

```python
# Request flow:
# 1. Request comes in → FetchFromCacheMiddleware checks cache
# 2. If cached: Return cached response immediately
# 3. If not cached: Process through all middleware and view
# 4. Response ready → UpdateCacheMiddleware saves to cache
```

### Per-User Caching with Middleware

```python
# Cache varies on Cookie header (includes sessionid)
MIDDLEWARE = [
    'django.middleware.cache.UpdateCacheMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',  # Before FetchFromCache
    'django.middleware.cache.FetchFromCacheMiddleware',
]

# Each user gets their own cached version
```

### Conditional Caching

```python
# Custom middleware for conditional caching
class ConditionalCacheMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Don't cache authenticated users
        if request.user.is_authenticated:
            request._cache_update_cache = False

        response = self.get_response(request)

        # Don't cache error responses
        if response.status_code != 200:
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'

        return response

# settings.py
MIDDLEWARE = [
    'myapp.middleware.ConditionalCacheMiddleware',
    # ... other middleware ...
]
```

## Cache Control with @cache_control

### Setting Cache-Control Headers

```python
from django.views.decorators.cache import cache_control

@cache_control(private=True, max_age=3600)
def user_profile(request):
    # Browser caches for 1 hour, but marked as private (not shared caches)
    return render(request, 'profile.html')

@cache_control(public=True, max_age=300)
def public_page(request):
    # Can be cached by browser and CDN for 5 minutes
    return render(request, 'public.html')

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
def sensitive_data(request):
    # Never cache this
    return render(request, 'sensitive.html')
```

### Common Cache-Control Directives

```python
from django.views.decorators.cache import cache_control

# Public, cacheable by CDN
@cache_control(public=True, max_age=3600)
def static_page(request):
    pass

# Private, browser only
@cache_control(private=True, max_age=300)
def user_page(request):
    pass

# No caching at all
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
def no_cache_page(request):
    pass

# Cacheable but must revalidate
@cache_control(max_age=0, must_revalidate=True)
def revalidate_page(request):
    pass

# Immutable (never changes)
@cache_control(public=True, max_age=31536000, immutable=True)
def immutable_asset(request):
    pass
```

### Combining with @cache_page

```python
from django.views.decorators.cache import cache_page, cache_control

# Server-side cache for 15 min, browser cache for 5 min
@cache_page(60 * 15)
@cache_control(max_age=300)
def my_view(request):
    return render(request, 'template.html')
```

### Patch Cache Control

```python
from django.views.decorators.cache import patch_cache_control

def my_view(request):
    response = render(request, 'template.html')

    # Conditionally modify cache control
    if request.user.is_authenticated:
        patch_cache_control(response, private=True, max_age=300)
    else:
        patch_cache_control(response, public=True, max_age=3600)

    return response
```

### Never Cache Decorator

```python
from django.views.decorators.cache import never_cache

@never_cache
def sensitive_view(request):
    # Sets: Cache-Control: max-age=0, no-cache, no-store, must-revalidate, private
    return render(request, 'sensitive.html')
```

## Vary Headers

### vary_on_headers Decorator

```python
from django.views.decorators.vary import vary_on_headers

@cache_page(60 * 15)
@vary_on_headers('User-Agent')
def my_view(request):
    # Different cache for each User-Agent
    return render(request, 'template.html')

@cache_page(60 * 15)
@vary_on_headers('Accept-Language', 'User-Agent')
def localized_view(request):
    # Cache varies on both language and user agent
    return render(request, 'template.html')
```

### vary_on_cookie Decorator

```python
from django.views.decorators.vary import vary_on_cookie

@cache_page(60 * 15)
@vary_on_cookie
def user_dashboard(request):
    # Each user (by session cookie) gets their own cache
    return render(request, 'dashboard.html', {
        'user': request.user
    })
```

### Manual Vary Headers

```python
from django.views.decorators.vary import vary_on_headers

def my_view(request):
    response = render(request, 'template.html')
    response['Vary'] = 'Accept-Language, User-Agent'
    return response
```

### Common Vary Patterns

```python
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers, vary_on_cookie

# Per-user caching
@cache_page(60 * 15)
@vary_on_cookie
def user_specific(request):
    pass

# Per-language caching
@cache_page(60 * 15)
@vary_on_headers('Accept-Language')
def localized(request):
    pass

# Mobile vs desktop
@cache_page(60 * 15)
@vary_on_headers('User-Agent')
def responsive(request):
    pass

# API versioning
@cache_page(60 * 15)
@vary_on_headers('Accept')
def api_endpoint(request):
    pass
```

## Conditional View Processing

### ETag Support

```python
from django.views.decorators.http import etag

def generate_etag(request, *args, **kwargs):
    # Generate unique identifier for resource state
    return hashlib.md5(
        f"{request.path}:{Article.objects.latest('modified').modified}".encode()
    ).hexdigest()

@etag(generate_etag)
def article_list(request):
    # Returns 304 Not Modified if ETag matches
    articles = Article.objects.all()
    return render(request, 'articles.html', {'articles': articles})
```

### Last-Modified Support

```python
from django.views.decorators.http import last_modified

def latest_article_time(request):
    return Article.objects.latest('modified').modified

@last_modified(latest_article_time)
def article_list(request):
    # Returns 304 Not Modified if content hasn't changed
    articles = Article.objects.all()
    return render(request, 'articles.html', {'articles': articles})
```

### Combining ETag and Last-Modified

```python
from django.views.decorators.http import condition

def latest_article_time(request):
    return Article.objects.latest('modified').modified

def article_etag(request):
    latest = Article.objects.latest('modified')
    return hashlib.md5(f"{latest.id}:{latest.modified}".encode()).hexdigest()

@condition(etag_func=article_etag, last_modified_func=latest_article_time)
def article_list(request):
    articles = Article.objects.all()
    return render(request, 'articles.html', {'articles': articles})
```

### Manual Conditional Processing

```python
from django.http import HttpResponseNotModified
from django.utils.http import http_date

def article_list(request):
    latest = Article.objects.latest('modified')

    # Check If-Modified-Since header
    if_modified_since = request.META.get('HTTP_IF_MODIFIED_SINCE')
    if if_modified_since:
        if_modified_since = parse_http_date(if_modified_since)
        if latest.modified.timestamp() <= if_modified_since:
            return HttpResponseNotModified()

    response = render(request, 'articles.html', {
        'articles': Article.objects.all()
    })

    # Set Last-Modified header
    response['Last-Modified'] = http_date(latest.modified.timestamp())

    return response
```

## Custom Cache Keys

### Key Prefix Function

```python
# settings.py
def make_key_prefix(key, key_prefix, version):
    return f'{key_prefix}:{version}:{request.user.id}:{key}'

CACHES = {
    'default': {
        'KEY_FUNCTION': 'myapp.cache.make_key_prefix',
    }
}
```

### Cache Key Function for Views

```python
from django.utils.cache import get_cache_key

def my_view(request):
    # Get the cache key that would be used
    cache_key = get_cache_key(request)

    # Manually manipulate cache
    if cache_key:
        from django.core.cache import cache
        cache.delete(cache_key)

    return render(request, 'template.html')
```

### Custom Cache Key Decorator

```python
from functools import wraps
from django.core.cache import cache

def cache_page_per_user(timeout):
    """Cache page separately for each user"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Generate user-specific cache key
            cache_key = f'view:{request.path}:user:{request.user.id}'

            # Try to get from cache
            response = cache.get(cache_key)
            if response is not None:
                return response

            # Generate response
            response = view_func(request, *args, **kwargs)

            # Cache it
            cache.set(cache_key, response, timeout)

            return response
        return wrapper
    return decorator

# Usage
@cache_page_per_user(60 * 15)
def user_dashboard(request):
    return render(request, 'dashboard.html')
```

## Cache for API Views

### Django REST Framework Integration

```python
from rest_framework.views import APIView
from rest_framework.response import Response
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator

class ArticleListAPI(APIView):
    @method_decorator(cache_page(60 * 15))
    def get(self, request):
        articles = Article.objects.all()
        serializer = ArticleSerializer(articles, many=True)
        return Response(serializer.data)
```

### Cache with Vary on Accept Header

```python
from django.views.decorators.vary import vary_on_headers

class ArticleListAPI(APIView):
    @method_decorator(cache_page(60 * 15))
    @method_decorator(vary_on_headers('Accept', 'Accept-Language'))
    def get(self, request):
        # Different cache for JSON vs XML, and per language
        articles = Article.objects.all()
        serializer = ArticleSerializer(articles, many=True)
        return Response(serializer.data)
```

### Custom API Cache

```python
from functools import wraps
from django.core.cache import cache
from rest_framework.response import Response
import hashlib
import json

def cache_api_response(timeout=300):
    """Cache API responses based on path, query params, and user"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Generate cache key from request
            cache_key_data = {
                'path': request.path,
                'method': request.method,
                'query': dict(request.GET),
                'user': request.user.id if request.user.is_authenticated else None,
            }
            cache_key_str = json.dumps(cache_key_data, sort_keys=True)
            cache_key = f'api:{hashlib.md5(cache_key_str.encode()).hexdigest()}'

            # Try to get from cache
            cached_data = cache.get(cache_key)
            if cached_data is not None:
                return Response(cached_data)

            # Generate response
            response = view_func(request, *args, **kwargs)

            # Cache successful responses
            if isinstance(response, Response) and 200 <= response.status_code < 300:
                cache.set(cache_key, response.data, timeout)

            return response
        return wrapper
    return decorator

# Usage
@cache_api_response(timeout=300)
def article_list_api(request):
    articles = Article.objects.all()
    serializer = ArticleSerializer(articles, many=True)
    return Response(serializer.data)
```

## Performance Patterns

### Partial Page Caching

```python
from django.core.cache import cache

def homepage(request):
    # Cache expensive components separately
    recent_posts = cache.get_or_set(
        'homepage:recent_posts',
        lambda: list(Post.objects.order_by('-created')[:5]),
        300
    )

    popular_posts = cache.get_or_set(
        'homepage:popular_posts',
        lambda: list(Post.objects.order_by('-views')[:5]),
        600
    )

    # User-specific data not cached
    user_activity = get_user_activity(request.user)

    return render(request, 'homepage.html', {
        'recent_posts': recent_posts,
        'popular_posts': popular_posts,
        'user_activity': user_activity,
    })
```

### Cache Warming for Views

```python
from django.test import RequestFactory
from django.core.cache import cache

def warm_view_cache(view_func, url_path, timeout=300):
    """Pre-populate view cache"""
    factory = RequestFactory()
    request = factory.get(url_path)

    # Generate response (this will populate cache)
    response = view_func(request)

    return response

# In management command or celery task
warm_view_cache(article_list, '/articles/', timeout=60*15)
```

### Invalidate View Cache

```python
from django.core.cache import cache
from django.utils.cache import get_cache_key
from django.test import RequestFactory

def invalidate_view_cache(url_path):
    """Invalidate cached view"""
    factory = RequestFactory()
    request = factory.get(url_path)

    # Get cache key
    cache_key = get_cache_key(request)

    if cache_key:
        cache.delete(cache_key)
        return True
    return False

# Usage
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Article)
def invalidate_article_list_cache(sender, instance, **kwargs):
    invalidate_view_cache('/articles/')
    invalidate_view_cache(f'/articles/{instance.id}/')
```

## Complete Example

```python
from django.views.decorators.cache import cache_page, cache_control
from django.views.decorators.vary import vary_on_cookie
from django.views.decorators.http import condition
from django.core.cache import cache
from django.shortcuts import render
import hashlib

def article_etag(request):
    """Generate ETag based on latest article"""
    latest = Article.objects.latest('modified')
    return hashlib.md5(
        f"{latest.id}:{latest.modified}".encode()
    ).hexdigest()

def article_last_modified(request):
    """Get last modified time"""
    return Article.objects.latest('modified').modified

@cache_page(60 * 15)  # Cache on server for 15 minutes
@cache_control(public=True, max_age=300)  # Browser cache for 5 minutes
@vary_on_headers('Accept-Language')  # Different cache per language
@condition(etag_func=article_etag, last_modified_func=article_last_modified)
def article_list(request):
    """
    Article list with multiple caching strategies:
    - Server-side caching with @cache_page
    - Browser caching with Cache-Control
    - Per-language caching with Vary
    - Conditional responses with ETag/Last-Modified
    """
    articles = cache.get_or_set(
        'articles:list',
        lambda: list(Article.objects.select_related('author')
                     .prefetch_related('tags')
                     .filter(published=True)
                     .order_by('-created')),
        300
    )

    return render(request, 'articles/list.html', {
        'articles': articles
    })
```
