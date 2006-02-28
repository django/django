# TODO: this will be replaced by the muti-auth stuff
class UserSource:
    def get_user(self, request):
        from django.contrib.auth.models import User, SESSION_KEY
        try:
            user_id = request.session[SESSION_KEY]
            if not user_id:
                raise ValueError
            user = User.objects.get(pk=user_id)
        except (AttributeError, KeyError, ValueError, User.DoesNotExist):
            from django.parts.auth import anonymoususers
            user = anonymoususers.AnonymousUser()
        return user

class RequestUserMiddleware:
    def process_request(self, request):
        request._user_source = UserSource()
        return None
