"""
Miscellaneous helper functions.
"""

import warnings

from django.utils.encoding import smart_unicode

# Django currently supports two forms of ordering.
# Form 1 (deprecated) example:
#     order_by=(('pub_date', 'DESC'), ('headline', 'ASC'), (None, 'RANDOM'))
# Form 2 (new-style) example:
#     order_by=('-pub_date', 'headline', '?')
# Form 1 is deprecated and will no longer be supported for Django's first
# official release. The following code converts from Form 1 to Form 2.

LEGACY_ORDERING_MAPPING = {'ASC': '_', 'DESC': '-_', 'RANDOM': '?'}

def handle_legacy_orderlist(order_list):
    if not order_list or isinstance(order_list[0], basestring):
        return order_list
    else:
        new_order_list = [LEGACY_ORDERING_MAPPING[j.upper()].replace('_', smart_unicode(i)) for i, j in order_list]
        warnings.warn("%r ordering syntax is deprecated. Use %r instead."
                % (order_list, new_order_list), DeprecationWarning)
        return new_order_list

