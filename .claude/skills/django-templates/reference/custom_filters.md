# Creating Custom Template Filters

Complete guide to creating custom Django template filters.

## Table of Contents
- [Setup](#setup)
- [Basic Filters](#basic-filters)
- [Filters with Arguments](#filters-with-arguments)
- [Safe Output](#safe-output)
- [Advanced Patterns](#advanced-patterns)
- [Best Practices](#best-practices)
- [Testing](#testing)

## Setup

### 1. Create templatetags directory

Same structure as custom tags:

```
myapp/
├── __init__.py
├── models.py
├── views.py
└── templatetags/
    ├── __init__.py
    └── custom_filters.py
```

### 2. Create filter library file

```python
# myapp/templatetags/custom_filters.py
from django import template

register = template.Library()

# Your filters go here
```

### 3. Load in template

```django
{% load custom_filters %}
{{ value|my_filter }}
```

## Basic Filters

### Simple Filter (No Arguments)

```python
from django import template

register = template.Library()

@register.filter
def lower_first(value):
    """Lowercase the first character."""
    if not value:
        return value
    return value[0].lower() + value[1:]
```

**Usage:**
```django
{{ "Hello World"|lower_first }}
{# Output: hello World #}
```

### String Manipulation

```python
@register.filter
def remove_spaces(value):
    """Remove all spaces from string."""
    return value.replace(' ', '')

@register.filter
def reverse_string(value):
    """Reverse a string."""
    return value[::-1]

@register.filter
def count_vowels(value):
    """Count vowels in string."""
    vowels = 'aeiouAEIOU'
    return sum(1 for char in value if char in vowels)
```

**Usage:**
```django
{{ "hello world"|remove_spaces }}  {# helloworld #}
{{ "Django"|reverse_string }}       {# ognajD #}
{{ "Django"|count_vowels }}         {# 2 #}
```

### Numeric Filters

```python
@register.filter
def percentage(value, total):
    """Calculate percentage."""
    try:
        return round((float(value) / float(total)) * 100, 1)
    except (ValueError, ZeroDivisionError):
        return 0

@register.filter
def absolute(value):
    """Return absolute value."""
    try:
        return abs(float(value))
    except (ValueError, TypeError):
        return value
```

**Usage:**
```django
{{ 75|percentage:100 }}     {# 75.0 #}
{{ -42|absolute }}          {# 42 #}
```

## Filters with Arguments

### Single Argument

```python
@register.filter
def multiply(value, arg):
    """Multiply value by argument."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return ''

@register.filter
def starts_with(value, arg):
    """Check if string starts with argument."""
    return str(value).startswith(str(arg))
```

**Usage:**
```django
{{ 5|multiply:3 }}              {# 15 #}
{{ "Django"|starts_with:"Dj" }} {# True #}
```

### Multiple Arguments (Using String Parsing)

```python
@register.filter
def replace(value, args):
    """Replace old with new. Args format: 'old,new'"""
    try:
        old, new = args.split(',')
        return value.replace(old, new)
    except (ValueError, AttributeError):
        return value

@register.filter
def slice_string(value, args):
    """Slice string. Args format: 'start,end'"""
    try:
        start, end = map(int, args.split(','))
        return value[start:end]
    except (ValueError, IndexError):
        return value
```

**Usage:**
```django
{{ "hello world"|replace:"world,Django" }}  {# hello Django #}
{{ "Django Framework"|slice_string:"0,6" }} {# Django #}
```

## Safe Output

### Returning HTML

```python
from django.utils.safestring import mark_safe
from django.utils.html import escape

@register.filter
def highlight(value, term):
    """Highlight search term in text."""
    if not term:
        return value

    # Escape both value and term to prevent XSS
    safe_value = escape(value)
    safe_term = escape(term)

    # Highlight the term
    highlighted = safe_value.replace(
        safe_term,
        f'<mark>{safe_term}</mark>'
    )

    # Mark as safe (we've escaped the inputs)
    return mark_safe(highlighted)
```

**Usage:**
```django
{{ article.content|highlight:search_query }}
```

### Safe Filter Decorator

```python
from django.utils.safestring import mark_safe

@register.filter(is_safe=True)
def make_bold(value):
    """Wrap text in <strong> tags."""
    return mark_safe(f'<strong>{escape(value)}</strong>')
```

**Usage:**
```django
{{ text|make_bold }}
```

### Preserving Safety

```python
from django.utils.safestring import mark_safe, SafeString

@register.filter(is_safe=True)
def add_class(value, css_class):
    """Add CSS class to HTML element."""
    # If input is safe, output is safe
    if isinstance(value, SafeString):
        return mark_safe(value.replace('>', f' class="{css_class}">', 1))
    return value
```

## Advanced Patterns

### Working with QuerySets

```python
@register.filter
def filter_published(queryset):
    """Filter queryset for published items."""
    try:
        return queryset.filter(published=True)
    except (AttributeError, TypeError):
        return queryset

@register.filter
def order_by_field(queryset, field_name):
    """Order queryset by field name."""
    try:
        return queryset.order_by(field_name)
    except (AttributeError, TypeError):
        return queryset
```

**Usage:**
```django
{% for post in posts|filter_published|order_by_field:"-created_at" %}
    {{ post.title }}
{% endfor %}
```

### Date Formatting

```python
from django.utils import timezone
from datetime import timedelta

@register.filter
def days_since(value):
    """Calculate days since given date."""
    if not value:
        return None

    try:
        delta = timezone.now().date() - value
        return delta.days
    except (AttributeError, TypeError):
        return None

@register.filter
def is_recent(value, days=7):
    """Check if date is within last N days."""
    if not value:
        return False

    try:
        cutoff = timezone.now() - timedelta(days=int(days))
        return value >= cutoff
    except (AttributeError, TypeError, ValueError):
        return False
```

**Usage:**
```django
{{ post.published_date|days_since }} days ago

{% if post.created_at|is_recent:30 %}
    <span class="badge">New</span>
{% endif %}
```

### File Size Formatting

```python
@register.filter
def filesize(bytes):
    """Format bytes as human-readable file size."""
    try:
        bytes = float(bytes)
    except (ValueError, TypeError):
        return "0 bytes"

    if bytes < 1024:
        return f"{bytes:.0f} bytes"
    elif bytes < 1024 ** 2:
        return f"{bytes / 1024:.1f} KB"
    elif bytes < 1024 ** 3:
        return f"{bytes / (1024 ** 2):.1f} MB"
    else:
        return f"{bytes / (1024 ** 3):.1f} GB"
```

**Usage:**
```django
{{ file.size|filesize }}  {# 1.5 MB #}
```

### JSON Formatting

```python
import json
from django.utils.safestring import mark_safe

@register.filter
def to_json(value):
    """Convert Python object to JSON string."""
    try:
        return mark_safe(json.dumps(value))
    except (TypeError, ValueError):
        return '{}'

@register.filter
def pretty_json(value):
    """Format JSON with indentation."""
    try:
        parsed = json.loads(value) if isinstance(value, str) else value
        return mark_safe(json.dumps(parsed, indent=2))
    except (TypeError, ValueError, json.JSONDecodeError):
        return value
```

**Usage:**
```django
<script>
    var data = {{ object|to_json }};
</script>

<pre>{{ json_string|pretty_json }}</pre>
```

### Color Manipulation

```python
@register.filter
def darken_color(hex_color, percent=20):
    """Darken hex color by percentage."""
    try:
        # Remove # if present
        hex_color = hex_color.lstrip('#')

        # Convert to RGB
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)

        # Darken
        factor = 1 - (percent / 100)
        r = int(r * factor)
        g = int(g * factor)
        b = int(b * factor)

        # Convert back to hex
        return f'#{r:02x}{g:02x}{b:02x}'
    except (ValueError, IndexError):
        return hex_color
```

**Usage:**
```django
<div style="background-color: {{ brand_color|darken_color:30 }}"></div>
```

### Text Truncation with Ellipsis

```python
@register.filter
def smart_truncate(value, length=100):
    """Truncate text at word boundary."""
    if len(value) <= length:
        return value

    # Find last space before length
    truncated = value[:length].rsplit(' ', 1)[0]
    return f"{truncated}..."
```

**Usage:**
```django
{{ article.content|smart_truncate:200 }}
```

### Markdown to HTML

```python
@register.filter
def markdown_to_html(value):
    """Convert Markdown to HTML."""
    try:
        import markdown
        return mark_safe(markdown.markdown(
            value,
            extensions=['extra', 'codehilite']
        ))
    except ImportError:
        return value
```

**Usage:**
```django
{{ post.content|markdown_to_html }}
```

### Dictionary Access

```python
@register.filter
def get_item(dictionary, key):
    """Get item from dictionary."""
    try:
        return dictionary.get(key)
    except (AttributeError, TypeError):
        return None

@register.filter
def get_attr(obj, attr_name):
    """Get attribute from object."""
    try:
        return getattr(obj, attr_name)
    except (AttributeError, TypeError):
        return None
```

**Usage:**
```django
{{ user_stats|get_item:"posts_count" }}
{{ object|get_attr:"dynamic_field_name" }}
```

## Best Practices

### 1. Error Handling

Always handle exceptions gracefully:

```python
# BAD - can crash template
@register.filter
def divide(value, arg):
    return float(value) / float(arg)

# GOOD - handles errors
@register.filter
def divide(value, arg):
    try:
        return float(value) / float(arg)
    except (ValueError, ZeroDivisionError, TypeError):
        return 0
```

### 2. Type Checking

```python
@register.filter
def add_prefix(value, prefix):
    """Add prefix to string."""
    if not isinstance(value, str):
        value = str(value)
    if not isinstance(prefix, str):
        prefix = str(prefix)
    return f"{prefix}{value}"
```

### 3. Null/Empty Handling

```python
@register.filter
def format_phone(value):
    """Format phone number."""
    if not value:
        return ''

    # Remove non-digits
    digits = ''.join(c for c in str(value) if c.isdigit())

    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    return value
```

### 4. Documentation

```python
@register.filter
def calculate_discount(price, discount_percent):
    """
    Calculate discounted price.

    Args:
        price: Original price (float)
        discount_percent: Discount percentage (int or float)

    Returns:
        Discounted price rounded to 2 decimals

    Example:
        {{ 100|calculate_discount:20 }}  # Returns 80.0
    """
    try:
        price = float(price)
        discount = float(discount_percent)
        discounted = price * (1 - discount / 100)
        return round(discounted, 2)
    except (ValueError, TypeError):
        return price
```

### 5. Performance

```python
# BAD - complex database query in filter
@register.filter
def get_user_posts(user):
    return Post.objects.filter(author=user).select_related('category')

# GOOD - do this in view, not filter
# Filters should transform existing data, not fetch new data
```

### 6. Security

```python
from django.utils.html import escape
from django.utils.safestring import mark_safe

# BAD - XSS vulnerability
@register.filter
def link_username(user):
    return mark_safe(f'<a href="/users/{user.id}/">{user.username}</a>')

# GOOD - escape user data
@register.filter
def link_username(user):
    escaped_name = escape(user.username)
    return mark_safe(f'<a href="/users/{user.id}/">{escaped_name}</a>')
```

### 7. Naming

```python
# GOOD - descriptive names
@register.filter
def format_currency(value):
    pass

@register.filter
def humanize_bytes(value):
    pass

# BAD - vague names
@register.filter
def fmt(value):
    pass

@register.filter
def process(value):
    pass
```

## Testing

### Basic Filter Tests

```python
# tests/test_filters.py
from django.test import TestCase
from django.template import Context, Template

class CustomFiltersTest(TestCase):
    def test_multiply_filter(self):
        template = Template("{{ value|multiply:3 }}")
        context = Context({'value': 5})
        result = template.render(context)
        self.assertEqual(result, '15.0')

    def test_multiply_filter_with_invalid_input(self):
        template = Template("{{ value|multiply:3 }}")
        context = Context({'value': 'invalid'})
        result = template.render(context)
        self.assertEqual(result, '')

    def test_highlight_filter(self):
        template = Template(
            "{% load custom_filters %}"
            "{{ text|highlight:term }}"
        )
        context = Context({
            'text': 'Hello world',
            'term': 'world'
        })
        result = template.render(context)
        self.assertIn('<mark>world</mark>', result)
```

### Edge Case Tests

```python
class FilterEdgeCasesTest(TestCase):
    def test_filter_with_none(self):
        template = Template("{{ value|my_filter }}")
        context = Context({'value': None})
        result = template.render(context)
        self.assertIsNotNone(result)

    def test_filter_with_empty_string(self):
        template = Template("{{ value|my_filter }}")
        context = Context({'value': ''})
        result = template.render(context)
        self.assertEqual(result, '')

    def test_filter_chaining(self):
        template = Template("{{ value|filter1|filter2 }}")
        context = Context({'value': 'test'})
        result = template.render(context)
        # Assert expected result
```

## Common Patterns

### Active/Inactive Badge

```python
@register.filter
def status_badge(is_active):
    """Return Bootstrap badge for status."""
    if is_active:
        return mark_safe('<span class="badge badge-success">Active</span>')
    return mark_safe('<span class="badge badge-secondary">Inactive</span>')
```

**Usage:**
```django
{{ user.is_active|status_badge }}
```

### Initials Generator

```python
@register.filter
def initials(name):
    """Get initials from name."""
    if not name:
        return ''

    parts = name.split()
    if len(parts) >= 2:
        return f"{parts[0][0]}{parts[-1][0]}".upper()
    return name[0].upper()
```

**Usage:**
```django
<div class="avatar">{{ user.get_full_name|initials }}</div>
```

### Pluralize with Custom Words

```python
@register.filter
def smart_pluralize(count, words):
    """Pluralize with custom singular/plural. Format: 'singular,plural'"""
    try:
        singular, plural = words.split(',')
        return singular if count == 1 else plural
    except ValueError:
        return words
```

**Usage:**
```django
{{ count }} {{ count|smart_pluralize:"child,children" }}
{{ count }} {{ count|smart_pluralize:"person,people" }}
```

### Social Share Link

```python
from urllib.parse import quote

@register.filter
def twitter_share_url(text, url=''):
    """Generate Twitter share URL."""
    encoded_text = quote(text)
    encoded_url = quote(url)
    return mark_safe(
        f'https://twitter.com/intent/tweet?text={encoded_text}&url={encoded_url}'
    )
```

**Usage:**
```django
<a href="{{ post.title|twitter_share_url:post.get_absolute_url }}">
    Share on Twitter
</a>
```

### Credit Card Masking

```python
@register.filter
def mask_credit_card(number):
    """Mask credit card number."""
    if not number:
        return ''

    number = str(number).replace(' ', '')
    if len(number) < 8:
        return '****'

    return f"{'*' * (len(number) - 4)}{number[-4:]}"
```

**Usage:**
```django
{{ card_number|mask_credit_card }}  {# ************1234 #}
```

## Troubleshooting

### Filter not found
```
Invalid filter: 'my_filter'
```
**Fix:**
- Load library: `{% load custom_filters %}`
- Check filter is registered with `@register.filter`
- Restart development server

### Filter returns None
```python
@register.filter
def my_filter(value):
    # No return statement!
    value.upper()
```
**Fix:** Always return a value:
```python
@register.filter
def my_filter(value):
    return value.upper()
```

### Argument not passed correctly
```django
{# WRONG #}
{{ value|my_filter:"arg1,arg2" }}

{# RIGHT (if filter expects one string argument) #}
{{ value|my_filter:"arg1,arg2" }}

{# RIGHT (if filter expects separate arguments - not standard) #}
{# Use a custom tag instead for multiple arguments #}
```

### Safe HTML not rendering
```python
# Missing mark_safe
@register.filter
def my_html_filter(value):
    return f'<strong>{value}</strong>'  # Will be escaped!

# Fixed
@register.filter
def my_html_filter(value):
    from django.utils.safestring import mark_safe
    from django.utils.html import escape
    return mark_safe(f'<strong>{escape(value)}</strong>')
```

## Django Version Notes

### Django 3.x+
- Better type checking in filters
- Improved error messages

### Django 4.x+
- Enhanced safe string handling
- Performance improvements

### Django 5.x+
- Additional security checks for `mark_safe` usage
