"""
Test PostgreSQL full text search.

These tests use dialogue from the 1975 film Monty Python and the Holy Grail.
All text copyright Python (Monty) Pictures. Thanks to sacred-texts.com for the
transcript.
"""
from django.contrib.postgres.search import (
    SearchQuery, SearchRank, SearchVector,
)
from django.db.models import F
from django.test import modify_settings

from . import PostgreSQLTestCase
from .models import Character, Line, Scene


class GrailTestData(object):

    @classmethod
    def setUpTestData(cls):
        cls.robin = Scene.objects.create(scene='Scene 10', setting='The dark forest of Ewing')
        cls.minstrel = Character.objects.create(name='Minstrel')
        verses = [
            (
                'Bravely bold Sir Robin, rode forth from Camelot. '
                'He was not afraid to die, o Brave Sir Robin. '
                'He was not at all afraid to be killed in nasty ways. '
                'Brave, brave, brave, brave Sir Robin!'
            ),
            (
                'He was not in the least bit scared to be mashed into a pulp, '
                'Or to have his eyes gouged out, and his elbows broken. '
                'To have his kneecaps split, and his body burned away, '
                'And his limbs all hacked and mangled, brave Sir Robin!'
            ),
            (
                'His head smashed in and his heart cut out, '
                'And his liver removed and his bowels unplugged, '
                'And his nostrils ripped and his bottom burned off,'
                'And his --'
            ),
        ]
        cls.verses = [Line.objects.create(
            scene=cls.robin,
            character=cls.minstrel,
            dialogue=verse,
        ) for verse in verses]
        cls.verse0, cls.verse1, cls.verse2 = cls.verses

        cls.witch_scene = Scene.objects.create(scene='Scene 5', setting="Sir Bedemir's Castle")
        bedemir = Character.objects.create(name='Bedemir')
        crowd = Character.objects.create(name='Crowd')
        witch = Character.objects.create(name='Witch')
        duck = Character.objects.create(name='Duck')

        cls.bedemir0 = Line.objects.create(
            scene=cls.witch_scene,
            character=bedemir,
            dialogue='We shall use my larger scales!',
            dialogue_config='english',
        )
        cls.bedemir1 = Line.objects.create(
            scene=cls.witch_scene,
            character=bedemir,
            dialogue='Right, remove the supports!',
            dialogue_config='english',
        )
        cls.duck = Line.objects.create(scene=cls.witch_scene, character=duck, dialogue=None)
        cls.crowd = Line.objects.create(scene=cls.witch_scene, character=crowd, dialogue='A witch! A witch!')
        cls.witch = Line.objects.create(scene=cls.witch_scene, character=witch, dialogue="It's a fair cop.")

        trojan_rabbit = Scene.objects.create(scene='Scene 8', setting="The castle of Our Master Ruiz' de lu la Ramper")
        guards = Character.objects.create(name='French Guards')
        cls.french = Line.objects.create(
            scene=trojan_rabbit,
            character=guards,
            dialogue='Oh. Un cadeau. Oui oui.',
            dialogue_config='french',
        )


@modify_settings(INSTALLED_APPS={'append': 'django.contrib.postgres'})
class SimpleSearchTest(GrailTestData, PostgreSQLTestCase):

    def test_simple(self):
        searched = Line.objects.filter(dialogue__search='elbows')
        self.assertSequenceEqual(searched, [self.verse1])

    def test_non_exact_match(self):
        searched = Line.objects.filter(dialogue__search='hearts')
        self.assertSequenceEqual(searched, [self.verse2])

    def test_search_two_terms(self):
        searched = Line.objects.filter(dialogue__search='heart bowel')
        self.assertSequenceEqual(searched, [self.verse2])

    def test_search_two_terms_with_partial_match(self):
        searched = Line.objects.filter(dialogue__search='Robin killed')
        self.assertSequenceEqual(searched, [self.verse0])


@modify_settings(INSTALLED_APPS={'append': 'django.contrib.postgres'})
class SearchVectorFieldTest(GrailTestData, PostgreSQLTestCase):
    def test_existing_vector(self):
        Line.objects.update(dialogue_search_vector=SearchVector('dialogue'))
        searched = Line.objects.filter(dialogue_search_vector=SearchQuery('Robin killed'))
        self.assertSequenceEqual(searched, [self.verse0])

    def test_existing_vector_config_explicit(self):
        Line.objects.update(dialogue_search_vector=SearchVector('dialogue'))
        searched = Line.objects.filter(dialogue_search_vector=SearchQuery('cadeaux', config='french'))
        self.assertSequenceEqual(searched, [self.french])


class MultipleFieldsTest(GrailTestData, PostgreSQLTestCase):

    def test_simple_on_dialogue(self):
        searched = Line.objects.annotate(
            search=SearchVector('scene__setting', 'dialogue'),
        ).filter(search='elbows')
        self.assertSequenceEqual(searched, [self.verse1])

    def test_simple_on_scene(self):
        searched = Line.objects.annotate(
            search=SearchVector('scene__setting', 'dialogue'),
        ).filter(search='Forest')
        self.assertSequenceEqual(searched, self.verses)

    def test_non_exact_match(self):
        searched = Line.objects.annotate(
            search=SearchVector('scene__setting', 'dialogue'),
        ).filter(search='heart')
        self.assertSequenceEqual(searched, [self.verse2])

    def test_search_two_terms(self):
        searched = Line.objects.annotate(
            search=SearchVector('scene__setting', 'dialogue'),
        ).filter(search='heart forest')
        self.assertSequenceEqual(searched, [self.verse2])

    def test_terms_adjacent(self):
        searched = Line.objects.annotate(
            search=SearchVector('character__name', 'dialogue'),
        ).filter(search='minstrel')
        self.assertSequenceEqual(searched, self.verses)
        searched = Line.objects.annotate(
            search=SearchVector('scene__setting', 'dialogue'),
        ).filter(search='minstrelbravely')
        self.assertSequenceEqual(searched, [])

    def test_search_with_null(self):
        searched = Line.objects.annotate(
            search=SearchVector('scene__setting', 'dialogue'),
        ).filter(search='bedemir')
        self.assertEqual(set(searched), {self.bedemir0, self.bedemir1, self.crowd, self.witch, self.duck})

    def test_config_query_explicit(self):
        searched = Line.objects.annotate(
            search=SearchVector('scene__setting', 'dialogue', config='french'),
        ).filter(search=SearchQuery('cadeaux', config='french'))
        self.assertSequenceEqual(searched, [self.french])

    def test_config_query_implicit(self):
        searched = Line.objects.annotate(
            search=SearchVector('scene__setting', 'dialogue', config='french'),
        ).filter(search='cadeaux')
        self.assertSequenceEqual(searched, [self.french])

    def test_config_from_field_explicit(self):
        searched = Line.objects.annotate(
            search=SearchVector('scene__setting', 'dialogue', config=F('dialogue_config')),
        ).filter(search=SearchQuery('cadeaux', config=F('dialogue_config')))
        self.assertSequenceEqual(searched, [self.french])

    def test_config_from_field_implicit(self):
        searched = Line.objects.annotate(
            search=SearchVector('scene__setting', 'dialogue', config=F('dialogue_config')),
        ).filter(search='cadeaux')
        self.assertSequenceEqual(searched, [self.french])


@modify_settings(INSTALLED_APPS={'append': 'django.contrib.postgres'})
class TestCombinations(GrailTestData, PostgreSQLTestCase):

    def test_vector_add(self):
        searched = Line.objects.annotate(
            search=SearchVector('scene__setting') + SearchVector('character__name'),
        ).filter(search='bedemir')
        self.assertEqual(set(searched), {self.bedemir0, self.bedemir1, self.crowd, self.witch, self.duck})

    def test_vector_add_multi(self):
        searched = Line.objects.annotate(
            search=(
                SearchVector('scene__setting') +
                SearchVector('character__name') +
                SearchVector('dialogue')
            ),
        ).filter(search='bedemir')
        self.assertEqual(set(searched), {self.bedemir0, self.bedemir1, self.crowd, self.witch, self.duck})

    def test_query_and(self):
        searched = Line.objects.annotate(
            search=SearchVector('scene__setting', 'dialogue'),
        ).filter(search=SearchQuery('bedemir') & SearchQuery('scales'))
        self.assertSequenceEqual(searched, [self.bedemir0])

    def test_query_multiple_and(self):
        searched = Line.objects.annotate(
            search=SearchVector('scene__setting', 'dialogue'),
        ).filter(search=SearchQuery('bedemir') & SearchQuery('scales') & SearchQuery('nostrils'))
        self.assertSequenceEqual(searched, [])

        searched = Line.objects.annotate(
            search=SearchVector('scene__setting', 'dialogue'),
        ).filter(search=SearchQuery('shall') & SearchQuery('use') & SearchQuery('larger'))
        self.assertSequenceEqual(searched, [self.bedemir0])

    def test_query_or(self):
        searched = Line.objects.filter(dialogue__search=SearchQuery('kneecaps') | SearchQuery('nostrils'))
        self.assertSequenceEqual(set(searched), {self.verse1, self.verse2})

    def test_query_multiple_or(self):
        searched = Line.objects.filter(
            dialogue__search=SearchQuery('kneecaps') | SearchQuery('nostrils') | SearchQuery('Sir Robin')
        )
        self.assertSequenceEqual(set(searched), {self.verse1, self.verse2, self.verse0})

    def test_query_invert(self):
        searched = Line.objects.filter(character=self.minstrel, dialogue__search=~SearchQuery('kneecaps'))
        self.assertEqual(set(searched), {self.verse0, self.verse2})

    def test_query_config_mismatch(self):
        with self.assertRaisesMessage(TypeError, "SearchQuery configs don't match."):
            Line.objects.filter(
                dialogue__search=SearchQuery('kneecaps', config='german') |
                SearchQuery('nostrils', config='english')
            )

    def test_query_combined_mismatch(self):
        msg = "SearchQuery can only be combined with other SearchQuerys, got"
        with self.assertRaisesMessage(TypeError, msg):
            Line.objects.filter(dialogue__search=None | SearchQuery('kneecaps'))

        with self.assertRaisesMessage(TypeError, msg):
            Line.objects.filter(dialogue__search=None & SearchQuery('kneecaps'))


@modify_settings(INSTALLED_APPS={'append': 'django.contrib.postgres'})
class TestRankingAndWeights(GrailTestData, PostgreSQLTestCase):

    def test_ranking(self):
        searched = Line.objects.filter(character=self.minstrel).annotate(
            rank=SearchRank(SearchVector('dialogue'), SearchQuery('brave sir robin')),
        ).order_by('rank')
        self.assertSequenceEqual(searched, [self.verse2, self.verse1, self.verse0])

    def test_rank_passing_untyped_args(self):
        searched = Line.objects.filter(character=self.minstrel).annotate(
            rank=SearchRank('dialogue', 'brave sir robin'),
        ).order_by('rank')
        self.assertSequenceEqual(searched, [self.verse2, self.verse1, self.verse0])

    def test_weights_in_vector(self):
        vector = SearchVector('dialogue', weight='A') + SearchVector('character__name', weight='D')
        searched = Line.objects.filter(scene=self.witch_scene).annotate(
            rank=SearchRank(vector, SearchQuery('witch')),
        ).order_by('-rank')[:2]
        self.assertSequenceEqual(searched, [self.crowd, self.witch])

        vector = SearchVector('dialogue', weight='D') + SearchVector('character__name', weight='A')
        searched = Line.objects.filter(scene=self.witch_scene).annotate(
            rank=SearchRank(vector, SearchQuery('witch')),
        ).order_by('-rank')[:2]
        self.assertSequenceEqual(searched, [self.witch, self.crowd])

    def test_ranked_custom_weights(self):
        vector = SearchVector('dialogue', weight='D') + SearchVector('character__name', weight='A')
        searched = Line.objects.filter(scene=self.witch_scene).annotate(
            rank=SearchRank(vector, SearchQuery('witch'), weights=[1, 0, 0, 0.5]),
        ).order_by('-rank')[:2]
        self.assertSequenceEqual(searched, [self.crowd, self.witch])

    def test_ranking_chaining(self):
        searched = Line.objects.filter(character=self.minstrel).annotate(
            rank=SearchRank(SearchVector('dialogue'), SearchQuery('brave sir robin')),
        ).filter(rank__gt=0.3)
        self.assertSequenceEqual(searched, [self.verse0])
