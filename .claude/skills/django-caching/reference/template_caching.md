# Template Fragment Caching Reference

This document covers template-level caching strategies using the `{% cache %}` template tag.

## Table of Contents

- [Basic Template Caching](#basic-template-caching)
- [Cache with Variables](#cache-with-variables)
- [Per-User Caching](#per-user-caching)
- [Nested Caching](#nested-caching)
- [Advanced Patterns](#advanced-patterns)
- [Template Cache Invalidation](#template-cache-invalidation)

## Basic Template Caching

### Simple Fragment Cache

```django
{% load cache %}

{% cache 500 sidebar %}
    <!-- This fragment is cached for 500 seconds -->
    <div class="sidebar">
        <h3>Categories</h3>
        <ul>
            {% for category in categories %}
                <li><a href="{{ category.url }}">{{ category.name }}</a></li>
            {% endfor %}
        </ul>
    </div>
{% endcache %}
```

### Multiple Cache Fragments

```django
{% load cache %}

<!DOCTYPE html>
<html>
<head>
    {% cache 3600 header %}
        <header>
            <nav>...</nav>
        </header>
    {% endcache %}
</head>
<body>
    {% cache 300 main_content %}
        <main>
            <!-- Cached for 5 minutes -->
        </main>
    {% endcache %}

    {% cache 600 sidebar %}
        <aside>
            <!-- Cached for 10 minutes -->
        </aside>
    {% endcache %}

    {% cache 86400 footer %}
        <footer>
            <!-- Cached for 24 hours -->
        </footer>
    {% endcache %}
</body>
</html>
```

### Specifying Cache Backend

```django
{% load cache %}

{% cache 500 sidebar using='special_cache' %}
    <div class="sidebar">
        <!-- Uses 'special_cache' backend instead of default -->
    </div>
{% endcache %}
```

## Cache with Variables

### Per-Object Caching

```django
{% load cache %}

{% for post in posts %}
    {% cache 600 post_item post.id %}
        <article>
            <h2>{{ post.title }}</h2>
            <p>{{ post.summary }}</p>
            <a href="{{ post.url }}">Read more</a>
        </article>
    {% endcache %}
{% endfor %}
```

### Cache with Multiple Variables

```django
{% load cache %}

{% cache 300 post_detail post.id post.updated_at %}
    <!-- Cache key includes both ID and update timestamp -->
    <!-- Automatically invalidated when updated_at changes -->
    <article>
        <h1>{{ post.title }}</h1>
        <div>{{ post.content|safe }}</div>
    </article>
{% endcache %}
```

### Cache with Translation

```django
{% load cache i18n %}

{% get_current_language as LANGUAGE_CODE %}

{% cache 600 navigation LANGUAGE_CODE %}
    <nav>
        <a href="{% url 'home' %}">{% trans "Home" %}</a>
        <a href="{% url 'about' %}">{% trans "About" %}</a>
        <a href="{% url 'contact' %}">{% trans "Contact" %}</a>
    </nav>
{% endcache %}
```

### Cache with Template Variable

```django
{% load cache %}

{% cache 300 user_widget user.id user.profile.updated_at %}
    <div class="user-widget">
        <img src="{{ user.profile.avatar }}" alt="{{ user.username }}">
        <h3>{{ user.get_full_name }}</h3>
        <p>{{ user.profile.bio }}</p>
    </div>
{% endcache %}
```

## Per-User Caching

### Simple Per-User Cache

```django
{% load cache %}

{% cache 600 user_dashboard request.user.id %}
    <div class="dashboard">
        <h2>Welcome, {{ request.user.username }}!</h2>
        <p>You have {{ user_notifications_count }} notifications</p>
        <!-- User-specific content -->
    </div>
{% endcache %}
```

### Per-User with Staff Detection

```django
{% load cache %}

{% cache 300 navigation request.user.id request.user.is_staff %}
    <nav>
        <a href="{% url 'home' %}">Home</a>
        {% if request.user.is_staff %}
            <a href="{% url 'admin:index' %}">Admin</a>
        {% endif %}
        {% if request.user.is_authenticated %}
            <a href="{% url 'logout' %}">Logout</a>
        {% else %}
            <a href="{% url 'login' %}">Login</a>
        {% endif %}
    </nav>
{% endcache %}
```

### Anonymous vs Authenticated

```django
{% load cache %}

{% if request.user.is_authenticated %}
    {% cache 300 user_header request.user.id %}
        <header class="user-header">
            <span>Welcome, {{ request.user.username }}</span>
            <a href="{% url 'profile' %}">Profile</a>
        </header>
    {% endcache %}
{% else %}
    {% cache 600 anonymous_header %}
        <header class="anonymous-header">
            <a href="{% url 'login' %}">Login</a>
            <a href="{% url 'signup' %}">Sign Up</a>
        </header>
    {% endcache %}
{% endif %}
```

## Nested Caching

### Outer and Inner Caches

```django
{% load cache %}

{% cache 3600 page_layout %}
    <!-- Page layout cached for 1 hour -->
    <div class="layout">
        <header>...</header>

        {% cache 300 dynamic_content %}
            <!-- Dynamic content refreshes every 5 minutes -->
            <div class="content">
                {% for item in latest_items %}
                    <div>{{ item }}</div>
                {% endfor %}
            </div>
        {% endcache %}

        <footer>...</footer>
    </div>
{% endcache %}
```

### Per-Object within List Cache

```django
{% load cache %}

{% cache 600 article_list category.id %}
    <div class="article-list">
        <h2>{{ category.name }}</h2>

        {% for article in articles %}
            {% cache 300 article_item article.id article.updated_at %}
                <!-- Each article cached separately -->
                <!-- Updates to one article don't invalidate entire list -->
                <article>
                    <h3>{{ article.title }}</h3>
                    <p>{{ article.summary }}</p>
                </article>
            {% endcache %}
        {% endfor %}
    </div>
{% endcache %}
```

**Note:** Be careful with nested caching - the outer cache will include the inner cached fragments, so updating the inner cache may not take effect until the outer cache expires.

## Advanced Patterns

### Conditional Caching

```django
{% load cache %}

{% if should_cache %}
    {% cache 600 conditional_fragment object.id %}
        <div>{{ expensive_content }}</div>
    {% endcache %}
{% else %}
    <div>{{ expensive_content }}</div>
{% endif %}
```

### Cache with Computed Key

```django
{% load cache %}

{% with cache_key=object.id|stringformat:"s"|add:":"|add:object.version %}
    {% cache 300 dynamic_cache cache_key %}
        <div>{{ object.content }}</div>
    {% endcache %}
{% endwith %}
```

### Cache with Request Parameters

```django
{% load cache %}

{% cache 300 search_results request.GET.q|default:"all" request.GET.page|default:"1" %}
    <div class="search-results">
        {% for result in results %}
            <div>{{ result.title }}</div>
        {% endfor %}
    </div>
{% endcache %}
```

### Time-Based Cache Keys

```django
{% load cache %}

{% now "Y-m-d-H" as current_hour %}

{% cache 3600 hourly_stats current_hour %}
    <!-- Cache refreshes every hour automatically -->
    <div class="stats">
        <p>Page views this hour: {{ hourly_views }}</p>
    </div>
{% endcache %}
```

### Cache with Feature Flags

```django
{% load cache %}

{% cache 600 feature_content request.user.id feature_enabled %}
    {% if feature_enabled %}
        <div class="new-feature">
            <!-- New feature content -->
        </div>
    {% else %}
        <div class="old-feature">
            <!-- Old feature content -->
        </div>
    {% endif %}
{% endcache %}
```

## Template Cache Invalidation

### Automatic Invalidation with Updated Timestamp

```django
{% load cache %}

{% cache 600 article article.id article.updated_at %}
    <!-- Cache automatically invalidated when article.updated_at changes -->
    <article>
        <h1>{{ article.title }}</h1>
        <div>{{ article.content }}</div>
    </article>
{% endcache %}
```

### Version-Based Invalidation

```python
# In view
def article_detail(request, article_id):
    article = get_object_or_404(Article, id=article_id)
    cache_version = article.cache_version  # Increment to invalidate

    return render(request, 'article.html', {
        'article': article,
        'cache_version': cache_version,
    })
```

```django
{% load cache %}

{% cache 3600 article article.id cache_version %}
    <article>{{ article.content }}</article>
{% endcache %}
```

### Manual Invalidation from Python

```python
from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key

# Invalidate specific fragment
key = make_template_fragment_key('article', [article.id])
cache.delete(key)

# Invalidate with variables
key = make_template_fragment_key('post_detail', [post.id, post.updated_at])
cache.delete(key)

# With cache backend
key = make_template_fragment_key('sidebar', using='special_cache')
cache.delete(key)
```

### Signal-Based Invalidation

```python
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key

@receiver([post_save, post_delete], sender=Article)
def invalidate_article_cache(sender, instance, **kwargs):
    # Invalidate article detail cache
    key = make_template_fragment_key('article', [instance.id])
    cache.delete(key)

    # Invalidate article list cache
    key = make_template_fragment_key('article_list', [instance.category_id])
    cache.delete(key)

    # Invalidate with timestamp (all versions)
    # Need to use pattern deletion (Redis only)
    if hasattr(cache, 'delete_pattern'):
        cache.delete_pattern(f'template.cache.article.{instance.id}.*')
```

## Common Patterns

### Sidebar Widget Pattern

```django
{% load cache %}

{% cache 3600 sidebar_categories %}
    <div class="sidebar-widget">
        <h3>Categories</h3>
        <ul>
            {% for category in categories %}
                <li>
                    <a href="{{ category.url }}">
                        {{ category.name }} ({{ category.article_count }})
                    </a>
                </li>
            {% endfor %}
        </ul>
    </div>
{% endcache %}
```

### User-Specific Menu Pattern

```django
{% load cache %}

{% if request.user.is_authenticated %}
    {% cache 600 user_menu request.user.id request.user.is_staff %}
        <nav class="user-menu">
            <a href="{% url 'profile' request.user.username %}">Profile</a>
            <a href="{% url 'settings' %}">Settings</a>
            {% if request.user.is_staff %}
                <a href="{% url 'admin:index' %}">Admin</a>
            {% endif %}
            <a href="{% url 'logout' %}">Logout</a>
        </nav>
    {% endcache %}
{% else %}
    {% cache 3600 anonymous_menu %}
        <nav class="anonymous-menu">
            <a href="{% url 'login' %}">Login</a>
            <a href="{% url 'signup' %}">Sign Up</a>
        </nav>
    {% endcache %}
{% endif %}
```

### Comment List Pattern

```django
{% load cache %}

<div class="comments">
    {% for comment in comments %}
        {% cache 600 comment comment.id comment.updated_at %}
            <div class="comment">
                <div class="comment-author">
                    {{ comment.author.username }}
                </div>
                <div class="comment-content">
                    {{ comment.content }}
                </div>
                <div class="comment-date">
                    {{ comment.created_at|date:"F d, Y" }}
                </div>
            </div>
        {% endcache %}
    {% endfor %}
</div>
```

### Paginated List Pattern

```django
{% load cache %}

{% cache 300 article_list page_obj.number %}
    <div class="article-list">
        {% for article in page_obj %}
            {% cache 600 article_preview article.id article.updated_at %}
                <article class="preview">
                    <h2>{{ article.title }}</h2>
                    <p>{{ article.summary }}</p>
                    <a href="{{ article.url }}">Read more</a>
                </article>
            {% endcache %}
        {% endfor %}
    </div>

    <div class="pagination">
        {% if page_obj.has_previous %}
            <a href="?page={{ page_obj.previous_page_number }}">Previous</a>
        {% endif %}
        <span>Page {{ page_obj.number }} of {{ page_obj.paginator.num_pages }}</span>
        {% if page_obj.has_next %}
            <a href="?page={{ page_obj.next_page_number }}">Next</a>
        {% endif %}
    </div>
{% endcache %}
```

### Statistics Widget Pattern

```django
{% load cache %}

{% now "Y-m-d-H" as current_hour %}

{% cache 3600 site_stats current_hour %}
    <div class="stats-widget">
        <h3>Site Statistics</h3>
        <ul>
            <li>Total Users: {{ total_users }}</li>
            <li>Total Posts: {{ total_posts }}</li>
            <li>Active Today: {{ active_today }}</li>
        </ul>
    </div>
{% endcache %}
```

## Performance Tips

### Don't Over-Cache

```django
{% load cache %}

<!-- BAD: Entire page cached, including user-specific parts -->
{% cache 600 entire_page %}
    <div>Welcome, {{ request.user.username }}</div>
    <div>Static content...</div>
{% endcache %}

<!-- GOOD: Cache only static parts -->
<div>Welcome, {{ request.user.username }}</div>
{% cache 600 static_content %}
    <div>Static content...</div>
{% endcache %}
```

### Cache at the Right Granularity

```django
{% load cache %}

<!-- TOO COARSE: One user's change invalidates everything -->
{% cache 300 all_comments post.id %}
    {% for comment in comments %}
        <div>{{ comment.content }}</div>
    {% endfor %}
{% endcache %}

<!-- TOO FINE: Too many cache operations -->
{% for comment in comments %}
    {% cache 300 comment_author comment.id %}{{ comment.author }}{% endcache %}
    {% cache 300 comment_content comment.id %}{{ comment.content }}{% endcache %}
    {% cache 300 comment_date comment.id %}{{ comment.created_at }}{% endcache %}
{% endfor %}

<!-- JUST RIGHT: Cache per comment -->
{% for comment in comments %}
    {% cache 300 comment comment.id comment.updated_at %}
        <div class="comment">
            <strong>{{ comment.author }}</strong>
            <p>{{ comment.content }}</p>
            <time>{{ comment.created_at }}</time>
        </div>
    {% endcache %}
{% endfor %}
```

### Include Version Information in Cache Key

```django
{% load cache %}

<!-- GOOD: Cache invalidates when object changes -->
{% cache 600 article article.id article.updated_at %}
    <article>{{ article.content }}</article>
{% endcache %}

<!-- BETTER: Also include related object versions -->
{% cache 600 article article.id article.updated_at article.author.updated_at %}
    <article>
        <h1>{{ article.title }}</h1>
        <p>By {{ article.author.name }}</p>
        <div>{{ article.content }}</div>
    </article>
{% endcache %}
```

## Complete Example

```django
{% load cache i18n %}

{% get_current_language as LANGUAGE_CODE %}

<!DOCTYPE html>
<html lang="{{ LANGUAGE_CODE }}">
<head>
    <title>{{ page_title }}</title>
</head>
<body>
    <!-- Site-wide header: cached per language -->
    {% cache 3600 site_header LANGUAGE_CODE %}
        <header>
            <h1>{% trans "My Site" %}</h1>
            <nav>
                <a href="{% url 'home' %}">{% trans "Home" %}</a>
                <a href="{% url 'about' %}">{% trans "About" %}</a>
            </nav>
        </header>
    {% endcache %}

    <!-- User-specific menu -->
    {% if request.user.is_authenticated %}
        {% cache 600 user_menu request.user.id request.user.is_staff %}
            <nav class="user-menu">
                <a href="{% url 'profile' %}">{{ request.user.username }}</a>
                {% if request.user.is_staff %}
                    <a href="{% url 'admin:index' %}">Admin</a>
                {% endif %}
            </nav>
        {% endcache %}
    {% endif %}

    <!-- Main content: cached per page -->
    <main>
        {% block content %}
            {% cache 300 page_content page.id page.updated_at LANGUAGE_CODE %}
                <h1>{{ page.title }}</h1>
                <div>{{ page.content|safe }}</div>
            {% endcache %}
        {% endblock %}
    </main>

    <!-- Sidebar: cached components -->
    <aside>
        {% cache 600 popular_posts LANGUAGE_CODE %}
            <div class="widget">
                <h3>{% trans "Popular Posts" %}</h3>
                <ul>
                    {% for post in popular_posts %}
                        <li>
                            <a href="{{ post.url }}">{{ post.title }}</a>
                        </li>
                    {% endfor %}
                </ul>
            </div>
        {% endcache %}

        {% now "Y-m-d-H" as current_hour %}
        {% cache 3600 recent_comments current_hour %}
            <div class="widget">
                <h3>{% trans "Recent Comments" %}</h3>
                <ul>
                    {% for comment in recent_comments %}
                        <li>
                            <strong>{{ comment.author }}</strong>:
                            {{ comment.content|truncatewords:10 }}
                        </li>
                    {% endfor %}
                </ul>
            </div>
        {% endcache %}
    </aside>

    <!-- Footer: cached per language, long timeout -->
    {% cache 86400 site_footer LANGUAGE_CODE %}
        <footer>
            <p>{% trans "© 2024 My Site. All rights reserved." %}</p>
        </footer>
    {% endcache %}
</body>
</html>
```

## Debugging Template Caches

### Check if Fragment is Cached

```python
from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key

# Check if fragment exists
key = make_template_fragment_key('article', [article.id])
is_cached = cache.get(key) is not None
print(f"Article {article.id} cached: {is_cached}")
```

### Clear All Template Fragments

```python
# This varies by backend
# For Redis with django-redis:
cache.delete_pattern('template.cache.*')

# For other backends, you may need to clear entire cache:
cache.clear()
```

### Log Cache Hits/Misses

```python
# Custom template tag to log cache operations
from django import template
from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key
import logging

logger = logging.getLogger(__name__)
register = template.Library()

@register.simple_tag
def log_cache_status(fragment_name, *args):
    key = make_template_fragment_key(fragment_name, args)
    is_cached = cache.get(key) is not None
    logger.info(f"Cache {'HIT' if is_cached else 'MISS'}: {key}")
    return ''
```

```django
{% load cache custom_tags %}

{% log_cache_status 'article' article.id %}
{% cache 600 article article.id %}
    <article>{{ article.content }}</article>
{% endcache %}
```
