"""A pytest plugin which helps testing Django applications

This plugin handles creating and destroying the test environment and
test database and provides some useful text fixtures.
"""

from __future__ import annotations

import contextlib
import inspect
import os
import pathlib
import sys
import types
from functools import reduce
from typing import TYPE_CHECKING, ContextManager, Generator, List, NoReturn

import pytest

from .django_compat import is_django_unittest
from .fixtures import (
    _django_db_helper,  # noqa: F401
    _live_server_helper,  # noqa: F401
    admin_client,  # noqa: F401
    admin_user,  # noqa: F401
    async_client,  # noqa: F401
    async_rf,  # noqa: F401
    client,  # noqa: F401
    db,  # noqa: F401
    django_assert_max_num_queries,  # noqa: F401
    django_assert_num_queries,  # noqa: F401
    django_capture_on_commit_callbacks,  # noqa: F401
    django_db_createdb,  # noqa: F401
    django_db_keepdb,  # noqa: F401
    django_db_modify_db_settings,  # noqa: F401
    django_db_modify_db_settings_parallel_suffix,  # noqa: F401
    django_db_modify_db_settings_tox_suffix,  # noqa: F401
    django_db_modify_db_settings_xdist_suffix,  # noqa: F401
    django_db_reset_sequences,  # noqa: F401
    django_db_serialized_rollback,  # noqa: F401
    django_db_setup,  # noqa: F401
    django_db_use_migrations,  # noqa: F401
    django_user_model,  # noqa: F401
    django_username_field,  # noqa: F401
    live_server,  # noqa: F401
    rf,  # noqa: F401
    settings,  # noqa: F401
    transactional_db,  # noqa: F401
    validate_django_db,
)
from .lazy_django import django_settings_is_configured, skip_if_no_django


if TYPE_CHECKING:
    import django


SETTINGS_MODULE_ENV = "DJANGO_SETTINGS_MODULE"
CONFIGURATION_ENV = "DJANGO_CONFIGURATION"
INVALID_TEMPLATE_VARS_ENV = "FAIL_INVALID_TEMPLATE_VARS"


# ############### pytest hooks ################


@pytest.hookimpl()
def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("django")
    group.addoption(
        "--reuse-db",
        action="store_true",
        dest="reuse_db",
        default=False,
        help="Re-use the testing database if it already exists, "
        "and do not remove it when the test finishes.",
    )
    group.addoption(
        "--create-db",
        action="store_true",
        dest="create_db",
        default=False,
        help="Re-create the database, even if it exists. This "
        "option can be used to override --reuse-db.",
    )
    group.addoption(
        "--ds",
        action="store",
        type=str,
        dest="ds",
        default=None,
        help="Set DJANGO_SETTINGS_MODULE.",
    )
    group.addoption(
        "--dc",
        action="store",
        type=str,
        dest="dc",
        default=None,
        help="Set DJANGO_CONFIGURATION.",
    )
    group.addoption(
        "--nomigrations",
        "--no-migrations",
        action="store_true",
        dest="nomigrations",
        default=False,
        help="Disable Django migrations on test setup",
    )
    group.addoption(
        "--migrations",
        action="store_false",
        dest="nomigrations",
        default=False,
        help="Enable Django migrations on test setup",
    )
    parser.addini(
        CONFIGURATION_ENV,
        "django-configurations class to use by pytest-django.",
    )
    group.addoption(
        "--liveserver",
        default=None,
        help="Address and port for the live_server fixture.",
    )
    parser.addini(
        SETTINGS_MODULE_ENV,
        "Django settings module to use by pytest-django.",
    )

    parser.addini(
        "django_find_project",
        "Automatically find and add a Django project to the Python path.",
        type="bool",
        default=True,
    )
    parser.addini(
        "django_debug_mode",
        "How to set the Django DEBUG setting (default `False`). Use `keep` to not override.",
        default="False",
    )
    group.addoption(
        "--fail-on-template-vars",
        action="store_true",
        dest="itv",
        default=False,
        help="Fail for invalid variables in templates.",
    )
    parser.addini(
        INVALID_TEMPLATE_VARS_ENV,
        "Fail for invalid variables in templates.",
        type="bool",
        default=False,
    )


PROJECT_FOUND = (
    "pytest-django found a Django project in %s "
    "(it contains manage.py) and added it to the Python path.\n"
    'If this is wrong, add "django_find_project = false" to '
    "pytest.ini and explicitly manage your Python path."
)

PROJECT_NOT_FOUND = (
    "pytest-django could not find a Django project "
    "(no manage.py file could be found). You must "
    "explicitly add your Django project to the Python path "
    "to have it picked up."
)

PROJECT_SCAN_DISABLED = (
    "pytest-django did not search for Django "
    "projects since it is disabled in the configuration "
    '("django_find_project = false")'
)


@contextlib.contextmanager
def _handle_import_error(extra_message: str) -> Generator[None, None, None]:
    try:
        yield
    except ImportError as e:
        django_msg = (e.args[0] + "\n\n") if e.args else ""
        msg = django_msg + extra_message
        raise ImportError(msg) from None


def _add_django_project_to_path(args) -> str:
    def is_django_project(path: pathlib.Path) -> bool:
        try:
            return path.is_dir() and (path / "manage.py").exists()
        except OSError:
            return False

    def arg_to_path(arg: str) -> pathlib.Path:
        # Test classes or functions can be appended to paths separated by ::
        arg = arg.split("::", 1)[0]
        return pathlib.Path(arg)

    def find_django_path(args) -> pathlib.Path | None:
        str_args = (str(arg) for arg in args)
        path_args = [arg_to_path(x) for x in str_args if not x.startswith("-")]

        cwd = pathlib.Path.cwd()
        if not path_args:
            path_args.append(cwd)
        elif cwd not in path_args:
            path_args.append(cwd)

        for arg in path_args:
            if is_django_project(arg):
                return arg
            for parent in arg.parents:
                if is_django_project(parent):
                    return parent
        return None

    project_dir = find_django_path(args)
    if project_dir:
        sys.path.insert(0, str(project_dir.absolute()))
        return PROJECT_FOUND % project_dir
    return PROJECT_NOT_FOUND


def _setup_django(config: pytest.Config) -> None:
    if "django" not in sys.modules:
        return

    import django.conf

    # Avoid force-loading Django when settings are not properly configured.
    if not django.conf.settings.configured:
        return

    import django.apps

    if not django.apps.apps.ready:
        django.setup()

    blocking_manager = config.stash[blocking_manager_key]
    blocking_manager.block()


def _get_boolean_value(
    x: None | (bool | str),
    name: str,
    default: bool | None = None,
) -> bool:
    if x is None:
        return bool(default)
    if isinstance(x, bool):
        return x
    possible_values = {"true": True, "false": False, "1": True, "0": False}
    try:
        return possible_values[x.lower()]
    except KeyError:
        possible = ", ".join(possible_values)
        raise ValueError(
            f"{x} is not a valid value for {name}. It must be one of {possible}."
        ) from None


report_header_key = pytest.StashKey[List[str]]()


@pytest.hookimpl()
def pytest_load_initial_conftests(
    early_config: pytest.Config,
    parser: pytest.Parser,
    args: list[str],
) -> None:
    # Register the marks
    early_config.addinivalue_line(
        "markers",
        "django_db(transaction=False, reset_sequences=False, databases=None, "
        "serialized_rollback=False): "
        "Mark the test as using the Django test database.  "
        "The *transaction* argument allows you to use real transactions "
        "in the test like Django's TransactionTestCase.  "
        "The *reset_sequences* argument resets database sequences before "
        "the test.  "
        "The *databases* argument sets which database aliases the test "
        "uses (by default, only 'default'). Use '__all__' for all databases.  "
        "The *serialized_rollback* argument enables rollback emulation for "
        "the test.",
    )
    early_config.addinivalue_line(
        "markers",
        "urls(modstr): Use a different URLconf for this test, similar to "
        "the `urls` attribute of Django's `TestCase` objects.  *modstr* is "
        "a string specifying the module of a URL config, e.g. "
        '"my_app.test_urls".',
    )
    early_config.addinivalue_line(
        "markers",
        "ignore_template_errors(): ignore errors from invalid template "
        "variables (if --fail-on-template-vars is used).",
    )

    options = parser.parse_known_args(args)

    if options.version or options.help:
        return

    django_find_project = _get_boolean_value(
        early_config.getini("django_find_project"), "django_find_project"
    )

    if django_find_project:
        _django_project_scan_outcome = _add_django_project_to_path(args)
    else:
        _django_project_scan_outcome = PROJECT_SCAN_DISABLED

    if (
        options.itv
        or _get_boolean_value(os.environ.get(INVALID_TEMPLATE_VARS_ENV), INVALID_TEMPLATE_VARS_ENV)
        or early_config.getini(INVALID_TEMPLATE_VARS_ENV)
    ):
        os.environ[INVALID_TEMPLATE_VARS_ENV] = "true"

    def _get_option_with_source(
        option: str | None,
        envname: str,
    ) -> tuple[str, str] | tuple[None, None]:
        if option:
            return option, "option"
        if envname in os.environ:
            return os.environ[envname], "env"
        cfgval = early_config.getini(envname)
        if cfgval:
            return cfgval, "ini"
        return None, None

    ds, ds_source = _get_option_with_source(options.ds, SETTINGS_MODULE_ENV)
    dc, dc_source = _get_option_with_source(options.dc, CONFIGURATION_ENV)

    report_header: list[str] = []
    early_config.stash[report_header_key] = report_header

    if ds:
        report_header.append(f"settings: {ds} (from {ds_source})")
        os.environ[SETTINGS_MODULE_ENV] = ds

        if dc:
            report_header.append(f"configuration: {dc} (from {dc_source})")
            os.environ[CONFIGURATION_ENV] = dc

            # Install the django-configurations importer
            import configurations.importer

            configurations.importer.install()

        # Forcefully load Django settings, throws ImportError or
        # ImproperlyConfigured if settings cannot be loaded.
        from django.conf import settings as dj_settings

        with _handle_import_error(_django_project_scan_outcome):
            dj_settings.DATABASES  # noqa: B018

    early_config.stash[blocking_manager_key] = DjangoDbBlocker(_ispytest=True)

    _setup_django(early_config)


@pytest.hookimpl(trylast=True)
def pytest_configure(config: pytest.Config) -> None:
    if config.getoption("version", 0) > 0 or config.getoption("help", False):
        return

    # Normally Django is set up in `pytest_load_initial_conftests`, but we also
    # allow users to not set DJANGO_SETTINGS_MODULE/`--ds` and instead
    # configure the Django settings in a `pytest_configure` hookimpl using e.g.
    # `settings.configure(...)`. In this case, the `_setup_django` call in
    # `pytest_load_initial_conftests` only partially initializes Django, and
    # it's fully initialized here.
    _setup_django(config)


@pytest.hookimpl()
def pytest_report_header(config: pytest.Config) -> list[str] | None:
    report_header = config.stash[report_header_key]

    if "django" in sys.modules:
        import django

        report_header.insert(0, f"version: {django.get_version()}")

    if report_header:
        return ["django: " + ", ".join(report_header)]
    return None


# Convert Django test tags on test classes to pytest marks.
# Unlike the Django test runner, we only check tags on Django
# test classes, to keep the plugin's effect contained.
def pytest_collectstart(collector: pytest.Collector) -> None:
    if "django" not in sys.modules:
        return

    if not isinstance(collector, pytest.Class):
        return

    tags = getattr(collector.obj, "tags", ())
    if not tags:
        return

    from django.test import SimpleTestCase

    if not issubclass(collector.obj, SimpleTestCase):
        return

    for tag in tags:
        collector.add_marker(tag)


# Convert Django test tags on test methods to pytest marks.
def pytest_itemcollected(item: pytest.Item) -> None:
    if "django" not in sys.modules:
        return

    if not isinstance(item, pytest.Function):
        return

    tags = getattr(item.obj, "tags", ())
    if not tags:
        return

    from django.test import SimpleTestCase

    if not issubclass(item.cls, SimpleTestCase):
        return

    for tag in tags:
        item.add_marker(tag)


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    # If Django is not configured we don't need to bother
    if not django_settings_is_configured():
        return

    from django.test import TestCase, TransactionTestCase

    def get_order_number(test: pytest.Item) -> int:
        test_cls = getattr(test, "cls", None)
        if test_cls and issubclass(test_cls, TransactionTestCase):
            # Note, TestCase is a subclass of TransactionTestCase.
            uses_db = True
            transactional = not issubclass(test_cls, TestCase)
        else:
            marker_db = test.get_closest_marker("django_db")
            if marker_db:
                (
                    transaction,
                    reset_sequences,
                    databases,
                    serialized_rollback,
                    available_apps,
                ) = validate_django_db(marker_db)
                uses_db = True
                transactional = transaction or reset_sequences
            else:
                uses_db = False
                transactional = False
            fixtures = getattr(test, "fixturenames", [])
            transactional = transactional or "transactional_db" in fixtures
            uses_db = uses_db or "db" in fixtures

        if transactional:
            return 1
        elif uses_db:
            return 0
        else:
            return 2

    items.sort(key=get_order_number)


def pytest_unconfigure(config: pytest.Config) -> None:
    # Undo the block() in _setup_django(), if it happenned.
    # It's also possible the user forgot to call restore().
    # We can warn about it, but let's just clean it up.
    if blocking_manager_key in config.stash:
        blocking_manager = config.stash[blocking_manager_key]
        while blocking_manager.is_active:
            blocking_manager.restore()


@pytest.fixture(autouse=True, scope="session")
def django_test_environment(request: pytest.FixtureRequest) -> Generator[None, None, None]:
    """Setup Django's test environment for the testing session.

    XXX It is a little dodgy that this is an autouse fixture.  Perhaps
        an email fixture should be requested in order to be able to
        use the Django email machinery just like you need to request a
        db fixture for access to the Django database, etc.  But
        without duplicating a lot more of Django's test support code
        we need to follow this model.
    """
    if django_settings_is_configured():
        from django.test.utils import setup_test_environment, teardown_test_environment

        debug_ini = request.config.getini("django_debug_mode")
        if debug_ini == "keep":
            debug = None
        else:
            debug = _get_boolean_value(debug_ini, "django_debug_mode", False)

        setup_test_environment(debug=debug)
        yield
        teardown_test_environment()

    else:
        yield


@pytest.fixture(scope="session")
def django_db_blocker(request: pytest.FixtureRequest) -> DjangoDbBlocker | None:
    """Block or unblock database access.

    This is an advanced feature for implementing database fixtures.

    By default, pytest-django blocks access the the database. In tests which
    request access to the database, the access is automatically unblocked.

    In a test or fixture context where database access is blocked, you can
    temporarily unblock access as follows::

        with django_db_blocker.unblock():
            ...

    In a test or fixture context where database access is not blocked, you can
    temporarily block access as follows::

        with django_db_blocker.block():
            ...

    This fixture is also used internally by pytest-django.
    """
    if not django_settings_is_configured():
        return None

    blocking_manager = request.config.stash[blocking_manager_key]
    return blocking_manager


@pytest.fixture(autouse=True)
def _django_db_marker(request: pytest.FixtureRequest) -> None:
    """Implement the django_db marker, internal to pytest-django."""
    marker = request.node.get_closest_marker("django_db")
    if marker:
        request.getfixturevalue("_django_db_helper")


@pytest.fixture(autouse=True, scope="class")
def _django_setup_unittest(
    request: pytest.FixtureRequest,
    django_db_blocker: DjangoDbBlocker,
) -> Generator[None, None, None]:
    """Setup a django unittest, internal to pytest-django."""
    if not django_settings_is_configured() or not is_django_unittest(request):
        yield
        return

    # Fix/patch pytest.
    # Before pytest 5.4: https://github.com/pytest-dev/pytest/issues/5991
    # After pytest 5.4: https://github.com/pytest-dev/pytest-django/issues/824
    from _pytest.unittest import TestCaseFunction

    original_runtest = TestCaseFunction.runtest

    def non_debugging_runtest(self) -> None:
        self._testcase(result=self)

    from django.test import SimpleTestCase

    assert issubclass(request.cls, SimpleTestCase)  # Guarded by 'is_django_unittest'
    try:
        TestCaseFunction.runtest = non_debugging_runtest  # type: ignore[method-assign]

        # Don't set up the DB if the unittest does not require DB.
        # The `databases` propery seems like the best indicator for that.
        if request.cls.databases:
            request.getfixturevalue("django_db_setup")
            db_unblock = django_db_blocker.unblock()
        else:
            db_unblock = contextlib.nullcontext()

        with db_unblock:
            yield
    finally:
        TestCaseFunction.runtest = original_runtest  # type: ignore[method-assign]


@pytest.fixture(autouse=True)
def _dj_autoclear_mailbox() -> None:
    if not django_settings_is_configured():
        return

    from django.core import mail

    del mail.outbox[:]


@pytest.fixture()
def mailoutbox(
    django_mail_patch_dns: None,
    _dj_autoclear_mailbox: None,
) -> list[django.core.mail.EmailMessage] | None:
    """A clean email outbox to which Django-generated emails are sent."""
    if not django_settings_is_configured():
        return None

    from django.core import mail

    return mail.outbox  # type: ignore[no-any-return]


@pytest.fixture()
def django_mail_patch_dns(
    monkeypatch: pytest.MonkeyPatch,
    django_mail_dnsname: str,
) -> None:
    """Patch the server dns name used in email messages."""
    from django.core import mail

    monkeypatch.setattr(mail.message, "DNS_NAME", django_mail_dnsname)


@pytest.fixture()
def django_mail_dnsname() -> str:
    """Return server dns name for using in email messages."""
    return "fake-tests.example.com"


@pytest.fixture(autouse=True)
def _django_set_urlconf(request: pytest.FixtureRequest) -> Generator[None, None, None]:
    """Apply the @pytest.mark.urls marker, internal to pytest-django."""
    marker: pytest.Mark | None = request.node.get_closest_marker("urls")
    if marker:
        skip_if_no_django()
        import django.conf
        from django.urls import clear_url_caches, set_urlconf

        urls = validate_urls(marker)
        original_urlconf = django.conf.settings.ROOT_URLCONF
        django.conf.settings.ROOT_URLCONF = urls
        clear_url_caches()
        set_urlconf(None)

    yield

    if marker:
        django.conf.settings.ROOT_URLCONF = original_urlconf
        # Copy the pattern from
        # https://github.com/django/django/blob/main/django/test/signals.py#L152
        clear_url_caches()
        set_urlconf(None)


@pytest.fixture(autouse=True, scope="session")
def _fail_for_invalid_template_variable() -> Generator[None, None, None]:
    """Fixture that fails for invalid variables in templates.

    This fixture will fail each test that uses django template rendering
    should a template contain an invalid template variable.
    The fail message will include the name of the invalid variable and
    in most cases the template name.

    It does not raise an exception, but fails, as the stack trace doesn't
    offer any helpful information to debug.
    This behavior can be switched off using the marker:
    ``pytest.mark.ignore_template_errors``
    """

    class InvalidVarException:
        """Custom handler for invalid strings in templates."""

        def __init__(self, *, origin_value: str) -> None:
            self.fail = True
            self.origin_value = origin_value

        def __contains__(self, key: str) -> bool:
            return key == "%s"

        @staticmethod
        def _get_origin() -> str | None:
            stack = inspect.stack()

            # Try to use topmost `self.origin` first (Django 1.9+, and with
            # TEMPLATE_DEBUG)..
            for frame_info in stack[2:]:
                if frame_info.function == "render":
                    origin: str | None
                    try:
                        origin = frame_info.frame.f_locals["self"].origin
                    except (AttributeError, KeyError):
                        origin = None
                    if origin is not None:
                        return origin

            from django.template import Template

            # finding the ``render`` needle in the stack
            frameinfo = reduce(
                lambda x, y: y if y.function == "render" and "base.py" in y.filename else x, stack
            )
            # ``django.template.base.Template``
            template = frameinfo.frame.f_locals["self"]
            if isinstance(template, Template):
                name: str = template.name
                return name
            return None

        def __mod__(self, var: str) -> str:
            origin = self._get_origin()
            if origin:
                msg = f"Undefined template variable '{var}' in '{origin}'"
            else:
                msg = f"Undefined template variable '{var}'"
            if self.fail:
                pytest.fail(msg)
            else:
                return self.origin_value

    with pytest.MonkeyPatch.context() as mp:
        if (
            os.environ.get(INVALID_TEMPLATE_VARS_ENV, "false") == "true"
            and django_settings_is_configured()
        ):
            from django.conf import settings as dj_settings

            if dj_settings.TEMPLATES:
                mp.setitem(
                    dj_settings.TEMPLATES[0]["OPTIONS"],
                    "string_if_invalid",
                    InvalidVarException(
                        origin_value=dj_settings.TEMPLATES[0]["OPTIONS"].get(
                            "string_if_invalid", ""
                        )
                    ),
                )
        yield


@pytest.fixture(autouse=True)
def _template_string_if_invalid_marker(
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
) -> None:
    """Apply the @pytest.mark.ignore_template_errors marker,
    internal to pytest-django."""
    marker = request.keywords.get("ignore_template_errors", None)
    if os.environ.get(INVALID_TEMPLATE_VARS_ENV, "false") == "true":
        if marker and django_settings_is_configured():
            from django.conf import settings as dj_settings

            if dj_settings.TEMPLATES:
                monkeypatch.setattr(
                    dj_settings.TEMPLATES[0]["OPTIONS"]["string_if_invalid"],
                    "fail",
                    False,
                )


@pytest.fixture(autouse=True)
def _django_clear_site_cache() -> None:
    """Clears ``django.contrib.sites.models.SITE_CACHE`` to avoid
    unexpected behavior with cached site objects.
    """

    if django_settings_is_configured():
        from django.conf import settings as dj_settings

        if "django.contrib.sites" in dj_settings.INSTALLED_APPS:
            from django.contrib.sites.models import Site

            Site.objects.clear_cache()


# ############### Helper Functions ################


class _DatabaseBlockerContextManager:
    def __init__(self, db_blocker: DjangoDbBlocker) -> None:
        self._db_blocker = db_blocker

    def __enter__(self) -> None:
        pass

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: types.TracebackType | None,
    ) -> None:
        self._db_blocker.restore()


class DjangoDbBlocker:
    """Manager for django.db.backends.base.base.BaseDatabaseWrapper.

    This is the object returned by django_db_blocker.
    """

    def __init__(self, *, _ispytest: bool = False) -> None:
        if not _ispytest:  # pragma: no cover
            raise TypeError(
                "The DjangoDbBlocker constructor is private. "
                "use the django_db_blocker fixture instead."
            )

        self._history = []  # type: ignore[var-annotated]
        self._real_ensure_connection = None

    @property
    def _dj_db_wrapper(self) -> django.db.backends.base.base.BaseDatabaseWrapper:
        from django.db.backends.base.base import BaseDatabaseWrapper

        # The first time the _dj_db_wrapper is accessed, save a reference to the
        # real implementation.
        if self._real_ensure_connection is None:
            self._real_ensure_connection = BaseDatabaseWrapper.ensure_connection

        return BaseDatabaseWrapper

    def _save_active_wrapper(self) -> None:
        self._history.append(self._dj_db_wrapper.ensure_connection)

    def _blocking_wrapper(*args, **kwargs) -> NoReturn:
        __tracebackhide__ = True
        raise RuntimeError(
            "Database access not allowed, "
            'use the "django_db" mark, or the '
            '"db" or "transactional_db" fixtures to enable it.'
        )

    def unblock(self) -> ContextManager[None]:
        """Enable access to the Django database."""
        self._save_active_wrapper()
        self._dj_db_wrapper.ensure_connection = self._real_ensure_connection
        return _DatabaseBlockerContextManager(self)

    def block(self) -> ContextManager[None]:
        """Disable access to the Django database."""
        self._save_active_wrapper()
        self._dj_db_wrapper.ensure_connection = self._blocking_wrapper
        return _DatabaseBlockerContextManager(self)

    def restore(self) -> None:
        """Undo a previous call to block() or unblock().

        Consider using block() and unblock() as context managers instead of
        manually calling restore().
        """
        self._dj_db_wrapper.ensure_connection = self._history.pop()

    @property
    def is_active(self) -> bool:
        """Whether a block() or unblock() is currently active."""
        return bool(self._history)


# On Config.stash.
blocking_manager_key = pytest.StashKey[DjangoDbBlocker]()


def validate_urls(marker: pytest.Mark) -> list[str]:
    """Validate the urls marker.

    It checks the signature and creates the `urls` attribute on the
    marker which will have the correct value.
    """

    def apifun(urls: list[str]) -> list[str]:
        return urls

    return apifun(*marker.args, **marker.kwargs)
