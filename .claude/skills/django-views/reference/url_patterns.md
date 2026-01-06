# Django URL Patterns Reference

## Table of Contents

- [Path vs Re_path](#path-vs-re_path)
- [Built-in Path Converters](#built-in-path-converters)
- [Custom Path Converters](#custom-path-converters)
- [URL Namespacing](#url-namespacing)
- [URL Reversing](#url-reversing)
- [Advanced Patterns](#advanced-patterns)
- [Best Practices](#best-practices)

## Path vs Re_path

### path()

**Recommended for most cases.** Uses simple syntax with typed converters.

```python
from django.urls import path
from . import views

urlpatterns = [
    # Static paths
    path('about/', views.about, name='about'),

    # Path converters
    path('articles/<int:pk>/', views.article_detail, name='article-detail'),
    path('category/<slug:slug>/', views.category, name='category'),
    path('archive/<int:year>/<int:month>/', views.archive, name='archive'),
]
```

**Advantages:**
- Cleaner, more readable syntax
- Type conversion built-in
- Most common use cases covered
- Less error-prone

### re_path()

**Use for complex patterns.** Uses full regex syntax.

```python
from django.urls import re_path
from . import views

urlpatterns = [
    # Complex patterns
    re_path(r'^articles/(?P<year>[0-9]{4})/$', views.year_archive),

    # Multiple formats
    re_path(r'^data\.(?P<format>json|xml|csv)$', views.export_data),

    # Optional segments
    re_path(r'^profile/(?P<username>\w+)(?:/(?P<tab>\w+))?/$', views.profile),

    # Legacy URL support
    re_path(r'^old-url/(?P<pk>\d+)/$', views.redirect_old_url),
]
```

**Use when:**
- Need regex features (lookahead, character classes)
- Supporting legacy URL patterns
- Complex validation requirements
- Multiple optional segments

## Built-in Path Converters

### str (default)
**Matches:** Any non-empty string, excluding `/`
**Returns:** String

```python
path('tag/<str:tag_name>/', views.tag_list)
# Matches: /tag/python/, /tag/django-tips/
# Doesn't match: /tag/, /tag//
```

### int
**Matches:** Zero or positive integer
**Returns:** Integer

```python
path('article/<int:pk>/', views.article_detail)
# Matches: /article/1/, /article/99999/
# Doesn't match: /article/0/, /article/-1/, /article/abc/
```

### slug
**Matches:** ASCII letters, numbers, hyphens, underscores
**Pattern:** `[-a-zA-Z0-9_]+`
**Returns:** String

```python
path('post/<slug:slug>/', views.post_detail)
# Matches: /post/my-first-post/, /post/hello_world/
# Doesn't match: /post/hello world/, /post/café/
```

### uuid
**Matches:** UUID format (8-4-4-4-12 hex digits)
**Returns:** UUID object

```python
from uuid import UUID

path('document/<uuid:doc_id>/', views.document_detail)
# Matches: /document/550e8400-e29b-41d4-a716-446655440000/
# Returns: UUID('550e8400-e29b-41d4-a716-446655440000')
```

### path
**Matches:** Any non-empty string, including `/`
**Returns:** String
**Use for:** Catching remaining URL parts

```python
path('file/<path:file_path>/', views.serve_file)
# Matches: /file/docs/guide.pdf, /file/a/b/c/d.txt
```

## Custom Path Converters

### Creating a Converter

```python
# converters.py
class YearMonthConverter:
    """Matches YYYY-MM format."""
    regex = r'[0-9]{4}-[0-9]{2}'

    def to_python(self, value):
        """Convert URL string to Python object."""
        year, month = value.split('-')
        return {'year': int(year), 'month': int(month)}

    def to_url(self, value):
        """Convert Python object to URL string (for reverse())."""
        return f"{value['year']:04d}-{value['month']:02d}"
```

### Registering Converter

```python
# urls.py
from django.urls import path, register_converter
from . import converters, views

register_converter(converters.YearMonthConverter, 'ym')

urlpatterns = [
    path('archive/<ym:date>/', views.archive),
]

# Usage in view
def archive(request, date):
    # date = {'year': 2024, 'month': 1}
    year = date['year']
    month = date['month']
```

### More Custom Converters

#### Date Converter

```python
from datetime import datetime

class DateConverter:
    regex = r'[0-9]{4}-[0-9]{2}-[0-9]{2}'

    def to_python(self, value):
        return datetime.strptime(value, '%Y-%m-%d').date()

    def to_url(self, value):
        return value.strftime('%Y-%m-%d')

# Register
register_converter(DateConverter, 'date')

# Use
path('events/<date:event_date>/', views.events)
```

#### Username Converter (with validation)

```python
class UsernameConverter:
    """Alphanumeric username, 3-20 chars."""
    regex = r'[a-zA-Z0-9_]{3,20}'

    def to_python(self, value):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            return User.objects.get(username=value)
        except User.DoesNotExist:
            # Will result in 404
            return None

    def to_url(self, value):
        if hasattr(value, 'username'):
            return value.username
        return str(value)

register_converter(UsernameConverter, 'username')

path('profile/<username:user>/', views.profile)
# View receives User object directly!
```

#### Enum Converter

```python
from enum import Enum

class FileFormat(Enum):
    JSON = 'json'
    XML = 'xml'
    CSV = 'csv'

class FormatConverter:
    regex = r'(json|xml|csv)'

    def to_python(self, value):
        return FileFormat(value)

    def to_url(self, value):
        if isinstance(value, FileFormat):
            return value.value
        return value

register_converter(FormatConverter, 'format')

path('export.<format:file_format>/', views.export)
```

## URL Namespacing

### Application Namespace

**Project urls.py:**
```python
from django.urls import path, include

urlpatterns = [
    path('blog/', include('blog.urls', namespace='blog')),
    path('shop/', include('shop.urls', namespace='shop')),
]
```

**App urls.py (blog/urls.py):**
```python
from django.urls import path
from . import views

app_name = 'blog'  # REQUIRED for namespace

urlpatterns = [
    path('', views.ArticleListView.as_view(), name='list'),
    path('<int:pk>/', views.ArticleDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.ArticleUpdateView.as_view(), name='edit'),
]
```

**Reversing namespaced URLs:**
```python
# In views
from django.urls import reverse

url = reverse('blog:detail', kwargs={'pk': 1})
# → /blog/1/

# In templates
{% url 'blog:detail' pk=article.pk %}

# In redirects
return redirect('blog:list')
```

### Instance Namespace (Advanced)

**Use case:** Same app included multiple times

```python
# Project urls.py
urlpatterns = [
    path('blog/', include('blog.urls', namespace='blog')),
    path('news/', include('blog.urls', namespace='news')),
]

# Can now reverse to different instances
reverse('blog:list')  # → /blog/
reverse('news:list')  # → /news/
```

### Nested Namespaces

```python
# Project urls.py
urlpatterns = [
    path('api/v1/', include('api.v1.urls', namespace='api-v1')),
]

# api/v1/urls.py
app_name = 'api-v1'
urlpatterns = [
    path('blog/', include('blog.api.urls', namespace='blog')),
]

# blog/api/urls.py
app_name = 'blog'
urlpatterns = [
    path('articles/', views.article_list, name='article-list'),
]

# Reverse
reverse('api-v1:blog:article-list')  # → /api/v1/blog/articles/
```

## URL Reversing

### In Views

```python
from django.urls import reverse
from django.shortcuts import redirect

def my_view(request):
    # Reverse by name
    url = reverse('article-detail', kwargs={'pk': 1})
    # → /articles/1/

    # With namespace
    url = reverse('blog:article-detail', kwargs={'pk': 1})

    # With args instead of kwargs
    url = reverse('archive', args=[2024, 1])
    # → /archive/2024/1/

    # Redirect
    return redirect('article-detail', pk=1)
```

### In Templates

```django
{# Basic #}
<a href="{% url 'article-detail' pk=article.pk %}">Read More</a>

{# With namespace #}
<a href="{% url 'blog:article-detail' pk=article.pk %}">Read More</a>

{# With positional args #}
<a href="{% url 'archive' 2024 1 %}">January 2024</a>

{# Store in variable #}
{% url 'article-detail' pk=article.pk as article_url %}
<a href="{{ article_url }}">Read More</a>

{# Add query string #}
<a href="{% url 'article-list' %}?page=2&sort=date">Page 2</a>
```

### In Models

```python
from django.urls import reverse

class Article(models.Model):
    title = models.CharField(max_length=200)

    def get_absolute_url(self):
        """Used by CreateView, UpdateView success redirect."""
        return reverse('article-detail', kwargs={'pk': self.pk})

# In views
class ArticleCreateView(CreateView):
    model = Article
    # Automatically redirects to article.get_absolute_url()
```

### Reverse Lazy (for class attributes)

```python
from django.urls import reverse_lazy

class ArticleCreateView(CreateView):
    model = Article
    success_url = reverse_lazy('article-list')
    # reverse() would fail here - URLs not loaded yet!
```

### Getting Current URL Name

```python
from django.urls import resolve

def my_view(request):
    # Get current URL name
    current_url = resolve(request.path_info).url_name
    namespace = resolve(request.path_info).namespace

    # Check current URL
    if current_url == 'article-detail':
        # Do something
        pass
```

## Advanced Patterns

### Optional Parameters

**Using path() with default view parameter:**
```python
path('articles/', views.article_list, name='article-list'),
path('articles/page/<int:page>/', views.article_list, name='article-list-page'),

def article_list(request, page=1):
    # Handle pagination
    pass
```

**Using re_path() with optional groups:**
```python
re_path(
    r'^profile/(?P<username>\w+)(?:/(?P<tab>\w+))?/$',
    views.profile,
    name='profile'
)

def profile(request, username, tab='overview'):
    # tab defaults to 'overview' if not in URL
    pass
```

### Multiple URL Patterns for Same View

```python
urlpatterns = [
    # Support both slug and ID
    path('article/<int:pk>/', views.article_detail, name='article-by-id'),
    path('article/<slug:slug>/', views.article_detail, name='article-by-slug'),
]

def article_detail(request, pk=None, slug=None):
    if pk:
        article = get_object_or_404(Article, pk=pk)
    else:
        article = get_object_or_404(Article, slug=slug)
    return render(request, 'article.html', {'article': article})
```

### Trailing Slashes

**Django default: trailing slash required**
```python
path('articles/', views.list)  # /articles/ ✓, /articles ✗
```

**Optional trailing slash:**
```python
re_path(r'^articles/?$', views.list)  # Both work
```

**Settings to auto-append:**
```python
# settings.py
APPEND_SLASH = True  # Default
# /articles → redirects to /articles/
```

### URL Includes with Prefix

```python
# Project urls.py
urlpatterns = [
    # Include all blog URLs under /blog/
    path('blog/', include([
        path('', views.article_list, name='article-list'),
        path('<int:pk>/', views.article_detail, name='article-detail'),
    ])),
]
```

### URL Error Handlers

```python
# Project urls.py
from django.conf.urls import handler400, handler403, handler404, handler500

handler404 = 'myapp.views.custom_404'
handler500 = 'myapp.views.custom_500'

# myapp/views.py
def custom_404(request, exception):
    return render(request, '404.html', status=404)

def custom_500(request):
    return render(request, '500.html', status=500)
```

### Versioned API URLs

```python
# urls.py
from django.urls import path, include

urlpatterns = [
    path('api/v1/', include('api.v1.urls', namespace='api-v1')),
    path('api/v2/', include('api.v2.urls', namespace='api-v2')),
]

# api/v1/urls.py
app_name = 'api-v1'
urlpatterns = [
    path('articles/', views.article_list_v1),
]

# api/v2/urls.py
app_name = 'api-v2'
urlpatterns = [
    path('articles/', views.article_list_v2),
]
```

### Subdomain Routing (with middleware)

```python
# middleware.py
class SubdomainURLConfMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host().split(':')[0]
        subdomain = host.split('.')[0]

        if subdomain == 'api':
            request.urlconf = 'api.urls'
        elif subdomain == 'blog':
            request.urlconf = 'blog.urls'

        return self.get_response(request)

# settings.py
MIDDLEWARE = [
    'myapp.middleware.SubdomainURLConfMiddleware',
    # ... other middleware
]
```

### Conditional URL Patterns

```python
# urls.py
from django.conf import settings
from django.urls import path

urlpatterns = [
    path('', views.home),
]

if settings.DEBUG:
    # Debug-only URLs
    urlpatterns += [
        path('debug/', views.debug_info),
    ]

# Or feature flags
if 'new_feature' in settings.FEATURES:
    urlpatterns += [
        path('beta/', views.beta_feature),
    ]
```

## Best Practices

### 1. Always Name Your URLs

```python
# GOOD
path('articles/', views.list, name='article-list')

# BAD - Hard to maintain
path('articles/', views.list)
```

### 2. Use Consistent Naming

```python
# Convention: app:model-action
urlpatterns = [
    path('', views.ArticleListView.as_view(), name='article-list'),
    path('<int:pk>/', views.ArticleDetailView.as_view(), name='article-detail'),
    path('create/', views.ArticleCreateView.as_view(), name='article-create'),
    path('<int:pk>/edit/', views.ArticleUpdateView.as_view(), name='article-update'),
    path('<int:pk>/delete/', views.ArticleDeleteView.as_view(), name='article-delete'),
]
```

### 3. Keep URLs RESTful

```python
# GOOD - RESTful
path('articles/', views.list)           # GET list
path('articles/<int:pk>/', views.detail)  # GET detail
path('articles/create/', views.create)   # POST create
path('articles/<int:pk>/edit/', views.update)  # POST update
path('articles/<int:pk>/delete/', views.delete)  # POST delete

# AVOID - Non-RESTful
path('get-articles/', views.list)
path('article-detail/<int:pk>/', views.detail)
path('new-article/', views.create)
```

### 4. Use Namespaces for Apps

```python
# GOOD - Clear, no conflicts
reverse('blog:article-detail', kwargs={'pk': 1})
reverse('shop:product-detail', kwargs={'pk': 1})

# BAD - Name collisions possible
reverse('article-detail', kwargs={'pk': 1})
reverse('product-detail', kwargs={'pk': 1})
```

### 5. Prefer path() Over re_path()

```python
# GOOD - Readable
path('articles/<int:year>/<int:month>/', views.archive)

# UNNECESSARY - Harder to read
re_path(r'^articles/(?P<year>\d{4})/(?P<month>\d{2})/$', views.archive)
```

### 6. Use get_absolute_url() in Models

```python
class Article(models.Model):
    def get_absolute_url(self):
        return reverse('article-detail', kwargs={'pk': self.pk})

# Benefits:
# - DRY: URL logic in one place
# - Works with CreateView/UpdateView
# - Easy to use in templates: {{ article.get_absolute_url }}
```

### 7. Avoid Hardcoded URLs

```python
# BAD
return redirect('/articles/1/')
<a href="/articles/{{ article.pk }}/">Read More</a>

# GOOD
return redirect('article-detail', pk=1)
<a href="{% url 'article-detail' pk=article.pk %}">Read More</a>
```

### 8. Use reverse_lazy for Class Attributes

```python
# GOOD
class ArticleCreateView(CreateView):
    success_url = reverse_lazy('article-list')

# BAD - Will raise error
class ArticleCreateView(CreateView):
    success_url = reverse('article-list')  # URLs not loaded yet!
```

### 9. Order URLs Specific to General

```python
urlpatterns = [
    # Specific patterns first
    path('articles/featured/', views.featured),
    path('articles/latest/', views.latest),

    # General patterns last
    path('articles/<slug:slug>/', views.detail),
    path('articles/', views.list),
]
```

### 10. Validate URL Parameters in Views

```python
# Don't rely solely on URL converters
def article_detail(request, year, month):
    # Validate date is valid
    try:
        date = datetime(year, month, 1)
    except ValueError:
        raise Http404("Invalid date")

    articles = Article.objects.filter(
        created_at__year=year,
        created_at__month=month
    )
    return render(request, 'list.html', {'articles': articles})
```

## Common Pitfalls

### 1. Forgetting app_name for Namespaces

```python
# urls.py
path('blog/', include('blog.urls', namespace='blog'))

# blog/urls.py - MISSING app_name
urlpatterns = [...]
# Error: 'blog' is not a registered namespace

# FIX: Add app_name
app_name = 'blog'
urlpatterns = [...]
```

### 2. URL Pattern Order

```python
# BAD - 'featured' will never match
urlpatterns = [
    path('articles/<slug:slug>/', views.detail),
    path('articles/featured/', views.featured),  # Never reached!
]

# GOOD - Specific first
urlpatterns = [
    path('articles/featured/', views.featured),
    path('articles/<slug:slug>/', views.detail),
]
```

### 3. Missing Trailing Slash

```python
# With APPEND_SLASH = True (default)
path('articles', views.list)  # Accessed as /articles/ (redirected)

# Better: Include slash
path('articles/', views.list)
```

### 4. reverse() in Class Body

```python
# BAD - Executes during import
class MyView(CreateView):
    success_url = reverse('article-list')  # Error!

# GOOD - Executes at runtime
class MyView(CreateView):
    success_url = reverse_lazy('article-list')

# OR
class MyView(CreateView):
    def get_success_url(self):
        return reverse('article-list')
```
