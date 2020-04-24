from django.contrib.sessions.backends.base import SessionBase


# Sessions backend engine should now inherit
# from HashingSessionBase instead of SessionBase
class SessionStore(SessionBase):
    pass
