from django.db.models import F
from django.test import TestCase, skipUnlessDBFeature

from .models import UpdateReturningModel


@skipUnlessDBFeature("can_return_columns_from_update")
class UpdateReturningTests(TestCase):
    def test_update_returning_single(self):
        obj = UpdateReturningModel.objects.create(key="key1", content="content", hits=0)

        updated = (
            UpdateReturningModel.objects.filter(key=obj.key)
            .update_returning(hits=F("hits") + 1)
            .get()
        )

        assert updated.pk == obj.pk
        assert updated.key == obj.key
        assert updated.content == obj.content
        assert updated.hits == obj.hits + 1

    def test_update_returning_multiple(self):
        UpdateReturningModel.objects.create(key="key1", content="content", hits=1)
        UpdateReturningModel.objects.create(key="key2", content="content", hits=2)
        UpdateReturningModel.objects.create(key="key3", content="content", hits=3)

        updated = UpdateReturningModel.objects.filter(hits__gt=1).update_returning(
            hits=F("hits") + 10
        )
        assert len(updated) == 2
        for obj in updated:
            assert obj.hits in (12, 13)

    def test_update_returning_only(self):
        obj = UpdateReturningModel.objects.create(key="key1", content="content", hits=0)

        updated = (
            UpdateReturningModel.objects.filter(key=obj.key)
            .update_returning(hits=F("hits") + 1)
            .only("hits")
            .get()
        )

        assert updated.pk == obj.pk
        assert updated.key == obj.key
        assert updated.content == obj.content
        assert updated.hits == obj.hits + 1, updated.hits

    def test_update_returning_defer(self):
        obj = UpdateReturningModel.objects.create(key="key1", content="content", hits=0)

        updated = (
            UpdateReturningModel.objects.filter(key=obj.key)
            .update_returning(hits=F("hits") + 1)
            .defer("hits", "content")
            .get()
        )

        assert updated.pk == obj.pk
        assert updated.key == obj.key
        assert updated.content == obj.content
        assert updated.hits == obj.hits + 1, updated.hits

    def test_update_returning_values(self):
        obj1 = UpdateReturningModel.objects.create(
            key="key1", content="content", hits=1
        )
        obj2 = UpdateReturningModel.objects.create(
            key="key2", content="content", hits=2
        )
        obj3 = UpdateReturningModel.objects.create(
            key="key3", content="content", hits=3
        )

        updated = UpdateReturningModel.objects.update_returning(
            hits=F("hits") + 1
        ).values("pk", "hits")

        updated = list(updated)
        assert len(updated) == 3
        updated.sort(key=lambda x: x["pk"])
        assert updated == [
            {"pk": obj1.pk, "hits": 2},
            {"pk": obj2.pk, "hits": 3},
            {"pk": obj3.pk, "hits": 4},
        ]

    def test_update_returning_values_list(self):
        UpdateReturningModel.objects.create(key="key1", content="content", hits=1)
        UpdateReturningModel.objects.create(key="key2", content="content", hits=2)
        UpdateReturningModel.objects.create(key="key3", content="content", hits=3)

        updated = UpdateReturningModel.objects.update_returning(
            hits=F("hits") + 1
        ).values_list("hits", flat=True)

        updated = list(updated)
        assert len(updated) == 3
        updated.sort(key=lambda x: x)
        assert updated == [2, 3, 4]
