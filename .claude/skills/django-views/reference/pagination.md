# Django Pagination Reference

Complete guide to implementing pagination in Django views, templates, and APIs.

## Table of Contents

- [Django Paginator Basics](#django-paginator-basics)
- [Template-Based Pagination](#template-based-pagination)
- [API Pagination](#api-pagination)
- [Class-Based View Pagination](#class-based-view-pagination)
- [Advanced Patterns](#advanced-patterns)
- [Performance Optimization](#performance-optimization)

## Django Paginator Basics

### Basic Usage

```python
from django.core.paginator import Paginator

# Create paginator
articles = Article.objects.all().order_by('-created_at')
paginator = Paginator(articles, 25)  # 25 items per page

# Get page
page_number = 1
page_obj = paginator.page(page_number)

# Access data
print(page_obj.object_list)  # Items on this page
print(page_obj.number)        # Current page number
print(page_obj.has_next())    # Has next page?
print(page_obj.has_previous()) # Has previous page?
```

### Paginator Attributes

```python
paginator = Paginator(articles, 25)

# Paginator attributes
paginator.count          # Total number of objects
paginator.num_pages      # Total number of pages
paginator.page_range     # Range object: range(1, num_pages+1)
paginator.per_page       # Items per page (25)

# Page object attributes
page = paginator.page(2)
page.number              # Current page number (2)
page.object_list         # QuerySet of items on this page
page.has_next()          # True if next page exists
page.has_previous()      # True if previous page exists
page.next_page_number()  # Next page number (3)
page.previous_page_number() # Previous page number (1)
page.start_index()       # 1-indexed start (26)
page.end_index()         # 1-indexed end (50)
```

### Error Handling

```python
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

paginator = Paginator(articles, 25)
page_number = request.GET.get('page')

try:
    page = paginator.page(page_number)
except PageNotAnInteger:
    # If page is not an integer, deliver first page
    page = paginator.page(1)
except EmptyPage:
    # If page is out of range, deliver last page
    page = paginator.page(paginator.num_pages)
```

### Safe Page Retrieval

```python
# get_page() handles errors automatically
page_number = request.GET.get('page')
page = paginator.get_page(page_number)

# Returns:
# - First page if page_number is None or not an integer
# - Last page if page_number is out of range
# Never raises exceptions
```

## Template-Based Pagination

### Function-Based View

```python
from django.core.paginator import Paginator
from django.shortcuts import render

def article_list(request):
    """List articles with pagination."""
    article_list = Article.objects.filter(
        published=True
    ).select_related('author').order_by('-created_at')

    # Pagination
    paginator = Paginator(article_list, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'blog/article_list.html', {
        'page_obj': page_obj,
    })
```

### Template Implementation

```django
{# blog/article_list.html #}

{# Display articles #}
{% for article in page_obj %}
    <article>
        <h2>{{ article.title }}</h2>
        <p>By {{ article.author.username }}</p>
    </article>
{% empty %}
    <p>No articles found.</p>
{% endfor %}

{# Pagination controls #}
<div class="pagination">
    <span class="step-links">
        {% if page_obj.has_previous %}
            <a href="?page=1">&laquo; first</a>
            <a href="?page={{ page_obj.previous_page_number }}">previous</a>
        {% endif %}

        <span class="current">
            Page {{ page_obj.number }} of {{ page_obj.paginator.num_pages }}
        </span>

        {% if page_obj.has_next %}
            <a href="?page={{ page_obj.next_page_number }}">next</a>
            <a href="?page={{ page_obj.paginator.num_pages }}">last &raquo;</a>
        {% endif %}
    </span>
</div>
```

### Pagination with Page Range

```django
{# Show page numbers with ellipsis #}
<div class="pagination">
    {% if page_obj.has_previous %}
        <a href="?page={{ page_obj.previous_page_number }}">&laquo;</a>
    {% endif %}

    {% for num in page_obj.paginator.page_range %}
        {% if page_obj.number == num %}
            <span class="current">{{ num }}</span>
        {% elif num > page_obj.number|add:'-3' and num < page_obj.number|add:'3' %}
            <a href="?page={{ num }}">{{ num }}</a>
        {% endif %}
    {% endfor %}

    {% if page_obj.has_next %}
        <a href="?page={{ page_obj.next_page_number }}">&raquo;</a>
    {% endif %}
</div>
```

### Preserve Query Parameters

```python
# views.py
def article_list(request):
    # Build base query
    articles = Article.objects.filter(published=True)

    # Apply filters
    search = request.GET.get('search', '')
    category = request.GET.get('category', '')

    if search:
        articles = articles.filter(title__icontains=search)

    if category:
        articles = articles.filter(category=category)

    # Paginate
    paginator = Paginator(articles, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'blog/article_list.html', {
        'page_obj': page_obj,
        'search': search,
        'category': category,
    })
```

```django
{# Template: Preserve filters in pagination links #}
<a href="?page={{ page_obj.next_page_number }}&search={{ search }}&category={{ category }}">
    Next
</a>

{# Or use a custom template tag #}
{% load pagination_tags %}
<a href="{% append_query page=page_obj.next_page_number %}">Next</a>
```

### Custom Template Tag for Query Preservation

```python
# templatetags/pagination_tags.py
from django import template
from django.http import QueryDict

register = template.Library()

@register.simple_tag(takes_context=True)
def append_query(context, **kwargs):
    """Append/update query parameters."""
    request = context['request']
    query = request.GET.copy()

    for key, value in kwargs.items():
        query[key] = value

    return f"?{query.urlencode()}"
```

## API Pagination

### Offset-Based Pagination (Page Numbers)

```python
from django.http import JsonResponse
from django.core.paginator import Paginator

def article_list_api(request):
    """API with offset pagination."""
    page = int(request.GET.get('page', 1))
    page_size = min(int(request.GET.get('page_size', 20)), 100)

    articles = Article.objects.filter(
        published=True
    ).select_related('author').order_by('-created_at')

    paginator = Paginator(articles, page_size)
    page_obj = paginator.get_page(page)

    return JsonResponse({
        'count': paginator.count,
        'page': page_obj.number,
        'num_pages': paginator.num_pages,
        'next': page_obj.next_page_number() if page_obj.has_next() else None,
        'previous': page_obj.previous_page_number() if page_obj.has_previous() else None,
        'results': [
            {
                'id': article.id,
                'title': article.title,
                'author': article.author.username,
            }
            for article in page_obj
        ]
    })
```

### Cursor-Based Pagination

**Better for:**
- Large datasets
- Real-time data
- Preventing duplicate/missing items during pagination
- Mobile apps with infinite scroll

```python
def article_list_cursor_api(request):
    """Cursor-based pagination."""
    cursor = request.GET.get('cursor')  # Last item ID
    limit = min(int(request.GET.get('limit', 20)), 100)

    # Query
    queryset = Article.objects.filter(
        published=True
    ).select_related('author').order_by('-id')

    if cursor:
        # Get items after cursor
        queryset = queryset.filter(id__lt=int(cursor))

    # Fetch limit + 1 to check if more exist
    articles = list(queryset[:limit + 1])
    has_more = len(articles) > limit

    if has_more:
        articles = articles[:limit]
        next_cursor = articles[-1].id
    else:
        next_cursor = None

    return JsonResponse({
        'results': [
            {
                'id': a.id,
                'title': a.title,
                'author': a.author.username,
            }
            for a in articles
        ],
        'next_cursor': next_cursor,
        'has_more': has_more,
    })
```

### Limit-Offset Pagination

```python
def article_list_limit_offset_api(request):
    """Limit/offset pagination."""
    limit = min(int(request.GET.get('limit', 20)), 100)
    offset = int(request.GET.get('offset', 0))

    # Total count
    total_count = Article.objects.filter(published=True).count()

    # Get items
    articles = Article.objects.filter(
        published=True
    ).select_related('author')[offset:offset + limit]

    return JsonResponse({
        'count': total_count,
        'limit': limit,
        'offset': offset,
        'next_offset': offset + limit if offset + limit < total_count else None,
        'results': [
            {
                'id': a.id,
                'title': a.title,
            }
            for a in articles
        ]
    })
```

### Time-Based Cursor Pagination

```python
from django.utils import timezone

def article_list_time_cursor_api(request):
    """Cursor based on timestamp."""
    cursor = request.GET.get('cursor')
    limit = min(int(request.GET.get('limit', 20)), 100)

    queryset = Article.objects.filter(
        published=True
    ).order_by('-created_at', '-id')

    if cursor:
        # Parse cursor: timestamp_id
        timestamp_str, item_id = cursor.split('_')
        cursor_time = timezone.datetime.fromisoformat(timestamp_str)

        # Items older than cursor
        queryset = queryset.filter(
            created_at__lt=cursor_time
        ) | queryset.filter(
            created_at=cursor_time,
            id__lt=int(item_id)
        )

    articles = list(queryset[:limit + 1])
    has_more = len(articles) > limit

    if has_more:
        articles = articles[:limit]
        last = articles[-1]
        next_cursor = f"{last.created_at.isoformat()}_{last.id}"
    else:
        next_cursor = None

    return JsonResponse({
        'results': [
            {
                'id': a.id,
                'title': a.title,
                'created_at': a.created_at.isoformat(),
            }
            for a in articles
        ],
        'next_cursor': next_cursor,
    })
```

## Class-Based View Pagination

### ListView with Pagination

```python
from django.views.generic import ListView

class ArticleListView(ListView):
    model = Article
    template_name = 'blog/article_list.html'
    context_object_name = 'articles'
    paginate_by = 25
    ordering = ['-created_at']

    def get_queryset(self):
        return Article.objects.filter(
            published=True
        ).select_related('author')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Additional context
        context['total_count'] = Article.objects.filter(published=True).count()
        return context
```

**Template receives:**
- `page_obj` - Current page
- `paginator` - Paginator object
- `is_paginated` - True if multiple pages exist
- `articles` - Alias for page_obj.object_list

### Dynamic Page Size

```python
class ArticleListView(ListView):
    model = Article
    template_name = 'blog/article_list.html'
    paginate_by = 25

    def get_paginate_by(self, queryset):
        """Allow page_size query param."""
        page_size = self.request.GET.get('page_size', self.paginate_by)
        try:
            page_size = int(page_size)
            # Cap at 100
            return min(page_size, 100)
        except ValueError:
            return self.paginate_by
```

### Paginated API View

```python
from django.views.generic import ListView
from django.http import JsonResponse

class ArticleListAPIView(ListView):
    model = Article
    paginate_by = 20

    def render_to_response(self, context, **response_kwargs):
        """Override to return JSON."""
        page_obj = context['page_obj']
        paginator = context['paginator']

        return JsonResponse({
            'count': paginator.count,
            'page': page_obj.number,
            'num_pages': paginator.num_pages,
            'results': [
                {
                    'id': article.id,
                    'title': article.title,
                }
                for article in page_obj
            ]
        })
```

## Advanced Patterns

### Paginate Multiple QuerySets

```python
def combined_list(request):
    """Paginate articles and products together."""
    from itertools import chain
    from operator import attrgetter

    articles = Article.objects.filter(published=True)
    products = Product.objects.filter(active=True)

    # Combine and sort
    combined = sorted(
        chain(articles, products),
        key=attrgetter('created_at'),
        reverse=True
    )

    # Paginate
    paginator = Paginator(combined, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'combined_list.html', {'page_obj': page_obj})
```

### Async Pagination (Django 4.1+)

```python
from django.views.generic import ListView
from django.http import JsonResponse

class ArticleListAPIView(ListView):
    model = Article
    paginate_by = 20

    async def get(self, request, *args, **kwargs):
        """Async pagination."""
        page = int(request.GET.get('page', 1))
        page_size = self.paginate_by

        # Async query
        offset = (page - 1) * page_size
        articles = [
            article async for article in
            Article.objects.filter(published=True)[offset:offset + page_size]
        ]

        total = await Article.objects.filter(published=True).acount()

        return JsonResponse({
            'count': total,
            'page': page,
            'results': [
                {'id': a.id, 'title': a.title}
                for a in articles
            ]
        })
```

### Custom Paginator

```python
from django.core.paginator import Paginator

class CustomPaginator(Paginator):
    """Add custom behavior to paginator."""

    def __init__(self, *args, **kwargs):
        # Custom options
        self.show_total = kwargs.pop('show_total', True)
        super().__init__(*args, **kwargs)

    def get_page_numbers(self, page_number, on_each_side=3, on_ends=2):
        """Get smart page range around current page."""
        if self.num_pages <= 10:
            return list(range(1, self.num_pages + 1))

        page_numbers = []

        # Start pages
        for i in range(1, on_ends + 1):
            if i <= self.num_pages:
                page_numbers.append(i)

        # Middle pages
        start = max(page_number - on_each_side, on_ends + 1)
        end = min(page_number + on_each_side, self.num_pages - on_ends)

        if start > on_ends + 1:
            page_numbers.append('...')

        for i in range(start, end + 1):
            page_numbers.append(i)

        if end < self.num_pages - on_ends:
            page_numbers.append('...')

        # End pages
        for i in range(self.num_pages - on_ends + 1, self.num_pages + 1):
            if i > end:
                page_numbers.append(i)

        return page_numbers
```

### Infinite Scroll Pagination

```python
def article_list_infinite(request):
    """Load more items for infinite scroll."""
    page = int(request.GET.get('page', 1))
    page_size = 20

    articles = Article.objects.filter(
        published=True
    ).select_related('author')

    paginator = Paginator(articles, page_size)
    page_obj = paginator.get_page(page)

    # AJAX request - return JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'html': render_to_string(
                'blog/_article_list_items.html',
                {'articles': page_obj}
            ),
            'has_next': page_obj.has_next(),
        })

    # Regular request - return full page
    return render(request, 'blog/article_list.html', {
        'page_obj': page_obj,
    })
```

```javascript
// Frontend JavaScript
let page = 1;
let loading = false;

window.addEventListener('scroll', () => {
    if (loading) return;

    const bottom = window.scrollY + window.innerHeight >= document.body.scrollHeight - 100;

    if (bottom) {
        loading = true;
        page++;

        fetch(`/articles/?page=${page}`, {
            headers: {'X-Requested-With': 'XMLHttpRequest'}
        })
        .then(res => res.json())
        .then(data => {
            document.getElementById('article-list').insertAdjacentHTML('beforeend', data.html);
            loading = false;

            if (!data.has_next) {
                window.removeEventListener('scroll', this);
            }
        });
    }
});
```

## Performance Optimization

### Count Optimization

```python
# SLOW - Full count on every page
paginator = Paginator(Article.objects.all(), 25)

# FAST - Cache the count
from django.core.cache import cache

def get_article_count():
    count = cache.get('article_count')
    if count is None:
        count = Article.objects.count()
        cache.set('article_count', count, 300)  # 5 minutes
    return count

# Use cached count
articles = Article.objects.all()
paginator = Paginator(articles, 25)
paginator._count = get_article_count()  # Override count
```

### Avoid N+1 Queries

```python
# BAD - N+1 queries
articles = Article.objects.all()
paginator = Paginator(articles, 25)
page = paginator.page(1)
# In template: {{ article.author.username }} causes N queries

# GOOD - Optimized
articles = Article.objects.select_related('author').all()
paginator = Paginator(articles, 25)
page = paginator.page(1)
```

### Use iterator() for Large Datasets

```python
# For read-only iteration over large datasets
def export_all_articles(request):
    """Export without loading all into memory."""
    articles = Article.objects.all().iterator(chunk_size=1000)

    # Process in chunks
    for article in articles:
        # Process article
        pass
```

### Keyset Pagination (Most Efficient)

```python
def article_list_keyset(request):
    """Keyset pagination - no offset, always fast."""
    last_id = request.GET.get('last_id')
    limit = 20

    queryset = Article.objects.filter(
        published=True
    ).order_by('-id')

    if last_id:
        queryset = queryset.filter(id__lt=int(last_id))

    articles = list(queryset[:limit])

    return JsonResponse({
        'results': [{'id': a.id, 'title': a.title} for a in articles],
        'last_id': articles[-1].id if articles else None,
    })
```

**Benefits:**
- No OFFSET clause (always fast, even on page 10000)
- Consistent results (no duplicates/missing items)
- Works with infinite scroll

**Drawbacks:**
- Can't jump to arbitrary page
- Requires indexed ordering field

### Approximate Count for Large Tables

```python
def approximate_count(queryset):
    """Fast approximate count for PostgreSQL."""
    from django.db import connection

    table = queryset.model._meta.db_table
    with connection.cursor() as cursor:
        cursor.execute(
            f"SELECT reltuples::bigint FROM pg_class WHERE relname = %s",
            [table]
        )
        row = cursor.fetchone()
        return row[0] if row else 0

# Use for pagination
articles = Article.objects.all()
paginator = Paginator(articles, 25)
paginator._count = approximate_count(articles)  # Fast estimate
```

## Best Practices

1. **Always order your queryset** - Pagination requires consistent ordering
2. **Use select_related/prefetch_related** - Avoid N+1 queries
3. **Cap page size** - Prevent memory issues with large page sizes
4. **Use cursor pagination for APIs** - Better for real-time data
5. **Cache counts** - Expensive on large tables
6. **Consider keyset pagination** - For large datasets
7. **Preserve filters in pagination links** - UX improvement
8. **Handle edge cases** - Invalid page numbers, empty results
9. **Use get_page()** - Handles errors automatically
10. **Index ordering fields** - Required for good performance
