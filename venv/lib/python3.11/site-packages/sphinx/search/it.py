"""Italian search language: includes the JS Italian stemmer."""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict

import snowballstemmer

from sphinx.search import SearchLanguage, parse_stop_word

italian_stopwords = parse_stop_word('''
| source: http://snowball.tartarus.org/algorithms/italian/stop.txt
ad             |  a (to) before vowel
al             |  a + il
allo           |  a + lo
ai             |  a + i
agli           |  a + gli
all            |  a + l'
agl            |  a + gl'
alla           |  a + la
alle           |  a + le
con            |  with
col            |  con + il
coi            |  con + i (forms collo, cogli etc are now very rare)
da             |  from
dal            |  da + il
dallo          |  da + lo
dai            |  da + i
dagli          |  da + gli
dall           |  da + l'
dagl           |  da + gll'
dalla          |  da + la
dalle          |  da + le
di             |  of
del            |  di + il
dello          |  di + lo
dei            |  di + i
degli          |  di + gli
dell           |  di + l'
degl           |  di + gl'
della          |  di + la
delle          |  di + le
in             |  in
nel            |  in + el
nello          |  in + lo
nei            |  in + i
negli          |  in + gli
nell           |  in + l'
negl           |  in + gl'
nella          |  in + la
nelle          |  in + le
su             |  on
sul            |  su + il
sullo          |  su + lo
sui            |  su + i
sugli          |  su + gli
sull           |  su + l'
sugl           |  su + gl'
sulla          |  su + la
sulle          |  su + le
per            |  through, by
tra            |  among
contro         |  against
io             |  I
tu             |  thou
lui            |  he
lei            |  she
noi            |  we
voi            |  you
loro           |  they
mio            |  my
mia            |
miei           |
mie            |
tuo            |
tua            |
tuoi           |  thy
tue            |
suo            |
sua            |
suoi           |  his, her
sue            |
nostro         |  our
nostra         |
nostri         |
nostre         |
vostro         |  your
vostra         |
vostri         |
vostre         |
mi             |  me
ti             |  thee
ci             |  us, there
vi             |  you, there
lo             |  him, the
la             |  her, the
li             |  them
le             |  them, the
gli            |  to him, the
ne             |  from there etc
il             |  the
un             |  a
uno            |  a
una            |  a
ma             |  but
ed             |  and
se             |  if
perché         |  why, because
anche          |  also
come           |  how
dov            |  where (as dov')
dove           |  where
che            |  who, that
chi            |  who
cui            |  whom
non            |  not
più            |  more
quale          |  who, that
quanto         |  how much
quanti         |
quanta         |
quante         |
quello         |  that
quelli         |
quella         |
quelle         |
questo         |  this
questi         |
questa         |
queste         |
si             |  yes
tutto          |  all
tutti          |  all

               |  single letter forms:

a              |  at
c              |  as c' for ce or ci
e              |  and
i              |  the
l              |  as l'
o              |  or

               | forms of avere, to have (not including the infinitive):

ho
hai
ha
abbiamo
avete
hanno
abbia
abbiate
abbiano
avrò
avrai
avrà
avremo
avrete
avranno
avrei
avresti
avrebbe
avremmo
avreste
avrebbero
avevo
avevi
aveva
avevamo
avevate
avevano
ebbi
avesti
ebbe
avemmo
aveste
ebbero
avessi
avesse
avessimo
avessero
avendo
avuto
avuta
avuti
avute

               | forms of essere, to be (not including the infinitive):
sono
sei
è
siamo
siete
sia
siate
siano
sarò
sarai
sarà
saremo
sarete
saranno
sarei
saresti
sarebbe
saremmo
sareste
sarebbero
ero
eri
era
eravamo
eravate
erano
fui
fosti
fu
fummo
foste
furono
fossi
fosse
fossimo
fossero
essendo

               | forms of fare, to do (not including the infinitive, fa, fat-):
faccio
fai
facciamo
fanno
faccia
facciate
facciano
farò
farai
farà
faremo
farete
faranno
farei
faresti
farebbe
faremmo
fareste
farebbero
facevo
facevi
faceva
facevamo
facevate
facevano
feci
facesti
fece
facemmo
faceste
fecero
facessi
facesse
facessimo
facessero
facendo

               | forms of stare, to be (not including the infinitive):
sto
stai
sta
stiamo
stanno
stia
stiate
stiano
starò
starai
starà
staremo
starete
staranno
starei
staresti
starebbe
staremmo
stareste
starebbero
stavo
stavi
stava
stavamo
stavate
stavano
stetti
stesti
stette
stemmo
steste
stettero
stessi
stesse
stessimo
stessero
''')


class SearchItalian(SearchLanguage):
    lang = 'it'
    language_name = 'Italian'
    js_stemmer_rawcode = 'italian-stemmer.js'
    stopwords = italian_stopwords

    def init(self, options: dict) -> None:
        self.stemmer = snowballstemmer.stemmer('italian')

    def stem(self, word: str) -> str:
        return self.stemmer.stemWord(word.lower())
