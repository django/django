from types import SimpleNamespace

from .models import (
    BugReport,
    Comment,
    Organization,
    Post,
    Project,
    Task,
    User,
    Workspace,
)


def create_composite_test_data():
    acme = Organization.objects.create(name="Acme", slug="acme")
    acme_duplicate = Organization.objects.create(name="Acme", slug="acme-india")
    beta = Organization.objects.create(name="Beta", slug="beta")

    ada = User.objects.create(
        name="Ada",
        email="ada@example.com",
        age=34,
        organization=acme,
    )
    bob = User.objects.create(
        name="Bob",
        email="bob@example.com",
        age=28,
        organization=acme,
        manager=ada,
    )
    bob_duplicate = User.objects.create(
        name="Bob",
        email="bob.duplicate@example.com",
        age=28,
        organization=acme_duplicate,
        manager=ada,
    )
    cy = User.objects.create(
        name="Cy",
        email="cy@example.com",
        age=41,
        organization=beta,
    )
    no_org = User.objects.create(
        name="No Org",
        email="no-org@example.com",
        age=20,
    )

    core = Workspace.objects.create(organization=acme, owner=ada, name="Core")
    core_duplicate = Workspace.objects.create(
        organization=acme_duplicate, owner=bob_duplicate, name="Core"
    )
    labs = Workspace.objects.create(organization=beta, owner=cy, name="Labs")

    auth = Project.objects.create(
        workspace=core, owner=ada, title="Authentication", code="AUTH"
    )
    auth_duplicate = Project.objects.create(
        workspace=core_duplicate,
        owner=bob_duplicate,
        title="Authentication",
        code="AUTH-IN",
    )
    reports = Project.objects.create(
        workspace=labs, owner=cy, title="Reports", code="RPT"
    )

    login = Task.objects.create(
        project=auth, assignee=bob, name="Login flow", status="open"
    )
    login_duplicate = Task.objects.create(
        project=auth_duplicate,
        assignee=bob_duplicate,
        name="Login flow",
        status="open",
    )
    export = Task.objects.create(
        project=reports, assignee=None, name="Export CSV", status="blocked"
    )

    crash = BugReport.objects.create(
        task=login,
        reporter=cy,
        description="Login crash",
        severity_level=3,
    )
    crash_duplicate = BugReport.objects.create(
        task=login_duplicate,
        reporter=bob,
        description="Login crash",
        severity_level=3,
    )
    missing_export = BugReport.objects.create(
        task=export,
        reporter=None,
        description="Export missing rows",
        severity_level=2,
    )

    welcome = Post.objects.create(user=ada, title="Welcome", body="Hello")
    welcome_duplicate = Post.objects.create(user=bob, title="Welcome", body="Hello")
    empty_post = Post.objects.create(user=no_org, title="Empty", body="")

    Comment.objects.create(post=welcome, user=bob, text="Nice")
    Comment.objects.create(post=welcome, user=cy, text="Nice")
    Comment.objects.create(post=empty_post, user=None, text="Anonymous")

    return SimpleNamespace(
        organizations=SimpleNamespace(
            acme=acme,
            acme_duplicate=acme_duplicate,
            beta=beta,
        ),
        users=SimpleNamespace(
            ada=ada,
            bob=bob,
            bob_duplicate=bob_duplicate,
            cy=cy,
            no_org=no_org,
        ),
        workspaces=SimpleNamespace(
            core=core,
            core_duplicate=core_duplicate,
            labs=labs,
        ),
        projects=SimpleNamespace(
            auth=auth,
            auth_duplicate=auth_duplicate,
            reports=reports,
        ),
        tasks=SimpleNamespace(
            login=login,
            login_duplicate=login_duplicate,
            export=export,
        ),
        bug_reports=SimpleNamespace(
            crash=crash,
            crash_duplicate=crash_duplicate,
            missing_export=missing_export,
        ),
        posts=SimpleNamespace(
            welcome=welcome,
            welcome_duplicate=welcome_duplicate,
            empty=empty_post,
        ),
    )
