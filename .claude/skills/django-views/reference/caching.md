# View Caching Reference

Complete guide to caching Django views for better performance.

## Table of Contents

- [Cache Backends](#cache-backends)
- [cache_page Decorator](#cache_page-decorator)
- [Cache Control](#cache-control)
- [Conditional Views (ETags & Last-Modified)](#conditional-views-etags--last-modified)
- [Cache Invalidation](#cache-invalidation)
- [Per-User Caching](#per-user-caching)
- [Fragment Caching](#fragment-caching)
- [Low-Level Cache API](#low-level-cache-api)
- [Best Practices](#best-practices)

## Cache Backends

### Configuration

```python
# settings.py

# Development - Local memory cache
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

# Production - Redis
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'db': 1,
            'parser_class': 'redis.connection.PythonParser',
            'pool_class': 'redis.BlockingConnectionPool',
        }
    }
}

# Production - Memcached
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.PyMemcacheCache',
        'LOCATION': '127.0.0.1:11211',
    }
}

# Multiple caches
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
    },
    'sessions': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/2',
    },
    'staticfiles': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/3',
    },
}
```

## cache_page Decorator

### Basic Usage

```python
from django.views.decorators.cache import cache_page

# Cache for 15 minutes (900 seconds)
@cache_page(60 * 15)
def article_list(request):
    articles = Article.objects.filter(published=True)
    return render(request, 'blog/article_list.html', {
        'articles': articles
    })
```

### With URL Parameters

```python
# Different cache for each article
@cache_page(60 * 15)
def article_detail(request, slug):
    article = get_object_or_404(Article, slug=slug)
    return render(request, 'blog/article_detail.html', {
        'article': article
    })

# Cache key includes: URL path, query params, language, etc.
# /articles/django-tips/ → cached separately from /articles/python-tricks/
```

### URLconf Caching

```python
# urls.py
from django.views.decorators.cache import cache_page

urlpatterns = [
    path('articles/', cache_page(60 * 15)(views.article_list)),
    path('articles/<slug:slug>/', cache_page(60 * 15)(views.article_detail)),
]
```

### Class-Based Views

```python
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.generic import ListView

# Option 1: Decorate dispatch()
class ArticleListView(ListView):
    model = Article

    @method_decorator(cache_page(60 * 15))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

# Option 2: In URLs
urlpatterns = [
    path('articles/', cache_page(60 * 15)(ArticleListView.as_view())),
]

# Option 3: Mixin
class CachedListView(ListView):
    cache_timeout = 60 * 15

    @method_decorator(cache_page(cache_timeout))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

class ArticleListView(CachedListView):
    model = Article
    cache_timeout = 60 * 30  # Override
```

### Vary on Headers

```python
from django.views.decorators.vary import vary_on_headers

# Cache per language
@cache_page(60 * 15)
@vary_on_headers('Accept-Language')
def article_list(request):
    articles = Article.objects.filter(published=True)
    return render(request, 'blog/article_list.html', {
        'articles': articles
    })

# Cache per user agent
@cache_page(60 * 15)
@vary_on_headers('User-Agent')
def mobile_optimized(request):
    return render(request, 'mobile.html')

# Multiple headers
@cache_page(60 * 15)
@vary_on_headers('Accept-Language', 'Accept-Encoding')
def content(request):
    return render(request, 'content.html')
```

### Vary on Cookie

```python
from django.views.decorators.vary import vary_on_cookie

# Cache per user (based on session cookie)
@cache_page(60 * 15)
@vary_on_cookie
def dashboard(request):
    return render(request, 'dashboard.html', {
        'user': request.user
    })

# Specific cookie
@vary_on_headers('Cookie')
@cache_page(60 * 15)
def view(request):
    theme = request.COOKIES.get('theme', 'light')
    return render(request, 'page.html', {'theme': theme})
```

## Cache Control

### cache_control Decorator

```python
from django.views.decorators.cache import cache_control

# Browser caching (max-age in seconds)
@cache_control(max_age=3600)
def static_content(request):
    """Browser caches for 1 hour."""
    return render(request, 'static.html')

# No caching
@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
def sensitive_data(request):
    """Never cached."""
    return render(request, 'sensitive.html')

# Public vs Private
@cache_control(max_age=3600, public=True)
def public_page(request):
    """Can be cached by CDN."""
    return render(request, 'public.html')

@cache_control(max_age=3600, private=True)
def user_page(request):
    """Only cached by browser, not CDN."""
    return render(request, 'private.html')
```

### never_cache Decorator

```python
from django.views.decorators.cache import never_cache

# Never cache this view
@never_cache
def live_data(request):
    """Always fresh data."""
    data = get_realtime_data()
    return JsonResponse(data)
```

### Response Headers

```python
def article_detail(request, slug):
    article = get_object_or_404(Article, slug=slug)
    response = render(request, 'blog/article_detail.html', {
        'article': article
    })

    # Set cache headers manually
    response['Cache-Control'] = 'public, max-age=3600'
    response['Vary'] = 'Accept-Language'

    return response
```

## Conditional Views (ETags & Last-Modified)

### ETag Decorator

```python
from django.views.decorators.http import etag
import hashlib

def article_etag(request, slug):
    """Calculate ETag for article."""
    article = Article.objects.get(slug=slug)
    content = f"{article.id}:{article.updated_at.timestamp()}"
    return hashlib.md5(content.encode()).hexdigest()

@etag(article_etag)
def article_detail(request, slug):
    """Returns 304 Not Modified if ETag matches."""
    article = get_object_or_404(Article, slug=slug)
    return render(request, 'blog/article_detail.html', {
        'article': article
    })
```

**How it works:**
1. First request: Generate ETag, send with response
2. Browser stores ETag, sends in subsequent requests
3. Django checks ETag; if unchanged, returns 304
4. Browser uses cached version

### Last-Modified Decorator

```python
from django.views.decorators.http import last_modified

def article_last_modified(request, slug):
    """Get last modified time."""
    article = Article.objects.get(slug=slug)
    return article.updated_at

@last_modified(article_last_modified)
def article_detail(request, slug):
    """Returns 304 if not modified since last request."""
    article = get_object_or_404(Article, slug=slug)
    return render(request, 'blog/article_detail.html', {
        'article': article
    })
```

### Combined ETag + Last-Modified

```python
@etag(article_etag)
@last_modified(article_last_modified)
def article_detail(request, slug):
    """Most efficient - checks both."""
    article = get_object_or_404(Article, slug=slug)
    return render(request, 'blog/article_detail.html', {
        'article': article
    })
```

### Conditional Decorators with Exceptions

```python
def article_last_modified(request, slug):
    try:
        article = Article.objects.get(slug=slug)
        return article.updated_at
    except Article.DoesNotExist:
        # Return None for 404 cases
        return None

@last_modified(article_last_modified)
def article_detail(request, slug):
    article = get_object_or_404(Article, slug=slug)
    return render(request, 'blog/article_detail.html', {
        'article': article
    })
```

### Class-Based Views

```python
from django.utils.decorators import method_decorator

class ArticleDetailView(DetailView):
    model = Article

    @method_decorator(etag(article_etag))
    @method_decorator(last_modified(article_last_modified))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
```

## Cache Invalidation

### Manual Invalidation

```python
from django.core.cache import cache

# Clear specific cache key
cache.delete('article_list')

# Clear multiple keys
cache.delete_many(['article_list', 'article_detail_1', 'article_detail_2'])

# Clear all cache
cache.clear()
```

### Invalidate on Save

```python
# models.py
from django.core.cache import cache
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

class Article(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)

    def get_cache_key(self):
        return f'article_detail_{self.slug}'

@receiver(post_save, sender=Article)
@receiver(post_delete, sender=Article)
def invalidate_article_cache(sender, instance, **kwargs):
    """Clear cache when article changes."""
    # Clear detail page cache
    cache.delete(instance.get_cache_key())

    # Clear list cache
    cache.delete('article_list')

    # Clear all article-related caches
    cache.delete_many([
        'article_list',
        'article_featured',
        f'article_category_{instance.category_id}',
    ])
```

### Invalidate in View

```python
from django.views.generic import UpdateView
from django.core.cache import cache

class ArticleUpdateView(UpdateView):
    model = Article

    def form_valid(self, form):
        response = super().form_valid(form)

        # Invalidate caches
        cache.delete(f'article_detail_{self.object.slug}')
        cache.delete('article_list')

        return response
```

### Cache Versioning

```python
from django.core.cache import cache

# Increment version to invalidate all caches
CACHE_VERSION = 1

@cache_page(60 * 15, key_prefix=f'v{CACHE_VERSION}')
def article_list(request):
    articles = Article.objects.filter(published=True)
    return render(request, 'blog/article_list.html', {
        'articles': articles
    })

# When you want to invalidate all caches, increment CACHE_VERSION
# Old caches remain but won't be used
```

### Smart Invalidation

```python
class Article(models.Model):
    title = models.CharField(max_length=200)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)

    def invalidate_caches(self):
        """Invalidate all related caches."""
        keys_to_delete = [
            f'article_detail_{self.slug}',
            'article_list',
            f'article_category_{self.category_id}',
            f'article_author_{self.author_id}',
        ]

        cache.delete_many(keys_to_delete)

        # Also invalidate category list
        cache.delete(f'category_articles_{self.category_id}')

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.invalidate_caches()

    def delete(self, *args, **kwargs):
        self.invalidate_caches()
        super().delete(*args, **kwargs)
```

## Per-User Caching

### Using vary_on_cookie

```python
from django.views.decorators.vary import vary_on_cookie
from django.views.decorators.cache import cache_page

# Cache per user session
@cache_page(60 * 15)
@vary_on_cookie
def user_dashboard(request):
    return render(request, 'dashboard.html', {
        'user': request.user
    })
```

### Custom Cache Key

```python
from django.utils.cache import get_cache_key
from django.core.cache import cache

def per_user_cache(view_func):
    """Cache per authenticated user."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Anonymous users: normal caching
        if not request.user.is_authenticated:
            return view_func(request, *args, **kwargs)

        # Build cache key with user ID
        cache_key = f'user_{request.user.id}_{request.path}'

        # Check cache
        response = cache.get(cache_key)
        if response:
            return response

        # Generate response
        response = view_func(request, *args, **kwargs)

        # Cache for 15 minutes
        cache.set(cache_key, response, 60 * 15)

        return response

    return wrapper

@per_user_cache
def dashboard(request):
    return render(request, 'dashboard.html')
```

### Per-User + Per-Language

```python
def user_language_cache_key(request):
    """Generate cache key based on user and language."""
    user_id = request.user.id if request.user.is_authenticated else 'anon'
    language = request.LANGUAGE_CODE
    return f'view_{request.path}_{user_id}_{language}'

def multilingual_user_cache(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        cache_key = user_language_cache_key(request)

        response = cache.get(cache_key)
        if response:
            return response

        response = view_func(request, *args, **kwargs)
        cache.set(cache_key, response, 60 * 15)

        return response

    return wrapper
```

## Fragment Caching

### In Templates

```django
{% load cache %}

{# Cache for 15 minutes #}
{% cache 900 sidebar %}
    <div class="sidebar">
        {# Expensive query #}
        {% for category in categories %}
            <a href="{{ category.get_absolute_url }}">
                {{ category.name }}
            </a>
        {% endfor %}
    </div>
{% endcache %}

{# Cache with variables #}
{% cache 900 article_detail article.id %}
    <div class="article">
        {{ article.content }}
    </div>
{% endcache %}

{# Cache per user #}
{% cache 900 sidebar request.user.id %}
    {# User-specific sidebar #}
{% endcache %}

{# Cache per language #}
{% cache 900 header LANGUAGE_CODE %}
    {# Translated header #}
{% endcache %}
```

### Cache Template Fragment in View

```python
from django.core.cache import cache
from django.template.loader import render_to_string

def article_detail(request, slug):
    article = get_object_or_404(Article, slug=slug)

    # Check cache for sidebar
    sidebar_cache_key = 'sidebar'
    sidebar_html = cache.get(sidebar_cache_key)

    if not sidebar_html:
        sidebar_html = render_to_string('includes/sidebar.html', {
            'categories': Category.objects.all()
        })
        cache.set(sidebar_cache_key, sidebar_html, 60 * 15)

    return render(request, 'blog/article_detail.html', {
        'article': article,
        'sidebar_html': sidebar_html,
    })
```

## Low-Level Cache API

### Basic Operations

```python
from django.core.cache import cache

# Set
cache.set('my_key', 'my_value', 60 * 15)  # 15 minutes

# Get
value = cache.get('my_key')
if value is None:
    value = expensive_operation()
    cache.set('my_key', value, 60 * 15)

# Get with default
value = cache.get('my_key', 'default_value')

# Get or set (atomic)
value = cache.get_or_set('my_key', expensive_operation, 60 * 15)

# Delete
cache.delete('my_key')

# Check existence
if 'my_key' in cache:
    print("Key exists")

# Increment/Decrement
cache.set('counter', 0)
cache.incr('counter')  # 1
cache.incr('counter', 10)  # 11
cache.decr('counter', 5)  # 6
```

### Multiple Keys

```python
# Set multiple
cache.set_many({
    'key1': 'value1',
    'key2': 'value2',
    'key3': 'value3',
}, 60 * 15)

# Get multiple
values = cache.get_many(['key1', 'key2', 'key3'])
# Returns: {'key1': 'value1', 'key2': 'value2', 'key3': 'value3'}

# Delete multiple
cache.delete_many(['key1', 'key2', 'key3'])
```

### Cache with Timeout

```python
# Set with custom timeout
cache.set('key', 'value', 60)  # 1 minute

# Never expire (requires backend support)
cache.set('key', 'value', None)

# Default timeout (from settings.py)
cache.set('key', 'value')
```

### Multiple Cache Backends

```python
from django.core.cache import caches

# Access different cache
default_cache = caches['default']
session_cache = caches['sessions']

session_cache.set('user_session', data, 60 * 60)
```

## Best Practices

### 1. Cache What's Expensive

```python
# GOOD - Cache expensive query
@cache_page(60 * 15)
def analytics_dashboard(request):
    stats = Article.objects.aggregate(
        total=Count('id'),
        views=Sum('view_count'),
        avg_rating=Avg('rating')
    )
    return render(request, 'dashboard.html', stats)

# BAD - Caching trivial view
@cache_page(60 * 15)
def hello_world(request):
    return HttpResponse("Hello!")
```

### 2. Use Appropriate Cache Duration

```python
# Static content - long cache
@cache_page(60 * 60 * 24)  # 24 hours
def about_page(request):
    return render(request, 'about.html')

# Semi-static content - medium cache
@cache_page(60 * 15)  # 15 minutes
def article_list(request):
    articles = Article.objects.filter(published=True)
    return render(request, 'blog/list.html', {'articles': articles})

# Dynamic content - short cache or no cache
@cache_page(60)  # 1 minute
def trending_articles(request):
    articles = get_trending_articles()
    return render(request, 'trending.html', {'articles': articles})

# Real-time content - no cache
@never_cache
def live_scores(request):
    scores = get_live_scores()
    return JsonResponse(scores)
```

### 3. Invalidate Proactively

```python
# When data changes, invalidate cache immediately
def create_article(request):
    if request.method == 'POST':
        form = ArticleForm(request.POST)
        if form.is_valid():
            article = form.save()

            # Invalidate list cache
            cache.delete('article_list')
            cache.delete(f'category_{article.category_id}_articles')

            return redirect('article-detail', pk=article.pk)
```

### 4. Use ETags for APIs

```python
# More efficient than full caching for APIs
@etag(lambda request, pk: f"{pk}_{Article.objects.get(pk=pk).updated_at.timestamp()}")
def article_api(request, pk):
    article = get_object_or_404(Article, pk=pk)
    return JsonResponse({
        'id': article.id,
        'title': article.title,
    })
```

### 5. Cache Keys Should Be Descriptive

```python
# GOOD - Clear what's cached
cache.set(f'article_detail_{article.slug}', data)
cache.set(f'user_{user.id}_dashboard', html)
cache.set(f'category_{category.id}_articles_page_{page}', results)

# BAD - Unclear
cache.set('ad', data)
cache.set('u1', html)
cache.set('cat_arts', results)
```

### 6. Don't Cache User-Specific Data Globally

```python
# BAD - Will serve user A's data to user B
@cache_page(60 * 15)
def dashboard(request):
    return render(request, 'dashboard.html', {
        'user': request.user  # User-specific!
    })

# GOOD - Cache per user or don't cache
@cache_page(60 * 15)
@vary_on_cookie
def dashboard(request):
    return render(request, 'dashboard.html', {
        'user': request.user
    })
```

### 7. Monitor Cache Hit Rates

```python
# Add instrumentation
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

def get_cached_data(key, fallback_func, timeout=900):
    data = cache.get(key)

    if data is not None:
        logger.info(f"Cache HIT: {key}")
        return data
    else:
        logger.info(f"Cache MISS: {key}")
        data = fallback_func()
        cache.set(key, data, timeout)
        return data
```

### 8. Use Fragment Caching for Partial Updates

```python
# Don't cache entire page if only part is expensive
def article_detail(request, slug):
    article = get_object_or_404(Article, slug=slug)

    # Cache related articles (expensive)
    related_key = f'related_articles_{article.id}'
    related = cache.get(related_key)
    if not related:
        related = Article.objects.filter(
            category=article.category
        ).exclude(id=article.id)[:5]
        cache.set(related_key, related, 60 * 15)

    # Don't cache main article (changes frequently)
    return render(request, 'blog/article_detail.html', {
        'article': article,
        'related': related,
    })
```

### 9. Be Careful with Cached QuerySets

```python
# BAD - QuerySet not fully evaluated, won't cache properly
cache.set('articles', Article.objects.all())

# GOOD - Force evaluation
cache.set('articles', list(Article.objects.all()))

# BETTER - Cache serialized data
cache.set('articles', [
    {'id': a.id, 'title': a.title}
    for a in Article.objects.all()
])
```

### 10. Test Cache Behavior

```python
# Test cache invalidation
from django.test import TestCase
from django.core.cache import cache

class ArticleCacheTest(TestCase):
    def test_cache_invalidation_on_save(self):
        article = Article.objects.create(title='Test')

        # Set cache
        cache.set(f'article_{article.id}', article)

        # Modify article
        article.title = 'Updated'
        article.save()

        # Cache should be invalidated
        self.assertIsNone(cache.get(f'article_{article.id}'))
```
