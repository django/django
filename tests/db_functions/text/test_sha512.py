from django.db import connection
from django.db.models import CharField
from django.db.models.functions import SHA512
from django.test import TestCase
from django.test.utils import register_lookup

from ..models import Author


class SHA512Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Author.objects.bulk_create(
            [
                Author(alias="John Smith"),
                Author(alias="Jordan Élena"),
                Author(alias="皇帝"),
                Author(alias=""),
                Author(alias=None),
            ]
        )

    def test_basic(self):
        authors = (
            Author.objects.annotate(
                sha512_alias=SHA512("alias"),
            )
            .values_list("sha512_alias", flat=True)
            .order_by("pk")
        )
        self.assertSequenceEqual(
            authors,
            [
                "ed014a19bb67a85f9c8b1d81e04a0e7101725be8627d79d02ca4f3bd803f33cf"
                "3b8fed53e80d2a12c0d0e426824d99d110f0919298a5055efff040a3fc091518",
                "b09c449f3ba49a32ab44754982d4749ac938af293e4af2de28858858080a1611"
                "2b719514b5e48cb6ce54687e843a4b3e69a04cdb2a9dc99c3b99bdee419fa7d0",
                "b554d182e25fb487a3f2b4285bb8672f98956b5369138e681b467d1f079af116"
                "172d88798345a3a7666faf5f35a144c60812d3234dcd35f444624f2faee16857",
                "cf83e1357eefb8bdf1542850d66d8007d620e4050b5715dc83f4a921d36ce9ce"
                "47d0d13c5d85f2b0ff8318d2877eec2f63b931bd47417a81a538327af927da3e",
                "cf83e1357eefb8bdf1542850d66d8007d620e4050b5715dc83f4a921d36ce9ce"
                "47d0d13c5d85f2b0ff8318d2877eec2f63b931bd47417a81a538327af927da3e"
                if connection.features.interprets_empty_strings_as_nulls
                else None,
            ],
        )

    def test_transform(self):
        with register_lookup(CharField, SHA512):
            authors = Author.objects.filter(
                alias__sha512=(
                    "ed014a19bb67a85f9c8b1d81e04a0e7101725be8627d79d02ca4f3bd8"
                    "03f33cf3b8fed53e80d2a12c0d0e426824d99d110f0919298a5055eff"
                    "f040a3fc091518"
                ),
            ).values_list("alias", flat=True)
            self.assertSequenceEqual(authors, ["John Smith"])
