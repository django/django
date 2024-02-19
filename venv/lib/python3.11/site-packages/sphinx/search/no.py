"""Norwegian search language: includes the JS Norwegian stemmer."""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict

import snowballstemmer

from sphinx.search import SearchLanguage, parse_stop_word

norwegian_stopwords = parse_stop_word('''
| source: http://snowball.tartarus.org/algorithms/norwegian/stop.txt
og             | and
i              | in
jeg            | I
det            | it/this/that
at             | to (w. inf.)
en             | a/an
et             | a/an
den            | it/this/that
til            | to
er             | is/am/are
som            | who/that
på             | on
de             | they / you(formal)
med            | with
han            | he
av             | of
ikke           | not
ikkje          | not *
der            | there
så             | so
var            | was/were
meg            | me
seg            | you
men            | but
ett            | one
har            | have
om             | about
vi             | we
min            | my
mitt           | my
ha             | have
hadde          | had
hun            | she
nå             | now
over           | over
da             | when/as
ved            | by/know
fra            | from
du             | you
ut             | out
sin            | your
dem            | them
oss            | us
opp            | up
man            | you/one
kan            | can
hans           | his
hvor           | where
eller          | or
hva            | what
skal           | shall/must
selv           | self (reflective)
sjøl           | self (reflective)
her            | here
alle           | all
vil            | will
bli            | become
ble            | became
blei           | became *
blitt          | have become
kunne          | could
inn            | in
når            | when
være           | be
kom            | come
noen           | some
noe            | some
ville          | would
dere           | you
som            | who/which/that
deres          | their/theirs
kun            | only/just
ja             | yes
etter          | after
ned            | down
skulle         | should
denne          | this
for            | for/because
deg            | you
si             | hers/his
sine           | hers/his
sitt           | hers/his
mot            | against
å              | to
meget          | much
hvorfor        | why
dette          | this
disse          | these/those
uten           | without
hvordan        | how
ingen          | none
din            | your
ditt           | your
blir           | become
samme          | same
hvilken        | which
hvilke         | which (plural)
sånn           | such a
inni           | inside/within
mellom         | between
vår            | our
hver           | each
hvem           | who
vors           | us/ours
hvis           | whose
både           | both
bare           | only/just
enn            | than
fordi          | as/because
før            | before
mange          | many
også           | also
slik           | just
vært           | been
være           | to be
båe            | both *
begge          | both
siden          | since
dykk           | your *
dykkar         | yours *
dei            | they *
deira          | them *
deires         | theirs *
deim           | them *
di             | your (fem.) *
då             | as/when *
eg             | I *
ein            | a/an *
eit            | a/an *
eitt           | a/an *
elles          | or *
honom          | he *
hjå            | at *
ho             | she *
hoe            | she *
henne          | her
hennar         | her/hers
hennes         | hers
hoss           | how *
hossen         | how *
ikkje          | not *
ingi           | noone *
inkje          | noone *
korleis        | how *
korso          | how *
kva            | what/which *
kvar           | where *
kvarhelst      | where *
kven           | who/whom *
kvi            | why *
kvifor         | why *
me             | we *
medan          | while *
mi             | my *
mine           | my *
mykje          | much *
no             | now *
nokon          | some (masc./neut.) *
noka           | some (fem.) *
nokor          | some *
noko           | some *
nokre          | some *
si             | his/hers *
sia            | since *
sidan          | since *
so             | so *
somt           | some *
somme          | some *
um             | about*
upp            | up *
vere           | be *
vore           | was *
verte          | become *
vort           | become *
varte          | became *
vart           | became *
''')


class SearchNorwegian(SearchLanguage):
    lang = 'no'
    language_name = 'Norwegian'
    js_stemmer_rawcode = 'norwegian-stemmer.js'
    stopwords = norwegian_stopwords

    def init(self, options: dict) -> None:
        self.stemmer = snowballstemmer.stemmer('norwegian')

    def stem(self, word: str) -> str:
        return self.stemmer.stemWord(word.lower())
