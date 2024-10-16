from django.conf import settings
from django.contrib import admin, messages
from django.contrib.admin.options import IS_POPUP_VAR
from django.contrib.admin.utils import unquote
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import (
    AdminPasswordChangeForm,
    AdminUserCreationForm,
    UserChangeForm,
)
from django.contrib.auth.models import Group, User
from django.core.exceptions import PermissionDenied
from django.db import router, transaction
from django.http import Http404, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.decorators import method_decorator
from django.utils.html import escape
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters

csrf_protect_m = method_decorator(csrf_protect)
sensitive_post_parameters_m = method_decorator(sensitive_post_parameters())

@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    search_fields = ("name",)
    ordering = ("name",)
    filter_horizontal = ("permissions",)

    def formfield_for_manytomany(self, db_field, request=None, **kwargs):
        if db_field.name == "permissions":
            # Optimize the queryset to avoid performance issues
            kwargs["queryset"] = kwargs.get("queryset", db_field.remote_field.model.objects.select_related("content_type"))
        return super().formfield_for_manytomany(db_field, request=request, **kwargs)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    add_form_template = "admin/auth/user/add_form.html"
    change_user_password_template = None
    form = UserChangeForm
    add_form = AdminUserCreationForm
    change_password_form = AdminPasswordChangeForm
    list_display = ("username", "email", "first_name", "last_name", "is_staff")
    list_filter = ("is_staff", "is_superuser", "is_active", "groups")
    search_fields = ("username", "first_name", "last_name", "email")
    ordering = ("username",)
    filter_horizontal = ("groups", "user_permissions")

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (_("Personal info"), {"fields": ("first_name", "last_name", "email")}),
        (_("Permissions"), {
            "fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions"),
        }),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("username", "usable_password", "password1", "password2"),
        }),
    )

    def get_fieldsets(self, request, obj=None):
        # Return different fieldsets for the add form vs change form
        if not obj:
            return self.add_fieldsets
        return super().get_fieldsets(request, obj)

    def get_form(self, request, obj=None, **kwargs):
        # Use special form during user creation
        if obj is None:
            kwargs.setdefault('form', self.add_form)
        return super().get_form(request, obj, **kwargs)

    def get_urls(self):
        # Add custom URL for changing user password
        return [
            path("<id>/password/", self.admin_site.admin_view(self.user_change_password), name="auth_user_password_change"),
        ] + super().get_urls()

    def lookup_allowed(self, lookup, value, request=None):
        # Don't allow lookups involving passwords.
        return not lookup.startswith("password") and super().lookup_allowed(lookup, value, request)

    @sensitive_post_parameters_m
    @csrf_protect_m
    def add_view(self, request, form_url="", extra_context=None):
        # Only allow adding users if the user has both add and change permissions
        if request.method == "POST":
            with transaction.atomic(using=router.db_for_write(self.model)):
                return self._add_view(request, form_url, extra_context)
        return self._add_view(request, form_url, extra_context)

    def _add_view(self, request, form_url="", extra_context=None):
        if not self.has_change_permission(request):
            if self.has_add_permission(request) and settings.DEBUG:
                raise Http404("In order to add users, your account must have both the 'Add user' and 'Change user' permissions.")
            raise PermissionDenied

        extra_context = extra_context or {}
        username_field = self.opts.get_field(self.model.USERNAME_FIELD)
        extra_context.update({
            "auto_populated_fields": (),
            "username_help_text": username_field.help_text,
        })
        return super().add_view(request, form_url, extra_context)

    @sensitive_post_parameters_m
    def user_change_password(self, request, id, form_url=""):
        user = self.get_object(request, unquote(id))
        if not self.has_change_permission(request, user):
            raise PermissionDenied
        if not user:
            raise Http404(_("User with ID %(key)s does not exist.") % {"key": escape(id)})

        if request.method == "POST":
            form = self.change_password_form(user, request.POST)
            if form.is_valid():
                valid_submission = form.cleaned_data["set_usable_password"] or "unset-password" in request.POST
                if not valid_submission:
                    messages.error(request, _("Conflicting form data submitted. Please try again."))
                    return HttpResponseRedirect(request.get_full_path())

                user = form.save()
                change_message = self.construct_change_message(request, form, None)
                self.log_change(request, user, change_message)

                if user.has_usable_password():
                    messages.success(request, _("Password changed successfully."))
                else:
                    messages.success(request, _("Password-based authentication was disabled."))
                
                update_session_auth_hash(request, form.user)
                return HttpResponseRedirect(reverse("%s:%s_%s_change" % (self.admin_site.name, user._meta.app_label, user._meta.model_name), args=(user.pk,)))
        else:
            form = self.change_password_form(user)

        admin_form = admin.helpers.AdminForm(form, [(None, {"fields": list(form.base_fields)})], {})

        title = _("Change password: %s") if user.has_usable_password() else _("Set password: %s")
        context = {
            "title": title % escape(user.get_username()),
            "adminForm": admin_form,
            "form_url": form_url,
            "opts": self.opts,
            "original": user,
            **self.admin_site.each_context(request),
        }

        return TemplateResponse(request, self.change_user_password_template or "admin/auth/user/change_password.html", context)

    def response_add(self, request, obj, post_url_continue=None):
        # Customize the response after adding a user
        if "_addanother" not in request.POST and IS_POPUP_VAR not in request.POST:
            request.POST = request.POST.copy()
            request.POST["_continue"] = 1
        return super().response_add(request, obj, post_url_continue)
