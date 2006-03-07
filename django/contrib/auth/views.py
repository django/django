from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.forms import PasswordResetForm, PasswordChangeForm
from django import forms
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.contrib.auth.models import SESSION_KEY
from django.contrib.sites.models import Site
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import LOGIN_URL, REDIRECT_FIELD_NAME

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
        'form': forms.FormWrapper(manipulator, request.POST, errors),
        REDIRECT_FIELD_NAME: redirect_to,
        'site_name': Site.objects.get_current().name,
    }, context_instance=RequestContext(request))

def logout(request, next_page=None):
    "Logs out the user and displays 'You are logged out' message."
    try:
        del request.session[SESSION_KEY]
    except KeyError:
        return render_to_response('registration/logged_out', context_instance=RequestContext(request))
    else:
        # Redirect to this page until the session has been cleared.
        return HttpResponseRedirect(next_page or request.path)

def logout_then_login(request, login_url=LOGIN_URL):
    "Logs out the user if he is logged in. Then redirects to the log-in page."
    return logout(request, login_url)

def redirect_to_login(next, login_url=LOGIN_URL):
    "Redirects the user to the login page, passing the given 'next' page"
    return HttpResponseRedirect('%s?%s=%s' % (login_url, REDIRECT_FIELD_NAME, next))

def password_reset(request, is_admin_site=False):
    new_data, errors = {}, {}
    form = PasswordResetForm()
    if request.POST:
        new_data = request.POST.copy()
        errors = form.get_validation_errors(new_data)
        if not errors:
            if is_admin_site:
                form.save(request.META['HTTP_HOST'])
            else:
                form.save()
            return HttpResponseRedirect('%sdone/' % request.path)
    return render_to_response('registration/password_reset_form', {'form': forms.FormWrapper(form, new_data, errors)},
        context_instance=RequestContext(request))

def password_reset_done(request):
    return render_to_response('registration/password_reset_done', context_instance=RequestContext(request))

def password_change(request):
    new_data, errors = {}, {}
    form = PasswordChangeForm(request.user)
    if request.POST:
        new_data = request.POST.copy()
        errors = form.get_validation_errors(new_data)
        if not errors:
            form.save(new_data)
            return HttpResponseRedirect('%sdone/' % request.path)
    return render_to_response('registration/password_change_form', {'form': forms.FormWrapper(form, new_data, errors)},
        context_instance=RequestContext(request))
password_change = login_required(password_change)

def password_change_done(request):
    return render_to_response('registration/password_change_done', context_instance=RequestContext(request))
