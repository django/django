# Async Views Reference

Complete guide to building asynchronous views in Django 4.1+.

## Table of Contents

- [Async View Basics](#async-view-basics)
- [When to Use Async](#when-to-use-async)
- [Async Database Operations](#async-database-operations)
- [Async HTTP Requests](#async-http-requests)
- [Async Middleware](#async-middleware)
- [Common Pitfalls](#common-pitfalls)
- [Performance Considerations](#performance-considerations)
- [Testing Async Views](#testing-async-views)

## Async View Basics

### Requirements

```python
# settings.py
# Must use ASGI application
ASGI_APPLICATION = 'myproject.asgi.application'

# Database backend must support async (Django 4.2+)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        # psycopg 3 for async support
    }
}
```

### Simple Async View

```python
import asyncio
from django.http import HttpResponse

# Function-based async view
async def hello_async(request):
    """Async function-based view."""
    await asyncio.sleep(1)  # Simulate async operation
    return HttpResponse("Hello from async view!")
```

### Async Class-Based View

```python
from django.views import View
from django.http import JsonResponse

class AsyncDataView(View):
    """Async class-based view."""

    async def get(self, request):
        # Async operations
        data = await fetch_data()
        return JsonResponse(data)

    async def post(self, request):
        # Process async
        result = await process_data(request.body)
        return JsonResponse({'result': result})
```

### Async Generic Views

```python
from django.views.generic import TemplateView, ListView
from django.http import JsonResponse

class AsyncArticleListView(ListView):
    """Async ListView."""
    model = Article
    template_name = 'articles.html'

    async def get_queryset(self):
        """Override to use async ORM."""
        # Async query (Django 4.1+)
        articles = [
            article async for article in
            Article.objects.filter(published=True)
        ]
        return articles

class AsyncAPIView(TemplateView):
    """Async template view with API calls."""

    async def get_context_data(self, **kwargs):
        context = await super().get_context_data(**kwargs)

        # Parallel async operations
        context['weather'] = await fetch_weather()
        context['news'] = await fetch_news()

        return context
```

## When to Use Async

### Good Use Cases

**1. Multiple I/O-Bound Operations**

```python
import httpx
import asyncio

async def dashboard(request):
    """Fetch from multiple APIs in parallel."""

    async with httpx.AsyncClient() as client:
        # Run in parallel
        weather_task = client.get('https://api.weather.com/...')
        news_task = client.get('https://api.news.com/...')
        stocks_task = client.get('https://api.stocks.com/...')

        # Await all
        weather, news, stocks = await asyncio.gather(
            weather_task,
            news_task,
            stocks_task
        )

    return render(request, 'dashboard.html', {
        'weather': weather.json(),
        'news': news.json(),
        'stocks': stocks.json(),
    })
```

**2. Long-Polling / Server-Sent Events**

```python
async def live_updates(request):
    """Stream updates to client."""
    async def event_stream():
        while True:
            # Check for updates
            updates = await get_updates()

            if updates:
                yield f"data: {json.dumps(updates)}\n\n"

            await asyncio.sleep(1)

    from django.http import StreamingHttpResponse
    return StreamingHttpResponse(
        event_stream(),
        content_type='text/event-stream'
    )
```

**3. WebSocket Handling**

```python
# consumers.py (Django Channels)
from channels.generic.websocket import AsyncWebsocketConsumer
import json

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()

    async def receive(self, text_data):
        data = json.loads(text_data)

        # Async processing
        response = await process_message(data)

        await self.send(text_data=json.dumps(response))
```

### Bad Use Cases (Avoid Async)

**1. CPU-Bound Operations**

```python
# BAD - Async doesn't help CPU-bound work
async def compute_heavy(request):
    result = await asyncio.to_thread(heavy_computation)  # Still blocks
    return JsonResponse({'result': result})

# GOOD - Use Celery or sync view
def compute_heavy(request):
    task = heavy_computation.delay()  # Celery task
    return JsonResponse({'task_id': task.id})
```

**2. Simple CRUD Operations**

```python
# BAD - Unnecessary complexity
async def article_list(request):
    articles = [a async for a in Article.objects.all()]
    return render(request, 'articles.html', {'articles': articles})

# GOOD - Sync is simpler and fine
def article_list(request):
    articles = Article.objects.all()
    return render(request, 'articles.html', {'articles': articles})
```

**3. Views Without I/O**

```python
# BAD - No I/O, async overhead for nothing
async def hello(request):
    return HttpResponse("Hello!")

# GOOD - Use sync
def hello(request):
    return HttpResponse("Hello!")
```

## Async Database Operations

### Django 4.1+ Async ORM

```python
# Basic async queries
async def article_list(request):
    # Async iteration
    articles = [
        article async for article in
        Article.objects.filter(published=True)
    ]

    return JsonResponse({
        'articles': [
            {'id': a.id, 'title': a.title}
            for a in articles
        ]
    })

# Async get
async def article_detail(request, pk):
    try:
        article = await Article.objects.aget(pk=pk)
    except Article.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)

    return JsonResponse({
        'id': article.id,
        'title': article.title,
    })

# Async count, exists
async def stats(request):
    count = await Article.objects.acount()
    exists = await Article.objects.filter(featured=True).aexists()

    return JsonResponse({
        'total': count,
        'has_featured': exists,
    })
```

### Async Aggregation

```python
from django.db.models import Count, Avg

async def analytics(request):
    # Async aggregate (Django 4.2+)
    stats = await Article.objects.aaggregate(
        total=Count('id'),
        avg_views=Avg('view_count')
    )

    return JsonResponse(stats)
```

### Async Transactions

```python
from django.db import transaction

async def create_article(request):
    data = json.loads(request.body)

    async with transaction.atomic():
        # Create article
        article = await Article.objects.acreate(
            title=data['title'],
            content=data['content']
        )

        # Create tags
        for tag_name in data['tags']:
            tag, created = await Tag.objects.aget_or_create(name=tag_name)
            await article.tags.aadd(tag)

    return JsonResponse({'id': article.id})
```

### Parallel Queries

```python
async def complex_dashboard(request):
    """Execute multiple queries in parallel."""

    # Run queries concurrently
    articles_task = Article.objects.acount()
    users_task = User.objects.acount()
    comments_task = Comment.objects.filter(
        created_at__gte=timezone.now() - timedelta(days=7)
    ).acount()

    # Await all
    article_count, user_count, comment_count = await asyncio.gather(
        articles_task,
        users_task,
        comments_task
    )

    return JsonResponse({
        'articles': article_count,
        'users': user_count,
        'recent_comments': comment_count,
    })
```

### Async Related Objects

```python
# Django 4.2+
async def article_with_author(request, pk):
    article = await Article.objects.select_related('author').aget(pk=pk)

    # Access related object (loaded via select_related)
    author_name = article.author.username

    return JsonResponse({
        'id': article.id,
        'title': article.title,
        'author': author_name,
    })

# Many-to-many
async def article_with_tags(request, pk):
    article = await Article.objects.prefetch_related('tags').aget(pk=pk)

    tags = [tag.name async for tag in article.tags.all()]

    return JsonResponse({
        'id': article.id,
        'title': article.title,
        'tags': tags,
    })
```

### Fallback for Unsupported Operations

```python
from asgiref.sync import sync_to_async

# Wrap sync ORM operations
@sync_to_async
def get_complex_data():
    """Complex query not yet async."""
    return Article.objects.annotate(
        comment_count=Count('comments')
    ).filter(comment_count__gt=10)

async def popular_articles(request):
    articles = await get_complex_data()
    return JsonResponse({
        'articles': [
            {'id': a.id, 'title': a.title}
            for a in articles
        ]
    })
```

## Async HTTP Requests

### Using httpx

```python
import httpx

async def fetch_external_data(request):
    """Fetch from external API."""
    async with httpx.AsyncClient() as client:
        response = await client.get('https://api.example.com/data')
        data = response.json()

    return JsonResponse(data)

# Multiple requests in parallel
async def aggregate_apis(request):
    """Fetch from multiple APIs concurrently."""
    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(
            client.get('https://api1.example.com/data'),
            client.get('https://api2.example.com/data'),
            client.get('https://api3.example.com/data'),
        )

    return JsonResponse({
        'api1': results[0].json(),
        'api2': results[1].json(),
        'api3': results[2].json(),
    })
```

### Error Handling

```python
async def fetch_with_retry(request):
    """Retry failed requests."""
    async with httpx.AsyncClient() as client:
        for attempt in range(3):
            try:
                response = await client.get(
                    'https://api.example.com/data',
                    timeout=5.0
                )
                response.raise_for_status()
                return JsonResponse(response.json())

            except httpx.TimeoutException:
                if attempt == 2:  # Last attempt
                    return JsonResponse(
                        {'error': 'Request timeout'},
                        status=504
                    )
                await asyncio.sleep(1)  # Wait before retry

            except httpx.HTTPStatusError as e:
                return JsonResponse(
                    {'error': f'HTTP {e.response.status_code}'},
                    status=502
                )
```

### Concurrent Requests with Timeout

```python
async def fetch_with_timeout(request):
    """Fetch with overall timeout."""
    async with httpx.AsyncClient() as client:
        try:
            # All requests must complete within 5 seconds
            results = await asyncio.wait_for(
                asyncio.gather(
                    client.get('https://api1.example.com/data'),
                    client.get('https://api2.example.com/data'),
                    client.get('https://api3.example.com/data'),
                ),
                timeout=5.0
            )

            return JsonResponse({
                'results': [r.json() for r in results]
            })

        except asyncio.TimeoutError:
            return JsonResponse(
                {'error': 'Overall timeout exceeded'},
                status=504
            )
```

## Async Middleware

### Async Middleware Class

```python
# middleware.py
class AsyncTimingMiddleware:
    """Measure request processing time."""

    def __init__(self, get_response):
        self.get_response = get_response

    async def __call__(self, request):
        # Before view
        import time
        start = time.time()

        # Call view
        response = await self.get_response(request)

        # After view
        duration = time.time() - start
        response['X-Process-Time'] = str(duration)

        return response

# settings.py
MIDDLEWARE = [
    'myapp.middleware.AsyncTimingMiddleware',
    # ...
]
```

### Sync and Async Middleware

```python
from asgiref.sync import iscoroutinefunction, markcoroutinefunction

class HybridMiddleware:
    """Works with both sync and async views."""

    def __init__(self, get_response):
        self.get_response = get_response

        # Check if get_response is async
        if iscoroutinefunction(self.get_response):
            markcoroutinefunction(self)

    async def __call__(self, request):
        # Pre-processing
        await self.process_request(request)

        # Call view (sync or async)
        if iscoroutinefunction(self.get_response):
            response = await self.get_response(request)
        else:
            response = await sync_to_async(self.get_response)(request)

        # Post-processing
        await self.process_response(response)

        return response

    async def process_request(self, request):
        # Your async pre-processing
        pass

    async def process_response(self, response):
        # Your async post-processing
        pass
```

### Async Authentication Middleware

```python
class AsyncAuthMiddleware:
    """Async user authentication."""

    def __init__(self, get_response):
        self.get_response = get_response

    async def __call__(self, request):
        # Get auth token
        token = request.headers.get('Authorization')

        if token:
            # Async user lookup
            try:
                user = await User.objects.aget(auth_token=token)
                request.user = user
            except User.DoesNotExist:
                request.user = None
        else:
            request.user = None

        response = await self.get_response(request)
        return response
```

## Common Pitfalls

### 1. Mixing Sync and Async

```python
# BAD - Calling sync code from async
async def bad_view(request):
    # This blocks the event loop!
    articles = list(Article.objects.all())  # Sync ORM call
    return JsonResponse({'articles': articles})

# GOOD - Use async ORM or wrap in sync_to_async
async def good_view(request):
    articles = [a async for a in Article.objects.all()]
    return JsonResponse({'articles': articles})

# GOOD - Wrap sync code
from asgiref.sync import sync_to_async

@sync_to_async
def get_articles():
    return list(Article.objects.all())

async def good_view_wrapped(request):
    articles = await get_articles()
    return JsonResponse({'articles': articles})
```

### 2. Not Awaiting Async Functions

```python
# BAD - Forgot await
async def bad_view(request):
    article = Article.objects.aget(pk=1)  # Returns coroutine, not article!
    return JsonResponse({'title': article.title})  # Error!

# GOOD
async def good_view(request):
    article = await Article.objects.aget(pk=1)  # Await the coroutine
    return JsonResponse({'title': article.title})
```

### 3. Using Sync-Only Libraries

```python
# BAD - requests library is sync
import requests

async def bad_view(request):
    response = requests.get('https://api.example.com')  # Blocks event loop!
    return JsonResponse(response.json())

# GOOD - Use httpx or aiohttp
import httpx

async def good_view(request):
    async with httpx.AsyncClient() as client:
        response = await client.get('https://api.example.com')
    return JsonResponse(response.json())
```

### 4. Creating Many Tasks Without Limits

```python
# BAD - Could create thousands of concurrent tasks
async def bad_view(request):
    urls = get_1000_urls()
    tasks = [fetch_url(url) for url in urls]
    results = await asyncio.gather(*tasks)  # Too many concurrent!

# GOOD - Limit concurrency
import asyncio

async def good_view(request):
    urls = get_1000_urls()

    # Process in batches
    semaphore = asyncio.Semaphore(10)  # Max 10 concurrent

    async def fetch_with_limit(url):
        async with semaphore:
            return await fetch_url(url)

    tasks = [fetch_with_limit(url) for url in urls]
    results = await asyncio.gather(*tasks)
```

### 5. Blocking I/O Operations

```python
# BAD - File I/O blocks
async def bad_view(request):
    with open('data.json') as f:  # Blocks!
        data = f.read()
    return JsonResponse({'data': data})

# GOOD - Use aiofiles
import aiofiles

async def good_view(request):
    async with aiofiles.open('data.json') as f:
        data = await f.read()
    return JsonResponse({'data': data})

# Or wrap in thread
from asgiref.sync import sync_to_async
import os

async def good_view_wrapped(request):
    data = await sync_to_async(open)('data.json').read()
    return JsonResponse({'data': data})
```

## Performance Considerations

### Measure Performance

```python
import time
import logging

logger = logging.getLogger(__name__)

async def measured_view(request):
    start = time.time()

    # Your async operations
    data = await fetch_data()

    duration = time.time() - start
    logger.info(f"View took {duration:.2f}s")

    return JsonResponse(data)
```

### When Async is Slower

```python
# Simple query - sync is faster
# Async overhead: ~0.5ms
# Query time: ~1ms
# Total: ~1.5ms
async def async_simple(request):
    article = await Article.objects.aget(pk=1)
    return JsonResponse({'title': article.title})

# Sync is faster here
# No async overhead
# Query time: ~1ms
# Total: ~1ms
def sync_simple(request):
    article = Article.objects.get(pk=1)
    return JsonResponse({'title': article.title})
```

### When Async is Faster

```python
# Multiple I/O operations - async wins
# Sync: 3 * 200ms = 600ms total
def sync_multiple(request):
    data1 = fetch_api1()  # 200ms
    data2 = fetch_api2()  # 200ms
    data3 = fetch_api3()  # 200ms
    return JsonResponse({'data': [data1, data2, data3]})

# Async: max(200ms, 200ms, 200ms) = 200ms total
async def async_multiple(request):
    data1, data2, data3 = await asyncio.gather(
        fetch_api1(),  # Parallel
        fetch_api2(),  # Parallel
        fetch_api3(),  # Parallel
    )
    return JsonResponse({'data': [data1, data2, data3]})
```

## Testing Async Views

### Test Client

```python
from django.test import TestCase, AsyncClient

class AsyncViewTest(TestCase):
    async def test_async_view(self):
        """Test async view."""
        client = AsyncClient()

        response = await client.get('/async-endpoint/')

        self.assertEqual(response.status_code, 200)
        self.assertIn('data', response.json())

    def test_sync_wrapper(self):
        """Run async test from sync test method."""
        import asyncio

        async def run_test():
            client = AsyncClient()
            response = await client.get('/async-endpoint/')
            return response

        response = asyncio.run(run_test())
        self.assertEqual(response.status_code, 200)
```

### Testing with pytest

```python
import pytest
from django.test import AsyncClient

@pytest.mark.asyncio
@pytest.mark.django_db
async def test_async_view():
    """Test async view with pytest."""
    client = AsyncClient()

    response = await client.get('/async-endpoint/')

    assert response.status_code == 200
    assert 'data' in response.json()
```

### Mocking Async Operations

```python
from unittest.mock import AsyncMock, patch
from django.test import TestCase

class AsyncViewTest(TestCase):
    @patch('myapp.views.fetch_external_data')
    async def test_with_mock(self, mock_fetch):
        """Mock async function."""
        # Setup mock
        mock_fetch.return_value = {'result': 'mocked'}

        # Test view
        client = AsyncClient()
        response = await client.get('/api-view/')

        # Assertions
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'result': 'mocked'})
        mock_fetch.assert_called_once()
```

## Best Practices

1. **Use async only when beneficial** - Multiple I/O operations
2. **Don't mix sync and async** - Use consistent async or sync_to_async
3. **Limit concurrency** - Use Semaphore for many tasks
4. **Use async-compatible libraries** - httpx, aiofiles, aioredis
5. **Profile before optimizing** - Measure actual performance
6. **Handle errors properly** - Async exceptions can be tricky
7. **Test async code** - Use AsyncClient and pytest-asyncio
8. **Use Django 4.2+** - Better async ORM support
9. **Configure ASGI properly** - Use Uvicorn or Daphne
10. **Monitor event loop** - Watch for blocking operations
