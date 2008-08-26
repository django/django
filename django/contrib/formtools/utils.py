try:
    import cPickle as pickle
except ImportError:
    import pickle
    
from django.conf import settings
from django.utils.hashcompat import md5_constructor
from django.forms import BooleanField

def security_hash(request, form, *args):
        """
        Calculates a security hash for the given Form instance.

        This creates a list of the form field names/values in a deterministic
        order, pickles the result with the SECRET_KEY setting, then takes an md5
        hash of that.
        """
        # Ensure that the hash does not change when a BooleanField's bound
        # data is a string `False' or a boolean False.
        # Rather than re-coding this special behaviour here, we
        # create a dummy BooleanField and call its clean method to get a
        # boolean True or False verdict that is consistent with
        # BooleanField.clean()
        dummy_bool = BooleanField(required=False)
        def _cleaned_data(bf):
            if isinstance(bf.field, BooleanField):
                return dummy_bool.clean(bf.data)
            return bf.data
        
        data = [(bf.name, _cleaned_data(bf) or '') for bf in form]
        data.extend(args)
        data.append(settings.SECRET_KEY)
        
        # Use HIGHEST_PROTOCOL because it's the most efficient. It requires
        # Python 2.3, but Django requires 2.3 anyway, so that's OK.
        pickled = pickle.dumps(data, pickle.HIGHEST_PROTOCOL)
        
        return md5_constructor(pickled).hexdigest()

