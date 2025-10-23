# Proposed Improvement for Ticket #36594

## Issue Summary
Ticket #36594 addresses the need to clarify UniqueConstraint's `nulls_distinct` system check warning. The current warning message is misleading as it doesn't clearly indicate that boolean values for `nulls_distinct` are not supported on databases other than PostgreSQL 15+.

## Current Warning Message (line 386-387 in django/db/models/constraints.py)
```python
f"{connection.display_name} does not support unique constraints "
"with nulls distinct.",
```

## Proposed Improvement
Change the warning message to be more explicit about the parameter not being supported:

```python
f"{connection.display_name} does not support the 'nulls_distinct' parameter "
"for UniqueConstraint. Remove or set nulls_distinct=None.",
```

## Rationale
1. **Explicit mention of the parameter**: Makes it clear that the issue is with the `nulls_distinct` parameter itself
2. **Actionable guidance**: Tells users exactly what to do (remove or set to None)
3. **Reduces confusion**: Users won't misinterpret whether True or False is the correct value

## Additional Documentation Enhancement
The hint could also be improved to provide more context:

```python
hint=(
    "The nulls_distinct parameter is only supported on PostgreSQL 15+. "
    "A constraint won't be created on this database. "
    "Silence this warning if you don't care about it."
),
```

## Note
This proposal is being submitted as an alternative/complementary improvement to PR #19870, which already addresses this ticket with a different approach. The intent is to provide an even clearer message based on the original ticket reporter's feedback.
