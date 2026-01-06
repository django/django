# Creating Custom Template Tags

Complete guide to creating custom Django template tags.

## Table of Contents
- [Setup](#setup)
- [Simple Tags](#simple-tags)
- [Inclusion Tags](#inclusion-tags)
- [Assignment Tags](#assignment-tags)
- [Block Tags](#block-tags)
- [Advanced Patterns](#advanced-patterns)
- [Best Practices](#best-practices)

## Setup

### 1. Create templatetags directory

Template tag libraries must be in a `templatetags/` directory within a Django app:

```
myapp/
├── __init__.py
├── models.py
├── views.py
└── templatetags/
    ├── __init__.py
    └── custom_tags.py
```

**Both `__init__.py` files must exist!**

### 2. Create tag library file

```python
# myapp/templatetags/custom_tags.py
from django import template

register = template.Library()

# Your tags go here
```

### 3. Load in template

```django
{% load custom_tags %}
{% my_custom_tag %}
```

### 4. App must be in INSTALLED_APPS

```python
# settings.py
INSTALLED_APPS = [
    # ...
    'myapp',
]
```

## Simple Tags

Simple tags process arguments and return a value.

### Basic Simple Tag

```python
from django import template

register = template.Library()

@register.simple_tag
def multiply(a, b):
    """Multiply two numbers."""
    return a * b
```

**Usage:**
```django
{% load custom_tags %}
{% multiply 5 10 %}  {# Output: 50 #}
{% multiply 5 10 as result %}
{{ result }}  {# Output: 50 #}
```

### With Keyword Arguments

```python
@register.simple_tag
def format_price(amount, currency='USD', symbol='$'):
    """Format price with currency."""
    return f"{symbol}{amount:.2f} {currency}"
```

**Usage:**
```django
{% format_price 19.99 %}
{# Output: $19.99 USD #}

{% format_price 19.99 currency="EUR" symbol="€" %}
{# Output: €19.99 EUR #}
```

### Accessing Context

```python
@register.simple_tag(takes_context=True)
def current_user_full_name(context):
    """Get current user's full name."""
    user = context['request'].user
    return user.get_full_name() or user.username
```

**Usage:**
```django
{% current_user_full_name %}
```

### Database Queries

```python
@register.simple_tag
def get_recent_posts(count=5):
    """Get recent published posts."""
    from blog.models import Post
    return Post.objects.filter(
        published=True
    ).select_related('author').order_by('-created_at')[:count]
```

**Usage:**
```django
{% get_recent_posts 3 as posts %}
{% for post in posts %}
    <h3>{{ post.title }}</h3>
{% endfor %}
```

### Complex Logic Example

```python
@register.simple_tag(takes_context=True)
def user_has_permission(context, permission):
    """Check if current user has permission."""
    user = context['request'].user
    return user.has_perm(permission)
```

**Usage:**
```django
{% user_has_permission "blog.add_post" as can_add %}
{% if can_add %}
    <a href="{% url 'blog:create_post' %}">New Post</a>
{% endif %}
```

## Inclusion Tags

Inclusion tags render a template with provided context.

### Basic Inclusion Tag

```python
@register.inclusion_tag('blog/recent_posts.html')
def show_recent_posts(count=5):
    """Render recent posts list."""
    from blog.models import Post
    posts = Post.objects.filter(published=True)[:count]
    return {'posts': posts}
```

**Template (blog/recent_posts.html):**
```django
<div class="recent-posts">
    <h3>Recent Posts</h3>
    <ul>
        {% for post in posts %}
            <li><a href="{{ post.get_absolute_url }}">{{ post.title }}</a></li>
        {% endfor %}
    </ul>
</div>
```

**Usage:**
```django
{% show_recent_posts 10 %}
```

### With Context

```python
@register.inclusion_tag('components/user_card.html', takes_context=True)
def user_card(context, user):
    """Render user card with permissions check."""
    current_user = context['request'].user
    can_edit = current_user.has_perm('auth.change_user') or current_user == user

    return {
        'user': user,
        'can_edit': can_edit,
        'current_user': current_user,
    }
```

**Template (components/user_card.html):**
```django
<div class="card user-card">
    <img src="{{ user.profile.avatar }}" alt="{{ user.username }}">
    <h4>{{ user.get_full_name }}</h4>
    <p>{{ user.profile.bio|truncatewords:20 }}</p>
    {% if can_edit %}
        <a href="{% url 'user_edit' user.pk %}" class="btn">Edit</a>
    {% endif %}
</div>
```

**Usage:**
```django
{% user_card user=profile_user %}
```

### Complex Inclusion Tag

```python
@register.inclusion_tag('components/paginator.html')
def paginate(page_obj, adjacent_pages=2):
    """Render pagination with page numbers."""
    current_page = page_obj.number
    num_pages = page_obj.paginator.num_pages

    # Calculate page range
    start_page = max(current_page - adjacent_pages, 1)
    end_page = min(current_page + adjacent_pages, num_pages)

    page_numbers = range(start_page, end_page + 1)

    return {
        'page_obj': page_obj,
        'page_numbers': page_numbers,
        'show_first': start_page > 1,
        'show_last': end_page < num_pages,
    }
```

**Template (components/paginator.html):**
```django
<nav class="pagination">
    {% if page_obj.has_previous %}
        <a href="?page=1" class="page-link">First</a>
        <a href="?page={{ page_obj.previous_page_number }}" class="page-link">Previous</a>
    {% endif %}

    {% if show_first %}
        <span class="ellipsis">...</span>
    {% endif %}

    {% for page_num in page_numbers %}
        {% if page_num == page_obj.number %}
            <span class="page-current">{{ page_num }}</span>
        {% else %}
            <a href="?page={{ page_num }}" class="page-link">{{ page_num }}</a>
        {% endif %}
    {% endfor %}

    {% if show_last %}
        <span class="ellipsis">...</span>
    {% endif %}

    {% if page_obj.has_next %}
        <a href="?page={{ page_obj.next_page_number }}" class="page-link">Next</a>
        <a href="?page={{ page_obj.paginator.num_pages }}" class="page-link">Last</a>
    {% endif %}
</nav>
```

**Usage:**
```django
{% paginate page_obj adjacent_pages=3 %}
```

## Assignment Tags

**Note:** As of Django 1.9+, use `simple_tag` with `as` syntax instead.

```python
# OLD (deprecated)
@register.assignment_tag
def get_value():
    return "value"

# NEW (use this)
@register.simple_tag
def get_value():
    return "value"
```

**Usage:**
```django
{% get_value as my_value %}
{{ my_value }}
```

## Block Tags

Block tags are more complex and allow custom parsing.

### Basic Block Tag

```python
from django import template
from django.template.base import Node, NodeList

register = template.Library()

class UpperNode(Node):
    def __init__(self, nodelist):
        self.nodelist = nodelist

    def render(self, context):
        output = self.nodelist.render(context)
        return output.upper()

@register.tag
def upper(parser, token):
    """Convert enclosed content to uppercase."""
    nodelist = parser.parse(('endupper',))
    parser.delete_first_token()
    return UpperNode(nodelist)
```

**Usage:**
```django
{% upper %}
    This text will be uppercase
{% endupper %}
```

### Block Tag with Arguments

```python
class RepeatNode(Node):
    def __init__(self, nodelist, count):
        self.nodelist = nodelist
        self.count = template.Variable(count)

    def render(self, context):
        count = self.count.resolve(context)
        output = self.nodelist.render(context)
        return output * count

@register.tag
def repeat(parser, token):
    """Repeat enclosed content N times."""
    try:
        tag_name, count = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError(
            f"{token.contents.split()[0]} tag requires a count argument"
        )

    nodelist = parser.parse(('endrepeat',))
    parser.delete_first_token()
    return RepeatNode(nodelist, count)
```

**Usage:**
```django
{% repeat 3 %}
    <p>This paragraph repeats</p>
{% endrepeat %}
```

### Conditional Block Tag

```python
class IfUserGroupNode(Node):
    def __init__(self, group_name, nodelist_true, nodelist_false):
        self.group_name = template.Variable(group_name)
        self.nodelist_true = nodelist_true
        self.nodelist_false = nodelist_false

    def render(self, context):
        try:
            group_name = self.group_name.resolve(context)
            user = context['request'].user

            if user.groups.filter(name=group_name).exists():
                return self.nodelist_true.render(context)
            else:
                return self.nodelist_false.render(context)
        except (template.VariableDoesNotExist, KeyError):
            return self.nodelist_false.render(context)

@register.tag
def ifusergroup(parser, token):
    """Check if user belongs to group."""
    try:
        tag_name, group_name = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError(
            "ifusergroup tag requires a group name"
        )

    nodelist_true = parser.parse(('else', 'endifusergroup'))
    token = parser.next_token()

    if token.contents == 'else':
        nodelist_false = parser.parse(('endifusergroup',))
        parser.delete_first_token()
    else:
        nodelist_false = NodeList()

    return IfUserGroupNode(group_name, nodelist_true, nodelist_false)
```

**Usage:**
```django
{% ifusergroup "editors" %}
    <p>You are an editor</p>
{% else %}
    <p>You are not an editor</p>
{% endifusergroup %}
```

### Cache Block Tag (Advanced)

```python
from django.core.cache import cache

class CacheFragmentNode(Node):
    def __init__(self, nodelist, cache_key, timeout):
        self.nodelist = nodelist
        self.cache_key = template.Variable(cache_key)
        self.timeout = template.Variable(timeout) if timeout else None

    def render(self, context):
        cache_key = self.cache_key.resolve(context)
        timeout = self.timeout.resolve(context) if self.timeout else 300

        # Try to get from cache
        output = cache.get(cache_key)

        if output is None:
            # Render and cache
            output = self.nodelist.render(context)
            cache.set(cache_key, output, timeout)

        return output

@register.tag
def cache_fragment(parser, token):
    """Cache template fragment."""
    try:
        bits = token.split_contents()
        tag_name = bits[0]
        cache_key = bits[1]
        timeout = bits[2] if len(bits) > 2 else None
    except (ValueError, IndexError):
        raise template.TemplateSyntaxError(
            f"{tag_name} requires at least a cache key"
        )

    nodelist = parser.parse(('endcache_fragment',))
    parser.delete_first_token()
    return CacheFragmentNode(nodelist, cache_key, timeout)
```

**Usage:**
```django
{% cache_fragment "sidebar" 600 %}
    {# Expensive content cached for 600 seconds #}
    {% expensive_query %}
{% endcache_fragment %}
```

## Advanced Patterns

### Tag with Multiple Arguments

```python
@register.simple_tag
def query_string(request, **kwargs):
    """Update query string parameters."""
    query = request.GET.copy()

    for key, value in kwargs.items():
        if value:
            query[key] = value
        elif key in query:
            del query[key]

    return f"?{query.urlencode()}" if query else ""
```

**Usage:**
```django
<a href="{% url 'search' %}{% query_string request page=2 sort='date' %}">
    Page 2, sorted by date
</a>
```

### Tag with Variable Arguments

```python
@register.simple_tag
def join_strings(*args, separator=", "):
    """Join multiple strings."""
    return separator.join(str(arg) for arg in args)
```

**Usage:**
```django
{% join_strings "apple" "banana" "cherry" separator=" | " %}
{# Output: apple | banana | cherry #}
```

### Tag Returning Safe HTML

```python
from django.utils.safestring import mark_safe
from django.utils.html import escape

@register.simple_tag
def icon(name, classes=""):
    """Render icon HTML."""
    html = f'<i class="icon icon-{escape(name)} {escape(classes)}"></i>'
    return mark_safe(html)
```

**Usage:**
```django
{% icon "user" classes="large blue" %}
{# Output: <i class="icon icon-user large blue"></i> #}
```

### Tag with Error Handling

```python
@register.simple_tag
def safe_divide(a, b, default=0):
    """Safely divide two numbers."""
    try:
        return float(a) / float(b)
    except (ValueError, TypeError, ZeroDivisionError):
        return default
```

**Usage:**
```django
{% safe_divide total count default="N/A" %}
```

### Tag with QuerySet Optimization

```python
@register.simple_tag
def get_user_posts(user, limit=10):
    """Get user's posts with optimizations."""
    from blog.models import Post

    return Post.objects.filter(
        author=user,
        published=True
    ).select_related(
        'category'
    ).prefetch_related(
        'tags'
    ).only(
        'title', 'slug', 'created_at', 'category__name'
    )[:limit]
```

**Usage:**
```django
{% get_user_posts user 5 as posts %}
{% for post in posts %}
    <h3>{{ post.title }}</h3>
    <span>{{ post.category.name }}</span>
{% endfor %}
```

## Best Practices

### 1. Naming Conventions

```python
# GOOD - descriptive names
@register.simple_tag
def get_recent_comments(post, count=5):
    pass

# BAD - vague names
@register.simple_tag
def get_stuff(obj, n=5):
    pass
```

### 2. Documentation

```python
@register.simple_tag
def format_currency(amount, currency='USD'):
    """
    Format amount as currency.

    Args:
        amount: Numeric amount
        currency: Currency code (default: USD)

    Returns:
        Formatted currency string

    Example:
        {% format_currency 19.99 "EUR" %}
    """
    # Implementation
```

### 3. Error Handling

```python
@register.simple_tag
def get_object_or_none(model_class, **kwargs):
    """Get object or return None on error."""
    try:
        return model_class.objects.get(**kwargs)
    except (model_class.DoesNotExist, model_class.MultipleObjectsReturned):
        return None
```

### 4. Performance

```python
# BAD - N+1 queries
@register.simple_tag
def get_posts_with_comments():
    posts = Post.objects.all()
    # Each post.comments.all() is a separate query
    return posts

# GOOD - optimized queries
@register.simple_tag
def get_posts_with_comments():
    return Post.objects.prefetch_related('comments').all()
```

### 5. Context Awareness

```python
# GOOD - respect context
@register.simple_tag(takes_context=True)
def url_with_params(context, view_name, **kwargs):
    """Generate URL preserving current query params."""
    request = context['request']
    url = reverse(view_name)

    # Preserve relevant query params
    query = request.GET.copy()
    query.update(kwargs)

    return f"{url}?{query.urlencode()}"
```

### 6. Security

```python
from django.utils.html import escape
from django.utils.safestring import mark_safe

@register.simple_tag
def render_alert(message, alert_type="info"):
    """Render Bootstrap alert (safely)."""
    # Escape user input
    safe_message = escape(message)
    safe_type = escape(alert_type)

    html = f'<div class="alert alert-{safe_type}">{safe_message}</div>'
    return mark_safe(html)
```

### 7. Testing

```python
# tests/test_templatetags.py
from django.test import TestCase
from django.template import Context, Template

class CustomTagsTest(TestCase):
    def test_multiply_tag(self):
        template = Template("{% load custom_tags %}{% multiply 5 10 %}")
        rendered = template.render(Context({}))
        self.assertEqual(rendered, "50")

    def test_multiply_with_assignment(self):
        template = Template(
            "{% load custom_tags %}"
            "{% multiply 5 10 as result %}"
            "{{ result }}"
        )
        rendered = template.render(Context({}))
        self.assertEqual(rendered, "50")
```

## Common Patterns

### Active Navigation Link

```python
@register.simple_tag(takes_context=True)
def nav_active(context, view_name, css_class='active'):
    """Return CSS class if current view matches."""
    request = context['request']
    if request.resolver_match.url_name == view_name:
        return css_class
    return ''
```

**Usage:**
```django
<a href="{% url 'home' %}" class="nav-link {% nav_active 'home' %}">Home</a>
```

### Gravatar Image

```python
import hashlib

@register.simple_tag
def gravatar_url(email, size=80):
    """Generate Gravatar URL."""
    email_hash = hashlib.md5(email.lower().encode()).hexdigest()
    return f"https://www.gravatar.com/avatar/{email_hash}?s={size}"
```

**Usage:**
```django
<img src="{% gravatar_url user.email 150 %}" alt="{{ user.username }}">
```

### Reading Time

```python
@register.simple_tag
def reading_time(content, wpm=200):
    """Calculate reading time in minutes."""
    from django.utils.html import strip_tags

    text = strip_tags(content)
    word_count = len(text.split())
    minutes = max(1, round(word_count / wpm))

    return f"{minutes} min read"
```

**Usage:**
```django
<span class="reading-time">{% reading_time article.content %}</span>
```

## Troubleshooting

### Tag not found
```
Invalid block tag: 'my_tag'
```
**Fix:**
- Load the library: `{% load custom_tags %}`
- Check app is in `INSTALLED_APPS`
- Verify `templatetags/__init__.py` exists
- Restart development server

### ImportError
```
ImportError: No module named 'templatetags'
```
**Fix:**
- Ensure `templatetags/__init__.py` exists
- Check directory structure
- Restart server

### Context variable not available
```python
# Tag expecting context
@register.simple_tag  # Missing takes_context=True
def my_tag(context):
    # context is actually the first positional arg, not the context!
```

**Fix:**
```python
@register.simple_tag(takes_context=True)
def my_tag(context, arg1):
    # Now context is properly passed
```
