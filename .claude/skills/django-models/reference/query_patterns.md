# Django Query Patterns Reference

Advanced QuerySet patterns and optimization techniques for Django ORM.

## Table of Contents

- [select_related vs prefetch_related](#select_related-vs-prefetch_related)
- [Annotate and Aggregate](#annotate-and-aggregate)
- [F and Q Objects](#f-and-q-objects)
- [Subqueries](#subqueries)
- [Window Functions](#window-functions)
- [Conditional Expressions](#conditional-expressions)
- [Raw SQL and Custom Queries](#raw-sql-and-custom-queries)
- [Query Optimization Patterns](#query-optimization-patterns)

## select_related vs prefetch_related

### select_related (SQL JOIN)

**Use for:** Forward ForeignKey and OneToOne relationships
**How it works:** Creates SQL JOIN, returns objects in single query

```python
# Without select_related: N+1 queries
articles = Article.objects.all()  # 1 query
for article in articles:
    print(article.author.name)  # N queries (one per article)

# With select_related: 1 query with JOIN
articles = Article.objects.select_related('author')
for article in articles:
    print(article.author.name)  # No extra queries

# SQL generated:
# SELECT article.*, author.*
# FROM article
# INNER JOIN author ON article.author_id = author.id
```

**Multiple relationships:**
```python
# Chain relationships with double underscore
articles = Article.objects.select_related('author__profile')
# Now you can access article.author.profile without extra queries

# Multiple relationships
articles = Article.objects.select_related('author', 'category')
```

**When NOT to use:**
- ManyToMany relationships (use prefetch_related)
- Reverse ForeignKey (use prefetch_related)
- When you don't need the related data

### prefetch_related (Separate Queries + Python JOIN)

**Use for:** Reverse ForeignKey, ManyToMany, and multiple relationships
**How it works:** Separate queries, joins in Python with IN clause

```python
# Without prefetch_related: N+1 queries
articles = Article.objects.all()  # 1 query
for article in articles:
    tags = article.tags.all()  # N queries

# With prefetch_related: 2 queries
articles = Article.objects.prefetch_related('tags')
# Query 1: SELECT * FROM article
# Query 2: SELECT * FROM tag WHERE id IN (tag_ids)
for article in articles:
    tags = article.tags.all()  # No extra queries (cached)
```

**Complex prefetching:**
```python
from django.db.models import Prefetch

# Custom queryset for prefetch
articles = Article.objects.prefetch_related(
    Prefetch(
        'comments',
        queryset=Comment.objects.filter(approved=True).select_related('author')
    )
)

# Multiple levels
articles = Article.objects.prefetch_related('tags__category')

# Combining select_related and prefetch_related
articles = Article.objects.select_related('author').prefetch_related('tags')
```

**Prefetching with filters:**
```python
# Get articles with their published comments only
articles = Article.objects.prefetch_related(
    Prefetch(
        'comments',
        queryset=Comment.objects.filter(status='published'),
        to_attr='published_comments'
    )
)

# Access: article.published_comments (not article.comments)
for article in articles:
    for comment in article.published_comments:
        print(comment.text)
```

### Decision Matrix

| Relationship Type | Method | Why |
|------------------|--------|-----|
| ForeignKey (forward) | `select_related` | Single JOIN query |
| OneToOneField | `select_related` | Single JOIN query |
| ManyToManyField | `prefetch_related` | JOIN would duplicate rows |
| Reverse ForeignKey | `prefetch_related` | Multiple related objects |
| GenericRelation | `prefetch_related` | Multiple related objects |

## Annotate and Aggregate

### Annotate (Add Calculated Fields)

**Annotate:** Add calculated fields to each object in queryset

```python
from django.db.models import Count, Avg, Sum, Max, Min, F

# Count related objects
authors = Author.objects.annotate(
    book_count=Count('books')
)
for author in authors:
    print(f"{author.name}: {author.book_count} books")

# Filter on annotation
popular_authors = Author.objects.annotate(
    book_count=Count('books')
).filter(book_count__gte=5)

# Multiple annotations
articles = Article.objects.annotate(
    comment_count=Count('comments'),
    avg_rating=Avg('ratings__score'),
    total_views=Sum('views')
)
```

**Annotate with calculations:**
```python
from django.db.models import ExpressionWrapper, DecimalField

# Calculate field from other fields
products = Product.objects.annotate(
    price_with_tax=ExpressionWrapper(
        F('price') * 1.1,
        output_field=DecimalField(max_digits=10, decimal_places=2)
    )
)
```

**Annotate with conditional aggregation:**
```python
from django.db.models import Case, When, IntegerField

# Count only certain related objects
articles = Article.objects.annotate(
    approved_comments=Count(
        'comments',
        filter=Q(comments__approved=True)
    ),
    pending_comments=Count(
        'comments',
        filter=Q(comments__approved=False)
    )
)
```

### Aggregate (Calculate Across Entire QuerySet)

**Aggregate:** Calculate single value across queryset

```python
from django.db.models import Count, Avg, Sum, Max, Min

# Returns dict, not queryset
stats = Article.objects.aggregate(
    total=Count('id'),
    avg_views=Avg('views'),
    total_views=Sum('views'),
    max_views=Max('views'),
    min_views=Min('views')
)
# {'total': 100, 'avg_views': 523.4, ...}

# Aggregate with filters
published_stats = Article.objects.filter(
    status='published'
).aggregate(
    total=Count('id'),
    avg_views=Avg('views')
)
```

**Conditional aggregation:**
```python
# Count different categories
stats = Article.objects.aggregate(
    total=Count('id'),
    published=Count('id', filter=Q(status='published')),
    draft=Count('id', filter=Q(status='draft'))
)
```

### Annotate vs Aggregate

```python
# Annotate: Adds field to each object (returns QuerySet)
authors = Author.objects.annotate(book_count=Count('books'))
# Can still filter, order, etc.
authors.filter(book_count__gt=5).order_by('-book_count')

# Aggregate: Single result across all objects (returns dict)
result = Author.objects.aggregate(
    total_authors=Count('id'),
    avg_books=Avg('book_count')
)
# {'total_authors': 42, 'avg_books': 3.5}
```

## F and Q Objects

### F Objects (Field References)

**Use for:** Reference model fields in queries and updates

```python
from django.db.models import F

# Compare two fields
Article.objects.filter(views__gt=F('likes'))

# Arithmetic operations
Article.objects.filter(updated_at__gt=F('created_at') + timedelta(days=7))

# Update based on current value (atomic, no race conditions)
Article.objects.filter(pk=article_id).update(views=F('views') + 1)

# Annotation with F objects
from django.db.models import ExpressionWrapper, IntegerField

Article.objects.annotate(
    popularity=ExpressionWrapper(
        F('views') + F('likes') * 2,
        output_field=IntegerField()
    )
).order_by('-popularity')
```

**F object with relationships:**
```python
# Compare across relationships
Article.objects.filter(author__age__gt=F('reviewer__age'))

# Order by related field
Article.objects.order_by(F('author__name').asc(nulls_last=True))
```

### Q Objects (Complex Lookups)

**Use for:** OR conditions, NOT conditions, complex logic

```python
from django.db.models import Q

# OR conditions
Article.objects.filter(
    Q(status='published') | Q(status='archived')
)

# AND conditions (same as multiple filter())
Article.objects.filter(
    Q(status='published') & Q(featured=True)
)

# NOT conditions
Article.objects.filter(~Q(status='draft'))

# Complex nested logic
Article.objects.filter(
    Q(status='published') &
    (Q(featured=True) | Q(views__gte=1000))
)
# SQL: WHERE status='published' AND (featured=true OR views >= 1000)
```

**Dynamic Q object construction:**
```python
# Build query dynamically
filters = Q()

if title:
    filters &= Q(title__icontains=title)

if author_name:
    filters &= Q(author__name__icontains=author_name)

if tags:
    filters &= Q(tags__name__in=tags)

articles = Article.objects.filter(filters)
```

**Q objects with annotations:**
```python
from django.db.models import Count

# Filter on annotation with complex logic
Article.objects.annotate(
    comment_count=Count('comments')
).filter(
    Q(comment_count__gte=10) | Q(featured=True)
)
```

## Subqueries

### Subquery Expression

**Use for:** Complex filtering based on related data

```python
from django.db.models import Subquery, OuterRef, Exists

# Get latest comment for each article
from django.db.models.functions import Coalesce

latest_comment = Comment.objects.filter(
    article=OuterRef('pk')
).order_by('-created_at')

articles = Article.objects.annotate(
    latest_comment_text=Subquery(
        latest_comment.values('text')[:1]
    ),
    latest_comment_date=Subquery(
        latest_comment.values('created_at')[:1]
    )
)
```

**Exists for filtering:**
```python
# Get articles that have at least one approved comment
has_approved = Comment.objects.filter(
    article=OuterRef('pk'),
    approved=True
)

articles = Article.objects.annotate(
    has_approved_comments=Exists(has_approved)
).filter(has_approved_comments=True)

# More efficient than:
# Article.objects.filter(comments__approved=True).distinct()
```

**Subquery with aggregation:**
```python
from django.db.models import Count, Sum

# Get total comment count per article
comment_count = Comment.objects.filter(
    article=OuterRef('pk')
).values('article').annotate(
    count=Count('id')
).values('count')

articles = Article.objects.annotate(
    comment_count=Coalesce(Subquery(comment_count), 0)
)
```

**Complex subquery example:**
```python
# Get articles with more comments than average
avg_comments = Article.objects.annotate(
    comment_count=Count('comments')
).aggregate(avg=Avg('comment_count'))['avg']

above_average = Article.objects.annotate(
    comment_count=Count('comments')
).filter(comment_count__gt=avg_comments)

# Or using subquery:
from django.db.models import Avg

articles = Article.objects.annotate(
    comment_count=Count('comments')
).filter(
    comment_count__gt=Subquery(
        Article.objects.aggregate(avg=Avg('comment_count')).values()
    )
)
```

## Window Functions

**Use for:** Calculations across related rows (Django 2.0+)

```python
from django.db.models import F, Window
from django.db.models.functions import RowNumber, Rank, DenseRank

# Row number partitioned by category
articles = Article.objects.annotate(
    row_number=Window(
        expression=RowNumber(),
        partition_by=[F('category')],
        order_by=F('created_at').desc()
    )
)
```

**Ranking:**
```python
from django.db.models.functions import Rank

# Rank articles by views within each category
articles = Article.objects.annotate(
    rank=Window(
        expression=Rank(),
        partition_by=[F('category')],
        order_by=F('views').desc()
    )
)

# Get top 3 per category
top_articles = Article.objects.annotate(
    rank=Window(
        expression=Rank(),
        partition_by=[F('category')],
        order_by=F('views').desc()
    )
).filter(rank__lte=3)
```

**Running totals:**
```python
from django.db.models.functions import Sum

# Running total of sales
orders = Order.objects.annotate(
    running_total=Window(
        expression=Sum('amount'),
        order_by=F('created_at').asc()
    )
)
```

**Lead and Lag (access adjacent rows):**
```python
from django.db.models.functions import Lead, Lag

# Get previous and next article
articles = Article.objects.annotate(
    prev_title=Window(
        expression=Lag('title'),
        order_by=F('created_at').asc()
    ),
    next_title=Window(
        expression=Lead('title'),
        order_by=F('created_at').asc()
    )
)
```

## Conditional Expressions

### Case/When

**Use for:** Conditional logic in queries

```python
from django.db.models import Case, When, Value, CharField

# Simple case
articles = Article.objects.annotate(
    status_display=Case(
        When(status='draft', then=Value('Draft')),
        When(status='published', then=Value('Published')),
        When(status='archived', then=Value('Archived')),
        default=Value('Unknown'),
        output_field=CharField()
    )
)

# Case with filters
articles = Article.objects.annotate(
    priority=Case(
        When(featured=True, then=Value(1)),
        When(views__gte=1000, then=Value(2)),
        When(status='published', then=Value(3)),
        default=Value(4),
        output_field=IntegerField()
    )
).order_by('priority')
```

**Case with aggregation:**
```python
from django.db.models import Sum, IntegerField

# Conditional sum
result = Order.objects.aggregate(
    total_paid=Sum(
        Case(
            When(status='paid', then=F('amount')),
            default=Value(0),
            output_field=DecimalField()
        )
    ),
    total_pending=Sum(
        Case(
            When(status='pending', then=F('amount')),
            default=Value(0),
            output_field=DecimalField()
        )
    )
)
```

### Conditional Updates

```python
from django.db.models import Case, When, F

# Update with conditions
Article.objects.update(
    priority=Case(
        When(featured=True, then=Value(1)),
        When(views__gte=1000, then=Value(2)),
        default=F('priority'),
        output_field=IntegerField()
    )
)
```

## Raw SQL and Custom Queries

### raw() Method

**Use for:** Custom SELECT queries

```python
# Basic raw query
articles = Article.objects.raw(
    'SELECT * FROM myapp_article WHERE views > %s',
    [1000]
)

for article in articles:
    print(article.title)  # Returns Article objects

# Map to different fields
articles = Article.objects.raw(
    'SELECT id, title AS headline FROM myapp_article'
)
# article.headline works

# With annotations
articles = Article.objects.raw('''
    SELECT a.*, COUNT(c.id) as comment_count
    FROM myapp_article a
    LEFT JOIN myapp_comment c ON c.article_id = a.id
    GROUP BY a.id
''')
# article.comment_count available
```

### extra() Method (Deprecated - Use annotations instead)

```python
# Avoid extra() - use annotate instead
# Old way:
articles = Article.objects.extra(
    select={'is_recent': "published_date > '2024-01-01'"}
)

# New way:
from django.db.models import Q, Value, BooleanField, Case, When

articles = Article.objects.annotate(
    is_recent=Case(
        When(published_date__gt='2024-01-01', then=Value(True)),
        default=Value(False),
        output_field=BooleanField()
    )
)
```

### Direct SQL with cursor

**Use for:** Non-SELECT queries or very complex queries

```python
from django.db import connection

with connection.cursor() as cursor:
    # Parameterized query (safe)
    cursor.execute(
        "UPDATE myapp_article SET views = views + 1 WHERE id = %s",
        [article_id]
    )

    # Fetch results
    cursor.execute("SELECT * FROM myapp_article WHERE views > %s", [1000])
    rows = cursor.fetchall()

    # Named cursor (PostgreSQL)
    cursor.execute(
        "SELECT %(field)s FROM myapp_article WHERE id = %(id)s",
        {'field': 'title', 'id': 1}
    )
```

**Never do this (SQL injection):**
```python
# DANGEROUS - SQL INJECTION
cursor.execute(f"SELECT * FROM article WHERE title = '{user_input}'")

# SAFE - Parameterized
cursor.execute("SELECT * FROM article WHERE title = %s", [user_input])
```

## Query Optimization Patterns

### Only/Defer (Select Specific Fields)

```python
# Only load specific fields
articles = Article.objects.only('id', 'title', 'status')
# Accessing other fields causes additional query

# Defer specific fields (load everything except)
articles = Article.objects.defer('content', 'description')
# Good for large text fields you don't need
```

### Iterator (Memory Efficiency)

```python
# Default: Loads all results into memory
articles = Article.objects.all()

# Iterator: Fetch in batches (default chunk_size=2000)
for article in Article.objects.iterator(chunk_size=1000):
    process(article)
# Better for large datasets

# Trade-off: No result caching, can't evaluate queryset multiple times
```

### Bulk Operations

```python
# Bulk create (single INSERT with multiple rows)
articles = [
    Article(title=f'Article {i}', status='draft')
    for i in range(1000)
]
Article.objects.bulk_create(articles, batch_size=500)

# Bulk update (efficient UPDATE)
articles = Article.objects.filter(status='draft')
for article in articles:
    article.status = 'published'
Article.objects.bulk_update(articles, ['status'], batch_size=500)

# Simple update (even more efficient)
Article.objects.filter(status='draft').update(status='published')
```

### Database Functions

```python
from django.db.models.functions import (
    Lower, Upper, Length, Concat, Substr,
    Now, TruncDate, ExtractYear
)

# String functions
articles = Article.objects.annotate(
    title_lower=Lower('title'),
    title_length=Length('title')
)

# Date functions
from django.db.models.functions import TruncDate, ExtractYear

articles = Article.objects.annotate(
    publish_date_only=TruncDate('published_at'),
    publish_year=ExtractYear('published_at')
)

# Concatenation
authors = Author.objects.annotate(
    full_name=Concat('first_name', Value(' '), 'last_name')
)
```

### Query Debugging

```python
# Print SQL
print(Article.objects.filter(status='published').query)

# Count queries
from django.db import connection, reset_queries
from django.conf import settings

settings.DEBUG = True
reset_queries()

# Your code here
articles = Article.objects.select_related('author').all()
for article in articles:
    print(article.title)

print(f"Total queries: {len(connection.queries)}")
for query in connection.queries:
    print(query['sql'])

# Explain query (PostgreSQL, MySQL 8+, SQLite 3.24+)
print(Article.objects.filter(status='published').explain())

# Analyze query performance
print(Article.objects.filter(status='published').explain(analyze=True))
```

### Indexes for Query Optimization

```python
class Article(models.Model):
    title = models.CharField(max_length=200)
    status = models.CharField(max_length=20, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Single field index
        indexes = [
            models.Index(fields=['status']),
            # Compound index
            models.Index(fields=['status', '-created_at']),
            # Partial index (PostgreSQL)
            models.Index(
                fields=['created_at'],
                name='published_created_idx',
                condition=Q(status='published')
            ),
        ]
```

### Common Query Optimization Checklist

1. **Use select_related() for ForeignKey/OneToOne**
   ```python
   # Before: N+1 queries
   articles = Article.objects.all()

   # After: 1 query
   articles = Article.objects.select_related('author')
   ```

2. **Use prefetch_related() for ManyToMany/reverse ForeignKey**
   ```python
   # Before: N+1 queries
   articles = Article.objects.all()

   # After: 2 queries
   articles = Article.objects.prefetch_related('tags')
   ```

3. **Use only()/defer() for large fields**
   ```python
   # Don't load large content field
   articles = Article.objects.defer('content')
   ```

4. **Use iterator() for large datasets**
   ```python
   # Process in batches
   for article in Article.objects.iterator(chunk_size=1000):
       process(article)
   ```

5. **Use count() instead of len()**
   ```python
   # Bad: Loads all objects
   count = len(Article.objects.all())

   # Good: Database COUNT query
   count = Article.objects.count()
   ```

6. **Use exists() instead of count() for existence checks**
   ```python
   # Bad: Counts all matching rows
   if Article.objects.filter(status='published').count() > 0:
       pass

   # Good: Stops at first match
   if Article.objects.filter(status='published').exists():
       pass
   ```

7. **Use bulk operations**
   ```python
   # Bad: N queries
   for article in articles:
       article.views += 1
       article.save()

   # Good: 1 query
   Article.objects.filter(id__in=article_ids).update(views=F('views') + 1)
   ```

8. **Avoid queries in loops**
   ```python
   # Bad: N queries in loop
   for author in authors:
       book_count = author.books.count()

   # Good: Single query with annotation
   authors = Author.objects.annotate(book_count=Count('books'))
   ```

## Performance Testing Queries

```python
from django.test import TestCase
from django.test.utils import override_settings
from django.db import connection, reset_queries

class QueryPerformanceTest(TestCase):
    def test_article_list_queries(self):
        with override_settings(DEBUG=True):
            reset_queries()

            # Your query
            articles = Article.objects.select_related('author').prefetch_related('tags')
            list(articles)  # Force evaluation

            # Assert query count
            self.assertLess(
                len(connection.queries),
                5,
                f"Too many queries: {len(connection.queries)}"
            )

            # Print queries for debugging
            for query in connection.queries:
                print(query['sql'])
```
