from django.contrib.auth.tests.custom_user import *
from django.contrib.auth.tests.auth_backends import *
from django.contrib.auth.tests.basic import *
from django.contrib.auth.tests.context_processors import *
from django.contrib.auth.tests.decorators import *
from django.contrib.auth.tests.forms import *
from django.contrib.auth.tests.remote_user import *
from django.contrib.auth.tests.management import *
from django.contrib.auth.tests.models import *
from django.contrib.auth.tests.handlers import *
from django.contrib.auth.tests.hashers import *
from django.contrib.auth.tests.signals import *
from django.contrib.auth.tests.tokens import *
from django.contrib.auth.tests.views import *

# The password for the fixture data users is 'password'

from django.dispatch import receiver
from django.test.signals import setting_changed


@receiver(setting_changed)
def user_model_swapped(**kwargs):
    if kwargs['setting'] == 'AUTH_USER_MODEL':
        from django.db.models.manager import ensure_default_manager
        from django.contrib.auth.models import User
        # Reset User manager
        setattr(User, 'objects', User._default_manager)
        ensure_default_manager(User)
