from django.db import models
from django.contrib.comments.models import Comment


# Regression for #13368. This is an example of a model
# that imports a class that has an abstract base class.
class CommentScore(models.Model):
    comment = models.OneToOneField(Comment, primary_key=True)
