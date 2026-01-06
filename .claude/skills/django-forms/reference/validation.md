# Django Form Validation Reference

Complete guide to form validation patterns in Django.

## Table of Contents

- [Validation Flow](#validation-flow)
- [Field-Level Validation](#field-level-validation)
- [Form-Level Validation](#form-level-validation)
- [Cross-Field Validation](#cross-field-validation)
- [Custom Validators](#custom-validators)
- [ModelForm Validation](#modelform-validation)
- [Async Validation Workarounds](#async-validation-workarounds)
- [Error Messages](#error-messages)

## Validation Flow

Django validates forms in this order:

```
1. to_python()              Convert input to Python type
2. validate()               Built-in field validation
3. run_validators()         Custom validators
4. clean()                  Field's clean method
5. clean_<fieldname>()      Form's field-specific clean method
6. clean()                  Form's general clean method
```

**Example flow:**
```python
class ContactForm(forms.Form):
    email = forms.EmailField(
        validators=[custom_email_validator]  # Step 3
    )

    def clean_email(self):  # Step 5
        email = self.cleaned_data.get('email')
        if email and email.endswith('@blocked.com'):
            raise forms.ValidationError('Domain not allowed')
        return email

    def clean(self):  # Step 6
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        phone = cleaned_data.get('phone')
        if not email and not phone:
            raise forms.ValidationError('Provide either email or phone')
        return cleaned_data
```

## Field-Level Validation

### Method 1: clean_<fieldname>()

Override `clean_<fieldname>()` method in form class.

```python
from django import forms
from django.core.exceptions import ValidationError

class ProductForm(forms.Form):
    name = forms.CharField(max_length=100)
    price = forms.DecimalField(max_digits=10, decimal_places=2)
    stock = forms.IntegerField()

    def clean_name(self):
        """Validate product name."""
        name = self.cleaned_data.get('name')

        # Check for profanity (example)
        banned_words = ['spam', 'scam']
        if any(word in name.lower() for word in banned_words):
            raise ValidationError('Name contains prohibited words.')

        # Check uniqueness
        if Product.objects.filter(name__iexact=name).exists():
            raise ValidationError('A product with this name already exists.')

        return name.strip()

    def clean_price(self):
        """Validate price is positive."""
        price = self.cleaned_data.get('price')
        if price is not None and price <= 0:
            raise ValidationError('Price must be greater than zero.')
        return price

    def clean_stock(self):
        """Validate stock is non-negative."""
        stock = self.cleaned_data.get('stock')
        if stock is not None and stock < 0:
            raise ValidationError('Stock cannot be negative.')
        return stock
```

**When to use:**
- Field-specific validation logic
- Database lookups for single field
- Field transformation/normalization
- Validation that only concerns one field

### Method 2: Field Validators

Add validators to field definition.

```python
from django.core.validators import (
    MinValueValidator,
    MaxValueValidator,
    RegexValidator,
    EmailValidator,
)

def validate_even_number(value):
    """Custom validator function."""
    if value % 2 != 0:
        raise ValidationError(f'{value} is not an even number.')

class OrderForm(forms.Form):
    quantity = forms.IntegerField(
        validators=[
            MinValueValidator(1, message='Must order at least 1 item.'),
            MaxValueValidator(100, message='Cannot order more than 100 items.'),
            validate_even_number,
        ]
    )

    phone = forms.CharField(
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message='Enter a valid phone number.',
                code='invalid_phone'
            )
        ]
    )

    email = forms.EmailField(
        validators=[
            EmailValidator(message='Enter a valid email address.')
        ]
    )
```

**When to use:**
- Reusable validation logic
- Simple validation rules
- Standard validation patterns

## Form-Level Validation

### clean() Method

Use `clean()` for validation that involves multiple fields.

```python
from django import forms
from datetime import date, timedelta

class EventForm(forms.Form):
    name = forms.CharField(max_length=200)
    start_date = forms.DateField()
    end_date = forms.DateField()
    is_online = forms.BooleanField(required=False)
    venue = forms.CharField(max_length=200, required=False)
    meeting_link = forms.URLField(required=False)

    def clean(self):
        """Validate form data across multiple fields."""
        cleaned_data = super().clean()

        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        is_online = cleaned_data.get('is_online')
        venue = cleaned_data.get('venue')
        meeting_link = cleaned_data.get('meeting_link')

        # Validate date range
        if start_date and end_date:
            if end_date < start_date:
                raise ValidationError(
                    'End date must be after start date.'
                )

            if start_date < date.today():
                self.add_error('start_date',
                    'Event cannot start in the past.')

            # Warn if event is too long
            if (end_date - start_date).days > 30:
                self.add_error('end_date',
                    'Event duration cannot exceed 30 days.')

        # Conditional field requirements
        if is_online:
            if not meeting_link:
                self.add_error('meeting_link',
                    'Meeting link is required for online events.')
        else:
            if not venue:
                self.add_error('venue',
                    'Venue is required for in-person events.')

        return cleaned_data
```

**add_error() vs raise ValidationError:**

```python
def clean(self):
    cleaned_data = super().clean()

    # Option 1: Field-specific error (preferred)
    if some_condition:
        self.add_error('field_name', 'Error message')

    # Option 2: General form error (no specific field)
    if some_other_condition:
        raise ValidationError('General error message')

    # Option 3: Multiple errors
    if multiple_issues:
        raise ValidationError({
            'field1': 'Error for field1',
            'field2': 'Error for field2',
        })

    return cleaned_data
```

## Cross-Field Validation

### Pattern 1: Interdependent Fields

```python
class PasswordChangeForm(forms.Form):
    old_password = forms.CharField(widget=forms.PasswordInput)
    new_password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        old_password = cleaned_data.get('old_password')
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')

        # Verify old password
        if old_password and not self.user.check_password(old_password):
            self.add_error('old_password', 'Current password is incorrect.')

        # Check new passwords match
        if new_password and confirm_password:
            if new_password != confirm_password:
                self.add_error('confirm_password',
                    'Passwords do not match.')

        # Ensure new password is different
        if old_password and new_password:
            if old_password == new_password:
                self.add_error('new_password',
                    'New password must be different from current password.')

        return cleaned_data
```

### Pattern 2: Conditional Validation

```python
class ShippingForm(forms.Form):
    shipping_method = forms.ChoiceField(
        choices=[
            ('standard', 'Standard'),
            ('express', 'Express'),
            ('pickup', 'Store Pickup'),
        ]
    )
    address = forms.CharField(required=False)
    city = forms.CharField(required=False)
    zip_code = forms.CharField(required=False)
    store_location = forms.ChoiceField(required=False)

    def clean(self):
        cleaned_data = super().clean()
        method = cleaned_data.get('shipping_method')

        if method in ['standard', 'express']:
            # Validate shipping address
            required_fields = ['address', 'city', 'zip_code']
            for field in required_fields:
                if not cleaned_data.get(field):
                    self.add_error(field, f'{field.title()} is required for shipping.')

        elif method == 'pickup':
            # Validate store selection
            if not cleaned_data.get('store_location'):
                self.add_error('store_location',
                    'Please select a store location.')

        return cleaned_data
```

### Pattern 3: Range Validation

```python
class DiscountForm(forms.Form):
    discount_type = forms.ChoiceField(
        choices=[('percentage', 'Percentage'), ('fixed', 'Fixed Amount')]
    )
    discount_value = forms.DecimalField(max_digits=10, decimal_places=2)
    min_purchase = forms.DecimalField(max_digits=10, decimal_places=2)
    max_discount = forms.DecimalField(required=False)

    def clean(self):
        cleaned_data = super().clean()
        discount_type = cleaned_data.get('discount_type')
        discount_value = cleaned_data.get('discount_value')
        min_purchase = cleaned_data.get('min_purchase')
        max_discount = cleaned_data.get('max_discount')

        if discount_type == 'percentage':
            # Percentage must be 0-100
            if discount_value:
                if discount_value < 0 or discount_value > 100:
                    self.add_error('discount_value',
                        'Percentage must be between 0 and 100.')

        if discount_type == 'fixed':
            # Fixed discount cannot exceed minimum purchase
            if discount_value and min_purchase:
                if discount_value > min_purchase:
                    self.add_error('discount_value',
                        'Discount cannot exceed minimum purchase amount.')

        # Max discount validation
        if max_discount and min_purchase:
            if max_discount > min_purchase:
                self.add_error('max_discount',
                    'Maximum discount cannot exceed minimum purchase.')

        return cleaned_data
```

### Pattern 4: At Least One Required

```python
class ContactForm(forms.Form):
    email = forms.EmailField(required=False)
    phone = forms.CharField(required=False)
    message = forms.CharField(widget=forms.Textarea)

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        phone = cleaned_data.get('phone')

        if not email and not phone:
            raise ValidationError(
                'Please provide at least one contact method (email or phone).'
            )

        return cleaned_data
```

## Custom Validators

### Function-Based Validators

```python
from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible

def validate_file_size(file):
    """Limit file size to 5MB."""
    max_size_mb = 5
    if file.size > max_size_mb * 1024 * 1024:
        raise ValidationError(f'File size cannot exceed {max_size_mb}MB.')

def validate_positive(value):
    """Ensure value is positive."""
    if value <= 0:
        raise ValidationError('Value must be positive.')

def validate_future_date(date_value):
    """Ensure date is in the future."""
    from datetime import date
    if date_value < date.today():
        raise ValidationError('Date must be in the future.')

# Usage
class EventForm(forms.Form):
    start_date = forms.DateField(validators=[validate_future_date])
    attachment = forms.FileField(validators=[validate_file_size])
    attendees = forms.IntegerField(validators=[validate_positive])
```

### Class-Based Validators

Use `@deconstructible` for validators with state.

```python
from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible

@deconstructible
class FileSizeValidator:
    """Validates file size."""

    def __init__(self, max_size_mb):
        self.max_size_mb = max_size_mb

    def __call__(self, file):
        if file.size > self.max_size_mb * 1024 * 1024:
            raise ValidationError(
                f'File size cannot exceed {self.max_size_mb}MB.'
            )

    def __eq__(self, other):
        return isinstance(other, FileSizeValidator) and \
               self.max_size_mb == other.max_size_mb

@deconstructible
class RangeValidator:
    """Validates value is within range."""

    def __init__(self, min_value, max_value):
        self.min_value = min_value
        self.max_value = max_value

    def __call__(self, value):
        if value < self.min_value or value > self.max_value:
            raise ValidationError(
                f'Value must be between {self.min_value} and {self.max_value}.'
            )

# Usage
class ProductForm(forms.Form):
    image = forms.ImageField(validators=[FileSizeValidator(max_size_mb=2)])
    rating = forms.IntegerField(validators=[RangeValidator(1, 5)])
```

### Reusable Validator Module

```python
# validators.py
from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible
import re

@deconstructible
class PhoneValidator:
    """Validates phone numbers."""

    def __init__(self, country_code='US'):
        self.country_code = country_code

    def __call__(self, value):
        if self.country_code == 'US':
            pattern = r'^\+?1?\d{10}$'
            if not re.match(pattern, value):
                raise ValidationError('Enter a valid US phone number.')

@deconstructible
class ProhibitedWordsValidator:
    """Validates text doesn't contain prohibited words."""

    def __init__(self, prohibited_words):
        self.prohibited_words = [w.lower() for w in prohibited_words]

    def __call__(self, value):
        for word in self.prohibited_words:
            if word in value.lower():
                raise ValidationError(
                    f'Text contains prohibited word: {word}'
                )

# Usage in forms.py
from .validators import PhoneValidator, ProhibitedWordsValidator

class UserForm(forms.Form):
    phone = forms.CharField(
        validators=[PhoneValidator(country_code='US')]
    )
    bio = forms.CharField(
        widget=forms.Textarea,
        validators=[ProhibitedWordsValidator(['spam', 'scam'])]
    )
```

## ModelForm Validation

ModelForms have dual validation: form and model.

### Model Validators

```python
# models.py
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class Product(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.01)]
    )
    stock = models.IntegerField(
        validators=[MinValueValidator(0)]
    )

    def clean(self):
        """Model-level validation."""
        if self.price > 1000000:
            raise ValidationError('Price exceeds maximum limit.')
```

### ModelForm with Additional Validation

```python
# forms.py
from django import forms
from .models import Product

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'price', 'stock']

    def clean_name(self):
        """Form-level validation (runs before model validation)."""
        name = self.cleaned_data.get('name')

        # Check for duplicate (excluding current instance)
        qs = Product.objects.filter(name__iexact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError(
                'A product with this name already exists.'
            )

        return name

    def clean(self):
        """Cross-field validation."""
        cleaned_data = super().clean()
        price = cleaned_data.get('price')
        stock = cleaned_data.get('stock')

        # Business logic: expensive items must have limited stock
        if price and stock:
            if price > 10000 and stock > 100:
                raise forms.ValidationError(
                    'High-value items cannot have stock over 100.'
                )

        return cleaned_data
```

### Validation Order in ModelForm

```
1. Form field validation (to_python, validate, run_validators)
2. Form clean_<field>() methods
3. Form clean() method
4. Model field validation (model validators)
5. Model clean() method
6. Model save()
```

## Async Validation Workarounds

Django forms don't support async validation directly. Workarounds:

### Pattern 1: Client-Side Pre-validation

```python
# views.py
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

@require_http_methods(["GET"])
def check_username_available(request):
    """AJAX endpoint for username availability."""
    username = request.GET.get('username', '')

    if not username:
        return JsonResponse({'available': False, 'message': 'Username required'})

    exists = User.objects.filter(username=username).exists()

    return JsonResponse({
        'available': not exists,
        'message': 'Username taken' if exists else 'Username available'
    })
```

```javascript
// Client-side validation
document.getElementById('username').addEventListener('blur', async (e) => {
    const username = e.target.value;
    const response = await fetch(`/api/check-username/?username=${username}`);
    const data = await response.json();

    if (!data.available) {
        // Show error
        e.target.classList.add('is-invalid');
    }
});
```

### Pattern 2: Background Task with Status Check

```python
# For expensive validation (API calls, etc.)
from celery import shared_task

@shared_task
def validate_vat_number(vat_number):
    """Validate VAT number via external API."""
    # Call external API
    result = external_api.validate_vat(vat_number)
    return result

# In view
def handle_form(request):
    if form.is_valid():
        # Queue validation
        task = validate_vat_number.delay(form.cleaned_data['vat_number'])

        # Save with pending status
        instance = form.save(commit=False)
        instance.validation_status = 'pending'
        instance.validation_task_id = task.id
        instance.save()
```

## Error Messages

### Custom Error Messages

```python
class RegistrationForm(forms.Form):
    username = forms.CharField(
        max_length=30,
        error_messages={
            'required': 'Username is required.',
            'max_length': 'Username cannot exceed 30 characters.',
        }
    )

    age = forms.IntegerField(
        error_messages={
            'required': 'Please enter your age.',
            'invalid': 'Enter a valid number.',
        }
    )
```

### Error Message Keys by Field Type

| Field Type | Error Keys |
|------------|-----------|
| CharField | required, max_length, min_length |
| IntegerField | required, invalid, max_value, min_value |
| EmailField | required, invalid |
| URLField | required, invalid |
| DateField | required, invalid |
| FileField | required, invalid, missing, empty, max_length |

### Displaying Errors in Templates

```html
<!-- All form errors -->
{% if form.errors %}
  <div class="alert alert-danger">
    <ul>
      {% for field in form %}
        {% for error in field.errors %}
          <li>{{ field.label }}: {{ error }}</li>
        {% endfor %}
      {% endfor %}
      {% for error in form.non_field_errors %}
        <li>{{ error }}</li>
      {% endfor %}
    </ul>
  </div>
{% endif %}

<!-- Per-field errors -->
<div class="form-group">
  {{ form.username.label_tag }}
  {{ form.username }}
  {% if form.username.errors %}
    <div class="invalid-feedback">
      {{ form.username.errors.0 }}
    </div>
  {% endif %}
</div>

<!-- Non-field errors (from clean() method) -->
{% if form.non_field_errors %}
  <div class="alert alert-danger">
    {{ form.non_field_errors }}
  </div>
{% endif %}
```

### Programmatic Error Handling

```python
# In views
if form.is_valid():
    form.save()
else:
    # Access specific field errors
    for field, errors in form.errors.items():
        for error in errors:
            print(f'{field}: {error}')

    # Get all errors as dictionary
    error_dict = form.errors.as_data()

    # Get all errors as JSON
    error_json = form.errors.as_json()
```

## Validation Best Practices

1. **Validate early and often**: Client-side + server-side
2. **Use specific error messages**: Help users fix issues
3. **Validate in the right place**:
   - Field-level: Single field logic
   - Form-level: Cross-field logic
   - Model-level: Business rules
4. **Don't duplicate validation**: Use validators for reusable logic
5. **Return cleaned data**: Always return from clean methods
6. **Use add_error() for field errors**: Better UX than raising ValidationError
7. **Test validation thoroughly**: Edge cases, boundary values
8. **Consider UX**: Progressive enhancement, real-time feedback

## Common Validation Patterns

### Email Domain Whitelist

```python
def clean_email(self):
    email = self.cleaned_data.get('email')
    allowed_domains = ['company.com', 'company.org']

    if email:
        domain = email.split('@')[1]
        if domain not in allowed_domains:
            raise ValidationError(
                f'Email must be from: {", ".join(allowed_domains)}'
            )

    return email
```

### Password Strength

```python
import re

def clean_password(self):
    password = self.cleaned_data.get('password')

    if password:
        if len(password) < 8:
            raise ValidationError('Password must be at least 8 characters.')

        if not re.search(r'[A-Z]', password):
            raise ValidationError('Password must contain an uppercase letter.')

        if not re.search(r'[a-z]', password):
            raise ValidationError('Password must contain a lowercase letter.')

        if not re.search(r'[0-9]', password):
            raise ValidationError('Password must contain a digit.')

        if not re.search(r'[!@#$%^&*]', password):
            raise ValidationError('Password must contain a special character.')

    return password
```

### Age Verification

```python
from datetime import date

def clean_birth_date(self):
    birth_date = self.cleaned_data.get('birth_date')

    if birth_date:
        today = date.today()
        age = today.year - birth_date.year - (
            (today.month, today.day) < (birth_date.month, birth_date.day)
        )

        if age < 18:
            raise ValidationError('You must be at least 18 years old.')

    return birth_date
```

## See Also

- **Field Types:** `/home/user/django/.claude/skills/django-forms/reference/field_types.md`
- **Widgets:** `/home/user/django/.claude/skills/django-forms/reference/widgets.md`
- **File Uploads:** `/home/user/django/.claude/skills/django-forms/reference/file_uploads.md`
