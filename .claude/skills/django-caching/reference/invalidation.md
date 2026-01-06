# Cache Invalidation Reference

This document covers cache invalidation strategies and patterns in Django.

> "There are only two hard things in Computer Science: cache invalidation and naming things." - Phil Karlton

## Table of Contents

- [Manual Invalidation](#manual-invalidation)
- [Signal-Based Invalidation](#signal-based-invalidation)
- [Time-Based Invalidation](#time-based-invalidation)
- [Version-Based Invalidation](#version-based-invalidation)
- [Pattern-Based Invalidation](#pattern-based-invalidation)
- [Invalidation Strategies](#invalidation-strategies)
- [Testing Cache Invalidation](#testing-cache-invalidation)

## Manual Invalidation

### Basic Delete

```python
from django.core.cache import cache

# Delete single key
cache.delete('my_key')

# Delete multiple keys
cache.delete_many(['key1', 'key2', 'key3'])

# Clear entire cache (use with caution!)
cache.clear()
```

### Invalidation After Updates

```python
from django.core.cache import cache

def update_article(article_id, **kwargs):
    """Update article and invalidate related caches"""
    article = Article.objects.get(id=article_id)

    # Update article
    for key, value in kwargs.items():
        setattr(article, key, value)
    article.save()

    # Invalidate caches
    cache.delete(f'article:{article_id}')
    cache.delete(f'article:detail:{article_id}')
    cache.delete('article:list')
    cache.delete(f'category:articles:{article.category_id}')

    return article
```

### Invalidation in Model Methods

```python
from django.db import models
from django.core.cache import cache

class Article(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    category = models.ForeignKey('Category', on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Invalidate caches after save
        self.invalidate_cache()

    def delete(self, *args, **kwargs):
        # Store values before deletion
        article_id = self.id
        category_id = self.category_id

        super().delete(*args, **kwargs)

        # Invalidate caches after delete
        cache.delete(f'article:{article_id}')
        cache.delete('article:list')
        cache.delete(f'category:articles:{category_id}')

    def invalidate_cache(self):
        """Invalidate all caches related to this article"""
        cache.delete_many([
            f'article:{self.id}',
            f'article:detail:{self.id}',
            'article:list',
            f'category:articles:{self.category_id}',
            'popular_articles',
        ])
```

### Template Fragment Invalidation

```python
from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key

# Invalidate specific template fragment
key = make_template_fragment_key('sidebar')
cache.delete(key)

# With variables
key = make_template_fragment_key('article', [article.id])
cache.delete(key)

# With multiple variables
key = make_template_fragment_key('post_detail', [post.id, post.updated_at])
cache.delete(key)

# Helper function
def invalidate_template_fragment(fragment_name, *args):
    """Helper to invalidate template fragments"""
    key = make_template_fragment_key(fragment_name, args)
    cache.delete(key)
    return key

# Usage
invalidate_template_fragment('article', article.id)
invalidate_template_fragment('user_profile', user.id, user.updated_at)
```

## Signal-Based Invalidation

### Basic Signal Handler

```python
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache

@receiver(post_save, sender=Article)
def invalidate_article_cache_on_save(sender, instance, created, **kwargs):
    """Invalidate article caches when article is saved"""
    cache.delete(f'article:{instance.id}')
    cache.delete('article:list')

    if created:
        # New article, invalidate category cache
        cache.delete(f'category:articles:{instance.category_id}')

@receiver(post_delete, sender=Article)
def invalidate_article_cache_on_delete(sender, instance, **kwargs):
    """Invalidate article caches when article is deleted"""
    cache.delete(f'article:{instance.id}')
    cache.delete('article:list')
    cache.delete(f'category:articles:{instance.category_id}')
```

### Combined Signal Handler

```python
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache

@receiver([post_save, post_delete], sender=Article)
def invalidate_article_caches(sender, instance, **kwargs):
    """Invalidate article-related caches on any change"""
    keys_to_delete = [
        f'article:{instance.id}',
        f'article:detail:{instance.id}',
        'article:list',
        'popular_articles',
        f'category:{instance.category_id}:articles',
    ]

    # Add author-related caches
    if hasattr(instance, 'author_id'):
        keys_to_delete.append(f'author:{instance.author_id}:articles')

    cache.delete_many(keys_to_delete)
```

### Signal Handler with Related Objects

```python
from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver

@receiver(post_save, sender=Article)
def invalidate_on_article_save(sender, instance, **kwargs):
    cache.delete(f'article:{instance.id}')
    cache.delete(f'category:{instance.category_id}:count')

@receiver(m2m_changed, sender=Article.tags.through)
def invalidate_on_tags_change(sender, instance, action, **kwargs):
    """Invalidate when article tags change"""
    if action in ['post_add', 'post_remove', 'post_clear']:
        cache.delete(f'article:{instance.id}')
        cache.delete('popular_tags')

        # Invalidate tag-specific caches
        if action in ['post_add', 'post_remove']:
            pk_set = kwargs.get('pk_set', set())
            for tag_id in pk_set:
                cache.delete(f'tag:{tag_id}:articles')
```

### Conditional Invalidation

```python
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Article)
def conditional_cache_invalidation(sender, instance, created, **kwargs):
    """Only invalidate if certain fields changed"""
    if created:
        # New article, invalidate list caches
        cache.delete('article:list')
        cache.delete('recent_articles')
    else:
        # Check if important fields changed
        if instance.tracker.has_changed('published'):
            # Published status changed
            cache.delete('article:list')
            cache.delete('published_articles')

        if instance.tracker.has_changed('title') or instance.tracker.has_changed('content'):
            # Content changed, invalidate detail cache
            cache.delete(f'article:{instance.id}')
```

**Note:** Using `django-model-utils` FieldTracker for change detection:

```python
from model_utils import FieldTracker

class Article(models.Model):
    title = models.CharField(max_length=200)
    published = models.BooleanField(default=False)

    tracker = FieldTracker()
```

## Time-Based Invalidation

### Fixed Time Intervals

```python
from django.core.cache import cache

# Cache expires after fixed time
cache.set('data', value, timeout=300)  # 5 minutes

# Different timeouts for different data types
CACHE_TIMEOUTS = {
    'static': 86400,      # 24 hours
    'dynamic': 300,       # 5 minutes
    'real_time': 60,      # 1 minute
}

cache.set('static_data', data, CACHE_TIMEOUTS['static'])
cache.set('user_data', data, CACHE_TIMEOUTS['dynamic'])
```

### Time-Based Cache Keys

```python
from datetime import datetime
from django.core.cache import cache

def get_hourly_stats():
    """Cache key changes every hour, automatic invalidation"""
    hour = datetime.now().strftime('%Y%m%d%H')
    cache_key = f'stats:hourly:{hour}'

    return cache.get_or_set(
        cache_key,
        lambda: compute_hourly_stats(),
        timeout=3600  # 1 hour
    )

def get_daily_report():
    """Cache key changes every day"""
    date = datetime.now().strftime('%Y%m%d')
    cache_key = f'report:daily:{date}'

    return cache.get_or_set(
        cache_key,
        lambda: generate_daily_report(),
        timeout=86400  # 24 hours
    )
```

### Scheduled Invalidation

```python
# Using Celery for scheduled cache invalidation
from celery import shared_task
from django.core.cache import cache

@shared_task
def invalidate_stale_caches():
    """Run every hour to clear specific caches"""
    cache.delete_many([
        'dashboard:stats',
        'popular_posts',
        'trending_topics',
    ])

# celerybeat_schedule
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'invalidate-caches': {
        'task': 'myapp.tasks.invalidate_stale_caches',
        'schedule': crontab(minute=0, hour='*'),  # Every hour
    },
}
```

## Version-Based Invalidation

### Global Cache Version

```python
# settings.py
CACHES = {
    'default': {
        'BACKEND': '...',
        'VERSION': 2,  # Increment to invalidate all caches
    }
}

# All cache operations now use version 2
from django.core.cache import cache
cache.set('key', 'value')  # Uses version 2
```

### Per-Model Version

```python
from django.db import models
from django.core.cache import cache

class Article(models.Model):
    title = models.CharField(max_length=200)
    cache_version = models.IntegerField(default=1)

    def get_cached_data(self):
        cache_key = f'article:{self.id}'
        return cache.get_or_set(
            cache_key,
            lambda: self.compute_expensive_data(),
            timeout=3600,
            version=self.cache_version
        )

    def invalidate_cache(self):
        """Increment version instead of deleting"""
        self.cache_version += 1
        self.save(update_fields=['cache_version'])
```

### Application-Level Versioning

```python
# settings.py
CACHE_VERSION = '1.0.0'

# In code
from django.conf import settings
from django.core.cache import cache
import hashlib

def versioned_cache_key(key):
    """Generate versioned cache key"""
    version_hash = hashlib.md5(
        settings.CACHE_VERSION.encode()
    ).hexdigest()[:8]
    return f'{key}:v{version_hash}'

# Usage
cache_key = versioned_cache_key('my_data')
cache.set(cache_key, data, 3600)
```

## Pattern-Based Invalidation

### Redis Pattern Deletion

```python
from django.core.cache import cache

# Requires django-redis backend
def invalidate_user_caches(user_id):
    """Delete all caches for a user"""
    if hasattr(cache, 'delete_pattern'):
        # Redis backend supports pattern deletion
        cache.delete_pattern(f'user:{user_id}:*')
    else:
        # Fallback for other backends
        known_keys = [
            f'user:{user_id}:profile',
            f'user:{user_id}:orders',
            f'user:{user_id}:settings',
        ]
        cache.delete_many(known_keys)

def invalidate_category_caches(category_id):
    """Delete all caches for a category"""
    if hasattr(cache, 'delete_pattern'):
        cache.delete_pattern(f'category:{category_id}:*')
        cache.delete_pattern(f'*:category:{category_id}:*')
```

### Manual Pattern Tracking

```python
from django.core.cache import cache
import json

class CacheKeyTracker:
    """Track cache keys for pattern-based invalidation"""

    TRACKER_KEY = 'cache_key_tracker'

    @classmethod
    def register_key(cls, pattern, key):
        """Register a cache key under a pattern"""
        tracker = cache.get(cls.TRACKER_KEY) or {}
        if pattern not in tracker:
            tracker[pattern] = []
        if key not in tracker[pattern]:
            tracker[pattern].append(key)
        cache.set(cls.TRACKER_KEY, tracker, timeout=None)

    @classmethod
    def invalidate_pattern(cls, pattern):
        """Invalidate all keys matching pattern"""
        tracker = cache.get(cls.TRACKER_KEY) or {}
        keys = tracker.get(pattern, [])
        if keys:
            cache.delete_many(keys)
            # Remove pattern from tracker
            del tracker[pattern]
            cache.set(cls.TRACKER_KEY, tracker, timeout=None)

# Usage
cache_key = f'user:{user_id}:profile'
cache.set(cache_key, data, 3600)
CacheKeyTracker.register_key(f'user:{user_id}', cache_key)

# Later, invalidate all user caches
CacheKeyTracker.invalidate_pattern(f'user:{user_id}')
```

## Invalidation Strategies

### Write-Through Strategy

Update cache immediately when data changes.

```python
def update_product(product_id, **kwargs):
    """Update product and cache simultaneously"""
    product = Product.objects.get(id=product_id)

    # Update database
    for key, value in kwargs.items():
        setattr(product, key, value)
    product.save()

    # Update cache immediately
    cache.set(f'product:{product_id}', product, 3600)

    return product
```

### Write-Behind (Write-Back) Strategy

Update database but invalidate cache (refill on next read).

```python
def update_product(product_id, **kwargs):
    """Update product and invalidate cache"""
    product = Product.objects.get(id=product_id)

    # Update database
    for key, value in kwargs.items():
        setattr(product, key, value)
    product.save()

    # Invalidate cache (will be refilled on next read)
    cache.delete(f'product:{product_id}')

    return product
```

### Lazy Invalidation with Timestamps

```python
from django.db import models
from django.core.cache import cache
from django.utils import timezone

class Article(models.Model):
    title = models.CharField(max_length=200)
    updated_at = models.DateTimeField(auto_now=True)

    def get_cached_data(self):
        cache_key = f'article:{self.id}'
        cached = cache.get(cache_key)

        if cached:
            # Check if cache is stale
            cached_time = cached.get('cached_at')
            if cached_time and cached_time >= self.updated_at:
                return cached['data']

        # Cache miss or stale, fetch fresh data
        data = self.compute_expensive_data()

        cache.set(cache_key, {
            'data': data,
            'cached_at': timezone.now()
        }, 3600)

        return data
```

### Probabilistic Early Expiration

Prevents cache stampede by refreshing before expiration.

```python
import random
from django.core.cache import cache
from django.utils import timezone

def get_cached_with_early_refresh(key, compute_func, timeout=300):
    """
    Cache with probabilistic early refresh to prevent stampede.

    XFetch algorithm: refresh early based on time since cached.
    """
    cached = cache.get(key)

    if cached:
        data, cached_at, cache_timeout = cached

        # Calculate time elapsed
        elapsed = (timezone.now() - cached_at).total_seconds()

        # Probability of early refresh increases as expiration approaches
        # delta * beta * log(random) formula
        delta = timeout - elapsed
        beta = 1.0  # Tuning parameter

        if delta > 0:
            early_refresh_threshold = delta * beta * abs(random.gauss(0, 1))
            if elapsed < early_refresh_threshold:
                return data

    # Cache miss or early refresh triggered
    data = compute_func()
    cache.set(key, (data, timezone.now(), timeout), timeout)

    return data
```

## Testing Cache Invalidation

### Unit Test for Invalidation

```python
from django.test import TestCase
from django.core.cache import cache

class CacheInvalidationTest(TestCase):
    def setUp(self):
        cache.clear()

    def test_article_save_invalidates_cache(self):
        """Test that saving article invalidates its cache"""
        article = Article.objects.create(title='Test')

        # Cache the article
        cache_key = f'article:{article.id}'
        cache.set(cache_key, article, 300)

        # Verify cached
        self.assertEqual(cache.get(cache_key), article)

        # Update article
        article.title = 'Updated'
        article.save()

        # Cache should be invalidated
        self.assertIsNone(cache.get(cache_key))

    def test_article_delete_invalidates_list(self):
        """Test that deleting article invalidates list cache"""
        article = Article.objects.create(title='Test')

        # Cache article list
        cache.set('article:list', [article], 300)

        # Delete article
        article.delete()

        # List cache should be invalidated
        self.assertIsNone(cache.get('article:list'))
```

### Integration Test with Signals

```python
from django.test import TestCase
from django.core.cache import cache
from django.db.models import signals

class SignalInvalidationTest(TestCase):
    def test_signal_handler_invalidates_cache(self):
        """Test signal handler properly invalidates cache"""
        # Create and cache article
        article = Article.objects.create(title='Test')
        cache_key = f'article:{article.id}'
        cache.set(cache_key, 'cached_data', 300)

        # Trigger signal by updating
        article.title = 'Updated'
        article.save()

        # Cache should be invalidated by signal handler
        self.assertIsNone(cache.get(cache_key))

    def test_signal_disconnection(self):
        """Test behavior when signal handler is disconnected"""
        # Disconnect signal
        signals.post_save.disconnect(
            sender=Article,
            dispatch_uid='invalidate_article_cache'
        )

        try:
            article = Article.objects.create(title='Test')
            cache_key = f'article:{article.id}'
            cache.set(cache_key, 'cached_data', 300)

            article.title = 'Updated'
            article.save()

            # Cache should NOT be invalidated
            self.assertEqual(cache.get(cache_key), 'cached_data')

        finally:
            # Reconnect signal
            signals.post_save.connect(
                invalidate_article_cache,
                sender=Article,
                dispatch_uid='invalidate_article_cache'
            )
```

### Mock Cache for Testing

```python
from unittest.mock import patch
from django.test import TestCase

class CacheInvalidationMockTest(TestCase):
    @patch('django.core.cache.cache.delete')
    def test_invalidation_called(self, mock_delete):
        """Test that cache.delete is called with correct keys"""
        article = Article.objects.create(title='Test')

        article.invalidate_cache()

        # Verify delete was called with expected keys
        expected_keys = [
            f'article:{article.id}',
            f'article:detail:{article.id}',
            'article:list',
        ]

        mock_delete.assert_called()
        # Check all expected keys were deleted
        for key in expected_keys:
            self.assertIn(
                key,
                [call[0][0] for call in mock_delete.call_args_list]
            )
```

## Best Practices

### 1. Always Have a Fallback

```python
def get_data(key):
    """Always handle cache failures gracefully"""
    try:
        data = cache.get(key)
        if data is None:
            data = fetch_from_db()
            try:
                cache.set(key, data, 300)
            except Exception:
                pass  # Log but don't fail
        return data
    except Exception:
        return fetch_from_db()
```

### 2. Batch Invalidations

```python
# BAD: Multiple cache operations
def update_articles(article_ids):
    for article_id in article_ids:
        cache.delete(f'article:{article_id}')

# GOOD: Single batch operation
def update_articles(article_ids):
    keys = [f'article:{aid}' for aid in article_ids]
    cache.delete_many(keys)
```

### 3. Log Invalidations

```python
import logging
from django.core.cache import cache

logger = logging.getLogger(__name__)

def invalidate_with_logging(keys):
    """Invalidate cache with logging"""
    if isinstance(keys, str):
        keys = [keys]

    logger.info(f"Invalidating {len(keys)} cache keys: {keys}")

    try:
        cache.delete_many(keys)
        logger.info("Cache invalidation successful")
    except Exception as e:
        logger.error(f"Cache invalidation failed: {e}")
        raise
```

### 4. Document Cache Dependencies

```python
class Article(models.Model):
    """
    Article model with caching.

    Cache keys used:
    - article:{id} - Article detail
    - article:list - All articles list
    - category:{category_id}:articles - Articles by category
    - author:{author_id}:articles - Articles by author
    - popular_articles - Top 10 popular articles

    Invalidation triggers:
    - save(): Invalidates detail and list caches
    - delete(): Invalidates all related caches
    - tags change (M2M): Invalidates detail and tag caches
    """
    title = models.CharField(max_length=200)
    # ... fields
```

### 5. Use Constants for Cache Keys

```python
# cache_keys.py
class CacheKeys:
    """Centralized cache key definitions"""
    ARTICLE_DETAIL = 'article:{id}'
    ARTICLE_LIST = 'article:list'
    CATEGORY_ARTICLES = 'category:{category_id}:articles'
    USER_PROFILE = 'user:{user_id}:profile'

    @classmethod
    def article_detail(cls, article_id):
        return cls.ARTICLE_DETAIL.format(id=article_id)

    @classmethod
    def category_articles(cls, category_id):
        return cls.CATEGORY_ARTICLES.format(category_id=category_id)

# Usage
from .cache_keys import CacheKeys

cache.delete(CacheKeys.article_detail(article.id))
cache.delete(CacheKeys.ARTICLE_LIST)
```
