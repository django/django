from django.urls import path

from .views import LazyRedirectView, empty_view, login_required_view

urlpatterns = [
    path('redirected_to/', empty_view, name='named-lazy-url-redirected-to'),
    path('login/', empty_view, name='some-login-page'),
    path('login_required_view/', login_required_view),
    path('redirect/', LazyRedirectView.as_view()),
]
