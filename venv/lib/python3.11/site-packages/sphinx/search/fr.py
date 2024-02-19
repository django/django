"""French search language: includes the JS French stemmer."""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict

import snowballstemmer

from sphinx.search import SearchLanguage, parse_stop_word

french_stopwords = parse_stop_word('''
| source: http://snowball.tartarus.org/algorithms/french/stop.txt
au             |  a + le
aux            |  a + les
avec           |  with
ce             |  this
ces            |  these
dans           |  with
de             |  of
des            |  de + les
du             |  de + le
elle           |  she
en             |  `of them' etc
et             |  and
eux            |  them
il             |  he
je             |  I
la             |  the
le             |  the
leur           |  their
lui            |  him
ma             |  my (fem)
mais           |  but
me             |  me
même           |  same; as in moi-même (myself) etc
mes            |  me (pl)
moi            |  me
mon            |  my (masc)
ne             |  not
nos            |  our (pl)
notre          |  our
nous           |  we
on             |  one
ou             |  where
par            |  by
pas            |  not
pour           |  for
qu             |  que before vowel
que            |  that
qui            |  who
sa             |  his, her (fem)
se             |  oneself
ses            |  his (pl)
son            |  his, her (masc)
sur            |  on
ta             |  thy (fem)
te             |  thee
tes            |  thy (pl)
toi            |  thee
ton            |  thy (masc)
tu             |  thou
un             |  a
une            |  a
vos            |  your (pl)
votre          |  your
vous           |  you

               |  single letter forms

c              |  c'
d              |  d'
j              |  j'
l              |  l'
à              |  to, at
m              |  m'
n              |  n'
s              |  s'
t              |  t'
y              |  there

               | forms of être (not including the infinitive):
été
étée
étées
étés
étant
suis
es
est
sommes
êtes
sont
serai
seras
sera
serons
serez
seront
serais
serait
serions
seriez
seraient
étais
était
étions
étiez
étaient
fus
fut
fûmes
fûtes
furent
sois
soit
soyons
soyez
soient
fusse
fusses
fût
fussions
fussiez
fussent

               | forms of avoir (not including the infinitive):
ayant
eu
eue
eues
eus
ai
as
avons
avez
ont
aurai
auras
aura
aurons
aurez
auront
aurais
aurait
aurions
auriez
auraient
avais
avait
avions
aviez
avaient
eut
eûmes
eûtes
eurent
aie
aies
ait
ayons
ayez
aient
eusse
eusses
eût
eussions
eussiez
eussent

               | Later additions (from Jean-Christophe Deschamps)
ceci           |  this
cela           |  that (added 11 Apr 2012. Omission reported by Adrien Grand)
celà           |  that (incorrect, though common)
cet            |  this
cette          |  this
ici            |  here
ils            |  they
les            |  the (pl)
leurs          |  their (pl)
quel           |  which
quels          |  which
quelle         |  which
quelles        |  which
sans           |  without
soi            |  oneself
''')


class SearchFrench(SearchLanguage):
    lang = 'fr'
    language_name = 'French'
    js_stemmer_rawcode = 'french-stemmer.js'
    stopwords = french_stopwords

    def init(self, options: dict) -> None:
        self.stemmer = snowballstemmer.stemmer('french')

    def stem(self, word: str) -> str:
        return self.stemmer.stemWord(word.lower())
