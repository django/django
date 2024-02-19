"""Finnish search language: includes the JS Finnish stemmer."""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict

import snowballstemmer

from sphinx.search import SearchLanguage, parse_stop_word

finnish_stopwords = parse_stop_word('''
| source: http://snowball.tartarus.org/algorithms/finnish/stop.txt
| forms of BE

olla
olen
olet
on
olemme
olette
ovat
ole        | negative form

oli
olisi
olisit
olisin
olisimme
olisitte
olisivat
olit
olin
olimme
olitte
olivat
ollut
olleet

en         | negation
et
ei
emme
ette
eivät

|Nom   Gen    Acc    Part   Iness   Elat    Illat  Adess   Ablat   Allat   Ess    Trans
minä   minun  minut  minua  minussa minusta minuun minulla minulta minulle               | I
sinä   sinun  sinut  sinua  sinussa sinusta sinuun sinulla sinulta sinulle               | you
hän    hänen  hänet  häntä  hänessä hänestä häneen hänellä häneltä hänelle               | he she
me     meidän meidät meitä  meissä  meistä  meihin meillä  meiltä  meille                | we
te     teidän teidät teitä  teissä  teistä  teihin teillä  teiltä  teille                | you
he     heidän heidät heitä  heissä  heistä  heihin heillä  heiltä  heille                | they

tämä   tämän         tätä   tässä   tästä   tähän  tällä   tältä   tälle   tänä   täksi  | this
tuo    tuon          tuota  tuossa  tuosta  tuohon tuolla  tuolta  tuolle  tuona  tuoksi | that
se     sen           sitä   siinä   siitä   siihen sillä   siltä   sille   sinä   siksi  | it
nämä   näiden        näitä  näissä  näistä  näihin näillä  näiltä  näille  näinä  näiksi | these
nuo    noiden        noita  noissa  noista  noihin noilla  noilta  noille  noina  noiksi | those
ne     niiden        niitä  niissä  niistä  niihin niillä  niiltä  niille  niinä  niiksi | they

kuka   kenen kenet   ketä   kenessä kenestä keneen kenellä keneltä kenelle kenenä keneksi| who
ketkä  keiden ketkä  keitä  keissä  keistä  keihin keillä  keiltä  keille  keinä  keiksi | (pl)
mikä   minkä minkä   mitä   missä   mistä   mihin  millä   miltä   mille   minä   miksi  | which what
mitkä                                                                                    | (pl)

joka   jonka         jota   jossa   josta   johon  jolla   jolta   jolle   jona   joksi  | who which
jotka  joiden        joita  joissa  joista  joihin joilla  joilta  joille  joina  joiksi | (pl)

| conjunctions

että   | that
ja     | and
jos    | if
koska  | because
kuin   | than
mutta  | but
niin   | so
sekä   | and
sillä  | for
tai    | or
vaan   | but
vai    | or
vaikka | although


| prepositions

kanssa  | with
mukaan  | according to
noin    | about
poikki  | across
yli     | over, across

| other

kun    | when
niin   | so
nyt    | now
itse   | self
''')


class SearchFinnish(SearchLanguage):
    lang = 'fi'
    language_name = 'Finnish'
    js_stemmer_rawcode = 'finnish-stemmer.js'
    stopwords = finnish_stopwords

    def init(self, options: dict) -> None:
        self.stemmer = snowballstemmer.stemmer('finnish')

    def stem(self, word: str) -> str:
        return self.stemmer.stemWord(word.lower())
