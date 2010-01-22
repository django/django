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

# Whether the framework should propagate raw exceptions rather than catching
# them. This is useful under some testing siutations and should never be used
# on a live site.
DEBUG_PROPAGATE_EXCEPTIONS = False

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
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name (although not all
# systems may support all possibilities).
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

# Languages we provide translations for, out of the box. The language name
# should be the utf-8 encoded local name for the language.
LANGUAGES = (
    ('ar', gettext_noop('Arabic')),
    ('bn', gettext_noop('Bengali')),
    ('bg', gettext_noop('Bulgarian')),
    ('ca', gettext_noop('Catalan')),
    ('cs', gettext_noop('Czech')),
    ('cy', gettext_noop('Welsh')),
    ('da', gettext_noop('Danish')),
    ('de', gettext_noop('German')),
    ('el', gettext_noop('Greek')),
    ('en', gettext_noop('English')),
    ('es', gettext_noop('Spanish')),
    ('et', gettext_noop('Estonian')),
    ('es-ar', gettext_noop('Argentinean Spanish')),
    ('eu', gettext_noop('Basque')),
    ('fa', gettext_noop('Persian')),
    ('fi', gettext_noop('Finnish')),
    ('fr', gettext_noop('French')),
    ('ga', gettext_noop('Irish')),
    ('gl', gettext_noop('Galician')),
    ('hu', gettext_noop('Hungarian')),
    ('he', gettext_noop('Hebrew')),
    ('hi', gettext_noop('Hindi')),
    ('hr', gettext_noop('Croatian')),
    ('is', gettext_noop('Icelandic')),
    ('it', gettext_noop('Italian')),
    ('ja', gettext_noop('Japanese')),
    ('ka', gettext_noop('Georgian')),
    ('ko', gettext_noop('Korean')),
    ('km', gettext_noop('Khmer')),
    ('kn', gettext_noop('Kannada')),
    ('lv', gettext_noop('Latvian')),
    ('lt', gettext_noop('Lithuanian')),
    ('mk', gettext_noop('Macedonian')),
    ('nl', gettext_noop('Dutch')),
    ('no', gettext_noop('Norwegian')),
    ('pl', gettext_noop('Polish')),
    ('pt', gettext_noop('Portuguese')),
    ('pt-br', gettext_noop('Brazilian Portuguese')),
    ('ro', gettext_noop('Romanian')),
    ('ru', gettext_noop('Russian')),
    ('sk', gettext_noop('Slovak')),
    ('sl', gettext_noop('Slovenian')),
    ('sr', gettext_noop('Serbian')),
    ('sr-latn', gettext_noop('Serbian Latin')),
    ('sv', gettext_noop('Swedish')),
    ('ta', gettext_noop('Tamil')),
    ('te', gettext_noop('Telugu')),
    ('th', gettext_noop('Thai')),
    ('tr', gettext_noop('Turkish')),
    ('uk', gettext_noop('Ukrainian')),
    ('zh-cn', gettext_noop('Simplified Chinese')),
    ('zh-tw', gettext_noop('Traditional Chinese')),
)

# Languages using BiDi (right-to-left) layout
LANGUAGES_BIDI = ("he", "ar", "fa")

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True
LOCALE_PATHS = ()
LANGUAGE_COOKIE_NAME = 'django_language'

# If you set this to True, Django will format dates, numbers and calendars
# according to user current locale
USE_L10N = False

# Not-necessarily-technical managers of the site. They get broken link
# notifications and other various e-mails.
MANAGERS = ADMINS

# Default content type and charset to use for all HttpResponse objects, if a
# MIME type isn't manually specified. These are used to construct the
# Content-Type header.
DEFAULT_CONTENT_TYPE = 'text/html'
DEFAULT_CHARSET = 'utf-8'

# Encoding of files read from disk (template and initial SQL files).
FILE_CHARSET = 'utf-8'

# E-mail address that error messages come from.
SERVER_EMAIL = 'root@localhost'

# Whether to send broken-link e-mails.
SEND_BROKEN_LINK_EMAILS = False

# Database connection info.
# Legacy format
DATABASE_ENGINE = ''           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
DATABASE_NAME = ''             # Or path to database file if using sqlite3.
DATABASE_USER = ''             # Not used with sqlite3.
DATABASE_PASSWORD = ''         # Not used with sqlite3.
DATABASE_HOST = ''             # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = ''             # Set to empty string for default. Not used with sqlite3.
DATABASE_OPTIONS = {}          # Set to empty dictionary for default.

# New format
DATABASES = {
}

# Classes used to implement db routing behaviour
DATABASE_ROUTERS = []

# The email backend to use. For possible shortcuts see django.core.mail.
# The default is to use the SMTP backend.
# Third-party backends can be specified by providing a Python path
# to a module that defines an EmailBackend class.
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

# Host for sending e-mail.
EMAIL_HOST = 'localhost'

# Port for sending e-mail.
EMAIL_PORT = 25

# Optional SMTP authentication information for EMAIL_HOST.
EMAIL_HOST_USER = ''
EMAIL_HOST_PASSWORD = ''
EMAIL_USE_TLS = False

# List of strings representing installed apps.
INSTALLED_APPS = ()

# List of locations of the template source files, in search order.
TEMPLATE_DIRS = ()

# List of callables that know how to import templates from various sources.
# See the comments in django/core/template/loader.py for interface
# documentation.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

# List of processors used by RequestContext to populate the context.
# Each one should be a callable that takes the request object as its
# only parameter and returns a dictionary to add to the context.
TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
#    'django.core.context_processors.request',
    'django.contrib.messages.context_processors.messages',
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

# Override the server-derived value of SCRIPT_NAME
FORCE_SCRIPT_NAME = None

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

# Default file storage mechanism that holds media.
DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT.
# Example: "http://media.lawrence.com"
MEDIA_URL = ''

# List of upload handler classes to be applied in order.
FILE_UPLOAD_HANDLERS = (
    'django.core.files.uploadhandler.MemoryFileUploadHandler',
    'django.core.files.uploadhandler.TemporaryFileUploadHandler',
)

# Maximum size, in bytes, of a request before it will be streamed to the
# file system instead of into memory.
FILE_UPLOAD_MAX_MEMORY_SIZE = 2621440 # i.e. 2.5 MB

# Directory in which upload streamed files will be temporarily saved. A value of
# `None` will make Django use the operating system's default temporary directory
# (i.e. "/tmp" on *nix systems).
FILE_UPLOAD_TEMP_DIR = None

# The numeric mode to set newly-uploaded files to. The value should be a mode
# you'd pass directly to os.chmod; see http://docs.python.org/lib/os-file-dir.html.
FILE_UPLOAD_PERMISSIONS = None

# Python module path where user will place custom format definition.
# The directory where this setting is pointing should contain subdirectories
# named as the locales, containing a formats.py file
# (i.e. "myproject.locale" for myproject/locale/en/formats.py etc. use)
FORMAT_MODULE_PATH = None

# Default formatting for date objects. See all available format strings here:
# http://docs.djangoproject.com/en/dev/ref/templates/builtins/#now
DATE_FORMAT = 'N j, Y'

# Default formatting for datetime objects. See all available format strings here:
# http://docs.djangoproject.com/en/dev/ref/templates/builtins/#now
DATETIME_FORMAT = 'N j, Y, P'

# Default formatting for time objects. See all available format strings here:
# http://docs.djangoproject.com/en/dev/ref/templates/builtins/#now
TIME_FORMAT = 'P'

# Default formatting for date objects when only the year and month are relevant.
# See all available format strings here:
# http://docs.djangoproject.com/en/dev/ref/templates/builtins/#now
YEAR_MONTH_FORMAT = 'F Y'

# Default formatting for date objects when only the month and day are relevant.
# See all available format strings here:
# http://docs.djangoproject.com/en/dev/ref/templates/builtins/#now
MONTH_DAY_FORMAT = 'F j'

# Default shortformatting for date objects. See all available format strings here:
# http://docs.djangoproject.com/en/dev/ref/templates/builtins/#now
SHORT_DATE_FORMAT = 'm/d/Y'

# Default short formatting for datetime objects.
# See all available format strings here:
# http://docs.djangoproject.com/en/dev/ref/templates/builtins/#now
SHORT_DATETIME_FORMAT = 'm/d/Y P'

# Default formats to be used when parsing dates from input boxes, in order
# See all available format string here:
# http://docs.python.org/library/datetime.html#strftime-behavior
# * Note that these format strings are different from the ones to display dates
DATE_INPUT_FORMATS = (
    '%Y-%m-%d', '%m/%d/%Y', '%m/%d/%y', # '2006-10-25', '10/25/2006', '10/25/06'
    '%b %d %Y', '%b %d, %Y',            # 'Oct 25 2006', 'Oct 25, 2006'
    '%d %b %Y', '%d %b, %Y',            # '25 Oct 2006', '25 Oct, 2006'
    '%B %d %Y', '%B %d, %Y',            # 'October 25 2006', 'October 25, 2006'
    '%d %B %Y', '%d %B, %Y',            # '25 October 2006', '25 October, 2006'
)

# Default formats to be used when parsing times from input boxes, in order
# See all available format string here:
# http://docs.python.org/library/datetime.html#strftime-behavior
# * Note that these format strings are different from the ones to display dates
TIME_INPUT_FORMATS = (
    '%H:%M:%S',     # '14:30:59'
    '%H:%M',        # '14:30'
)

# Default formats to be used when parsing dates and times from input boxes,
# in order
# See all available format string here:
# http://docs.python.org/library/datetime.html#strftime-behavior
# * Note that these format strings are different from the ones to display dates
DATETIME_INPUT_FORMATS = (
    '%Y-%m-%d %H:%M:%S',     # '2006-10-25 14:30:59'
    '%Y-%m-%d %H:%M',        # '2006-10-25 14:30'
    '%Y-%m-%d',              # '2006-10-25'
    '%m/%d/%Y %H:%M:%S',     # '10/25/2006 14:30:59'
    '%m/%d/%Y %H:%M',        # '10/25/2006 14:30'
    '%m/%d/%Y',              # '10/25/2006'
    '%m/%d/%y %H:%M:%S',     # '10/25/06 14:30:59'
    '%m/%d/%y %H:%M',        # '10/25/06 14:30'
    '%m/%d/%y',              # '10/25/06'
)

# First day of week, to be used on calendars
# 0 means Sunday, 1 means Monday...
FIRST_DAY_OF_WEEK = 0

# Decimal separator symbol
DECIMAL_SEPARATOR = '.'

# Boolean that sets whether to add thousand separator when formatting numbers
USE_THOUSAND_SEPARATOR = False

# Number of digits that will be togheter, when spliting them by THOUSAND_SEPARATOR
# 0 means no grouping, 3 means splitting by thousands...
NUMBER_GROUPING = 0

# Thousand separator symbol
THOUSAND_SEPARATOR = ','

# Do you want to manage transactions manually?
# Hint: you really don't!
TRANSACTIONS_MANAGED = False

# The User-Agent string to use when checking for URL validity through the
# isExistingURL validator.
from django import get_version
URL_VALIDATOR_USER_AGENT = "Django/%s (http://www.djangoproject.com)" % get_version()

# The tablespaces to use for each model when not specified otherwise.
DEFAULT_TABLESPACE = ''
DEFAULT_INDEX_TABLESPACE = ''

##############
# MIDDLEWARE #
##############

# List of middleware classes to use.  Order is important; in the request phase,
# this middleware classes will be applied in the order given, and in the
# response phase the middleware will be applied in reverse order.
MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
#     'django.middleware.http.ConditionalGetMiddleware',
#     'django.middleware.gzip.GZipMiddleware',
)

############
# SESSIONS #
############

SESSION_COOKIE_NAME = 'sessionid'                       # Cookie name. This can be whatever you want.
SESSION_COOKIE_AGE = 60 * 60 * 24 * 7 * 2               # Age of cookie, in seconds (default: 2 weeks).
SESSION_COOKIE_DOMAIN = None                            # A string like ".lawrence.com", or None for standard domain cookie.
SESSION_COOKIE_SECURE = False                           # Whether the session cookie should be secure (https:// only).
SESSION_COOKIE_PATH = '/'                               # The path of the session cookie.
SESSION_SAVE_EVERY_REQUEST = False                      # Whether to save the session data on every request.
SESSION_EXPIRE_AT_BROWSER_CLOSE = False                 # Whether a user's session cookie expires when the Web browser is closed.
SESSION_ENGINE = 'django.contrib.sessions.backends.db'  # The module to store session data
SESSION_FILE_PATH = None                                # Directory to store session files if using the file session module. If None, the backend will use a sensible default.

#########
# CACHE #
#########

# The cache backend to use.  See the docstring in django.core.cache for the
# possible values.
CACHE_BACKEND = 'locmem://'
CACHE_MIDDLEWARE_KEY_PREFIX = ''
CACHE_MIDDLEWARE_SECONDS = 600

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

LOGIN_URL = '/accounts/login/'

LOGOUT_URL = '/accounts/logout/'

LOGIN_REDIRECT_URL = '/accounts/profile/'

# The number of days a password reset link is valid for
PASSWORD_RESET_TIMEOUT_DAYS = 3

########
# CSRF #
########

# Dotted path to callable to be used as view when a request is
# rejected by the CSRF middleware.
CSRF_FAILURE_VIEW = 'django.views.csrf.csrf_failure'

# Name and domain for CSRF cookie.
CSRF_COOKIE_NAME = 'csrftoken'
CSRF_COOKIE_DOMAIN = None

############
# MESSAGES #
############

# Class to use as messges backend
MESSAGE_STORAGE = 'django.contrib.messages.storage.user_messages.LegacyFallbackStorage'

# Default values of MESSAGE_LEVEL and MESSAGE_TAGS are defined within
# django.contrib.messages to avoid imports in this settings file.

###########
# TESTING #
###########

# The name of the class to use to run the test suite
TEST_RUNNER = 'django.test.simple.DjangoTestSuiteRunner'

# The name of the database to use for testing purposes.
# If None, a name of 'test_' + DATABASE_NAME will be assumed
TEST_DATABASE_NAME = None

# Strings used to set the character set and collation order for the test
# database. These values are passed literally to the server, so they are
# backend-dependent. If None, no special settings are sent (system defaults are
# used).
TEST_DATABASE_CHARSET = None
TEST_DATABASE_COLLATION = None

############
# FIXTURES #
############

# The list of directories to search for fixtures
FIXTURE_DIRS = ()
