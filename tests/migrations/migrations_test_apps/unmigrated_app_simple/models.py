from django.db import models


class UnmigratedModel(models.Model):
    """
    A model that is in a migration-less app (which this app is
    if its migrations directory has not been repointed)
    """

    pass
