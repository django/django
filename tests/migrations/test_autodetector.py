import functools
import re
from unittest import mock

from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser
from django.core.validators import RegexValidator, validate_slug
from django.db import connection, migrations, models
from django.db.migrations.autodetector import MigrationAutodetector
from django.db.migrations.graph import MigrationGraph
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.questioner import MigrationQuestioner
from django.db.migrations.state import ModelState, ProjectState
from django.test import SimpleTestCase, TestCase, ignore_warnings, override_settings
from django.test.utils import isolate_lru_cache
from django.utils.deprecation import RemovedInDjango51Warning

from .models import FoodManager, FoodQuerySet


class DeconstructibleObject:
    """
    A custom deconstructible object.
    """

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def deconstruct(self):
        return (self.__module__ + "." + self.__class__.__name__, self.args, self.kwargs)


class BaseAutodetectorTests(TestCase):
    def repr_changes(self, changes, include_dependencies=False):
        output = ""
        for app_label, migrations_ in sorted(changes.items()):
            output += "  %s:\n" % app_label
            for migration in migrations_:
                output += "    %s\n" % migration.name
                for operation in migration.operations:
                    output += "      %s\n" % operation
                if include_dependencies:
                    output += "      Dependencies:\n"
                    if migration.dependencies:
                        for dep in migration.dependencies:
                            output += "        %s\n" % (dep,)
                    else:
                        output += "        None\n"
        return output

    def assertNumberMigrations(self, changes, app_label, number):
        if len(changes.get(app_label, [])) != number:
            self.fail(
                "Incorrect number of migrations (%s) for %s (expected %s)\n%s"
                % (
                    len(changes.get(app_label, [])),
                    app_label,
                    number,
                    self.repr_changes(changes),
                )
            )

    def assertMigrationDependencies(self, changes, app_label, position, dependencies):
        if not changes.get(app_label):
            self.fail(
                "No migrations found for %s\n%s"
                % (app_label, self.repr_changes(changes))
            )
        if len(changes[app_label]) < position + 1:
            self.fail(
                "No migration at index %s for %s\n%s"
                % (position, app_label, self.repr_changes(changes))
            )
        migration = changes[app_label][position]
        if set(migration.dependencies) != set(dependencies):
            self.fail(
                "Migration dependencies mismatch for %s.%s (expected %s):\n%s"
                % (
                    app_label,
                    migration.name,
                    dependencies,
                    self.repr_changes(changes, include_dependencies=True),
                )
            )

    def assertOperationTypes(self, changes, app_label, position, types):
        if not changes.get(app_label):
            self.fail(
                "No migrations found for %s\n%s"
                % (app_label, self.repr_changes(changes))
            )
        if len(changes[app_label]) < position + 1:
            self.fail(
                "No migration at index %s for %s\n%s"
                % (position, app_label, self.repr_changes(changes))
            )
        migration = changes[app_label][position]
        real_types = [
            operation.__class__.__name__ for operation in migration.operations
        ]
        if types != real_types:
            self.fail(
                "Operation type mismatch for %s.%s (expected %s):\n%s"
                % (
                    app_label,
                    migration.name,
                    types,
                    self.repr_changes(changes),
                )
            )

    def assertOperationAttributes(
        self, changes, app_label, position, operation_position, **attrs
    ):
        if not changes.get(app_label):
            self.fail(
                "No migrations found for %s\n%s"
                % (app_label, self.repr_changes(changes))
            )
        if len(changes[app_label]) < position + 1:
            self.fail(
                "No migration at index %s for %s\n%s"
                % (position, app_label, self.repr_changes(changes))
            )
        migration = changes[app_label][position]
        if len(changes[app_label]) < position + 1:
            self.fail(
                "No operation at index %s for %s.%s\n%s"
                % (
                    operation_position,
                    app_label,
                    migration.name,
                    self.repr_changes(changes),
                )
            )
        operation = migration.operations[operation_position]
        for attr, value in attrs.items():
            if getattr(operation, attr, None) != value:
                self.fail(
                    "Attribute mismatch for %s.%s op #%s, %s (expected %r, got %r):\n%s"
                    % (
                        app_label,
                        migration.name,
                        operation_position,
                        attr,
                        value,
                        getattr(operation, attr, None),
                        self.repr_changes(changes),
                    )
                )

    def assertOperationFieldAttributes(
        self, changes, app_label, position, operation_position, **attrs
    ):
        if not changes.get(app_label):
            self.fail(
                "No migrations found for %s\n%s"
                % (app_label, self.repr_changes(changes))
            )
        if len(changes[app_label]) < position + 1:
            self.fail(
                "No migration at index %s for %s\n%s"
                % (position, app_label, self.repr_changes(changes))
            )
        migration = changes[app_label][position]
        if len(changes[app_label]) < position + 1:
            self.fail(
                "No operation at index %s for %s.%s\n%s"
                % (
                    operation_position,
                    app_label,
                    migration.name,
                    self.repr_changes(changes),
                )
            )
        operation = migration.operations[operation_position]
        if not hasattr(operation, "field"):
            self.fail(
                "No field attribute for %s.%s op #%s."
                % (
                    app_label,
                    migration.name,
                    operation_position,
                )
            )
        field = operation.field
        for attr, value in attrs.items():
            if getattr(field, attr, None) != value:
                self.fail(
                    "Field attribute mismatch for %s.%s op #%s, field.%s (expected %r, "
                    "got %r):\n%s"
                    % (
                        app_label,
                        migration.name,
                        operation_position,
                        attr,
                        value,
                        getattr(field, attr, None),
                        self.repr_changes(changes),
                    )
                )

    def make_project_state(self, model_states):
        "Shortcut to make ProjectStates from lists of predefined models"
        project_state = ProjectState()
        for model_state in model_states:
            project_state.add_model(model_state.clone())
        return project_state

    def get_changes(self, before_states, after_states, questioner=None):
        if not isinstance(before_states, ProjectState):
            before_states = self.make_project_state(before_states)
        if not isinstance(after_states, ProjectState):
            after_states = self.make_project_state(after_states)
        return MigrationAutodetector(
            before_states,
            after_states,
            questioner,
        )._detect_changes()


class AutodetectorTests(BaseAutodetectorTests):
    """
    Tests the migration autodetector.
    """

    author_empty = ModelState(
        "testapp", "Author", [("id", models.AutoField(primary_key=True))]
    )
    author_name = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
            ("name", models.CharField(max_length=200)),
        ],
    )
    author_name_null = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
            ("name", models.CharField(max_length=200, null=True)),
        ],
    )
    author_name_longer = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
            ("name", models.CharField(max_length=400)),
        ],
    )
    author_name_renamed = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
            ("names", models.CharField(max_length=200)),
        ],
    )
    author_name_default = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
            ("name", models.CharField(max_length=200, default="Ada Lovelace")),
        ],
    )
    author_name_check_constraint = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
            ("name", models.CharField(max_length=200)),
        ],
        {
            "constraints": [
                models.CheckConstraint(
                    check=models.Q(name__contains="Bob"), name="name_contains_bob"
                )
            ]
        },
    )
    author_dates_of_birth_auto_now = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
            ("date_of_birth", models.DateField(auto_now=True)),
            ("date_time_of_birth", models.DateTimeField(auto_now=True)),
            ("time_of_birth", models.TimeField(auto_now=True)),
        ],
    )
    author_dates_of_birth_auto_now_add = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
            ("date_of_birth", models.DateField(auto_now_add=True)),
            ("date_time_of_birth", models.DateTimeField(auto_now_add=True)),
            ("time_of_birth", models.TimeField(auto_now_add=True)),
        ],
    )
    author_name_deconstructible_1 = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
            ("name", models.CharField(max_length=200, default=DeconstructibleObject())),
        ],
    )
    author_name_deconstructible_2 = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
            ("name", models.CharField(max_length=200, default=DeconstructibleObject())),
        ],
    )
    author_name_deconstructible_3 = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
            ("name", models.CharField(max_length=200, default=models.IntegerField())),
        ],
    )
    author_name_deconstructible_4 = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
            ("name", models.CharField(max_length=200, default=models.IntegerField())),
        ],
    )
    author_name_deconstructible_list_1 = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
            (
                "name",
                models.CharField(
                    max_length=200, default=[DeconstructibleObject(), 123]
                ),
            ),
        ],
    )
    author_name_deconstructible_list_2 = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
            (
                "name",
                models.CharField(
                    max_length=200, default=[DeconstructibleObject(), 123]
                ),
            ),
        ],
    )
    author_name_deconstructible_list_3 = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
            (
                "name",
                models.CharField(
                    max_length=200, default=[DeconstructibleObject(), 999]
                ),
            ),
        ],
    )
    author_name_deconstructible_tuple_1 = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
            (
                "name",
                models.CharField(
                    max_length=200, default=(DeconstructibleObject(), 123)
                ),
            ),
        ],
    )
    author_name_deconstructible_tuple_2 = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
            (
                "name",
                models.CharField(
                    max_length=200, default=(DeconstructibleObject(), 123)
                ),
            ),
        ],
    )
    author_name_deconstructible_tuple_3 = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
            (
                "name",
                models.CharField(
                    max_length=200, default=(DeconstructibleObject(), 999)
                ),
            ),
        ],
    )
    author_name_deconstructible_dict_1 = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
            (
                "name",
                models.CharField(
                    max_length=200,
                    default={"item": DeconstructibleObject(), "otheritem": 123},
                ),
            ),
        ],
    )
    author_name_deconstructible_dict_2 = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
            (
                "name",
                models.CharField(
                    max_length=200,
                    default={"item": DeconstructibleObject(), "otheritem": 123},
                ),
            ),
        ],
    )
    author_name_deconstructible_dict_3 = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
            (
                "name",
                models.CharField(
                    max_length=200,
                    default={"item": DeconstructibleObject(), "otheritem": 999},
                ),
            ),
        ],
    )
    author_name_nested_deconstructible_1 = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
            (
                "name",
                models.CharField(
                    max_length=200,
                    default=DeconstructibleObject(
                        DeconstructibleObject(1),
                        (
                            DeconstructibleObject("t1"),
                            DeconstructibleObject("t2"),
                        ),
                        a=DeconstructibleObject("A"),
                        b=DeconstructibleObject(B=DeconstructibleObject("c")),
                    ),
                ),
            ),
        ],
    )
    author_name_nested_deconstructible_2 = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
            (
                "name",
                models.CharField(
                    max_length=200,
                    default=DeconstructibleObject(
                        DeconstructibleObject(1),
                        (
                            DeconstructibleObject("t1"),
                            DeconstructibleObject("t2"),
                        ),
                        a=DeconstructibleObject("A"),
                        b=DeconstructibleObject(B=DeconstructibleObject("c")),
                    ),
                ),
            ),
        ],
    )
    author_name_nested_deconstructible_changed_arg = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
            (
                "name",
                models.CharField(
                    max_length=200,
                    default=DeconstructibleObject(
                        DeconstructibleObject(1),
                        (
                            DeconstructibleObject("t1"),
                            DeconstructibleObject("t2-changed"),
                        ),
                        a=DeconstructibleObject("A"),
                        b=DeconstructibleObject(B=DeconstructibleObject("c")),
                    ),
                ),
            ),
        ],
    )
    author_name_nested_deconstructible_extra_arg = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
            (
                "name",
                models.CharField(
                    max_length=200,
                    default=DeconstructibleObject(
                        DeconstructibleObject(1),
                        (
                            DeconstructibleObject("t1"),
                            DeconstructibleObject("t2"),
                        ),
                        None,
                        a=DeconstructibleObject("A"),
                        b=DeconstructibleObject(B=DeconstructibleObject("c")),
                    ),
                ),
            ),
        ],
    )
    author_name_nested_deconstructible_changed_kwarg = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
            (
                "name",
                models.CharField(
                    max_length=200,
                    default=DeconstructibleObject(
                        DeconstructibleObject(1),
                        (
                            DeconstructibleObject("t1"),
                            DeconstructibleObject("t2"),
                        ),
                        a=DeconstructibleObject("A"),
                        b=DeconstructibleObject(B=DeconstructibleObject("c-changed")),
                    ),
                ),
            ),
        ],
    )
    author_name_nested_deconstructible_extra_kwarg = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
            (
                "name",
                models.CharField(
                    max_length=200,
                    default=DeconstructibleObject(
                        DeconstructibleObject(1),
                        (
                            DeconstructibleObject("t1"),
                            DeconstructibleObject("t2"),
                        ),
                        a=DeconstructibleObject("A"),
                        b=DeconstructibleObject(B=DeconstructibleObject("c")),
                        c=None,
                    ),
                ),
            ),
        ],
    )
    author_custom_pk = ModelState(
        "testapp", "Author", [("pk_field", models.IntegerField(primary_key=True))]
    )
    author_with_biography_non_blank = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
            ("name", models.CharField()),
            ("biography", models.TextField()),
        ],
    )
    author_with_biography_blank = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
            ("name", models.CharField(blank=True)),
            ("biography", models.TextField(blank=True)),
        ],
    )
    author_with_book = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
            ("name", models.CharField(max_length=200)),
            ("book", models.ForeignKey("otherapp.Book", models.CASCADE)),
        ],
    )
    author_with_book_order_wrt = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
            ("name", models.CharField(max_length=200)),
            ("book", models.ForeignKey("otherapp.Book", models.CASCADE)),
        ],
        options={"order_with_respect_to": "book"},
    )
    author_renamed_with_book = ModelState(
        "testapp",
        "Writer",
        [
            ("id", models.AutoField(primary_key=True)),
            ("name", models.CharField(max_length=200)),
            ("book", models.ForeignKey("otherapp.Book", models.CASCADE)),
        ],
    )
    author_with_publisher_string = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
            ("name", models.CharField(max_length=200)),
            ("publisher_name", models.CharField(max_length=200)),
        ],
    )
    author_with_publisher = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
            ("name", models.CharField(max_length=200)),
            ("publisher", models.ForeignKey("testapp.Publisher", models.CASCADE)),
        ],
    )
    author_with_user = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
            ("name", models.CharField(max_length=200)),
            ("user", models.ForeignKey("auth.User", models.CASCADE)),
        ],
    )
    author_with_custom_user = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
            ("name", models.CharField(max_length=200)),
            ("user", models.ForeignKey("thirdapp.CustomUser", models.CASCADE)),
        ],
    )
    author_proxy = ModelState(
        "testapp", "AuthorProxy", [], {"proxy": True}, ("testapp.author",)
    )
    author_proxy_options = ModelState(
        "testapp",
        "AuthorProxy",
        [],
        {
            "proxy": True,
            "verbose_name": "Super Author",
        },
        ("testapp.author",),
    )
    author_proxy_notproxy = ModelState(
        "testapp", "AuthorProxy", [], {}, ("testapp.author",)
    )
    author_proxy_third = ModelState(
        "thirdapp", "AuthorProxy", [], {"proxy": True}, ("testapp.author",)
    )
    author_proxy_third_notproxy = ModelState(
        "thirdapp", "AuthorProxy", [], {}, ("testapp.author",)
    )
    author_proxy_proxy = ModelState(
        "testapp", "AAuthorProxyProxy", [], {"proxy": True}, ("testapp.authorproxy",)
    )
    author_unmanaged = ModelState(
        "testapp", "AuthorUnmanaged", [], {"managed": False}, ("testapp.author",)
    )
    author_unmanaged_managed = ModelState(
        "testapp", "AuthorUnmanaged", [], {}, ("testapp.author",)
    )
    author_unmanaged_default_pk = ModelState(
        "testapp", "Author", [("id", models.AutoField(primary_key=True))]
    )
    author_unmanaged_custom_pk = ModelState(
        "testapp",
        "Author",
        [
            ("pk_field", models.IntegerField(primary_key=True)),
        ],
    )
    author_with_m2m = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
            ("publishers", models.ManyToManyField("testapp.Publisher")),
        ],
    )
    author_with_m2m_blank = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
            ("publishers", models.ManyToManyField("testapp.Publisher", blank=True)),
        ],
    )
    author_with_m2m_through = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
            (
                "publishers",
                models.ManyToManyField("testapp.Publisher", through="testapp.Contract"),
            ),
        ],
    )
    author_with_renamed_m2m_through = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
            (
                "publishers",
                models.ManyToManyField("testapp.Publisher", through="testapp.Deal"),
            ),
        ],
    )
    author_with_former_m2m = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
            ("publishers", models.CharField(max_length=100)),
        ],
    )
    author_with_options = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
        ],
        {
            "permissions": [("can_hire", "Can hire")],
            "verbose_name": "Authi",
        },
    )
    author_with_db_table_comment = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
        ],
        {"db_table_comment": "Table comment"},
    )
    author_with_db_table_options = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
        ],
        {"db_table": "author_one"},
    )
    author_with_new_db_table_options = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
        ],
        {"db_table": "author_two"},
    )
    author_renamed_with_db_table_options = ModelState(
        "testapp",
        "NewAuthor",
        [
            ("id", models.AutoField(primary_key=True)),
        ],
        {"db_table": "author_one"},
    )
    author_renamed_with_new_db_table_options = ModelState(
        "testapp",
        "NewAuthor",
        [
            ("id", models.AutoField(primary_key=True)),
        ],
        {"db_table": "author_three"},
    )
    contract = ModelState(
        "testapp",
        "Contract",
        [
            ("id", models.AutoField(primary_key=True)),
            ("author", models.ForeignKey("testapp.Author", models.CASCADE)),
            ("publisher", models.ForeignKey("testapp.Publisher", models.CASCADE)),
        ],
    )
    contract_renamed = ModelState(
        "testapp",
        "Deal",
        [
            ("id", models.AutoField(primary_key=True)),
            ("author", models.ForeignKey("testapp.Author", models.CASCADE)),
            ("publisher", models.ForeignKey("testapp.Publisher", models.CASCADE)),
        ],
    )
    publisher = ModelState(
        "testapp",
        "Publisher",
        [
            ("id", models.AutoField(primary_key=True)),
            ("name", models.CharField(max_length=100)),
        ],
    )
    publisher_with_author = ModelState(
        "testapp",
        "Publisher",
        [
            ("id", models.AutoField(primary_key=True)),
            ("author", models.ForeignKey("testapp.Author", models.CASCADE)),
            ("name", models.CharField(max_length=100)),
        ],
    )
    publisher_with_aardvark_author = ModelState(
        "testapp",
        "Publisher",
        [
            ("id", models.AutoField(primary_key=True)),
            ("author", models.ForeignKey("testapp.Aardvark", models.CASCADE)),
            ("name", models.CharField(max_length=100)),
        ],
    )
    publisher_with_book = ModelState(
        "testapp",
        "Publisher",
        [
            ("id", models.AutoField(primary_key=True)),
            ("author", models.ForeignKey("otherapp.Book", models.CASCADE)),
            ("name", models.CharField(max_length=100)),
        ],
    )
    other_pony = ModelState(
        "otherapp",
        "Pony",
        [
            ("id", models.AutoField(primary_key=True)),
        ],
    )
    other_pony_food = ModelState(
        "otherapp",
        "Pony",
        [
            ("id", models.AutoField(primary_key=True)),
        ],
        managers=[
            ("food_qs", FoodQuerySet.as_manager()),
            ("food_mgr", FoodManager("a", "b")),
            ("food_mgr_kwargs", FoodManager("x", "y", 3, 4)),
        ],
    )
    other_stable = ModelState(
        "otherapp", "Stable", [("id", models.AutoField(primary_key=True))]
    )
    third_thing = ModelState(
        "thirdapp", "Thing", [("id", models.AutoField(primary_key=True))]
    )
    book = ModelState(
        "otherapp",
        "Book",
        [
            ("id", models.AutoField(primary_key=True)),
            ("author", models.ForeignKey("testapp.Author", models.CASCADE)),
            ("title", models.CharField(max_length=200)),
        ],
    )
    book_proxy_fk = ModelState(
        "otherapp",
        "Book",
        [
            ("id", models.AutoField(primary_key=True)),
            ("author", models.ForeignKey("thirdapp.AuthorProxy", models.CASCADE)),
            ("title", models.CharField(max_length=200)),
        ],
    )
    book_proxy_proxy_fk = ModelState(
        "otherapp",
        "Book",
        [
            ("id", models.AutoField(primary_key=True)),
            ("author", models.ForeignKey("testapp.AAuthorProxyProxy", models.CASCADE)),
        ],
    )
    book_migrations_fk = ModelState(
        "otherapp",
        "Book",
        [
            ("id", models.AutoField(primary_key=True)),
            ("author", models.ForeignKey("migrations.UnmigratedModel", models.CASCADE)),
            ("title", models.CharField(max_length=200)),
        ],
    )
    book_with_no_author_fk = ModelState(
        "otherapp",
        "Book",
        [
            ("id", models.AutoField(primary_key=True)),
            ("author", models.IntegerField()),
            ("title", models.CharField(max_length=200)),
        ],
    )
    book_with_no_author = ModelState(
        "otherapp",
        "Book",
        [
            ("id", models.AutoField(primary_key=True)),
            ("title", models.CharField(max_length=200)),
        ],
    )
    book_with_author_renamed = ModelState(
        "otherapp",
        "Book",
        [
            ("id", models.AutoField(primary_key=True)),
            ("author", models.ForeignKey("testapp.Writer", models.CASCADE)),
            ("title", models.CharField(max_length=200)),
        ],
    )
    book_with_field_and_author_renamed = ModelState(
        "otherapp",
        "Book",
        [
            ("id", models.AutoField(primary_key=True)),
            ("writer", models.ForeignKey("testapp.Writer", models.CASCADE)),
            ("title", models.CharField(max_length=200)),
        ],
    )
    book_with_multiple_authors = ModelState(
        "otherapp",
        "Book",
        [
            ("id", models.AutoField(primary_key=True)),
            ("authors", models.ManyToManyField("testapp.Author")),
            ("title", models.CharField(max_length=200)),
        ],
    )
    book_with_multiple_authors_through_attribution = ModelState(
        "otherapp",
        "Book",
        [
            ("id", models.AutoField(primary_key=True)),
            (
                "authors",
                models.ManyToManyField(
                    "testapp.Author", through="otherapp.Attribution"
                ),
            ),
            ("title", models.CharField(max_length=200)),
        ],
    )
    book_indexes = ModelState(
        "otherapp",
        "Book",
        [
            ("id", models.AutoField(primary_key=True)),
            ("author", models.ForeignKey("testapp.Author", models.CASCADE)),
            ("title", models.CharField(max_length=200)),
        ],
        {
            "indexes": [
                models.Index(fields=["author", "title"], name="book_title_author_idx")
            ],
        },
    )
    book_unordered_indexes = ModelState(
        "otherapp",
        "Book",
        [
            ("id", models.AutoField(primary_key=True)),
            ("author", models.ForeignKey("testapp.Author", models.CASCADE)),
            ("title", models.CharField(max_length=200)),
        ],
        {
            "indexes": [
                models.Index(fields=["title", "author"], name="book_author_title_idx")
            ],
        },
    )
    book_unique_together = ModelState(
        "otherapp",
        "Book",
        [
            ("id", models.AutoField(primary_key=True)),
            ("author", models.ForeignKey("testapp.Author", models.CASCADE)),
            ("title", models.CharField(max_length=200)),
        ],
        {
            "unique_together": {("author", "title")},
        },
    )
    book_unique_together_2 = ModelState(
        "otherapp",
        "Book",
        [
            ("id", models.AutoField(primary_key=True)),
            ("author", models.ForeignKey("testapp.Author", models.CASCADE)),
            ("title", models.CharField(max_length=200)),
        ],
        {
            "unique_together": {("title", "author")},
        },
    )
    book_unique_together_3 = ModelState(
        "otherapp",
        "Book",
        [
            ("id", models.AutoField(primary_key=True)),
            ("newfield", models.IntegerField()),
            ("author", models.ForeignKey("testapp.Author", models.CASCADE)),
            ("title", models.CharField(max_length=200)),
        ],
        {
            "unique_together": {("title", "newfield")},
        },
    )
    book_unique_together_4 = ModelState(
        "otherapp",
        "Book",
        [
            ("id", models.AutoField(primary_key=True)),
            ("newfield2", models.IntegerField()),
            ("author", models.ForeignKey("testapp.Author", models.CASCADE)),
            ("title", models.CharField(max_length=200)),
        ],
        {
            "unique_together": {("title", "newfield2")},
        },
    )
    attribution = ModelState(
        "otherapp",
        "Attribution",
        [
            ("id", models.AutoField(primary_key=True)),
            ("author", models.ForeignKey("testapp.Author", models.CASCADE)),
            ("book", models.ForeignKey("otherapp.Book", models.CASCADE)),
        ],
    )
    edition = ModelState(
        "thirdapp",
        "Edition",
        [
            ("id", models.AutoField(primary_key=True)),
            ("book", models.ForeignKey("otherapp.Book", models.CASCADE)),
        ],
    )
    custom_user = ModelState(
        "thirdapp",
        "CustomUser",
        [
            ("id", models.AutoField(primary_key=True)),
            ("username", models.CharField(max_length=255)),
        ],
        bases=(AbstractBaseUser,),
    )
    custom_user_no_inherit = ModelState(
        "thirdapp",
        "CustomUser",
        [
            ("id", models.AutoField(primary_key=True)),
            ("username", models.CharField(max_length=255)),
        ],
    )
    aardvark = ModelState(
        "thirdapp", "Aardvark", [("id", models.AutoField(primary_key=True))]
    )
    aardvark_testapp = ModelState(
        "testapp", "Aardvark", [("id", models.AutoField(primary_key=True))]
    )
    aardvark_based_on_author = ModelState(
        "testapp", "Aardvark", [], bases=("testapp.Author",)
    )
    aardvark_pk_fk_author = ModelState(
        "testapp",
        "Aardvark",
        [
            (
                "id",
                models.OneToOneField(
                    "testapp.Author", models.CASCADE, primary_key=True
                ),
            ),
        ],
    )
    knight = ModelState("eggs", "Knight", [("id", models.AutoField(primary_key=True))])
    rabbit = ModelState(
        "eggs",
        "Rabbit",
        [
            ("id", models.AutoField(primary_key=True)),
            ("knight", models.ForeignKey("eggs.Knight", models.CASCADE)),
            ("parent", models.ForeignKey("eggs.Rabbit", models.CASCADE)),
        ],
        {
            "unique_together": {("parent", "knight")},
            "indexes": [
                models.Index(
                    fields=["parent", "knight"], name="rabbit_circular_fk_index"
                )
            ],
        },
    )

    def test_arrange_for_graph(self):
        """Tests auto-naming of migrations for graph matching."""
        # Make a fake graph
        graph = MigrationGraph()
        graph.add_node(("testapp", "0001_initial"), None)
        graph.add_node(("testapp", "0002_foobar"), None)
        graph.add_node(("otherapp", "0001_initial"), None)
        graph.add_dependency(
            "testapp.0002_foobar",
            ("testapp", "0002_foobar"),
            ("testapp", "0001_initial"),
        )
        graph.add_dependency(
            "testapp.0002_foobar",
            ("testapp", "0002_foobar"),
            ("otherapp", "0001_initial"),
        )
        # Use project state to make a new migration change set
        before = self.make_project_state([self.publisher, self.other_pony])
        after = self.make_project_state(
            [
                self.author_empty,
                self.publisher,
                self.other_pony,
                self.other_stable,
            ]
        )
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector._detect_changes()
        # Run through arrange_for_graph
        changes = autodetector.arrange_for_graph(changes, graph)
        # Make sure there's a new name, deps match, etc.
        self.assertEqual(changes["testapp"][0].name, "0003_author")
        self.assertEqual(
            changes["testapp"][0].dependencies, [("testapp", "0002_foobar")]
        )
        self.assertEqual(changes["otherapp"][0].name, "0002_stable")
        self.assertEqual(
            changes["otherapp"][0].dependencies, [("otherapp", "0001_initial")]
        )

    def test_arrange_for_graph_with_multiple_initial(self):
        # Make a fake graph.
        graph = MigrationGraph()
        # Use project state to make a new migration change set.
        before = self.make_project_state([])
        after = self.make_project_state(
            [self.author_with_book, self.book, self.attribution]
        )
        autodetector = MigrationAutodetector(
            before, after, MigrationQuestioner({"ask_initial": True})
        )
        changes = autodetector._detect_changes()
        changes = autodetector.arrange_for_graph(changes, graph)

        self.assertEqual(changes["otherapp"][0].name, "0001_initial")
        self.assertEqual(changes["otherapp"][0].dependencies, [])
        self.assertEqual(changes["otherapp"][1].name, "0002_initial")
        self.assertCountEqual(
            changes["otherapp"][1].dependencies,
            [("testapp", "0001_initial"), ("otherapp", "0001_initial")],
        )
        self.assertEqual(changes["testapp"][0].name, "0001_initial")
        self.assertEqual(
            changes["testapp"][0].dependencies, [("otherapp", "0001_initial")]
        )

    def test_trim_apps(self):
        """
        Trim does not remove dependencies but does remove unwanted apps.
        """
        # Use project state to make a new migration change set
        before = self.make_project_state([])
        after = self.make_project_state(
            [self.author_empty, self.other_pony, self.other_stable, self.third_thing]
        )
        autodetector = MigrationAutodetector(
            before, after, MigrationQuestioner({"ask_initial": True})
        )
        changes = autodetector._detect_changes()
        # Run through arrange_for_graph
        graph = MigrationGraph()
        changes = autodetector.arrange_for_graph(changes, graph)
        changes["testapp"][0].dependencies.append(("otherapp", "0001_initial"))
        changes = autodetector._trim_to_apps(changes, {"testapp"})
        # Make sure there's the right set of migrations
        self.assertEqual(changes["testapp"][0].name, "0001_initial")
        self.assertEqual(changes["otherapp"][0].name, "0001_initial")
        self.assertNotIn("thirdapp", changes)

    def test_custom_migration_name(self):
        """Tests custom naming of migrations for graph matching."""
        # Make a fake graph
        graph = MigrationGraph()
        graph.add_node(("testapp", "0001_initial"), None)
        graph.add_node(("testapp", "0002_foobar"), None)
        graph.add_node(("otherapp", "0001_initial"), None)
        graph.add_dependency(
            "testapp.0002_foobar",
            ("testapp", "0002_foobar"),
            ("testapp", "0001_initial"),
        )

        # Use project state to make a new migration change set
        before = self.make_project_state([])
        after = self.make_project_state(
            [self.author_empty, self.other_pony, self.other_stable]
        )
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector._detect_changes()

        # Run through arrange_for_graph
        migration_name = "custom_name"
        changes = autodetector.arrange_for_graph(changes, graph, migration_name)

        # Make sure there's a new name, deps match, etc.
        self.assertEqual(changes["testapp"][0].name, "0003_%s" % migration_name)
        self.assertEqual(
            changes["testapp"][0].dependencies, [("testapp", "0002_foobar")]
        )
        self.assertEqual(changes["otherapp"][0].name, "0002_%s" % migration_name)
        self.assertEqual(
            changes["otherapp"][0].dependencies, [("otherapp", "0001_initial")]
        )

    def test_new_model(self):
        """Tests autodetection of new models."""
        changes = self.get_changes([], [self.other_pony_food])
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "otherapp", 1)
        self.assertOperationTypes(changes, "otherapp", 0, ["CreateModel"])
        self.assertOperationAttributes(changes, "otherapp", 0, 0, name="Pony")
        self.assertEqual(
            [name for name, mgr in changes["otherapp"][0].operations[0].managers],
            ["food_qs", "food_mgr", "food_mgr_kwargs"],
        )

    def test_old_model(self):
        """Tests deletion of old models."""
        changes = self.get_changes([self.author_empty], [])
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["DeleteModel"])
        self.assertOperationAttributes(changes, "testapp", 0, 0, name="Author")

    def test_add_field(self):
        """Tests autodetection of new fields."""
        changes = self.get_changes([self.author_empty], [self.author_name])
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["AddField"])
        self.assertOperationAttributes(changes, "testapp", 0, 0, name="name")

    @mock.patch(
        "django.db.migrations.questioner.MigrationQuestioner.ask_not_null_addition",
        side_effect=AssertionError("Should not have prompted for not null addition"),
    )
    def test_add_date_fields_with_auto_now_not_asking_for_default(
        self, mocked_ask_method
    ):
        changes = self.get_changes(
            [self.author_empty], [self.author_dates_of_birth_auto_now]
        )
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(
            changes, "testapp", 0, ["AddField", "AddField", "AddField"]
        )
        self.assertOperationFieldAttributes(changes, "testapp", 0, 0, auto_now=True)
        self.assertOperationFieldAttributes(changes, "testapp", 0, 1, auto_now=True)
        self.assertOperationFieldAttributes(changes, "testapp", 0, 2, auto_now=True)

    @mock.patch(
        "django.db.migrations.questioner.MigrationQuestioner.ask_not_null_addition",
        side_effect=AssertionError("Should not have prompted for not null addition"),
    )
    def test_add_date_fields_with_auto_now_add_not_asking_for_null_addition(
        self, mocked_ask_method
    ):
        changes = self.get_changes(
            [self.author_empty], [self.author_dates_of_birth_auto_now_add]
        )
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(
            changes, "testapp", 0, ["AddField", "AddField", "AddField"]
        )
        self.assertOperationFieldAttributes(changes, "testapp", 0, 0, auto_now_add=True)
        self.assertOperationFieldAttributes(changes, "testapp", 0, 1, auto_now_add=True)
        self.assertOperationFieldAttributes(changes, "testapp", 0, 2, auto_now_add=True)

    @mock.patch(
        "django.db.migrations.questioner.MigrationQuestioner.ask_auto_now_add_addition"
    )
    def test_add_date_fields_with_auto_now_add_asking_for_default(
        self, mocked_ask_method
    ):
        changes = self.get_changes(
            [self.author_empty], [self.author_dates_of_birth_auto_now_add]
        )
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(
            changes, "testapp", 0, ["AddField", "AddField", "AddField"]
        )
        self.assertOperationFieldAttributes(changes, "testapp", 0, 0, auto_now_add=True)
        self.assertOperationFieldAttributes(changes, "testapp", 0, 1, auto_now_add=True)
        self.assertOperationFieldAttributes(changes, "testapp", 0, 2, auto_now_add=True)
        self.assertEqual(mocked_ask_method.call_count, 3)

    def test_remove_field(self):
        """Tests autodetection of removed fields."""
        changes = self.get_changes([self.author_name], [self.author_empty])
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["RemoveField"])
        self.assertOperationAttributes(changes, "testapp", 0, 0, name="name")

    def test_alter_field(self):
        """Tests autodetection of new fields."""
        changes = self.get_changes([self.author_name], [self.author_name_longer])
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["AlterField"])
        self.assertOperationAttributes(
            changes, "testapp", 0, 0, name="name", preserve_default=True
        )

    def test_supports_functools_partial(self):
        def _content_file_name(instance, filename, key, **kwargs):
            return "{}/{}".format(instance, filename)

        def content_file_name(key, **kwargs):
            return functools.partial(_content_file_name, key, **kwargs)

        # An unchanged partial reference.
        before = [
            ModelState(
                "testapp",
                "Author",
                [
                    ("id", models.AutoField(primary_key=True)),
                    (
                        "file",
                        models.FileField(
                            max_length=200, upload_to=content_file_name("file")
                        ),
                    ),
                ],
            )
        ]
        after = [
            ModelState(
                "testapp",
                "Author",
                [
                    ("id", models.AutoField(primary_key=True)),
                    (
                        "file",
                        models.FileField(
                            max_length=200, upload_to=content_file_name("file")
                        ),
                    ),
                ],
            )
        ]
        changes = self.get_changes(before, after)
        self.assertNumberMigrations(changes, "testapp", 0)

        # A changed partial reference.
        args_changed = [
            ModelState(
                "testapp",
                "Author",
                [
                    ("id", models.AutoField(primary_key=True)),
                    (
                        "file",
                        models.FileField(
                            max_length=200, upload_to=content_file_name("other-file")
                        ),
                    ),
                ],
            )
        ]
        changes = self.get_changes(before, args_changed)
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["AlterField"])
        # Can't use assertOperationFieldAttributes because we need the
        # deconstructed version, i.e., the exploded func/args/keywords rather
        # than the partial: we don't care if it's not the same instance of the
        # partial, only if it's the same source function, args, and keywords.
        value = changes["testapp"][0].operations[0].field.upload_to
        self.assertEqual(
            (_content_file_name, ("other-file",), {}),
            (value.func, value.args, value.keywords),
        )

        kwargs_changed = [
            ModelState(
                "testapp",
                "Author",
                [
                    ("id", models.AutoField(primary_key=True)),
                    (
                        "file",
                        models.FileField(
                            max_length=200,
                            upload_to=content_file_name("file", spam="eggs"),
                        ),
                    ),
                ],
            )
        ]
        changes = self.get_changes(before, kwargs_changed)
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["AlterField"])
        value = changes["testapp"][0].operations[0].field.upload_to
        self.assertEqual(
            (_content_file_name, ("file",), {"spam": "eggs"}),
            (value.func, value.args, value.keywords),
        )

    @mock.patch(
        "django.db.migrations.questioner.MigrationQuestioner.ask_not_null_alteration",
        side_effect=AssertionError("Should not have prompted for not null addition"),
    )
    def test_alter_field_to_not_null_with_default(self, mocked_ask_method):
        """
        #23609 - Tests autodetection of nullable to non-nullable alterations.
        """
        changes = self.get_changes([self.author_name_null], [self.author_name_default])
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["AlterField"])
        self.assertOperationAttributes(
            changes, "testapp", 0, 0, name="name", preserve_default=True
        )
        self.assertOperationFieldAttributes(
            changes, "testapp", 0, 0, default="Ada Lovelace"
        )

    @mock.patch(
        "django.db.migrations.questioner.MigrationQuestioner.ask_not_null_alteration",
        return_value=models.NOT_PROVIDED,
    )
    def test_alter_field_to_not_null_without_default(self, mocked_ask_method):
        """
        #23609 - Tests autodetection of nullable to non-nullable alterations.
        """
        changes = self.get_changes([self.author_name_null], [self.author_name])
        self.assertEqual(mocked_ask_method.call_count, 1)
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["AlterField"])
        self.assertOperationAttributes(
            changes, "testapp", 0, 0, name="name", preserve_default=True
        )
        self.assertOperationFieldAttributes(
            changes, "testapp", 0, 0, default=models.NOT_PROVIDED
        )

    @mock.patch(
        "django.db.migrations.questioner.MigrationQuestioner.ask_not_null_alteration",
        return_value="Some Name",
    )
    def test_alter_field_to_not_null_oneoff_default(self, mocked_ask_method):
        """
        #23609 - Tests autodetection of nullable to non-nullable alterations.
        """
        changes = self.get_changes([self.author_name_null], [self.author_name])
        self.assertEqual(mocked_ask_method.call_count, 1)
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["AlterField"])
        self.assertOperationAttributes(
            changes, "testapp", 0, 0, name="name", preserve_default=False
        )
        self.assertOperationFieldAttributes(
            changes, "testapp", 0, 0, default="Some Name"
        )

    def test_rename_field(self):
        """Tests autodetection of renamed fields."""
        changes = self.get_changes(
            [self.author_name],
            [self.author_name_renamed],
            MigrationQuestioner({"ask_rename": True}),
        )
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["RenameField"])
        self.assertOperationAttributes(
            changes, "testapp", 0, 0, old_name="name", new_name="names"
        )

    def test_rename_field_foreign_key_to_field(self):
        before = [
            ModelState(
                "app",
                "Foo",
                [
                    ("id", models.AutoField(primary_key=True)),
                    ("field", models.IntegerField(unique=True)),
                ],
            ),
            ModelState(
                "app",
                "Bar",
                [
                    ("id", models.AutoField(primary_key=True)),
                    (
                        "foo",
                        models.ForeignKey("app.Foo", models.CASCADE, to_field="field"),
                    ),
                ],
            ),
        ]
        after = [
            ModelState(
                "app",
                "Foo",
                [
                    ("id", models.AutoField(primary_key=True)),
                    ("renamed_field", models.IntegerField(unique=True)),
                ],
            ),
            ModelState(
                "app",
                "Bar",
                [
                    ("id", models.AutoField(primary_key=True)),
                    (
                        "foo",
                        models.ForeignKey(
                            "app.Foo", models.CASCADE, to_field="renamed_field"
                        ),
                    ),
                ],
            ),
        ]
        changes = self.get_changes(
            before, after, MigrationQuestioner({"ask_rename": True})
        )
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "app", 1)
        self.assertOperationTypes(changes, "app", 0, ["RenameField"])
        self.assertOperationAttributes(
            changes, "app", 0, 0, old_name="field", new_name="renamed_field"
        )

    def test_rename_foreign_object_fields(self):
        fields = ("first", "second")
        renamed_fields = ("first_renamed", "second_renamed")
        before = [
            ModelState(
                "app",
                "Foo",
                [
                    ("id", models.AutoField(primary_key=True)),
                    ("first", models.IntegerField()),
                    ("second", models.IntegerField()),
                ],
                options={"unique_together": {fields}},
            ),
            ModelState(
                "app",
                "Bar",
                [
                    ("id", models.AutoField(primary_key=True)),
                    ("first", models.IntegerField()),
                    ("second", models.IntegerField()),
                    (
                        "foo",
                        models.ForeignObject(
                            "app.Foo",
                            models.CASCADE,
                            from_fields=fields,
                            to_fields=fields,
                        ),
                    ),
                ],
            ),
        ]
        # Case 1: to_fields renames.
        after = [
            ModelState(
                "app",
                "Foo",
                [
                    ("id", models.AutoField(primary_key=True)),
                    ("first_renamed", models.IntegerField()),
                    ("second_renamed", models.IntegerField()),
                ],
                options={"unique_together": {renamed_fields}},
            ),
            ModelState(
                "app",
                "Bar",
                [
                    ("id", models.AutoField(primary_key=True)),
                    ("first", models.IntegerField()),
                    ("second", models.IntegerField()),
                    (
                        "foo",
                        models.ForeignObject(
                            "app.Foo",
                            models.CASCADE,
                            from_fields=fields,
                            to_fields=renamed_fields,
                        ),
                    ),
                ],
            ),
        ]
        changes = self.get_changes(
            before, after, MigrationQuestioner({"ask_rename": True})
        )
        self.assertNumberMigrations(changes, "app", 1)
        self.assertOperationTypes(
            changes, "app", 0, ["RenameField", "RenameField", "AlterUniqueTogether"]
        )
        self.assertOperationAttributes(
            changes,
            "app",
            0,
            0,
            model_name="foo",
            old_name="first",
            new_name="first_renamed",
        )
        self.assertOperationAttributes(
            changes,
            "app",
            0,
            1,
            model_name="foo",
            old_name="second",
            new_name="second_renamed",
        )
        # Case 2: from_fields renames.
        after = [
            ModelState(
                "app",
                "Foo",
                [
                    ("id", models.AutoField(primary_key=True)),
                    ("first", models.IntegerField()),
                    ("second", models.IntegerField()),
                ],
                options={"unique_together": {fields}},
            ),
            ModelState(
                "app",
                "Bar",
                [
                    ("id", models.AutoField(primary_key=True)),
                    ("first_renamed", models.IntegerField()),
                    ("second_renamed", models.IntegerField()),
                    (
                        "foo",
                        models.ForeignObject(
                            "app.Foo",
                            models.CASCADE,
                            from_fields=renamed_fields,
                            to_fields=fields,
                        ),
                    ),
                ],
            ),
        ]
        changes = self.get_changes(
            before, after, MigrationQuestioner({"ask_rename": True})
        )
        self.assertNumberMigrations(changes, "app", 1)
        self.assertOperationTypes(changes, "app", 0, ["RenameField", "RenameField"])
        self.assertOperationAttributes(
            changes,
            "app",
            0,
            0,
            model_name="bar",
            old_name="first",
            new_name="first_renamed",
        )
        self.assertOperationAttributes(
            changes,
            "app",
            0,
            1,
            model_name="bar",
            old_name="second",
            new_name="second_renamed",
        )

    def test_rename_referenced_primary_key(self):
        before = [
            ModelState(
                "app",
                "Foo",
                [
                    ("id", models.CharField(primary_key=True, serialize=False)),
                ],
            ),
            ModelState(
                "app",
                "Bar",
                [
                    ("id", models.AutoField(primary_key=True)),
                    ("foo", models.ForeignKey("app.Foo", models.CASCADE)),
                ],
            ),
        ]
        after = [
            ModelState(
                "app",
                "Foo",
                [("renamed_id", models.CharField(primary_key=True, serialize=False))],
            ),
            ModelState(
                "app",
                "Bar",
                [
                    ("id", models.AutoField(primary_key=True)),
                    ("foo", models.ForeignKey("app.Foo", models.CASCADE)),
                ],
            ),
        ]
        changes = self.get_changes(
            before, after, MigrationQuestioner({"ask_rename": True})
        )
        self.assertNumberMigrations(changes, "app", 1)
        self.assertOperationTypes(changes, "app", 0, ["RenameField"])
        self.assertOperationAttributes(
            changes, "app", 0, 0, old_name="id", new_name="renamed_id"
        )

    def test_rename_field_preserved_db_column(self):
        """
        RenameField is used if a field is renamed and db_column equal to the
        old field's column is added.
        """
        before = [
            ModelState(
                "app",
                "Foo",
                [
                    ("id", models.AutoField(primary_key=True)),
                    ("field", models.IntegerField()),
                ],
            ),
        ]
        after = [
            ModelState(
                "app",
                "Foo",
                [
                    ("id", models.AutoField(primary_key=True)),
                    ("renamed_field", models.IntegerField(db_column="field")),
                ],
            ),
        ]
        changes = self.get_changes(
            before, after, MigrationQuestioner({"ask_rename": True})
        )
        self.assertNumberMigrations(changes, "app", 1)
        self.assertOperationTypes(changes, "app", 0, ["AlterField", "RenameField"])
        self.assertOperationAttributes(
            changes,
            "app",
            0,
            0,
            model_name="foo",
            name="field",
        )
        self.assertEqual(
            changes["app"][0].operations[0].field.deconstruct(),
            (
                "field",
                "django.db.models.IntegerField",
                [],
                {"db_column": "field"},
            ),
        )
        self.assertOperationAttributes(
            changes,
            "app",
            0,
            1,
            model_name="foo",
            old_name="field",
            new_name="renamed_field",
        )

    def test_rename_related_field_preserved_db_column(self):
        before = [
            ModelState(
                "app",
                "Foo",
                [
                    ("id", models.AutoField(primary_key=True)),
                ],
            ),
            ModelState(
                "app",
                "Bar",
                [
                    ("id", models.AutoField(primary_key=True)),
                    ("foo", models.ForeignKey("app.Foo", models.CASCADE)),
                ],
            ),
        ]
        after = [
            ModelState(
                "app",
                "Foo",
                [
                    ("id", models.AutoField(primary_key=True)),
                ],
            ),
            ModelState(
                "app",
                "Bar",
                [
                    ("id", models.AutoField(primary_key=True)),
                    (
                        "renamed_foo",
                        models.ForeignKey(
                            "app.Foo", models.CASCADE, db_column="foo_id"
                        ),
                    ),
                ],
            ),
        ]
        changes = self.get_changes(
            before, after, MigrationQuestioner({"ask_rename": True})
        )
        self.assertNumberMigrations(changes, "app", 1)
        self.assertOperationTypes(changes, "app", 0, ["AlterField", "RenameField"])
        self.assertOperationAttributes(
            changes,
            "app",
            0,
            0,
            model_name="bar",
            name="foo",
        )
        self.assertEqual(
            changes["app"][0].operations[0].field.deconstruct(),
            (
                "foo",
                "django.db.models.ForeignKey",
                [],
                {"to": "app.foo", "on_delete": models.CASCADE, "db_column": "foo_id"},
            ),
        )
        self.assertOperationAttributes(
            changes,
            "app",
            0,
            1,
            model_name="bar",
            old_name="foo",
            new_name="renamed_foo",
        )

    def test_rename_field_with_renamed_model(self):
        changes = self.get_changes(
            [self.author_name],
            [
                ModelState(
                    "testapp",
                    "RenamedAuthor",
                    [
                        ("id", models.AutoField(primary_key=True)),
                        ("renamed_name", models.CharField(max_length=200)),
                    ],
                ),
            ],
            MigrationQuestioner({"ask_rename_model": True, "ask_rename": True}),
        )
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["RenameModel", "RenameField"])
        self.assertOperationAttributes(
            changes,
            "testapp",
            0,
            0,
            old_name="Author",
            new_name="RenamedAuthor",
        )
        self.assertOperationAttributes(
            changes,
            "testapp",
            0,
            1,
            old_name="name",
            new_name="renamed_name",
        )

    def test_rename_model(self):
        """Tests autodetection of renamed models."""
        changes = self.get_changes(
            [self.author_with_book, self.book],
            [self.author_renamed_with_book, self.book_with_author_renamed],
            MigrationQuestioner({"ask_rename_model": True}),
        )
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["RenameModel"])
        self.assertOperationAttributes(
            changes, "testapp", 0, 0, old_name="Author", new_name="Writer"
        )
        # Now that RenameModel handles related fields too, there should be
        # no AlterField for the related field.
        self.assertNumberMigrations(changes, "otherapp", 0)

    def test_rename_model_case(self):
        """
        Model name is case-insensitive. Changing case doesn't lead to any
        autodetected operations.
        """
        author_renamed = ModelState(
            "testapp",
            "author",
            [
                ("id", models.AutoField(primary_key=True)),
            ],
        )
        changes = self.get_changes(
            [self.author_empty, self.book],
            [author_renamed, self.book],
            questioner=MigrationQuestioner({"ask_rename_model": True}),
        )
        self.assertNumberMigrations(changes, "testapp", 0)
        self.assertNumberMigrations(changes, "otherapp", 0)

    def test_renamed_referenced_m2m_model_case(self):
        publisher_renamed = ModelState(
            "testapp",
            "publisher",
            [
                ("id", models.AutoField(primary_key=True)),
                ("name", models.CharField(max_length=100)),
            ],
        )
        changes = self.get_changes(
            [self.publisher, self.author_with_m2m],
            [publisher_renamed, self.author_with_m2m],
            questioner=MigrationQuestioner({"ask_rename_model": True}),
        )
        self.assertNumberMigrations(changes, "testapp", 0)
        self.assertNumberMigrations(changes, "otherapp", 0)

    def test_rename_m2m_through_model(self):
        """
        Tests autodetection of renamed models that are used in M2M relations as
        through models.
        """
        changes = self.get_changes(
            [self.author_with_m2m_through, self.publisher, self.contract],
            [
                self.author_with_renamed_m2m_through,
                self.publisher,
                self.contract_renamed,
            ],
            MigrationQuestioner({"ask_rename_model": True}),
        )
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["RenameModel"])
        self.assertOperationAttributes(
            changes, "testapp", 0, 0, old_name="Contract", new_name="Deal"
        )

    def test_rename_model_with_renamed_rel_field(self):
        """
        Tests autodetection of renamed models while simultaneously renaming one
        of the fields that relate to the renamed model.
        """
        changes = self.get_changes(
            [self.author_with_book, self.book],
            [self.author_renamed_with_book, self.book_with_field_and_author_renamed],
            MigrationQuestioner({"ask_rename": True, "ask_rename_model": True}),
        )
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["RenameModel"])
        self.assertOperationAttributes(
            changes, "testapp", 0, 0, old_name="Author", new_name="Writer"
        )
        # Right number/type of migrations for related field rename?
        # Alter is already taken care of.
        self.assertNumberMigrations(changes, "otherapp", 1)
        self.assertOperationTypes(changes, "otherapp", 0, ["RenameField"])
        self.assertOperationAttributes(
            changes, "otherapp", 0, 0, old_name="author", new_name="writer"
        )

    def test_rename_model_with_fks_in_different_position(self):
        """
        #24537 - The order of fields in a model does not influence
        the RenameModel detection.
        """
        before = [
            ModelState(
                "testapp",
                "EntityA",
                [
                    ("id", models.AutoField(primary_key=True)),
                ],
            ),
            ModelState(
                "testapp",
                "EntityB",
                [
                    ("id", models.AutoField(primary_key=True)),
                    ("some_label", models.CharField(max_length=255)),
                    ("entity_a", models.ForeignKey("testapp.EntityA", models.CASCADE)),
                ],
            ),
        ]
        after = [
            ModelState(
                "testapp",
                "EntityA",
                [
                    ("id", models.AutoField(primary_key=True)),
                ],
            ),
            ModelState(
                "testapp",
                "RenamedEntityB",
                [
                    ("id", models.AutoField(primary_key=True)),
                    ("entity_a", models.ForeignKey("testapp.EntityA", models.CASCADE)),
                    ("some_label", models.CharField(max_length=255)),
                ],
            ),
        ]
        changes = self.get_changes(
            before, after, MigrationQuestioner({"ask_rename_model": True})
        )
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["RenameModel"])
        self.assertOperationAttributes(
            changes, "testapp", 0, 0, old_name="EntityB", new_name="RenamedEntityB"
        )

    def test_rename_model_reverse_relation_dependencies(self):
        """
        The migration to rename a model pointed to by a foreign key in another
        app must run after the other app's migration that adds the foreign key
        with model's original name. Therefore, the renaming migration has a
        dependency on that other migration.
        """
        before = [
            ModelState(
                "testapp",
                "EntityA",
                [
                    ("id", models.AutoField(primary_key=True)),
                ],
            ),
            ModelState(
                "otherapp",
                "EntityB",
                [
                    ("id", models.AutoField(primary_key=True)),
                    ("entity_a", models.ForeignKey("testapp.EntityA", models.CASCADE)),
                ],
            ),
        ]
        after = [
            ModelState(
                "testapp",
                "RenamedEntityA",
                [
                    ("id", models.AutoField(primary_key=True)),
                ],
            ),
            ModelState(
                "otherapp",
                "EntityB",
                [
                    ("id", models.AutoField(primary_key=True)),
                    (
                        "entity_a",
                        models.ForeignKey("testapp.RenamedEntityA", models.CASCADE),
                    ),
                ],
            ),
        ]
        changes = self.get_changes(
            before, after, MigrationQuestioner({"ask_rename_model": True})
        )
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertMigrationDependencies(
            changes, "testapp", 0, [("otherapp", "__first__")]
        )
        self.assertOperationTypes(changes, "testapp", 0, ["RenameModel"])
        self.assertOperationAttributes(
            changes, "testapp", 0, 0, old_name="EntityA", new_name="RenamedEntityA"
        )

    def test_fk_dependency(self):
        """Having a ForeignKey automatically adds a dependency."""
        # Note that testapp (author) has no dependencies,
        # otherapp (book) depends on testapp (author),
        # thirdapp (edition) depends on otherapp (book)
        changes = self.get_changes([], [self.author_name, self.book, self.edition])
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["CreateModel"])
        self.assertOperationAttributes(changes, "testapp", 0, 0, name="Author")
        self.assertMigrationDependencies(changes, "testapp", 0, [])
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "otherapp", 1)
        self.assertOperationTypes(changes, "otherapp", 0, ["CreateModel"])
        self.assertOperationAttributes(changes, "otherapp", 0, 0, name="Book")
        self.assertMigrationDependencies(
            changes, "otherapp", 0, [("testapp", "auto_1")]
        )
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "thirdapp", 1)
        self.assertOperationTypes(changes, "thirdapp", 0, ["CreateModel"])
        self.assertOperationAttributes(changes, "thirdapp", 0, 0, name="Edition")
        self.assertMigrationDependencies(
            changes, "thirdapp", 0, [("otherapp", "auto_1")]
        )

    def test_proxy_fk_dependency(self):
        """FK dependencies still work on proxy models."""
        # Note that testapp (author) has no dependencies,
        # otherapp (book) depends on testapp (authorproxy)
        changes = self.get_changes(
            [], [self.author_empty, self.author_proxy_third, self.book_proxy_fk]
        )
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["CreateModel"])
        self.assertOperationAttributes(changes, "testapp", 0, 0, name="Author")
        self.assertMigrationDependencies(changes, "testapp", 0, [])
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "otherapp", 1)
        self.assertOperationTypes(changes, "otherapp", 0, ["CreateModel"])
        self.assertOperationAttributes(changes, "otherapp", 0, 0, name="Book")
        self.assertMigrationDependencies(
            changes, "otherapp", 0, [("thirdapp", "auto_1")]
        )
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "thirdapp", 1)
        self.assertOperationTypes(changes, "thirdapp", 0, ["CreateModel"])
        self.assertOperationAttributes(changes, "thirdapp", 0, 0, name="AuthorProxy")
        self.assertMigrationDependencies(
            changes, "thirdapp", 0, [("testapp", "auto_1")]
        )

    def test_same_app_no_fk_dependency(self):
        """
        A migration with a FK between two models of the same app
        does not have a dependency to itself.
        """
        changes = self.get_changes([], [self.author_with_publisher, self.publisher])
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["CreateModel", "CreateModel"])
        self.assertOperationAttributes(changes, "testapp", 0, 0, name="Publisher")
        self.assertOperationAttributes(changes, "testapp", 0, 1, name="Author")
        self.assertMigrationDependencies(changes, "testapp", 0, [])

    def test_circular_fk_dependency(self):
        """
        Having a circular ForeignKey dependency automatically
        resolves the situation into 2 migrations on one side and 1 on the other.
        """
        changes = self.get_changes(
            [], [self.author_with_book, self.book, self.publisher_with_book]
        )
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["CreateModel", "CreateModel"])
        self.assertOperationAttributes(changes, "testapp", 0, 0, name="Author")
        self.assertOperationAttributes(changes, "testapp", 0, 1, name="Publisher")
        self.assertMigrationDependencies(
            changes, "testapp", 0, [("otherapp", "auto_1")]
        )
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "otherapp", 2)
        self.assertOperationTypes(changes, "otherapp", 0, ["CreateModel"])
        self.assertOperationTypes(changes, "otherapp", 1, ["AddField"])
        self.assertMigrationDependencies(changes, "otherapp", 0, [])
        self.assertMigrationDependencies(
            changes, "otherapp", 1, [("otherapp", "auto_1"), ("testapp", "auto_1")]
        )
        # both split migrations should be `initial`
        self.assertTrue(changes["otherapp"][0].initial)
        self.assertTrue(changes["otherapp"][1].initial)

    def test_same_app_circular_fk_dependency(self):
        """
        A migration with a FK between two models of the same app does
        not have a dependency to itself.
        """
        changes = self.get_changes(
            [], [self.author_with_publisher, self.publisher_with_author]
        )
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(
            changes, "testapp", 0, ["CreateModel", "CreateModel", "AddField"]
        )
        self.assertOperationAttributes(changes, "testapp", 0, 0, name="Author")
        self.assertOperationAttributes(changes, "testapp", 0, 1, name="Publisher")
        self.assertOperationAttributes(changes, "testapp", 0, 2, name="publisher")
        self.assertMigrationDependencies(changes, "testapp", 0, [])

    def test_same_app_circular_fk_dependency_with_unique_together_and_indexes(self):
        """
        #22275 - A migration with circular FK dependency does not try
        to create unique together constraint and indexes before creating all
        required fields first.
        """
        changes = self.get_changes([], [self.knight, self.rabbit])
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "eggs", 1)
        self.assertOperationTypes(
            changes,
            "eggs",
            0,
            ["CreateModel", "CreateModel", "AddIndex", "AlterUniqueTogether"],
        )
        self.assertNotIn("unique_together", changes["eggs"][0].operations[0].options)
        self.assertNotIn("unique_together", changes["eggs"][0].operations[1].options)
        self.assertMigrationDependencies(changes, "eggs", 0, [])

    def test_alter_db_table_add(self):
        """Tests detection for adding db_table in model's options."""
        changes = self.get_changes(
            [self.author_empty], [self.author_with_db_table_options]
        )
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["AlterModelTable"])
        self.assertOperationAttributes(
            changes, "testapp", 0, 0, name="author", table="author_one"
        )

    def test_alter_db_table_change(self):
        """Tests detection for changing db_table in model's options'."""
        changes = self.get_changes(
            [self.author_with_db_table_options], [self.author_with_new_db_table_options]
        )
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["AlterModelTable"])
        self.assertOperationAttributes(
            changes, "testapp", 0, 0, name="author", table="author_two"
        )

    def test_alter_db_table_remove(self):
        """Tests detection for removing db_table in model's options."""
        changes = self.get_changes(
            [self.author_with_db_table_options], [self.author_empty]
        )
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["AlterModelTable"])
        self.assertOperationAttributes(
            changes, "testapp", 0, 0, name="author", table=None
        )

    def test_alter_db_table_no_changes(self):
        """
        Alter_db_table doesn't generate a migration if no changes have been made.
        """
        changes = self.get_changes(
            [self.author_with_db_table_options], [self.author_with_db_table_options]
        )
        # Right number of migrations?
        self.assertEqual(len(changes), 0)

    def test_keep_db_table_with_model_change(self):
        """
        Tests when model changes but db_table stays as-is, autodetector must not
        create more than one operation.
        """
        changes = self.get_changes(
            [self.author_with_db_table_options],
            [self.author_renamed_with_db_table_options],
            MigrationQuestioner({"ask_rename_model": True}),
        )
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["RenameModel"])
        self.assertOperationAttributes(
            changes, "testapp", 0, 0, old_name="Author", new_name="NewAuthor"
        )

    def test_alter_db_table_with_model_change(self):
        """
        Tests when model and db_table changes, autodetector must create two
        operations.
        """
        changes = self.get_changes(
            [self.author_with_db_table_options],
            [self.author_renamed_with_new_db_table_options],
            MigrationQuestioner({"ask_rename_model": True}),
        )
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(
            changes, "testapp", 0, ["RenameModel", "AlterModelTable"]
        )
        self.assertOperationAttributes(
            changes, "testapp", 0, 0, old_name="Author", new_name="NewAuthor"
        )
        self.assertOperationAttributes(
            changes, "testapp", 0, 1, name="newauthor", table="author_three"
        )

    def test_alter_db_table_comment_add(self):
        changes = self.get_changes(
            [self.author_empty], [self.author_with_db_table_comment]
        )
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["AlterModelTableComment"])
        self.assertOperationAttributes(
            changes, "testapp", 0, 0, name="author", table_comment="Table comment"
        )

    def test_alter_db_table_comment_change(self):
        author_with_new_db_table_comment = ModelState(
            "testapp",
            "Author",
            [
                ("id", models.AutoField(primary_key=True)),
            ],
            {"db_table_comment": "New table comment"},
        )
        changes = self.get_changes(
            [self.author_with_db_table_comment],
            [author_with_new_db_table_comment],
        )
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["AlterModelTableComment"])
        self.assertOperationAttributes(
            changes,
            "testapp",
            0,
            0,
            name="author",
            table_comment="New table comment",
        )

    def test_alter_db_table_comment_remove(self):
        changes = self.get_changes(
            [self.author_with_db_table_comment],
            [self.author_empty],
        )
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["AlterModelTableComment"])
        self.assertOperationAttributes(
            changes, "testapp", 0, 0, name="author", db_table_comment=None
        )

    def test_alter_db_table_comment_no_changes(self):
        changes = self.get_changes(
            [self.author_with_db_table_comment],
            [self.author_with_db_table_comment],
        )
        self.assertNumberMigrations(changes, "testapp", 0)

    def test_identical_regex_doesnt_alter(self):
        from_state = ModelState(
            "testapp",
            "model",
            [
                (
                    "id",
                    models.AutoField(
                        primary_key=True,
                        validators=[
                            RegexValidator(
                                re.compile("^[-a-zA-Z0-9_]+\\Z"),
                                "Enter a valid “slug” consisting of letters, numbers, "
                                "underscores or hyphens.",
                                "invalid",
                            )
                        ],
                    ),
                )
            ],
        )
        to_state = ModelState(
            "testapp",
            "model",
            [("id", models.AutoField(primary_key=True, validators=[validate_slug]))],
        )
        changes = self.get_changes([from_state], [to_state])
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 0)

    def test_different_regex_does_alter(self):
        from_state = ModelState(
            "testapp",
            "model",
            [
                (
                    "id",
                    models.AutoField(
                        primary_key=True,
                        validators=[
                            RegexValidator(
                                re.compile("^[a-z]+\\Z", 32),
                                "Enter a valid “slug” consisting of letters, numbers, "
                                "underscores or hyphens.",
                                "invalid",
                            )
                        ],
                    ),
                )
            ],
        )
        to_state = ModelState(
            "testapp",
            "model",
            [("id", models.AutoField(primary_key=True, validators=[validate_slug]))],
        )
        changes = self.get_changes([from_state], [to_state])
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["AlterField"])

    def test_alter_regex_string_to_compiled_regex(self):
        regex_string = "^[a-z]+$"
        from_state = ModelState(
            "testapp",
            "model",
            [
                (
                    "id",
                    models.AutoField(
                        primary_key=True, validators=[RegexValidator(regex_string)]
                    ),
                )
            ],
        )
        to_state = ModelState(
            "testapp",
            "model",
            [
                (
                    "id",
                    models.AutoField(
                        primary_key=True,
                        validators=[RegexValidator(re.compile(regex_string))],
                    ),
                )
            ],
        )
        changes = self.get_changes([from_state], [to_state])
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["AlterField"])

    def test_empty_unique_together(self):
        """Empty unique_together shouldn't generate a migration."""
        # Explicitly testing for not specified, since this is the case after
        # a CreateModel operation w/o any definition on the original model
        model_state_not_specified = ModelState(
            "a", "model", [("id", models.AutoField(primary_key=True))]
        )
        # Explicitly testing for None, since this was the issue in #23452 after
        # an AlterUniqueTogether operation with e.g. () as value
        model_state_none = ModelState(
            "a",
            "model",
            [("id", models.AutoField(primary_key=True))],
            {
                "unique_together": None,
            },
        )
        # Explicitly testing for the empty set, since we now always have sets.
        # During removal (('col1', 'col2'),) --> () this becomes set([])
        model_state_empty = ModelState(
            "a",
            "model",
            [("id", models.AutoField(primary_key=True))],
            {
                "unique_together": set(),
            },
        )

        def test(from_state, to_state, msg):
            changes = self.get_changes([from_state], [to_state])
            if changes:
                ops = ", ".join(
                    o.__class__.__name__ for o in changes["a"][0].operations
                )
                self.fail("Created operation(s) %s from %s" % (ops, msg))

        tests = (
            (
                model_state_not_specified,
                model_state_not_specified,
                '"not specified" to "not specified"',
            ),
            (model_state_not_specified, model_state_none, '"not specified" to "None"'),
            (
                model_state_not_specified,
                model_state_empty,
                '"not specified" to "empty"',
            ),
            (model_state_none, model_state_not_specified, '"None" to "not specified"'),
            (model_state_none, model_state_none, '"None" to "None"'),
            (model_state_none, model_state_empty, '"None" to "empty"'),
            (
                model_state_empty,
                model_state_not_specified,
                '"empty" to "not specified"',
            ),
            (model_state_empty, model_state_none, '"empty" to "None"'),
            (model_state_empty, model_state_empty, '"empty" to "empty"'),
        )

        for t in tests:
            test(*t)

    def test_create_model_with_indexes(self):
        """Test creation of new model with indexes already defined."""
        author = ModelState(
            "otherapp",
            "Author",
            [
                ("id", models.AutoField(primary_key=True)),
                ("name", models.CharField(max_length=200)),
            ],
            {
                "indexes": [
                    models.Index(fields=["name"], name="create_model_with_indexes_idx")
                ]
            },
        )
        changes = self.get_changes([], [author])
        added_index = models.Index(
            fields=["name"], name="create_model_with_indexes_idx"
        )
        # Right number of migrations?
        self.assertEqual(len(changes["otherapp"]), 1)
        # Right number of actions?
        migration = changes["otherapp"][0]
        self.assertEqual(len(migration.operations), 2)
        # Right actions order?
        self.assertOperationTypes(changes, "otherapp", 0, ["CreateModel", "AddIndex"])
        self.assertOperationAttributes(changes, "otherapp", 0, 0, name="Author")
        self.assertOperationAttributes(
            changes, "otherapp", 0, 1, model_name="author", index=added_index
        )

    def test_add_indexes(self):
        """Test change detection of new indexes."""
        changes = self.get_changes(
            [self.author_empty, self.book], [self.author_empty, self.book_indexes]
        )
        self.assertNumberMigrations(changes, "otherapp", 1)
        self.assertOperationTypes(changes, "otherapp", 0, ["AddIndex"])
        added_index = models.Index(
            fields=["author", "title"], name="book_title_author_idx"
        )
        self.assertOperationAttributes(
            changes, "otherapp", 0, 0, model_name="book", index=added_index
        )

    def test_remove_indexes(self):
        """Test change detection of removed indexes."""
        changes = self.get_changes(
            [self.author_empty, self.book_indexes], [self.author_empty, self.book]
        )
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "otherapp", 1)
        self.assertOperationTypes(changes, "otherapp", 0, ["RemoveIndex"])
        self.assertOperationAttributes(
            changes, "otherapp", 0, 0, model_name="book", name="book_title_author_idx"
        )

    def test_rename_indexes(self):
        book_renamed_indexes = ModelState(
            "otherapp",
            "Book",
            [
                ("id", models.AutoField(primary_key=True)),
                ("author", models.ForeignKey("testapp.Author", models.CASCADE)),
                ("title", models.CharField(max_length=200)),
            ],
            {
                "indexes": [
                    models.Index(
                        fields=["author", "title"], name="renamed_book_title_author_idx"
                    )
                ],
            },
        )
        changes = self.get_changes(
            [self.author_empty, self.book_indexes],
            [self.author_empty, book_renamed_indexes],
        )
        self.assertNumberMigrations(changes, "otherapp", 1)
        self.assertOperationTypes(changes, "otherapp", 0, ["RenameIndex"])
        self.assertOperationAttributes(
            changes,
            "otherapp",
            0,
            0,
            model_name="book",
            new_name="renamed_book_title_author_idx",
            old_name="book_title_author_idx",
        )

    def test_order_fields_indexes(self):
        """Test change detection of reordering of fields in indexes."""
        changes = self.get_changes(
            [self.author_empty, self.book_indexes],
            [self.author_empty, self.book_unordered_indexes],
        )
        self.assertNumberMigrations(changes, "otherapp", 1)
        self.assertOperationTypes(changes, "otherapp", 0, ["RemoveIndex", "AddIndex"])
        self.assertOperationAttributes(
            changes, "otherapp", 0, 0, model_name="book", name="book_title_author_idx"
        )
        added_index = models.Index(
            fields=["title", "author"], name="book_author_title_idx"
        )
        self.assertOperationAttributes(
            changes, "otherapp", 0, 1, model_name="book", index=added_index
        )

    def test_create_model_with_check_constraint(self):
        """Test creation of new model with constraints already defined."""
        author = ModelState(
            "otherapp",
            "Author",
            [
                ("id", models.AutoField(primary_key=True)),
                ("name", models.CharField(max_length=200)),
            ],
            {
                "constraints": [
                    models.CheckConstraint(
                        check=models.Q(name__contains="Bob"), name="name_contains_bob"
                    )
                ]
            },
        )
        changes = self.get_changes([], [author])
        added_constraint = models.CheckConstraint(
            check=models.Q(name__contains="Bob"), name="name_contains_bob"
        )
        # Right number of migrations?
        self.assertEqual(len(changes["otherapp"]), 1)
        # Right number of actions?
        migration = changes["otherapp"][0]
        self.assertEqual(len(migration.operations), 2)
        # Right actions order?
        self.assertOperationTypes(
            changes, "otherapp", 0, ["CreateModel", "AddConstraint"]
        )
        self.assertOperationAttributes(changes, "otherapp", 0, 0, name="Author")
        self.assertOperationAttributes(
            changes, "otherapp", 0, 1, model_name="author", constraint=added_constraint
        )

    def test_add_constraints(self):
        """Test change detection of new constraints."""
        changes = self.get_changes(
            [self.author_name], [self.author_name_check_constraint]
        )
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["AddConstraint"])
        added_constraint = models.CheckConstraint(
            check=models.Q(name__contains="Bob"), name="name_contains_bob"
        )
        self.assertOperationAttributes(
            changes, "testapp", 0, 0, model_name="author", constraint=added_constraint
        )

    def test_remove_constraints(self):
        """Test change detection of removed constraints."""
        changes = self.get_changes(
            [self.author_name_check_constraint], [self.author_name]
        )
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["RemoveConstraint"])
        self.assertOperationAttributes(
            changes, "testapp", 0, 0, model_name="author", name="name_contains_bob"
        )

    def test_add_unique_together(self):
        """Tests unique_together detection."""
        changes = self.get_changes(
            [self.author_empty, self.book],
            [self.author_empty, self.book_unique_together],
        )
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "otherapp", 1)
        self.assertOperationTypes(changes, "otherapp", 0, ["AlterUniqueTogether"])
        self.assertOperationAttributes(
            changes,
            "otherapp",
            0,
            0,
            name="book",
            unique_together={("author", "title")},
        )

    def test_remove_unique_together(self):
        """Tests unique_together detection."""
        changes = self.get_changes(
            [self.author_empty, self.book_unique_together],
            [self.author_empty, self.book],
        )
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "otherapp", 1)
        self.assertOperationTypes(changes, "otherapp", 0, ["AlterUniqueTogether"])
        self.assertOperationAttributes(
            changes, "otherapp", 0, 0, name="book", unique_together=set()
        )

    def test_unique_together_remove_fk(self):
        """Tests unique_together and field removal detection & ordering"""
        changes = self.get_changes(
            [self.author_empty, self.book_unique_together],
            [self.author_empty, self.book_with_no_author],
        )
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "otherapp", 1)
        self.assertOperationTypes(
            changes,
            "otherapp",
            0,
            ["AlterUniqueTogether", "RemoveField"],
        )
        self.assertOperationAttributes(
            changes, "otherapp", 0, 0, name="book", unique_together=set()
        )
        self.assertOperationAttributes(
            changes, "otherapp", 0, 1, model_name="book", name="author"
        )

    def test_unique_together_no_changes(self):
        """
        unique_together doesn't generate a migration if no
        changes have been made.
        """
        changes = self.get_changes(
            [self.author_empty, self.book_unique_together],
            [self.author_empty, self.book_unique_together],
        )
        # Right number of migrations?
        self.assertEqual(len(changes), 0)

    def test_unique_together_ordering(self):
        """
        unique_together also triggers on ordering changes.
        """
        changes = self.get_changes(
            [self.author_empty, self.book_unique_together],
            [self.author_empty, self.book_unique_together_2],
        )
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "otherapp", 1)
        self.assertOperationTypes(
            changes,
            "otherapp",
            0,
            ["AlterUniqueTogether"],
        )
        self.assertOperationAttributes(
            changes,
            "otherapp",
            0,
            0,
            name="book",
            unique_together={("title", "author")},
        )

    def test_add_field_and_unique_together(self):
        """
        Added fields will be created before using them in unique_together.
        """
        changes = self.get_changes(
            [self.author_empty, self.book],
            [self.author_empty, self.book_unique_together_3],
        )
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "otherapp", 1)
        self.assertOperationTypes(
            changes,
            "otherapp",
            0,
            ["AddField", "AlterUniqueTogether"],
        )
        self.assertOperationAttributes(
            changes,
            "otherapp",
            0,
            1,
            name="book",
            unique_together={("title", "newfield")},
        )

    def test_create_model_and_unique_together(self):
        author = ModelState(
            "otherapp",
            "Author",
            [
                ("id", models.AutoField(primary_key=True)),
                ("name", models.CharField(max_length=200)),
            ],
        )
        book_with_author = ModelState(
            "otherapp",
            "Book",
            [
                ("id", models.AutoField(primary_key=True)),
                ("author", models.ForeignKey("otherapp.Author", models.CASCADE)),
                ("title", models.CharField(max_length=200)),
            ],
            {
                "unique_together": {("title", "author")},
            },
        )
        changes = self.get_changes(
            [self.book_with_no_author], [author, book_with_author]
        )
        # Right number of migrations?
        self.assertEqual(len(changes["otherapp"]), 1)
        # Right number of actions?
        migration = changes["otherapp"][0]
        self.assertEqual(len(migration.operations), 3)
        # Right actions order?
        self.assertOperationTypes(
            changes,
            "otherapp",
            0,
            ["CreateModel", "AddField", "AlterUniqueTogether"],
        )

    def test_remove_field_and_unique_together(self):
        """
        Removed fields will be removed after updating unique_together.
        """
        changes = self.get_changes(
            [self.author_empty, self.book_unique_together_3],
            [self.author_empty, self.book_unique_together],
        )
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "otherapp", 1)
        self.assertOperationTypes(
            changes,
            "otherapp",
            0,
            ["AlterUniqueTogether", "RemoveField"],
        )
        self.assertOperationAttributes(
            changes,
            "otherapp",
            0,
            0,
            name="book",
            unique_together={("author", "title")},
        )
        self.assertOperationAttributes(
            changes,
            "otherapp",
            0,
            1,
            model_name="book",
            name="newfield",
        )

    def test_alter_field_and_unique_together(self):
        """Fields are altered after deleting some unique_together."""
        initial_author = ModelState(
            "testapp",
            "Author",
            [
                ("id", models.AutoField(primary_key=True)),
                ("name", models.CharField(max_length=200)),
                ("age", models.IntegerField(db_index=True)),
            ],
            {
                "unique_together": {("name",)},
            },
        )
        author_reversed_constraints = ModelState(
            "testapp",
            "Author",
            [
                ("id", models.AutoField(primary_key=True)),
                ("name", models.CharField(max_length=200, unique=True)),
                ("age", models.IntegerField()),
            ],
            {
                "unique_together": {("age",)},
            },
        )
        changes = self.get_changes([initial_author], [author_reversed_constraints])

        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(
            changes,
            "testapp",
            0,
            [
                "AlterUniqueTogether",
                "AlterField",
                "AlterField",
                "AlterUniqueTogether",
            ],
        )
        self.assertOperationAttributes(
            changes,
            "testapp",
            0,
            0,
            name="author",
            unique_together=set(),
        )
        self.assertOperationAttributes(
            changes,
            "testapp",
            0,
            1,
            model_name="author",
            name="age",
        )
        self.assertOperationAttributes(
            changes,
            "testapp",
            0,
            2,
            model_name="author",
            name="name",
        )
        self.assertOperationAttributes(
            changes,
            "testapp",
            0,
            3,
            name="author",
            unique_together={("age",)},
        )

    def test_partly_alter_unique_together_increase(self):
        initial_author = ModelState(
            "testapp",
            "Author",
            [
                ("id", models.AutoField(primary_key=True)),
                ("name", models.CharField(max_length=200)),
                ("age", models.IntegerField()),
            ],
            {
                "unique_together": {("name",)},
            },
        )
        author_new_constraints = ModelState(
            "testapp",
            "Author",
            [
                ("id", models.AutoField(primary_key=True)),
                ("name", models.CharField(max_length=200)),
                ("age", models.IntegerField()),
            ],
            {
                "unique_together": {("name",), ("age",)},
            },
        )
        changes = self.get_changes([initial_author], [author_new_constraints])

        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(
            changes,
            "testapp",
            0,
            ["AlterUniqueTogether"],
        )
        self.assertOperationAttributes(
            changes,
            "testapp",
            0,
            0,
            name="author",
            unique_together={("name",), ("age",)},
        )

    def test_partly_alter_unique_together_decrease(self):
        initial_author = ModelState(
            "testapp",
            "Author",
            [
                ("id", models.AutoField(primary_key=True)),
                ("name", models.CharField(max_length=200)),
                ("age", models.IntegerField()),
            ],
            {
                "unique_together": {("name",), ("age",)},
            },
        )
        author_new_constraints = ModelState(
            "testapp",
            "Author",
            [
                ("id", models.AutoField(primary_key=True)),
                ("name", models.CharField(max_length=200)),
                ("age", models.IntegerField()),
            ],
            {
                "unique_together": {("name",)},
            },
        )
        changes = self.get_changes([initial_author], [author_new_constraints])

        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(
            changes,
            "testapp",
            0,
            ["AlterUniqueTogether"],
        )
        self.assertOperationAttributes(
            changes,
            "testapp",
            0,
            0,
            name="author",
            unique_together={("name",)},
        )

    def test_rename_field_and_unique_together(self):
        """Fields are renamed before updating unique_together."""
        changes = self.get_changes(
            [self.author_empty, self.book_unique_together_3],
            [self.author_empty, self.book_unique_together_4],
            MigrationQuestioner({"ask_rename": True}),
        )
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "otherapp", 1)
        self.assertOperationTypes(
            changes,
            "otherapp",
            0,
            ["RenameField", "AlterUniqueTogether"],
        )
        self.assertOperationAttributes(
            changes,
            "otherapp",
            0,
            1,
            name="book",
            unique_together={("title", "newfield2")},
        )

    def test_proxy(self):
        """The autodetector correctly deals with proxy models."""
        # First, we test adding a proxy model
        changes = self.get_changes(
            [self.author_empty], [self.author_empty, self.author_proxy]
        )
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["CreateModel"])
        self.assertOperationAttributes(
            changes,
            "testapp",
            0,
            0,
            name="AuthorProxy",
            options={"proxy": True, "indexes": [], "constraints": []},
        )
        # Now, we test turning a proxy model into a non-proxy model
        # It should delete the proxy then make the real one
        changes = self.get_changes(
            [self.author_empty, self.author_proxy],
            [self.author_empty, self.author_proxy_notproxy],
        )
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["DeleteModel", "CreateModel"])
        self.assertOperationAttributes(changes, "testapp", 0, 0, name="AuthorProxy")
        self.assertOperationAttributes(
            changes, "testapp", 0, 1, name="AuthorProxy", options={}
        )

    def test_proxy_non_model_parent(self):
        class Mixin:
            pass

        author_proxy_non_model_parent = ModelState(
            "testapp",
            "AuthorProxy",
            [],
            {"proxy": True},
            (Mixin, "testapp.author"),
        )
        changes = self.get_changes(
            [self.author_empty],
            [self.author_empty, author_proxy_non_model_parent],
        )
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["CreateModel"])
        self.assertOperationAttributes(
            changes,
            "testapp",
            0,
            0,
            name="AuthorProxy",
            options={"proxy": True, "indexes": [], "constraints": []},
            bases=(Mixin, "testapp.author"),
        )

    def test_proxy_custom_pk(self):
        """
        #23415 - The autodetector must correctly deal with custom FK on proxy
        models.
        """
        # First, we test the default pk field name
        changes = self.get_changes(
            [], [self.author_empty, self.author_proxy_third, self.book_proxy_fk]
        )
        # The model the FK is pointing from and to.
        self.assertEqual(
            changes["otherapp"][0].operations[0].fields[2][1].remote_field.model,
            "thirdapp.AuthorProxy",
        )
        # Now, we test the custom pk field name
        changes = self.get_changes(
            [], [self.author_custom_pk, self.author_proxy_third, self.book_proxy_fk]
        )
        # The model the FK is pointing from and to.
        self.assertEqual(
            changes["otherapp"][0].operations[0].fields[2][1].remote_field.model,
            "thirdapp.AuthorProxy",
        )

    def test_proxy_to_mti_with_fk_to_proxy(self):
        # First, test the pk table and field name.
        to_state = self.make_project_state(
            [self.author_empty, self.author_proxy_third, self.book_proxy_fk],
        )
        changes = self.get_changes([], to_state)
        fk_field = changes["otherapp"][0].operations[0].fields[2][1]
        self.assertEqual(
            to_state.get_concrete_model_key(fk_field.remote_field.model),
            ("testapp", "author"),
        )
        self.assertEqual(fk_field.remote_field.model, "thirdapp.AuthorProxy")

        # Change AuthorProxy to use MTI.
        from_state = to_state.clone()
        to_state = self.make_project_state(
            [self.author_empty, self.author_proxy_third_notproxy, self.book_proxy_fk],
        )
        changes = self.get_changes(from_state, to_state)
        # Right number/type of migrations for the AuthorProxy model?
        self.assertNumberMigrations(changes, "thirdapp", 1)
        self.assertOperationTypes(
            changes, "thirdapp", 0, ["DeleteModel", "CreateModel"]
        )
        # Right number/type of migrations for the Book model with a FK to
        # AuthorProxy?
        self.assertNumberMigrations(changes, "otherapp", 1)
        self.assertOperationTypes(changes, "otherapp", 0, ["AlterField"])
        # otherapp should depend on thirdapp.
        self.assertMigrationDependencies(
            changes, "otherapp", 0, [("thirdapp", "auto_1")]
        )
        # Now, test the pk table and field name.
        fk_field = changes["otherapp"][0].operations[0].field
        self.assertEqual(
            to_state.get_concrete_model_key(fk_field.remote_field.model),
            ("thirdapp", "authorproxy"),
        )
        self.assertEqual(fk_field.remote_field.model, "thirdapp.AuthorProxy")

    def test_proxy_to_mti_with_fk_to_proxy_proxy(self):
        # First, test the pk table and field name.
        to_state = self.make_project_state(
            [
                self.author_empty,
                self.author_proxy,
                self.author_proxy_proxy,
                self.book_proxy_proxy_fk,
            ]
        )
        changes = self.get_changes([], to_state)
        fk_field = changes["otherapp"][0].operations[0].fields[1][1]
        self.assertEqual(
            to_state.get_concrete_model_key(fk_field.remote_field.model),
            ("testapp", "author"),
        )
        self.assertEqual(fk_field.remote_field.model, "testapp.AAuthorProxyProxy")

        # Change AuthorProxy to use MTI. FK still points to AAuthorProxyProxy,
        # a proxy of AuthorProxy.
        from_state = to_state.clone()
        to_state = self.make_project_state(
            [
                self.author_empty,
                self.author_proxy_notproxy,
                self.author_proxy_proxy,
                self.book_proxy_proxy_fk,
            ]
        )
        changes = self.get_changes(from_state, to_state)
        # Right number/type of migrations for the AuthorProxy model?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["DeleteModel", "CreateModel"])
        # Right number/type of migrations for the Book model with a FK to
        # AAuthorProxyProxy?
        self.assertNumberMigrations(changes, "otherapp", 1)
        self.assertOperationTypes(changes, "otherapp", 0, ["AlterField"])
        # otherapp should depend on testapp.
        self.assertMigrationDependencies(
            changes, "otherapp", 0, [("testapp", "auto_1")]
        )
        # Now, test the pk table and field name.
        fk_field = changes["otherapp"][0].operations[0].field
        self.assertEqual(
            to_state.get_concrete_model_key(fk_field.remote_field.model),
            ("testapp", "authorproxy"),
        )
        self.assertEqual(fk_field.remote_field.model, "testapp.AAuthorProxyProxy")

    def test_unmanaged_create(self):
        """The autodetector correctly deals with managed models."""
        # First, we test adding an unmanaged model
        changes = self.get_changes(
            [self.author_empty], [self.author_empty, self.author_unmanaged]
        )
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["CreateModel"])
        self.assertOperationAttributes(
            changes, "testapp", 0, 0, name="AuthorUnmanaged", options={"managed": False}
        )

    def test_unmanaged_delete(self):
        changes = self.get_changes(
            [self.author_empty, self.author_unmanaged], [self.author_empty]
        )
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["DeleteModel"])

    def test_unmanaged_to_managed(self):
        # Now, we test turning an unmanaged model into a managed model
        changes = self.get_changes(
            [self.author_empty, self.author_unmanaged],
            [self.author_empty, self.author_unmanaged_managed],
        )
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["AlterModelOptions"])
        self.assertOperationAttributes(
            changes, "testapp", 0, 0, name="authorunmanaged", options={}
        )

    def test_managed_to_unmanaged(self):
        # Now, we turn managed to unmanaged.
        changes = self.get_changes(
            [self.author_empty, self.author_unmanaged_managed],
            [self.author_empty, self.author_unmanaged],
        )
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["AlterModelOptions"])
        self.assertOperationAttributes(
            changes, "testapp", 0, 0, name="authorunmanaged", options={"managed": False}
        )

    def test_unmanaged_custom_pk(self):
        """
        #23415 - The autodetector must correctly deal with custom FK on
        unmanaged models.
        """
        # First, we test the default pk field name
        changes = self.get_changes([], [self.author_unmanaged_default_pk, self.book])
        # The model the FK on the book model points to.
        fk_field = changes["otherapp"][0].operations[0].fields[2][1]
        self.assertEqual(fk_field.remote_field.model, "testapp.Author")
        # Now, we test the custom pk field name
        changes = self.get_changes([], [self.author_unmanaged_custom_pk, self.book])
        # The model the FK on the book model points to.
        fk_field = changes["otherapp"][0].operations[0].fields[2][1]
        self.assertEqual(fk_field.remote_field.model, "testapp.Author")

    @override_settings(AUTH_USER_MODEL="thirdapp.CustomUser")
    def test_swappable(self):
        with isolate_lru_cache(apps.get_swappable_settings_name):
            changes = self.get_changes(
                [self.custom_user], [self.custom_user, self.author_with_custom_user]
            )
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["CreateModel"])
        self.assertOperationAttributes(changes, "testapp", 0, 0, name="Author")
        self.assertMigrationDependencies(
            changes, "testapp", 0, [("__setting__", "AUTH_USER_MODEL")]
        )

    def test_swappable_lowercase(self):
        model_state = ModelState(
            "testapp",
            "Document",
            [
                ("id", models.AutoField(primary_key=True)),
                (
                    "owner",
                    models.ForeignKey(
                        settings.AUTH_USER_MODEL.lower(),
                        models.CASCADE,
                    ),
                ),
            ],
        )
        with isolate_lru_cache(apps.get_swappable_settings_name):
            changes = self.get_changes([], [model_state])
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["CreateModel"])
        self.assertOperationAttributes(changes, "testapp", 0, 0, name="Document")
        self.assertMigrationDependencies(
            changes,
            "testapp",
            0,
            [("__setting__", "AUTH_USER_MODEL")],
        )

    @override_settings(AUTH_USER_MODEL="thirdapp.CustomUser")
    def test_swappable_many_to_many_model_case(self):
        document_lowercase = ModelState(
            "testapp",
            "Document",
            [
                ("id", models.AutoField(primary_key=True)),
                ("owners", models.ManyToManyField(settings.AUTH_USER_MODEL.lower())),
            ],
        )
        document = ModelState(
            "testapp",
            "Document",
            [
                ("id", models.AutoField(primary_key=True)),
                ("owners", models.ManyToManyField(settings.AUTH_USER_MODEL)),
            ],
        )
        with isolate_lru_cache(apps.get_swappable_settings_name):
            changes = self.get_changes(
                [self.custom_user, document_lowercase],
                [self.custom_user, document],
            )
        self.assertEqual(len(changes), 0)

    def test_swappable_changed(self):
        with isolate_lru_cache(apps.get_swappable_settings_name):
            before = self.make_project_state([self.custom_user, self.author_with_user])
            with override_settings(AUTH_USER_MODEL="thirdapp.CustomUser"):
                after = self.make_project_state(
                    [self.custom_user, self.author_with_custom_user]
                )
            autodetector = MigrationAutodetector(before, after)
            changes = autodetector._detect_changes()
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["AlterField"])
        self.assertOperationAttributes(
            changes, "testapp", 0, 0, model_name="author", name="user"
        )
        fk_field = changes["testapp"][0].operations[0].field
        self.assertEqual(fk_field.remote_field.model, "thirdapp.CustomUser")

    def test_add_field_with_default(self):
        """#22030 - Adding a field with a default should work."""
        changes = self.get_changes([self.author_empty], [self.author_name_default])
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["AddField"])
        self.assertOperationAttributes(changes, "testapp", 0, 0, name="name")

    def test_custom_deconstructible(self):
        """
        Two instances which deconstruct to the same value aren't considered a
        change.
        """
        changes = self.get_changes(
            [self.author_name_deconstructible_1], [self.author_name_deconstructible_2]
        )
        # Right number of migrations?
        self.assertEqual(len(changes), 0)

    def test_deconstruct_field_kwarg(self):
        """Field instances are handled correctly by nested deconstruction."""
        changes = self.get_changes(
            [self.author_name_deconstructible_3], [self.author_name_deconstructible_4]
        )
        self.assertEqual(changes, {})

    def test_deconstructible_list(self):
        """Nested deconstruction descends into lists."""
        # When lists contain items that deconstruct to identical values, those lists
        # should be considered equal for the purpose of detecting state changes
        # (even if the original items are unequal).
        changes = self.get_changes(
            [self.author_name_deconstructible_list_1],
            [self.author_name_deconstructible_list_2],
        )
        self.assertEqual(changes, {})
        # Legitimate differences within the deconstructed lists should be reported
        # as a change
        changes = self.get_changes(
            [self.author_name_deconstructible_list_1],
            [self.author_name_deconstructible_list_3],
        )
        self.assertEqual(len(changes), 1)

    def test_deconstructible_tuple(self):
        """Nested deconstruction descends into tuples."""
        # When tuples contain items that deconstruct to identical values, those tuples
        # should be considered equal for the purpose of detecting state changes
        # (even if the original items are unequal).
        changes = self.get_changes(
            [self.author_name_deconstructible_tuple_1],
            [self.author_name_deconstructible_tuple_2],
        )
        self.assertEqual(changes, {})
        # Legitimate differences within the deconstructed tuples should be reported
        # as a change
        changes = self.get_changes(
            [self.author_name_deconstructible_tuple_1],
            [self.author_name_deconstructible_tuple_3],
        )
        self.assertEqual(len(changes), 1)

    def test_deconstructible_dict(self):
        """Nested deconstruction descends into dict values."""
        # When dicts contain items whose values deconstruct to identical values,
        # those dicts should be considered equal for the purpose of detecting
        # state changes (even if the original values are unequal).
        changes = self.get_changes(
            [self.author_name_deconstructible_dict_1],
            [self.author_name_deconstructible_dict_2],
        )
        self.assertEqual(changes, {})
        # Legitimate differences within the deconstructed dicts should be reported
        # as a change
        changes = self.get_changes(
            [self.author_name_deconstructible_dict_1],
            [self.author_name_deconstructible_dict_3],
        )
        self.assertEqual(len(changes), 1)

    def test_nested_deconstructible_objects(self):
        """
        Nested deconstruction is applied recursively to the args/kwargs of
        deconstructed objects.
        """
        # If the items within a deconstructed object's args/kwargs have the same
        # deconstructed values - whether or not the items themselves are different
        # instances - then the object as a whole is regarded as unchanged.
        changes = self.get_changes(
            [self.author_name_nested_deconstructible_1],
            [self.author_name_nested_deconstructible_2],
        )
        self.assertEqual(changes, {})
        # Differences that exist solely within the args list of a deconstructed object
        # should be reported as changes
        changes = self.get_changes(
            [self.author_name_nested_deconstructible_1],
            [self.author_name_nested_deconstructible_changed_arg],
        )
        self.assertEqual(len(changes), 1)
        # Additional args should also be reported as a change
        changes = self.get_changes(
            [self.author_name_nested_deconstructible_1],
            [self.author_name_nested_deconstructible_extra_arg],
        )
        self.assertEqual(len(changes), 1)
        # Differences that exist solely within the kwargs dict of a deconstructed object
        # should be reported as changes
        changes = self.get_changes(
            [self.author_name_nested_deconstructible_1],
            [self.author_name_nested_deconstructible_changed_kwarg],
        )
        self.assertEqual(len(changes), 1)
        # Additional kwargs should also be reported as a change
        changes = self.get_changes(
            [self.author_name_nested_deconstructible_1],
            [self.author_name_nested_deconstructible_extra_kwarg],
        )
        self.assertEqual(len(changes), 1)

    def test_deconstruct_type(self):
        """
        #22951 -- Uninstantiated classes with deconstruct are correctly returned
        by deep_deconstruct during serialization.
        """
        author = ModelState(
            "testapp",
            "Author",
            [
                ("id", models.AutoField(primary_key=True)),
                (
                    "name",
                    models.CharField(
                        max_length=200,
                        # IntegerField intentionally not instantiated.
                        default=models.IntegerField,
                    ),
                ),
            ],
        )
        changes = self.get_changes([], [author])
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["CreateModel"])

    def test_replace_string_with_foreignkey(self):
        """
        #22300 - Adding an FK in the same "spot" as a deleted CharField should
        work.
        """
        changes = self.get_changes(
            [self.author_with_publisher_string],
            [self.author_with_publisher, self.publisher],
        )
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(
            changes, "testapp", 0, ["CreateModel", "RemoveField", "AddField"]
        )
        self.assertOperationAttributes(changes, "testapp", 0, 0, name="Publisher")
        self.assertOperationAttributes(changes, "testapp", 0, 1, name="publisher_name")
        self.assertOperationAttributes(changes, "testapp", 0, 2, name="publisher")

    def test_foreign_key_removed_before_target_model(self):
        """
        Removing an FK and the model it targets in the same change must remove
        the FK field before the model to maintain consistency.
        """
        changes = self.get_changes(
            [self.author_with_publisher, self.publisher], [self.author_name]
        )  # removes both the model and FK
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["RemoveField", "DeleteModel"])
        self.assertOperationAttributes(changes, "testapp", 0, 0, name="publisher")
        self.assertOperationAttributes(changes, "testapp", 0, 1, name="Publisher")

    @mock.patch(
        "django.db.migrations.questioner.MigrationQuestioner.ask_not_null_addition",
        side_effect=AssertionError("Should not have prompted for not null addition"),
    )
    def test_add_many_to_many(self, mocked_ask_method):
        """#22435 - Adding a ManyToManyField should not prompt for a default."""
        changes = self.get_changes(
            [self.author_empty, self.publisher], [self.author_with_m2m, self.publisher]
        )
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["AddField"])
        self.assertOperationAttributes(changes, "testapp", 0, 0, name="publishers")

    def test_alter_many_to_many(self):
        changes = self.get_changes(
            [self.author_with_m2m, self.publisher],
            [self.author_with_m2m_blank, self.publisher],
        )
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["AlterField"])
        self.assertOperationAttributes(changes, "testapp", 0, 0, name="publishers")

    def test_create_with_through_model(self):
        """
        Adding a m2m with a through model and the models that use it should be
        ordered correctly.
        """
        changes = self.get_changes(
            [], [self.author_with_m2m_through, self.publisher, self.contract]
        )
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(
            changes,
            "testapp",
            0,
            [
                "CreateModel",
                "CreateModel",
                "CreateModel",
                "AddField",
            ],
        )
        self.assertOperationAttributes(changes, "testapp", 0, 0, name="Author")
        self.assertOperationAttributes(changes, "testapp", 0, 1, name="Publisher")
        self.assertOperationAttributes(changes, "testapp", 0, 2, name="Contract")
        self.assertOperationAttributes(
            changes, "testapp", 0, 3, model_name="author", name="publishers"
        )

    def test_create_with_through_model_separate_apps(self):
        author_with_m2m_through = ModelState(
            "authors",
            "Author",
            [
                ("id", models.AutoField(primary_key=True)),
                (
                    "publishers",
                    models.ManyToManyField(
                        "testapp.Publisher", through="contract.Contract"
                    ),
                ),
            ],
        )
        contract = ModelState(
            "contract",
            "Contract",
            [
                ("id", models.AutoField(primary_key=True)),
                ("author", models.ForeignKey("authors.Author", models.CASCADE)),
                ("publisher", models.ForeignKey("testapp.Publisher", models.CASCADE)),
            ],
        )
        changes = self.get_changes(
            [], [author_with_m2m_through, self.publisher, contract]
        )
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertNumberMigrations(changes, "contract", 1)
        self.assertNumberMigrations(changes, "authors", 2)
        self.assertMigrationDependencies(
            changes,
            "authors",
            1,
            {("authors", "auto_1"), ("contract", "auto_1"), ("testapp", "auto_1")},
        )
        self.assertOperationTypes(changes, "testapp", 0, ["CreateModel"])
        self.assertOperationAttributes(changes, "testapp", 0, 0, name="Publisher")
        self.assertOperationTypes(changes, "contract", 0, ["CreateModel"])
        self.assertOperationAttributes(changes, "contract", 0, 0, name="Contract")
        self.assertOperationTypes(changes, "authors", 0, ["CreateModel"])
        self.assertOperationTypes(changes, "authors", 1, ["AddField"])
        self.assertOperationAttributes(changes, "authors", 0, 0, name="Author")
        self.assertOperationAttributes(
            changes, "authors", 1, 0, model_name="author", name="publishers"
        )

    def test_many_to_many_removed_before_through_model(self):
        """
        Removing a ManyToManyField and the "through" model in the same change
        must remove the field before the model to maintain consistency.
        """
        changes = self.get_changes(
            [
                self.book_with_multiple_authors_through_attribution,
                self.author_name,
                self.attribution,
            ],
            [self.book_with_no_author, self.author_name],
        )
        # Remove both the through model and ManyToMany
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "otherapp", 1)
        self.assertOperationTypes(
            changes, "otherapp", 0, ["RemoveField", "DeleteModel"]
        )
        self.assertOperationAttributes(
            changes, "otherapp", 0, 0, name="authors", model_name="book"
        )
        self.assertOperationAttributes(changes, "otherapp", 0, 1, name="Attribution")

    def test_many_to_many_removed_before_through_model_2(self):
        """
        Removing a model that contains a ManyToManyField and the "through" model
        in the same change must remove the field before the model to maintain
        consistency.
        """
        changes = self.get_changes(
            [
                self.book_with_multiple_authors_through_attribution,
                self.author_name,
                self.attribution,
            ],
            [self.author_name],
        )
        # Remove both the through model and ManyToMany
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "otherapp", 1)
        self.assertOperationTypes(
            changes, "otherapp", 0, ["RemoveField", "DeleteModel", "DeleteModel"]
        )
        self.assertOperationAttributes(
            changes, "otherapp", 0, 0, name="authors", model_name="book"
        )
        self.assertOperationAttributes(changes, "otherapp", 0, 1, name="Attribution")
        self.assertOperationAttributes(changes, "otherapp", 0, 2, name="Book")

    def test_m2m_w_through_multistep_remove(self):
        """
        A model with a m2m field that specifies a "through" model cannot be
        removed in the same migration as that through model as the schema will
        pass through an inconsistent state. The autodetector should produce two
        migrations to avoid this issue.
        """
        changes = self.get_changes(
            [self.author_with_m2m_through, self.publisher, self.contract],
            [self.publisher],
        )
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(
            changes,
            "testapp",
            0,
            ["RemoveField", "RemoveField", "DeleteModel", "DeleteModel"],
        )
        self.assertOperationAttributes(
            changes, "testapp", 0, 0, name="author", model_name="contract"
        )
        self.assertOperationAttributes(
            changes, "testapp", 0, 1, name="publisher", model_name="contract"
        )
        self.assertOperationAttributes(changes, "testapp", 0, 2, name="Author")
        self.assertOperationAttributes(changes, "testapp", 0, 3, name="Contract")

    def test_concrete_field_changed_to_many_to_many(self):
        """
        #23938 - Changing a concrete field into a ManyToManyField
        first removes the concrete field and then adds the m2m field.
        """
        changes = self.get_changes(
            [self.author_with_former_m2m], [self.author_with_m2m, self.publisher]
        )
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(
            changes, "testapp", 0, ["CreateModel", "RemoveField", "AddField"]
        )
        self.assertOperationAttributes(changes, "testapp", 0, 0, name="Publisher")
        self.assertOperationAttributes(
            changes, "testapp", 0, 1, name="publishers", model_name="author"
        )
        self.assertOperationAttributes(
            changes, "testapp", 0, 2, name="publishers", model_name="author"
        )

    def test_many_to_many_changed_to_concrete_field(self):
        """
        #23938 - Changing a ManyToManyField into a concrete field
        first removes the m2m field and then adds the concrete field.
        """
        changes = self.get_changes(
            [self.author_with_m2m, self.publisher], [self.author_with_former_m2m]
        )
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(
            changes, "testapp", 0, ["RemoveField", "DeleteModel", "AddField"]
        )
        self.assertOperationAttributes(
            changes, "testapp", 0, 0, name="publishers", model_name="author"
        )
        self.assertOperationAttributes(changes, "testapp", 0, 1, name="Publisher")
        self.assertOperationAttributes(
            changes, "testapp", 0, 2, name="publishers", model_name="author"
        )
        self.assertOperationFieldAttributes(changes, "testapp", 0, 2, max_length=100)

    def test_non_circular_foreignkey_dependency_removal(self):
        """
        If two models with a ForeignKey from one to the other are removed at the
        same time, the autodetector should remove them in the correct order.
        """
        changes = self.get_changes(
            [self.author_with_publisher, self.publisher_with_author], []
        )
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(
            changes, "testapp", 0, ["RemoveField", "DeleteModel", "DeleteModel"]
        )
        self.assertOperationAttributes(
            changes, "testapp", 0, 0, name="author", model_name="publisher"
        )
        self.assertOperationAttributes(changes, "testapp", 0, 1, name="Author")
        self.assertOperationAttributes(changes, "testapp", 0, 2, name="Publisher")

    def test_alter_model_options(self):
        """Changing a model's options should make a change."""
        changes = self.get_changes([self.author_empty], [self.author_with_options])
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["AlterModelOptions"])
        self.assertOperationAttributes(
            changes,
            "testapp",
            0,
            0,
            options={
                "permissions": [("can_hire", "Can hire")],
                "verbose_name": "Authi",
            },
        )

        # Changing them back to empty should also make a change
        changes = self.get_changes([self.author_with_options], [self.author_empty])
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["AlterModelOptions"])
        self.assertOperationAttributes(
            changes, "testapp", 0, 0, name="author", options={}
        )

    def test_alter_model_options_proxy(self):
        """Changing a proxy model's options should also make a change."""
        changes = self.get_changes(
            [self.author_proxy, self.author_empty],
            [self.author_proxy_options, self.author_empty],
        )
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["AlterModelOptions"])
        self.assertOperationAttributes(
            changes,
            "testapp",
            0,
            0,
            name="authorproxy",
            options={"verbose_name": "Super Author"},
        )

    def test_set_alter_order_with_respect_to(self):
        """Setting order_with_respect_to adds a field."""
        changes = self.get_changes(
            [self.book, self.author_with_book],
            [self.book, self.author_with_book_order_wrt],
        )
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["AlterOrderWithRespectTo"])
        self.assertOperationAttributes(
            changes, "testapp", 0, 0, name="author", order_with_respect_to="book"
        )

    def test_add_alter_order_with_respect_to(self):
        """
        Setting order_with_respect_to when adding the FK too does
        things in the right order.
        """
        changes = self.get_changes(
            [self.author_name], [self.book, self.author_with_book_order_wrt]
        )
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(
            changes, "testapp", 0, ["AddField", "AlterOrderWithRespectTo"]
        )
        self.assertOperationAttributes(
            changes, "testapp", 0, 0, model_name="author", name="book"
        )
        self.assertOperationAttributes(
            changes, "testapp", 0, 1, name="author", order_with_respect_to="book"
        )

    def test_remove_alter_order_with_respect_to(self):
        """
        Removing order_with_respect_to when removing the FK too does
        things in the right order.
        """
        changes = self.get_changes(
            [self.book, self.author_with_book_order_wrt], [self.author_name]
        )
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(
            changes, "testapp", 0, ["AlterOrderWithRespectTo", "RemoveField"]
        )
        self.assertOperationAttributes(
            changes, "testapp", 0, 0, name="author", order_with_respect_to=None
        )
        self.assertOperationAttributes(
            changes, "testapp", 0, 1, model_name="author", name="book"
        )

    def test_add_model_order_with_respect_to(self):
        """
        Setting order_with_respect_to when adding the whole model
        does things in the right order.
        """
        changes = self.get_changes([], [self.book, self.author_with_book_order_wrt])
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["CreateModel"])
        self.assertOperationAttributes(
            changes,
            "testapp",
            0,
            0,
            name="Author",
            options={"order_with_respect_to": "book"},
        )
        self.assertNotIn(
            "_order",
            [name for name, field in changes["testapp"][0].operations[0].fields],
        )

    def test_add_model_order_with_respect_to_unique_together(self):
        changes = self.get_changes(
            [],
            [
                self.book,
                ModelState(
                    "testapp",
                    "Author",
                    [
                        ("id", models.AutoField(primary_key=True)),
                        ("name", models.CharField(max_length=200)),
                        ("book", models.ForeignKey("otherapp.Book", models.CASCADE)),
                    ],
                    options={
                        "order_with_respect_to": "book",
                        "unique_together": {("id", "_order")},
                    },
                ),
            ],
        )
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["CreateModel"])
        self.assertOperationAttributes(
            changes,
            "testapp",
            0,
            0,
            name="Author",
            options={
                "order_with_respect_to": "book",
                "unique_together": {("id", "_order")},
            },
        )

    def test_add_model_order_with_respect_to_index_constraint(self):
        tests = [
            (
                "AddIndex",
                {
                    "indexes": [
                        models.Index(fields=["_order"], name="book_order_idx"),
                    ]
                },
            ),
            (
                "AddConstraint",
                {
                    "constraints": [
                        models.CheckConstraint(
                            check=models.Q(_order__gt=1),
                            name="book_order_gt_1",
                        ),
                    ]
                },
            ),
        ]
        for operation, extra_option in tests:
            with self.subTest(operation=operation):
                after = ModelState(
                    "testapp",
                    "Author",
                    [
                        ("id", models.AutoField(primary_key=True)),
                        ("name", models.CharField(max_length=200)),
                        ("book", models.ForeignKey("otherapp.Book", models.CASCADE)),
                    ],
                    options={
                        "order_with_respect_to": "book",
                        **extra_option,
                    },
                )
                changes = self.get_changes([], [self.book, after])
                self.assertNumberMigrations(changes, "testapp", 1)
                self.assertOperationTypes(
                    changes,
                    "testapp",
                    0,
                    [
                        "CreateModel",
                        operation,
                    ],
                )
                self.assertOperationAttributes(
                    changes,
                    "testapp",
                    0,
                    0,
                    name="Author",
                    options={"order_with_respect_to": "book"},
                )

    def test_set_alter_order_with_respect_to_index_constraint_unique_together(self):
        tests = [
            (
                "AddIndex",
                {
                    "indexes": [
                        models.Index(fields=["_order"], name="book_order_idx"),
                    ]
                },
            ),
            (
                "AddConstraint",
                {
                    "constraints": [
                        models.CheckConstraint(
                            check=models.Q(_order__gt=1),
                            name="book_order_gt_1",
                        ),
                    ]
                },
            ),
            ("AlterUniqueTogether", {"unique_together": {("id", "_order")}}),
        ]
        for operation, extra_option in tests:
            with self.subTest(operation=operation):
                after = ModelState(
                    "testapp",
                    "Author",
                    [
                        ("id", models.AutoField(primary_key=True)),
                        ("name", models.CharField(max_length=200)),
                        ("book", models.ForeignKey("otherapp.Book", models.CASCADE)),
                    ],
                    options={
                        "order_with_respect_to": "book",
                        **extra_option,
                    },
                )
                changes = self.get_changes(
                    [self.book, self.author_with_book],
                    [self.book, after],
                )
                self.assertNumberMigrations(changes, "testapp", 1)
                self.assertOperationTypes(
                    changes,
                    "testapp",
                    0,
                    [
                        "AlterOrderWithRespectTo",
                        operation,
                    ],
                )

    def test_alter_model_managers(self):
        """
        Changing the model managers adds a new operation.
        """
        changes = self.get_changes([self.other_pony], [self.other_pony_food])
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "otherapp", 1)
        self.assertOperationTypes(changes, "otherapp", 0, ["AlterModelManagers"])
        self.assertOperationAttributes(changes, "otherapp", 0, 0, name="pony")
        self.assertEqual(
            [name for name, mgr in changes["otherapp"][0].operations[0].managers],
            ["food_qs", "food_mgr", "food_mgr_kwargs"],
        )
        self.assertEqual(
            changes["otherapp"][0].operations[0].managers[1][1].args, ("a", "b", 1, 2)
        )
        self.assertEqual(
            changes["otherapp"][0].operations[0].managers[2][1].args, ("x", "y", 3, 4)
        )

    def test_swappable_first_inheritance(self):
        """Swappable models get their CreateModel first."""
        changes = self.get_changes([], [self.custom_user, self.aardvark])
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "thirdapp", 1)
        self.assertOperationTypes(
            changes, "thirdapp", 0, ["CreateModel", "CreateModel"]
        )
        self.assertOperationAttributes(changes, "thirdapp", 0, 0, name="CustomUser")
        self.assertOperationAttributes(changes, "thirdapp", 0, 1, name="Aardvark")

    def test_default_related_name_option(self):
        model_state = ModelState(
            "app",
            "model",
            [
                ("id", models.AutoField(primary_key=True)),
            ],
            options={"default_related_name": "related_name"},
        )
        changes = self.get_changes([], [model_state])
        self.assertNumberMigrations(changes, "app", 1)
        self.assertOperationTypes(changes, "app", 0, ["CreateModel"])
        self.assertOperationAttributes(
            changes,
            "app",
            0,
            0,
            name="model",
            options={"default_related_name": "related_name"},
        )
        altered_model_state = ModelState(
            "app",
            "Model",
            [
                ("id", models.AutoField(primary_key=True)),
            ],
        )
        changes = self.get_changes([model_state], [altered_model_state])
        self.assertNumberMigrations(changes, "app", 1)
        self.assertOperationTypes(changes, "app", 0, ["AlterModelOptions"])
        self.assertOperationAttributes(changes, "app", 0, 0, name="model", options={})

    @override_settings(AUTH_USER_MODEL="thirdapp.CustomUser")
    def test_swappable_first_setting(self):
        """Swappable models get their CreateModel first."""
        with isolate_lru_cache(apps.get_swappable_settings_name):
            changes = self.get_changes([], [self.custom_user_no_inherit, self.aardvark])
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "thirdapp", 1)
        self.assertOperationTypes(
            changes, "thirdapp", 0, ["CreateModel", "CreateModel"]
        )
        self.assertOperationAttributes(changes, "thirdapp", 0, 0, name="CustomUser")
        self.assertOperationAttributes(changes, "thirdapp", 0, 1, name="Aardvark")

    def test_bases_first(self):
        """Bases of other models come first."""
        changes = self.get_changes(
            [], [self.aardvark_based_on_author, self.author_name]
        )
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["CreateModel", "CreateModel"])
        self.assertOperationAttributes(changes, "testapp", 0, 0, name="Author")
        self.assertOperationAttributes(changes, "testapp", 0, 1, name="Aardvark")

    def test_bases_first_mixed_case_app_label(self):
        app_label = "MiXedCaseApp"
        changes = self.get_changes(
            [],
            [
                ModelState(
                    app_label,
                    "owner",
                    [
                        ("id", models.AutoField(primary_key=True)),
                    ],
                ),
                ModelState(
                    app_label,
                    "place",
                    [
                        ("id", models.AutoField(primary_key=True)),
                        (
                            "owner",
                            models.ForeignKey("MiXedCaseApp.owner", models.CASCADE),
                        ),
                    ],
                ),
                ModelState(app_label, "restaurant", [], bases=("MiXedCaseApp.place",)),
            ],
        )
        self.assertNumberMigrations(changes, app_label, 1)
        self.assertOperationTypes(
            changes,
            app_label,
            0,
            [
                "CreateModel",
                "CreateModel",
                "CreateModel",
            ],
        )
        self.assertOperationAttributes(changes, app_label, 0, 0, name="owner")
        self.assertOperationAttributes(changes, app_label, 0, 1, name="place")
        self.assertOperationAttributes(changes, app_label, 0, 2, name="restaurant")

    def test_multiple_bases(self):
        """
        Inheriting models doesn't move *_ptr fields into AddField operations.
        """
        A = ModelState("app", "A", [("a_id", models.AutoField(primary_key=True))])
        B = ModelState("app", "B", [("b_id", models.AutoField(primary_key=True))])
        C = ModelState("app", "C", [], bases=("app.A", "app.B"))
        D = ModelState("app", "D", [], bases=("app.A", "app.B"))
        E = ModelState("app", "E", [], bases=("app.A", "app.B"))
        changes = self.get_changes([], [A, B, C, D, E])
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "app", 1)
        self.assertOperationTypes(
            changes,
            "app",
            0,
            ["CreateModel", "CreateModel", "CreateModel", "CreateModel", "CreateModel"],
        )
        self.assertOperationAttributes(changes, "app", 0, 0, name="A")
        self.assertOperationAttributes(changes, "app", 0, 1, name="B")
        self.assertOperationAttributes(changes, "app", 0, 2, name="C")
        self.assertOperationAttributes(changes, "app", 0, 3, name="D")
        self.assertOperationAttributes(changes, "app", 0, 4, name="E")

    def test_proxy_bases_first(self):
        """Bases of proxies come first."""
        changes = self.get_changes(
            [], [self.author_empty, self.author_proxy, self.author_proxy_proxy]
        )
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(
            changes, "testapp", 0, ["CreateModel", "CreateModel", "CreateModel"]
        )
        self.assertOperationAttributes(changes, "testapp", 0, 0, name="Author")
        self.assertOperationAttributes(changes, "testapp", 0, 1, name="AuthorProxy")
        self.assertOperationAttributes(
            changes, "testapp", 0, 2, name="AAuthorProxyProxy"
        )

    def test_pk_fk_included(self):
        """
        A relation used as the primary key is kept as part of CreateModel.
        """
        changes = self.get_changes([], [self.aardvark_pk_fk_author, self.author_name])
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["CreateModel", "CreateModel"])
        self.assertOperationAttributes(changes, "testapp", 0, 0, name="Author")
        self.assertOperationAttributes(changes, "testapp", 0, 1, name="Aardvark")

    def test_first_dependency(self):
        """
        A dependency to an app with no migrations uses __first__.
        """
        # Load graph
        loader = MigrationLoader(connection)
        before = self.make_project_state([])
        after = self.make_project_state([self.book_migrations_fk])
        after.real_apps = {"migrations"}
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector._detect_changes(graph=loader.graph)
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "otherapp", 1)
        self.assertOperationTypes(changes, "otherapp", 0, ["CreateModel"])
        self.assertOperationAttributes(changes, "otherapp", 0, 0, name="Book")
        self.assertMigrationDependencies(
            changes, "otherapp", 0, [("migrations", "__first__")]
        )

    @override_settings(MIGRATION_MODULES={"migrations": "migrations.test_migrations"})
    def test_last_dependency(self):
        """
        A dependency to an app with existing migrations uses the
        last migration of that app.
        """
        # Load graph
        loader = MigrationLoader(connection)
        before = self.make_project_state([])
        after = self.make_project_state([self.book_migrations_fk])
        after.real_apps = {"migrations"}
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector._detect_changes(graph=loader.graph)
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "otherapp", 1)
        self.assertOperationTypes(changes, "otherapp", 0, ["CreateModel"])
        self.assertOperationAttributes(changes, "otherapp", 0, 0, name="Book")
        self.assertMigrationDependencies(
            changes, "otherapp", 0, [("migrations", "0002_second")]
        )

    def test_alter_fk_before_model_deletion(self):
        """
        ForeignKeys are altered _before_ the model they used to
        refer to are deleted.
        """
        changes = self.get_changes(
            [self.author_name, self.publisher_with_author],
            [self.aardvark_testapp, self.publisher_with_aardvark_author],
        )
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(
            changes, "testapp", 0, ["CreateModel", "AlterField", "DeleteModel"]
        )
        self.assertOperationAttributes(changes, "testapp", 0, 0, name="Aardvark")
        self.assertOperationAttributes(changes, "testapp", 0, 1, name="author")
        self.assertOperationAttributes(changes, "testapp", 0, 2, name="Author")

    def test_fk_dependency_other_app(self):
        """
        #23100 - ForeignKeys correctly depend on other apps' models.
        """
        changes = self.get_changes(
            [self.author_name, self.book], [self.author_with_book, self.book]
        )
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["AddField"])
        self.assertOperationAttributes(changes, "testapp", 0, 0, name="book")
        self.assertMigrationDependencies(
            changes, "testapp", 0, [("otherapp", "__first__")]
        )

    def test_alter_unique_together_fk_to_m2m(self):
        changes = self.get_changes(
            [self.author_name, self.book_unique_together],
            [
                self.author_name,
                ModelState(
                    "otherapp",
                    "Book",
                    [
                        ("id", models.AutoField(primary_key=True)),
                        ("author", models.ManyToManyField("testapp.Author")),
                        ("title", models.CharField(max_length=200)),
                    ],
                ),
            ],
        )
        self.assertNumberMigrations(changes, "otherapp", 1)
        self.assertOperationTypes(
            changes, "otherapp", 0, ["AlterUniqueTogether", "RemoveField", "AddField"]
        )
        self.assertOperationAttributes(
            changes, "otherapp", 0, 0, name="book", unique_together=set()
        )
        self.assertOperationAttributes(
            changes, "otherapp", 0, 1, model_name="book", name="author"
        )
        self.assertOperationAttributes(
            changes, "otherapp", 0, 2, model_name="book", name="author"
        )

    def test_alter_field_to_fk_dependency_other_app(self):
        changes = self.get_changes(
            [self.author_empty, self.book_with_no_author_fk],
            [self.author_empty, self.book],
        )
        self.assertNumberMigrations(changes, "otherapp", 1)
        self.assertOperationTypes(changes, "otherapp", 0, ["AlterField"])
        self.assertMigrationDependencies(
            changes, "otherapp", 0, [("testapp", "__first__")]
        )

    def test_circular_dependency_mixed_addcreate(self):
        """
        #23315 - The dependency resolver knows to put all CreateModel
        before AddField and not become unsolvable.
        """
        address = ModelState(
            "a",
            "Address",
            [
                ("id", models.AutoField(primary_key=True)),
                ("country", models.ForeignKey("b.DeliveryCountry", models.CASCADE)),
            ],
        )
        person = ModelState(
            "a",
            "Person",
            [
                ("id", models.AutoField(primary_key=True)),
            ],
        )
        apackage = ModelState(
            "b",
            "APackage",
            [
                ("id", models.AutoField(primary_key=True)),
                ("person", models.ForeignKey("a.Person", models.CASCADE)),
            ],
        )
        country = ModelState(
            "b",
            "DeliveryCountry",
            [
                ("id", models.AutoField(primary_key=True)),
            ],
        )
        changes = self.get_changes([], [address, person, apackage, country])
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "a", 2)
        self.assertNumberMigrations(changes, "b", 1)
        self.assertOperationTypes(changes, "a", 0, ["CreateModel", "CreateModel"])
        self.assertOperationTypes(changes, "a", 1, ["AddField"])
        self.assertOperationTypes(changes, "b", 0, ["CreateModel", "CreateModel"])

    @override_settings(AUTH_USER_MODEL="a.Tenant")
    def test_circular_dependency_swappable(self):
        """
        #23322 - The dependency resolver knows to explicitly resolve
        swappable models.
        """
        with isolate_lru_cache(apps.get_swappable_settings_name):
            tenant = ModelState(
                "a",
                "Tenant",
                [
                    ("id", models.AutoField(primary_key=True)),
                    ("primary_address", models.ForeignKey("b.Address", models.CASCADE)),
                ],
                bases=(AbstractBaseUser,),
            )
            address = ModelState(
                "b",
                "Address",
                [
                    ("id", models.AutoField(primary_key=True)),
                    (
                        "tenant",
                        models.ForeignKey(settings.AUTH_USER_MODEL, models.CASCADE),
                    ),
                ],
            )
            changes = self.get_changes([], [address, tenant])

        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "a", 2)
        self.assertOperationTypes(changes, "a", 0, ["CreateModel"])
        self.assertOperationTypes(changes, "a", 1, ["AddField"])
        self.assertMigrationDependencies(changes, "a", 0, [])
        self.assertMigrationDependencies(
            changes, "a", 1, [("a", "auto_1"), ("b", "auto_1")]
        )
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "b", 1)
        self.assertOperationTypes(changes, "b", 0, ["CreateModel"])
        self.assertMigrationDependencies(
            changes, "b", 0, [("__setting__", "AUTH_USER_MODEL")]
        )

    @override_settings(AUTH_USER_MODEL="b.Tenant")
    def test_circular_dependency_swappable2(self):
        """
        #23322 - The dependency resolver knows to explicitly resolve
        swappable models but with the swappable not being the first migrated
        model.
        """
        with isolate_lru_cache(apps.get_swappable_settings_name):
            address = ModelState(
                "a",
                "Address",
                [
                    ("id", models.AutoField(primary_key=True)),
                    (
                        "tenant",
                        models.ForeignKey(settings.AUTH_USER_MODEL, models.CASCADE),
                    ),
                ],
            )
            tenant = ModelState(
                "b",
                "Tenant",
                [
                    ("id", models.AutoField(primary_key=True)),
                    ("primary_address", models.ForeignKey("a.Address", models.CASCADE)),
                ],
                bases=(AbstractBaseUser,),
            )
            changes = self.get_changes([], [address, tenant])
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "a", 2)
        self.assertOperationTypes(changes, "a", 0, ["CreateModel"])
        self.assertOperationTypes(changes, "a", 1, ["AddField"])
        self.assertMigrationDependencies(changes, "a", 0, [])
        self.assertMigrationDependencies(
            changes, "a", 1, [("__setting__", "AUTH_USER_MODEL"), ("a", "auto_1")]
        )
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "b", 1)
        self.assertOperationTypes(changes, "b", 0, ["CreateModel"])
        self.assertMigrationDependencies(changes, "b", 0, [("a", "auto_1")])

    @override_settings(AUTH_USER_MODEL="a.Person")
    def test_circular_dependency_swappable_self(self):
        """
        #23322 - The dependency resolver knows to explicitly resolve
        swappable models.
        """
        with isolate_lru_cache(apps.get_swappable_settings_name):
            person = ModelState(
                "a",
                "Person",
                [
                    ("id", models.AutoField(primary_key=True)),
                    (
                        "parent1",
                        models.ForeignKey(
                            settings.AUTH_USER_MODEL,
                            models.CASCADE,
                            related_name="children",
                        ),
                    ),
                ],
            )
            changes = self.get_changes([], [person])
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "a", 1)
        self.assertOperationTypes(changes, "a", 0, ["CreateModel"])
        self.assertMigrationDependencies(changes, "a", 0, [])

    @override_settings(AUTH_USER_MODEL="a.User")
    def test_swappable_circular_multi_mti(self):
        with isolate_lru_cache(apps.get_swappable_settings_name):
            parent = ModelState(
                "a",
                "Parent",
                [("user", models.ForeignKey(settings.AUTH_USER_MODEL, models.CASCADE))],
            )
            child = ModelState("a", "Child", [], bases=("a.Parent",))
            user = ModelState("a", "User", [], bases=(AbstractBaseUser, "a.Child"))
            changes = self.get_changes([], [parent, child, user])
        self.assertNumberMigrations(changes, "a", 1)
        self.assertOperationTypes(
            changes, "a", 0, ["CreateModel", "CreateModel", "CreateModel", "AddField"]
        )

    @mock.patch(
        "django.db.migrations.questioner.MigrationQuestioner.ask_not_null_addition",
        side_effect=AssertionError("Should not have prompted for not null addition"),
    )
    def test_add_blank_textfield_and_charfield(self, mocked_ask_method):
        """
        #23405 - Adding a NOT NULL and blank `CharField` or `TextField`
        without default should not prompt for a default.
        """
        changes = self.get_changes(
            [self.author_empty], [self.author_with_biography_blank]
        )
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["AddField", "AddField"])
        self.assertOperationAttributes(changes, "testapp", 0, 0)

    @mock.patch(
        "django.db.migrations.questioner.MigrationQuestioner.ask_not_null_addition"
    )
    def test_add_non_blank_textfield_and_charfield(self, mocked_ask_method):
        """
        #23405 - Adding a NOT NULL and non-blank `CharField` or `TextField`
        without default should prompt for a default.
        """
        changes = self.get_changes(
            [self.author_empty], [self.author_with_biography_non_blank]
        )
        self.assertEqual(mocked_ask_method.call_count, 2)
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["AddField", "AddField"])
        self.assertOperationAttributes(changes, "testapp", 0, 0)

    def test_mti_inheritance_model_removal(self):
        Animal = ModelState(
            "app",
            "Animal",
            [
                ("id", models.AutoField(primary_key=True)),
            ],
        )
        Dog = ModelState("app", "Dog", [], bases=("app.Animal",))
        changes = self.get_changes([Animal, Dog], [Animal])
        self.assertNumberMigrations(changes, "app", 1)
        self.assertOperationTypes(changes, "app", 0, ["DeleteModel"])
        self.assertOperationAttributes(changes, "app", 0, 0, name="Dog")

    def test_add_model_with_field_removed_from_base_model(self):
        """
        Removing a base field takes place before adding a new inherited model
        that has a field with the same name.
        """
        before = [
            ModelState(
                "app",
                "readable",
                [
                    ("id", models.AutoField(primary_key=True)),
                    ("title", models.CharField(max_length=200)),
                ],
            ),
        ]
        after = [
            ModelState(
                "app",
                "readable",
                [
                    ("id", models.AutoField(primary_key=True)),
                ],
            ),
            ModelState(
                "app",
                "book",
                [
                    ("title", models.CharField(max_length=200)),
                ],
                bases=("app.readable",),
            ),
        ]
        changes = self.get_changes(before, after)
        self.assertNumberMigrations(changes, "app", 1)
        self.assertOperationTypes(changes, "app", 0, ["RemoveField", "CreateModel"])
        self.assertOperationAttributes(
            changes, "app", 0, 0, name="title", model_name="readable"
        )
        self.assertOperationAttributes(changes, "app", 0, 1, name="book")

    def test_parse_number(self):
        tests = [
            ("no_number", None),
            ("0001_initial", 1),
            ("0002_model3", 2),
            ("0002_auto_20380101_1112", 2),
            ("0002_squashed_0003", 3),
            ("0002_model2_squashed_0003_other4", 3),
            ("0002_squashed_0003_squashed_0004", 4),
            ("0002_model2_squashed_0003_other4_squashed_0005_other6", 5),
            ("0002_custom_name_20380101_1112_squashed_0003_model", 3),
            ("2_squashed_4", 4),
        ]
        for migration_name, expected_number in tests:
            with self.subTest(migration_name=migration_name):
                self.assertEqual(
                    MigrationAutodetector.parse_number(migration_name),
                    expected_number,
                )

    def test_add_custom_fk_with_hardcoded_to(self):
        class HardcodedForeignKey(models.ForeignKey):
            def __init__(self, *args, **kwargs):
                kwargs["to"] = "testapp.Author"
                super().__init__(*args, **kwargs)

            def deconstruct(self):
                name, path, args, kwargs = super().deconstruct()
                del kwargs["to"]
                return name, path, args, kwargs

        book_hardcoded_fk_to = ModelState(
            "testapp",
            "Book",
            [
                ("author", HardcodedForeignKey(on_delete=models.CASCADE)),
            ],
        )
        changes = self.get_changes(
            [self.author_empty],
            [self.author_empty, book_hardcoded_fk_to],
        )
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["CreateModel"])
        self.assertOperationAttributes(changes, "testapp", 0, 0, name="Book")


@ignore_warnings(category=RemovedInDjango51Warning)
class AutodetectorIndexTogetherTests(BaseAutodetectorTests):
    book_index_together = ModelState(
        "otherapp",
        "Book",
        [
            ("id", models.AutoField(primary_key=True)),
            ("author", models.ForeignKey("testapp.Author", models.CASCADE)),
            ("title", models.CharField(max_length=200)),
        ],
        {
            "index_together": {("author", "title")},
        },
    )
    book_index_together_2 = ModelState(
        "otherapp",
        "Book",
        [
            ("id", models.AutoField(primary_key=True)),
            ("author", models.ForeignKey("testapp.Author", models.CASCADE)),
            ("title", models.CharField(max_length=200)),
        ],
        {
            "index_together": {("title", "author")},
        },
    )
    book_index_together_3 = ModelState(
        "otherapp",
        "Book",
        [
            ("id", models.AutoField(primary_key=True)),
            ("newfield", models.IntegerField()),
            ("author", models.ForeignKey("testapp.Author", models.CASCADE)),
            ("title", models.CharField(max_length=200)),
        ],
        {
            "index_together": {("title", "newfield")},
        },
    )
    book_index_together_4 = ModelState(
        "otherapp",
        "Book",
        [
            ("id", models.AutoField(primary_key=True)),
            ("newfield2", models.IntegerField()),
            ("author", models.ForeignKey("testapp.Author", models.CASCADE)),
            ("title", models.CharField(max_length=200)),
        ],
        {
            "index_together": {("title", "newfield2")},
        },
    )

    def test_empty_index_together(self):
        """Empty index_together shouldn't generate a migration."""
        # Explicitly testing for not specified, since this is the case after
        # a CreateModel operation w/o any definition on the original model
        model_state_not_specified = ModelState(
            "a", "model", [("id", models.AutoField(primary_key=True))]
        )
        # Explicitly testing for None, since this was the issue in #23452 after
        # an AlterIndexTogether operation with e.g. () as value
        model_state_none = ModelState(
            "a",
            "model",
            [("id", models.AutoField(primary_key=True))],
            {
                "index_together": None,
            },
        )
        # Explicitly testing for the empty set, since we now always have sets.
        # During removal (('col1', 'col2'),) --> () this becomes set([])
        model_state_empty = ModelState(
            "a",
            "model",
            [("id", models.AutoField(primary_key=True))],
            {
                "index_together": set(),
            },
        )

        def test(from_state, to_state, msg):
            changes = self.get_changes([from_state], [to_state])
            if changes:
                ops = ", ".join(
                    o.__class__.__name__ for o in changes["a"][0].operations
                )
                self.fail("Created operation(s) %s from %s" % (ops, msg))

        tests = (
            (
                model_state_not_specified,
                model_state_not_specified,
                '"not specified" to "not specified"',
            ),
            (model_state_not_specified, model_state_none, '"not specified" to "None"'),
            (
                model_state_not_specified,
                model_state_empty,
                '"not specified" to "empty"',
            ),
            (model_state_none, model_state_not_specified, '"None" to "not specified"'),
            (model_state_none, model_state_none, '"None" to "None"'),
            (model_state_none, model_state_empty, '"None" to "empty"'),
            (
                model_state_empty,
                model_state_not_specified,
                '"empty" to "not specified"',
            ),
            (model_state_empty, model_state_none, '"empty" to "None"'),
            (model_state_empty, model_state_empty, '"empty" to "empty"'),
        )

        for t in tests:
            test(*t)

    def test_rename_index_together_to_index(self):
        changes = self.get_changes(
            [AutodetectorTests.author_empty, self.book_index_together],
            [AutodetectorTests.author_empty, AutodetectorTests.book_indexes],
        )
        self.assertNumberMigrations(changes, "otherapp", 1)
        self.assertOperationTypes(changes, "otherapp", 0, ["RenameIndex"])
        self.assertOperationAttributes(
            changes,
            "otherapp",
            0,
            0,
            model_name="book",
            new_name="book_title_author_idx",
            old_fields=("author", "title"),
        )

    def test_rename_index_together_to_index_extra_options(self):
        # Indexes with extra options don't match indexes in index_together.
        book_partial_index = ModelState(
            "otherapp",
            "Book",
            [
                ("id", models.AutoField(primary_key=True)),
                ("author", models.ForeignKey("testapp.Author", models.CASCADE)),
                ("title", models.CharField(max_length=200)),
            ],
            {
                "indexes": [
                    models.Index(
                        fields=["author", "title"],
                        condition=models.Q(title__startswith="The"),
                        name="book_title_author_idx",
                    )
                ],
            },
        )
        changes = self.get_changes(
            [AutodetectorTests.author_empty, self.book_index_together],
            [AutodetectorTests.author_empty, book_partial_index],
        )
        self.assertNumberMigrations(changes, "otherapp", 1)
        self.assertOperationTypes(
            changes,
            "otherapp",
            0,
            ["AlterIndexTogether", "AddIndex"],
        )

    def test_rename_index_together_to_index_order_fields(self):
        # Indexes with reordered fields don't match indexes in index_together.
        changes = self.get_changes(
            [AutodetectorTests.author_empty, self.book_index_together],
            [AutodetectorTests.author_empty, AutodetectorTests.book_unordered_indexes],
        )
        self.assertNumberMigrations(changes, "otherapp", 1)
        self.assertOperationTypes(
            changes,
            "otherapp",
            0,
            ["AlterIndexTogether", "AddIndex"],
        )

    def test_add_index_together(self):
        changes = self.get_changes(
            [AutodetectorTests.author_empty, AutodetectorTests.book],
            [AutodetectorTests.author_empty, self.book_index_together],
        )
        self.assertNumberMigrations(changes, "otherapp", 1)
        self.assertOperationTypes(changes, "otherapp", 0, ["AlterIndexTogether"])
        self.assertOperationAttributes(
            changes, "otherapp", 0, 0, name="book", index_together={("author", "title")}
        )

    def test_remove_index_together(self):
        changes = self.get_changes(
            [AutodetectorTests.author_empty, self.book_index_together],
            [AutodetectorTests.author_empty, AutodetectorTests.book],
        )
        self.assertNumberMigrations(changes, "otherapp", 1)
        self.assertOperationTypes(changes, "otherapp", 0, ["AlterIndexTogether"])
        self.assertOperationAttributes(
            changes, "otherapp", 0, 0, name="book", index_together=set()
        )

    def test_index_together_remove_fk(self):
        changes = self.get_changes(
            [AutodetectorTests.author_empty, self.book_index_together],
            [AutodetectorTests.author_empty, AutodetectorTests.book_with_no_author],
        )
        self.assertNumberMigrations(changes, "otherapp", 1)
        self.assertOperationTypes(
            changes,
            "otherapp",
            0,
            ["AlterIndexTogether", "RemoveField"],
        )
        self.assertOperationAttributes(
            changes, "otherapp", 0, 0, name="book", index_together=set()
        )
        self.assertOperationAttributes(
            changes, "otherapp", 0, 1, model_name="book", name="author"
        )

    def test_index_together_no_changes(self):
        """
        index_together doesn't generate a migration if no changes have been
        made.
        """
        changes = self.get_changes(
            [AutodetectorTests.author_empty, self.book_index_together],
            [AutodetectorTests.author_empty, self.book_index_together],
        )
        self.assertEqual(len(changes), 0)

    def test_index_together_ordering(self):
        """index_together triggers on ordering changes."""
        changes = self.get_changes(
            [AutodetectorTests.author_empty, self.book_index_together],
            [AutodetectorTests.author_empty, self.book_index_together_2],
        )
        self.assertNumberMigrations(changes, "otherapp", 1)
        self.assertOperationTypes(
            changes,
            "otherapp",
            0,
            ["AlterIndexTogether"],
        )
        self.assertOperationAttributes(
            changes,
            "otherapp",
            0,
            0,
            name="book",
            index_together={("title", "author")},
        )

    def test_add_field_and_index_together(self):
        """
        Added fields will be created before using them in index_together.
        """
        changes = self.get_changes(
            [AutodetectorTests.author_empty, AutodetectorTests.book],
            [AutodetectorTests.author_empty, self.book_index_together_3],
        )
        self.assertNumberMigrations(changes, "otherapp", 1)
        self.assertOperationTypes(
            changes,
            "otherapp",
            0,
            ["AddField", "AlterIndexTogether"],
        )
        self.assertOperationAttributes(
            changes,
            "otherapp",
            0,
            1,
            name="book",
            index_together={("title", "newfield")},
        )

    def test_create_model_and_index_together(self):
        author = ModelState(
            "otherapp",
            "Author",
            [
                ("id", models.AutoField(primary_key=True)),
                ("name", models.CharField(max_length=200)),
            ],
        )
        book_with_author = ModelState(
            "otherapp",
            "Book",
            [
                ("id", models.AutoField(primary_key=True)),
                ("author", models.ForeignKey("otherapp.Author", models.CASCADE)),
                ("title", models.CharField(max_length=200)),
            ],
            {
                "index_together": {("title", "author")},
            },
        )
        changes = self.get_changes(
            [AutodetectorTests.book_with_no_author], [author, book_with_author]
        )
        self.assertEqual(len(changes["otherapp"]), 1)
        migration = changes["otherapp"][0]
        self.assertEqual(len(migration.operations), 3)
        self.assertOperationTypes(
            changes,
            "otherapp",
            0,
            ["CreateModel", "AddField", "AlterIndexTogether"],
        )

    def test_remove_field_and_index_together(self):
        """
        Removed fields will be removed after updating index_together.
        """
        changes = self.get_changes(
            [AutodetectorTests.author_empty, self.book_index_together_3],
            [AutodetectorTests.author_empty, self.book_index_together],
        )
        self.assertNumberMigrations(changes, "otherapp", 1)
        self.assertOperationTypes(
            changes,
            "otherapp",
            0,
            ["AlterIndexTogether", "RemoveField"],
        )
        self.assertOperationAttributes(
            changes,
            "otherapp",
            0,
            0,
            name="book",
            index_together={("author", "title")},
        )
        self.assertOperationAttributes(
            changes,
            "otherapp",
            0,
            1,
            model_name="book",
            name="newfield",
        )

    def test_alter_field_and_index_together(self):
        """Fields are altered after deleting some index_together."""
        initial_author = ModelState(
            "testapp",
            "Author",
            [
                ("id", models.AutoField(primary_key=True)),
                ("name", models.CharField(max_length=200)),
                ("age", models.IntegerField(db_index=True)),
            ],
            {
                "index_together": {("name",)},
            },
        )
        author_reversed_constraints = ModelState(
            "testapp",
            "Author",
            [
                ("id", models.AutoField(primary_key=True)),
                ("name", models.CharField(max_length=200, unique=True)),
                ("age", models.IntegerField()),
            ],
            {
                "index_together": {("age",)},
            },
        )
        changes = self.get_changes([initial_author], [author_reversed_constraints])

        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(
            changes,
            "testapp",
            0,
            [
                "AlterIndexTogether",
                "AlterField",
                "AlterField",
                "AlterIndexTogether",
            ],
        )
        self.assertOperationAttributes(
            changes,
            "testapp",
            0,
            0,
            name="author",
            index_together=set(),
        )
        self.assertOperationAttributes(
            changes,
            "testapp",
            0,
            1,
            model_name="author",
            name="age",
        )
        self.assertOperationAttributes(
            changes,
            "testapp",
            0,
            2,
            model_name="author",
            name="name",
        )
        self.assertOperationAttributes(
            changes,
            "testapp",
            0,
            3,
            name="author",
            index_together={("age",)},
        )

    def test_partly_alter_index_together_increase(self):
        initial_author = ModelState(
            "testapp",
            "Author",
            [
                ("id", models.AutoField(primary_key=True)),
                ("name", models.CharField(max_length=200)),
                ("age", models.IntegerField()),
            ],
            {
                "index_together": {("name",)},
            },
        )
        author_new_constraints = ModelState(
            "testapp",
            "Author",
            [
                ("id", models.AutoField(primary_key=True)),
                ("name", models.CharField(max_length=200)),
                ("age", models.IntegerField()),
            ],
            {
                "index_together": {("name",), ("age",)},
            },
        )
        changes = self.get_changes([initial_author], [author_new_constraints])

        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(
            changes,
            "testapp",
            0,
            ["AlterIndexTogether"],
        )
        self.assertOperationAttributes(
            changes,
            "testapp",
            0,
            0,
            name="author",
            index_together={("name",), ("age",)},
        )

    def test_partly_alter_index_together_decrease(self):
        initial_author = ModelState(
            "testapp",
            "Author",
            [
                ("id", models.AutoField(primary_key=True)),
                ("name", models.CharField(max_length=200)),
                ("age", models.IntegerField()),
            ],
            {
                "index_together": {("name",), ("age",)},
            },
        )
        author_new_constraints = ModelState(
            "testapp",
            "Author",
            [
                ("id", models.AutoField(primary_key=True)),
                ("name", models.CharField(max_length=200)),
                ("age", models.IntegerField()),
            ],
            {
                "index_together": {("age",)},
            },
        )
        changes = self.get_changes([initial_author], [author_new_constraints])

        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(
            changes,
            "testapp",
            0,
            ["AlterIndexTogether"],
        )
        self.assertOperationAttributes(
            changes,
            "testapp",
            0,
            0,
            name="author",
            index_together={("age",)},
        )

    def test_rename_field_and_index_together(self):
        """Fields are renamed before updating index_together."""
        changes = self.get_changes(
            [AutodetectorTests.author_empty, self.book_index_together_3],
            [AutodetectorTests.author_empty, self.book_index_together_4],
            MigrationQuestioner({"ask_rename": True}),
        )
        self.assertNumberMigrations(changes, "otherapp", 1)
        self.assertOperationTypes(
            changes,
            "otherapp",
            0,
            ["RenameField", "AlterIndexTogether"],
        )
        self.assertOperationAttributes(
            changes,
            "otherapp",
            0,
            1,
            name="book",
            index_together={("title", "newfield2")},
        )

    def test_add_model_order_with_respect_to_index_together(self):
        changes = self.get_changes(
            [],
            [
                AutodetectorTests.book,
                ModelState(
                    "testapp",
                    "Author",
                    [
                        ("id", models.AutoField(primary_key=True)),
                        ("name", models.CharField(max_length=200)),
                        ("book", models.ForeignKey("otherapp.Book", models.CASCADE)),
                    ],
                    options={
                        "order_with_respect_to": "book",
                        "index_together": {("name", "_order")},
                    },
                ),
            ],
        )
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["CreateModel"])
        self.assertOperationAttributes(
            changes,
            "testapp",
            0,
            0,
            name="Author",
            options={
                "order_with_respect_to": "book",
                "index_together": {("name", "_order")},
            },
        )

    def test_set_alter_order_with_respect_to_index_together(self):
        after = ModelState(
            "testapp",
            "Author",
            [
                ("id", models.AutoField(primary_key=True)),
                ("name", models.CharField(max_length=200)),
                ("book", models.ForeignKey("otherapp.Book", models.CASCADE)),
            ],
            options={
                "order_with_respect_to": "book",
                "index_together": {("name", "_order")},
            },
        )
        changes = self.get_changes(
            [AutodetectorTests.book, AutodetectorTests.author_with_book],
            [AutodetectorTests.book, after],
        )
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(
            changes,
            "testapp",
            0,
            ["AlterOrderWithRespectTo", "AlterIndexTogether"],
        )


class MigrationSuggestNameTests(SimpleTestCase):
    def test_no_operations(self):
        class Migration(migrations.Migration):
            operations = []

        migration = Migration("some_migration", "test_app")
        self.assertIs(migration.suggest_name().startswith("auto_"), True)

    def test_no_operations_initial(self):
        class Migration(migrations.Migration):
            initial = True
            operations = []

        migration = Migration("some_migration", "test_app")
        self.assertEqual(migration.suggest_name(), "initial")

    def test_single_operation(self):
        class Migration(migrations.Migration):
            operations = [migrations.CreateModel("Person", fields=[])]

        migration = Migration("0001_initial", "test_app")
        self.assertEqual(migration.suggest_name(), "person")

        class Migration(migrations.Migration):
            operations = [migrations.DeleteModel("Person")]

        migration = Migration("0002_initial", "test_app")
        self.assertEqual(migration.suggest_name(), "delete_person")

    def test_single_operation_long_name(self):
        class Migration(migrations.Migration):
            operations = [migrations.CreateModel("A" * 53, fields=[])]

        migration = Migration("some_migration", "test_app")
        self.assertEqual(migration.suggest_name(), "a" * 53)

    def test_two_operations(self):
        class Migration(migrations.Migration):
            operations = [
                migrations.CreateModel("Person", fields=[]),
                migrations.DeleteModel("Animal"),
            ]

        migration = Migration("some_migration", "test_app")
        self.assertEqual(migration.suggest_name(), "person_delete_animal")

    def test_two_create_models(self):
        class Migration(migrations.Migration):
            operations = [
                migrations.CreateModel("Person", fields=[]),
                migrations.CreateModel("Animal", fields=[]),
            ]

        migration = Migration("0001_initial", "test_app")
        self.assertEqual(migration.suggest_name(), "person_animal")

    def test_two_create_models_with_initial_true(self):
        class Migration(migrations.Migration):
            initial = True
            operations = [
                migrations.CreateModel("Person", fields=[]),
                migrations.CreateModel("Animal", fields=[]),
            ]

        migration = Migration("0001_initial", "test_app")
        self.assertEqual(migration.suggest_name(), "initial")

    def test_many_operations_suffix(self):
        class Migration(migrations.Migration):
            operations = [
                migrations.CreateModel("Person1", fields=[]),
                migrations.CreateModel("Person2", fields=[]),
                migrations.CreateModel("Person3", fields=[]),
                migrations.DeleteModel("Person4"),
                migrations.DeleteModel("Person5"),
            ]

        migration = Migration("some_migration", "test_app")
        self.assertEqual(
            migration.suggest_name(),
            "person1_person2_person3_delete_person4_and_more",
        )

    def test_operation_with_no_suggested_name(self):
        class Migration(migrations.Migration):
            operations = [
                migrations.CreateModel("Person", fields=[]),
                migrations.RunSQL("SELECT 1 FROM person;"),
            ]

        migration = Migration("some_migration", "test_app")
        self.assertIs(migration.suggest_name().startswith("auto_"), True)

    def test_operation_with_invalid_chars_in_suggested_name(self):
        class Migration(migrations.Migration):
            operations = [
                migrations.AddConstraint(
                    "Person",
                    models.UniqueConstraint(
                        fields=["name"], name="person.name-*~unique!"
                    ),
                ),
            ]

        migration = Migration("some_migration", "test_app")
        self.assertEqual(migration.suggest_name(), "person_person_name_unique_")

    def test_none_name(self):
        class Migration(migrations.Migration):
            operations = [migrations.RunSQL("SELECT 1 FROM person;")]

        migration = Migration("0001_initial", "test_app")
        suggest_name = migration.suggest_name()
        self.assertIs(suggest_name.startswith("auto_"), True)

    def test_none_name_with_initial_true(self):
        class Migration(migrations.Migration):
            initial = True
            operations = [migrations.RunSQL("SELECT 1 FROM person;")]

        migration = Migration("0001_initial", "test_app")
        self.assertEqual(migration.suggest_name(), "initial")

    def test_auto(self):
        migration = migrations.Migration("0001_initial", "test_app")
        suggest_name = migration.suggest_name()
        self.assertIs(suggest_name.startswith("auto_"), True)
