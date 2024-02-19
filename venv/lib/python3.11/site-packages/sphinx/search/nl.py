"""Dutch search language: includes the JS porter stemmer."""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict

import snowballstemmer

from sphinx.search import SearchLanguage, parse_stop_word

dutch_stopwords = parse_stop_word('''
| source: http://snowball.tartarus.org/algorithms/dutch/stop.txt
de             |  the
en             |  and
van            |  of, from
ik             |  I, the ego
te             |  (1) chez, at etc, (2) to, (3) too
dat            |  that, which
die            |  that, those, who, which
in             |  in, inside
een            |  a, an, one
hij            |  he
het            |  the, it
niet           |  not, nothing, naught
zijn           |  (1) to be, being, (2) his, one's, its
is             |  is
was            |  (1) was, past tense of all persons sing. of 'zijn' (to be) (2) wax, (3) the washing, (4) rise of river
op             |  on, upon, at, in, up, used up
aan            |  on, upon, to (as dative)
met            |  with, by
als            |  like, such as, when
voor           |  (1) before, in front of, (2) furrow
had            |  had, past tense all persons sing. of 'hebben' (have)
er             |  there
maar           |  but, only
om             |  round, about, for etc
hem            |  him
dan            |  then
zou            |  should/would, past tense all persons sing. of 'zullen'
of             |  or, whether, if
wat            |  what, something, anything
mijn           |  possessive and noun 'mine'
men            |  people, 'one'
dit            |  this
zo             |  so, thus, in this way
door           |  through by
over           |  over, across
ze             |  she, her, they, them
zich           |  oneself
bij            |  (1) a bee, (2) by, near, at
ook            |  also, too
tot            |  till, until
je             |  you
mij            |  me
uit            |  out of, from
der            |  Old Dutch form of 'van der' still found in surnames
daar           |  (1) there, (2) because
haar           |  (1) her, their, them, (2) hair
naar           |  (1) unpleasant, unwell etc, (2) towards, (3) as
heb            |  present first person sing. of 'to have'
hoe            |  how, why
heeft          |  present third person sing. of 'to have'
hebben         |  'to have' and various parts thereof
deze           |  this
u              |  you
want           |  (1) for, (2) mitten, (3) rigging
nog            |  yet, still
zal            |  'shall', first and third person sing. of verb 'zullen' (will)
me             |  me
zij            |  she, they
nu             |  now
ge             |  'thou', still used in Belgium and south Netherlands
geen           |  none
omdat          |  because
iets           |  something, somewhat
worden         |  to become, grow, get
toch           |  yet, still
al             |  all, every, each
waren          |  (1) 'were' (2) to wander, (3) wares, (3)
veel           |  much, many
meer           |  (1) more, (2) lake
doen           |  to do, to make
toen           |  then, when
moet           |  noun 'spot/mote' and present form of 'to must'
ben            |  (1) am, (2) 'are' in interrogative second person singular of 'to be'
zonder         |  without
kan            |  noun 'can' and present form of 'to be able'
hun            |  their, them
dus            |  so, consequently
alles          |  all, everything, anything
onder          |  under, beneath
ja             |  yes, of course
eens           |  once, one day
hier           |  here
wie            |  who
werd           |  imperfect third person sing. of 'become'
altijd         |  always
doch           |  yet, but etc
wordt          |  present third person sing. of 'become'
wezen          |  (1) to be, (2) 'been' as in 'been fishing', (3) orphans
kunnen         |  to be able
ons            |  us/our
zelf           |  self
tegen          |  against, towards, at
na             |  after, near
reeds          |  already
wil            |  (1) present tense of 'want', (2) 'will', noun, (3) fender
kon            |  could; past tense of 'to be able'
niets          |  nothing
uw             |  your
iemand         |  somebody
geweest        |  been; past participle of 'be'
andere         |  other
''')


class SearchDutch(SearchLanguage):
    lang = 'nl'
    language_name = 'Dutch'
    js_stemmer_rawcode = 'dutch-stemmer.js'
    stopwords = dutch_stopwords

    def init(self, options: dict) -> None:
        self.stemmer = snowballstemmer.stemmer('dutch')

    def stem(self, word: str) -> str:
        return self.stemmer.stemWord(word.lower())
