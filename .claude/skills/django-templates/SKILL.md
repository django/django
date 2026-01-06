# Django Templates Skill

## Overview

Master Django's template system - the "T" in MTV (Model-Template-View). This skill helps you create maintainable, performant templates using Django's powerful template language. Use this skill when building user interfaces, creating reusable components, or optimizing template rendering.

**When to use this skill:**
- Creating HTML interfaces for Django views
- Building reusable template components
- Writing custom template tags and filters
- Debugging template inheritance or context issues
- Optimizing template rendering performance
- Working with template fragments and caching

## Quick Start

Most common task - create a base template with inheritance:

```bash
# 1. Create base template structure
cat > templates/base.html << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}My Site{% endblock %}</title>
    {% block extra_head %}{% endblock %}
</head>
<body>
    <header>{% include 'partials/header.html' %}</header>
    <main>{% block content %}{% endblock %}</main>
    <footer>{% include 'partials/footer.html' %}</footer>
    {% block extra_js %}{% endblock %}
</body>
</html>
EOF

# 2. Create child template
cat > templates/page.html << 'EOF'
{% extends 'base.html' %}

{% block title %}{{ page.title }} - {{ block.super }}{% endblock %}

{% block content %}
    <h1>{{ page.title }}</h1>
    <div>{{ page.content|safe }}</div>
{% endblock %}
EOF

# 3. Use in view
# views.py: return render(request, 'page.html', {'page': page_obj})
```

## Core Workflows

### Workflow 1: Create Base Template with Blocks

**Use when:** Starting a new Django project or refactoring templates

**Steps:**
1. **Identify common page sections** - header, nav, content, footer, scripts
2. **Create base template with strategic blocks** (see Quick Start for example)
3. **Create child templates** that extend base using `{% extends 'base.html' %}`
4. **Test inheritance** - verify blocks override correctly

**Common block naming patterns:**
- `title` - page title
- `content` - main content area
- `extra_head` - additional CSS/meta tags
- `extra_js` - additional JavaScript
- `body_class` - dynamic body classes

### Workflow 2: Build Reusable Template Components

**Use when:** Creating UI components used across multiple pages

**Steps:**
1. **Create component template** in `templates/components/` with parameters
2. **Use with `{% include %}`**:
   ```django
   {% include 'components/card.html' with title="Profile" only %}
   ```
3. **Or create inclusion tag** for complex logic (see [custom_tags.md](reference/custom_tags.md))
4. **Test component** across different contexts

### Workflow 3: Create Custom Template Tags

**Use when:** Need complex logic or database queries in templates

**See:** [reference/custom_tags.md](reference/custom_tags.md) for complete guide

**Quick example:**
```python
@register.simple_tag
def get_latest_posts(count=5):
    return Post.objects.filter(published=True)[:count]
```

**Generate boilerplate:**
```bash
python scripts/generate_templatetag.py blog post_tags --type simple
```

### Workflow 4: Create Custom Template Filters

**Use when:** Need to transform variables in templates

**See:** [reference/custom_filters.md](reference/custom_filters.md) for complete guide

**Quick example:**
```python
@register.filter
def highlight_term(text, term):
    """Highlights search term in text."""
    safe_text = escape(text)
    safe_term = escape(term)
    return mark_safe(safe_text.replace(safe_term, f'<mark>{safe_term}</mark>'))
```

### Workflow 5: Optimize Template Performance

**Use when:** Templates are slow or causing N+1 queries

**See:** [reference/performance.md](reference/performance.md) for complete guide

**Quick tips:**
1. Enable cached template loader in production
2. Use `{% cache %}` for expensive blocks
3. Optimize queries with select_related/prefetch_related in views
4. Analyze with: `python scripts/template_analyzer.py --check-performance templates/`

## Template Inheritance Patterns

### Linear Inheritance (Most Common)
```
base.html
  └── page.html
        └── article_detail.html
```

**When to use:** Standard page types with progressive specialization

### Multiple Base Templates
```
base.html                    base_minimal.html
  ├── page.html                └── landing.html
  └── dashboard_base.html
        └── analytics.html
```

**When to use:** Different page layouts (full site vs landing pages)

### Mixin Pattern (Advanced)
```django
{# templates/mixins/analytics.html #}
{% block analytics_head %}
    <script>/* analytics code */</script>
{% endblock %}

{# templates/page_with_analytics.html #}
{% extends 'base.html' %}
{% include 'mixins/analytics.html' %}
```

**When to use:** Optional features that cross-cut multiple page types

## Anti-Patterns

### ❌ Business Logic in Templates
**Bad:**
```django
{% for user in all_users %}
    {% if user.is_active and user.posts.count > 5 and user.last_login > cutoff_date %}
        {# This is a database query in every loop iteration! #}
    {% endif %}
{% endfor %}
```

**Good:**
```python
# In view
qualified_users = User.objects.filter(
    is_active=True,
    posts__count__gt=5,
    last_login__gt=cutoff_date
).annotate(post_count=Count('posts'))

return render(request, 'template.html', {'users': qualified_users})
```

### ❌ Deep Inheritance (>3 levels)
**Bad:**
```
base.html → section_base.html → subsection_base.html → page_base.html → actual_page.html
```

**Good:** Keep inheritance to 2-3 levels maximum

### ❌ Not Using `{{ block.super }}`
**Bad:**
```django
{% block title %}Dashboard{% endblock %}
{# Loses site name from base template #}
```

**Good:**
```django
{% block title %}Dashboard | {{ block.super }}{% endblock %}
```

### ❌ Forgetting `|safe` vs Auto-escaping
**Bad:**
```django
{{ user_content|safe }}  {# XSS vulnerability! #}
```

**Good:**
```python
# In model or view
from django.utils.html import escape
safe_content = escape(user_content)
# Or use a sanitizer like bleach
```

```django
{{ safe_content|safe }}
```

### ❌ Complex Logic in Filters
**Bad:**
```python
@register.filter
def complex_calculation(value):
    # 50 lines of business logic
    # Database queries
    # External API calls
    return result
```

**Good:** Use template tags for complex logic, keep filters simple

### ❌ Not Using Template Fragment Caching
**Bad:**
```django
{# This queries database on every page load #}
{% for category in categories %}
    {% for post in category.posts.all %}
        ...
    {% endfor %}
{% endfor %}
```

**Good:**
```django
{% cache 300 category_posts %}
    {% for category in categories %}
        {% for post in category.posts.all %}
            ...
        {% endfor %}
    {% endfor %}
{% endcache %}
```

## Scripts & Tools

### Generate Template Tag Boilerplate
```bash
python scripts/generate_templatetag.py app_name tag_name --type [simple|inclusion|assignment]
```

Creates a template tag file with proper structure.

### Analyze Templates
```bash
# Find unused templates
python scripts/template_analyzer.py --find-unused

# Detect missing blocks in inheritance chain
python scripts/template_analyzer.py --check-blocks templates/

# Analyze performance issues
python scripts/template_analyzer.py --check-performance templates/

# Show inheritance chain
python scripts/template_analyzer.py --show-inheritance templates/page.html
```

## Common Patterns

### Context Processor Pattern
Add site-wide context variables:

```python
# context_processors.py
def site_settings(request):
    return {
        'SITE_NAME': 'My Site',
        'CURRENT_YEAR': datetime.now().year,
    }

# settings.py
TEMPLATES = [{
    'OPTIONS': {
        'context_processors': [
            # ...
            'myapp.context_processors.site_settings',
        ],
    },
}]
```

### Template Tag Libraries Pattern
Organize related tags:

```python
# templatetags/dates.py
register = template.Library()

@register.filter
def days_ago(date):
    return (timezone.now().date() - date).days

@register.simple_tag
def current_time(format_string):
    return timezone.now().strftime(format_string)
```

### Component with Slots Pattern
```django
{# templates/components/modal.html #}
<div class="modal">
    <div class="modal-header">
        {% block modal_header %}{{ title }}{% endblock %}
    </div>
    <div class="modal-body">
        {% block modal_body %}{% endblock %}
    </div>
    <div class="modal-footer">
        {% block modal_footer %}
            <button class="btn-close">Close</button>
        {% endblock %}
    </div>
</div>
```

## Related Skills

- **django-views** - Passing context to templates
- **django-forms** - Rendering forms in templates
- **django-models** - Template tags that query models
- **django-caching** - Template fragment caching strategies

## Django Version Notes

### Django 4.x+
- Template-based form rendering API (`{{ form.as_div }}`)
- Improved `{% cached %}` tag with conditional invalidation

### Django 3.x
- `{% translate %}` and `{% blocktranslate %}` (shorter aliases)
- Async template rendering support

### Django 5.x+
- Field groups in form rendering
- Improved error messages for template syntax

## Troubleshooting

### Template Not Found
```
TemplateDoesNotExist at /page/
template.html
```

**Fix:**
1. Check `TEMPLATES[0]['DIRS']` includes your template directory
2. Verify `APP_DIRS=True` for app templates
3. Check template name spelling and path
4. Ensure app is in `INSTALLED_APPS`

### Context Variable Not Available
```django
{{ user.profile.avatar }}  {# Nothing renders #}
```

**Debug:**
```django
{# Temporarily add to template #}
<pre>{{ user|pprint }}</pre>  {# After {% load debug %} #}
```

Or use Django Debug Toolbar to inspect context.

### Template Tag Not Found
```
Invalid block tag: 'custom_tag'
```

**Fix:**
1. Verify `{% load custom_tags %}` at top of template
2. Check template tag file in `templatetags/` directory
3. Ensure app is in `INSTALLED_APPS`
4. Restart development server after creating new tag library

### Infinite Recursion in Blocks
```
RecursionError: maximum recursion depth exceeded
```

**Cause:** Template extends itself or circular dependency

**Fix:** Check inheritance chain for cycles

## Reference Documentation

- [Template Syntax](reference/template_syntax.md) - Variables, filters, tags, comments
- [Built-in Tags](reference/built_in_tags.md) - Complete tag reference
- [Built-in Filters](reference/built_in_filters.md) - Complete filter reference
- [Custom Tags](reference/custom_tags.md) - Creating custom tags
- [Custom Filters](reference/custom_filters.md) - Creating custom filters
- [Performance](reference/performance.md) - Caching and optimization
