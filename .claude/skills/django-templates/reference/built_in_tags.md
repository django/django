# Django Built-in Template Tags Reference

Complete reference for all Django built-in template tags.

## Table of Contents
- [Control Flow Tags](#control-flow-tags)
- [Template Structure Tags](#template-structure-tags)
- [URL and Static Tags](#url-and-static-tags)
- [Data Manipulation Tags](#data-manipulation-tags)
- [Internationalization Tags](#internationalization-tags)
- [Debugging Tags](#debugging-tags)
- [Caching Tags](#caching-tags)

## Control Flow Tags

### if

Test a condition and render content conditionally.

```django
{% if condition %}
    Content
{% endif %}
```

**With elif and else:**
```django
{% if user.is_superuser %}
    <p>Admin access</p>
{% elif user.is_staff %}
    <p>Staff access</p>
{% else %}
    <p>Regular user</p>
{% endif %}
```

**Operators:**
- `==` - Equal
- `!=` - Not equal
- `<` - Less than
- `>` - Greater than
- `<=` - Less than or equal
- `>=` - Greater than or equal
- `in` - Contains
- `not in` - Does not contain
- `is` - Identity check
- `is not` - Negative identity check

**Boolean operators:**
```django
{% if user.is_active and user.is_verified %}
{% if user.is_staff or user.is_superuser %}
{% if not user.is_banned %}
```

**Complex conditions:**
```django
{% if athlete_list and coach_list or cheerleader_list %}
    {# 'and' has higher precedence than 'or' #}
{% endif %}
```

**Filters in conditions:**
```django
{% if messages|length >= 100 %}
    <p>Too many messages!</p>
{% endif %}
```

### for

Iterate over a sequence.

```django
{% for item in item_list %}
    <li>{{ item }}</li>
{% endfor %}
```

**With empty clause:**
```django
{% for item in item_list %}
    <li>{{ item }}</li>
{% empty %}
    <li>No items available.</li>
{% endfor %}
```

**Loop variables:**
```django
{% for item in items %}
    {{ forloop.counter }}      {# 1-indexed #}
    {{ forloop.counter0 }}     {# 0-indexed #}
    {{ forloop.revcounter }}   {# Countdown from end #}
    {{ forloop.revcounter0 }}  {# Countdown from end (0-indexed) #}
    {{ forloop.first }}        {# True on first iteration #}
    {{ forloop.last }}         {# True on last iteration #}
    {{ forloop.parentloop }}   {# Reference to parent loop #}
{% endfor %}
```

**Unpacking:**
```django
{% for key, value in dictionary.items %}
    {{ key }}: {{ value }}
{% endfor %}

{% for x, y in points %}
    Point: ({{ x }}, {{ y }})
{% endfor %}
```

**Reversed iteration:**
```django
{% for item in item_list reversed %}
    {{ item }}
{% endfor %}
```

**Nested loops:**
```django
{% for group in groups %}
    <h2>{{ group.name }}</h2>
    {% for member in group.members %}
        <p>{{ forloop.parentloop.counter }}.{{ forloop.counter }} {{ member.name }}</p>
    {% endfor %}
{% endfor %}
```

### ifchanged

Detect changes in loop values.

```django
{% for date in dates %}
    {% ifchanged date.date %}
        <h3>{{ date.date }}</h3>
    {% endifchanged %}
    <p>{{ date.title }}</p>
{% endfor %}
```

**Multiple values:**
```django
{% for date in days %}
    {% ifchanged date.date date.hour %}
        {{ date.date }} {{ date.hour }}:00
    {% endifchanged %}
{% endfor %}
```

**With else clause:**
```django
{% for match in matches %}
    {% ifchanged match.team %}
        <h2>{{ match.team }}</h2>
    {% else %}
        {# Same team as previous #}
    {% endifchanged %}
{% endfor %}
```

### cycle

Cycle through values in a loop.

```django
{% for item in items %}
    <tr class="{% cycle 'row1' 'row2' %}">
        <td>{{ item }}</td>
    </tr>
{% endfor %}
```

**Named cycles:**
```django
{% for item in items %}
    <tr class="{% cycle 'odd' 'even' as rowcolors %}">
        <td>{{ item }}</td>
    </tr>
{% endfor %}

{# Manually advance #}
{% cycle rowcolors %}
```

**Silent cycling:**
```django
{% cycle 'row1' 'row2' as rowcolors silent %}
{{ rowcolors }}
```

### resetcycle

Reset a cycle to its first value.

```django
{% for group in groups %}
    <h2>{{ group.name }}</h2>
    {% for item in group.items %}
        <li class="{% cycle 'odd' 'even' %}">{{ item }}</li>
    {% endfor %}
    {% resetcycle %}
{% endfor %}
```

## Template Structure Tags

### extends

Declare template inheritance.

```django
{% extends "base.html" %}
```

**Dynamic parent:**
```django
{% extends parent_template %}  {# Variable from context #}
```

**Must be first tag** (except for comments and `{% load %}`):
```django
{% load static %}
{% extends "base.html" %}
```

### block

Define overridable content sections.

```django
{# In parent template #}
{% block content %}
    Default content
{% endblock %}

{# In child template #}
{% block content %}
    Overridden content
{% endblock %}
```

**Named endblock:**
```django
{% block navigation %}
    ...
{% endblock navigation %}
```

**Include parent content:**
```django
{% block content %}
    {{ block.super }}
    Additional content
{% endblock %}
```

**Nested blocks:**
```django
{% block outer %}
    <div>
        {% block inner %}Default inner{% endblock %}
    </div>
{% endblock %}
```

### include

Include another template.

```django
{% include "sidebar.html" %}
```

**With context variables:**
```django
{% include "name_snippet.html" with person="Jane" greeting="Hello" %}
```

**Isolated context (only specified variables):**
```django
{% include "name_snippet.html" with person="Jane" only %}
```

**Dynamic template name:**
```django
{% include template_name %}
```

**With default fallback:**
```django
{% include "template.html" with default="fallback.html" %}
```

### load

Load custom template tag library.

```django
{% load static %}
{% load i18n %}
{% load custom_tags %}
```

**Multiple libraries:**
```django
{% load static i18n %}
```

**Selective import:**
```django
{% load custom_filter from custom_tags %}
```

## URL and Static Tags

### url

Generate URLs from view names.

```django
{% url 'view_name' %}
{% url 'namespace:view_name' %}
```

**With positional arguments:**
```django
{% url 'article_detail' article.pk %}
{% url 'article_detail' article.pk article.slug %}
```

**With keyword arguments:**
```django
{% url 'article_detail' pk=article.pk slug=article.slug %}
```

**Assign to variable:**
```django
{% url 'article_detail' article.pk as article_url %}
<a href="{{ article_url }}">Read more</a>
```

**With query parameters (manual):**
```django
<a href="{% url 'search' %}?q={{ query|urlencode }}">Search</a>
```

**URL reversing patterns:**
```django
{# app_name:view_name #}
{% url 'blog:post_detail' post.pk %}

{# With current namespace #}
{% url ':view_name' %}
```

### static

Generate URLs for static files.

```django
{% load static %}
<img src="{% static 'images/logo.png' %}" alt="Logo">
```

**Assign to variable:**
```django
{% static 'images/hero.jpg' as hero_image %}
<div style="background-image: url({{ hero_image }})"></div>
```

**Common uses:**
```django
<link rel="stylesheet" href="{% static 'css/style.css' %}">
<script src="{% static 'js/app.js' %}"></script>
<img src="{% static 'images/icon.svg' %}" alt="Icon">
```

### get_static_prefix

Get the static files URL prefix.

```django
{% load static %}
{% get_static_prefix as STATIC_PREFIX %}

<script>
    var STATIC_URL = "{{ STATIC_PREFIX }}";
</script>
```

### get_media_prefix

Get the media files URL prefix.

```django
{% load static %}
{% get_media_prefix as MEDIA_PREFIX %}
<img src="{{ MEDIA_PREFIX }}{{ user.avatar }}">
```

## Data Manipulation Tags

### with

Assign values to variables in a scope.

```django
{% with total=business.employees.count %}
    {{ total }} employee{{ total|pluralize }}
{% endwith %}
```

**Multiple variables:**
```django
{% with alpha=1 beta=2 %}
    Sum: {{ alpha|add:beta }}
{% endwith %}
```

**Cache expensive operations:**
```django
{% with entries=blog.entries.all %}
    {% for entry in entries %}
        {{ entry.title }}
    {% endfor %}
    Total: {{ entries|length }}
{% endwith %}
```

### regroup

Group list by attribute.

```django
{% regroup people by gender as gender_list %}

{% for gender in gender_list %}
    <h2>{{ gender.grouper }}</h2>
    <ul>
        {% for person in gender.list %}
            <li>{{ person.name }}</li>
        {% endfor %}
    </ul>
{% endfor %}
```

**Multiple groupings:**
```django
{% regroup people by city as city_list %}
{% for city in city_list %}
    <h2>{{ city.grouper }}</h2>
    {% regroup city.list by gender as gender_list %}
    {% for gender in gender_list %}
        <h3>{{ gender.grouper }}</h3>
        <ul>
            {% for person in gender.list %}
                <li>{{ person.name }}</li>
            {% endfor %}
        </ul>
    {% endfor %}
{% endfor %}
```

### filter

Apply filters to a block of text.

```django
{% filter lower|escape %}
    This TEXT will be lowercase AND escaped.
{% endfilter %}
```

**Common use - force escaping:**
```django
{% filter force_escape %}
    {{ user_content }}
{% endfilter %}
```

### autoescape

Control auto-escaping for a block.

```django
{% autoescape off %}
    {{ html_content }}
{% endautoescape %}
```

**Nested:**
```django
{% autoescape off %}
    {{ safe_html }}
    {% autoescape on %}
        {{ user_input }}  {# Still escaped #}
    {% endautoescape %}
{% endautoescape %}
```

### firstof

Output the first non-false variable.

```django
{% firstof var1 var2 var3 %}

{# Equivalent to: #}
{% if var1 %}{{ var1 }}{% elif var2 %}{{ var2 }}{% elif var3 %}{{ var3 }}{% endif %}
```

**With fallback:**
```django
{% firstof var1 var2 var3 "default" %}
```

**Assign to variable:**
```django
{% firstof var1 var2 var3 as value %}
```

### now

Output current date/time.

```django
{% now "Y-m-d" %}
{% now "D d M Y" %}
{% now "Y" as current_year %}
```

**Format strings:**
```django
{% now "Y-m-d H:i:s" %}      {# 2024-03-15 14:30:00 #}
{% now "jS F Y" %}           {# 15th March 2024 #}
{% now "D M j G:i:s T Y" %}  {# Fri Mar 15 14:30:00 UTC 2024 #}
```

### spaceless

Remove whitespace between HTML tags.

```django
{% spaceless %}
    <p>
        <a href="...">Link</a>
    </p>
{% endspaceless %}

{# Outputs: <p><a href="...">Link</a></p> #}
```

**Note:** Only removes whitespace **between** tags, not inside tags.

### verbatim

Prevent template processing.

```django
{% verbatim %}
    {{ this }} {% will %} {{not}} {% be %} processed
{% endverbatim %}
```

**Useful for JavaScript templates:**
```django
{% verbatim %}
    <script type="text/template">
        <div>{{ name }}</div>
    </script>
{% endverbatim %}
```

**Named endverbatim:**
```django
{% verbatim myblock %}
    {{ unprocessed }}
{% endverbatim myblock %}
```

### widthratio

Calculate ratios (useful for progress bars).

```django
{# widthratio value max_value max_width #}
{% widthratio current_value max_value 100 %}
```

**Progress bar example:**
```django
<div class="progress-bar" style="width: {% widthratio progress 100 100 %}%"></div>
```

**Assign to variable:**
```django
{% widthratio current_value max_value 100 as percentage %}
Progress: {{ percentage }}%
```

### lorem

Generate dummy text.

```django
{% lorem %}           {# 1 paragraph #}
{% lorem 3 p %}       {# 3 paragraphs #}
{% lorem 10 w %}      {# 10 words #}
{% lorem 5 w random %} {# 5 random words #}
```

## Internationalization Tags

### translate / trans

Mark strings for translation.

```django
{% load i18n %}
{% translate "Hello" %}
{% trans "Hello" %}  {# Shorter alias #}
```

**With context:**
```django
{% trans "Hello" context "greeting" %}
```

**As variable:**
```django
{% trans "Hello" as greeting %}
{{ greeting }}
```

**Noop translation (for extraction only):**
```django
{% trans "Hello" noop %}
```

### blocktranslate / blocktrans

Translate blocks with variables.

```django
{% blocktranslate %}
    Hello {{ name }}!
{% endblocktranslate %}

{# Shorter alias #}
{% blocktrans %}
    You have {{ count }} messages.
{% endblocktrans %}
```

**With pluralization:**
```django
{% blocktrans count counter=items|length %}
    {{ counter }} item
{% plural %}
    {{ counter }} items
{% endblocktrans %}
```

**With context:**
```django
{% blocktrans with name=user.name %}
    Hello {{ name }}!
{% endblocktrans %}
```

### language

Set language for a block.

```django
{% load i18n %}
{% language 'fr' %}
    {% trans "Hello" %}
{% endlanguage %}
```

### get_current_language

Get current language code.

```django
{% get_current_language as LANGUAGE_CODE %}
<html lang="{{ LANGUAGE_CODE }}">
```

### get_available_languages

Get available languages.

```django
{% get_available_languages as LANGUAGES %}
<select name="language">
    {% for lang_code, lang_name in LANGUAGES %}
        <option value="{{ lang_code }}">{{ lang_name }}</option>
    {% endfor %}
</select>
```

### get_language_info

Get language information.

```django
{% get_language_info for 'fr' as lang %}
{{ lang.name_local }}  {# Français #}
{{ lang.code }}        {# fr #}
{{ lang.name }}        {# French #}
```

## Debugging Tags

### debug

Output debugging information.

```django
{% debug %}
```

Outputs all context variables and available tags/filters. Only works if `DEBUG=True`.

### comment

Multi-line comments.

```django
{% comment %}
    This is a comment.
    It can span multiple lines.
{% endcomment %}
```

**Named comment:**
```django
{% comment "Disabled feature" %}
    {% if show_feature %}
        ...
    {% endif %}
{% endcomment %}
```

## Caching Tags

### cache

Cache template fragment.

```django
{% load cache %}
{% cache 500 sidebar %}
    {# Expensive content cached for 500 seconds #}
    {% expensive_tag %}
{% endcache %}
```

**With variables in cache key:**
```django
{% cache 500 sidebar request.user.id %}
    {# Cache per-user #}
{% endcache %}
```

**Multiple key parts:**
```django
{% cache 600 object_detail object.id object.modified %}
    {# Cache invalidated when modified changes #}
{% endcache %}
```

**Using cache alias:**
```django
{% cache 300 sidebar using="default" %}
    ...
{% endcache %}
```

## Form-Related Tags

### csrf_token

Include CSRF token for forms.

```django
<form method="post">
    {% csrf_token %}
    ...
</form>
```

**Required for all POST forms** to prevent Cross-Site Request Forgery attacks.

## Template Loading Tags

### ssi

Include static file (Server Side Include).

```django
{% ssi "/path/to/file.html" %}
```

**With parsing:**
```django
{% ssi "/path/to/file.html" parsed %}
```

**Note:** Deprecated in favor of `{% include %}`. Requires `ALLOWED_INCLUDE_ROOTS` setting.

## Best Practices

1. **Use meaningful variable names in `{% with %}`**
2. **Always include `{% csrf_token %}` in POST forms**
3. **Cache expensive operations** with `{% cache %}`
4. **Use `{% ifchanged %}` to avoid redundant output** in loops
5. **Prefer `{% url %}` over hardcoded URLs** for maintainability
6. **Load tag libraries at top of template** before use
7. **Use `{% empty %}` clause in `{% for %}`** for better UX
8. **Keep logic minimal** - move complex logic to views/tags

## Common Patterns

### Conditional CSS classes
```django
<div class="{% if user.is_premium %}premium{% else %}standard{% endif %}">
```

### Alternating row colors
```django
{% for item in items %}
    <tr class="{% cycle 'odd' 'even' %}">
        <td>{{ item }}</td>
    </tr>
{% endfor %}
```

### Breadcrumbs
```django
{% for crumb in breadcrumbs %}
    <a href="{% url crumb.view %}">{{ crumb.title }}</a>
    {% if not forloop.last %} › {% endif %}
{% endfor %}
```

### Pagination
```django
{% if page_obj.has_previous %}
    <a href="?page=1">First</a>
    <a href="?page={{ page_obj.previous_page_number }}">Previous</a>
{% endif %}

<span>Page {{ page_obj.number }} of {{ page_obj.paginator.num_pages }}</span>

{% if page_obj.has_next %}
    <a href="?page={{ page_obj.next_page_number }}">Next</a>
    <a href="?page={{ page_obj.paginator.num_pages }}">Last</a>
{% endif %}
```

### Active navigation
```django
<nav>
    <a href="{% url 'home' %}" class="{% if request.resolver_match.url_name == 'home' %}active{% endif %}">
        Home
    </a>
</nav>
```
