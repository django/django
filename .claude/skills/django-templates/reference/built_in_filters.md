# Django Built-in Template Filters Reference

Complete reference for all Django built-in template filters.

## Table of Contents
- [String Filters](#string-filters)
- [HTML and Escaping Filters](#html-and-escaping-filters)
- [List and Sequence Filters](#list-and-sequence-filters)
- [Number Filters](#number-filters)
- [Date and Time Filters](#date-and-time-filters)
- [Logic Filters](#logic-filters)
- [URL Filters](#url-filters)
- [Utility Filters](#utility-filters)

## String Filters

### lower
Convert string to lowercase.
```django
{{ "HELLO WORLD"|lower }}
{# Output: hello world #}

{{ user.name|lower }}
```

### upper
Convert string to uppercase.
```django
{{ "hello world"|upper }}
{# Output: HELLO WORLD #}
```

### title
Convert to title case (first letter of each word capitalized).
```django
{{ "hello world"|title }}
{# Output: Hello World #}
```

### capfirst
Capitalize the first character.
```django
{{ "hello world"|capfirst }}
{# Output: Hello world #}
```

### center
Center string in field of given width.
```django
{{ "Django"|center:15 }}
{# Output: "     Django     " #}
```

### ljust
Left-align string in field of given width.
```django
{{ "Django"|ljust:10 }}
{# Output: "Django    " #}
```

### rjust
Right-align string in field of given width.
```django
{{ "Django"|rjust:10 }}
{# Output: "    Django" #}
```

### cut
Remove all occurrences of argument from string.
```django
{{ "String with spaces"|cut:" " }}
{# Output: Stringwithspaces #}

{{ "hello world"|cut:"l" }}
{# Output: heo word #}
```

### slugify
Convert to ASCII, convert spaces to hyphens, remove non-alphanumerics.
```django
{{ "Joel is a slug"|slugify }}
{# Output: joel-is-a-slug #}

{{ "This is a test!!!"|slugify }}
{# Output: this-is-a-test #}
```

### wordcount
Count number of words.
```django
{{ "The quick brown fox"|wordcount }}
{# Output: 4 #}
```

### truncatewords
Truncate after specified number of words.
```django
{{ "This is a long sentence with many words"|truncatewords:5 }}
{# Output: This is a long sentence ... #}
```

### truncatewords_html
Truncate after specified words, respecting HTML tags.
```django
{{ "<p>This is a <strong>long</strong> sentence</p>"|truncatewords_html:3 }}
{# Output: <p>This is a ...</p> #}
```

### truncatechars
Truncate after specified number of characters.
```django
{{ "This is a long string"|truncatechars:13 }}
{# Output: This is a ... #}
```

### truncatechars_html
Truncate after specified characters, respecting HTML tags.
```django
{{ "<p>This is text</p>"|truncatechars_html:9 }}
{# Output: <p>This ...</p> #}
```

### wordwrap
Wrap words at specified line length.
```django
{{ "This is a long line that needs wrapping"|wordwrap:10 }}
{# Wraps at 10 characters #}
```

### add
Add argument to value (works for numbers and strings).
```django
{{ 4|add:2 }}
{# Output: 6 #}

{{ "hello "|add:"world" }}
{# Output: hello world #}

{{ [1, 2, 3]|add:[4, 5] }}
{# Output: [1, 2, 3, 4, 5] #}
```

### addslashes
Add slashes before quotes (for JavaScript strings).
```django
{{ "I'm using Django"|addslashes }}
{# Output: I\'m using Django #}
```

### stringformat
Format value using Python's string formatting.
```django
{{ 123|stringformat:"05d" }}
{# Output: 00123 #}

{{ 3.14159|stringformat:".2f" }}
{# Output: 3.14 #}
```

## HTML and Escaping Filters

### escape
Escape HTML characters.
```django
{{ "<script>alert('XSS')</script>"|escape }}
{# Output: &lt;script&gt;alert(&#x27;XSS&#x27;)&lt;/script&gt; #}
```

### force_escape
Force HTML escaping even if already marked safe.
```django
{{ value|force_escape }}
```

### safe
Mark string as safe (no escaping).
```django
{{ "<strong>Bold</strong>"|safe }}
{# Output: <strong>Bold</strong> #}
```

**Warning:** Never use on untrusted user input!

### escapejs
Escape for use in JavaScript strings.
```django
<script>
    var message = "{{ message|escapejs }}";
</script>
```

### linebreaks
Convert newlines to `<p>` and `<br>` tags.
```django
{{ "Line 1\nLine 2\n\nLine 3"|linebreaks }}
{# Output: <p>Line 1<br>Line 2</p><p>Line 3</p> #}
```

### linebreaksbr
Convert newlines to `<br>` tags.
```django
{{ "Line 1\nLine 2"|linebreaksbr }}
{# Output: Line 1<br>Line 2 #}
```

### striptags
Remove all HTML tags.
```django
{{ "<p>Hello <strong>world</strong>!</p>"|striptags }}
{# Output: Hello world! #}
```

### removetags
Remove specified HTML tags.
```django
{{ "<p>Hello <a href='#'>world</a>!</p>"|removetags:"a" }}
{# Output: <p>Hello world!</p> #}
```

**Note:** Deprecated in Django 2.1+ due to security concerns. Use `striptags` or a library like bleach.

## List and Sequence Filters

### first
Return first item in list.
```django
{{ [1, 2, 3]|first }}
{# Output: 1 #}

{{ "Django"|first }}
{# Output: D #}
```

### last
Return last item in list.
```django
{{ [1, 2, 3]|last }}
{# Output: 3 #}

{{ "Django"|last }}
{# Output: o #}
```

### join
Join list with string.
```django
{{ ['apple', 'banana', 'cherry']|join:", " }}
{# Output: apple, banana, cherry #}

{{ [1, 2, 3]|join:" - " }}
{# Output: 1 - 2 - 3 #}
```

### length
Return length of value.
```django
{{ [1, 2, 3]|length }}
{# Output: 3 #}

{{ "Django"|length }}
{# Output: 6 #}

{{ user_list|length }}
```

### length_is
Check if length equals argument.
```django
{% if items|length_is:3 %}
    Exactly 3 items
{% endif %}
```

### slice
Return slice of sequence.
```django
{{ "Django"|slice:":2" }}
{# Output: Dj #}

{{ [1, 2, 3, 4, 5]|slice:"1:4" }}
{# Output: [2, 3, 4] #}

{{ items|slice:":3" }}
{# First 3 items #}
```

### dictsort
Sort list of dictionaries by key.
```django
{{ value|dictsort:"name" }}
```

**Example:**
```django
{% for person in people|dictsort:"age" %}
    {{ person.name }}: {{ person.age }}
{% endfor %}
```

### dictsortreversed
Sort list of dictionaries in reverse by key.
```django
{{ value|dictsortreversed:"name" }}
```

### random
Return random item from list.
```django
{{ [1, 2, 3, 4, 5]|random }}
{# Randomly returns one item #}
```

### unordered_list
Recursively format list as HTML `<ul>`.
```django
{{ items|unordered_list }}
```

**Example:**
```django
{# Given: ['States', ['Kansas', ['Lawrence', 'Topeka'], 'Illinois']] #}
<ul>
    <li>States
        <ul>
            <li>Kansas
                <ul>
                    <li>Lawrence</li>
                    <li>Topeka</li>
                </ul>
            </li>
            <li>Illinois</li>
        </ul>
    </li>
</ul>
```

## Number Filters

### floatformat
Format float to specified decimal places.
```django
{{ 34.23234|floatformat }}
{# Output: 34.2 (default 1 decimal) #}

{{ 34.23234|floatformat:3 }}
{# Output: 34.232 #}

{{ 34.00000|floatformat:2 }}
{# Output: 34 (removes unnecessary zeros) #}

{{ 34.26000|floatformat:"-3" }}
{# Output: 34.260 (negative arg forces trailing zeros) #}
```

### divisibleby
Check if value is divisible by argument.
```django
{% if value|divisibleby:3 %}
    Divisible by 3
{% endif %}

{{ 21|divisibleby:7 }}
{# Output: True #}
```

### get_digit
Return specified digit (1-indexed from right).
```django
{{ 123456789|get_digit:1 }}
{# Output: 9 (rightmost digit) #}

{{ 123456789|get_digit:5 }}
{# Output: 5 #}
```

### phone2numeric
Convert phone letters to numbers.
```django
{{ "1-800-COLLECT"|phone2numeric }}
{# Output: 1-800-2655328 #}
```

## Date and Time Filters

### date
Format date.
```django
{{ value|date:"Y-m-d" }}
{# Output: 2024-03-15 #}

{{ value|date:"D d M Y" }}
{# Output: Fri 15 Mar 2024 #}

{{ value|date:"SHORT_DATE_FORMAT" }}
{# Uses Django's localized format #}
```

**Common format strings:**
```django
"Y-m-d"               {# 2024-03-15 #}
"d/m/Y"               {# 15/03/2024 #}
"F j, Y"              {# March 15, 2024 #}
"l, F j, Y"           {# Friday, March 15, 2024 #}
"D d M Y"             {# Fri 15 Mar 2024 #}
"Y-m-d H:i:s"         {# 2024-03-15 14:30:00 #}
```

### time
Format time.
```django
{{ value|time:"H:i" }}
{# Output: 14:30 #}

{{ value|time:"g:i A" }}
{# Output: 2:30 PM #}

{{ value|time:"TIME_FORMAT" }}
{# Uses Django's localized format #}
```

### timesince
Format as time since given date.
```django
{{ blog_date|timesince }}
{# Output: 3 days, 4 hours #}

{{ blog_date|timesince:other_date }}
{# Time since other_date #}
```

### timeuntil
Format as time until given date.
```django
{{ event_date|timeuntil }}
{# Output: 5 days, 2 hours #}

{{ event_date|timeuntil:from_date }}
{# Time until from from_date #}
```

### naturalday
Format date as "today", "yesterday", "tomorrow", or date.
```django
{{ some_date|naturalday }}
{# Output: today #}

{{ some_date|naturalday:"M d, Y" }}
{# Output: today or Mar 15, 2024 #}
```

### naturaltime
Format as natural time description.
```django
{{ datetime|naturaltime }}
{# Output: 3 seconds ago, 2 minutes ago, an hour ago, etc. #}
```

## Logic Filters

### default
Provide default value if variable is falsy.
```django
{{ value|default:"nothing" }}
{# If value is False, "", None, 0, empty list, returns "nothing" #}

{{ items|default:"No items available" }}
```

### default_if_none
Provide default only if variable is None.
```django
{{ value|default_if_none:"N/A" }}
{# Only returns "N/A" if value is None (not False or 0) #}
```

### yesno
Map True/False/None to custom strings.
```django
{{ value|yesno:"Yes,No,Maybe" }}
{# True → Yes, False → No, None → Maybe #}

{{ value|yesno:"yeah,nope" }}
{# True → yeah, False → nope, None → nope #}

{{ user.is_active|yesno:"Active,Inactive" }}
```

**Common use case:**
```django
<span class="badge badge-{{ user.is_active|yesno:'success,danger' }}">
    {{ user.is_active|yesno:"Active,Inactive" }}
</span>
```

### filesizeformat
Format number as file size.
```django
{{ 123456789|filesizeformat }}
{# Output: 117.7 MB #}

{{ 1024|filesizeformat }}
{# Output: 1.0 KB #}

{{ 1234567890123|filesizeformat }}
{# Output: 1.1 TB #}
```

## URL Filters

### urlencode
URL-encode value.
```django
{{ "hello world"|urlencode }}
{# Output: hello%20world #}

{{ "foo=bar&baz=qux"|urlencode }}
{# Output: foo%3Dbar%26baz%3Dqux #}
```

**Common use:**
```django
<a href="{% url 'search' %}?q={{ query|urlencode }}">Search</a>
```

### urlize
Convert URLs in text to clickable links.
```django
{{ "Visit https://djangoproject.com"|urlize }}
{# Output: Visit <a href="https://djangoproject.com">https://djangoproject.com</a> #}
```

### urlizetrunc
Convert URLs to links and truncate.
```django
{{ "Visit https://djangoproject.com/very/long/url"|urlizetrunc:20 }}
{# Truncates URL text to 20 characters #}
```

### iriencode
Convert IRI (Internationalized Resource Identifier) to URL.
```django
{{ "http://example.com/путь"|iriencode }}
{# Output: http://example.com/%D0%BF%D1%83%D1%82%D1%8C #}
```

## Utility Filters

### make_list
Convert value to list.
```django
{{ "Django"|make_list }}
{# Output: ['D', 'j', 'a', 'n', 'g', 'o'] #}

{{ 123|make_list }}
{# Output: ['1', '2', '3'] #}
```

### pprint
Pretty-print value (for debugging).
```django
{{ complex_object|pprint }}
```

### pluralize
Return plural suffix.
```django
You have {{ num_items }} item{{ num_items|pluralize }}
{# 1 item, 2 items, 0 items #}

{{ num_items }} cand{{ num_items|pluralize:"y,ies" }}
{# 1 candy, 2 candies #}

{{ num_items }} ox{{ num_items|pluralize:"en" }}
{# 1 ox, 2 oxen #}
```

### linenumbers
Display text with line numbers.
```django
{{ code|linenumbers }}
{# Output:
1. First line
2. Second line
3. Third line
#}
```

### json_script
Output value as JSON in script tag.
```django
{{ data|json_script:"user-data" }}
{# Output: <script id="user-data" type="application/json">{"key": "value"}</script> #}
```

**Usage with JavaScript:**
```django
{{ data|json_script:"my-data" }}
<script>
    const data = JSON.parse(document.getElementById('my-data').textContent);
</script>
```

### safeseq
Apply `safe` filter to each element in sequence.
```django
{{ html_list|safeseq|join:", " }}
```

## Chaining Filters

Filters can be chained together:

```django
{{ text|lower|truncatewords:10 }}
{{ user.bio|striptags|truncatechars:100 }}
{{ value|default:"N/A"|upper }}
```

**Order matters:**
```django
{{ "HELLO"|lower|capfirst }}
{# Output: Hello #}

{{ "HELLO"|capfirst|lower }}
{# Output: hello #}
```

## Custom Filter Arguments

### Using variables as arguments
```django
{{ value|truncatewords:max_words }}
{{ text|default:default_text }}
```

### Multiple arguments (some filters)
Most filters take 0 or 1 argument. The `pluralize` filter can take special syntax:
```django
{{ count|pluralize:"y,ies" }}
```

## Best Practices

### 1. Use appropriate escaping
```django
{# BAD - XSS vulnerability #}
{{ user_input|safe }}

{# GOOD #}
{{ user_input }}  {# Auto-escaped #}
{{ trusted_html|safe }}  {# Only for trusted sources #}
```

### 2. Chain filters efficiently
```django
{# BAD - unnecessary work #}
{{ value|upper|lower|upper }}

{# GOOD #}
{{ value|upper }}
```

### 3. Provide user-friendly defaults
```django
{# GOOD #}
{{ profile.bio|default:"No bio provided" }}
{{ post.published_date|date:"F j, Y"|default:"Not published" }}
```

### 4. Use appropriate date formats
```django
{# User-facing #}
{{ date|date:"F j, Y" }}  {# March 15, 2024 #}

{# API/data #}
{{ date|date:"Y-m-d" }}   {# 2024-03-15 #}

{# Relative #}
{{ date|naturaltime }}     {# 3 hours ago #}
```

### 5. Handle empty lists gracefully
```django
{% if items %}
    {{ items|join:", " }}
{% else %}
    No items available
{% endif %}
```

## Common Patterns

### Display count with proper pluralization
```django
{{ item_count }} item{{ item_count|pluralize }} found
```

### Format currency
```django
${{ price|floatformat:2 }}
```

### Safe HTML with fallback
```django
{{ content|striptags|truncatewords:50|default:"No content available" }}
```

### User-friendly dates
```django
Posted {{ post.created|naturaltime }}
{# or #}
Posted on {{ post.created|date:"F j, Y" }}
```

### Format lists for display
```django
Tags: {{ post.tags.all|join:", " }}
```

### Highlight search results
```django
{# Custom filter needed for actual highlighting #}
{{ text|truncatewords_html:50 }}
```

## Filter Availability

### Template-only filters
Some filters only work in templates:
- `json_script`
- `pprint`

### Available in code
Most filters can also be used in Python:
```python
from django.template.defaultfilters import slugify, truncatewords

slug = slugify("My Title")
excerpt = truncatewords(text, 50)
```

## Django Version Notes

### Django 4.x+
- `json_script` filter improved security
- Better handling of None values in various filters

### Django 5.x+
- Performance improvements in `truncatewords_html`
- Better Unicode handling in `slugify`

## Troubleshooting

### Filter returns empty string
```django
{{ value|some_filter }}  {# Nothing appears #}
```
**Check:**
- Is `value` in the context?
- Is the filter loaded? (`{% load custom_filters %}`)
- Does the filter return a value?

### Filter not found
```
Invalid filter: 'custom_filter'
```
**Fix:**
- Load the filter library: `{% load custom_filters %}`
- Check filter is registered
- Restart development server

### Unexpected escaping
```django
{{ html|safe|truncatewords:10 }}  {# Still escaped! #}
```
**Reason:** `truncatewords` returns escaped content. Use `truncatewords_html` instead.
