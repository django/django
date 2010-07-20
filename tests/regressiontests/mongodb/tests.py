from django.db import connection, UnsupportedDatabaseOperation
from django.db.models import Count, Sum, F, Q
from django.test import TestCase

from models import Artist, Group, Post


class MongoTestCase(TestCase):
    def assert_unsupported(self, obj):
        if callable(obj):
            # Queryset wrapped in a function (for aggregates and such)
            self.assertRaises(UnsupportedDatabaseOperation, obj)
        else:
            # Just a queryset that blows up on evaluation
            self.assertRaises(UnsupportedDatabaseOperation, list, obj)

    def test_create(self):
        b = Artist.objects.create(name="Bruce Springsteen", good=True)
        self.assertTrue(b.pk is not None)
        self.assertEqual(b.name, "Bruce Springsteen")
        self.assertTrue(b.good)
        b2 = Artist.objects.get(pk=b.pk)
        self.assertEqual(b.pk, b2.pk)
        self.assertEqual(b.name, b2.name)
        self.assertEqual(b.good, b2.good)
    
    def test_update(self):
        l = Artist.objects.create(name="Lady Gaga", good=True)
        self.assertTrue(l.pk is not None)
        pk = l.pk
        # Whoops, we screwed up.
        l.good = False
        l.save()
        self.assertEqual(l.pk, pk)
        
        l = Artist.objects.get(pk=pk)
        self.assertTrue(not l.good)
    
    def test_bulk_update(self):
        # Doesn't actually do an op on more than 1 item, but it's the bulk
        # update syntax nonetheless
        v = Artist.objects.create(name="Van Morrison", good=False)
        # How do you make a mistake like this, I don't know...
        Artist.objects.filter(pk=v.pk).update(good=True)
        self.assertTrue(Artist.objects.get(pk=v.pk).good)
    
    def test_f_expressions(self):
        k = Artist.objects.create(name="Keb' Mo'", age=57, good=True)
        # Birthday!
        Artist.objects.filter(pk=k.pk).update(age=F("age") + 1)
        self.assertEqual(Artist.objects.get(pk=k.pk).age, 58)
        
        # Backwards birthday
        Artist.objects.filter(pk=k.pk).update(age=F("age") - 1)
        self.assertEqual(Artist.objects.get(pk=k.pk).age, 57)
        
        # Birthday again!
        Artist.objects.filter(pk=k.pk).update(age=1 + F("age"))
        self.assertEqual(Artist.objects.get(pk=k.pk).age, 58)
    
    def test_delete(self):
        o = Artist.objects.create(name="O.A.R.", good=True)
        self.assertEqual(Artist.objects.count(), 1)
        
        o.delete()
        self.assertEqual(Artist.objects.count(), 0)
    
    def test_bulk_delete(self):
        d = Artist.objects.create(name="Dispatch", good=True)
        b = Artist.objects.create(name="Backstreet Boys", good=False)
        
        # Good riddance.
        Artist.objects.filter(good=False).delete()
        self.assertEqual(Artist.objects.count(), 1)
        self.assertEqual(Artist.objects.get(), d)
    
    def test_count(self):
        Artist.objects.create(name="Billy Joel", good=True)
        Artist.objects.create(name="John Mellencamp", good=True)
        Artist.objects.create(name="Warren Zevon", good=True)
        Artist.objects.create(name="Matisyahu", good=True)
        Artist.objects.create(name="Gary US Bonds", good=True)
        
        self.assertEqual(Artist.objects.count(), 5)
        self.assertEqual(Artist.objects.filter(good=True).count(), 5)
        
        Artist.objects.create(name="Bon Iver", good=False)
        
        self.assertEqual(Artist.objects.count(), 6)
        self.assertEqual(Artist.objects.filter(good=True).count(), 5)
        self.assertEqual(Artist.objects.filter(good=False).count(), 1)
        
        self.assertEqual(Artist.objects.aggregate(c=Count("pk")), {"c": 6})
        
        self.assertEqual(Artist.objects.all()[:3].count(), 3)
        self.assertEqual(Artist.objects.all()[3:].count(), 3)
    
    def test_foreignkey(self):
        e = Group.objects.create(name="The E Street Band")
        b = Artist.objects.create(name="Clarence Clemons", good=True,
            current_group=e)
        
        self.assertEqual(b.current_group, e)
        self.assertEqual(b.current_group_id, e.pk)
        
        b = Artist.objects.get(name="Clarence Clemons")
        self.assertEqual(b.current_group_id, e.pk)
        self.assertFalse(hasattr(b, "_current_group_cache"))
        self.assertEqual(b.current_group, e)
        
        self.assertEqual(Artist.objects.get(current_group=e), b)
        self.assertEqual(Artist.objects.get(current_group__id=e.pk), b)
    
    def test_exists(self):
        self.assertFalse(Artist.objects.filter(name="Brian May").exists())
        Artist.objects.create(name="Brian May")
        self.assertTrue(Artist.objects.filter(name="Brian May").exists())
    
    def test_orderby(self):
        Group.objects.create(name="Queen", year_formed=1971)
        Group.objects.create(name="The E Street Band", year_formed=1972)
        Group.objects.create(name="The Beatles", year_formed=1960)
        
        self.assertQuerysetEqual(
            Group.objects.order_by("year_formed"), [
                "The Beatles",
                "Queen",
                "The E Street Band",
            ],
            lambda g: g.name
        )
        
        self.assertQuerysetEqual(
            Group.objects.order_by("-year_formed"), [
                "The E Street Band",
                "Queen",
                "The Beatles",
            ],
            lambda g: g.name,
        )
    
    def test_slicing(self):
        artists = [
            Artist.objects.create(name="Huey Lewis"),
            Artist.objects.create(name="John Hiatt"),
            Artist.objects.create(name="Jackson Browne"),
            Artist.objects.create(name="Rick Springfield"),
        ]
        
        for i in xrange(5):
            for j in xrange(i, 5):
                self.assertQuerysetEqual(
                    Artist.objects.all()[i:j],
                    artists[i:j],
                    lambda a: a,
                )
        self.assertQuerysetEqual(
            Artist.objects.all()[:3],
            artists[:3],
            lambda a: a,
        )
        
        self.assertQuerysetEqual(
            Artist.objects.all()[2:],
            artists[2:],
            lambda a: a,
        )
    
    def test_values(self):
        a = Artist.objects.create(name="Steve Perry", good=True)
        
        self.assertQuerysetEqual(
            Artist.objects.values(), [
                {"name": "Steve Perry", "good": True, "current_group_id": None, "id": a.pk, "age": None},
            ],
            lambda a: a,
        )
        
        self.assertQuerysetEqual(
            Artist.objects.values("name"), [
                {"name": "Steve Perry"},
            ],
            lambda a: a,
        )
        
        self.assertQuerysetEqual(
            Artist.objects.values_list("name"), [
                ("Steve Perry",)
            ],
            lambda a: a,
        )
        
        self.assertQuerysetEqual(
            Artist.objects.values_list("name", flat=True), [
                "Steve Perry",
            ],
            lambda a: a,
        )

    def test_not_equals(self):
        q = Group.objects.create(name="Queen", year_formed=1971)
        e = Group.objects.create(name="The E Street Band", year_formed=1972)
        b = Group.objects.create(name="The Beatles")
        
        self.assertQuerysetEqual(
            Group.objects.exclude(year_formed=1972), [
                "Queen",
                "The Beatles",
            ],
            lambda g: g.name,
        )
    
    def test_less_than(self):
        q = Group.objects.create(name="Queen", year_formed=1971)
        e = Group.objects.create(name="The E Street Band", year_formed=1972)
        
        self.assertQuerysetEqual(
            Group.objects.filter(year_formed__lt=1980), [
                "Queen",
                "The E Street Band",
            ],
            lambda g: g.name
        )
        
        self.assertQuerysetEqual(
            Group.objects.filter(year_formed__lt=1972), [
                "Queen",
            ],
            lambda g: g.name
        )
        
        self.assertQuerysetEqual(
            Group.objects.filter(year_formed__lt=1971),
            [],
            lambda g: g.name
        )
        
        self.assertQuerysetEqual(
            Group.objects.exclude(year_formed__lt=1972), [
                "The E Street Band"
            ],
            lambda g: g.name,
        )
    
    def test_isnull(self):
        q = Group.objects.create(name="Queen", year_formed=1971)
        e = Group.objects.create(name="The E Street Band", year_formed=1972)
        b = Group.objects.create(name="The Beatles")
        
        self.assertQuerysetEqual(
            Group.objects.filter(year_formed__isnull=True), [
                "The Beatles",
            ],
            lambda g: g.name,
        )
        
        self.assertQuerysetEqual(
            Group.objects.filter(year_formed__isnull=False), [
                "Queen",
                "The E Street Band",
            ],
            lambda g: g.name
        )
        
        self.assertQuerysetEqual(
            Group.objects.exclude(year_formed__isnull=True), [
                "Queen",
                "The E Street Band",
            ],
            lambda g: g.name
        )
        
        self.assertQuerysetEqual(
            Group.objects.exclude(year_formed__isnull=False), [
                "The Beatles",
            ],
            lambda g: g.name
        )
    
    def test_gt(self):
        q = Group.objects.create(name="Queen", year_formed=1971)
        e = Group.objects.create(name="The E Street Band", year_formed=1972)
        
        self.assertQuerysetEqual(
            Group.objects.filter(year_formed__gt=1970), [
                "Queen",
                "The E Street Band",
            ],
            lambda g: g.name
        )
        
        self.assertQuerysetEqual(
            Group.objects.filter(year_formed__gt=1971), [
                "The E Street Band",
            ],
            lambda g: g.name
        )
        
        self.assertQuerysetEqual(
            Group.objects.filter(year_formed__gt=1972),
            [],
            lambda g: g.name
        )
        
        self.assertQuerysetEqual(
            Group.objects.exclude(year_formed__gt=1971), [
                "Queen",
            ],
            lambda g: g.name,
        )
    
    def test_in(self):
        q = Group.objects.create(name="Queen", year_formed=1971)
        e = Group.objects.create(name="The E Street Band", year_formed=1972)
        
        self.assertQuerysetEqual(
            Group.objects.filter(year_formed__in=[1972]), [
                "The E Street Band",
            ],
            lambda g: g.name,
        )
        
        self.assertQuerysetEqual(
            Group.objects.filter(year_formed__in=[1972, 1971]), [
                "Queen",
                "The E Street Band",
            ],
            lambda g: g.name
        )
        
        self.assertQuerysetEqual(
            Group.objects.exclude(year_formed__in=[1972]), [
                "Queen",
            ],
            lambda g: g.name,
        )
    
    def test_regex(self):
        q = Group.objects.create(name="Queen")
        e = Group.objects.create(name="The E Street Band")
        b = Group.objects.create(name="The Beatles")
        
        self.assertQuerysetEqual(
            Group.objects.filter(name__regex="^The"), [
                "The E Street Band",
                "The Beatles",
            ],
            lambda g: g.name
        )
        
        self.assertQuerysetEqual(
            Group.objects.filter(name__iregex="^the"), [
                "The E Street Band",
                "The Beatles",
            ],
            lambda g: g.name
        )

        self.assertQuerysetEqual(
            Group.objects.exclude(name__regex="^The"), [
                "Queen",
            ],
            lambda g: g.name,
        )
    
    def test_close(self):
        # Ensure that closing a connection that was never established doesn't
        # blow up.
        connection.close()

    def test_unsupported_ops(self):
        self.assert_unsupported(
            Artist.objects.filter(current_group__name="The Beatles")
        )
        
        self.assert_unsupported(
            Artist.objects.extra(select={"a": "1.0"})
        )
        
        self.assert_unsupported(
            Group.objects.annotate(artists=Count("current_artists"))
        )
        
        self.assert_unsupported(
            lambda: Artist.objects.aggregate(Sum("age"))
        )
        
        self.assert_unsupported(
            lambda: Artist.objects.aggregate(Count("age"))
        )
        
        self.assert_unsupported(
            lambda: Artist.objects.aggregate(Count("id"), Count("pk"))
        )
        
        self.assert_unsupported(
            Artist.objects.filter(Q(pk=0) | Q(pk=1))
        )
    
    def test_list_field(self):
        p = Post.objects.create(
            title="Django ORM grows MongoDB support",
            tags=["python", "django", "mongodb", "web"]
        )
        
        self.assertEqual(p.tags, ["python", "django", "mongodb", "web"])
        
        p = Post.objects.get(pk=p.pk)
        self.assertEqual(p.tags, ["python", "django", "mongodb", "web"])
        
        p = Post.objects.create(
            title="Rails 3.0 Released",
            tags=["ruby", "rails", "release", "web"],
        )
        
        self.assertQuerysetEqual(
            Post.objects.filter(tags="web"), [
                "Django ORM grows MongoDB support",
                "Rails 3.0 Released",
            ],
            lambda p: p.title,
        )
        
        self.assertQuerysetEqual(
            Post.objects.filter(tags="python"), [
                "Django ORM grows MongoDB support",
            ],
            lambda p: p.title
        )
        
        self.assertRaises(ValueError,
            lambda: Post.objects.create(magic_numbers=["a"])
        )
        
        p = Post.objects.create(
            title="Simon the Wizard",
            magic_numbers=["42"]
        )
        self.assertQuerysetEqual(
            Post.objects.filter(magic_numbers=42), [
                "Simon the Wizard",
            ],
            lambda p: p.title,
        )
        self.assertQuerysetEqual(
            Post.objects.filter(magic_numbers="42"), [
                "Simon the Wizard",
            ],
            lambda p: p.title,
        )
