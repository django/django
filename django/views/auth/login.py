from django.parts.auth.formfields import AuthenticationForm
from django.core import formfields, template_loader
from django.core.extensions import DjangoContext, render_to_response
from django.models.auth import users
from django.models.core import sites
from django.utils.httpwrappers import HttpResponse, HttpResponseRedirect

REDIRECT_FIELD_NAME = 'next'

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
            request.session[users.SESSION_KEY] = manipulator.get_user_id()
            request.session.delete_test_cookie()
            return HttpResponseRedirect(redirect_to)
    else:
        errors = {}
    request.session.set_test_cookie()
    return render_to_response('registration/login', {
        'form': formfields.FormWrapper(manipulator, request.POST, errors),
        REDIRECT_FIELD_NAME: redirect_to,
        'site_name': sites.get_current().name,
    }, context_instance=DjangoContext(request))

def logout(request, next_page=None):
    "Logs out the user and displays 'You are logged out' message."
    try:
        del request.session[users.SESSION_KEY]
    except KeyError:
        return render_to_response('registration/logged_out', context_instance=DjangoContext(request))
    else:
        # Redirect to this page until the session has been cleared.
        return HttpResponseRedirect(next_page or request.path)

def logout_then_login(request):
    "Logs out the user if he is logged in. Then redirects to the log-in page."
    return logout(request, '/accounts/login/')

def redirect_to_login(next):
    "Redirects the user to the login page, passing the given 'next' page"
    return HttpResponseRedirect('/accounts/login/?%s=%s' % (REDIRECT_FIELD_NAME, next))
