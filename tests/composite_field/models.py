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


class Workspace(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="workspaces")
    name = models.CharField(max_length=100)


class Project(models.Model):
    workspace = models.ForeignKey(
        Workspace, on_delete=models.CASCADE, related_name="projects"
    )
    title = models.CharField(max_length=100)


class Task(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="tasks")
    name = models.CharField(max_length=100)


class BugReport(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="bug_reports")
    description = models.CharField(max_length=255)
    severity_level = models.IntegerField(default=1)
