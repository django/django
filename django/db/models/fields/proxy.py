"""
Field-like classes that aren't really fields. It's easier to use objects that
have the same attributes as fields sometimes (avoids a lot of special casing).
"""

from django.db.models import fields

class OrderWrt(fields.IntegerField):
    """
    A proxy for the _order database field that is used when
    Meta.order_with_respect_to is specified.
    """

    def __init__(self, model, *args, **kwargs):
        super(OrderWrt, self).__init__(*args, **kwargs)
        self.model = model
        self.attname = '_order'
        self.column = '_order'
        self.name = '_order'
