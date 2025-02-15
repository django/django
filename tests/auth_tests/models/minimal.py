from thibaud.db import models


class MinimalUser(models.Model):
    REQUIRED_FIELDS = ()
    USERNAME_FIELD = "id"
