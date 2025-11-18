# Fix for Model Save Behavior with Explicit PK and Default Values

## Issue
In Django 3.0+, when saving a model instance with an explicitly set primary key value where the pk field has a default, the save operation would incorrectly force an INSERT instead of attempting an UPDATE first. This caused IntegrityError when trying to update existing objects.

### Example Scenario
```python
from uuid import uuid4
from django.db import models

class Sample(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4)
    name = models.CharField(blank=True, max_length=100)

# In Django 2.2: This works correctly (UPDATE)
s0 = Sample.objects.create()
s1 = Sample(pk=s0.pk, name='Test 1')
s1.save()  # Attempts UPDATE first, succeeds

# In Django 3.0+: This fails with IntegrityError
s0 = Sample.objects.create()
s1 = Sample(pk=s0.pk, name='Test 1')
s1.save()  # Forces INSERT, fails with UNIQUE constraint violation
```

This also affected the `loaddata` management command when loading fixtures with explicit pk values multiple times.

## Root Cause
The optimization introduced in Django 3.0 (related to ticket #29260) would force an INSERT when:
1. `self._state.adding` is True (new instance)
2. The pk field has a default value

However, this didn't distinguish between:
- A pk value that was auto-generated from the default
- A pk value that was explicitly set by the user

## Solution
The fix tracks whether the primary key was explicitly provided by the user during `__init__`:

1. **Added `pk_explicitly_set` flag to `ModelState`**: Tracks if the pk was provided via args or kwargs
2. **Updated `Model.__init__`**: Sets `pk_explicitly_set = True` when pk is found in initialization arguments
3. **Updated `Model._save_table`**: Only forces INSERT if pk was NOT explicitly set

### Key Changes

#### `django/db/models/base.py`

1. **ModelState class** (line 393-403):
   - Added `pk_explicitly_set` field to track explicit pk values

2. **Model.__init__** (lines 428-456):
   - Added logic to detect when pk is provided in positional args
   - Added logic to detect when pk is provided in kwargs (both by field name and by `pk` property)
   - Sets `self._state.pk_explicitly_set = True` when detected
   - Handles three cases:
     - Positional args: Checks if pk field index is present in args
     - Keyword args (field name): Checks if pk field attname is in kwargs
     - Keyword args (`pk` property): Checks if 'pk' is in kwargs

3. **Model._save_table** (lines 869-878):
   - Modified the optimization condition to include `not self._state.pk_explicitly_set`
   - This preserves the optimization for auto-generated pks while allowing explicit pks to attempt UPDATE first

#### `tests/basic/tests.py`

Added comprehensive tests:
1. `test_save_primary_with_default_and_explicit_pk`: Tests updating existing object with explicit pk
2. `test_save_primary_with_default_explicit_pk_new`: Tests inserting new object with explicit pk
3. `test_save_primary_with_default_from_db`: Tests saving object loaded from database

## Behavior After Fix

### Scenario 1: No explicit pk (optimization applies)
```python
obj = PrimaryKeyWithDefault()  # pk auto-generated from default
obj.save()  # 1 query: INSERT only (no UPDATE attempt)
```

### Scenario 2: Explicit pk, object exists
```python
obj1 = PrimaryKeyWithDefault.objects.create()
obj2 = PrimaryKeyWithDefault(uuid=obj1.uuid)  # Explicit pk
obj2.save()  # 1 query: UPDATE (finds row, updates it)
```

### Scenario 3: Explicit pk, object doesn't exist
```python
obj1 = PrimaryKeyWithDefault.objects.create()
obj2 = PrimaryKeyWithDefault(uuid=some_new_uuid)  # Explicit pk, new value
obj2.save()  # 2 queries: UPDATE (0 rows) + INSERT
```

### Scenario 4: Object from database
```python
obj = PrimaryKeyWithDefault.objects.get(uuid=some_uuid)
obj.save()  # 1 query: UPDATE (adding=False, so optimization doesn't apply)
```

## Backward Compatibility
This fix restores the Django 2.2 behavior when an explicit pk is provided, while maintaining the optimization introduced in Django 3.0 for auto-generated pk values. All existing tests pass.

## Testing
All tests pass:
- `basic` module: 60 tests
- `model_fields` module: 320 tests
- `get_or_create` module: 45 tests
- `bulk_create` module: 27 tests
- `save_delete_hooks` module: Various tests

The fix specifically addresses:
- Direct model saves with explicit pk
- Fixture loading with `loaddata` command
- Object updates and inserts
- Database-loaded object behavior
