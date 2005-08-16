from django.parts.auth.formfields import AuthenticationForm
from django.core import formfields, template_loader
from django.core.extensions import DjangoContext as Context
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
            return HttpResponseRedirect(redirect_to)
    else:
        errors = {}
    response = HttpResponse()
    request.session.set_test_cookie()
    t = template_loader.get_template('registration/login')
    c = Context(request, {
        'form': formfields.FormWrapper(manipulator, request.POST, errors),
        REDIRECT_FIELD_NAME: redirect_to,
        'site_name': sites.get_current().name,
    })
    response.write(t.render(c))
    return response

def logout(request, next_page=None):
    "Logs out the user and displays 'You are logged out' message."
    try:
        del request.session[users.SESSION_KEY]
    except KeyError:
        t = template_loader.get_template('registration/logged_out')
        c = Context(request)
        return HttpResponse(t.render(c))
    else:
        # Do a redirect to this page until the session has been cleared.
        return HttpResponseRedirect(next_page or request.path)

def logout_then_login(request):
    "Logs out the user if he is logged in. Then redirects to the log-in page."
    return logout(request, '/accounts/login/')

def redirect_to_login(next):
    "Redirects the user to the login page, passing the given 'next' page"
    return HttpResponseRedirect('/accounts/login/?%s=%s' % (REDIRECT_FIELD_NAME, next))
