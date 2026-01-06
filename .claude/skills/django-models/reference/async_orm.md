# Django Async ORM Reference

Comprehensive guide to Django's async ORM operations (Django 4.1+).

## Table of Contents

- [Overview](#overview)
- [Available Async Methods](#available-async-methods)
- [Async QuerySet Operations](#async-queryset-operations)
- [sync_to_async Usage](#sync_to_async-usage)
- [Transaction Handling](#transaction-handling)
- [Limitations and Workarounds](#limitations-and-workarounds)
- [Performance Considerations](#performance-considerations)
- [Testing Async Code](#testing-async-code)

## Overview

Django 4.1+ provides native async ORM support for many QuerySet operations. However, not all ORM features are fully async yet.

**When to use async ORM:**
- Async views and middleware
- High-concurrency applications
- I/O-bound operations alongside database queries
- WebSocket handlers
- Background task workers using async frameworks

**When NOT to use async ORM:**
- Traditional Django views (sync is fine and simpler)
- CPU-bound operations
- When all operations are database-only (no I/O benefit)

## Available Async Methods

### Django 4.1+

```python
# Retrieving objects
await Model.objects.aget(pk=1)
await Model.objects.afirst()
await Model.objects.alast()

# Aggregation
await Model.objects.acount()
await Model.objects.aexists()

# Iteration
async for obj in Model.objects.filter(status='active'):
    print(obj)

# Creation
await Model.objects.acreate(field='value')
await Model.objects.aget_or_create(field='value')
await Model.objects.aupdate_or_create(field='value', defaults={...})
```

### Django 5.0+

```python
# Bulk operations
await Model.objects.abulk_create([obj1, obj2, obj3])
await Model.objects.abulk_update([obj1, obj2], ['field1', 'field2'])

# Updates
await Model.objects.filter(pk=1).aupdate(field='new_value')

# Deletion
await Model.objects.filter(pk=1).adelete()

# Aggregation with functions
from django.db.models import Count, Avg
result = await Model.objects.aaggregate(
    total=Count('id'),
    avg_rating=Avg('rating')
)

# In bulk (Django 5.0+)
await Model.objects.abulk_create([
    Model(title='Article 1'),
    Model(title='Article 2'),
])
```

### Django 5.1+

```python
# Async aggregation
result = await Article.objects.aaggregate(
    total=Count('id'),
    avg_views=Avg('views')
)

# Values and values_list
values = await Article.objects.values('title', 'status').alist()
flat_values = await Article.objects.values_list('title', flat=True).alist()
```

## Async QuerySet Operations

### Basic Queries

```python
from myapp.models import Article

async def get_article(article_id: int):
    """Get single article by ID"""
    try:
        article = await Article.objects.aget(pk=article_id)
        return article
    except Article.DoesNotExist:
        return None

async def get_published_articles():
    """Get all published articles"""
    articles = []
    async for article in Article.objects.filter(status='published'):
        articles.append(article)
    return articles

    # Or with alist() (Django 5.1+):
    # return await Article.objects.filter(status='published').alist()
```

### Filtering and Ordering

```python
async def get_recent_articles(limit: int = 10):
    """Get recent articles with async iteration"""
    articles = []
    query = Article.objects.filter(
        status='published'
    ).order_by('-published_at')[:limit]

    async for article in query:
        articles.append(article)

    return articles
```

### Checking Existence

```python
async def article_exists(slug: str) -> bool:
    """Check if article with slug exists"""
    return await Article.objects.filter(slug=slug).aexists()

async def get_article_count(status: str) -> int:
    """Count articles by status"""
    return await Article.objects.filter(status=status).acount()
```

### Creating Objects

```python
async def create_article(title: str, content: str, author_id: int):
    """Create new article"""
    article = await Article.objects.acreate(
        title=title,
        content=content,
        author_id=author_id,
        status='draft'
    )
    return article

async def get_or_create_tag(name: str):
    """Get or create tag"""
    tag, created = await Tag.objects.aget_or_create(
        name=name,
        defaults={'slug': slugify(name)}
    )
    return tag, created
```

### Updating Objects

```python
# Django 5.0+
async def publish_article(article_id: int):
    """Publish an article"""
    from django.utils import timezone

    updated = await Article.objects.filter(pk=article_id).aupdate(
        status='published',
        published_at=timezone.now()
    )
    return updated  # Number of rows updated

async def increment_views(article_id: int):
    """Increment view count atomically"""
    from django.db.models import F

    await Article.objects.filter(pk=article_id).aupdate(
        views=F('views') + 1
    )
```

### Deleting Objects

```python
# Django 5.0+
async def delete_article(article_id: int):
    """Delete an article"""
    deleted_count, _ = await Article.objects.filter(pk=article_id).adelete()
    return deleted_count

async def delete_old_drafts():
    """Delete drafts older than 30 days"""
    from django.utils import timezone
    from datetime import timedelta

    cutoff = timezone.now() - timedelta(days=30)
    deleted_count, _ = await Article.objects.filter(
        status='draft',
        created_at__lt=cutoff
    ).adelete()
    return deleted_count
```

## sync_to_async Usage

Use `sync_to_async` for ORM operations that don't have async equivalents.

### Basic Usage

```python
from asgiref.sync import sync_to_async

# Method 1: Decorator
@sync_to_async
def get_article_with_author(article_id: int):
    """Get article with author using select_related"""
    return Article.objects.select_related('author').get(pk=article_id)

# Usage:
article = await get_article_with_author(123)

# Method 2: Inline
async def get_article(article_id: int):
    article = await sync_to_async(
        Article.objects.select_related('author').get
    )(pk=article_id)
    return article
```

### With QuerySets

```python
@sync_to_async
def get_articles_with_tags():
    """Get articles with prefetch_related (not yet async)"""
    return list(
        Article.objects.prefetch_related('tags')
        .filter(status='published')
    )

async def process_articles():
    articles = await get_articles_with_tags()
    for article in articles:
        print(article.title, [tag.name for tag in article.tags.all()])
```

### With Related Objects

```python
from asgiref.sync import sync_to_async

async def add_tags_to_article(article_id: int, tag_names: list[str]):
    """Add tags to article (ManyToMany not fully async)"""
    # Get article
    article = await Article.objects.aget(pk=article_id)

    # Get or create tags
    tags = []
    for name in tag_names:
        tag, _ = await Tag.objects.aget_or_create(name=name)
        tags.append(tag)

    # ManyToMany operations need sync_to_async
    await sync_to_async(article.tags.set)(tags)

async def get_article_tags(article_id: int):
    """Get all tags for an article"""
    article = await Article.objects.aget(pk=article_id)

    # Access ManyToMany
    tags = await sync_to_async(list)(article.tags.all())
    return tags
```

### Thread-Safe Option

```python
# By default, sync_to_async uses thread_sensitive=True
# This keeps database connections in the same thread

@sync_to_async(thread_sensitive=True)
def database_operation():
    return Article.objects.count()

# Use thread_sensitive=False for thread-safe operations
@sync_to_async(thread_sensitive=False)
def thread_safe_operation():
    # Safe for multi-threaded access
    return some_thread_safe_function()
```

## Transaction Handling

### Async Transactions (Django 4.2+)

```python
from django.db import transaction

async def create_article_with_tags(title: str, tag_names: list[str]):
    """Create article and tags in transaction"""
    async with transaction.atomic():
        # Create article
        article = await Article.objects.acreate(
            title=title,
            status='draft'
        )

        # Create tags
        for name in tag_names:
            tag, _ = await Tag.objects.aget_or_create(name=name)
            # Note: ManyToMany operations still need sync_to_async
            await sync_to_async(article.tags.add)(tag)

        return article

async def transfer_articles(from_author_id: int, to_author_id: int):
    """Transfer all articles from one author to another"""
    async with transaction.atomic():
        count = await Article.objects.filter(
            author_id=from_author_id
        ).aupdate(author_id=to_author_id)

        # Log the transfer
        await AuditLog.objects.acreate(
            action='transfer_articles',
            count=count,
            from_author_id=from_author_id,
            to_author_id=to_author_id
        )

        return count
```

### Transaction with Savepoints

```python
async def complex_transaction():
    """Transaction with savepoints"""
    async with transaction.atomic():
        # Outer transaction
        article = await Article.objects.acreate(title='Test')

        # Create savepoint
        sid = await sync_to_async(transaction.savepoint)()

        try:
            # Operations that might fail
            await Comment.objects.acreate(
                article=article,
                text='Comment'
            )
        except Exception:
            # Rollback to savepoint
            await sync_to_async(transaction.savepoint_rollback)(sid)
        else:
            # Commit savepoint
            await sync_to_async(transaction.savepoint_commit)(sid)

        return article
```

### Error Handling

```python
from django.db import IntegrityError, transaction

async def create_article_safe(title: str, slug: str):
    """Create article with error handling"""
    try:
        async with transaction.atomic():
            article = await Article.objects.acreate(
                title=title,
                slug=slug
            )
            return article, None
    except IntegrityError as e:
        return None, str(e)
```

## Limitations and Workarounds

### Operations That Need sync_to_async

As of Django 5.1, these operations are NOT fully async:

#### 1. select_related() / prefetch_related()

```python
# Not fully async
@sync_to_async
def get_articles_with_authors():
    return list(Article.objects.select_related('author'))

async def process_articles():
    articles = await get_articles_with_authors()
    for article in articles:
        print(article.author.name)  # No extra query
```

#### 2. Aggregations with Relationships

```python
# Not fully async (Django 5.0)
@sync_to_async
def get_author_stats():
    from django.db.models import Count
    return Author.objects.annotate(
        book_count=Count('books')
    ).values('name', 'book_count')

async def display_stats():
    stats = await get_author_stats()
    for stat in stats:
        print(f"{stat['name']}: {stat['book_count']} books")
```

#### 3. ManyToMany Operations

```python
# ManyToMany add/remove/set/clear need sync_to_async
async def manage_article_tags(article_id: int, tag_ids: list[int]):
    article = await Article.objects.aget(pk=article_id)

    # Get tags
    tags = []
    async for tag in Tag.objects.filter(id__in=tag_ids):
        tags.append(tag)

    # Set tags (needs sync_to_async)
    await sync_to_async(article.tags.set)(tags)
```

#### 4. Related Object Access

```python
async def get_article_with_comments(article_id: int):
    article = await Article.objects.aget(pk=article_id)

    # Access reverse ForeignKey (needs sync_to_async)
    comments = await sync_to_async(list)(
        article.comments.filter(approved=True)
    )

    return article, comments
```

#### 5. Model Methods and Properties

```python
class Article(models.Model):
    title = models.CharField(max_length=200)

    @property
    def comment_count(self):
        # Sync property
        return self.comments.count()

    async def acomment_count(self):
        # Async version
        return await self.comments.acount()

# Usage:
async def get_stats(article_id: int):
    article = await Article.objects.aget(pk=article_id)

    # Use async version
    count = await article.acomment_count()

    # Or wrap sync property
    count = await sync_to_async(lambda: article.comment_count)()
```

### Workaround Patterns

#### Pattern 1: Pre-fetch Related Data

```python
@sync_to_async
def get_articles_with_data():
    """Fetch everything at once"""
    return list(
        Article.objects
        .select_related('author')
        .prefetch_related('tags', 'comments')
    )

async def process_articles():
    articles = await get_articles_with_data()

    # All related data is cached, no additional queries
    for article in articles:
        print(article.author.name)
        print([tag.name for tag in article.tags.all()])
        print(article.comments.count())
```

#### Pattern 2: Fetch IDs Async, Related Data Sync

```python
async def get_article_with_author(article_id: int):
    # Fetch article async
    article = await Article.objects.aget(pk=article_id)

    # Fetch author separately
    author = await Author.objects.aget(pk=article.author_id)

    # Attach to avoid additional queries
    article.author = author

    return article
```

#### Pattern 3: Batch Operations

```python
async def get_comment_counts(article_ids: list[int]):
    """Get comment counts for multiple articles efficiently"""
    @sync_to_async
    def fetch_counts():
        from django.db.models import Count
        return dict(
            Article.objects
            .filter(id__in=article_ids)
            .annotate(count=Count('comments'))
            .values_list('id', 'count')
        )

    return await fetch_counts()
```

## Performance Considerations

### Async vs Sync Performance

```python
import asyncio
from django.db import connection, reset_queries

# Async version
async def fetch_articles_async():
    articles = []
    async for article in Article.objects.filter(status='published'):
        articles.append(article)
    return articles

# Sync version
def fetch_articles_sync():
    return list(Article.objects.filter(status='published'))

# Benchmark
import time

async def benchmark():
    # Async
    start = time.time()
    articles = await fetch_articles_async()
    async_time = time.time() - start

    # Sync (wrapped)
    start = time.time()
    articles = await sync_to_async(fetch_articles_sync)()
    sync_time = time.time() - start

    print(f"Async: {async_time:.4f}s")
    print(f"Sync: {sync_time:.4f}s")
```

**Key insights:**
- Pure database operations: Async and sync have similar performance
- I/O alongside database: Async can be much faster (concurrent operations)
- Complex queries with joins: Sync might be simpler and equally fast

### When Async Helps

```python
import asyncio
import aiohttp

async def fetch_article_with_external_data(article_id: int):
    """Fetch article and external API data concurrently"""

    # Start both operations concurrently
    article_task = Article.objects.aget(pk=article_id)

    async with aiohttp.ClientSession() as session:
        api_task = session.get(f'https://api.example.com/data/{article_id}')

        # Wait for both
        article, api_response = await asyncio.gather(
            article_task,
            api_task
        )

    external_data = await api_response.json()

    return article, external_data

# This is FASTER than doing them sequentially
```

### When Sync is Better

```python
# Complex query with multiple joins and annotations
@sync_to_async
def get_dashboard_stats():
    """Complex aggregation query"""
    from django.db.models import Count, Avg, Sum

    return Author.objects.annotate(
        book_count=Count('books'),
        avg_rating=Avg('books__rating'),
        total_sales=Sum('books__sales')
    ).select_related('profile').prefetch_related('awards')

# Using sync_to_async here is simpler and not slower
# The complexity is in the database query, not Python
```

## Testing Async Code

### Test Case Setup

```python
from django.test import TestCase
from asgiref.sync import async_to_sync

class ArticleAsyncTest(TestCase):
    def test_create_article_async(self):
        """Test async article creation"""

        async def create_and_verify():
            # Create article
            article = await Article.objects.acreate(
                title='Test Article',
                status='draft'
            )

            # Verify
            self.assertEqual(article.title, 'Test Article')

            # Check in database
            count = await Article.objects.filter(
                title='Test Article'
            ).acount()
            self.assertEqual(count, 1)

        # Run async function in sync test
        async_to_sync(create_and_verify)()
```

### pytest-asyncio

```python
import pytest
from myapp.models import Article

@pytest.mark.asyncio
@pytest.mark.django_db
async def test_create_article():
    """Test async article creation with pytest"""
    article = await Article.objects.acreate(
        title='Test Article',
        status='draft'
    )

    assert article.title == 'Test Article'

    count = await Article.objects.acount()
    assert count == 1
```

### Testing with Transactions

```python
import pytest
from django.db import transaction

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_transaction_rollback():
    """Test transaction rollback"""
    try:
        async with transaction.atomic():
            await Article.objects.acreate(
                title='Test',
                status='draft'
            )
            # Force error
            raise Exception('Test error')
    except Exception:
        pass

    # Verify rollback
    count = await Article.objects.acount()
    assert count == 0
```

## Best Practices

### 1. Use Async Where It Matters

```python
# Good: I/O alongside database
async def get_article_with_cache(article_id: int):
    cache_task = get_from_cache_async(f'article:{article_id}')
    db_task = Article.objects.aget(pk=article_id)

    cached, article = await asyncio.gather(cache_task, db_task)
    return cached or article

# Not beneficial: Pure database query
async def simple_query():
    # No benefit over sync version
    return await Article.objects.filter(status='published').acount()
```

### 2. Batch Database Operations

```python
# Good: Batch operations
async def create_multiple_articles(articles_data: list[dict]):
    articles = [Article(**data) for data in articles_data]
    await Article.objects.abulk_create(articles)

# Bad: Multiple separate queries
async def create_multiple_articles_bad(articles_data: list[dict]):
    for data in articles_data:
        await Article.objects.acreate(**data)  # N queries!
```

### 3. Handle Missing Async Support Gracefully

```python
# Wrap complex queries that need prefetch_related
@sync_to_async
def get_articles_with_relations():
    return list(
        Article.objects
        .select_related('author')
        .prefetch_related('tags')
    )

async def process_articles():
    articles = await get_articles_with_relations()
    # All data is prefetched, no additional queries
    for article in articles:
        process(article, article.author, article.tags.all())
```

### 4. Use Type Hints

```python
from typing import Optional, List
from myapp.models import Article, Tag

async def get_article(article_id: int) -> Optional[Article]:
    """Get article by ID or None if not found"""
    try:
        return await Article.objects.aget(pk=article_id)
    except Article.DoesNotExist:
        return None

async def get_articles_by_tag(tag_name: str) -> List[Article]:
    """Get all articles with given tag"""
    @sync_to_async
    def fetch():
        return list(
            Article.objects.filter(tags__name=tag_name)
            .select_related('author')
        )

    return await fetch()
```

### 5. Error Handling

```python
from django.db import IntegrityError, DatabaseError
from typing import Tuple, Optional

async def safe_create_article(
    title: str,
    slug: str
) -> Tuple[Optional[Article], Optional[str]]:
    """Create article with error handling"""
    try:
        article = await Article.objects.acreate(
            title=title,
            slug=slug,
            status='draft'
        )
        return article, None
    except IntegrityError as e:
        return None, f"Duplicate slug: {slug}"
    except DatabaseError as e:
        return None, f"Database error: {str(e)}"
```
