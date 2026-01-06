# Low-Level Cache API Reference

This document covers Django's low-level cache API for direct cache manipulation.

## Table of Contents

- [Basic Operations](#basic-operations)
- [Advanced Operations](#advanced-operations)
- [Atomic Operations](#atomic-operations)
- [Bulk Operations](#bulk-operations)
- [Timeouts and Expiration](#timeouts-and-expiration)
- [Versioning](#versioning)
- [Async Cache Operations](#async-cache-operations)
- [Cache Key Functions](#cache-key-functions)

## Basic Operations

### cache.set()

Set a value in the cache.

```python
from django.core.cache import cache

# Basic usage
cache.set('my_key', 'my_value', timeout=300)  # 5 minutes

# No timeout (uses CACHES['default']['TIMEOUT'])
cache.set('my_key', 'my_value')

# Never expire (None or 0)
cache.set('my_key', 'my_value', timeout=None)

# Complex values
cache.set('user_data', {
    'id': 123,
    'name': 'John',
    'orders': [1, 2, 3]
}, timeout=3600)
```

### cache.get()

Retrieve a value from the cache.

```python
# Basic usage
value = cache.get('my_key')

# With default value
value = cache.get('my_key', default='default_value')

# Returns None if key doesn't exist
value = cache.get('nonexistent_key')  # None

# With version
value = cache.get('my_key', version=2)
```

### cache.delete()

Delete a key from the cache.

```python
# Delete single key
cache.delete('my_key')

# Returns None regardless of whether key existed
cache.delete('nonexistent_key')

# Delete with version
cache.delete('my_key', version=2)
```

### cache.clear()

Clear all keys from the cache.

```python
# WARNING: This clears ALL cache entries
cache.clear()

# Use with caution in production!
```

## Advanced Operations

### cache.add()

Set a value only if the key doesn't already exist.

```python
# Returns True if key was added
success = cache.add('my_key', 'my_value', timeout=300)

if success:
    print("Key was added")
else:
    print("Key already exists")

# Useful for race conditions
def get_or_create_cache():
    data = cache.get('data')
    if data is None:
        # Try to add lock
        if cache.add('data_lock', 'locked', timeout=60):
            try:
                data = expensive_operation()
                cache.set('data', data, 300)
            finally:
                cache.delete('data_lock')
        else:
            # Another process is computing, wait and retry
            time.sleep(0.1)
            return get_or_create_cache()
    return data
```

### cache.get_or_set()

Get a value, or set it if it doesn't exist.

```python
# Basic usage
value = cache.get_or_set('my_key', 'default_value', timeout=300)

# With callable default
def compute_value():
    return expensive_operation()

value = cache.get_or_set('my_key', compute_value, timeout=300)

# Callable is only executed if cache miss
value = cache.get_or_set(
    'user_stats',
    lambda: User.objects.aggregate(
        total=Count('id'),
        active=Count('id', filter=Q(is_active=True))
    ),
    timeout=3600
)
```

### cache.touch()

Update the timeout on a key without changing its value.

```python
# Extend expiration by 300 seconds from now
cache.touch('my_key', timeout=300)

# Returns True if key exists and was updated
success = cache.touch('my_key', 300)

if not success:
    print("Key doesn't exist")

# Useful for extending session-like data
def refresh_user_cache(user_id):
    key = f'user:{user_id}'
    if cache.touch(key, 3600):
        print(f"Extended cache for user {user_id}")
    else:
        # Cache expired, need to recreate
        user_data = fetch_user_data(user_id)
        cache.set(key, user_data, 3600)
```

## Atomic Operations

### cache.incr()

Atomically increment a numeric value.

```python
# Initialize counter
cache.set('page_views', 0)

# Increment by 1
cache.incr('page_views')  # Returns 1
cache.incr('page_views')  # Returns 2

# Increment by specific amount
cache.incr('page_views', delta=5)  # Returns 7

# Thread-safe counting
def track_view(page_id):
    key = f'views:{page_id}'
    try:
        return cache.incr(key)
    except ValueError:
        # Key doesn't exist, initialize it
        cache.set(key, 1, timeout=86400)
        return 1
```

### cache.decr()

Atomically decrement a numeric value.

```python
# Initialize counter
cache.set('items_remaining', 100)

# Decrement by 1
cache.decr('items_remaining')  # Returns 99

# Decrement by specific amount
cache.decr('items_remaining', delta=10)  # Returns 89

# Rate limiting example
def check_rate_limit(user_id, limit=100):
    key = f'rate_limit:{user_id}'
    remaining = cache.get(key)

    if remaining is None:
        # First request, set limit
        cache.set(key, limit - 1, timeout=3600)
        return True

    if remaining > 0:
        cache.decr(key)
        return True
    else:
        return False
```

**Note:** `incr()` and `decr()` raise `ValueError` if the key doesn't exist or isn't an integer.

## Bulk Operations

### cache.get_many()

Get multiple cache keys at once (more efficient than multiple `get()` calls).

```python
# Get multiple keys
keys = ['key1', 'key2', 'key3']
result = cache.get_many(keys)

# Returns dict: {'key1': value1, 'key2': value2}
# Missing keys are not included in result

# Example: Fetch multiple user profiles
user_ids = [1, 2, 3, 4, 5]
cache_keys = [f'user:{uid}' for uid in user_ids]
cached_users = cache.get_many(cache_keys)

# Find which users need to be fetched from DB
missing_keys = set(cache_keys) - set(cached_users.keys())
missing_ids = [int(key.split(':')[1]) for key in missing_keys]

if missing_ids:
    users = User.objects.filter(id__in=missing_ids)
    # Cache the missing users
    for user in users:
        cache.set(f'user:{user.id}', user, 3600)
```

### cache.set_many()

Set multiple cache keys at once.

```python
# Set multiple keys
cache.set_many({
    'key1': 'value1',
    'key2': 'value2',
    'key3': 'value3',
}, timeout=300)

# Returns list of keys that failed to be inserted
failed = cache.set_many(data, 300)

# Example: Cache multiple products
products = Product.objects.all()
cache_data = {
    f'product:{p.id}': p
    for p in products
}
cache.set_many(cache_data, timeout=3600)
```

### cache.delete_many()

Delete multiple cache keys at once.

```python
# Delete multiple keys
cache.delete_many(['key1', 'key2', 'key3'])

# Example: Clear user-related caches
def clear_user_caches(user_id):
    keys_to_delete = [
        f'user:{user_id}',
        f'user:{user_id}:profile',
        f'user:{user_id}:settings',
        f'user:{user_id}:orders',
    ]
    cache.delete_many(keys_to_delete)
```

## Timeouts and Expiration

### Timeout Values

```python
# Specific timeout (seconds)
cache.set('key', 'value', timeout=300)  # 5 minutes

# Default timeout (from settings)
cache.set('key', 'value')

# Never expire
cache.set('key', 'value', timeout=None)

# Expire immediately (effectively same as not caching)
cache.set('key', 'value', timeout=0)

# Using timedelta
from datetime import timedelta
cache.set('key', 'value', timeout=timedelta(hours=1).total_seconds())
```

### Dynamic Timeouts

```python
def get_cache_timeout(obj):
    """Return cache timeout based on object properties"""
    if obj.priority == 'high':
        return 60  # 1 minute for high priority
    elif obj.priority == 'medium':
        return 300  # 5 minutes
    else:
        return 3600  # 1 hour for low priority

cache.set(f'object:{obj.id}', obj, timeout=get_cache_timeout(obj))
```

### Time-Based Cache Keys

```python
from datetime import datetime

def get_hourly_cache_key(base_key):
    """Cache key that changes every hour"""
    hour = datetime.now().strftime('%Y%m%d%H')
    return f'{base_key}:{hour}'

# Cache refreshes automatically every hour
stats = cache.get_or_set(
    get_hourly_cache_key('stats'),
    compute_stats,
    timeout=3600
)
```

## Versioning

### Basic Versioning

```python
# Set with version
cache.set('my_key', 'value1', version=1)
cache.set('my_key', 'value2', version=2)

# Get with version
value1 = cache.get('my_key', version=1)  # 'value1'
value2 = cache.get('my_key', version=2)  # 'value2'

# Delete specific version
cache.delete('my_key', version=1)
```

### Global Version from Settings

```python
# settings.py
CACHES = {
    'default': {
        'BACKEND': '...',
        'VERSION': 2,  # Increment to invalidate all caches
    }
}

# All cache operations now use version 2
cache.set('key', 'value')  # Uses version 2
cache.get('key')  # Gets version 2
```

### Versioning for Cache Invalidation

```python
class Product(models.Model):
    # ... fields
    cache_version = models.IntegerField(default=1)

    def get_cache_key(self):
        return f'product:{self.id}'

    def get_cached_data(self):
        return cache.get_or_set(
            self.get_cache_key(),
            lambda: self.compute_expensive_data(),
            timeout=3600,
            version=self.cache_version
        )

    def invalidate_cache(self):
        # Increment version to invalidate cache
        self.cache_version += 1
        self.save(update_fields=['cache_version'])
```

## Async Cache Operations

### Available in Django 3.2+

```python
import asyncio
from django.core.cache import cache

async def async_cache_operations():
    # Async set
    await cache.aset('key', 'value', timeout=300)

    # Async get
    value = await cache.aget('key')

    # Async delete
    await cache.adelete('key')

    # Async add
    success = await cache.aadd('key', 'value')

    # Async get_or_set
    value = await cache.aget_or_set('key', 'default', timeout=300)

    # Async touch
    success = await cache.atouch('key', timeout=300)

    # Async clear
    await cache.aclear()

    # Async bulk operations
    await cache.aset_many({'key1': 'val1', 'key2': 'val2'})
    values = await cache.aget_many(['key1', 'key2'])
    await cache.adelete_many(['key1', 'key2'])

    # Async atomic operations
    await cache.aincr('counter')
    await cache.adecr('counter')
```

### Async View Example

```python
from django.views import View
from django.http import JsonResponse
from asgiref.sync import sync_to_async
from django.core.cache import cache

class AsyncCacheView(View):
    async def get(self, request):
        # Async cache operations
        stats = await cache.aget('site_stats')

        if stats is None:
            # Fetch from database asynchronously
            stats = await sync_to_async(self.compute_stats)()
            await cache.aset('site_stats', stats, 300)

        return JsonResponse(stats)

    def compute_stats(self):
        # Your expensive computation
        return {'users': 1000, 'posts': 5000}
```

## Cache Key Functions

### Default Key Function

Django generates cache keys like: `prefix:version:key`

```python
# With these settings:
# KEY_PREFIX = 'myapp'
# VERSION = 1

cache.set('user', data)
# Actual key: 'myapp:1:user'
```

### Custom Key Function

```python
# utils/cache.py
def make_cache_key(key, key_prefix, version):
    """Custom cache key function"""
    # Add timestamp for time-based invalidation
    from datetime import datetime
    hour = datetime.now().strftime('%Y%m%d%H')
    return f'{key_prefix}:{version}:{hour}:{key}'.lower()

# settings.py
CACHES = {
    'default': {
        'BACKEND': '...',
        'KEY_FUNCTION': 'utils.cache.make_cache_key',
    }
}
```

### Key Validation

```python
import re

def validate_cache_key(key):
    """Ensure cache key is valid"""
    # Most backends have restrictions:
    # - No spaces
    # - No control characters
    # - Limited length (250 chars for Memcached)

    if len(key) > 250:
        raise ValueError(f"Cache key too long: {len(key)} chars")

    if not re.match(r'^[\w\-\.]+$', key):
        raise ValueError(f"Invalid cache key: {key}")

    return key

# Use in your code
key = validate_cache_key(f'user:{user_id}')
cache.set(key, data)
```

### Key Hashing for Long Keys

```python
import hashlib

def make_hashed_key(key_parts):
    """Create a hashed key for long or complex keys"""
    key_string = ':'.join(str(part) for part in key_parts)

    if len(key_string) > 200:
        # Hash long keys
        hash_value = hashlib.md5(key_string.encode()).hexdigest()
        return f'hashed:{hash_value}'

    return key_string

# Usage
key = make_hashed_key(['user', user_id, 'orders', year, month])
cache.set(key, data)
```

## Error Handling

### Graceful Degradation

```python
def safe_cache_get(key, fallback_func):
    """Get from cache with fallback"""
    try:
        value = cache.get(key)
        if value is None:
            value = fallback_func()
            try:
                cache.set(key, value, 300)
            except Exception as e:
                # Log but don't fail
                logger.error(f"Cache set failed: {e}")
        return value
    except Exception as e:
        logger.error(f"Cache get failed: {e}")
        return fallback_func()
```

### Connection Error Handling

```python
from django.core.cache import cache
from django.core.cache.backends.base import InvalidCacheBackendError

def cached_operation(key, operation):
    """Cache operation with error handling"""
    try:
        # Try to get from cache
        result = cache.get(key)
        if result is not None:
            return result

        # Cache miss, perform operation
        result = operation()

        # Try to cache result
        try:
            cache.set(key, result, 300)
        except Exception as cache_error:
            # Log cache error but return result
            logger.warning(f"Failed to cache result: {cache_error}")

        return result

    except Exception as e:
        # If cache is completely broken, just perform operation
        logger.error(f"Cache completely unavailable: {e}")
        return operation()
```

## Performance Tips

### Minimize Serialization Overhead

```python
# BAD - Large objects are slow to serialize
cache.set('user', user_object)  # Serializes entire model instance

# GOOD - Cache only what you need
cache.set('user_data', {
    'id': user.id,
    'name': user.name,
    'email': user.email,
})

# BETTER - Cache IDs and fetch from DB with select_related
cache.set('popular_post_ids', list(
    Post.objects.filter(views__gt=1000).values_list('id', flat=True)
))
```

### Batch Operations

```python
# BAD - Multiple round trips
for user_id in user_ids:
    user = cache.get(f'user:{user_id}')
    if user is None:
        user = User.objects.get(id=user_id)
        cache.set(f'user:{user_id}', user)

# GOOD - Single round trip
cache_keys = [f'user:{uid}' for uid in user_ids]
cached = cache.get_many(cache_keys)

missing_ids = [
    uid for uid in user_ids
    if f'user:{uid}' not in cached
]

if missing_ids:
    users = User.objects.filter(id__in=missing_ids)
    cache.set_many({
        f'user:{u.id}': u for u in users
    }, 3600)
```

### Use Appropriate Timeouts

```python
# Different data has different freshness requirements

# Very dynamic data - short timeout
cache.set('active_users_count', count, 60)  # 1 minute

# Semi-static data - medium timeout
cache.set('popular_posts', posts, 300)  # 5 minutes

# Static data - long timeout
cache.set('site_config', config, 3600)  # 1 hour

# Reference data - very long timeout
cache.set('countries_list', countries, 86400)  # 24 hours
```

## Complete Example

```python
from django.core.cache import cache
from django.db.models import Sum, Count
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class UserStatsCache:
    """Encapsulate user statistics caching"""

    TIMEOUT = 300  # 5 minutes

    @staticmethod
    def _get_cache_key(user_id: int) -> str:
        return f'user_stats:{user_id}'

    @classmethod
    def get(cls, user_id: int) -> Dict[str, Any]:
        """Get user stats from cache or database"""
        cache_key = cls._get_cache_key(user_id)

        try:
            stats = cache.get(cache_key)
            if stats is not None:
                logger.debug(f"Cache hit for user {user_id}")
                return stats
        except Exception as e:
            logger.error(f"Cache get failed: {e}")

        # Cache miss, compute stats
        logger.debug(f"Cache miss for user {user_id}")
        stats = cls._compute_stats(user_id)

        # Try to cache
        try:
            cache.set(cache_key, stats, cls.TIMEOUT)
        except Exception as e:
            logger.error(f"Cache set failed: {e}")

        return stats

    @staticmethod
    def _compute_stats(user_id: int) -> Dict[str, Any]:
        """Compute user statistics from database"""
        from .models import Order

        stats = Order.objects.filter(user_id=user_id).aggregate(
            total_orders=Count('id'),
            total_spent=Sum('total'),
        )

        return {
            'total_orders': stats['total_orders'] or 0,
            'total_spent': float(stats['total_spent'] or 0),
        }

    @classmethod
    def invalidate(cls, user_id: int):
        """Invalidate cache for a user"""
        cache_key = cls._get_cache_key(user_id)
        try:
            cache.delete(cache_key)
            logger.debug(f"Invalidated cache for user {user_id}")
        except Exception as e:
            logger.error(f"Cache delete failed: {e}")

    @classmethod
    def refresh(cls, user_id: int) -> Dict[str, Any]:
        """Force refresh of user stats"""
        cls.invalidate(user_id)
        return cls.get(user_id)
```
