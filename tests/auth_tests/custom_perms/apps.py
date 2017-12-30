from django.apps import AppConfig


class CustomAppConfig(AppConfig):
    name = 'auth_tests.custom_perms'
    permissions = [
        ('can_haz', 'Can haz cheeseburger.'),
    ]
