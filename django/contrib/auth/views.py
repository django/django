from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.forms import PasswordResetForm, PasswordChangeForm
from django import oldforms
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.contrib.sites.models import Site, RequestSite
from django.http import HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.utils.translation import ugettext as _

def login(request, template_name='registration/login.html', redirect_field_name=REDIRECT_FIELD_NAME):
    "Displays the login form and handles the login action."
    manipulator = AuthenticationForm(request)
    redirect_to = request.REQUEST.get(redirect_field_name, '')
    if request.POST:
        errors = manipulator.get_validation_errors(request.POST)
        if not errors:
            # Light security check -- make sure redirect_to isn't garbage.
            if not redirect_to or '//' in redirect_to or ' ' in redirect_to:
                from django.conf import settings
                redirect_to = settings.LOGIN_REDIRECT_URL
            from django.contrib.auth import login
            login(request, manipulator.get_user())
            request.session.delete_test_cookie()
            return HttpResponseRedirect(redirect_to)
    else:
        errors = {}
    request.session.set_test_cookie()

    if Site._meta.installed:
        current_site = Site.objects.get_current()
    else:
        current_site = RequestSite(request)

    return render_to_response(template_name, {
        'form': oldforms.FormWrapper(manipulator, request.POST, errors),
        redirect_field_name: redirect_to,
        'site_name': current_site.name,
    }, context_instance=RequestContext(request))

def logout(request, next_page=None, template_name='registration/logged_out.html'):
    "Logs out the user and displays 'You are logged out' message."
    from django.contrib.auth import logout
    logout(request)
    if next_page is None:
        return render_to_response(template_name, {'title': _('Logged out')}, context_instance=RequestContext(request))
    else:
        # Redirect to this page until the session has been cleared.
        return HttpResponseRedirect(next_page or request.path)

def logout_then_login(request, login_url=None):
    "Logs out the user if he is logged in. Then redirects to the log-in page."
    if not login_url:
        from django.conf import settings
        login_url = settings.LOGIN_URL
    return logout(request, login_url)

def redirect_to_login(next, login_url=None, redirect_field_name=REDIRECT_FIELD_NAME):
    "Redirects the user to the login page, passing the given 'next' page"
    if not login_url:
        from django.conf import settings
        login_url = settings.LOGIN_URL
    return HttpResponseRedirect('%s?%s=%s' % (login_url, redirect_field_name, next))

def password_reset(request, is_admin_site=False, template_name='registration/password_reset_form.html',
        email_template_name='registration/password_reset_email.html'):
    new_data, errors = {}, {}
    form = PasswordResetForm()
    if request.POST:
        new_data = request.POST.copy()
        errors = form.get_validation_errors(new_data)
        if not errors:
            if is_admin_site:
                form.save(domain_override=request.META['HTTP_HOST'])
            else:
                form.save(email_template_name=email_template_name)
            return HttpResponseRedirect('%sdone/' % request.path)
    return render_to_response(template_name, {'form': oldforms.FormWrapper(form, new_data, errors)},
        context_instance=RequestContext(request))

def password_reset_done(request, template_name='registration/password_reset_done.html'):
    return render_to_response(template_name, context_instance=RequestContext(request))

def password_change(request, template_name='registration/password_change_form.html'):
    new_data, errors = {}, {}
    form = PasswordChangeForm(request.user)
    if request.POST:
        new_data = request.POST.copy()
        errors = form.get_validation_errors(new_data)
        if not errors:
            form.save(new_data)
            return HttpResponseRedirect('%sdone/' % request.path)
    return render_to_response(template_name, {'form': oldforms.FormWrapper(form, new_data, errors)},
        context_instance=RequestContext(request))
password_change = login_required(password_change)

def password_change_done(request, template_name='registration/password_change_done.html'):
    return render_to_response(template_name, context_instance=RequestContext(request))
