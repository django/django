import base64
import cPickle as pickle
import re

from django import http, template
from django.contrib.admin import ModelAdmin
from django.contrib.auth import authenticate, login
from django.db.models.base import ModelBase
from django.core.exceptions import ImproperlyConfigured
from django.shortcuts import render_to_response
from django.utils.safestring import mark_safe
from django.utils.text import capfirst
from django.utils.translation import ugettext_lazy, ugettext as _
from django.views.decorators.cache import never_cache
from django.conf import settings
from django.utils.hashcompat import md5_constructor

ERROR_MESSAGE = ugettext_lazy("Please enter a correct username and password. Note that both fields are case-sensitive.")
LOGIN_FORM_KEY = 'this_is_the_login_form'

class AlreadyRegistered(Exception):
    pass

class NotRegistered(Exception):
    pass

def _encode_post_data(post_data):
    pickled = pickle.dumps(post_data)
    pickled_md5 = md5_constructor(pickled + settings.SECRET_KEY).hexdigest()
    return base64.encodestring(pickled + pickled_md5)

def _decode_post_data(encoded_data):
    encoded_data = base64.decodestring(encoded_data)
    pickled, tamper_check = encoded_data[:-32], encoded_data[-32:]
    if md5_constructor(pickled + settings.SECRET_KEY).hexdigest() != tamper_check:
        from django.core.exceptions import SuspiciousOperation
        raise SuspiciousOperation, "User may have tampered with session cookie."
    return pickle.loads(pickled)

class AdminSite(object):
    """
    An AdminSite object encapsulates an instance of the Django admin application, ready
    to be hooked in to your URLConf. Models are registered with the AdminSite using the
    register() method, and the root() method can then be used as a Django view function
    that presents a full admin interface for the collection of registered models.
    """

    index_template = None
    login_template = None

    def __init__(self):
        self._registry = {} # model_class class -> admin_class instance

    def register(self, model_or_iterable, admin_class=None, **options):
        """
        Registers the given model(s) with the given admin class.

        The model(s) should be Model classes, not instances.

        If an admin class isn't given, it will use ModelAdmin (the default
        admin options). If keyword arguments are given -- e.g., list_display --
        they'll be applied as options to the admin class.

        If a model is already registered, this will raise AlreadyRegistered.
        """
        # Don't import the humongous validation code unless required
        if admin_class and settings.DEBUG:
            from django.contrib.admin.validation import validate
        else:
            validate = lambda model, adminclass: None

        if not admin_class:
            admin_class = ModelAdmin
        if isinstance(model_or_iterable, ModelBase):
            model_or_iterable = [model_or_iterable]
        for model in model_or_iterable:
            if model in self._registry:
                raise AlreadyRegistered('The model %s is already registered' % model.__name__)

            # If we got **options then dynamically construct a subclass of
            # admin_class with those **options.
            if options:
                # For reasons I don't quite understand, without a __module__
                # the created class appears to "live" in the wrong place,
                # which causes issues later on.
                options['__module__'] = __name__
                admin_class = type("%sAdmin" % model.__name__, (admin_class,), options)

            # Validate (which might be a no-op)
            validate(admin_class, model)

            # Instantiate the admin class to save in the registry
            self._registry[model] = admin_class(model, self)

    def unregister(self, model_or_iterable):
        """
        Unregisters the given model(s).

        If a model isn't already registered, this will raise NotRegistered.
        """
        if isinstance(model_or_iterable, ModelBase):
            model_or_iterable = [model_or_iterable]
        for model in model_or_iterable:
            if model not in self._registry:
                raise NotRegistered('The model %s is not registered' % model.__name__)
            del self._registry[model]

    def has_permission(self, request):
        """
        Returns True if the given HttpRequest has permission to view
        *at least one* page in the admin site.
        """
        return request.user.is_authenticated() and request.user.is_staff
    
    def check_dependencies(self):
        """
        Check that all things needed to run the admin have been correctly installed.

        The default implementation checks that LogEntry, ContentType and the
        auth context processor are installed.
        """
        from django.conf import settings
        from django.contrib.admin.models import LogEntry
        from django.contrib.contenttypes.models import ContentType

        if not LogEntry._meta.installed:
            raise ImproperlyConfigured("Put 'django.contrib.admin' in your INSTALLED_APPS setting in order to use the admin application.")
        if not ContentType._meta.installed:
            raise ImproperlyConfigured("Put 'django.contrib.contenttypes' in your INSTALLED_APPS setting in order to use the admin application.")
        if 'django.core.context_processors.auth' not in settings.TEMPLATE_CONTEXT_PROCESSORS:
            raise ImproperlyConfigured("Put 'django.core.context_processors.auth' in your TEMPLATE_CONTEXT_PROCESSORS setting in order to use the admin application.")

    def root(self, request, url):
        """
        Handles main URL routing for the admin app.

        `url` is the remainder of the URL -- e.g. 'comments/comment/'.
        """
        if request.method == 'GET' and not request.path.endswith('/'):
            return http.HttpResponseRedirect(request.path + '/')
        
        if settings.DEBUG:
            self.check_dependencies()

        # Figure out the admin base URL path and stash it for later use
        self.root_path = re.sub(re.escape(url) + '$', '', request.path)

        url = url.rstrip('/') # Trim trailing slash, if it exists.

        # The 'logout' view doesn't require that the person is logged in.
        if url == 'logout':
            return self.logout(request)

        # Check permission to continue or display login form.
        if not self.has_permission(request):
            return self.login(request)

        if url == '':
            return self.index(request)
        elif url == 'password_change':
            return self.password_change(request)
        elif url == 'password_change/done':
            return self.password_change_done(request)
        elif url == 'jsi18n':
            return self.i18n_javascript(request)
        # urls starting with 'r/' are for the "show in web" links
        elif url.startswith('r/'):
            from django.views.defaults import shortcut
            return shortcut(request, *url.split('/')[1:])
        else:
            if '/' in url:
                return self.model_page(request, *url.split('/', 2))
            else:
                return self.app_index(request, url)

        raise http.Http404('The requested admin page does not exist.')

    def model_page(self, request, app_label, model_name, rest_of_url=None):
        """
        Handles the model-specific functionality of the admin site, delegating
        to the appropriate ModelAdmin class.
        """
        from django.db import models
        model = models.get_model(app_label, model_name)
        if model is None:
            raise http.Http404("App %r, model %r, not found." % (app_label, model_name))
        try:
            admin_obj = self._registry[model]
        except KeyError:
            raise http.Http404("This model exists but has not been registered with the admin site.")
        return admin_obj(request, rest_of_url)
    model_page = never_cache(model_page)

    def password_change(self, request):
        """
        Handles the "change password" task -- both form display and validation.
        """
        from django.contrib.auth.views import password_change
        return password_change(request,
            post_save_redirect='%spassword_change/done/' % self.root_path)

    def password_change_done(self, request):
        """
        Displays the "success" page after a password change.
        """
        from django.contrib.auth.views import password_change_done
        return password_change_done(request)

    def i18n_javascript(self, request):
        """
        Displays the i18n JavaScript that the Django admin requires.

        This takes into account the USE_I18N setting. If it's set to False, the
        generated JavaScript will be leaner and faster.
        """
        if settings.USE_I18N:
            from django.views.i18n import javascript_catalog
        else:
            from django.views.i18n import null_javascript_catalog as javascript_catalog
        return javascript_catalog(request, packages='django.conf')

    def logout(self, request):
        """
        Logs out the user for the given HttpRequest.

        This should *not* assume the user is already logged in.
        """
        from django.contrib.auth.views import logout
        return logout(request)
    logout = never_cache(logout)

    def login(self, request):
        """
        Displays the login form for the given HttpRequest.
        """
        from django.contrib.auth.models import User

        # If this isn't already the login page, display it.
        if not request.POST.has_key(LOGIN_FORM_KEY):
            if request.POST:
                message = _("Please log in again, because your session has expired. Don't worry: Your submission has been saved.")
            else:
                message = ""
            return self.display_login_form(request, message)

        # Check that the user accepts cookies.
        if not request.session.test_cookie_worked():
            message = _("Looks like your browser isn't configured to accept cookies. Please enable cookies, reload this page, and try again.")
            return self.display_login_form(request, message)

        # Check the password.
        username = request.POST.get('username', None)
        password = request.POST.get('password', None)
        user = authenticate(username=username, password=password)
        if user is None:
            message = ERROR_MESSAGE
            if u'@' in username:
                # Mistakenly entered e-mail address instead of username? Look it up.
                try:
                    user = User.objects.get(email=username)
                except (User.DoesNotExist, User.MultipleObjectsReturned):
                    message = _("Usernames cannot contain the '@' character.")
                else:
                    if user.check_password(password):
                        message = _("Your e-mail address is not your username."
                                    " Try '%s' instead.") % user.username
                    else:
                        message = _("Usernames cannot contain the '@' character.")
            return self.display_login_form(request, message)

        # The user data is correct; log in the user in and continue.
        else:
            if user.is_active and user.is_staff:
                login(request, user)
                if request.POST.has_key('post_data'):
                    post_data = _decode_post_data(request.POST['post_data'])
                    if post_data and not post_data.has_key(LOGIN_FORM_KEY):
                        # overwrite request.POST with the saved post_data, and continue
                        request.POST = post_data
                        request.user = user
                        return self.root(request, request.path.split(self.root_path)[-1])
                    else:
                        request.session.delete_test_cookie()
                        return http.HttpResponseRedirect(request.get_full_path())
            else:
                return self.display_login_form(request, ERROR_MESSAGE)
    login = never_cache(login)

    def index(self, request, extra_context=None):
        """
        Displays the main admin index page, which lists all of the installed
        apps that have been registered in this site.
        """
        app_dict = {}
        user = request.user
        for model, model_admin in self._registry.items():
            app_label = model._meta.app_label
            has_module_perms = user.has_module_perms(app_label)

            if has_module_perms:
                perms = {
                    'add': model_admin.has_add_permission(request),
                    'change': model_admin.has_change_permission(request),
                    'delete': model_admin.has_delete_permission(request),
                }

                # Check whether user has any perm for this module.
                # If so, add the module to the model_list.
                if True in perms.values():
                    model_dict = {
                        'name': capfirst(model._meta.verbose_name_plural),
                        'admin_url': mark_safe('%s/%s/' % (app_label, model.__name__.lower())),
                        'perms': perms,
                    }
                    if app_label in app_dict:
                        app_dict[app_label]['models'].append(model_dict)
                    else:
                        app_dict[app_label] = {
                            'name': app_label.title(),
                            'app_url': app_label,
                            'has_module_perms': has_module_perms,
                            'models': [model_dict],
                        }

        # Sort the apps alphabetically.
        app_list = app_dict.values()
        app_list.sort(lambda x, y: cmp(x['name'], y['name']))

        # Sort the models alphabetically within each app.
        for app in app_list:
            app['models'].sort(lambda x, y: cmp(x['name'], y['name']))

        context = {
            'title': _('Site administration'),
            'app_list': app_list,
            'root_path': self.root_path,
        }
        context.update(extra_context or {})
        return render_to_response(self.index_template or 'admin/index.html', context,
            context_instance=template.RequestContext(request)
        )
    index = never_cache(index)

    def display_login_form(self, request, error_message='', extra_context=None):
        request.session.set_test_cookie()
        if request.POST and request.POST.has_key('post_data'):
            # User has failed login BUT has previously saved post data.
            post_data = request.POST['post_data']
        elif request.POST:
            # User's session must have expired; save their post data.
            post_data = _encode_post_data(request.POST)
        else:
            post_data = _encode_post_data({})

        context = {
            'title': _('Log in'),
            'app_path': request.get_full_path(),
            'post_data': post_data,
            'error_message': error_message,
            'root_path': self.root_path,
        }
        context.update(extra_context or {})
        return render_to_response(self.login_template or 'admin/login.html', context,
            context_instance=template.RequestContext(request)
        )
        
    def app_index(self, request, app_label):
        user = request.user
        has_module_perms = user.has_module_perms(app_label)
        app_dict = {}
        for model, model_admin in self._registry.items():
            if app_label == model._meta.app_label:
                if has_module_perms:
                    perms = {
                        'add': user.has_perm("%s.%s" % (app_label, model._meta.get_add_permission())),
                        'change': user.has_perm("%s.%s" % (app_label, model._meta.get_change_permission())),
                        'delete': user.has_perm("%s.%s" % (app_label, model._meta.get_delete_permission())),
                    }
                    # Check whether user has any perm for this module.
                    # If so, add the module to the model_list.
                    if True in perms.values():
                        model_dict = {
                            'name': capfirst(model._meta.verbose_name_plural),
                            'admin_url': '%s/' % model.__name__.lower(),
                            'perms': perms,
                        }
                    if app_dict:
                        app_dict['models'].append(model_dict),
                    else:
                        app_dict = {
                            'name': app_label.title(),
                            'app_url': '',
                            'has_module_perms': has_module_perms,
                            'models': [model_dict],
                        }
                    if not app_dict:
                        raise http.Http404('The requested admin page does not exist.')
        # Sort the models alphabetically within each app.
        app_dict['models'].sort(lambda x, y: cmp(x['name'], y['name']))
        return render_to_response('admin/app_index.html', {
            'title': _('%s administration' % capfirst(app_label)),
            'app_list': [app_dict]
        }, context_instance=template.RequestContext(request))

# This global object represents the default admin site, for the common case.
# You can instantiate AdminSite in your own code to create a custom admin site.
site = AdminSite()
