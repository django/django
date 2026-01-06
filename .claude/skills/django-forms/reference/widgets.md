# Django Form Widgets Reference

Complete guide to form widgets for customizing HTML rendering.

## Table of Contents

- [Widget Overview](#widget-overview)
- [Built-in Widgets](#built-in-widgets)
- [Widget Attributes](#widget-attributes)
- [Custom Widget Creation](#custom-widget-creation)
- [Widget Media (CSS/JS)](#widget-media-cssjs)
- [Widget Templates](#widget-templates)

## Widget Overview

Widgets control how form fields are rendered in HTML. They don't handle validation (that's the field's job).

**Key concepts:**
- One field → one or more widgets
- Widgets render HTML only
- Validation happens in field/form, not widget

## Built-in Widgets

### Text Input Widgets

#### TextInput

Single-line text input.

```python
from django import forms

class MyForm(forms.Form):
    name = forms.CharField(
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter your name',
            'class': 'form-control',
            'maxlength': '100',
        })
    )
```

**Renders:**
```html
<input type="text" name="name" placeholder="Enter your name" class="form-control" maxlength="100">
```

#### EmailInput

Email-specific input (HTML5).

```python
email = forms.EmailField(
    widget=forms.EmailInput(attrs={
        'placeholder': 'user@example.com',
        'autocomplete': 'email',
    })
)
```

**Renders:**
```html
<input type="email" name="email" placeholder="user@example.com" autocomplete="email">
```

#### URLInput

URL input with validation.

```python
website = forms.URLField(
    widget=forms.URLInput(attrs={
        'placeholder': 'https://example.com'
    })
)
```

#### NumberInput

Numeric input (HTML5).

```python
age = forms.IntegerField(
    widget=forms.NumberInput(attrs={
        'min': '0',
        'max': '150',
        'step': '1',
    })
)
```

#### PasswordInput

Password input (masked text).

```python
password = forms.CharField(
    widget=forms.PasswordInput(attrs={
        'placeholder': 'Enter password',
        'autocomplete': 'current-password',
    })
)

# Don't render value attribute (default behavior)
password_no_render = forms.CharField(
    widget=forms.PasswordInput(render_value=False)
)
```

#### HiddenInput

Hidden input field.

```python
user_id = forms.IntegerField(
    widget=forms.HiddenInput()
)
```

### Textarea Widget

Multi-line text input.

```python
description = forms.CharField(
    widget=forms.Textarea(attrs={
        'rows': 5,
        'cols': 40,
        'placeholder': 'Enter description...',
        'class': 'form-control',
    })
)
```

### Date and Time Widgets

#### DateInput

Date picker.

```python
# HTML5 date picker
birth_date = forms.DateField(
    widget=forms.DateInput(attrs={
        'type': 'date',
        'class': 'form-control',
    })
)

# Custom format
birth_date_custom = forms.DateField(
    widget=forms.DateInput(
        attrs={'placeholder': 'MM/DD/YYYY'},
        format='%m/%d/%Y',
    )
)
```

#### TimeInput

Time picker.

```python
appointment_time = forms.TimeField(
    widget=forms.TimeInput(attrs={
        'type': 'time',
        'class': 'form-control',
    })
)
```

#### DateTimeInput

Combined date and time.

```python
event_datetime = forms.DateTimeField(
    widget=forms.DateTimeInput(attrs={
        'type': 'datetime-local',
        'class': 'form-control',
    })
)
```

#### SelectDateWidget

Dropdown selectors for date.

```python
from django.forms.widgets import SelectDateWidget

birth_date = forms.DateField(
    widget=SelectDateWidget(
        years=range(1920, 2024),
        months={
            1: 'January', 2: 'February', 3: 'March',
            # ... etc
        },
        attrs={'class': 'form-select'}
    )
)
```

**Renders:** Three dropdowns (month, day, year).

### Checkbox and Radio Widgets

#### CheckboxInput

Single checkbox.

```python
agree = forms.BooleanField(
    widget=forms.CheckboxInput(attrs={
        'class': 'form-check-input'
    })
)
```

#### RadioSelect

Radio button group.

```python
PRIORITY_CHOICES = [
    ('low', 'Low'),
    ('medium', 'Medium'),
    ('high', 'High'),
]

priority = forms.ChoiceField(
    choices=PRIORITY_CHOICES,
    widget=forms.RadioSelect(attrs={
        'class': 'form-check-input'
    })
)
```

**Renders:**
```html
<div>
  <label><input type="radio" name="priority" value="low"> Low</label>
  <label><input type="radio" name="priority" value="medium"> Medium</label>
  <label><input type="radio" name="priority" value="high"> High</label>
</div>
```

#### CheckboxSelectMultiple

Multiple checkboxes.

```python
TAGS = [
    ('python', 'Python'),
    ('django', 'Django'),
    ('javascript', 'JavaScript'),
]

tags = forms.MultipleChoiceField(
    choices=TAGS,
    widget=forms.CheckboxSelectMultiple,
    required=False,
)
```

### Select Widgets

#### Select

Dropdown menu.

```python
STATUS_CHOICES = [
    ('', '--- Select Status ---'),
    ('draft', 'Draft'),
    ('published', 'Published'),
    ('archived', 'Archived'),
]

status = forms.ChoiceField(
    choices=STATUS_CHOICES,
    widget=forms.Select(attrs={
        'class': 'form-select'
    })
)
```

#### SelectMultiple

Multi-select dropdown (Ctrl+Click).

```python
categories = forms.MultipleChoiceField(
    choices=CATEGORY_CHOICES,
    widget=forms.SelectMultiple(attrs={
        'class': 'form-select',
        'size': '5',
    })
)
```

### File Upload Widgets

#### FileInput

Generic file upload.

```python
document = forms.FileField(
    widget=forms.FileInput(attrs={
        'accept': '.pdf,.doc,.docx',
        'class': 'form-control',
    })
)
```

#### ClearableFileInput

File upload with "clear" checkbox (default for FileField).

```python
avatar = forms.ImageField(
    widget=forms.ClearableFileInput(attrs={
        'accept': 'image/*',
        'class': 'form-control',
    })
)
```

**Renders:** File input + checkbox to clear existing file.

### Special Widgets

#### SplitDateTimeWidget

Separate date and time inputs.

```python
from django.forms.widgets import SplitDateTimeWidget

event_time = forms.DateTimeField(
    widget=SplitDateTimeWidget(
        date_attrs={'type': 'date', 'class': 'form-control'},
        time_attrs={'type': 'time', 'class': 'form-control'},
    )
)
```

#### SplitHiddenDateTimeWidget

Hidden date and time inputs.

```python
created_at = forms.DateTimeField(
    widget=forms.SplitHiddenDateTimeWidget()
)
```

## Widget Attributes

### Common HTML Attributes

```python
widget = forms.TextInput(attrs={
    # CSS
    'class': 'form-control custom-class',
    'style': 'width: 100%;',

    # HTML5
    'placeholder': 'Enter text...',
    'required': True,
    'readonly': True,
    'disabled': True,
    'autofocus': True,
    'autocomplete': 'name',

    # Data attributes
    'data-validate': 'true',
    'data-max-length': '100',

    # ARIA (accessibility)
    'aria-label': 'Search',
    'aria-describedby': 'help-text',
    'aria-required': 'true',

    # Input constraints
    'maxlength': '100',
    'minlength': '5',
    'pattern': '[A-Za-z]{3,}',

    # Numeric inputs
    'min': '0',
    'max': '100',
    'step': '0.01',
})
```

### Setting Attributes in Multiple Ways

```python
# Method 1: In field definition
class MyForm(forms.Form):
    name = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

# Method 2: In __init__
class MyForm(forms.Form):
    name = forms.CharField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter name'
        })

# Method 3: ModelForm Meta
class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'price']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Product name'
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
        }
```

### Conditional Attributes

```python
class ProductForm(forms.Form):
    name = forms.CharField()
    price = forms.DecimalField()

    def __init__(self, *args, is_admin=False, **kwargs):
        super().__init__(*args, **kwargs)

        if not is_admin:
            # Make price readonly for non-admins
            self.fields['price'].widget.attrs['readonly'] = True

        # Add Bootstrap classes to all fields
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
```

## Custom Widget Creation

### Basic Custom Widget

```python
from django.forms.widgets import Widget
from django.utils.html import format_html

class ColorPickerWidget(Widget):
    """Custom color picker widget."""

    template_name = 'widgets/color_picker.html'

    def get_context(self, name, value, attrs):
        """Add custom context data."""
        context = super().get_context(name, value, attrs)
        context['widget']['color_value'] = value or '#000000'
        return context

    def format_value(self, value):
        """Format value for display."""
        if value:
            return value.upper()
        return '#000000'

# Usage
class ThemeForm(forms.Form):
    primary_color = forms.CharField(
        widget=ColorPickerWidget(attrs={'class': 'color-picker'})
    )
```

**Template (widgets/color_picker.html):**
```django
<div class="color-picker-wrapper">
  <input type="color" name="{{ widget.name }}" value="{{ widget.color_value }}"
         {% include "django/forms/widgets/attrs.html" %}>
  <input type="text" value="{{ widget.color_value }}" readonly>
</div>
```

### Custom Widget with JavaScript

```python
from django.forms.widgets import Widget

class AutocompleteWidget(Widget):
    """Autocomplete text input."""

    template_name = 'widgets/autocomplete.html'

    def __init__(self, attrs=None, api_url=None):
        super().__init__(attrs)
        self.api_url = api_url

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context['widget']['api_url'] = self.api_url
        return context

    class Media:
        css = {
            'all': ('css/autocomplete.css',)
        }
        js = ('js/autocomplete.js',)

# Usage
class ProductForm(forms.Form):
    category = forms.CharField(
        widget=AutocompleteWidget(
            api_url='/api/categories/',
            attrs={'class': 'autocomplete-input'}
        )
    )
```

**Template (widgets/autocomplete.html):**
```django
<div class="autocomplete-wrapper" data-api-url="{{ widget.api_url }}">
  <input type="text" name="{{ widget.name }}" value="{{ widget.value|default:'' }}"
         {% include "django/forms/widgets/attrs.html" %}>
  <ul class="autocomplete-results"></ul>
</div>
```

### MultiWidget for Composite Fields

```python
from django.forms.widgets import MultiWidget, TextInput, Select

class PhoneWidget(MultiWidget):
    """Phone number with country code."""

    def __init__(self, attrs=None):
        widgets = [
            Select(attrs={'class': 'country-code'}, choices=[
                ('+1', 'US +1'),
                ('+44', 'UK +44'),
                ('+33', 'FR +33'),
            ]),
            TextInput(attrs={'class': 'phone-number', 'placeholder': '1234567890'}),
        ]
        super().__init__(widgets, attrs)

    def decompress(self, value):
        """Split value into widget values."""
        if value:
            # Split "+11234567890" into ["+1", "1234567890"]
            if value.startswith('+'):
                for i in range(2, 5):
                    code = value[:i]
                    number = value[i:]
                    if code in ['+1', '+44', '+33']:
                        return [code, number]
            return ['+1', value]
        return [None, None]

# Usage with custom field
from django.forms import MultiValueField, ChoiceField, CharField

class PhoneField(MultiValueField):
    widget = PhoneWidget

    def __init__(self, *args, **kwargs):
        fields = [
            ChoiceField(choices=[('+1', 'US'), ('+44', 'UK'), ('+33', 'FR')]),
            CharField(max_length=15),
        ]
        super().__init__(fields, *args, **kwargs)

    def compress(self, data_list):
        """Combine widget values into single value."""
        if data_list:
            return ''.join(data_list)
        return ''

class ContactForm(forms.Form):
    phone = PhoneField()
```

## Widget Media (CSS/JS)

### Defining Media

```python
from django.forms.widgets import Widget

class RichTextWidget(Widget):
    """WYSIWYG text editor."""

    template_name = 'widgets/richtext.html'

    class Media:
        css = {
            'all': (
                'https://cdn.example.com/editor.css',
                'css/custom-editor.css',
            ),
            'screen': ('css/editor-screen.css',),
        }
        js = (
            'https://cdn.example.com/editor.js',
            'js/editor-init.js',
        )
```

### Using Media in Templates

```django
<!-- In template head -->
{{ form.media.css }}

<!-- Before closing body -->
{{ form.media.js }}

<!-- Or combined -->
{{ form.media }}
```

**Renders:**
```html
<!-- CSS -->
<link href="/static/css/custom-editor.css" rel="stylesheet">
<link href="https://cdn.example.com/editor.css" rel="stylesheet">

<!-- JS -->
<script src="https://cdn.example.com/editor.js"></script>
<script src="/static/js/editor-init.js"></script>
```

### Combining Media

```python
# Multiple widgets with media
class ArticleForm(forms.Form):
    title = forms.CharField(widget=AutocompleteWidget())
    content = forms.CharField(widget=RichTextWidget())
    # form.media automatically combines both widgets' media
```

### Dynamic Media

```python
class ConditionalWidget(Widget):
    def __init__(self, use_advanced=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.use_advanced = use_advanced

    @property
    def media(self):
        base_media = forms.Media(
            css={'all': ('css/base.css',)},
            js=('js/base.js',)
        )

        if self.use_advanced:
            base_media += forms.Media(
                css={'all': ('css/advanced.css',)},
                js=('js/advanced.js',)
            )

        return base_media
```

## Widget Templates

### Default Widget Template Structure

Django 4.0+ uses template-based widget rendering.

**Default template location:**
```
django/forms/widgets/
├── input.html
├── textarea.html
├── select.html
├── checkbox.html
├── radio.html
└── ...
```

### Custom Widget Template

```python
# widgets.py
class CustomTextInput(forms.TextInput):
    template_name = 'widgets/custom_text_input.html'
```

**Template (templates/widgets/custom_text_input.html):**
```django
<div class="input-wrapper">
  {% if widget.label %}
    <label for="{{ widget.attrs.id }}">{{ widget.label }}</label>
  {% endif %}

  <input type="{{ widget.type }}"
         name="{{ widget.name }}"
         {% if widget.value != None %}value="{{ widget.value }}"{% endif %}
         {% include "django/forms/widgets/attrs.html" %}>

  {% if widget.help_text %}
    <small class="form-text">{{ widget.help_text }}</small>
  {% endif %}
</div>
```

### Override Widget Template in Form

```python
class MyForm(forms.Form):
    name = forms.CharField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Override widget template
        self.fields['name'].widget.template_name = 'my_custom_template.html'
```

## Widget Patterns

### Pattern 1: Add Bootstrap Classes to All Fields

```python
class BootstrapForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field_name, field in self.fields.items():
            widget = field.widget

            if isinstance(widget, (forms.TextInput, forms.EmailInput,
                                   forms.URLInput, forms.NumberInput,
                                   forms.Textarea)):
                widget.attrs['class'] = 'form-control'

            elif isinstance(widget, forms.Select):
                widget.attrs['class'] = 'form-select'

            elif isinstance(widget, forms.CheckboxInput):
                widget.attrs['class'] = 'form-check-input'
```

### Pattern 2: Placeholder as Label

```python
class PlaceholderForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field_name, field in self.fields.items():
            if 'placeholder' not in field.widget.attrs:
                field.widget.attrs['placeholder'] = field.label
```

### Pattern 3: Disable All Fields

```python
class ReadOnlyForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs['disabled'] = True
            # Or readonly for text inputs
            # field.widget.attrs['readonly'] = True
```

### Pattern 4: Dynamic Widget Selection

```python
class DynamicForm(forms.Form):
    def __init__(self, *args, use_richtext=False, **kwargs):
        super().__init__(*args, **kwargs)

        if use_richtext:
            self.fields['description'].widget = RichTextWidget()
        else:
            self.fields['description'].widget = forms.Textarea()

    description = forms.CharField()
```

## Third-Party Widgets

### django-widget-tweaks

Add CSS classes without modifying forms.

```django
{% load widget_tweaks %}

{{ form.email|add_class:"form-control"|attr:"placeholder:Enter email" }}
```

### django-crispy-forms

Render forms with Bootstrap/other CSS frameworks.

```python
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Submit

class MyForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Field('name', css_class='form-control'),
            Field('email', css_class='form-control'),
            Submit('submit', 'Save', css_class='btn btn-primary')
        )
```

### django-select2

Enhanced select widgets with search.

```python
from django_select2.forms import Select2Widget

class ProductForm(forms.Form):
    category = forms.ChoiceField(
        widget=Select2Widget(
            attrs={'data-minimum-input-length': 0}
        )
    )
```

## Widget Best Practices

1. **Use semantic HTML5 input types**: `email`, `url`, `number`, `date`, etc.
2. **Add ARIA attributes**: For accessibility
3. **Include placeholders**: Improve UX
4. **Use appropriate widgets**: Radio for few choices, select for many
5. **Leverage widget media**: Bundle CSS/JS properly
6. **Test on mobile**: Especially date/time pickers
7. **Consider performance**: Load heavy widgets only when needed
8. **Maintain consistency**: Use same widget types across forms

## See Also

- **Field Types:** `/home/user/django/.claude/skills/django-forms/reference/field_types.md`
- **CSS Frameworks:** `/home/user/django/.claude/skills/django-forms/reference/css_frameworks.md`
- **Accessibility:** Check accessibility_check.py script
