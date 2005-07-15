# Django settings for {{ app_name }} project.

DEBUG = True

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

LANGUAGE_CODE = 'en-us'

DATABASE_ENGINE = 'postgresql' # Either 'postgresql' or 'mysql'.
DATABASE_NAME = ''
DATABASE_USER = ''
DATABASE_HOST = '' # Set to empty string for localhost.

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT.
# Example: "http://media.lawrence.com"
MEDIA_URL = ''

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates".
)

INSTALLED_APPS = (
)
