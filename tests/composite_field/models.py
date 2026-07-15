from django.db import models


class Organization(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField()

    def __str__(self):
        return self.name


class User(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    age = models.IntegerField(default=24)
    organization = models.ForeignKey(
        Organization,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="users",
    )
    manager = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reports",
    )

    def __str__(self):
        return self.name


class Workspace(models.Model):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="workspaces"
    )
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="workspaces")
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Project(models.Model):
    workspace = models.ForeignKey(
        Workspace, on_delete=models.CASCADE, related_name="projects"
    )
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="projects")
    title = models.CharField(max_length=100)
    code = models.CharField(max_length=20)

    def __str__(self):
        return self.title


class Task(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="tasks")
    assignee = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tasks",
    )
    name = models.CharField(max_length=100)
    status = models.CharField(max_length=20, default="open")

    def __str__(self):
        return self.name


class BugReport(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="bug_reports")
    reporter = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="bug_reports",
    )
    description = models.CharField(max_length=255)
    severity_level = models.IntegerField(default=1)


class Post(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="posts")
    title = models.CharField(max_length=100)
    body = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.title


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="comments",
    )
    text = models.CharField(max_length=255)
