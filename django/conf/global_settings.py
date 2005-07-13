# Default Django settings. Override these with settings in the module
# pointed-to by the DJANGO_SETTINGS_MODULE environment variable.

import re

####################
# CORE             #
####################

DEBUG = False

# Whether to use the "Etag" header. This saves bandwidth but slows down performance.
USE_ETAGS = False

# people who get code error notifications
ADMINS = (('Adrian Holovaty','aholovaty@ljworld.com'), ('Jacob Kaplan-Moss', 'jacob@lawrence.com'))

# These IP addresses:
#   * See debug comments, when DEBUG is true
#   * Receive x-headers
INTERNAL_IPS = (
    '24.124.4.220',  # World Online offices
    '24.124.1.4',    # https://admin.6newslawrence.com/
    '24.148.30.138', # Adrian home
    '127.0.0.1',     # localhost
)

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

# which e-mail address error messages come from
SERVER_EMAIL = None

# Whether to send broken-link e-mails
SEND_BROKEN_LINK_EMAILS = True

# postgres database connection info
DATABASE_ENGINE = 'postgresql'
DATABASE_NAME = 'cms'
DATABASE_USER = 'apache'
DATABASE_PASSWORD = ''
DATABASE_HOST = '' # set to empty string for localhost

# host for sending e-mail
EMAIL_HOST = 'localhost'

# name of the session cookie
AUTH_SESSION_COOKIE = 'rizzo'

# name of the authorization profile module (below django.apps)
AUTH_PROFILE_MODULE = ''

# list of locations of the template source files, in search order
TEMPLATE_DIRS = []

# default e-mail address to use for various automated correspondence from the site managers
DEFAULT_FROM_EMAIL = 'webmaster@ljworld.com'

# whether to append trailing slashes to URLs
APPEND_SLASH = True

# whether to prepend the "www." subdomain to URLs
PREPEND_WWW = False

# list of regular expressions representing User-Agent strings that are not
# allowed to visit any page, CMS-wide. Use this for bad robots/crawlers.
DISALLOWED_USER_AGENTS = (
    re.compile(r'^NaverBot.*'),
    re.compile(r'^EmailSiphon.*'),
    re.compile(r'^SiteSucker.*'),
    re.compile(r'^sohu-search')
)

ABSOLUTE_URL_OVERRIDES = {}

# list of allowed prefixes for the {% ssi %} tag
ALLOWED_INCLUDE_ROOTS = ('/home/html',)

# if this is a admin settings module, this should be a list of
# settings modules for which this admin is an admin for
ADMIN_FOR = []

# 404s that may be ignored
IGNORABLE_404_STARTS = ('/cgi-bin/', '/_vti_bin', '/_vti_inf')
IGNORABLE_404_ENDS = ('mail.pl', 'mailform.pl', 'mail.cgi', 'mailform.cgi', 'favicon.ico', '.php')

##############
# Middleware #
##############

# List of middleware classes to use.  Order is important; in the request phase,
# this middleware classes will be applied in the order given, and in the
# response phase the middleware will be applied in reverse order.
MIDDLEWARE_CLASSES = (
    "django.middleware.common.CommonMiddleware",
    "django.middleware.doc.XViewMiddleware",
)

#########
# CACHE #
#########

# The cache backend to use.  See the docstring in django.core.cache for the
# values this can be set to.
CACHE_BACKEND = 'simple://'

####################
# REGISTRATION     #
####################

# E-mail addresses at these domains cannot sign up for accounts
BANNED_EMAIL_DOMAINS = [
    'mailinator.com', 'dodgeit.com', 'spamgourmet.com', 'mytrashmail.com'
]
REGISTRATION_COOKIE_DOMAIN = None # set to a string like ".lawrence.com", or None for standard domain cookie

# If this is set to True, users will be required to fill out their profile
# (defined by AUTH_PROFILE_MODULE) before they will be allowed to create
# an account.
REGISTRATION_REQUIRES_PROFILE = False

####################
# COMMENTS         #
####################

COMMENTS_ALLOW_PROFANITIES = False

# The group ID that designates which users are banned.
# Set to None if you're not using it.
COMMENTS_BANNED_USERS_GROUP = 19

# The group ID that designates which users can moderate comments.
# Set to None if you're not using it.
COMMENTS_MODERATORS_GROUP = 20

# The group ID that designates the users whose comments should be e-mailed to MANAGERS.
# Set to None if you're not using it.
COMMENTS_SKETCHY_USERS_GROUP = 22

# The system will e-mail MANAGERS the first COMMENTS_FIRST_FEW comments by each
# user. Set this to 0 if you want to disable it.
COMMENTS_FIRST_FEW = 10

BANNED_IPS = (
    # Dupont Stainmaster / GuessWho / a variety of other names (back when we had free comments)
    '204.94.104.99', '66.142.59.23', '220.196.165.142',
    # (Unknown)
    '64.65.191.117',
#     # Jimmy_Olsen / Clark_Kent / Bruce_Wayne
#     # Unbanned on 2005-06-17, because other people want to register from this address.
#     '12.106.111.10',
    # hoof_hearted / hugh_Jass / Ferd_Burfel / fanny_farkel
    '24.124.72.20', '170.135.241.46',
    # Zac_McGraw
    '198.74.20.74', '198.74.20.75',
)

####################
# BLOGS            #
####################

# E-mail addresses to notify when a new blog entry is posted live
BLOGS_EMAILS_TO_NOTIFY = []

####################
# PLACES           #
####################

# A list of IDs -- *as integers, not strings* -- that are considered the "main"
# cities served by this installation. Probably just one.
MAIN_CITY_IDS = (1,) # Lawrence

# A list of IDs -- *as integers, not strings* -- that are considered "local" by
# this installation.
LOCAL_CITY_IDS = (1, 3) # Lawrence and Kansas City, MO

####################
# THUMBNAILS       #
####################

THUMB_ALLOWED_WIDTHS = (90, 120, 180, 240, 450)

####################
# VARIOUS ROOTS    #
####################

# This is the new media root and URL! Use it, and only it!
MEDIA_ROOT = '/home/media/media.lawrence.com/'
MEDIA_URL = 'http://media.lawrence.com'
