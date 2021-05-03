from django.urls import include, path

from .views import empty_view, terminal_view


more_urls = [
    path('terminal21/', empty_view, name="terminal-21"),
    path('terminal22/', empty_view, name="terminal-22"),
]

extra_urls = [
    path('', terminal_view, name="terminal"),
    path('terminal1/', empty_view, name="terminal-1"),
    path('terminal2/', include(more_urls, terminal_prefix=True, terminal_callback="terminal")),
]


urlpatterns = [
    path('regular_path/', empty_view),
    path('terminal/', include(extra_urls, terminal_prefix=True)),
    path('', empty_view, name="empty"),
]
