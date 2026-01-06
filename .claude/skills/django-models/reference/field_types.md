# Django Field Types Reference

Complete guide to all Django model field types, when to use them, and their database implications.

## Table of Contents

- [Text Fields](#text-fields)
- [Numeric Fields](#numeric-fields)
- [Date and Time Fields](#date-and-time-fields)
- [Boolean Fields](#boolean-fields)
- [Relationship Fields](#relationship-fields)
- [File Fields](#file-fields)
- [Special Fields](#special-fields)
- [Field Options](#field-options)

## Text Fields

### CharField

**When to use:** Fixed-length text (names, titles, codes, short descriptions)

**Options:**
- `max_length` (required): Maximum character length
- `choices`: Predefined options
- `unique`: Enforce uniqueness
- `db_index`: Create database index

**Database:** VARCHAR(max_length)

```python
class Product(models.Model):
    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=50, unique=True, db_index=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('draft', 'Draft'),
            ('published', 'Published'),
            ('archived', 'Archived'),
        ],
        default='draft'
    )
```

**Gotchas:**
- Storing values longer than `max_length` raises validation error
- `unique=True` creates a database constraint
- Empty string vs NULL: Django uses empty string by default

### TextField

**When to use:** Long-form text (articles, descriptions, content)

**Options:**
- `max_length` (optional): Only for validation, not database constraint
- `blank`: Allow empty in forms

**Database:** TEXT (unlimited length in most databases)

```python
class Article(models.Model):
    content = models.TextField()
    notes = models.TextField(blank=True)  # Optional
```

**Gotchas:**
- No `max_length` database constraint even if specified
- Can be slower to index - avoid using in frequent filters
- Consider using CharField if content is short (<1000 chars)

### SlugField

**When to use:** URL-friendly strings (slugs, permalinks)

**Options:**
- `max_length`: Default 50
- `allow_unicode`: Allow non-ASCII characters (default: False)
- `unique`: Often used with unique=True

**Database:** VARCHAR(max_length)

```python
from django.utils.text import slugify

class Article(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, max_length=200)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)
```

**Gotchas:**
- Doesn't auto-generate slug - you must create it
- `allow_unicode=True` needed for non-English slugs
- Consider uniqueness across date ranges with `unique_for_date`

### EmailField

**When to use:** Email addresses

**Options:** Same as CharField
**Database:** VARCHAR(254)
**Default max_length:** 254

```python
class User(models.Model):
    email = models.EmailField(unique=True)
    secondary_email = models.EmailField(blank=True)
```

**Gotchas:**
- Only validates email format, doesn't verify deliverability
- Case-sensitive in database (normalize to lowercase in clean())
- max_length=254 per RFC 5321

### URLField

**When to use:** Web URLs

**Options:** Same as CharField
**Database:** VARCHAR(200)
**Default max_length:** 200

```python
class Website(models.Model):
    url = models.URLField(max_length=500)  # Increase for long URLs
```

**Gotchas:**
- Validates URL format (requires scheme: http://, https://)
- Default max_length might be too short for some URLs

## Numeric Fields

### IntegerField

**When to use:** Whole numbers (-2147483648 to 2147483647)

**Database:** INTEGER (4 bytes)

```python
class Product(models.Model):
    quantity = models.IntegerField(default=0)
    views = models.IntegerField(default=0, db_index=True)
```

**Gotchas:**
- Range limits depend on database
- Use PositiveIntegerField for non-negative values
- Use BigIntegerField for larger numbers

### BigIntegerField

**When to use:** Very large integers (-9223372036854775808 to 9223372036854775807)

**Database:** BIGINT (8 bytes)

```python
class Analytics(models.Model):
    total_views = models.BigIntegerField(default=0)
```

### SmallIntegerField

**When to use:** Small integers (-32768 to 32767)

**Database:** SMALLINT (2 bytes)

```python
class Rating(models.Model):
    score = models.SmallIntegerField(
        choices=[(i, str(i)) for i in range(1, 6)]
    )
```

### PositiveIntegerField / PositiveSmallIntegerField / PositiveBigIntegerField

**When to use:** Non-negative integers only (0 to max)

```python
class Product(models.Model):
    stock = models.PositiveIntegerField(default=0)
    order_count = models.PositiveIntegerField(default=0)
```

**Gotchas:**
- Database constraint enforces non-negative values
- Attempting to save negative value raises IntegrityError

### DecimalField

**When to use:** Precise decimal numbers (money, percentages, scientific data)

**Options:**
- `max_digits` (required): Total digits
- `decimal_places` (required): Decimal places

**Database:** DECIMAL(max_digits, decimal_places)

```python
class Product(models.Model):
    price = models.DecimalField(
        max_digits=10,  # Total digits
        decimal_places=2  # Decimal places
    )
    # Example: 99999999.99

class Rating(models.Model):
    average = models.DecimalField(
        max_digits=3,
        decimal_places=2
    )
    # Example: 4.75
```

**When to use DecimalField vs FloatField:**
- Use DecimalField for money (exact precision)
- Use FloatField for scientific calculations (approximate values)

### FloatField

**When to use:** Floating-point numbers (approximate values)

**Database:** DOUBLE PRECISION (8 bytes)

```python
class Measurement(models.Model):
    temperature = models.FloatField()
    latitude = models.FloatField()
    longitude = models.FloatField()
```

**Gotchas:**
- Subject to floating-point precision errors
- Never use for money - use DecimalField instead
- Comparisons might not be exact

## Date and Time Fields

### DateField

**When to use:** Date only (year, month, day)

**Options:**
- `auto_now`: Update on every save
- `auto_now_add`: Set on creation only

**Database:** DATE

```python
class Event(models.Model):
    event_date = models.DateField()
    created = models.DateField(auto_now_add=True)
```

**Gotchas:**
- `auto_now` and `auto_now_add` make field uneditable in admin
- These options don't work with `.update()` method
- Stores date without time information

### DateTimeField

**When to use:** Date and time together

**Options:** Same as DateField
**Database:** DATETIME (MySQL) or TIMESTAMP WITH TIME ZONE (PostgreSQL)

```python
from django.utils import timezone

class Article(models.Model):
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def publish(self):
        self.published_at = timezone.now()
        self.save()
```

**Gotchas:**
- Always use timezone-aware datetimes with `USE_TZ=True`
- `auto_now` doesn't trigger on `.update()`
- Timezone handling varies by database

### TimeField

**When to use:** Time only (hour, minute, second)

**Database:** TIME

```python
class BusinessHours(models.Model):
    open_time = models.TimeField()
    close_time = models.TimeField()
```

### DurationField

**When to use:** Time spans/intervals

**Database:** INTERVAL (PostgreSQL) or BIGINT (others)

```python
from datetime import timedelta

class Video(models.Model):
    duration = models.DurationField()

# Usage:
video = Video.objects.create(duration=timedelta(minutes=5, seconds=30))
```

## Boolean Fields

### BooleanField

**When to use:** True/False values

**Database:** BOOLEAN (PostgreSQL) or TINYINT (MySQL)

```python
class Article(models.Model):
    is_published = models.BooleanField(default=False)
    featured = models.BooleanField(default=False, db_index=True)
```

**Gotchas:**
- Cannot be NULL (use `null=True` for three-state logic)
- Default must be explicitly set or field is required

### NullBooleanField (Deprecated in Django 4.0)

**Replacement:** Use `BooleanField(null=True)`

```python
class Article(models.Model):
    # Old way (deprecated):
    # approved = models.NullBooleanField()

    # New way:
    approved = models.BooleanField(null=True, blank=True)
    # Values: True, False, or None
```

## Relationship Fields

### ForeignKey

**When to use:** Many-to-one relationships

**Options:**
- `on_delete` (required): CASCADE, SET_NULL, PROTECT, SET_DEFAULT, DO_NOTHING
- `related_name`: Reverse relation name
- `related_query_name`: Reverse filter name
- `to_field`: Reference non-primary key field

**Database:** INTEGER (or BIGINT for BigAutoField primary keys)

```python
class Author(models.Model):
    name = models.CharField(max_length=100)

class Book(models.Model):
    title = models.CharField(max_length=200)
    author = models.ForeignKey(
        Author,
        on_delete=models.CASCADE,  # Delete books when author deleted
        related_name='books'  # author.books.all()
    )

# Query examples:
author.books.all()  # All books by author
Book.objects.filter(author__name='Smith')  # Books by Smith
```

**on_delete options:**
```python
# CASCADE: Delete related objects
author = models.ForeignKey(Author, on_delete=models.CASCADE)

# PROTECT: Prevent deletion if related objects exist
author = models.ForeignKey(Author, on_delete=models.PROTECT)

# SET_NULL: Set to NULL (requires null=True)
author = models.ForeignKey(
    Author,
    on_delete=models.SET_NULL,
    null=True
)

# SET_DEFAULT: Set to default value (requires default)
author = models.ForeignKey(
    Author,
    on_delete=models.SET_DEFAULT,
    default=1
)

# SET(): Set to value from callable
def get_default_author():
    return Author.objects.get(name='Unknown')

author = models.ForeignKey(
    Author,
    on_delete=models.SET(get_default_author)
)

# DO_NOTHING: Do nothing (may cause database integrity error)
author = models.ForeignKey(Author, on_delete=models.DO_NOTHING)
```

### ManyToManyField

**When to use:** Many-to-many relationships

**Options:**
- `related_name`: Reverse relation name
- `through`: Intermediate model for extra fields
- `symmetrical`: For self-referential relationships (default: True)

**Database:** Creates intermediate junction table

```python
class Tag(models.Model):
    name = models.CharField(max_length=50)

class Article(models.Model):
    title = models.CharField(max_length=200)
    tags = models.ManyToManyField(
        Tag,
        related_name='articles',
        blank=True
    )

# Usage:
article.tags.add(tag1, tag2)
article.tags.remove(tag1)
article.tags.set([tag1, tag2, tag3])
article.tags.clear()

# Reverse:
tag.articles.all()
```

**Through model for extra fields:**
```python
class Author(models.Model):
    name = models.CharField(max_length=100)

class Book(models.Model):
    title = models.CharField(max_length=200)
    authors = models.ManyToManyField(
        Author,
        through='BookAuthor',
        related_name='books'
    )

class BookAuthor(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    author = models.ForeignKey(Author, on_delete=models.CASCADE)
    role = models.CharField(max_length=50)  # Extra field
    order = models.IntegerField()  # Extra field

    class Meta:
        unique_together = [['book', 'author']]

# Usage:
BookAuthor.objects.create(
    book=book,
    author=author,
    role='primary',
    order=1
)
```

### OneToOneField

**When to use:** One-to-one relationships (profile, settings extensions)

**Options:** Same as ForeignKey
**Database:** INTEGER with UNIQUE constraint

```python
from django.contrib.auth.models import User

class Profile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    bio = models.TextField()
    avatar = models.ImageField(upload_to='avatars/')

# Usage:
user.profile  # Get profile (raises if doesn't exist)
profile.user  # Get user

# Check existence:
hasattr(user, 'profile')

# Get or create:
profile, created = Profile.objects.get_or_create(user=user)
```

## File Fields

### FileField

**When to use:** File uploads

**Options:**
- `upload_to`: Subdirectory or callable
- `max_length`: Path length (default: 100)
- `storage`: Custom storage backend

**Database:** VARCHAR(max_length) - stores file path

```python
from django.utils import timezone

def document_upload_path(instance, filename):
    # File will be uploaded to MEDIA_ROOT/documents/2024/01/filename
    return f'documents/{timezone.now().strftime("%Y/%m")}/{filename}'

class Document(models.Model):
    title = models.CharField(max_length=200)
    file = models.FileField(upload_to=document_upload_path)

# Usage:
document.file.name  # Relative path
document.file.url  # URL to file
document.file.size  # File size
document.file.open()  # Open file
document.file.read()  # Read file
document.file.close()  # Close file
```

### ImageField

**When to use:** Image uploads (extends FileField)

**Options:** Same as FileField
**Database:** VARCHAR(max_length)
**Requires:** Pillow library

```python
class Product(models.Model):
    name = models.CharField(max_length=200)
    image = models.ImageField(
        upload_to='products/%Y/%m/',
        height_field='image_height',  # Auto-populate height
        width_field='image_width'  # Auto-populate width
    )
    image_height = models.IntegerField(null=True)
    image_width = models.IntegerField(null=True)
```

**Gotchas:**
- Requires Pillow: `pip install Pillow`
- Validates that uploaded file is an image
- Doesn't resize images automatically (use libraries like easy-thumbnails)

## Special Fields

### JSONField

**When to use:** Structured JSON data (PostgreSQL, MySQL 8.0+, SQLite 3.9+)

**Database:** JSON or JSONB (PostgreSQL)

```python
class Product(models.Model):
    name = models.CharField(max_length=200)
    metadata = models.JSONField(default=dict, blank=True)
    specifications = models.JSONField(default=list)

# Usage:
product = Product.objects.create(
    name='Laptop',
    metadata={'color': 'silver', 'weight': '1.5kg'},
    specifications=['15-inch display', 'Intel i7', '16GB RAM']
)

# Query:
Product.objects.filter(metadata__color='silver')
Product.objects.filter(specifications__contains='Intel i7')
```

**Query patterns:**
```python
# Key lookup
Product.objects.filter(metadata__price__gte=1000)

# Contains (PostgreSQL)
Product.objects.filter(metadata__contains={'color': 'silver'})

# Contained by (PostgreSQL)
Product.objects.filter(metadata__contained_by={'color': 'silver', 'size': 'M'})

# Has key
Product.objects.filter(metadata__has_key='price')
```

### BinaryField

**When to use:** Raw binary data (rarely needed - use FileField instead)

**Database:** BLOB

```python
class FileHash(models.Model):
    hash = models.BinaryField(max_length=32)  # SHA-256 hash
```

**Gotchas:**
- Not suitable for large files (use FileField)
- Cannot be used in filters
- Consider using TextField with base64 encoding instead

### UUIDField

**When to use:** UUID primary keys or unique identifiers

**Database:** UUID (PostgreSQL) or CHAR(32) (others)

```python
import uuid

class Article(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    title = models.CharField(max_length=200)

# Usage:
article = Article.objects.create(title='Test')
print(article.id)  # e.g., '550e8400-e29b-41d4-a716-446655440000'
```

**Gotchas:**
- Use `uuid.uuid4` not `uuid.uuid4()` (call without parentheses)
- Larger than IntegerField (16 bytes vs 4 bytes)
- Slower for indexing than integers on some databases

### GenericIPAddressField

**When to use:** IPv4 or IPv6 addresses

**Options:**
- `protocol`: 'both' (default), 'IPv4', or 'IPv6'

**Database:** VARCHAR(39)

```python
class AccessLog(models.Model):
    ip_address = models.GenericIPAddressField()
    ipv4_only = models.GenericIPAddressField(protocol='IPv4')
```

## Field Options

Common options available for most field types:

### Required Options

```python
class Product(models.Model):
    # null: Database-level (can store NULL in database)
    description = models.TextField(null=True)

    # blank: Validation-level (can be empty in forms)
    notes = models.TextField(blank=True)

    # Both together for optional text fields
    optional_text = models.TextField(null=True, blank=True)
```

**null vs blank:**
- `null=True`: Allows NULL in database
- `blank=True`: Allows empty value in forms
- For text fields, prefer `blank=True` without `null=True` (use empty string)
- For non-text fields (ForeignKey, DateField, etc.), use both

### Uniqueness Options

```python
class Article(models.Model):
    # Single field uniqueness
    slug = models.SlugField(unique=True)

    # Unique per date
    title = models.CharField(max_length=200, unique_for_date='publish_date')
    publish_date = models.DateField()

    # Unique together (in Meta)
    class Meta:
        unique_together = [['author', 'slug']]
        # Or constraints (Django 2.2+):
        constraints = [
            models.UniqueConstraint(
                fields=['author', 'slug'],
                name='unique_author_slug'
            )
        ]
```

### Index Options

```python
class Article(models.Model):
    # Simple index
    status = models.CharField(max_length=20, db_index=True)

    # In Meta for compound indexes
    class Meta:
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['author', 'status']),
        ]
```

### Default Values

```python
from django.utils import timezone

class Article(models.Model):
    # Static default
    status = models.CharField(max_length=20, default='draft')

    # Callable default
    created_at = models.DateTimeField(default=timezone.now)

    # Mutable default (list, dict)
    tags = models.JSONField(default=list)  # Not []
    metadata = models.JSONField(default=dict)  # Not {}
```

### Validation Options

```python
from django.core.validators import MinValueValidator, MaxValueValidator

class Product(models.Model):
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )

    rating = models.IntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5)
        ]
    )
```

### Help Text and Verbose Names

```python
class Article(models.Model):
    title = models.CharField(
        max_length=200,
        help_text='Enter the article title (max 200 characters)'
    )

    is_featured = models.BooleanField(
        default=False,
        verbose_name='Featured article',
        help_text='Display on homepage'
    )
```

### Database Options

```python
class Product(models.Model):
    # Custom column name
    internal_code = models.CharField(
        max_length=50,
        db_column='code'
    )

    # Custom tablespace (PostgreSQL)
    data = models.TextField(db_tablespace='ssd_tablespace')
```

## Performance Considerations

### Index Strategy

```python
class Article(models.Model):
    # Index frequently filtered fields
    status = models.CharField(max_length=20, db_index=True)

    # Index foreign keys (Django does this automatically)
    author = models.ForeignKey(User, on_delete=models.CASCADE)

    # Compound index for common filter combinations
    class Meta:
        indexes = [
            models.Index(fields=['status', '-created_at']),
        ]
```

### Text Field Choices

```python
# For frequently filtered fields, use CharField with choices
class Article(models.Model):
    # Good: Fast filtering with index
    status = models.CharField(
        max_length=20,
        choices=[
            ('draft', 'Draft'),
            ('published', 'Published'),
        ],
        db_index=True
    )

    # Avoid: TextField for status-like fields
    # status = models.TextField()  # Slower to index
```

### Integer vs UUID Primary Keys

```python
# Integer: Faster, smaller (4 bytes), sequential
class Article(models.Model):
    id = models.AutoField(primary_key=True)  # Default

# UUID: Larger (16 bytes), non-sequential, better for distributed systems
class Article(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
```

**When to use UUID:**
- Distributed systems with multiple databases
- Security (non-guessable IDs)
- Merging data from multiple sources

**When to use Integer:**
- Single database
- Performance is critical
- Sequential ordering matters
