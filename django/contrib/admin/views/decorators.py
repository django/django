from django import http, template
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.shortcuts import render_to_response
from django.utils.translation import gettext_lazy, gettext as _
import base64, datetime, md5
import cPickle as pickle

ERROR_MESSAGE = gettext_lazy("Please enter a correct username and password. Note that both fields are case-sensitive.")
LOGIN_FORM_KEY = 'this_is_the_login_form'

def _display_login_form(request, error_message=''):
    request.session.set_test_cookie()
    if request.POST and request.POST.has_key('post_data'):
        # User has failed login BUT has previously saved post data.
        post_data = request.POST['post_data']
    elif request.POST:
        # User's session must have expired; save their post data.
        post_data = _encode_post_data(request.POST)
    else:
        post_data = _encode_post_data({})
    return render_to_response('admin/login.html', {
        'title': _('Log in'),
        'app_path': request.path,
        'post_data': post_data,
        'error_message': error_message
    }, context_instance=template.RequestContext(request))

def _encode_post_data(post_data):
    pickled = pickle.dumps(post_data)
    pickled_md5 = md5.new(pickled + settings.SECRET_KEY).hexdigest()
    return base64.encodestring(pickled + pickled_md5)

def _decode_post_data(encoded_data):
    encoded_data = base64.decodestring(encoded_data)
    pickled, tamper_check = encoded_data[:-32], encoded_data[-32:]
    if md5.new(pickled + settings.SECRET_KEY).hexdigest() != tamper_check:
        from django.core.exceptions import SuspiciousOperation
        raise SuspiciousOperation, "User may have tampered with session cookie."
    return pickle.loads(pickled)

def staff_member_required(view_func):
    """
    Decorator for views that checks that the user is logged in and is a staff
    member, displaying the login page if necessary.
    """
    def _checklogin(request, *args, **kwargs):
        if request.user.is_authenticated() and request.user.is_staff:
            # The user is valid. Continue to the admin page.
            if request.POST.has_key('post_data'):
                # User must have re-authenticated through a different window
                # or tab.
                request.POST = _decode_post_data(request.POST['post_data'])
            return view_func(request, *args, **kwargs)

        assert hasattr(request, 'session'), "The Django admin requires session middleware to be installed. Edit your MIDDLEWARE_CLASSES setting to insert 'django.contrib.sessions.middleware.SessionMiddleware'."

        # If this isn't already the login page, display it.
        if not request.POST.has_key(LOGIN_FORM_KEY):
            if request.POST:
                message = _("Please log in again, because your session has expired. Don't worry: Your submission has been saved.")
            else:
                message = ""
            return _display_login_form(request, message)

        # Check that the user accepts cookies.
        if not request.session.test_cookie_worked():
            message = _("Looks like your browser isn't configured to accept cookies. Please enable cookies, reload this page, and try again.")
            return _display_login_form(request, message)

        # Check the password.
        username = request.POST.get('username', None)
        password = request.POST.get('password', None)
        user = authenticate(username=username, password=password)
        if user is None:
            message = ERROR_MESSAGE
            if '@' in username:
                # Mistakenly entered e-mail address instead of username? Look it up.
                try:
                    user = User.objects.get(email=username)
                except User.DoesNotExist:
                    message = _("Usernames cannot contain the '@' character.")
                else:
                    message = _("Your e-mail address is not your username. Try '%s' instead.") % user.username
            return _display_login_form(request, message)

        # The user data is correct; log in the user in and continue.
        else:
            if user.is_active and user.is_staff:
                login(request, user)
                # TODO: set last_login with an event.
                user.last_login = datetime.datetime.now()
                user.save()
                if request.POST.has_key('post_data'):
                    post_data = _decode_post_data(request.POST['post_data'])
                    if post_data and not post_data.has_key(LOGIN_FORM_KEY):
                        # overwrite request.POST with the saved post_data, and continue
                        request.POST = post_data
                        request.user = user
                        return view_func(request, *args, **kwargs)
                    else:
                        request.session.delete_test_cookie()
                        return http.HttpResponseRedirect(request.path)
            else:
                return _display_login_form(request, ERROR_MESSAGE)

    return _checklogin
