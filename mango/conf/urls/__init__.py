from mango.urls import include
from mango.views import defaults

__all__ = ['handler400', 'handler403', 'handler404', 'handler500', 'include']

handler400 = defaults.bad_request
handler403 = defaults.permission_denied
handler404 = defaults.page_not_found
handler500 = defaults.server_error
