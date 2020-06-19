# PermAppLabelWrapper, PermModelWrapper and PermLookupDict proxy the permissions system into objects that
# the template system can understand.


class PermLookupDict:
    def __init__(self, user, app_label, model):
        self.user, self.app_label, self.model = user, app_label, model

    def __repr__(self):
        return str(self.user.get_all_permissions())

    def __getitem__(self, perm_name):
        return self.user.has_perm("%s.%s.%s" % (self.app_label, self.model, perm_name))

    def __iter__(self):
        # To fix 'item in perms.someapp' and __getitem__ interaction we need to
        # define __iter__. See #18979 for details.
        raise TypeError("PermLookupDict is not iterable.")

    def __bool__(self):
        return self.user.has_model_perms('%s.%s' % (self.app_label, self.model))


class PermModelWrapper:
    def __init__(self, user, app_label):
        self.user, self.app_label = user, app_label

    def __getitem__(self, model):
        return PermLookupDict(self.user, self.app_label, model)

    def __iter__(self):
        raise TypeError("PermModelWrapper is not iterable.")

    def __contains__(self, perm_name):
        """
        Lookup by "somemodel" or "somemodel.someperm" in perms.
        """
        if '.' not in perm_name:
            # The name refers to model.
            return bool(self[perm_name])
        model, perm_name = perm_name.split('.', 1)
        return self[model][perm_name]

    def __bool__(self):
        return self.user.has_module_perms(self.app_label)


class PermAppLabelWrapper:
    def __init__(self, user):
        self.user = user

    def __getitem__(self, app_label):
        return PermModelWrapper(self.user, app_label)

    def __iter__(self):
        # I am large, I contain multitudes.
        raise TypeError("PermAppLabelWrapper is not iterable.")

    def __contains__(self, perm_name):
        """
        Lookup by "someapp", "someapp.somemodel" or "someapp.somemodel.someperm" in perms.
        """
        if '.' not in perm_name:
            # The name refers to module.
            return bool(self[perm_name])
        elif perm_name.count('.') == 1:
            app_label, model = perm_name.split('.')
            return self[app_label][model]
        app_label, model, perm_name = perm_name.split('.', 2)
        return self[app_label][model][perm_name]


def auth(request):
    """
    Return context variables required by apps that use Django's authentication
    system.

    If there is no 'user' attribute in the request, use AnonymousUser (from
    django.contrib.auth).
    """
    if hasattr(request, 'user'):
        user = request.user
    else:
        from django.contrib.auth.models import AnonymousUser
        user = AnonymousUser()

    return {
        'user': user,
        'perms': PermAppLabelWrapper(user),
    }
