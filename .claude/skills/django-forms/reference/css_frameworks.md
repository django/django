# CSS Frameworks Integration Reference

Complete guide to integrating Django forms with popular CSS frameworks and ensuring accessibility.

## Table of Contents

- [Bootstrap 5 Integration](#bootstrap-5-integration)
- [Tailwind CSS Integration](#tailwind-css-integration)
- [Accessibility (WCAG)](#accessibility-wcag)
- [Error Display Patterns](#error-display-patterns)
- [Form Rendering Strategies](#form-rendering-strategies)

## Bootstrap 5 Integration

### Basic Bootstrap Form

```python
# forms.py
from django import forms

class BootstrapFormMixin:
    """Mixin to add Bootstrap classes to all form fields."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            widget = field.widget

            # Text inputs, textareas, selects
            if isinstance(widget, (forms.TextInput, forms.EmailInput,
                                   forms.URLInput, forms.NumberInput,
                                   forms.DateInput, forms.TimeInput,
                                   forms.DateTimeInput, forms.Textarea)):
                widget.attrs['class'] = widget.attrs.get('class', '') + ' form-control'

            elif isinstance(widget, forms.Select):
                widget.attrs['class'] = widget.attrs.get('class', '') + ' form-select'

            elif isinstance(widget, forms.CheckboxInput):
                widget.attrs['class'] = widget.attrs.get('class', '') + ' form-check-input'

            elif isinstance(widget, forms.FileInput):
                widget.attrs['class'] = widget.attrs.get('class', '') + ' form-control'

class ContactForm(BootstrapFormMixin, forms.Form):
    name = forms.CharField(max_length=100)
    email = forms.EmailField()
    message = forms.CharField(widget=forms.Textarea(attrs={'rows': 5}))
```

**Template:**
```django
<form method="post" novalidate>
  {% csrf_token %}

  {% for field in form %}
    <div class="mb-3">
      <label for="{{ field.id_for_label }}" class="form-label">
        {{ field.label }}
        {% if field.field.required %}<span class="text-danger">*</span>{% endif %}
      </label>

      {{ field }}

      {% if field.help_text %}
        <div class="form-text">{{ field.help_text }}</div>
      {% endif %}

      {% if field.errors %}
        <div class="invalid-feedback d-block">
          {{ field.errors.0 }}
        </div>
      {% endif %}
    </div>
  {% endfor %}

  {% if form.non_field_errors %}
    <div class="alert alert-danger">
      {{ form.non_field_errors }}
    </div>
  {% endif %}

  <button type="submit" class="btn btn-primary">Submit</button>
</form>
```

### Bootstrap with Validation States

```python
# forms.py
class BootstrapForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Add Bootstrap classes
        for field_name, field in self.fields.items():
            widget = field.widget

            if isinstance(widget, (forms.TextInput, forms.EmailInput,
                                   forms.URLInput, forms.NumberInput,
                                   forms.Textarea, forms.Select)):
                css_class = 'form-control' if not isinstance(widget, forms.Select) else 'form-select'

                # Add is-invalid class if field has errors
                if self.errors.get(field_name):
                    css_class += ' is-invalid'

                widget.attrs['class'] = css_class

    name = forms.CharField(max_length=100)
    email = forms.EmailField()
```

**Template with client-side validation:**
```django
<form method="post" class="needs-validation" novalidate>
  {% csrf_token %}

  {% for field in form %}
    <div class="mb-3">
      <label for="{{ field.id_for_label }}" class="form-label">{{ field.label }}</label>

      {% if field.field.widget_type == 'checkbox' %}
        <div class="form-check">
          {{ field }}
          <label class="form-check-label" for="{{ field.id_for_label }}">
            {{ field.label }}
          </label>
        </div>
      {% else %}
        {{ field }}
      {% endif %}

      {% if field.errors %}
        <div class="invalid-feedback">
          {{ field.errors.0 }}
        </div>
      {% else %}
        {% if field.help_text %}
          <div class="form-text">{{ field.help_text }}</div>
        {% endif %}
      {% endif %}
    </div>
  {% endfor %}

  <button type="submit" class="btn btn-primary">Submit</button>
</form>

<script>
// Bootstrap validation
(function () {
  'use strict'
  var forms = document.querySelectorAll('.needs-validation')
  Array.prototype.slice.call(forms).forEach(function (form) {
    form.addEventListener('submit', function (event) {
      if (!form.checkValidity()) {
        event.preventDefault()
        event.stopPropagation()
      }
      form.classList.add('was-validated')
    }, false)
  })
})()
</script>
```

### Bootstrap Form Layouts

#### Horizontal Form

```django
<form method="post">
  {% csrf_token %}

  {% for field in form %}
    <div class="row mb-3">
      <label for="{{ field.id_for_label }}" class="col-sm-3 col-form-label">
        {{ field.label }}
      </label>
      <div class="col-sm-9">
        {{ field }}
        {% if field.errors %}
          <div class="invalid-feedback d-block">{{ field.errors.0 }}</div>
        {% endif %}
        {% if field.help_text %}
          <div class="form-text">{{ field.help_text }}</div>
        {% endif %}
      </div>
    </div>
  {% endfor %}

  <div class="row">
    <div class="col-sm-9 offset-sm-3">
      <button type="submit" class="btn btn-primary">Submit</button>
    </div>
  </div>
</form>
```

#### Inline Form

```django
<form method="post" class="row row-cols-lg-auto g-3 align-items-center">
  {% csrf_token %}

  {% for field in form %}
    <div class="col-12">
      <label class="visually-hidden" for="{{ field.id_for_label }}">
        {{ field.label }}
      </label>
      {{ field }}
    </div>
  {% endfor %}

  <div class="col-12">
    <button type="submit" class="btn btn-primary">Submit</button>
  </div>
</form>
```

### Using django-crispy-forms

```bash
pip install django-crispy-forms crispy-bootstrap5
```

```python
# settings.py
INSTALLED_APPS = [
    # ...
    'crispy_forms',
    'crispy_bootstrap5',
]

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"
```

```python
# forms.py
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, Div, Field

class ContactForm(forms.Form):
    name = forms.CharField()
    email = forms.EmailField()
    phone = forms.CharField()
    message = forms.CharField(widget=forms.Textarea)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('name', css_class='form-group col-md-6 mb-0'),
                Column('email', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            'phone',
            'message',
            Submit('submit', 'Send Message', css_class='btn btn-primary')
        )
```

**Template:**
```django
{% load crispy_forms_tags %}

<form method="post">
  {% csrf_token %}
  {% crispy form %}
</form>
```

## Tailwind CSS Integration

### Basic Tailwind Form

```python
# forms.py
class TailwindFormMixin:
    """Mixin to add Tailwind classes to all form fields."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            widget = field.widget

            base_classes = 'block w-full rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500'

            if isinstance(widget, (forms.TextInput, forms.EmailInput,
                                   forms.URLInput, forms.NumberInput,
                                   forms.DateInput, forms.TimeInput,
                                   forms.DateTimeInput)):
                widget.attrs['class'] = f'{base_classes} sm:text-sm border-gray-300'

            elif isinstance(widget, forms.Textarea):
                widget.attrs['class'] = f'{base_classes} sm:text-sm border-gray-300'

            elif isinstance(widget, forms.Select):
                widget.attrs['class'] = f'{base_classes} sm:text-sm border-gray-300'

            elif isinstance(widget, forms.CheckboxInput):
                widget.attrs['class'] = 'h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded'

            elif isinstance(widget, forms.FileInput):
                widget.attrs['class'] = 'block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100'

class ContactForm(TailwindFormMixin, forms.Form):
    name = forms.CharField(max_length=100)
    email = forms.EmailField()
    message = forms.CharField(widget=forms.Textarea(attrs={'rows': 4}))
```

**Template:**
```django
<form method="post" class="space-y-6">
  {% csrf_token %}

  {% for field in form %}
    <div>
      <label for="{{ field.id_for_label }}" class="block text-sm font-medium text-gray-700">
        {{ field.label }}
        {% if field.field.required %}
          <span class="text-red-500">*</span>
        {% endif %}
      </label>

      <div class="mt-1">
        {{ field }}
      </div>

      {% if field.help_text %}
        <p class="mt-2 text-sm text-gray-500">{{ field.help_text }}</p>
      {% endif %}

      {% if field.errors %}
        <p class="mt-2 text-sm text-red-600">
          {{ field.errors.0 }}
        </p>
      {% endif %}
    </div>
  {% endfor %}

  {% if form.non_field_errors %}
    <div class="rounded-md bg-red-50 p-4">
      <div class="flex">
        <div class="ml-3">
          <h3 class="text-sm font-medium text-red-800">
            There were errors with your submission
          </h3>
          <div class="mt-2 text-sm text-red-700">
            <ul class="list-disc pl-5 space-y-1">
              {% for error in form.non_field_errors %}
                <li>{{ error }}</li>
              {% endfor %}
            </ul>
          </div>
        </div>
      </div>
    </div>
  {% endif %}

  <div>
    <button type="submit" class="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500">
      Submit
    </button>
  </div>
</form>
```

### Tailwind with Error States

```python
class TailwindForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field_name, field in self.fields.items():
            widget = field.widget

            # Base classes
            base = 'block w-full rounded-md shadow-sm sm:text-sm'
            focus = 'focus:ring-indigo-500 focus:border-indigo-500'

            # Error state classes
            if self.errors.get(field_name):
                border = 'border-red-300 text-red-900 placeholder-red-300'
                focus = 'focus:ring-red-500 focus:border-red-500'
            else:
                border = 'border-gray-300'

            if isinstance(widget, (forms.TextInput, forms.EmailInput,
                                   forms.URLInput, forms.NumberInput,
                                   forms.Textarea, forms.Select)):
                widget.attrs['class'] = f'{base} {border} {focus}'

    name = forms.CharField()
    email = forms.EmailField()
```

### Using django-tailwind

```bash
pip install django-tailwind
python manage.py tailwind init
```

See: https://django-tailwind.readthedocs.io/

## Accessibility (WCAG)

### Essential ARIA Attributes

```python
class AccessibleForm(forms.Form):
    name = forms.CharField(
        label='Full Name',
        help_text='Enter your first and last name',
        widget=forms.TextInput(attrs={
            'aria-label': 'Full Name',
            'aria-describedby': 'name-help',
            'aria-required': 'true',
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Add aria-invalid to fields with errors
        for field_name, field in self.fields.items():
            if self.errors.get(field_name):
                field.widget.attrs['aria-invalid'] = 'true'
                field.widget.attrs['aria-describedby'] = f'{field_name}-error'
```

**Template:**
```django
<form method="post" novalidate>
  {% csrf_token %}

  {% for field in form %}
    <div class="form-group">
      <label for="{{ field.id_for_label }}">
        {{ field.label }}
        {% if field.field.required %}
          <abbr title="required" aria-label="required">*</abbr>
        {% endif %}
      </label>

      {{ field }}

      {% if field.help_text %}
        <small id="{{ field.name }}-help" class="form-text">
          {{ field.help_text }}
        </small>
      {% endif %}

      {% if field.errors %}
        <div id="{{ field.name }}-error" class="error-message" role="alert">
          {{ field.errors.0 }}
        </div>
      {% endif %}
    </div>
  {% endfor %}

  <button type="submit">Submit</button>
</form>
```

### WCAG 2.1 Compliance Checklist

**Level A (Must Have):**

- [ ] All form inputs have associated labels
- [ ] Required fields are marked (visually and in code)
- [ ] Error messages are clear and specific
- [ ] Form can be completed using keyboard only
- [ ] Color is not the only way to convey information

**Level AA (Should Have):**

- [ ] Labels are visible (not just placeholder)
- [ ] Error messages are programmatically associated with fields
- [ ] Focus indicators are clearly visible
- [ ] Text has sufficient color contrast (4.5:1)
- [ ] Form instructions are provided before form

**Level AAA (Nice to Have):**

- [ ] Help text is available for complex inputs
- [ ] Suggestions are provided for correcting errors
- [ ] Forms can be submitted/confirmed before final submission

### Accessible Form Pattern

```python
# forms.py
class AccessibleFormMixin:
    """Add accessibility attributes to all fields."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field_name, field in self.fields.items():
            widget = field.widget
            field_id = widget.attrs.get('id') or field.auto_id

            # Required fields
            if field.required:
                widget.attrs['aria-required'] = 'true'
                widget.attrs['required'] = 'required'

            # Help text
            if field.help_text:
                widget.attrs['aria-describedby'] = f'{field_id}-help'

            # Errors
            if self.errors.get(field_name):
                widget.attrs['aria-invalid'] = 'true'
                describedby = widget.attrs.get('aria-describedby', '')
                widget.attrs['aria-describedby'] = f'{describedby} {field_id}-error'.strip()

            # Autocomplete
            autocomplete_map = {
                'email': 'email',
                'username': 'username',
                'password': 'current-password',
                'first_name': 'given-name',
                'last_name': 'family-name',
                'phone': 'tel',
                'address': 'street-address',
                'city': 'address-level2',
                'zip_code': 'postal-code',
                'country': 'country-name',
            }
            if field_name in autocomplete_map:
                widget.attrs['autocomplete'] = autocomplete_map[field_name]
```

**Template:**
```django
<form method="post" novalidate>
  {% csrf_token %}

  <!-- Form-level errors announced to screen readers -->
  {% if form.errors %}
    <div class="alert alert-danger" role="alert" aria-live="assertive">
      <h2>There were {{ form.errors|length }} error(s) with your submission:</h2>
      <ul>
        {% for field, errors in form.errors.items %}
          {% for error in errors %}
            <li><a href="#id_{{ field }}">{{ field }}: {{ error }}</a></li>
          {% endfor %}
        {% endfor %}
      </ul>
    </div>
  {% endif %}

  {% for field in form %}
    <div class="form-group">
      <label for="{{ field.id_for_label }}">
        {{ field.label }}
        {% if field.field.required %}
          <abbr title="required" aria-label="required">*</abbr>
        {% endif %}
      </label>

      {{ field }}

      {% if field.help_text %}
        <small id="{{ field.auto_id }}-help" class="form-text">
          {{ field.help_text }}
        </small>
      {% endif %}

      {% if field.errors %}
        <div id="{{ field.auto_id }}-error" class="error" role="alert">
          <span class="visually-hidden">Error:</span>
          {{ field.errors.0 }}
        </div>
      {% endif %}
    </div>
  {% endfor %}

  <button type="submit">Submit</button>
</form>
```

### Screen Reader Friendly Forms

```django
<!-- Use fieldset for grouped inputs -->
<fieldset>
  <legend>Contact Information</legend>

  <div class="form-group">
    <label for="id_email">Email</label>
    <input type="email" name="email" id="id_email"
           aria-describedby="email-help"
           aria-required="true">
    <small id="email-help">We'll never share your email.</small>
  </div>

  <div class="form-group">
    <label for="id_phone">Phone</label>
    <input type="tel" name="phone" id="id_phone"
           aria-describedby="phone-help">
    <small id="phone-help">Format: (123) 456-7890</small>
  </div>
</fieldset>

<!-- Use role="alert" for dynamic error messages -->
<div id="form-errors" role="alert" aria-live="polite"></div>

<!-- Hide decorative elements from screen readers -->
<span aria-hidden="true">★</span>
```

## Error Display Patterns

### Inline Errors (Recommended)

```django
<div class="form-group {% if field.errors %}has-error{% endif %}">
  <label for="{{ field.id_for_label }}">{{ field.label }}</label>
  {{ field }}
  {% if field.errors %}
    <span class="error-message" role="alert">
      {{ field.errors.0 }}
    </span>
  {% endif %}
</div>
```

### Summary Errors (Top of Form)

```django
{% if form.errors %}
  <div class="alert alert-danger" role="alert">
    <h2>Please correct the following errors:</h2>
    <ul>
      {% for field in form %}
        {% for error in field.errors %}
          <li>
            <a href="#{{ field.auto_id }}">{{ field.label }}: {{ error }}</a>
          </li>
        {% endfor %}
      {% endfor %}
      {% for error in form.non_field_errors %}
        <li>{{ error }}</li>
      {% endfor %}
    </ul>
  </div>
{% endif %}
```

### Toast Notifications (JavaScript)

```javascript
// Show errors as toast notifications
document.querySelectorAll('.form-error').forEach(error => {
    // Using Bootstrap Toast
    const toast = new bootstrap.Toast(document.getElementById('error-toast'));
    document.getElementById('error-message').textContent = error.textContent;
    toast.show();
});
```

### Modal Errors

```django
<!-- Trigger modal on errors -->
{% if form.errors %}
  <div class="modal fade show" id="errorModal" tabindex="-1" role="dialog"
       aria-labelledby="errorModalLabel" style="display: block;">
    <div class="modal-dialog" role="document">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title" id="errorModalLabel">Form Errors</h5>
          <button type="button" class="close" data-dismiss="modal">
            <span aria-hidden="true">&times;</span>
          </button>
        </div>
        <div class="modal-body">
          <ul>
            {% for field in form %}
              {% for error in field.errors %}
                <li>{{ field.label }}: {{ error }}</li>
              {% endfor %}
            {% endfor %}
          </ul>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-primary" data-dismiss="modal">
            OK
          </button>
        </div>
      </div>
    </div>
  </div>
{% endif %}
```

## Form Rendering Strategies

### Strategy 1: Manual Field Rendering (Most Control)

```django
<form method="post">
  {% csrf_token %}

  <div class="form-group">
    <label for="{{ form.name.id_for_label }}">Name</label>
    <input type="text"
           name="{{ form.name.name }}"
           value="{{ form.name.value|default:'' }}"
           class="form-control {% if form.name.errors %}is-invalid{% endif %}"
           id="{{ form.name.id_for_label }}"
           {% if form.name.field.required %}required{% endif %}>
    {% if form.name.errors %}
      <div class="invalid-feedback">{{ form.name.errors.0 }}</div>
    {% endif %}
  </div>

  <button type="submit">Submit</button>
</form>
```

### Strategy 2: as_p / as_table / as_ul (Quick, Less Control)

```django
<form method="post">
  {% csrf_token %}
  {{ form.as_p }}
  <button type="submit">Submit</button>
</form>
```

### Strategy 3: Loop Over Fields (Good Balance)

```django
<form method="post">
  {% csrf_token %}

  {% for field in form %}
    <div class="form-group">
      {{ field.label_tag }}
      {{ field }}
      {% if field.help_text %}
        <small>{{ field.help_text }}</small>
      {% endif %}
      {% if field.errors %}
        <div class="error">{{ field.errors }}</div>
      {% endif %}
    </div>
  {% endfor %}

  <button type="submit">Submit</button>
</form>
```

### Strategy 4: Template Tag (Reusable)

```python
# templatetags/form_tags.py
from django import template

register = template.Library()

@register.inclusion_tag('forms/field.html')
def render_field(field):
    return {'field': field}
```

**Template (forms/field.html):**
```django
<div class="form-group {% if field.errors %}has-error{% endif %}">
  <label for="{{ field.id_for_label }}" class="form-label">
    {{ field.label }}
    {% if field.field.required %}<span class="required">*</span>{% endif %}
  </label>

  {{ field }}

  {% if field.help_text %}
    <small class="form-text">{{ field.help_text }}</small>
  {% endif %}

  {% if field.errors %}
    <div class="invalid-feedback d-block">
      {{ field.errors.0 }}
    </div>
  {% endif %}
</div>
```

**Usage:**
```django
{% load form_tags %}

<form method="post">
  {% csrf_token %}
  {% for field in form %}
    {% render_field field %}
  {% endfor %}
  <button type="submit">Submit</button>
</form>
```

## Best Practices

1. **Use semantic HTML**: `<fieldset>`, `<legend>`, proper labels
2. **Always include labels**: Never rely only on placeholders
3. **Mark required fields**: Both visually and programmatically
4. **Provide clear error messages**: Specific, actionable guidance
5. **Test with keyboard only**: Ensure full keyboard accessibility
6. **Test with screen reader**: Use NVDA, JAWS, or VoiceOver
7. **Use appropriate input types**: Improves mobile UX
8. **Add autocomplete attributes**: Helps users fill forms faster
9. **Consider color contrast**: Minimum 4.5:1 ratio
10. **Validate on client and server**: Never trust client-side only

## See Also

- **Widgets:** `/home/user/django/.claude/skills/django-forms/reference/widgets.md`
- **AJAX Patterns:** `/home/user/django/.claude/skills/django-forms/reference/ajax_patterns.md`
- **Accessibility Checker:** `/home/user/django/.claude/skills/django-forms/scripts/accessibility_check.py`
