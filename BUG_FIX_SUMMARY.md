# Bug Fix: Mixed-Case App Names in Django Migrations

## Overview
Fixed a critical bug in Django 3.1b1 where `makemigrations` crashes when using ForeignKey fields with mixed-case app names like 'DJ_RegLogin'.

## The Problem

### Original Error
```
ValueError: The field DJ_RegLogin.Content.category was declared with a lazy
reference to 'dj_reglogin.category', but app 'dj_reglogin' isn't installed.
```

### Root Cause
Two functions were incorrectly lowercasing the entire model reference string (including the app label) instead of only lowercasing the model name:

1. `resolve_relation()` in `django/db/migrations/operations/utils.py`
2. `ForeignObject.deconstruct()` in `django/db/models/fields/related.py`

Django's convention is:
- **App labels** preserve their original case (case-sensitive)
- **Model names** are always lowercased (case-insensitive)

## The Solution

### File 1: django/db/migrations/operations/utils.py (lines 21-23)

**Before:**
```python
if '.' in model:
    return tuple(model.lower().split('.', 1))
```

**After:**
```python
if '.' in model:
    app_label, model_name = model.split('.', 1)
    return app_label, model_name.lower()
```

### File 2: django/db/models/fields/related.py (lines 584-589)

**Before:**
```python
if isinstance(self.remote_field.model, str):
    kwargs['to'] = self.remote_field.model.lower()
```

**After:**
```python
if isinstance(self.remote_field.model, str):
    if '.' in self.remote_field.model:
        app_label, model_name = self.remote_field.model.split('.', 1)
        kwargs['to'] = '%s.%s' % (app_label, model_name.lower())
    else:
        kwargs['to'] = self.remote_field.model.lower()
```

## Testing

### New Tests Added
Created comprehensive test suite in `tests/migrations/test_utils.py`:
- `test_resolve_relation_with_mixed_case_app_label` - Validates case preservation
- `test_resolve_relation_with_lowercase_app_label` - Ensures backward compatibility
- `test_resolve_relation_without_dot` - Tests unscoped references
- `test_resolve_relation_recursive` - Tests 'self' references
- `test_resolve_relation_model_case_normalization` - Validates model lowercasing
- `test_resolve_relation_without_dot_missing_app_label` - Error handling
- `test_resolve_relation_recursive_missing_params` - Error handling

### Test Results
✅ All 7 new tests pass
✅ All 559 migration tests pass (no regressions)
✅ All 395 model_fields tests pass (no regressions)
✅ Integration tests validate end-to-end functionality

## Impact

### Fixed Scenarios
- ✅ Mixed-case app names (e.g., 'DJ_RegLogin') now work correctly
- ✅ ForeignKey references preserve app label case
- ✅ Migration generation succeeds without ValueError

### Backward Compatibility
- ✅ Lowercase app names continue to work as before
- ✅ No breaking changes to existing code
- ✅ All existing tests pass

### Examples
```python
# Now works correctly:
resolve_relation('DJ_RegLogin.Category')
# Returns: ('DJ_RegLogin', 'category')

resolve_relation('MyApp.MyModel')
# Returns: ('MyApp', 'mymodel')

# Still works as before:
resolve_relation('myapp.mymodel')
# Returns: ('myapp', 'mymodel')
```

## Related Django Conventions

This fix aligns with Django's established conventions:
1. **Model names** are case-insensitive and stored lowercase internally
2. **App labels** are case-sensitive and preserve their original case
3. Model references use the format: `AppLabel.modelname`

## Git Changes
```
Modified:   django/db/migrations/operations/utils.py
Modified:   django/db/models/fields/related.py
Added:      tests/migrations/test_utils.py
```
