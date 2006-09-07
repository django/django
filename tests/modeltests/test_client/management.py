from django.dispatch import dispatcher
from django.db.models import signals
import models as test_client_app
from django.contrib.auth.models import User

def setup_test(app, created_models, verbosity):
    # Create a user account for the login-based tests
    User.objects.create_user('testclient','testclient@example.com', 'password')

dispatcher.connect(setup_test, sender=test_client_app, signal=signals.post_syncdb)
