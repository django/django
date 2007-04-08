"""
An alphabetical list of states for use as `choices` in a formfield.

This exists in this standalone file so that it's only imported into memory
when explicitly needed.
"""

STATE_CHOICES = (
    ('ACT', 'Australian Capital Territory'),
    ('NSW', 'New South Wales'),
    ('NT', 'Northern Territory'),
    ('QLD', 'Queensland'),
    ('SA', 'South Australia'),
    ('TAS', 'Tasmania'),
    ('VIC', 'Victoria'),
    ('WA', 'Western Australia'),
)
