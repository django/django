from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm, PasswordChangeForm, AdminPasswordChangeForm
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import PermissionDenied
from django.shortcuts import render_to_response, get_object_or_404
from django.contrib.sites.models import Site, RequestSite
from django.http import HttpResponseRedirect, Http404
from django.template import RequestContext
from django.utils.http import urlquote, base36_to_int
from django.utils.html import escape
from django.utils.translation import ugettext as _
from django.contrib.auth.models import User
import re

def login(request, template_name='registration/login.html', redirect_field_name=REDIRECT_FIELD_NAME):
    "Displays the login form and handles the login action."
    redirect_to = request.REQUEST.get(redirect_field_name, '')
    if request.method == "POST":
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            # Light security check -- make sure redirect_to isn't garbage.
            if not redirect_to or '//' in redirect_to or ' ' in redirect_to:
                from django.conf import settings
                redirect_to = settings.LOGIN_REDIRECT_URL
            from django.contrib.auth import login
            login(request, form.get_user())
            if request.session.test_cookie_worked():
                request.session.delete_test_cookie()
            return HttpResponseRedirect(redirect_to)
    else:
        form = AuthenticationForm(request)
    request.session.set_test_cookie()
    if Site._meta.installed:
        current_site = Site.objects.get_current()
    else:
        current_site = RequestSite(request)
    return render_to_response(template_name, {
        'form': form,
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
    return HttpResponseRedirect('%s?%s=%s' % (login_url, urlquote(redirect_field_name), urlquote(next)))

# 4 views for password reset:
# - password_reset sends the mail
# - password_reset_done shows a success message for the above
# - password_reset_confirm checks the link the user clicked and 
#   prompts for a new password
# - password_reset_complete shows a success message for the above

def password_reset(request, is_admin_site=False, template_name='registration/password_reset_form.html',
        email_template_name='registration/password_reset_email.html',
        password_reset_form=PasswordResetForm, token_generator=default_token_generator):
    if request.method == "POST":
        form = password_reset_form(request.POST)
        if form.is_valid():
            opts = {}
            opts['use_https'] = request.is_secure()
            opts['token_generator'] = token_generator
            if is_admin_site:
                opts['domain_override'] = request.META['HTTP_HOST']
            else:
                opts['email_template_name'] = email_template_name
                if not Site._meta.installed:
                    opts['domain_override'] = RequestSite(request).domain
            form.save(**opts)
            return HttpResponseRedirect('%sdone/' % request.path)
    else:
        form = password_reset_form()
    return render_to_response(template_name, {
        'form': form,
    }, context_instance=RequestContext(request))

def password_reset_done(request, template_name='registration/password_reset_done.html'):
    return render_to_response(template_name, context_instance=RequestContext(request))

def password_reset_confirm(request, uidb36=None, token=None, template_name='registration/password_reset_confirm.html',
                           token_generator=default_token_generator, set_password_form=SetPasswordForm):
    """
    View that checks the hash in a password reset link and presents a
    form for entering a new password.
    """
    assert uidb36 is not None and token is not None # checked by URLconf
    try:
        uid_int = base36_to_int(uidb36)
    except ValueError:
        raise Http404

    user = get_object_or_404(User, id=uid_int)
    context_instance = RequestContext(request)

    if token_generator.check_token(user, token):
        context_instance['validlink'] = True
        if request.method == 'POST':
            form = set_password_form(user, request.POST)
            if form.is_valid():
                form.save()
                return HttpResponseRedirect("../done/")
        else:
            form = set_password_form(None)
    else:
        context_instance['validlink'] = False
        form = None
    context_instance['form'] = form    
    return render_to_response(template_name, context_instance=context_instance)

def password_reset_complete(request, template_name='registration/password_reset_complete.html'):
    return render_to_response(template_name, context_instance=RequestContext(request,
                                                                             {'login_url': settings.LOGIN_URL}))

def password_change(request, template_name='registration/password_change_form.html'):
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect('%sdone/' % request.path)
    else:
        form = PasswordChangeForm(request.user)
    return render_to_response(template_name, {
        'form': form,
    }, context_instance=RequestContext(request))
password_change = login_required(password_change)

def password_change_done(request, template_name='registration/password_change_done.html'):
    return render_to_response(template_name, context_instance=RequestContext(request))

# TODO: move to admin.py in the ModelAdmin
def user_change_password(request, id):
    if not request.user.has_perm('auth.change_user'):
        raise PermissionDenied
    user = get_object_or_404(User, pk=id)
    if request.method == 'POST':
        form = AdminPasswordChangeForm(user, request.POST)
        if form.is_valid():
            new_user = form.save()
            msg = _('Password changed successfully.')
            request.user.message_set.create(message=msg)
            return HttpResponseRedirect('..')
    else:
        form = AdminPasswordChangeForm(user)
    return render_to_response('admin/auth/user/change_password.html', {
        'title': _('Change password: %s') % escape(user.username),
        'form': form,
        'is_popup': '_popup' in request.REQUEST,
        'add': True,
        'change': False,
        'has_delete_permission': False,
        'has_change_permission': True,
        'has_absolute_url': False,
        'opts': User._meta,
        'original': user,
        'save_as': False,
        'show_save': True,
        'root_path': re.sub('auth/user/(\d+)/password/$', '', request.path),
    }, context_instance=RequestContext(request))
