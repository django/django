from django.db import models


class AbstractUser(models.Model):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=100)
    age = models.IntegerField(default=24)
    class Meta:
        abstract = True

class User(AbstractUser):
    pass


class Post(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="posts")
    title = models.CharField(max_length=100)
    body = models.CharField(blank=True)

    def __str__(self):
        return self.title