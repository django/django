from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME, get_user_model, login
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import MFA_USER_SESSION_ID, RedirectURLMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.views.generic import DeleteView
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView

from .forms import (
    EMAIL_KEY_NAME,
    DeviceDeleteForm,
    EmailSetupForm,
    EmailVerificationForm,
    MFAVerificationForm,
    TOTPSetupForm,
)
from .models import Device
from .signals import mfa_code_signal

UserModel = get_user_model()


class ViewMixin:
    def form_valid(self, form):
        form.save()
        return super().form_valid(form)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs


@method_decorator([never_cache, sensitive_post_parameters()], name="dispatch")
class TOTPSetupView(ViewMixin, LoginRequiredMixin, FormView):
    template_name = "mfa/totp_setup.html"
    form_class = TOTPSetupForm
    redirect_field_name = REDIRECT_FIELD_NAME
    success_url = reverse_lazy("mfa:complete")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["redirect_field_name"] = self.redirect_field_name
        context["redirect_url"] = reverse("mfa:email-setup")
        return context


@method_decorator([never_cache, sensitive_post_parameters()], name="dispatch")
class EmailSetupView(ViewMixin, LoginRequiredMixin, FormView):
    template_name = "mfa/email_setup.html"
    form_class = EmailSetupForm
    success_url = reverse_lazy("mfa:complete")
    redirect_field_name = REDIRECT_FIELD_NAME

    def get(self, request, *args, **kwargs):
        if request.session.get(EMAIL_KEY_NAME) is None:
            current_url = self.request.resolver_match.url_name
            return redirect(
                reverse("mfa:email-verification")
                + f"?{self.redirect_field_name}={current_url}"
            )
        form = self.form_class(**self.get_form_kwargs())
        return render(request, self.template_name, {"form": form})


class EmailVerificationView(RedirectURLMixin, ViewMixin, FormView):
    template_name = "mfa/email_verification.html"
    form_class = EmailVerificationForm
    next_page = reverse_lazy("mfa:email-verification")
    device_name = "device_name"

    def form_valid(self, form):
        email = form.cleaned_data.get("email")
        if form.same_email(email):
            if settings.RECEIVE_MFA_CODE is True:
                mfa_code_signal.send_robust(
                    sender=self.__class__, mfa_code=form._generate_totp()
                )
            else:
                form.send_email()
        return redirect(self.get_success_url())

    def get_redirect_url(self):
        redirect_urls = self.request.GET.getlist(self.redirect_field_name)
        verification_url = reverse("mfa:verification")
        if self.safe_urls(redirect_urls) and verification_url in redirect_urls:
            try:
                mfa_verification_url, next_url, *_ = redirect_urls
                redirect_to = (
                    mfa_verification_url
                    + f"?{self.redirect_field_name}={next_url}&{self.device_name}=email"
                )
                return redirect_to
            except ValueError:
                pass
        return super().get_redirect_url()

    def safe_urls(self, urls):
        for url in urls:
            if not url_has_allowed_host_and_scheme(
                url=url,
                allowed_hosts=self.get_success_url_allowed_hosts(),
                require_https=self.request.is_secure(),
            ):
                return False
        return True


class MFAView(LoginRequiredMixin, TemplateView):
    template_name = "mfa/mfa.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["devices"] = self.get_devices()
        return context

    def get_devices(self):
        return Device.objects.get_devices(self.request.user)


@method_decorator([sensitive_post_parameters(), never_cache], name="dispatch")
class MFAVerificationView(RedirectURLMixin, FormView):
    template_name = "mfa/mfa_verification.html"
    form_class = MFAVerificationForm
    device_name = "device_name"
    next_page = reverse_lazy("mfa:verification")

    def form_valid(self, form):
        login(self.request, self.get_user())
        if self.request.session.get(MFA_USER_SESSION_ID) is not None:
            del self.request.session[MFA_USER_SESSION_ID]
        return redirect(self.get_success_url())

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["device"] = self.get_device()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "device_name": self.get_device_name(),
                "verification_url": reverse("mfa:verification"),
                "next_url": self.get_success_url(),
                "redirect_field_name": self.redirect_field_name,
            }
        )
        return context

    def get_device(self):
        try:
            return Device.objects.get(user=self.get_user(), name=self.get_device_name())
        except Device.DoesNotExist:
            return None

    def get_device_name(self):
        device_name = self.request.GET.get(self.device_name, "").upper()
        allowed_names = ("TOTP", "EMAIL")
        return device_name if device_name in allowed_names else ""

    def get_user(self):
        if (user := self.request.user).is_authenticated:
            return user

        user_id = self.request.session.get(MFA_USER_SESSION_ID)
        try:
            return UserModel._default_manager.get(id=user_id)
        except UserModel.DoesNotExist:
            return None


class MFACompleteView(LoginRequiredMixin, TemplateView):
    template_name = "mfa/mfa_complete.html"


class DeviceDeleteView(
    LoginRequiredMixin, UserPassesTestMixin, SuccessMessageMixin, DeleteView
):
    model = Device
    context_object_name = "device"
    success_url = reverse_lazy("mfa:mfa")
    success_message = "Device deactivated."
    form_class = DeviceDeleteForm

    def test_func(self):
        device = self.get_object()
        return self.request.user == device.user
