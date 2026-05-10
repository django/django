import django
from django.conf import settings
from django.db import models
from django.core.management import call_command

settings.configure(
    INSTALLED_APPS=[
        'django.contrib.contenttypes',
    ],
    DATABASES={
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:',
        }
    }
)
django.setup()

def try_field(field_instance):
    try:
        errors = field_instance.check()
        print(f"Passed init, errors: {errors}")
    except Exception as e:
        print(f"Failed init: {type(e)} {e}")

try_field(models.CharField(max_length=-1))
try_field(models.FileField(upload_to="/somewhere"))
try_field(models.IntegerField(choices=123))

