# Default Django settings. Override these with settings in the module
# pointed-to by the DJANGO_SETTINGS_MODULE environment variable.

# This is defined here as a do-nothing function because we can't import
# django.utils.translation -- that module depends on the settings.
gettext_noop = lambda s: s

####################
# CORE             #
####################

DEBUG = False
TEMPLATE_DEBUG = False

# Whether to use the "Etag" header. This saves bandwidth but slows down performance.
USE_ETAGS = False

# People who get code error notifications.
# In the format (('Full Name', 'email@domain.com'), ('Full Name', 'anotheremail@domain.com'))
ADMINS = ()

# Tuple of IP addresses, as strings, that:
#   * See debug comments, when DEBUG is true
#   * Receive x-headers
INTERNAL_IPS = ()

# Local time zone for this installation. All choices can be found here:
# http://www.postgresql.org/docs/8.1/static/datetime-keywords.html#DATETIME-TIMEZONE-SET-TABLE
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.w3.org/TR/REC-html40/struct/dirlang.html#langcodes
# http://blogs.law.harvard.edu/tech/stories/storyReader$15
LANGUAGE_CODE = 'en-us'

# Languages we provide translations for, out of the box. The language name
# should be the utf-8 encoded local name for the language.
LANGUAGES = (
    ('ar', gettext_noop('Arabic')),
    ('bn', gettext_noop('Bengali')),
    ('ca', gettext_noop('Catalan')),
    ('cs', gettext_noop('Czech')),
    ('cy', gettext_noop('Welsh')),
    ('da', gettext_noop('Danish')),
    ('de', gettext_noop('German')),
    ('el', gettext_noop('Greek')),
    ('en', gettext_noop('English')),
    ('es', gettext_noop('Spanish')),
    ('es_AR', gettext_noop('Argentinean Spanish')),
    ('fi', gettext_noop('Finnish')),
    ('fr', gettext_noop('French')),
    ('gl', gettext_noop('Galician')),
    ('hu', gettext_noop('Hungarian')),
    ('he', gettext_noop('Hebrew')),
    ('is', gettext_noop('Icelandic')),
    ('it', gettext_noop('Italian')),
    ('ja', gettext_noop('Japanese')),
    ('kn', gettext_noop('Kannada')),
    ('lv', gettext_noop('Latvian')),
    ('mk', gettext_noop('Macedonian')),
    ('nl', gettext_noop('Dutch')),
    ('no', gettext_noop('Norwegian')),
    ('pl', gettext_noop('Polish')),
    ('pt-br', gettext_noop('Brazilian')),
    ('ro', gettext_noop('Romanian')),
    ('ru', gettext_noop('Russian')),
    ('sk', gettext_noop('Slovak')),
    ('sl', gettext_noop('Slovenian')),
    ('sr', gettext_noop('Serbian')),
    ('sv', gettext_noop('Swedish')),
    ('ta', gettext_noop('Tamil')),
    ('tr', gettext_noop('Turkish')),
    ('uk', gettext_noop('Ukrainian')),
    ('zh-cn', gettext_noop('Simplified Chinese')),
    ('zh-tw', gettext_noop('Traditional Chinese')),
)

# Languages using BiDi (right-to-left) layout
LANGUAGES_BIDI = ("he", "ar")

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Not-necessarily-technical managers of the site. They get broken link
# notifications and other various e-mails.
MANAGERS = ADMINS

# Default content type and charset to use for all HttpResponse objects, if a
# MIME type isn't manually specified. These are used to construct the
# Content-Type header.
DEFAULT_CONTENT_TYPE = 'text/html'
DEFAULT_CHARSET = 'utf-8'

# E-mail address that error messages come from.
SERVER_EMAIL = 'root@localhost'

# Whether to send broken-link e-mails.
SEND_BROKEN_LINK_EMAILS = False

# Database connection info.
DATABASE_ENGINE = ''           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'ado_mssql'.
DATABASE_NAME = ''             # Or path to database file if using sqlite3.
DATABASE_USER = ''             # Not used with sqlite3.
DATABASE_PASSWORD = ''         # Not used with sqlite3.
DATABASE_HOST = ''             # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = ''             # Set to empty string for default. Not used with sqlite3.
DATABASE_OPTIONS = {}          # Set to empty dictionary for default.

# Host for sending e-mail.
EMAIL_HOST = 'localhost'

# Port for sending e-mail.
EMAIL_PORT = 25

# Optional SMTP authentication information for EMAIL_HOST.
EMAIL_HOST_USER = ''
EMAIL_HOST_PASSWORD = ''

# List of strings representing installed apps.
INSTALLED_APPS = ()

# List of locations of the template source files, in search order.
TEMPLATE_DIRS = ()

# List of callables that know how to import templates from various sources.
# See the comments in django/core/template/loader.py for interface
# documentation.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)

# List of processors used by RequestContext to populate the context.
# Each one should be a callable that takes the request object as its
# only parameter and returns a dictionary to add to the context.
TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
#    'django.core.context_processors.request',
)

# Output to use in template system for invalid (e.g. misspelled) variables.
TEMPLATE_STRING_IF_INVALID = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Default e-mail address to use for various automated correspondence from
# the site managers.
DEFAULT_FROM_EMAIL = 'webmaster@localhost'

# Subject-line prefix for email messages send with django.core.mail.mail_admins
# or ...mail_managers.  Make sure to include the trailing space.
EMAIL_SUBJECT_PREFIX = '[Django] '

# Whether to append trailing slashes to URLs.
APPEND_SLASH = True

# Whether to prepend the "www." subdomain to URLs that don't have it.
PREPEND_WWW = False

# List of compiled regular expression objects representing User-Agent strings
# that are not allowed to visit any page, systemwide. Use this for bad
# robots/crawlers. Here are a few examples:
#     import re
#     DISALLOWED_USER_AGENTS = (
#         re.compile(r'^NaverBot.*'),
#         re.compile(r'^EmailSiphon.*'),
#         re.compile(r'^SiteSucker.*'),
#         re.compile(r'^sohu-search')
#     )
DISALLOWED_USER_AGENTS = ()

ABSOLUTE_URL_OVERRIDES = {}

# Tuple of strings representing allowed prefixes for the {% ssi %} tag.
# Example: ('/home/html', '/var/www')
ALLOWED_INCLUDE_ROOTS = ()

# If this is a admin settings module, this should be a list of
# settings modules (in the format 'foo.bar.baz') for which this admin
# is an admin.
ADMIN_FOR = ()

# 404s that may be ignored.
IGNORABLE_404_STARTS = ('/cgi-bin/', '/_vti_bin', '/_vti_inf')
IGNORABLE_404_ENDS = ('mail.pl', 'mailform.pl', 'mail.cgi', 'mailform.cgi', 'favicon.ico', '.php')

# A secret key for this particular Django installation. Used in secret-key
# hashing algorithms. Set this in your settings, or Django will complain
# loudly.
SECRET_KEY = ''

# Path to the "jing" executable -- needed to validate XMLFields
JING_PATH = "/usr/bin/jing"

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT.
# Example: "http://media.lawrence.com"
MEDIA_URL = ''

# Default formatting for date objects. See all available format strings here:
# http://www.djangoproject.com/documentation/templates/#now
DATE_FORMAT = 'N j, Y'

# Default formatting for datetime objects. See all available format strings here:
# http://www.djangoproject.com/documentation/templates/#now
DATETIME_FORMAT = 'N j, Y, P'

# Default formatting for time objects. See all available format strings here:
# http://www.djangoproject.com/documentation/templates/#now
TIME_FORMAT = 'P'

# Default formatting for date objects when only the year and month are relevant.
# See all available format strings here:
# http://www.djangoproject.com/documentation/templates/#now
YEAR_MONTH_FORMAT = 'F Y'

# Default formatting for date objects when only the month and day are relevant.
# See all available format strings here:
# http://www.djangoproject.com/documentation/templates/#now
MONTH_DAY_FORMAT = 'F j'

# Do you want to manage transactions manually?
# Hint: you really don't!
TRANSACTIONS_MANAGED = False

# The User-Agent string to use when checking for URL validity through the
# isExistingURL validator.
URL_VALIDATOR_USER_AGENT = "Django/0.96pre (http://www.djangoproject.com)"

##############
# MIDDLEWARE #
##############

# List of middleware classes to use.  Order is important; in the request phase,
# this middleware classes will be applied in the order given, and in the
# response phase the middleware will be applied in reverse order.
MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
#     'django.middleware.http.ConditionalGetMiddleware',
#     'django.middleware.gzip.GZipMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.doc.XViewMiddleware',
)

############
# SESSIONS #
############

SESSION_COOKIE_NAME = 'sessionid'         # Cookie name. This can be whatever you want.
SESSION_COOKIE_AGE = 60 * 60 * 24 * 7 * 2 # Age of cookie, in seconds (default: 2 weeks).
SESSION_COOKIE_DOMAIN = None              # A string like ".lawrence.com", or None for standard domain cookie.
SESSION_COOKIE_SECURE = False             # Whether the session cookie should be secure (https:// only).
SESSION_SAVE_EVERY_REQUEST = False        # Whether to save the session data on every request.
SESSION_EXPIRE_AT_BROWSER_CLOSE = False   # Whether sessions expire when a user closes his browser.

#########
# CACHE #
#########

# The cache backend to use.  See the docstring in django.core.cache for the
# possible values.
CACHE_BACKEND = 'simple://'
CACHE_MIDDLEWARE_KEY_PREFIX = ''

####################
# COMMENTS         #
####################

COMMENTS_ALLOW_PROFANITIES = False

# The profanities that will trigger a validation error in the
# 'hasNoProfanities' validator. All of these should be in lowercase.
PROFANITIES_LIST = ('asshat', 'asshead', 'asshole', 'cunt', 'fuck', 'gook', 'nigger', 'shit')

# The group ID that designates which users are banned.
# Set to None if you're not using it.
COMMENTS_BANNED_USERS_GROUP = None

# The group ID that designates which users can moderate comments.
# Set to None if you're not using it.
COMMENTS_MODERATORS_GROUP = None

# The group ID that designates the users whose comments should be e-mailed to MANAGERS.
# Set to None if you're not using it.
COMMENTS_SKETCHY_USERS_GROUP = None

# The system will e-mail MANAGERS the first COMMENTS_FIRST_FEW comments by each
# user. Set this to 0 if you want to disable it.
COMMENTS_FIRST_FEW = 0

# A tuple of IP addresses that have been banned from participating in various
# Django-powered features.
BANNED_IPS = ()

##################
# AUTHENTICATION #
##################

AUTHENTICATION_BACKENDS = ('django.contrib.auth.backends.ModelBackend',)

###########
# TESTING #
###########

# The name of the method to use to invoke the test suite
TEST_RUNNER = 'django.test.simple.run_tests'

# The name of the database to use for testing purposes.
# If None, a name of 'test_' + DATABASE_NAME will be assumed
TEST_DATABASE_NAME = None
