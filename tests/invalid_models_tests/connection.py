from django.conf import settings
from django.db import router

from .test_models import OtherModelTests, IsolatedModelsTestCase

cls = OtherModelTests(IsolatedModelsTestCase)
db = None
for db_key in settings.DATABASES.keys():
    # skip databases where the model won't be created
    if not router.allow_migrate(db_key, cls):
        continue
    db = db_key
