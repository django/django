# Template Performance Optimization

Guide to optimizing Django template rendering performance.

## Table of Contents
- [Template Caching](#template-caching)
- [Fragment Caching](#fragment-caching)
- [Lazy Evaluation](#lazy-evaluation)
- [Query Optimization](#query-optimization)
- [Template Compilation](#template-compilation)
- [Profiling](#profiling)
- [Best Practices](#best-practices)

## Template Caching

### Enable Cached Loader

The cached loader compiles templates once and reuses them.

```python
# settings.py
TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [BASE_DIR / 'templates'],
    'OPTIONS': {
        'context_processors': [
            'django.template.context_processors.debug',
            'django.template.context_processors.request',
            'django.contrib.auth.context_processors.auth',
            'django.contrib.messages.context_processors.messages',
        ],
        'loaders': [
            ('django.template.loaders.cached.Loader', [
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
            ]),
        ],
    },
}]
```

**Production-only:**
```python
# Only use cached loader in production
if not DEBUG:
    TEMPLATES[0]['OPTIONS']['loaders'] = [
        ('django.template.loaders.cached.Loader', [
            'django.template.loaders.filesystem.Loader',
            'django.template.loaders.app_directories.Loader',
        ]),
    ]
```

### Benefits

- **First load:** Template is compiled and cached
- **Subsequent loads:** Cached compiled template is reused
- **Performance gain:** 10-50x faster for complex templates

### Limitations

- Development: Must restart server to see template changes
- Memory: Compiled templates stored in memory

## Fragment Caching

### Basic Fragment Caching

Cache expensive template blocks:

```django
{% load cache %}

{% cache 500 sidebar %}
    {# Expensive content cached for 500 seconds #}
    {% for item in expensive_queryset %}
        <div>{{ item.name }}</div>
    {% endfor %}
{% endcache %}
```

### Per-User Caching

```django
{% cache 600 sidebar request.user.id %}
    {# Cached separately for each user #}
    <div>Welcome, {{ request.user.username }}!</div>
    {% get_user_notifications as notifications %}
    <ul>
        {% for notif in notifications %}
            <li>{{ notif.message }}</li>
        {% endfor %}
    </ul>
{% endcache %}
```

### Multiple Cache Keys

```django
{% cache 600 object_detail object.id object.modified %}
    {# Cache invalidated when object.modified changes #}
    <h1>{{ object.title }}</h1>
    <p>{{ object.content }}</p>
{% endcache %}
```

### Using Cache Alias

```python
# settings.py
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
    },
    'templates': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/2',
        'TIMEOUT': 3600,
    },
}
```

```django
{% cache 600 sidebar using="templates" %}
    {# Uses 'templates' cache alias #}
{% endcache %}
```

### Fragment Caching Patterns

**Sidebar with recent posts:**
```django
{% cache 300 recent_posts %}
    <div class="sidebar-section">
        <h3>Recent Posts</h3>
        {% get_recent_posts 5 as posts %}
        {% for post in posts %}
            <a href="{{ post.get_absolute_url }}">{{ post.title }}</a>
        {% endfor %}
    </div>
{% endcache %}
```

**Per-object caching with versioning:**
```django
{% cache 3600 product_detail product.id product.version %}
    <div class="product">
        <h1>{{ product.name }}</h1>
        <p>{{ product.description }}</p>
        <span class="price">${{ product.price }}</span>
    </div>
{% endcache %}
```

**Language-specific caching:**
```django
{% load i18n cache %}

{% cache 600 footer LANGUAGE_CODE %}
    <footer>
        <p>{% trans "Copyright 2024" %}</p>
    </footer>
{% endcache %}
```

## Lazy Evaluation

### Use `{% with %}` for Expensive Operations

```django
{# BAD - queryset evaluated multiple times #}
<h2>Posts ({{ posts.count }})</h2>
{% for post in posts %}
    <div>{{ post.title }}</div>
{% endfor %}
<p>Total: {{ posts.count }}</p>

{# GOOD - evaluate once #}
{% with post_count=posts.count %}
    <h2>Posts ({{ post_count }})</h2>
    {% for post in posts %}
        <div>{{ post.title }}</div>
    {% endfor %}
    <p>Total: {{ post_count }}</p>
{% endwith %}
```

### Cache Template Variables

```django
{% with total=user.posts.count published=user.posts.published.count %}
    <div class="stats">
        <span>Total: {{ total }}</span>
        <span>Published: {{ published }}</span>
        <span>Draft: {{ total|add:published|add:"-" }}</span>
    </div>
{% endwith %}
```

### Avoid Repeated Method Calls

```django
{# BAD - calls get_full_name() multiple times #}
<h1>{{ user.get_full_name }}</h1>
<p>Welcome, {{ user.get_full_name }}!</p>
<span>Logged in as {{ user.get_full_name }}</span>

{# GOOD - call once #}
{% with full_name=user.get_full_name %}
    <h1>{{ full_name }}</h1>
    <p>Welcome, {{ full_name }}!</p>
    <span>Logged in as {{ full_name }}</span>
{% endwith %}
```

## Query Optimization

### Select Related in Template Tags

```python
# templatetags/blog_tags.py
from django import template

register = template.Library()

# BAD - N+1 query problem
@register.simple_tag
def get_recent_posts(count=5):
    from blog.models import Post
    return Post.objects.filter(published=True)[:count]

# GOOD - optimize with select_related
@register.simple_tag
def get_recent_posts(count=5):
    from blog.models import Post
    return Post.objects.filter(
        published=True
    ).select_related(
        'author',
        'category'
    ).prefetch_related(
        'tags'
    )[:count]
```

### Optimize in View, Not Template

```python
# views.py - GOOD
def post_list(request):
    posts = Post.objects.select_related(
        'author',
        'category'
    ).prefetch_related(
        'tags',
        'comments__author'
    )
    return render(request, 'blog/post_list.html', {'posts': posts})
```

```django
{# Template can now access relations without extra queries #}
{% for post in posts %}
    <h2>{{ post.title }}</h2>
    <p>By {{ post.author.username }} in {{ post.category.name }}</p>
    <div class="tags">
        {% for tag in post.tags.all %}
            <span>{{ tag.name }}</span>
        {% endfor %}
    </div>
{% endfor %}
```

### Use `.only()` and `.defer()`

```python
# Fetch only needed fields
def post_list(request):
    posts = Post.objects.only(
        'id', 'title', 'slug', 'created_at', 'author__username'
    ).select_related('author')

    return render(request, 'blog/post_list.html', {'posts': posts})
```

### Avoid Template-Level Queries

```django
{# BAD - triggers database query in template #}
{% for user in users %}
    <div>{{ user.posts.count }}</div>  {# N+1 problem! #}
{% endfor %}

{# GOOD - annotate in view #}
```

```python
# views.py
from django.db.models import Count

def user_list(request):
    users = User.objects.annotate(
        post_count=Count('posts')
    )
    return render(request, 'users/list.html', {'users': users})
```

```django
{# Template #}
{% for user in users %}
    <div>{{ user.post_count }}</div>  {# No query! #}
{% endfor %}
```

## Template Compilation

### How Templates Are Compiled

1. **Parse:** Template string → Node tree
2. **Compile:** Node tree → Compiled template
3. **Render:** Compiled template + context → HTML

### Compilation Cache

With cached loader:
- Parse + Compile happens once
- Stored in memory
- Reused for all requests

### Precompile Templates (Advanced)

```python
# management/commands/precompile_templates.py
from django.core.management.base import BaseCommand
from django.template import engines
from pathlib import Path

class Command(BaseCommand):
    help = 'Precompile all templates'

    def handle(self, *args, **options):
        engine = engines['django']
        template_dirs = engine.engine.template_loaders[0].get_template_sources('')

        for template_dir in template_dirs:
            for template_file in Path(template_dir.name).rglob('*.html'):
                try:
                    engine.get_template(str(template_file.relative_to(template_dir.name)))
                    self.stdout.write(f'Compiled: {template_file}')
                except Exception as e:
                    self.stderr.write(f'Error: {template_file} - {e}')
```

## Profiling

### Django Debug Toolbar

Install and configure:

```python
# settings.py
INSTALLED_APPS = [
    # ...
    'debug_toolbar',
]

MIDDLEWARE = [
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    # ...
]

INTERNAL_IPS = [
    '127.0.0.1',
]
```

**View template rendering time:**
- Templates panel shows render times
- SQL panel shows queries triggered by templates

### Manual Profiling

```python
import time
from django.template import Template, Context

template = Template(template_string)
context = Context(context_dict)

start = time.time()
rendered = template.render(context)
end = time.time()

print(f"Render time: {(end - start) * 1000:.2f}ms")
```

### Template Profiling Context Processor

```python
# context_processors.py
import time
from django.conf import settings

def template_profiler(request):
    if settings.DEBUG:
        return {'_template_start_time': time.time()}
    return {}
```

```django
{# At end of base template #}
{% if debug %}
    <!-- Render time: {{ _template_start_time|timesince }} -->
{% endif %}
```

### Count Queries in Template

```python
from django.test.utils import override_settings
from django.db import connection
from django.template import Template, Context

with override_settings(DEBUG=True):
    connection.queries_log.clear()

    template = Template(template_string)
    template.render(Context(context_dict))

    print(f"Queries: {len(connection.queries)}")
    for query in connection.queries:
        print(f"{query['time']}s: {query['sql']}")
```

## Best Practices

### 1. Cache Expensive Operations

```django
{# BAD - complex calculation on every render #}
{% for item in items %}
    <div>{{ item.price|multiply:1.1|floatformat:2 }}</div>
{% endfor %}

{# GOOD - calculate in view or cache #}
{% cache 300 price_list %}
    {% for item in items %}
        <div>{{ item.price_with_tax }}</div>
    {% endfor %}
{% endcache %}
```

### 2. Minimize Template Inheritance Depth

```
# BAD - too deep
base.html → section_base.html → subsection_base.html → page.html

# GOOD - 2-3 levels max
base.html → section_base.html → page.html
```

### 3. Use Inclusion Tags Wisely

```python
# Inclusion tags render templates - can be expensive
# Cache the output if possible

@register.inclusion_tag('components/widget.html')
def expensive_widget():
    data = perform_expensive_operation()
    return {'data': data}
```

```django
{% cache 600 expensive_widget_cache %}
    {% expensive_widget %}
{% endcache %}
```

### 4. Avoid Complex Logic in Templates

```django
{# BAD - complex filtering in template #}
{% for item in all_items %}
    {% if item.status == 'active' and item.score > 50 and item.verified %}
        <div>{{ item.name }}</div>
    {% endif %}
{% endfor %}

{# GOOD - filter in view #}
{% for item in filtered_items %}
    <div>{{ item.name }}</div>
{% endfor %}
```

### 5. Optimize Includes

```django
{# BAD - include in loop without caching #}
{% for post in posts %}
    {% include 'blog/post_card.html' with post=post %}
{% endfor %}

{# BETTER - cache if post_card.html is expensive #}
{% for post in posts %}
    {% cache 300 post_card post.id %}
        {% include 'blog/post_card.html' with post=post %}
    {% endcache %}
{% endfor %}
```

### 6. Limit Loop Iterations

```django
{# BAD - no limit #}
{% for comment in post.comments.all %}
    <div>{{ comment.text }}</div>
{% endfor %}

{# GOOD - limit and paginate #}
{% for comment in post.recent_comments %}
    <div>{{ comment.text }}</div>
{% endfor %}
<a href="{% url 'comments' post.id %}">View all</a>
```

### 7. Use Static File Compression

```python
# settings.py
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'

# Or use whitenoise for compression
MIDDLEWARE = [
    'whitenoise.middleware.WhiteNoiseMiddleware',
    # ...
]

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
```

### 8. Async Template Loading (Django 4.1+)

```python
# views.py
from django.template.response import TemplateResponse

async def async_view(request):
    context = {
        'data': await get_async_data(),
    }
    return TemplateResponse(request, 'template.html', context)
```

## Performance Checklist

- [ ] Cached template loader enabled in production
- [ ] Fragment caching for expensive blocks
- [ ] QuerySet optimization (select_related/prefetch_related)
- [ ] `.only()` and `.defer()` for large models
- [ ] Avoid queries in template loops
- [ ] Template inheritance depth ≤ 3 levels
- [ ] Static files compressed and cached
- [ ] Database queries annotated in view
- [ ] Expensive calculations in view, not template
- [ ] Django Debug Toolbar installed for profiling

## Measuring Impact

### Before Optimization

```python
# views.py
def slow_view(request):
    posts = Post.objects.all()  # No optimization
    return render(request, 'blog/list.html', {'posts': posts})
```

```django
{# template.html - N+1 queries #}
{% for post in posts %}
    <div>
        <h2>{{ post.title }}</h2>
        <p>By {{ post.author.username }}</p>
        <p>{{ post.comments.count }} comments</p>
    </div>
{% endfor %}
```

**Result:** 100 posts = 201 queries, ~2000ms render time

### After Optimization

```python
# views.py
def fast_view(request):
    posts = Post.objects.select_related(
        'author'
    ).annotate(
        comment_count=Count('comments')
    )[:100]
    return render(request, 'blog/list.html', {'posts': posts})
```

```django
{# template.html - optimized #}
{% cache 300 post_list %}
    {% for post in posts %}
        <div>
            <h2>{{ post.title }}</h2>
            <p>By {{ post.author.username }}</p>
            <p>{{ post.comment_count }} comments</p>
        </div>
    {% endfor %}
{% endcache %}
```

**Result:** 100 posts = 1 query, ~50ms render time (after first load)

## Django Version Notes

### Django 4.1+
- Async template rendering support
- Improved cached loader performance

### Django 4.2+
- Better fragment cache key generation
- Optimized `{% include %}` tag

### Django 5.0+
- Template compilation improvements
- Reduced memory usage in cached loader

## Troubleshooting

### Cache not working

**Check:**
```python
# Is cache configured?
from django.core.cache import cache
cache.set('test', 'value', 10)
print(cache.get('test'))  # Should print 'value'
```

### High memory usage

**Cause:** Too many templates in cached loader

**Fix:** Use cache backend with memory limits or disable cached loader for rarely-used templates

### Stale cached fragments

**Solution:** Version cache keys:
```django
{% cache 600 object_detail object.id object.updated_at|date:"U" %}
    {# Cache key includes timestamp #}
{% endcache %}
```

### Queries still slow

**Profile with Django Debug Toolbar:**
- Check for N+1 queries
- Look for missing select_related/prefetch_related
- Verify indexes on filtered fields
