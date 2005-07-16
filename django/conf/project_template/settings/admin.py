# Django settings for {{ project_name }} project admin site.

from main import *

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates".
)
ROOT_URLCONF = 'django.conf.urls.admin'
MIDDLEWARE_CLASSES = (
    'django.middleware.admin.AdminUserRequired',
    'django.middleware.common.CommonMiddleware',
)
