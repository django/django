# Django Form Field Types Reference

Complete guide to all Django form fields with widgets, validation, and examples.

## Table of Contents

- [Field Type Overview](#field-type-overview)
- [Text Input Fields](#text-input-fields)
- [Numeric Fields](#numeric-fields)
- [Date and Time Fields](#date-and-time-fields)
- [Boolean Fields](#boolean-fields)
- [Choice Fields](#choice-fields)
- [File Fields](#file-fields)
- [Complex Fields](#complex-fields)
- [Custom Field Creation](#custom-field-creation)

## Field Type Overview

### Field → Widget Mapping

| Field Type | Default Widget | HTML Input Type |
|------------|----------------|-----------------|
| CharField | TextInput | text |
| EmailField | EmailInput | email |
| URLField | URLInput | url |
| IntegerField | NumberInput | number |
| FloatField | NumberInput | number |
| DecimalField | NumberInput | number |
| BooleanField | CheckboxInput | checkbox |
| DateField | DateInput | text |
| TimeField | TimeInput | text |
| DateTimeField | DateTimeInput | text |
| ChoiceField | Select | select |
| MultipleChoiceField | SelectMultiple | select multiple |
| FileField | ClearableFileInput | file |
| ImageField | ClearableFileInput | file |
| TextField | Textarea | textarea |

## Text Input Fields

### CharField

Basic text input field.

```python
from django import forms

class MyForm(forms.Form):
    name = forms.CharField(
        max_length=100,
        min_length=2,
        required=True,
        label='Full Name',
        help_text='Enter your first and last name',
        initial='',
        widget=forms.TextInput(attrs={
            'placeholder': 'John Doe',
            'class': 'form-control',
            'autocomplete': 'name',
        })
    )

    # Common variations
    short_text = forms.CharField(max_length=50)
    optional_text = forms.CharField(required=False)
    stripped_text = forms.CharField(strip=True)  # Remove leading/trailing whitespace
    not_stripped = forms.CharField(strip=False)
```

**Validation options:**
- `max_length` - Maximum character count
- `min_length` - Minimum character count
- `strip` - Strip whitespace (default: True)
- `empty_value` - Value to use for empty strings (default: '')

### EmailField

Validates email addresses.

```python
email = forms.EmailField(
    label='Email Address',
    widget=forms.EmailInput(attrs={
        'placeholder': 'user@example.com',
        'autocomplete': 'email',
    })
)
```

**Built-in validation:**
- Valid email format (uses Django's EmailValidator)
- Accepts international domain names

### URLField

Validates URLs.

```python
website = forms.URLField(
    required=False,
    label='Website',
    help_text='Must include http:// or https://',
    widget=forms.URLInput(attrs={
        'placeholder': 'https://example.com'
    })
)
```

**Built-in validation:**
- Valid URL format
- Must include scheme (http/https)

### SlugField

Validates slugs (URL-friendly strings).

```python
slug = forms.SlugField(
    max_length=50,
    help_text='Letters, numbers, underscores, and hyphens only',
)
```

**Allowed characters:** `a-z`, `A-Z`, `0-9`, `_`, `-`

### RegexField

Custom pattern validation.

```python
from django.core.validators import RegexValidator

phone_number = forms.CharField(
    max_length=15,
    validators=[
        RegexValidator(
            regex=r'^\+?1?\d{9,15}$',
            message='Enter a valid phone number',
        )
    ],
    widget=forms.TextInput(attrs={
        'placeholder': '+1234567890',
        'type': 'tel',
    })
)
```

### TextField (Using Textarea)

Multi-line text input.

```python
description = forms.CharField(
    widget=forms.Textarea(attrs={
        'rows': 5,
        'cols': 40,
        'placeholder': 'Enter description...',
        'maxlength': 500,
    }),
    max_length=500,
    required=False,
)
```

## Numeric Fields

### IntegerField

Integer values.

```python
age = forms.IntegerField(
    min_value=0,
    max_value=150,
    widget=forms.NumberInput(attrs={
        'min': '0',
        'max': '150',
        'step': '1',
    })
)

# Optional with default
quantity = forms.IntegerField(
    initial=1,
    min_value=1,
    max_value=100,
)
```

**Validation options:**
- `min_value` - Minimum allowed value
- `max_value` - Maximum allowed value

### FloatField

Floating-point numbers.

```python
rating = forms.FloatField(
    min_value=0.0,
    max_value=5.0,
    widget=forms.NumberInput(attrs={
        'step': '0.1',
    })
)
```

### DecimalField

Precise decimal numbers (for currency, measurements).

```python
from decimal import Decimal

price = forms.DecimalField(
    max_digits=10,
    decimal_places=2,
    min_value=Decimal('0.01'),
    max_value=Decimal('99999999.99'),
    widget=forms.NumberInput(attrs={
        'step': '0.01',
        'placeholder': '0.00',
    })
)
```

**Validation options:**
- `max_digits` - Total digits (including decimals)
- `decimal_places` - Decimal places
- `min_value` / `max_value` - Use Decimal type

## Date and Time Fields

### DateField

Date selection.

```python
birth_date = forms.DateField(
    input_formats=['%Y-%m-%d', '%m/%d/%Y', '%m/%d/%y'],
    widget=forms.DateInput(attrs={
        'type': 'date',  # HTML5 date picker
        'placeholder': 'YYYY-MM-DD',
    })
)

# With custom widget
from django.forms.widgets import SelectDateWidget

birth_date_select = forms.DateField(
    widget=SelectDateWidget(
        years=range(1920, 2024),
        attrs={'class': 'form-select'}
    )
)
```

**Input formats:** Accepts multiple date formats. First format is used for initial value.

### TimeField

Time selection.

```python
appointment_time = forms.TimeField(
    input_formats=['%H:%M', '%H:%M:%S', '%I:%M %p'],
    widget=forms.TimeInput(attrs={
        'type': 'time',  # HTML5 time picker
        'placeholder': 'HH:MM',
    })
)
```

### DateTimeField

Combined date and time.

```python
from django.utils import timezone

event_datetime = forms.DateTimeField(
    input_formats=['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%m/%d/%Y %I:%M %p'],
    widget=forms.DateTimeInput(attrs={
        'type': 'datetime-local',  # HTML5 datetime picker
        'placeholder': 'YYYY-MM-DD HH:MM',
    })
)
```

### DurationField

Time duration (timedelta).

```python
video_length = forms.DurationField(
    help_text='Format: DD HH:MM:SS or HH:MM:SS',
)
# Accepts: "1 12:30:00", "12:30:00", "12:30"
```

## Boolean Fields

### BooleanField

Checkbox that must be checked.

```python
agree_to_terms = forms.BooleanField(
    required=True,
    label='I agree to the terms and conditions',
    widget=forms.CheckboxInput(attrs={
        'class': 'form-check-input'
    })
)
```

**Note:** Always returns `True` or raises ValidationError if unchecked and required.

### NullBooleanField

Three-state: True, False, or None.

```python
# Deprecated in Django 4.0 - use BooleanField with required=False
is_active = forms.BooleanField(
    required=False,
    initial=None,
)
```

## Choice Fields

### ChoiceField

Single selection from predefined choices.

```python
STATUS_CHOICES = [
    ('', '--- Select Status ---'),  # Empty choice
    ('draft', 'Draft'),
    ('published', 'Published'),
    ('archived', 'Archived'),
]

status = forms.ChoiceField(
    choices=STATUS_CHOICES,
    required=True,
    widget=forms.Select(attrs={
        'class': 'form-select'
    })
)

# Radio buttons instead of dropdown
priority = forms.ChoiceField(
    choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High')],
    widget=forms.RadioSelect,
    initial='medium',
)
```

**Dynamic choices:**
```python
class MyForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].choices = [
            (cat.id, cat.name) for cat in Category.objects.all()
        ]

    category = forms.ChoiceField()
```

### MultipleChoiceField

Multiple selections.

```python
TAGS = [
    ('python', 'Python'),
    ('django', 'Django'),
    ('javascript', 'JavaScript'),
    ('react', 'React'),
]

tags = forms.MultipleChoiceField(
    choices=TAGS,
    required=False,
    widget=forms.CheckboxSelectMultiple,
)

# Or with SelectMultiple (Ctrl+Click)
tags_select = forms.MultipleChoiceField(
    choices=TAGS,
    widget=forms.SelectMultiple(attrs={
        'class': 'form-select',
        'size': '5',
    })
)
```

### TypedChoiceField

ChoiceField with type coercion.

```python
year = forms.TypedChoiceField(
    choices=[(2021, '2021'), (2022, '2022'), (2023, '2023')],
    coerce=int,  # Convert string input to int
    empty_value=None,
)
```

### ModelChoiceField

Choice from database queryset.

```python
from .models import Category

category = forms.ModelChoiceField(
    queryset=Category.objects.filter(active=True),
    empty_label='--- Select Category ---',
    to_field_name='id',  # Field to use as value (default: pk)
    widget=forms.Select(attrs={
        'class': 'form-select'
    })
)

# Custom display
def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.fields['category'].label_from_instance = lambda obj: f"{obj.name} ({obj.count})"
```

### ModelMultipleChoiceField

Multiple model selections.

```python
authors = forms.ModelMultipleChoiceField(
    queryset=Author.objects.all(),
    widget=forms.CheckboxSelectMultiple,
    required=False,
)
```

## File Fields

### FileField

Generic file upload.

```python
from django.core.validators import FileExtensionValidator

document = forms.FileField(
    required=False,
    validators=[
        FileExtensionValidator(
            allowed_extensions=['pdf', 'doc', 'docx', 'txt']
        )
    ],
    widget=forms.FileInput(attrs={
        'accept': '.pdf,.doc,.docx,.txt',
        'class': 'form-control'
    })
)
```

**Accessing uploaded file:**
```python
if form.is_valid():
    uploaded_file = form.cleaned_data['document']
    # uploaded_file.name - filename
    # uploaded_file.size - size in bytes
    # uploaded_file.read() - file contents
```

### ImageField

Image upload with validation.

```python
avatar = forms.ImageField(
    required=False,
    validators=[
        FileExtensionValidator(['jpg', 'jpeg', 'png', 'gif'])
    ],
    widget=forms.FileInput(attrs={
        'accept': 'image/*',
        'class': 'form-control'
    })
)
```

**Requires Pillow:**
```bash
pip install Pillow
```

**Additional validation:**
```python
from PIL import Image
from django.core.exceptions import ValidationError

def clean_avatar(self):
    avatar = self.cleaned_data.get('avatar')
    if avatar:
        # Check dimensions
        img = Image.open(avatar)
        if img.width > 1000 or img.height > 1000:
            raise ValidationError('Image dimensions cannot exceed 1000x1000 pixels.')
        avatar.seek(0)  # Reset file pointer
    return avatar
```

### FilePathField

Select file from server filesystem.

```python
template = forms.FilePathField(
    path='/path/to/templates/',
    match=r'.*\.html$',  # Regex pattern
    recursive=True,
    allow_files=True,
    allow_folders=False,
)
```

**Use cases:** Template selection, log file viewing (admin only).

## Complex Fields

### JSONField

JSON data (Django 3.1+).

```python
metadata = forms.JSONField(
    required=False,
    widget=forms.Textarea(attrs={
        'rows': 5,
        'placeholder': '{"key": "value"}',
    })
)
```

**Validation:** Ensures valid JSON syntax.

### GenericIPAddressField

IP address validation.

```python
ip_address = forms.GenericIPAddressField(
    protocol='both',  # 'both', 'ipv4', 'ipv6'
    label='IP Address',
)
```

### UUIDField

UUID validation.

```python
import uuid

unique_id = forms.UUIDField(
    initial=uuid.uuid4,
    widget=forms.TextInput(attrs={
        'readonly': 'readonly',
    })
)
```

## Custom Field Creation

### Basic Custom Field

```python
from django import forms
from django.core.exceptions import ValidationError

class UpperCaseCharField(forms.CharField):
    """CharField that converts input to uppercase."""

    def to_python(self, value):
        """Normalize data to uppercase string."""
        value = super().to_python(value)
        if value:
            return value.upper()
        return value

    def clean(self, value):
        """Validate the field."""
        value = super().clean(value)
        # Additional validation
        if value and len(value.split()) < 2:
            raise ValidationError('Enter at least two words.')
        return value
```

### Custom Field with Validator

```python
from django.core.validators import RegexValidator

class ColorField(forms.CharField):
    """Hex color code field."""

    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 7
        kwargs['validators'] = [
            RegexValidator(
                regex=r'^#[0-9A-Fa-f]{6}$',
                message='Enter a valid hex color code (e.g., #FF0000)',
            )
        ]
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        value = super().to_python(value)
        if value and not value.startswith('#'):
            value = '#' + value
        return value.upper() if value else value
```

### Composite Custom Field

```python
import re
from django.forms import MultiValueField, CharField

class SplitNameField(MultiValueField):
    """Split full name into first and last name."""

    def __init__(self, *args, **kwargs):
        fields = (
            CharField(max_length=50, label='First Name'),
            CharField(max_length=50, label='Last Name'),
        )
        super().__init__(fields, *args, **kwargs)

    def compress(self, data_list):
        """Combine first and last name."""
        if data_list:
            return ' '.join(data_list)
        return ''
```

### Field with Custom Widget

```python
from django.forms import Field
from django.forms.widgets import Widget

class ColorPickerWidget(Widget):
    template_name = 'widgets/color_picker.html'

    class Media:
        css = {
            'all': ('css/color-picker.css',)
        }
        js = ('js/color-picker.js',)

class ColorPickerField(Field):
    widget = ColorPickerWidget

    def validate(self, value):
        super().validate(value)
        if value and not re.match(r'^#[0-9A-Fa-f]{6}$', value):
            raise ValidationError('Invalid color code')
```

## Field Common Parameters

All field types accept these parameters:

```python
field = forms.CharField(
    # Validation
    required=True,              # Must be provided
    validators=[],              # List of validator functions

    # Display
    label='Field Label',        # Label text
    label_suffix=':',          # Suffix after label (default: ':')
    help_text='Help message',   # Help text displayed below field
    initial='default',          # Initial value

    # HTML attributes
    widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Enter value',
        'id': 'custom-id',
        'data-custom': 'value',
    }),

    # Errors
    error_messages={
        'required': 'This field is required.',
        'invalid': 'Enter a valid value.',
    },

    # Localization
    localize=False,            # Use localized input/output

    # Other
    disabled=False,            # Disable field (no validation)
    show_hidden_initial=False, # Add hidden input with initial value
)
```

## Field Validation Order

Django validates fields in this order:

1. **to_python()** - Convert input to Python type
2. **validate()** - Run field's built-in validation
3. **run_validators()** - Run custom validators
4. **clean()** - Custom cleaning/validation
5. **clean_<fieldname>()** - Form-level field cleaning

```python
class MyForm(forms.Form):
    email = forms.EmailField(
        validators=[custom_validator],  # Step 3
    )

    def clean_email(self):  # Step 5
        email = self.cleaned_data.get('email')
        if email and email.endswith('@spam.com'):
            raise forms.ValidationError('Email domain not allowed.')
        return email
```

## Best Practices

1. **Use most specific field type**: `EmailField` instead of `CharField` with regex
2. **Set appropriate max_length**: Prevents database errors
3. **Add help_text**: Improves UX
4. **Use validators list**: Reusable across forms
5. **Coerce types early**: Use `TypedChoiceField` for numeric choices
6. **Validate in clean()**: For field-specific logic
7. **Use initial values**: For better UX
8. **Add ARIA attributes**: For accessibility

## See Also

- **Validation:** `/home/user/django/.claude/skills/django-forms/reference/validation.md`
- **Widgets:** `/home/user/django/.claude/skills/django-forms/reference/widgets.md`
- **File Uploads:** `/home/user/django/.claude/skills/django-forms/reference/file_uploads.md`
