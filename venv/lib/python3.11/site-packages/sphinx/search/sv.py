"""Swedish search language: includes the JS Swedish stemmer."""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict

import snowballstemmer

from sphinx.search import SearchLanguage, parse_stop_word

swedish_stopwords = parse_stop_word('''
| source: http://snowball.tartarus.org/algorithms/swedish/stop.txt
och            | and
det            | it, this/that
att            | to (with infinitive)
i              | in, at
en             | a
jag            | I
hon            | she
som            | who, that
han            | he
på             | on
den            | it, this/that
med            | with
var            | where, each
sig            | him(self) etc
för            | for
så             | so (also: seed)
till           | to
är             | is
men            | but
ett            | a
om             | if; around, about
hade           | had
de             | they, these/those
av             | of
icke           | not, no
mig            | me
du             | you
henne          | her
då             | then, when
sin            | his
nu             | now
har            | have
inte           | inte någon = no one
hans           | his
honom          | him
skulle         | 'sake'
hennes         | her
där            | there
min            | my
man            | one (pronoun)
ej             | nor
vid            | at, by, on (also: vast)
kunde          | could
något          | some etc
från           | from, off
ut             | out
när            | when
efter          | after, behind
upp            | up
vi             | we
dem            | them
vara           | be
vad            | what
över           | over
än             | than
dig            | you
kan            | can
sina           | his
här            | here
ha             | have
mot            | towards
alla           | all
under          | under (also: wonder)
någon          | some etc
eller          | or (else)
allt           | all
mycket         | much
sedan          | since
ju             | why
denna          | this/that
själv          | myself, yourself etc
detta          | this/that
åt             | to
utan           | without
varit          | was
hur            | how
ingen          | no
mitt           | my
ni             | you
bli            | to be, become
blev           | from bli
oss            | us
din            | thy
dessa          | these/those
några          | some etc
deras          | their
blir           | from bli
mina           | my
samma          | (the) same
vilken         | who, that
er             | you, your
sådan          | such a
vår            | our
blivit         | from bli
dess           | its
inom           | within
mellan         | between
sådant         | such a
varför         | why
varje          | each
vilka          | who, that
ditt           | thy
vem            | who
vilket         | who, that
sitta          | his
sådana         | such a
vart           | each
dina           | thy
vars           | whose
vårt           | our
våra           | our
ert            | your
era            | your
vilkas         | whose
''')


class SearchSwedish(SearchLanguage):
    lang = 'sv'
    language_name = 'Swedish'
    js_stemmer_rawcode = 'swedish-stemmer.js'
    stopwords = swedish_stopwords

    def init(self, options: dict) -> None:
        self.stemmer = snowballstemmer.stemmer('swedish')

    def stem(self, word: str) -> str:
        return self.stemmer.stemWord(word.lower())
