# Django Models & ORM Skill

## Overview

This skill helps you work with Django's ORM (Object-Relational Mapping) system effectively. Use this when dealing with database models, queries, relationships, migrations, and data operations.

**When to use this skill:**
- Creating or modifying model schemas
- Optimizing database queries and preventing N+1 problems
- Working with model relationships (ForeignKey, ManyToMany, OneToOne)
- Writing efficient QuerySets and database operations
- Handling migrations and schema changes
- Using async ORM operations (Django 4.1+)
- Debugging slow queries or ORM issues

**When NOT to use this skill:**
- Simple CRUD views (use django-views instead)
- Admin customization (use django-admin instead)
- Form validation (use django-forms instead)

## Quick Start

**Most common workflow: Add a field to existing model**

1. **Add field to model** with appropriate default or null=True
2. **Generate migration** with `python manage.py makemigrations`
3. **Review and apply** migration with `python manage.py migrate`

```python
# 1. Add field to models.py
class Article(models.Model):
    title = models.CharField(max_length=200)
    status = models.CharField(max_length=20, default='draft')

# 2-3: Generate and apply migration
# $ python manage.py makemigrations
# $ python manage.py migrate
```

## Core Workflows

### Workflow 1: Add Field to Model with Existing Data

**Scenario:** Adding a non-nullable field to a model with existing data.

**Steps:**
1. Add field as nullable first
2. Create and apply schema migration
3. Create data migration to populate values
4. Make field non-nullable (if needed)

```python
# Step 1: Add nullable field
class Product(models.Model):
    name = models.CharField(max_length=200)
    category = models.ForeignKey('Category', on_delete=models.SET_NULL, null=True)

# Step 3: Data migration
def populate_category(apps, schema_editor):
    Product = apps.get_model('myapp', 'Product')
    Category = apps.get_model('myapp', 'Category')
    default = Category.objects.get_or_create(name='Uncategorized')[0]
    Product.objects.filter(category__isnull=True).update(category=default)
```

See [migration_ops.md](reference/migration_ops.md) for complete migration patterns.

### Workflow 2: Optimize Slow Query (Fix N+1 Problems)

**Scenario:** A query is slow or causing N+1 query problems.

**Steps:**
1. Detect the problem using the `analyze_queries.py` script or Django Debug Toolbar
2. Apply appropriate optimization:
   - Use `select_related()` for ForeignKey/OneToOne (single JOIN)
   - Use `prefetch_related()` for ManyToMany/reverse ForeignKey (separate queries)

```python
# Bad: N+1 queries
articles = Article.objects.all()
for article in articles:
    print(article.author.name)  # Extra query per article!

# Good: Single JOIN query with select_related
articles = Article.objects.select_related('author')
for article in articles:
    print(article.author.name)  # No extra query

# Good: Separate query with prefetch_related for ManyToMany
articles = Article.objects.prefetch_related('tags')
for article in articles:
    print([tag.name for tag in article.tags.all()])  # Cached
```

Run the analyzer:
```bash
python scripts/analyze_queries.py myapp/views.py
```

See [query_patterns.md](reference/query_patterns.md) for advanced optimization techniques.

### Workflow 3: Resolve Migration Conflicts

**Scenario:** Multiple developers created migrations on different branches.

**Steps:**
1. Identify the conflict when migration fails
2. Create a merge migration: `python manage.py makemigrations --merge`
3. Review the merge migration to ensure it's safe
4. Test on a copy of production data

```bash
python manage.py showmigrations myapp  # Check status
python manage.py makemigrations --merge  # Create merge
python manage.py migrate  # Apply
```

### Workflow 4: Create Model Relationships

**One-to-Many (ForeignKey):**
```python
class Book(models.Model):
    author = models.ForeignKey(
        Author,
        on_delete=models.CASCADE,  # Delete books when author deleted
        related_name='books'  # Access via author.books.all()
    )
```

**Many-to-Many:**
```python
class Book(models.Model):
    tags = models.ManyToManyField('Tag', related_name='books', blank=True)

# Usage: book.tags.add(tag1, tag2)
```

**One-to-One:**
```python
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')

# Usage: user.profile
```

See [field_types.md](reference/field_types.md) for complete field reference.

### Workflow 5: Async ORM Patterns

**Scenario:** Using Django's async ORM operations (Django 4.1+).

```python
import asyncio
from myapp.models import Article

async def get_articles():
    # Async QuerySet operations
    articles = await Article.objects.filter(status='published').aall()
    count = await Article.objects.acount()
    article = await Article.objects.aget(pk=1)

    # Async iteration
    async for article in Article.objects.filter(status='published'):
        print(article.title)

    # Create/update/delete (Django 5.0+)
    article = await Article.objects.acreate(title='Test', status='draft')
    await Article.objects.filter(pk=1).aupdate(status='published')
    await Article.objects.filter(pk=1).adelete()
```

**For operations without async support, use sync_to_async:**
```python
from asgiref.sync import sync_to_async

# select_related/prefetch_related not fully async yet
@sync_to_async
def get_articles_with_authors():
    return list(Article.objects.select_related('author'))

async def process():
    articles = await get_articles_with_authors()
    for article in articles:
        print(article.author.name)
```

See [async_orm.md](reference/async_orm.md) for comprehensive async patterns and limitations.

## Scripts & Tools

### analyze_queries.py

Detects N+1 query problems in your code.

```bash
python scripts/analyze_queries.py myapp/views.py
python scripts/analyze_queries.py myapp/views.py --json
```

Output:
```json
{
  "file": "myapp/views.py",
  "issues": [
    {
      "line": 42,
      "type": "n_plus_one",
      "relationship": "author",
      "recommendation": "Use select_related('author')"
    }
  ]
}
```

### generate_model.py

Generates Django model code from JSON schema.

```bash
python scripts/generate_model.py schema.json > models.py
```

Input format:
```json
{
  "model_name": "Article",
  "fields": [
    {"name": "title", "type": "CharField", "options": {"max_length": 200}},
    {"name": "author", "type": "ForeignKey", "options": {
      "to": "auth.User", "on_delete": "CASCADE", "related_name": "articles"
    }}
  ],
  "meta": {"ordering": ["-created_at"]},
  "str_field": "title"
}
```

## Common Patterns

### F() Objects for Database-Level Operations

```python
from django.db.models import F

# Atomic increment (no race conditions)
Article.objects.filter(pk=article_id).update(views=F('views') + 1)

# Compare fields
Article.objects.filter(publish_date__lt=F('updated_date'))
```

### Q() Objects for Complex Queries

```python
from django.db.models import Q

# OR conditions
Article.objects.filter(Q(status='published') | Q(status='archived'))

# Complex nested logic
Article.objects.filter(
    Q(status='published') & (Q(featured=True) | Q(views__gte=1000))
)

# NOT conditions
Article.objects.filter(~Q(status='draft'))
```

### Bulk Operations

```python
# Bulk create (single INSERT)
Article.objects.bulk_create([
    Article(title='Article 1'), Article(title='Article 2')
], batch_size=500)

# Bulk update
articles = Article.objects.filter(status='draft')
for article in articles:
    article.status = 'published'
Article.objects.bulk_update(articles, ['status'])

# Simple update (most efficient)
Article.objects.filter(status='draft').update(status='published')
```

## Anti-Patterns

### ❌ Accessing Related Objects in Loops (N+1 Queries)

```python
# BAD
for article in Article.objects.all():
    print(article.author.name)  # Query per article

# GOOD
for article in Article.objects.select_related('author'):
    print(article.author.name)  # No extra queries
```

### ❌ Using Signals for Business Logic

```python
# BAD: Hidden side effects
@receiver(post_save, sender=Article)
def notify_subscribers(sender, instance, **kwargs):
    send_notification(instance)  # Hard to test

# GOOD: Explicit in view/service
def publish_article(article):
    article.status = 'published'
    article.save()
    send_notification(article)  # Clear and testable
```

### ❌ Multi-Table Inheritance for Shared Fields

```python
# BAD: JOINs on every query
class Content(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)

class Article(Content):  # Creates JOIN
    title = models.CharField(max_length=200)

# GOOD: Abstract base class (no JOINs)
class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        abstract = True

class Article(TimestampedModel):  # No extra table
    title = models.CharField(max_length=200)
```

### ❌ Using .count() When You Need Objects

```python
# BAD: Two queries
if Article.objects.filter(status='published').count() > 0:
    articles = Article.objects.filter(status='published')

# GOOD: Use exists()
if Article.objects.filter(status='published').exists():
    articles = Article.objects.filter(status='published')
```

### ❌ Raw SQL Without Parameterization

```python
# BAD: SQL injection vulnerability
query = f"SELECT * FROM articles WHERE title = '{user_input}'"

# GOOD: Parameterized query
Article.objects.raw("SELECT * FROM articles WHERE title = %s", [user_input])
```

## Edge Cases & Gotchas

1. **auto_now and auto_now_add don't trigger on .update()**
   ```python
   # Won't update updated_at
   Article.objects.filter(pk=1).update(title='New')

   # Manual update needed
   from django.utils import timezone
   Article.objects.filter(pk=1).update(title='New', updated_at=timezone.now())
   ```

2. **QuerySets are lazy** - No database hit until evaluated
   ```python
   articles = Article.objects.filter(status='published')  # No query yet
   list(articles)  # Query happens here
   ```

3. **prefetch_related uses separate queries, not JOINs**
   ```python
   # Two queries (not one JOIN)
   articles = Article.objects.prefetch_related('tags')
   ```

4. **on_delete=SET_NULL requires null=True**
   ```python
   # Correct
   author = models.ForeignKey(Author, on_delete=models.SET_NULL, null=True)
   ```

5. **Async ORM has limited support** - As of Django 5.1:
   - `select_related/prefetch_related` need `sync_to_async`
   - ManyToMany operations need `sync_to_async`
   - See [async_orm.md](reference/async_orm.md) for details

## Related Skills

- **django-migrations**: Deep dive into migration strategies
- **django-admin**: Customize how models appear in Django admin
- **django-testing**: Test model methods, managers, and queries
- **django-performance**: Advanced query optimization and caching
- **django-signals**: When and how to use Django signals properly

## Reference Files

- [field_types.md](reference/field_types.md) - Complete guide to all Django field types with database implications
- [query_patterns.md](reference/query_patterns.md) - Advanced QuerySet patterns: annotate, aggregate, subqueries, window functions
- [async_orm.md](reference/async_orm.md) - Async ORM operations, sync_to_async usage, limitations and workarounds
- [migration_ops.md](reference/migration_ops.md) - Migration operations, data migrations, rollback strategies

## Django Version Notes

- **Django 4.1+:** Async ORM support (`aget()`, `aall()`, `acount()`, async iteration)
- **Django 4.2+:** Improved async support, async transactions
- **Django 5.0+:** `aupdate()`, `adelete()`, `abulk_create()`, `abulk_update()`
- **Django 5.1+:** `aaggregate()`, async values/values_list
