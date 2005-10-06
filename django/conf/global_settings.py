# Default Django settings. Override these with settings in the module
# pointed-to by the DJANGO_SETTINGS_MODULE environment variable.

####################
# CORE             #
####################

DEBUG = False

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
# http://www.postgresql.org/docs/current/static/datetime-keywords.html#DATETIME-TIMEZONE-SET-TABLE
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.w3.org/TR/REC-html40/struct/dirlang.html#langcodes
# http://blogs.law.harvard.edu/tech/stories/storyReader$15
LANGUAGE_CODE = 'en-us'

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
DATABASE_ENGINE = 'postgresql' # 'postgresql', 'mysql', or 'sqlite3'.
DATABASE_NAME = ''
DATABASE_USER = ''
DATABASE_PASSWORD = ''
DATABASE_HOST = ''             # Set to empty string for localhost

# Host for sending e-mail.
EMAIL_HOST = 'localhost'

# List of locations of the template source files, in search order.
TEMPLATE_DIRS = ()

# Extension on all templates.
TEMPLATE_FILE_EXTENSION = '.html'

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
ADMIN_FOR = []

# Whether to check the flat-pages table as a last resort for all 404 errors.
USE_FLAT_PAGES = True

# 404s that may be ignored.
IGNORABLE_404_STARTS = ('/cgi-bin/', '/_vti_bin', '/_vti_inf')
IGNORABLE_404_ENDS = ('mail.pl', 'mailform.pl', 'mail.cgi', 'mailform.cgi', 'favicon.ico', '.php')

# A secret key for this particular Django installation. Used in secret-key
# hashing algorithms. Set this in your settings, or Django will complain
# loudly.
SECRET_KEY = ''

# Path to the "jing" executable -- needed to validate XMLFields
JING_PATH = "/usr/bin/jing"

##############
# MIDDLEWARE #
##############

# List of middleware classes to use.  Order is important; in the request phase,
# this middleware classes will be applied in the order given, and in the
# response phase the middleware will be applied in reverse order.
MIDDLEWARE_CLASSES = (
    "django.middleware.sessions.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.doc.XViewMiddleware",
)

############
# SESSIONS #
############

SESSION_COOKIE_NAME = 'hotclub'           # Cookie name. This can be whatever you want.
SESSION_COOKIE_AGE = 60 * 60 * 24 * 7 * 2 # Age of cookie, in seconds (default: 2 weeks).
SESSION_COOKIE_DOMAIN = None              # A string like ".lawrence.com", or None for standard domain cookie.

#########
# CACHE #
#########

# The cache backend to use.  See the docstring in django.core.cache for the
# possible values.
CACHE_BACKEND = 'simple://'

####################
# COMMENTS         #
####################

COMMENTS_ALLOW_PROFANITIES = False

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

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT.
# Example: "http://media.lawrence.com"
MEDIA_URL = ''
