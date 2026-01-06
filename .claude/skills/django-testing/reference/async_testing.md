# Async Testing in Django

Complete guide to testing async views, async ORM operations, and async code in Django 4.1+.

## Table of Contents

- [Overview](#overview)
- [Async Test Methods](#async-test-methods)
- [Testing Async Views](#testing-async-views)
- [Testing Async ORM](#testing-async-orm)
- [AsyncClient](#asyncclient)
- [Testing Background Tasks](#testing-background-tasks)
- [Common Patterns](#common-patterns)
- [Troubleshooting](#troubleshooting)

## Overview

**Django 4.1+ Features:**
- ✅ Async views (`async def` view functions)
- ✅ Async ORM operations
- ✅ Async test methods
- ✅ AsyncClient for testing async views
- ✅ Async middleware support

**When to Write Async Tests:**
- Testing async views
- Testing async ORM operations
- Testing async middleware
- Testing WebSocket handlers
- Testing async third-party integrations

## Async Test Methods

### Basic Async Test

```python
from django.test import TestCase
from myapp.models import Article

class AsyncArticleTests(TestCase):
    async def test_async_article_creation(self):
        """Test async database operation"""
        # Use async ORM operations
        article = await Article.objects.acreate(
            title='Async Test Article',
            content='Created asynchronously'
        )

        self.assertEqual(article.title, 'Async Test Article')

        # Async query
        count = await Article.objects.acount()
        self.assertEqual(count, 1)

        # Async get
        fetched = await Article.objects.aget(pk=article.pk)
        self.assertEqual(fetched.title, 'Async Test Article')
```

### Mixing Sync and Async Tests

```python
class MixedTests(TestCase):
    def test_sync_operation(self):
        """Regular synchronous test"""
        article = Article.objects.create(title='Sync Article')
        self.assertEqual(article.title, 'Sync Article')

    async def test_async_operation(self):
        """Async test in same class"""
        article = await Article.objects.acreate(title='Async Article')
        self.assertEqual(article.title, 'Async Article')

    @classmethod
    def setUpTestData(cls):
        """setUpTestData is always sync"""
        cls.test_data = Article.objects.create(title='Setup Data')

    async def test_use_setup_data(self):
        """Access sync setup data in async test"""
        # Fetch asynchronously
        article = await Article.objects.aget(pk=self.test_data.pk)
        self.assertEqual(article.title, 'Setup Data')
```

## Testing Async Views

### Async Function-Based Views

```python
# views.py
from django.http import JsonResponse
from myapp.models import Article

async def article_list(request):
    """Async view that fetches articles"""
    articles = []
    async for article in Article.objects.filter(published=True):
        articles.append({
            'id': article.id,
            'title': article.title
        })

    return JsonResponse({'articles': articles})

# tests.py
from django.test import TestCase

class AsyncViewTests(TestCase):
    async def test_async_article_list(self):
        """Test async view"""
        # Create test data
        await Article.objects.acreate(title='Article 1', published=True)
        await Article.objects.acreate(title='Article 2', published=True)
        await Article.objects.acreate(title='Draft', published=False)

        # Use regular client - Django handles async views
        response = await self.async_client.get('/articles/')

        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(len(data['articles']), 2)
        self.assertEqual(data['articles'][0]['title'], 'Article 1')
```

### Async Class-Based Views

```python
# views.py
from django.views import View
from django.http import JsonResponse
from asgiref.sync import sync_to_async

class AsyncArticleDetailView(View):
    async def get(self, request, pk):
        """Async CBV"""
        try:
            article = await Article.objects.aget(pk=pk)
            return JsonResponse({
                'id': article.id,
                'title': article.title,
                'content': article.content
            })
        except Article.DoesNotExist:
            return JsonResponse({'error': 'Not found'}, status=404)

# tests.py
class AsyncCBVTests(TestCase):
    async def test_async_detail_view(self):
        """Test async class-based view"""
        article = await Article.objects.acreate(
            title='Test Article',
            content='Test content'
        )

        response = await self.async_client.get(f'/articles/{article.pk}/')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['title'], 'Test Article')

    async def test_async_detail_not_found(self):
        """Test 404 handling in async view"""
        response = await self.async_client.get('/articles/999/')

        self.assertEqual(response.status_code, 404)
        self.assertIn('error', response.json())
```

## Testing Async ORM

### Async QuerySet Operations

```python
from django.test import TestCase

class AsyncORMTests(TestCase):
    async def test_async_create(self):
        """Test acreate()"""
        article = await Article.objects.acreate(
            title='Async Created',
            content='Content'
        )
        self.assertIsNotNone(article.pk)

    async def test_async_get(self):
        """Test aget()"""
        article = await Article.objects.acreate(title='Test')

        fetched = await Article.objects.aget(pk=article.pk)
        self.assertEqual(fetched.title, 'Test')

        # Test DoesNotExist
        with self.assertRaises(Article.DoesNotExist):
            await Article.objects.aget(pk=999)

    async def test_async_filter(self):
        """Test async iteration"""
        await Article.objects.acreate(title='Article 1', published=True)
        await Article.objects.acreate(title='Article 2', published=True)
        await Article.objects.acreate(title='Draft', published=False)

        # Async iteration
        published = []
        async for article in Article.objects.filter(published=True):
            published.append(article.title)

        self.assertEqual(len(published), 2)
        self.assertIn('Article 1', published)

    async def test_async_count(self):
        """Test acount()"""
        await Article.objects.acreate(title='Test 1')
        await Article.objects.acreate(title='Test 2')

        count = await Article.objects.acount()
        self.assertEqual(count, 2)

    async def test_async_exists(self):
        """Test aexists()"""
        article = await Article.objects.acreate(title='Test')

        exists = await Article.objects.filter(pk=article.pk).aexists()
        self.assertTrue(exists)

        not_exists = await Article.objects.filter(pk=999).aexists()
        self.assertFalse(not_exists)

    async def test_async_update(self):
        """Test aupdate()"""
        article = await Article.objects.acreate(title='Original')

        await Article.objects.filter(pk=article.pk).aupdate(
            title='Updated'
        )

        # Refresh from database
        await article.arefresh_from_db()
        self.assertEqual(article.title, 'Updated')

    async def test_async_delete(self):
        """Test adelete()"""
        article = await Article.objects.acreate(title='To Delete')
        article_pk = article.pk

        await article.adelete()

        exists = await Article.objects.filter(pk=article_pk).aexists()
        self.assertFalse(exists)

    async def test_async_bulk_create(self):
        """Test abulk_create()"""
        articles = [
            Article(title=f'Article {i}')
            for i in range(5)
        ]

        created = await Article.objects.abulk_create(articles)

        self.assertEqual(len(created), 5)
        count = await Article.objects.acount()
        self.assertEqual(count, 5)
```

### Async Related Objects

```python
class AsyncRelatedTests(TestCase):
    async def test_async_foreign_key(self):
        """Test async access to foreign key"""
        user = await User.objects.acreate_user('testuser')
        article = await Article.objects.acreate(
            title='Test',
            author=user
        )

        # Async get related object
        fetched = await Article.objects.select_related('author').aget(
            pk=article.pk
        )
        author = await sync_to_async(lambda: fetched.author)()
        self.assertEqual(author.username, 'testuser')

    async def test_async_reverse_relation(self):
        """Test async access to reverse relations"""
        user = await User.objects.acreate_user('testuser')
        await Article.objects.acreate(title='Article 1', author=user)
        await Article.objects.acreate(title='Article 2', author=user)

        # Get user with articles
        user = await User.objects.prefetch_related('articles').aget(
            pk=user.pk
        )

        articles = []
        async for article in user.articles.all():
            articles.append(article)

        self.assertEqual(len(articles), 2)
```

## AsyncClient

### Basic AsyncClient Usage

```python
from django.test import TestCase

class AsyncClientTests(TestCase):
    async def test_get_request(self):
        """Test GET request with AsyncClient"""
        await Article.objects.acreate(title='Test')

        response = await self.async_client.get('/articles/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test')

    async def test_post_request(self):
        """Test POST request with AsyncClient"""
        user = await User.objects.acreate_user('user', password='pass')

        # Login
        logged_in = await self.async_client.login(
            username='user',
            password='pass'
        )
        self.assertTrue(logged_in)

        # Create article
        response = await self.async_client.post('/articles/create/', {
            'title': 'New Article',
            'content': 'Content here'
        })

        self.assertEqual(response.status_code, 302)

        # Verify created
        exists = await Article.objects.filter(
            title='New Article'
        ).aexists()
        self.assertTrue(exists)

    async def test_json_request(self):
        """Test JSON API request"""
        response = await self.async_client.post(
            '/api/articles/',
            data={'title': 'API Article', 'content': 'Content'},
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data['title'], 'API Article')
```

### AsyncClient with Authentication

```python
class AsyncAuthTests(TestCase):
    async def test_force_login(self):
        """Test force_login with AsyncClient"""
        user = await User.objects.acreate_user('testuser')

        await self.async_client.force_login(user)

        response = await self.async_client.get('/profile/')
        self.assertEqual(response.status_code, 200)

    async def test_login_required(self):
        """Test login required decorator with async"""
        # Without login
        response = await self.async_client.get('/profile/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

        # With login
        user = await User.objects.acreate_user('user', password='pass')
        await self.async_client.force_login(user)

        response = await self.async_client.get('/profile/')
        self.assertEqual(response.status_code, 200)

    async def test_logout(self):
        """Test logout with AsyncClient"""
        user = await User.objects.acreate_user('user')
        await self.async_client.force_login(user)

        # User is logged in
        response = await self.async_client.get('/profile/')
        self.assertEqual(response.status_code, 200)

        # Logout
        await self.async_client.logout()

        # User is logged out
        response = await self.async_client.get('/profile/')
        self.assertEqual(response.status_code, 302)
```

## Testing Background Tasks

### Testing Async Celery Tasks

```python
from unittest.mock import patch, AsyncMock

class AsyncCeleryTests(TestCase):
    @patch('myapp.tasks.send_email_async.delay')
    async def test_async_task_queued(self, mock_task):
        """Test async Celery task is queued"""
        article = await Article.objects.acreate(title='Test')

        await notify_subscribers_async(article.id)

        mock_task.assert_called_once_with(article.id)

    async def test_async_task_execution(self):
        """Test async task execution directly"""
        article = await Article.objects.acreate(title='Test')

        # Call task directly (not via Celery)
        result = await send_notification_async(article.id)

        self.assertTrue(result.success)
```

### Testing Async External Calls

```python
from unittest.mock import patch, AsyncMock

class AsyncExternalAPITests(TestCase):
    @patch('myapp.services.httpx.AsyncClient')
    async def test_async_api_call(self, mock_client):
        """Test async HTTP client"""
        # Configure async mock
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'data': 'test'}

        mock_instance = AsyncMock()
        mock_instance.get.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_instance

        # Make async API call
        result = await fetch_external_data('https://api.example.com/data')

        self.assertEqual(result['data'], 'test')
        mock_instance.get.assert_called_once()
```

## Common Patterns

### Pattern 1: Testing Async Model Methods

```python
# models.py
class Article(models.Model):
    title = models.CharField(max_length=200)
    views = models.IntegerField(default=0)

    async def increment_views(self):
        """Async method to increment views"""
        self.views += 1
        await self.asave(update_fields=['views'])

    async def get_related_articles(self):
        """Async method to fetch related articles"""
        related = []
        async for article in Article.objects.filter(
            category=self.category
        ).exclude(pk=self.pk)[:5]:
            related.append(article)
        return related

# tests.py
class AsyncModelMethodTests(TestCase):
    async def test_increment_views(self):
        """Test async model method"""
        article = await Article.objects.acreate(title='Test', views=0)

        await article.increment_views()

        await article.arefresh_from_db()
        self.assertEqual(article.views, 1)

    async def test_get_related_articles(self):
        """Test async query method"""
        category = await Category.objects.acreate(name='Tech')

        article1 = await Article.objects.acreate(
            title='Article 1',
            category=category
        )

        for i in range(3):
            await Article.objects.acreate(
                title=f'Related {i}',
                category=category
            )

        related = await article1.get_related_articles()
        self.assertEqual(len(related), 3)
```

### Pattern 2: Testing Async Middleware

```python
# middleware.py
class AsyncLoggingMiddleware:
    async def __call__(self, request):
        # Async pre-processing
        await log_request_async(request)

        response = await self.get_response(request)

        # Async post-processing
        await log_response_async(response)

        return response

# tests.py
from unittest.mock import AsyncMock, patch

class AsyncMiddlewareTests(TestCase):
    @patch('myapp.middleware.log_request_async')
    @patch('myapp.middleware.log_response_async')
    async def test_async_middleware(self, mock_log_response, mock_log_request):
        """Test async middleware"""
        mock_log_request.return_value = None
        mock_log_response.return_value = None

        response = await self.async_client.get('/test/')

        self.assertEqual(response.status_code, 200)
        mock_log_request.assert_called_once()
        mock_log_response.assert_called_once()
```

### Pattern 3: Testing Async Transactions

```python
from django.db import transaction

class AsyncTransactionTests(TestCase):
    async def test_async_atomic_success(self):
        """Test successful async transaction"""
        async with transaction.atomic():
            article = await Article.objects.acreate(title='Test')
            await Comment.objects.acreate(
                article=article,
                text='Comment'
            )

        # Both objects should exist
        article_exists = await Article.objects.aexists()
        comment_exists = await Comment.objects.aexists()
        self.assertTrue(article_exists)
        self.assertTrue(comment_exists)

    async def test_async_atomic_rollback(self):
        """Test async transaction rollback"""
        try:
            async with transaction.atomic():
                article = await Article.objects.acreate(title='Test')
                # Simulate error
                raise ValueError("Simulated error")
        except ValueError:
            pass

        # Article should be rolled back
        exists = await Article.objects.aexists()
        self.assertFalse(exists)
```

### Pattern 4: Testing Async Signals

```python
from django.db.models.signals import post_save
from django.dispatch import receiver
from asgiref.sync import sync_to_async

# signals.py
@receiver(post_save, sender=Article)
def article_post_save(sender, instance, created, **kwargs):
    """Sync signal handler"""
    if created:
        # Queue async task
        notify_subscribers.delay(instance.id)

# tests.py
class AsyncSignalTests(TestCase):
    @patch('myapp.tasks.notify_subscribers.delay')
    async def test_signal_triggers_async_task(self, mock_task):
        """Test signal triggers async task"""
        article = await Article.objects.acreate(title='Test')

        # Give signal time to fire
        import asyncio
        await asyncio.sleep(0.1)

        mock_task.assert_called_once_with(article.id)
```

## Troubleshooting

### Issue: "SynchronousOnlyOperation" Error

**Problem:** Calling sync code from async context without proper wrapping.

```python
# ❌ WRONG
async def test_bad(self):
    article = Article.objects.create(title='Test')  # Error!

# ✅ CORRECT
async def test_good(self):
    article = await Article.objects.acreate(title='Test')

# ✅ CORRECT: Wrap sync code if needed
from asgiref.sync import sync_to_async

async def test_wrapped(self):
    article = await sync_to_async(
        Article.objects.create
    )(title='Test')
```

### Issue: Mixing Async and Sync QuerySets

**Problem:** Using sync methods on async querysets.

```python
# ❌ WRONG
async def test_bad(self):
    articles = Article.objects.filter(published=True)
    for article in articles:  # Error! Can't iterate sync in async
        print(article)

# ✅ CORRECT
async def test_good(self):
    async for article in Article.objects.filter(published=True):
        print(article)

# OR convert to list first
async def test_also_good(self):
    articles = await sync_to_async(list)(
        Article.objects.filter(published=True)
    )
    for article in articles:
        print(article)
```

### Issue: TestCase vs Async Tests

**Problem:** Using TransactionTestCase features with async tests.

```python
# ✅ CORRECT: Use TestCase for async tests
class AsyncTests(TestCase):  # Good
    async def test_something(self):
        pass

# ⚠️ CAUTION: TransactionTestCase with async
class AsyncTransactionTests(TransactionTestCase):  # Slower
    async def test_something(self):
        pass  # Works but much slower
```

### Issue: Database Access in Async Code

**Problem:** Forgetting that database operations need async versions.

```python
# ❌ WRONG
async def test_bad(self):
    article = await Article.objects.acreate(title='Test')
    count = Article.objects.count()  # Error! Sync in async

# ✅ CORRECT
async def test_good(self):
    article = await Article.objects.acreate(title='Test')
    count = await Article.objects.acount()  # Async version
```

## Performance Considerations

### When to Use Async Tests

**Use Async When:**
- Testing async views
- Testing async ORM operations
- Testing concurrent operations
- Integrating with async libraries (httpx, aiohttp)

**Use Sync When:**
- Testing simple models
- Testing forms
- Testing standard views
- Performance isn't critical

### Async vs Sync Performance

```python
import time

class PerformanceTests(TestCase):
    def test_sync_creates(self):
        """Sync test - sequential"""
        start = time.time()
        for i in range(100):
            Article.objects.create(title=f'Article {i}')
        duration = time.time() - start
        print(f"Sync: {duration:.2f}s")

    async def test_async_creates(self):
        """Async test - but still sequential in DB"""
        start = time.time()
        for i in range(100):
            await Article.objects.acreate(title=f'Article {i}')
        duration = time.time() - start
        print(f"Async: {duration:.2f}s")

    async def test_concurrent_creates(self):
        """Truly concurrent with gather"""
        import asyncio
        start = time.time()

        await asyncio.gather(*[
            Article.objects.acreate(title=f'Article {i}')
            for i in range(100)
        ])

        duration = time.time() - start
        print(f"Concurrent: {duration:.2f}s")  # Faster!
```

## Summary

**Key Points:**
- Use `async def test_*` for async tests
- Use `await` with async ORM operations (`acreate`, `aget`, `acount`, etc.)
- Use `self.async_client` for async views
- Mix sync and async tests in the same TestCase
- Use `sync_to_async` to wrap sync code in async context
- Use `AsyncMock` for mocking async functions

**Common Async ORM Operations:**
- `acreate()` - Create object
- `aget()` - Get single object
- `acount()` - Count objects
- `aexists()` - Check existence
- `aupdate()` - Update objects
- `adelete()` - Delete object
- `async for` - Iterate queryset
- `arefresh_from_db()` - Refresh instance

**Remember:** Not everything needs to be async. Use async tests when testing async code or when concurrency matters!
