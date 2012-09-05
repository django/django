from __future__ import unicode_literals

# Do not try cPickle here (see #18340)
import pickle

from django.utils.crypto import salted_hmac
from django.utils import six


def form_hmac(form):
    """
    Calculates a security hash for the given Form instance.
    """
    data = []
    for bf in form:
        # Get the value from the form data. If the form allows empty or hasn't
        # changed then don't call clean() to avoid trigger validation errors.
        if form.empty_permitted and not form.has_changed():
            value = bf.data or ''
        else:
            value = bf.field.clean(bf.data) or ''
        if isinstance(value, six.string_types):
            value = value.strip()
        data.append((bf.name, value))

    pickled = pickle.dumps(data, pickle.HIGHEST_PROTOCOL)
    key_salt = 'django.contrib.formtools'
    return salted_hmac(key_salt, pickled).hexdigest()
