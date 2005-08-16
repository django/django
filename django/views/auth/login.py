from django.parts.auth.formfields import AuthenticationForm
from django.core import formfields, template_loader
from django.core.extensions import DjangoContext as Context
from django.models.auth import sessions
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
            response = HttpResponseRedirect(redirect_to)
            sessions.start_web_session(manipulator.get_user_id(), request, response)
            return response
    else:
        errors = {}
    response = HttpResponse()
    # Set this cookie as a test to see whether the user accepts cookies
    response.set_cookie(sessions.TEST_COOKIE_NAME, sessions.TEST_COOKIE_VALUE)
    t = template_loader.get_template('registration/login')
    c = Context(request, {
        'form': formfields.FormWrapper(manipulator, request.POST, errors),
        REDIRECT_FIELD_NAME: redirect_to,
        'site_name': sites.get_current().name,
    })
    response.write(t.render(c))
    return response

def logout(request):
    "Logs out the user and displays 'You are logged out' message."
    if request.session:
        # Do a redirect to this page until the session has been cleared.
        response = HttpResponseRedirect(request.path)
        # Delete the cookie by setting a cookie with an empty value and max_age=0
        response.set_cookie(request.session.get_cookie()[0], '', max_age=0)
        request.session.delete()
        return response
    else:
        t = template_loader.get_template('registration/logged_out')
        c = Context(request)
        return HttpResponse(t.render(c))

def logout_then_login(request):
    "Logs out the user if he is logged in. Then redirects to the log-in page."
    response = HttpResponseRedirect('/accounts/login/')
    if request.session:
        # Delete the cookie by setting a cookie with an empty value and max_age=0
        response.set_cookie(request.session.get_cookie()[0], '', max_age=0)
        request.session.delete()
    return response

def redirect_to_login(next):
    "Redirects the user to the login page, passing the given 'next' page"
    return HttpResponseRedirect('/accounts/login/?%s=%s' % (REDIRECT_FIELD_NAME, next))
