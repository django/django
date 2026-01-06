# Django Migration Operations Reference

Comprehensive guide to Django migrations, including data migrations, schema changes, and rollback strategies.

## Table of Contents

- [Migration Basics](#migration-basics)
- [Schema Migrations](#schema-migrations)
- [Data Migrations](#data-migrations)
- [Complex Migration Patterns](#complex-migration-patterns)
- [Rollback Strategies](#rollback-strategies)
- [Migration Conflicts](#migration-conflicts)
- [Best Practices](#best-practices)

## Migration Basics

### Creating Migrations

```bash
# Auto-detect model changes
python manage.py makemigrations

# Specify app
python manage.py makemigrations myapp

# Empty migration for data migration
python manage.py makemigrations --empty myapp

# Dry run (show what would be created)
python manage.py makemigrations --dry-run

# Name the migration
python manage.py makemigrations myapp --name add_status_field
```

### Applying Migrations

```bash
# Apply all migrations
python manage.py migrate

# Apply specific app
python manage.py migrate myapp

# Apply to specific migration
python manage.py migrate myapp 0004

# Show migration status
python manage.py showmigrations

# Show SQL for migration
python manage.py sqlmigrate myapp 0001

# Check for issues
python manage.py makemigrations --check
```

### Migration Structure

```python
from django.db import migrations, models

class Migration(migrations.Migration):
    # Dependencies: Migrations that must run before this one
    dependencies = [
        ('myapp', '0001_initial'),
    ]

    # Operations to perform
    operations = [
        migrations.AddField(
            model_name='article',
            name='status',
            field=models.CharField(max_length=20, default='draft'),
        ),
    ]
```

## Schema Migrations

### Adding Fields

```python
# Add nullable field (safe, no default needed)
operations = [
    migrations.AddField(
        model_name='article',
        name='subtitle',
        field=models.CharField(max_length=200, null=True, blank=True),
    ),
]

# Add field with default (safe)
operations = [
    migrations.AddField(
        model_name='article',
        name='status',
        field=models.CharField(max_length=20, default='draft'),
    ),
]

# Add non-nullable field to table with data (two-step process)
# Step 1: Add as nullable
operations = [
    migrations.AddField(
        model_name='article',
        name='category',
        field=models.ForeignKey(
            'Category',
            on_delete=models.SET_NULL,
            null=True
        ),
    ),
]

# Step 2: After populating data, make non-nullable (see Data Migrations)
```

### Removing Fields

```python
# Simple removal
operations = [
    migrations.RemoveField(
        model_name='article',
        name='old_field',
    ),
]

# Safe removal process:
# 1. Remove from models.py
# 2. Deploy code (field still in database)
# 3. Create migration to remove field
# 4. Deploy migration
```

### Altering Fields

```python
# Change field type
operations = [
    migrations.AlterField(
        model_name='article',
        name='status',
        field=models.CharField(max_length=50),  # Was max_length=20
    ),
]

# Add database index
operations = [
    migrations.AlterField(
        model_name='article',
        name='slug',
        field=models.SlugField(max_length=200, db_index=True),
    ),
]

# Change to non-nullable (requires data)
operations = [
    migrations.AlterField(
        model_name='article',
        name='category',
        field=models.ForeignKey(
            'Category',
            on_delete=models.CASCADE,
            # Removed null=True
        ),
    ),
]
```

### Renaming Fields

```python
# Rename field (database operation)
operations = [
    migrations.RenameField(
        model_name='article',
        old_name='publish_date',
        new_name='published_at',
    ),
]

# Note: This is safe - Django handles the rename
```

### Creating Models

```python
operations = [
    migrations.CreateModel(
        name='Category',
        fields=[
            ('id', models.AutoField(primary_key=True)),
            ('name', models.CharField(max_length=100)),
            ('slug', models.SlugField(unique=True)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
        ],
        options={
            'verbose_name_plural': 'categories',
            'ordering': ['name'],
        },
    ),
]
```

### Deleting Models

```python
operations = [
    migrations.DeleteModel(name='OldModel'),
]

# Safe deletion process:
# 1. Remove references in other models first
# 2. Deploy code changes
# 3. Create migration to delete model
# 4. Deploy migration
```

### Renaming Models

```python
operations = [
    migrations.RenameModel(
        old_name='Article',
        new_name='Post',
    ),
]

# Updates:
# - Table name
# - Foreign key references
# - Many-to-many tables
```

### Indexes and Constraints

```python
# Add index
operations = [
    migrations.AddIndex(
        model_name='article',
        index=models.Index(fields=['status', '-created_at'], name='status_created_idx'),
    ),
]

# Remove index
operations = [
    migrations.RemoveIndex(
        model_name='article',
        name='status_created_idx',
    ),
]

# Add unique constraint
operations = [
    migrations.AddConstraint(
        model_name='article',
        constraint=models.UniqueConstraint(
            fields=['author', 'slug'],
            name='unique_author_slug'
        ),
    ),
]

# Add check constraint
operations = [
    migrations.AddConstraint(
        model_name='article',
        constraint=models.CheckConstraint(
            check=models.Q(views__gte=0),
            name='views_non_negative'
        ),
    ),
]
```

## Data Migrations

### Basic Data Migration

```python
from django.db import migrations

def populate_status(apps, schema_editor):
    """Forward migration: Set default status"""
    Article = apps.get_model('myapp', 'Article')

    # Update in batches for large tables
    Article.objects.filter(status__isnull=True).update(status='draft')

def reverse_populate_status(apps, schema_editor):
    """Reverse migration: Clear status"""
    Article = apps.get_model('myapp', 'Article')
    Article.objects.all().update(status=None)

class Migration(migrations.Migration):
    dependencies = [
        ('myapp', '0002_article_status'),
    ]

    operations = [
        migrations.RunPython(populate_status, reverse_populate_status),
    ]
```

### Complex Data Migration

```python
def migrate_article_data(apps, schema_editor):
    """Migrate data from old structure to new"""
    Article = apps.get_model('myapp', 'Article')
    Category = apps.get_model('myapp', 'Category')

    # Get or create default category
    default_category, _ = Category.objects.get_or_create(
        name='Uncategorized',
        defaults={'slug': 'uncategorized'}
    )

    # Process in batches to avoid memory issues
    batch_size = 1000
    articles = Article.objects.filter(category__isnull=True)

    for i in range(0, articles.count(), batch_size):
        batch = articles[i:i + batch_size]
        for article in batch:
            article.category = default_category
            article.save(update_fields=['category'])

def reverse_migrate(apps, schema_editor):
    """Reverse: Set category to NULL"""
    Article = apps.get_model('myapp', 'Article')
    Category = apps.get_model('myapp', 'Category')

    default_category = Category.objects.filter(name='Uncategorized').first()
    if default_category:
        Article.objects.filter(category=default_category).update(category=None)

class Migration(migrations.Migration):
    dependencies = [
        ('myapp', '0003_add_category_field'),
    ]

    operations = [
        migrations.RunPython(migrate_article_data, reverse_migrate),
    ]
```

### Data Migration with bulk_update

```python
def migrate_slugs(apps, schema_editor):
    """Generate slugs for existing articles"""
    from django.utils.text import slugify

    Article = apps.get_model('myapp', 'Article')

    articles_to_update = []
    for article in Article.objects.filter(slug=''):
        article.slug = slugify(article.title)
        articles_to_update.append(article)

        # Update in batches
        if len(articles_to_update) >= 500:
            Article.objects.bulk_update(articles_to_update, ['slug'])
            articles_to_update = []

    # Update remaining
    if articles_to_update:
        Article.objects.bulk_update(articles_to_update, ['slug'])

class Migration(migrations.Migration):
    dependencies = [
        ('myapp', '0004_article_slug'),
    ]

    operations = [
        migrations.RunPython(migrate_slugs, migrations.RunPython.noop),
    ]
```

### Conditional Data Migration

```python
def migrate_user_data(apps, schema_editor):
    """Migrate user data with conditions"""
    User = apps.get_model('auth', 'User')
    Profile = apps.get_model('myapp', 'Profile')

    for user in User.objects.filter(is_active=True):
        # Check if profile exists
        if not Profile.objects.filter(user=user).exists():
            Profile.objects.create(
                user=user,
                bio='',
                notification_enabled=True
            )

class Migration(migrations.Migration):
    dependencies = [
        ('myapp', '0005_profile'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.RunPython(migrate_user_data, migrations.RunPython.noop),
    ]
```

### Raw SQL Migration

```python
def run_sql(apps, schema_editor):
    """Run raw SQL for complex data transformation"""
    # Use parameterized queries to prevent SQL injection
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("""
            UPDATE myapp_article
            SET view_count = COALESCE(
                (SELECT COUNT(*) FROM myapp_view WHERE article_id = myapp_article.id),
                0
            )
        """)

class Migration(migrations.Migration):
    dependencies = [
        ('myapp', '0006_article_view_count'),
    ]

    operations = [
        migrations.RunSQL(
            # Forward SQL
            """
            UPDATE myapp_article
            SET view_count = COALESCE(
                (SELECT COUNT(*) FROM myapp_view WHERE article_id = myapp_article.id),
                0
            )
            """,
            # Reverse SQL
            """
            UPDATE myapp_article SET view_count = 0
            """
        ),
    ]
```

## Complex Migration Patterns

### Three-Step Field Migration

**Scenario:** Changing a field type or making a nullable field non-nullable with existing data.

```python
# Step 1: Add new field as nullable
class Migration(migrations.Migration):
    dependencies = [('myapp', '0001_initial')]

    operations = [
        migrations.AddField(
            model_name='article',
            name='status_new',
            field=models.CharField(max_length=20, null=True),
        ),
    ]

# Step 2: Copy data from old field to new field
class Migration(migrations.Migration):
    dependencies = [('myapp', '0002_add_status_new')]

    operations = [
        migrations.RunPython(
            lambda apps, schema_editor: apps.get_model('myapp', 'Article')
                .objects.all().update(status_new=models.F('status_old')),
            migrations.RunPython.noop
        ),
    ]

# Step 3: Remove old field, rename new field
class Migration(migrations.Migration):
    dependencies = [('myapp', '0003_copy_status_data')]

    operations = [
        migrations.RemoveField(model_name='article', name='status_old'),
        migrations.RenameField(
            model_name='article',
            old_name='status_new',
            new_name='status',
        ),
        # Make non-nullable if needed
        migrations.AlterField(
            model_name='article',
            name='status',
            field=models.CharField(max_length=20, default='draft'),
        ),
    ]
```

### Splitting a Model

```python
# Original: Article model with user fields
# Goal: Split into Article and Author models

# Step 1: Create Author model
class Migration(migrations.Migration):
    operations = [
        migrations.CreateModel(
            name='Author',
            fields=[
                ('id', models.AutoField(primary_key=True)),
                ('name', models.CharField(max_length=100)),
                ('email', models.EmailField()),
            ],
        ),
    ]

# Step 2: Add ForeignKey to Article
class Migration(migrations.Migration):
    operations = [
        migrations.AddField(
            model_name='article',
            name='author',
            field=models.ForeignKey(
                'Author',
                on_delete=models.CASCADE,
                null=True
            ),
        ),
    ]

# Step 3: Migrate data
def create_authors(apps, schema_editor):
    Article = apps.get_model('myapp', 'Article')
    Author = apps.get_model('myapp', 'Author')

    # Get unique author info from articles
    author_map = {}
    for article in Article.objects.all():
        key = (article.author_name, article.author_email)
        if key not in author_map:
            author = Author.objects.create(
                name=article.author_name,
                email=article.author_email
            )
            author_map[key] = author
        else:
            author = author_map[key]

        article.author = author
        article.save(update_fields=['author'])

class Migration(migrations.Migration):
    operations = [
        migrations.RunPython(create_authors, migrations.RunPython.noop),
    ]

# Step 4: Remove old fields
class Migration(migrations.Migration):
    operations = [
        migrations.RemoveField(model_name='article', name='author_name'),
        migrations.RemoveField(model_name='article', name='author_email'),
        migrations.AlterField(
            model_name='article',
            name='author',
            field=models.ForeignKey('Author', on_delete=models.CASCADE),
        ),
    ]
```

### Zero-Downtime Migration

**Scenario:** Rename a field without downtime.

```python
# Step 1: Add new field (deploy this first)
class Migration(migrations.Migration):
    operations = [
        migrations.AddField(
            model_name='article',
            name='publication_date',
            field=models.DateField(null=True),
        ),
    ]

# Update code to write to both fields:
# article.publish_date = date
# article.publication_date = date
# article.save()

# Step 2: Backfill data (deploy after step 1)
class Migration(migrations.Migration):
    operations = [
        migrations.RunPython(
            lambda apps, schema_editor: apps.get_model('myapp', 'Article')
                .objects.all().update(publication_date=models.F('publish_date')),
            migrations.RunPython.noop
        ),
    ]

# Update code to read from new field only

# Step 3: Remove old field (deploy after all instances updated)
class Migration(migrations.Migration):
    operations = [
        migrations.RemoveField(model_name='article', name='publish_date'),
    ]
```

## Rollback Strategies

### Rollback Migrations

```bash
# Rollback to specific migration
python manage.py migrate myapp 0003

# Rollback all migrations in app
python manage.py migrate myapp zero

# Show what would be rolled back
python manage.py migrate myapp 0003 --plan
```

### Reversible Data Migrations

```python
def forward_migration(apps, schema_editor):
    """Forward: Convert status codes"""
    Article = apps.get_model('myapp', 'Article')

    mapping = {
        'P': 'published',
        'D': 'draft',
        'A': 'archived',
    }

    for old_status, new_status in mapping.items():
        Article.objects.filter(status_code=old_status).update(status=new_status)

def reverse_migration(apps, schema_editor):
    """Reverse: Convert back to codes"""
    Article = apps.get_model('myapp', 'Article')

    mapping = {
        'published': 'P',
        'draft': 'D',
        'archived': 'A',
    }

    for old_status, new_status in mapping.items():
        Article.objects.filter(status=old_status).update(status_code=new_status)

class Migration(migrations.Migration):
    operations = [
        migrations.RunPython(forward_migration, reverse_migration),
    ]
```

### Irreversible Migrations

```python
# Migration that can't be reversed
class Migration(migrations.Migration):
    operations = [
        migrations.RunPython(
            delete_old_data,
            reverse_code=migrations.RunPython.noop  # Can't reverse
        ),
    ]

# Or mark as irreversible
class Migration(migrations.Migration):
    operations = [
        migrations.RunSQL(
            "DELETE FROM myapp_article WHERE status = 'deleted'",
            reverse_sql=migrations.RunSQL.noop  # Can't reverse
        ),
    ]
```

### Safe Rollback Pattern

```python
def forward(apps, schema_editor):
    """Forward migration with safety checks"""
    Article = apps.get_model('myapp', 'Article')

    # Store original values for potential rollback
    # (in a separate table or JSON field)
    for article in Article.objects.all():
        ArticleBackup.objects.create(
            article_id=article.id,
            original_data={'status': article.status}
        )

    # Perform migration
    Article.objects.all().update(status='published')

def reverse(apps, schema_editor):
    """Reverse using backup data"""
    Article = apps.get_model('myapp', 'Article')
    ArticleBackup = apps.get_model('myapp', 'ArticleBackup')

    for backup in ArticleBackup.objects.all():
        Article.objects.filter(id=backup.article_id).update(
            status=backup.original_data['status']
        )

    ArticleBackup.objects.all().delete()

class Migration(migrations.Migration):
    operations = [
        migrations.RunPython(forward, reverse),
    ]
```

## Migration Conflicts

### Detecting Conflicts

```bash
# Check for conflicting migrations
python manage.py migrate --check

# Show migration graph
python manage.py showmigrations --plan
```

### Resolving Conflicts

```bash
# Automatic merge
python manage.py makemigrations --merge

# Manual merge (edit the generated migration file)
```

### Merge Migration Example

```python
class Migration(migrations.Migration):
    """Merge migration resolving parallel branches"""

    dependencies = [
        ('myapp', '0004_add_status'),  # Branch A
        ('myapp', '0004_add_category'),  # Branch B (same number)
    ]

    operations = [
        # No operations needed if branches don't conflict
        # Django will just mark both as applied
    ]
```

### Handling Migration Conflicts in Teams

```python
# .git/hooks/post-merge (Git hook)
#!/bin/bash
# Check for migration conflicts after merge

python manage.py makemigrations --check --dry-run
if [ $? -ne 0 ]; then
    echo "⚠️  Migration conflicts detected!"
    echo "Run: python manage.py makemigrations --merge"
fi
```

## Best Practices

### 1. Always Test Migrations

```python
# Test migration locally first
python manage.py migrate --plan  # Review plan
python manage.py migrate  # Apply

# Test rollback
python manage.py migrate myapp 0003
python manage.py migrate myapp 0004  # Re-apply
```

### 2. Backup Before Major Migrations

```bash
# PostgreSQL backup
pg_dump dbname > backup_before_migration.sql

# MySQL backup
mysqldump -u user -p dbname > backup_before_migration.sql

# SQLite backup
cp db.sqlite3 db.sqlite3.backup
```

### 3. Use Transactions for Data Migrations

```python
class Migration(migrations.Migration):
    atomic = True  # Default: True

    operations = [
        migrations.RunPython(
            migrate_data,
            reverse_code=reverse_migrate_data
        ),
    ]

# For MySQL (doesn't support DDL in transactions)
class Migration(migrations.Migration):
    atomic = False  # Required for some MySQL operations
```

### 4. Batch Process Large Data Migrations

```python
def migrate_large_table(apps, schema_editor):
    """Migrate large table in batches"""
    Article = apps.get_model('myapp', 'Article')

    batch_size = 5000
    total = Article.objects.count()

    for offset in range(0, total, batch_size):
        batch = Article.objects.all()[offset:offset + batch_size]
        for article in batch:
            # Process article
            article.status = 'published'
        Article.objects.bulk_update(batch, ['status'])

        # Log progress
        print(f"Processed {offset + batch_size}/{total}")
```

### 5. Separate Schema and Data Migrations

```python
# Migration 0005: Schema change
class Migration(migrations.Migration):
    operations = [
        migrations.AddField(model_name='article', name='status', ...),
    ]

# Migration 0006: Data migration
class Migration(migrations.Migration):
    operations = [
        migrations.RunPython(populate_status, reverse_populate_status),
    ]

# Easier to rollback and test separately
```

### 6. Document Complex Migrations

```python
class Migration(migrations.Migration):
    """
    Migrate article status from integer codes to string values.

    This migration:
    1. Adds new 'status' field (CharField)
    2. Converts status_code values (1='draft', 2='published', 3='archived')
    3. Removes old 'status_code' field

    Rollback: Converts back to integer codes.

    Safe to run multiple times (idempotent).
    Estimated time: ~5 minutes for 1M articles.
    """

    dependencies = [('myapp', '0007_add_status_field')]

    operations = [
        migrations.RunPython(convert_status_codes, reverse_convert),
    ]
```

### 7. Squash Migrations Periodically

```bash
# Squash multiple migrations into one
python manage.py squashmigrations myapp 0001 0010

# Creates a new migration that replaces 0001-0010
# Useful for cleaning up development migrations
```

### 8. Test on Production-Like Data

```python
# Load production data snapshot
python manage.py loaddata production_snapshot.json

# Test migration
python manage.py migrate

# Verify data integrity
python manage.py check
python manage.py validate_articles  # Custom command
```

### 9. Monitor Migration Performance

```python
import time
from django.db import migrations

def timed_migration(apps, schema_editor):
    """Data migration with timing"""
    start = time.time()

    # Perform migration
    migrate_data(apps, schema_editor)

    elapsed = time.time() - start
    print(f"Migration completed in {elapsed:.2f} seconds")

class Migration(migrations.Migration):
    operations = [
        migrations.RunPython(timed_migration, migrations.RunPython.noop),
    ]
```

### 10. Handle Migration Failures Gracefully

```python
def safe_migration(apps, schema_editor):
    """Migration with error handling"""
    Article = apps.get_model('myapp', 'Article')

    errors = []
    for article in Article.objects.all():
        try:
            # Migrate article
            article.status = calculate_status(article)
            article.save()
        except Exception as e:
            errors.append(f"Article {article.id}: {str(e)}")

    if errors:
        print("⚠️  Migration completed with errors:")
        for error in errors:
            print(f"  - {error}")

class Migration(migrations.Migration):
    operations = [
        migrations.RunPython(safe_migration, migrations.RunPython.noop),
    ]
```
