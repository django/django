# Django Caching Skill

## Overview

This skill helps you implement effective caching strategies in Django applications to improve performance and reduce database load. Caching is critical for scaling Django applications and providing fast response times.

**Use this skill when you need to:**
- Reduce database query load and speed up view responses
- Cache expensive computations or external API calls
- Optimize template rendering for high-traffic sites
- Scale your application to handle more concurrent users

## Quick Start

```python
from django.core.cache import cache

# Basic cache-aside pattern
def get_popular_posts():
    posts = cache.get('popular_posts')
    if posts is None:
        posts = list(Post.objects.filter(published=True)
                     .select_related('author')[:10])
        cache.set('popular_posts', posts, 60 * 15)  # 15 minutes
    return posts
```

## When to Use This Skill

**Use caching when:**
- [ ] Slow database queries run frequently
- [ ] Expensive computations or aggregations
- [ ] External API calls need rate limiting
- [ ] High-traffic views serve mostly static content
- [ ] Template fragments rarely change

**Avoid caching when:**
- [ ] Data changes frequently per user
- [ ] Memory constraints are critical
- [ ] Consistency is more important than speed
- [ ] Cache invalidation complexity outweighs benefits

## Core Workflows

### Workflow 1: Set Up Cache Backend

**When:** Starting a new project or migrating to production

1. **Choose backend** (see reference/backends.md):
   - Development: Local memory or dummy
   - Production: Redis (recommended) or Memcached
   - Shared hosting: Database cache

2. **Configure settings.py:**

```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'KEY_PREFIX': 'myapp',
        'TIMEOUT': 300,
    }
}
```

3. **Test connection and install dependencies:**

```bash
pip install django-redis redis
python manage.py shell -c "from django.core.cache import cache; cache.set('test', 1); print(cache.get('test'))"
```

### Workflow 2: Cache Database Queries

**When:** Expensive queries run frequently

1. **Identify slow queries:**

```bash
python scripts/cache_analyzer.py analyze --app myapp
```

2. **Implement cache-aside pattern:**

```python
from django.core.cache import cache

def get_user_dashboard_data(user_id):
    cache_key = f'dashboard:user:{user_id}'
    data = cache.get(cache_key)

    if data is None:
        data = {
            'orders_count': Order.objects.filter(user_id=user_id).count(),
            'total_spent': Order.objects.filter(user_id=user_id)
                          .aggregate(Sum('total'))['total__sum'] or 0,
        }
        cache.set(cache_key, data, 60 * 5)  # 5 minutes

    return data
```

3. **Use get_or_set() for simpler cases:**

```python
def get_categories():
    return cache.get_or_set(
        'category_tree',
        lambda: list(Category.objects.prefetch_related('children')),
        60 * 30  # 30 minutes
    )
```

4. **Cache QuerySets properly:**

```python
# WRONG - QuerySet not evaluated
cache.set('posts', Post.objects.all())  # ❌

# RIGHT - Force evaluation with list()
cache.set('posts', list(Post.objects.all()))  # ✅

# BETTER - Cache only IDs, fetch fresh objects later
cache.set('post_ids', list(Post.objects.values_list('id', flat=True)))  # ✅
```

### Workflow 3: Cache View Responses

**When:** Entire view output doesn't change often

1. **Use @cache_page for simple views:**

```python
from django.views.decorators.cache import cache_page

@cache_page(60 * 15)  # 15 minutes
def blog_index(request):
    posts = Post.objects.filter(published=True)[:20]
    return render(request, 'blog/index.html', {'posts': posts})
```

2. **Per-user caching with vary_on_cookie:**

```python
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_cookie

@cache_page(60 * 15)
@vary_on_cookie
def user_dashboard(request):
    return render(request, 'dashboard.html', {
        'data': get_user_data(request.user)
    })
```

3. **Control cache headers:**

```python
from django.views.decorators.cache import cache_control

@cache_control(private=True, max_age=3600)
def user_profile(request, username):
    user = get_object_or_404(User, username=username)
    return render(request, 'profile.html', {'profile_user': user})
```

### Workflow 4: Cache Template Fragments

**When:** Only parts of a template are expensive

```django
{% load cache %}

{# Static sidebar cached for 30 minutes #}
{% cache 1800 sidebar %}
    <div class="sidebar">
        {% for category in categories %}
            <a href="{{ category.url }}">{{ category.name }}</a>
        {% endfor %}
    </div>
{% endcache %}

{# Per-object caching with auto-invalidation #}
{% for post in posts %}
    {% cache 300 post_detail post.id post.updated_at %}
        <article>
            <h2>{{ post.title }}</h2>
            <p>{{ post.body }}</p>
        </article>
    {% endcache %}
{% endfor %}

{# Per-user fragment #}
{% cache 600 user_menu request.user.id %}
    <nav>
        <a href="{% url 'profile' %}">{{ request.user.username }}</a>
    </nav>
{% endcache %}
```

### Workflow 5: Invalidate Cache Properly

**When:** Data changes and cached values must be cleared

1. **Manual invalidation after updates:**

```python
def update_post(post_id, **kwargs):
    post = Post.objects.get(id=post_id)
    for key, value in kwargs.items():
        setattr(post, key, value)
    post.save()

    # Invalidate related caches
    cache.delete_many([
        f'post:{post_id}',
        'popular_posts',
        f'category:posts:{post.category_id}',
    ])
    return post
```

2. **Signal-based automatic invalidation:**

```python
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

@receiver([post_save, post_delete], sender=Post)
def invalidate_post_caches(sender, instance, **kwargs):
    cache.delete_many([
        f'post:{instance.id}',
        'popular_posts',
        f'category:{instance.category_id}:posts',
    ])
```

3. **Version-based invalidation:**

```python
# Increment VERSION in settings to invalidate all caches
CACHES = {
    'default': {
        'VERSION': 2,  # Increment to invalidate
    }
}

# Or per-key versioning
cache.set('my_key', value, 300, version=2)
```

4. **Pattern-based (Redis only):**

```python
from django.core.cache import cache

def invalidate_user_caches(user_id):
    if hasattr(cache, 'delete_pattern'):
        cache.delete_pattern(f'user:{user_id}:*')
```

## Cache Backend Selection Guide

| Backend | Best For | Speed | Persistence | Multi-Server |
|---------|----------|-------|-------------|--------------|
| **Redis** | Production | ★★★★★ | Yes | Yes |
| **Memcached** | High-throughput | ★★★★★ | No | Yes |
| **Database** | Shared hosting | ★★☆☆☆ | Yes | Yes |
| **File System** | Single server | ★★★☆☆ | Yes | No |
| **Local Memory** | Development | ★★★★★ | No | No |
| **Dummy** | Testing | N/A | No | N/A |

See `reference/backends.md` for detailed configurations.

## Common Patterns

### Cache-Aside (Lazy Loading)

```python
def get_product(product_id):
    cache_key = f'product:{product_id}'
    product = cache.get(cache_key)
    if product is None:
        product = Product.objects.select_related('category').get(id=product_id)
        cache.set(cache_key, product, 3600)
    return product
```

### Write-Through Cache

```python
def update_product(product_id, **kwargs):
    product = Product.objects.get(id=product_id)
    for key, value in kwargs.items():
        setattr(product, key, value)
    product.save()
    cache.set(f'product:{product_id}', product, 3600)  # Update cache immediately
    return product
```

### Computed Property Caching

```python
from django.utils.functional import cached_property

class User(models.Model):
    @cached_property
    def total_orders_value(self):
        """Cached for instance lifetime"""
        return self.orders.aggregate(Sum('total'))['total__sum'] or 0
```

### Cache Warming

```python
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    def handle(self, *args, **options):
        # Pre-populate critical caches
        cache.set('all_categories', list(Category.objects.all()), 3600)
        cache.set('popular_posts', list(Post.objects.order_by('-views')[:100]), 1800)
        self.stdout.write(self.style.SUCCESS('Cache warmed'))
```

## Anti-Patterns

### ❌ Cache Without Timeout

```python
cache.set('data', value)  # BAD - Never expires
cache.set('data', value, 3600)  # GOOD
```

### ❌ Cache User Data Without User ID

```python
@cache_page(60 * 15)  # BAD - All users get same cache
def dashboard(request):
    return render(request, 'dashboard.html', {'user': request.user})

@cache_page(60 * 15)
@vary_on_cookie  # GOOD - Separate cache per user
def dashboard(request):
    return render(request, 'dashboard.html', {'user': request.user})
```

### ❌ Cache Unevaluated QuerySets

```python
cache.set('posts', Post.objects.all())  # BAD
cache.set('posts', list(Post.objects.all()))  # GOOD
```

### ❌ Over-Cache Rapidly Changing Data

```python
# BAD - Active users change every second
cache.set('active_users', get_active_users(), 3600)

# GOOD - Short timeout for dynamic data
cache.set('active_users', get_active_users(), 60)
```

### ❌ No Fallback for Cache Failures

```python
def get_data():
    return cache.get('data')  # BAD - Returns None if cache fails

def get_data():  # GOOD - Always has fallback
    data = cache.get('data')
    if data is None:
        data = fetch_from_db()
        try:
            cache.set('data', data, 300)
        except Exception:
            pass
    return data
```

## Scripts & Tools

### cache_analyzer.py

Analyzes your code for caching opportunities and issues.

```bash
# Analyze all apps
python scripts/cache_analyzer.py analyze --verbose

# Analyze specific app
python scripts/cache_analyzer.py analyze --app myapp

# Check invalidation issues
python scripts/cache_analyzer.py check-invalidation

# Generate JSON report
python scripts/cache_analyzer.py report --output report.json
```

**Features:**
- Detects cacheable queries
- Finds views without caching
- Identifies invalidation issues
- Reports optimization opportunities

## Reference Documentation

- **reference/backends.md** - Cache backend configurations (Redis, Memcached, Database, etc.)
- **reference/low_level_api.md** - Low-level cache API (get, set, delete, incr, etc.)
- **reference/view_caching.md** - View-level caching (@cache_page, middleware, decorators)
- **reference/template_caching.md** - Template fragment caching ({% cache %} tag)
- **reference/invalidation.md** - Cache invalidation strategies and patterns
- **reference/patterns.md** - Advanced patterns (cache-aside, write-through, rate limiting)

## Edge Cases & Gotchas

### Serialization Issues

```python
# Works with most backends
cache.set('data', {'key': 'value', 'number': 123})

# May fail
cache.set('function', lambda x: x + 1)  # ❌ Functions not serializable
```

### Cache Key Collisions

```python
# BAD - Keys might collide across models
cache.set(f'data:{id}', value)

# GOOD - Include model/type in key
cache.set(f'post:{post.id}', value)
cache.set(f'user:{user.id}', value)
```

### Multi-Database Scenarios

```python
# Specify which database for database cache
from django.core.cache import caches
cache = caches['database_alias']
```

## Related Skills

- **django-models** - Understanding QuerySet optimization before caching
- **django-views** - View-level caching strategies
- **django-templates** - Template fragment caching
- **django-signals** - Signal-based cache invalidation

## Django Version Notes

- **Django 4.0+**: Built-in Redis backend (`django.core.cache.backends.redis.RedisCache`)
- **Django 3.2+**: Async cache operations (`cache.aget()`, `cache.aset()`)
- **Django 3.1+**: `cache.touch()` to update expiration
- **Django 2.1+**: `cache.get_or_set()` helper method

## Troubleshooting

**Cache Not Working:**
```python
cache.set('test', 'value', 30)
if cache.get('test') != 'value':
    # Check CACHES in settings.py, verify Redis/Memcached running
```

**Memory Issues:**
```bash
redis-cli info memory  # Monitor usage
# In redis.conf: maxmemory 256mb, maxmemory-policy allkeys-lru
```

**Stale Data:**
```python
cache.clear()  # Force clear for debugging
cache.delete_pattern('myapp:*')  # Redis pattern delete
```

**Performance Not Improving:**
```python
# Add logging to verify cache hits/misses
logger.info("Cache miss" if cache.get('key') is None else "Cache hit")
# Check Redis hit ratio: redis-cli info stats | grep keyspace
# Profile: python scripts/cache_analyzer.py analyze --verbose
```

## Examples

Comprehensive examples available in `reference/patterns.md`:
- E-commerce product caching
- Social media feed caching
- API response caching
- Search result caching
- Rate limiting with cache
- Session data caching
