# Django Template Syntax Reference

Complete guide to Django's template language syntax.

## Table of Contents
- [Variables](#variables)
- [Filters](#filters)
- [Tags](#tags)
- [Comments](#comments)
- [Template Inheritance](#template-inheritance)
- [Escaping](#escaping)
- [Whitespace Control](#whitespace-control)

## Variables

### Basic Syntax
```django
{{ variable_name }}
```

Variables are surrounded by `{{ }}` and are replaced with their values when the template is rendered.

### Dot Notation
```django
{{ user.username }}           {# Attribute lookup #}
{{ user.get_full_name }}      {# Method call (no arguments) #}
{{ items.0 }}                 {# List index #}
{{ data.key }}                {# Dictionary key #}
```

**Lookup order:**
1. Dictionary lookup (`obj['key']`)
2. Attribute lookup (`obj.key`)
3. List-index lookup (`obj[0]`)
4. Method call (`obj.key()`)

### Special Variables
```django
{{ forloop.counter }}         {# Inside {% for %} loop #}
{{ block.super }}             {# Parent block content #}
{{ request.user }}            {# If request in context #}
```

## Filters

### Basic Syntax
```django
{{ value|filter_name }}
{{ value|filter_name:"argument" }}
{{ value|filter1|filter2 }}   {# Chain filters #}
```

### Common Filters

**String Manipulation:**
```django
{{ text|lower }}                    {# Convert to lowercase #}
{{ text|upper }}                    {# Convert to uppercase #}
{{ text|title }}                    {# Title case #}
{{ text|capfirst }}                 {# Capitalize first letter #}
{{ text|truncatewords:30 }}         {# Truncate to 30 words #}
{{ text|truncatechars:100 }}        {# Truncate to 100 chars #}
{{ text|wordcount }}                {# Count words #}
{{ text|slugify }}                  {# Convert to slug #}
{{ text|striptags }}                {# Remove HTML tags #}
```

**HTML/Safety:**
```django
{{ html|safe }}                     {# Mark as safe (no escaping) #}
{{ html|escape }}                   {# Force HTML escaping #}
{{ html|escapejs }}                 {# Escape for JavaScript #}
{{ text|linebreaks }}               {# Convert \n to <p> tags #}
{{ text|linebreaksbr }}             {# Convert \n to <br> #}
```

**Lists:**
```django
{{ list|first }}                    {# First item #}
{{ list|last }}                     {# Last item #}
{{ list|join:", " }}                {# Join with separator #}
{{ list|length }}                   {# Count items #}
{{ list|slice:":3" }}               {# Slice [Python syntax] #}
```

**Numbers:**
```django
{{ number|add:5 }}                  {# Add 5 #}
{{ number|floatformat:2 }}          {# Format to 2 decimals #}
{{ number|divisibleby:3 }}          {# Check if divisible #}
```

**Dates:**
```django
{{ date|date:"Y-m-d" }}             {# Format date #}
{{ date|time:"H:i" }}               {# Format time #}
{{ date|timesince }}                {# "3 hours ago" #}
{{ date|timeuntil }}                {# "in 2 days" #}
```

**Default Values:**
```django
{{ value|default:"nothing" }}       {# If value is falsy #}
{{ value|default_if_none:"N/A" }}   {# If value is None #}
```

**URLs:**
```django
{{ url|urlencode }}                 {# URL encode #}
{{ text|urlize }}                   {# Convert URLs to links #}
{{ text|urlizetrunc:30 }}           {# Truncate URLs #}
```

### Filter Arguments
```django
{# String arguments in quotes #}
{{ value|filter:"argument" }}

{# Numeric arguments without quotes #}
{{ value|truncatewords:10 }}

{# Variable as argument #}
{{ value|default:other_value }}
```

## Tags

### Basic Syntax
```django
{% tag_name argument %}
{% tag_name %}...{% endtag_name %}
```

### Control Flow

**if/elif/else:**
```django
{% if user.is_authenticated %}
    <p>Welcome, {{ user.username }}!</p>
{% elif user.is_anonymous %}
    <p>Please log in.</p>
{% else %}
    <p>Unknown user state.</p>
{% endif %}
```

**Comparison Operators:**
```django
{% if age >= 18 %}
{% if name == "admin" %}
{% if count != 0 %}
{% if user.is_staff or user.is_superuser %}
{% if user.is_active and user.is_verified %}
{% if item not in excluded_items %}
{% if item is None %}
{% if item is not None %}
```

**for loops:**
```django
{% for item in items %}
    <p>{{ forloop.counter }}. {{ item.name }}</p>
{% empty %}
    <p>No items found.</p>
{% endfor %}
```

**Loop variables:**
```django
{{ forloop.counter }}       {# 1-indexed iteration #}
{{ forloop.counter0 }}      {# 0-indexed iteration #}
{{ forloop.revcounter }}    {# Reverse counter #}
{{ forloop.first }}         {# True on first iteration #}
{{ forloop.last }}          {# True on last iteration #}
{{ forloop.parentloop }}    {# Parent loop in nested loops #}
```

### Template Loading

**extends:**
```django
{% extends "base.html" %}
{% extends variable_name %}  {# Dynamic base template #}
```

**include:**
```django
{% include "partial.html" %}
{% include "partial.html" with title="Hello" %}
{% include "partial.html" with title="Hello" only %}  {# Isolated context #}
```

**block:**
```django
{% block content %}
    Default content
{% endblock content %}

{# In child template #}
{% block content %}
    {{ block.super }}  {# Include parent content #}
    New content
{% endblock %}
```

**load:**
```django
{% load static %}
{% load i18n %}
{% load custom_tags %}
{% load custom_tags another_tags %}  {# Multiple libraries #}
```

### URLs and Static Files

**url:**
```django
{% url 'view_name' %}
{% url 'view_name' arg1 arg2 %}
{% url 'namespace:view_name' %}
{% url 'view_name' pk=object.id %}
{% url 'view_name' as the_url %}  {# Assign to variable #}

{# Use in context #}
<a href="{% url 'article_detail' article.pk %}">Read more</a>
```

**static:**
```django
{% load static %}
<img src="{% static 'images/logo.png' %}" alt="Logo">
<link rel="stylesheet" href="{% static 'css/style.css' %}">

{# Assign to variable #}
{% static 'images/logo.png' as logo_url %}
<img src="{{ logo_url }}" alt="Logo">
```

**get_static_prefix:**
```django
{% load static %}
{% get_static_prefix as STATIC_PREFIX %}
<script>var STATIC_URL = "{{ STATIC_PREFIX }}";</script>
```

### Variable Assignment

**with:**
```django
{% with total=business.employees.count %}
    {{ total }} employee{{ total|pluralize }}
{% endwith %}

{# Multiple variables #}
{% with alpha=1 beta=2 %}
    Sum: {{ alpha|add:beta }}
{% endwith %}
```

**as (in various tags):**
```django
{% url 'view_name' as the_url %}
{% static 'file.js' as js_url %}
{% get_current_language as LANGUAGE %}
```

### Template Context

**csrf_token:**
```django
<form method="post">
    {% csrf_token %}
    ...
</form>
```

**now:**
```django
{% now "Y-m-d H:i" %}
{% now "Y" as current_year %}
```

**lorem:**
```django
{% lorem %}          {# 1 paragraph #}
{% lorem 3 p %}      {# 3 paragraphs #}
{% lorem 10 w %}     {# 10 words #}
```

### Cycles and Counters

**cycle:**
```django
{% for item in items %}
    <tr class="{% cycle 'row1' 'row2' %}">
        <td>{{ item }}</td>
    </tr>
{% endfor %}

{# Named cycle #}
{% for item in items %}
    <tr class="{% cycle 'row1' 'row2' as rowcolors %}">
        ...
    </tr>
{% endfor %}
{% cycle rowcolors %}  {# Advance to next value #}
```

**resetcycle:**
```django
{% for group in groups %}
    <h2>{{ group.name }}</h2>
    {% for item in group.items %}
        <li class="{% cycle 'odd' 'even' %}">{{ item }}</li>
    {% endfor %}
    {% resetcycle %}
{% endfor %}
```

### Filtering and Reordering

**filter:**
```django
{% filter lower|escape %}
    This TEXT will be lowercase and escaped.
{% endfilter %}
```

**regroup:**
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

## Comments

### Single Line
```django
{# This is a comment #}
```

### Multi-line
```django
{% comment %}
    This is a multi-line comment.
    It can span multiple lines.
{% endcomment %}
```

### Preventing Rendering
```django
{% comment %}
    {% if user.is_admin %}
        This code is disabled
    {% endif %}
{% endcomment %}
```

## Template Inheritance

### Pattern
```django
{# base.html #}
<!DOCTYPE html>
<html>
<head>
    <title>{% block title %}Default Title{% endblock %}</title>
</head>
<body>
    {% block content %}{% endblock %}
</body>
</html>

{# child.html #}
{% extends "base.html" %}

{% block title %}Page Title{% endblock %}

{% block content %}
    <h1>Content</h1>
{% endblock %}
```

### Using block.super
```django
{% block title %}
    {{ block.super }} - Additional Title
{% endblock %}
```

### Multiple Inheritance Levels
```django
base.html → section_base.html → page.html
```

## Escaping

### Auto-escaping (Default)
```django
{{ user_input }}  {# Automatically escaped #}
```

Auto-escaping converts:
- `<` → `&lt;`
- `>` → `&gt;`
- `'` → `&#x27;`
- `"` → `&quot;`
- `&` → `&amp;`

### Mark as Safe
```django
{{ trusted_html|safe }}
```

### Disable Auto-escaping
```django
{% autoescape off %}
    {{ html_content }}
{% endautoescape %}
```

### Force Escaping
```django
{% autoescape off %}
    {{ untrusted|escape }}  {# Still escaped #}
{% endautoescape %}
```

### JavaScript Escaping
```django
<script>
    var message = "{{ message|escapejs }}";
</script>
```

## Whitespace Control

### Default Behavior
```django
{% if True %}
    Text
{% endif %}
```
Renders with whitespace preserved.

### Manual Control
```django
{%- if True -%}
    Text
{%- endif -%}
```
The `-` removes whitespace before/after the tag.

**Note:** Django doesn't have built-in whitespace control like Jinja2. Use filters or formatting for precise control.

### Spaceless Tag
```django
{% spaceless %}
    <p>
        <a href="...">Link</a>
    </p>
{% endspaceless %}
```
Removes whitespace between HTML tags (not inside tags).

## Advanced Patterns

### Conditional Assignment
```django
{% if expensive_query %}
    {% with result=expensive_query %}
        {{ result }}
    {% endwith %}
{% endif %}
```

### Template Variable in URL
```django
{% for item in items %}
    <a href="{% url 'detail' item.pk %}">{{ item.name }}</a>
{% endfor %}
```

### Dynamic Template Names
```django
{% include template_name %}  {# template_name from context #}

{% with template_name="partials/header.html" %}
    {% include template_name %}
{% endwith %}
```

### Complex Conditionals
```django
{% if user.is_authenticated and user.profile.is_complete or user.is_staff %}
    {# Note: 'and' has higher precedence than 'or' #}
{% endif %}
```

### Nested Blocks
```django
{# base.html #}
{% block outer %}
    <div>
        {% block inner %}Default{% endblock %}
    </div>
{% endblock %}

{# child.html #}
{% block outer %}
    {{ block.super }}  {# Includes outer div and inner block #}
    Additional content
{% endblock %}

{# grandchild.html #}
{% block inner %}Override inner only{% endblock %}
```

## Best Practices

1. **Keep logic minimal** - Move complex logic to views or template tags
2. **Use meaningful variable names** - Clear context variable names
3. **Comment complex sections** - Explain non-obvious template logic
4. **Consistent block naming** - Use standard names (content, title, etc.)
5. **Avoid deep nesting** - Keep template inheritance shallow
6. **Escape user input** - Never use `|safe` on untrusted data
7. **Use `{% load %}` at top** - Load tag libraries before use
8. **Close all blocks** - Always match opening and closing tags

## Common Errors

### TemplateSyntaxError
```
Invalid block tag: 'endfor', expected 'endif'
```
**Cause:** Mismatched or misordered tags

### VariableDoesNotExist
```
Failed lookup for key [field] in ...
```
**Cause:** Variable not in context or typo

### Template Not Found
```
TemplateDoesNotExist at /path/
```
**Cause:** Template path incorrect or not in template directories
