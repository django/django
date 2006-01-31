from mod_python import apache
import os

def authenhandler(req, **kwargs):
    """
    Authentication handler that checks against Django's auth database.
    """

    # mod_python fakes the environ, and thus doesn't process SetEnv.  This fixes
    # that so that the following import works
    os.environ.update(req.subprocess_env)

    from django.contrib.auth.models import User

    # check for PythonOptions
    _str_to_bool = lambda s: s.lower() in ('1', 'true', 'on', 'yes')

    options = req.get_options()
    permission_name = options.get('DjangoPermissionName', None)
    staff_only = _str_to_bool(options.get('DjangoRequireStaffStatus', "on"))
    superuser_only = _str_to_bool(options.get('DjangoRequireSuperuserStatus', "off"))

    # check that the username is valid
    kwargs = {'username': req.user, 'is_active': True}
    if staff_only:
        kwargs['is_staff'] = True
    if superuser_only:
        kwargs['is_superuser'] = True
    try:
        user = User.objects.get(**kwargs)
    except User.DoesNotExist:
        return apache.HTTP_UNAUTHORIZED

    # check the password and any permission given
    if user.check_password(req.get_basic_auth_pw()):
        if permission_name:
            if user.has_perm(permission_name):
                return apache.OK
            else:
                return apache.HTTP_UNAUTHORIZED
        else:
            return apache.OK
    else:
        return apache.HTTP_UNAUTHORIZED
