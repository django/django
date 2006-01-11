from django.parts.auth.formfields import AuthenticationForm
from django.core import formfields
from django.core.extensions import DjangoContext, render_to_response
from django.contrib.auth.models import SESSION_KEY
from django.contrib.sites.models import Site
from django.http import HttpResponse, HttpResponseRedirect

REDIRECT_FIELD_NAME = 'next'
LOGIN_URL = '/accounts/login/'

def login(request):
    "Displays the login form and handles the login action."
    manipulator = AuthenticationForm(request)
    redirect_to = request.REQUEST.get(REDIRECT_FIELD_NAME, '')
    if request.POST:
        errors = manipulator.get_validation_errors(request.POST)
        if not errors:
            # Light security check -- make sure redirect_to isn't garbage.
            if not redirect_to or '://' in redirect_to or ' ' in redirect_to:
                redirect_to = '/accounts/profile/'
            request.session[SESSION_KEY] = manipulator.get_user_id()
            request.session.delete_test_cookie()
            return HttpResponseRedirect(redirect_to)
    else:
        errors = {}
    request.session.set_test_cookie()
    return render_to_response('registration/login', {
        'form': formfields.FormWrapper(manipulator, request.POST, errors),
        REDIRECT_FIELD_NAME: redirect_to,
        'site_name': Site.objects.get_current().name,
    }, context_instance=DjangoContext(request))

def logout(request, next_page=None):
    "Logs out the user and displays 'You are logged out' message."
    try:
        del request.session[SESSION_KEY]
    except KeyError:
        return render_to_response('registration/logged_out', context_instance=DjangoContext(request))
    else:
        # Redirect to this page until the session has been cleared.
        return HttpResponseRedirect(next_page or request.path)

def logout_then_login(request, login_url=LOGIN_URL):
    "Logs out the user if he is logged in. Then redirects to the log-in page."
    return logout(request, login_url)

def redirect_to_login(next, login_url=LOGIN_URL):
    "Redirects the user to the login page, passing the given 'next' page"
    return HttpResponseRedirect('%s?%s=%s' % (login_url, REDIRECT_FIELD_NAME, next))
