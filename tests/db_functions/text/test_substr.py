from django.db.models import Value as V
from django.db.models.functions import Lower, StrIndex, Substr, Upper
from django.test import TestCase

from ..models import Author


class SubstrTests(TestCase):
    def test_basic(self):
        Author.objects.create(name="John Smith", alias="smithj")
        Author.objects.create(name="Rhonda")
        authors = Author.objects.annotate(name_part=Substr("name", 5, 3))
        self.assertQuerySetEqual(
            authors.order_by("name"), [" Sm", "da"], lambda a: a.name_part
        )
        authors = Author.objects.annotate(name_part=Substr("name", 2))
        self.assertQuerySetEqual(
            authors.order_by("name"), ["ohn Smith", "honda"], lambda a: a.name_part
        )
        # If alias is null, set to first 5 lower characters of the name.
        Author.objects.filter(alias__isnull=True).update(
            alias=Lower(Substr("name", 1, 5)),
        )
        self.assertQuerySetEqual(
            authors.order_by("name"), ["smithj", "rhond"], lambda a: a.alias
        )

    def test_start(self):
        Author.objects.create(name="John Smith", alias="smithj")
        a = Author.objects.annotate(
            name_part_1=Substr("name", 1),
            name_part_2=Substr("name", 2),
        ).get(alias="smithj")

        self.assertEqual(a.name_part_1[1:], a.name_part_2)

    def test_pos_gt_zero(self):
        with self.assertRaisesMessage(ValueError, "'pos' must be greater than 0"):
            Author.objects.annotate(raises=Substr("name", 0))

    def test_expressions(self):
        Author.objects.create(name="John Smith", alias="smithj")
        Author.objects.create(name="Rhonda")
        substr = Substr(Upper("name"), StrIndex("name", V("h")), 5)
        authors = Author.objects.annotate(name_part=substr)
        self.assertQuerySetEqual(
            authors.order_by("name"), ["HN SM", "HONDA"], lambda a: a.name_part
        )

    def test_substr_null_with_pattern_lookups(self):
        """
        Test that Substr works correctly with pattern lookups.

        Regression test for #29222. On Oracle, SUBSTR(NULL, x, y) returns NULL,
        which when concatenated in LIKE patterns without NVL, creates patterns
        like LIKE '%' that incorrectly match all rows due to Oracle's NULL
        concatenation behavior (NULL || 'text' = 'text' on Oracle).
        """
        # Author where name matches the Substr pattern from alias
        match = Author.objects.create(name="JaneDoe", alias="janedoe")
        # Author with alias but name doesn't match the pattern
        Author.objects.create(name="Bob Wilson", alias="bobby")

        # Substr(alias, 1, 4) where alias="janedoe" = "jane"
        qs = Author.objects.filter(name__startswith=Substr("alias", 1, 4))
        self.assertCountEqual(qs, [match])

        # Case-insensitive startswith
        qs = Author.objects.filter(name__istartswith=Substr("alias", 1, 4))
        self.assertCountEqual(qs, [match])

        # Substr(alias, 5, 3) where alias="janedoe" = "doe"
        qs = Author.objects.filter(name__endswith=Substr("alias", 5, 3))
        self.assertCountEqual(qs, [match])

        # Substr(alias, 5, 3) where alias="janedoe" = "doe"
        qs = Author.objects.filter(name__iendswith=Substr("alias", 5, 3))
        self.assertCountEqual(qs, [match])

        # Substr(alias, 2, 4) where alias="janedoe" = "aned"
        qs = Author.objects.filter(name__contains=Substr("alias", 2, 4))
        self.assertCountEqual(qs, [match])

        # Substr(alias, 2, 4) where alias="janedoe" = "aned"
        qs = Author.objects.filter(name__icontains=Substr("alias", 2, 4))
        self.assertCountEqual(qs, [match])

        # Verify NULL handling: author with NULL alias shouldn't match
        Author.objects.create(name="NoAlias", alias=None)
        qs = Author.objects.filter(name__startswith=Substr("alias", 1, 4))
        self.assertCountEqual(qs, [match])
