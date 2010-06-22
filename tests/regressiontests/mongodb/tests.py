from django.db.models import Count
from django.test import TestCase

from models import Artist, Group


class MongoTestCase(TestCase):
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
            # TODO: should be i, but Mongo falls over with limit(0)
            for j in xrange(i+1, 5):
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
                {"name": "Steve Perry", "good": True, "current_group_id": None, "id": a.pk},
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
