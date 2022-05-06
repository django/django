from django.urls import path

from .views import (
    DeviceDeleteView,
    EmailSetupView,
    EmailVerificationView,
    MFACompleteView,
    MFAVerificationView,
    MFAView,
    TOTPSetupView,
)

app_name = "mfa"

urlpatterns = [
    path("", MFAView.as_view(), name="mfa"),
    path("complete/", MFACompleteView.as_view(), name="complete"),
    path("totp-setup/", TOTPSetupView.as_view(), name="totp-setup"),
    path("email-setup/", EmailSetupView.as_view(), name="email-setup"),
    path("verification/", MFAVerificationView.as_view(), name="verification"),
    path(
        "email-verification/",
        EmailVerificationView.as_view(),
        name="email-verification",
    ),
    path("<slug:slug>/delete/", DeviceDeleteView.as_view(), name="device-delete"),
]
