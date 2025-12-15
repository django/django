Refs #2259 -- Default readonly for non-AutoField PKs in admin, with opt-out and inline support.

## Problem

Non-AutoField primary keys are currently editable in admin change views, which can lead to silent creation of duplicate rows when a PK is changed to an existing value, and URL mismatches where the form saves to a different row but the URL stays on the original row.

## Solution

This PR makes non-AutoField primary keys readonly by default in admin change views, while keeping them editable in add views. The implementation:

- Adds `editable_primary_key = False` attribute to `BaseModelAdmin`
- Overrides `get_readonly_fields()` to automatically add PK field name for non-AutoField PKs when editing existing objects
- Works for both `ModelAdmin` and `InlineModelAdmin` via `BaseModelAdmin` inheritance
- Provides opt-out via `editable_primary_key=True` for edge cases

## Testing

Test coverage includes readonly behavior in change views, editable behavior in add views, inline support, AutoField exclusion, and opt-out mechanism.

## Documentation

- Added `editable_primary_key` attribute documentation
- Added release note referencing ticket #2259

## Author

LinkedIn: https://www.linkedin.com/in/pouria-sadat-102832244/
