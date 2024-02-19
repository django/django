"""Hungarian search language: includes the JS Hungarian stemmer."""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict

import snowballstemmer

from sphinx.search import SearchLanguage, parse_stop_word

hungarian_stopwords = parse_stop_word('''
| source: http://snowball.tartarus.org/algorithms/hungarian/stop.txt
| prepared by Anna Tordai
a
ahogy
ahol
aki
akik
akkor
alatt
által
általában
amely
amelyek
amelyekben
amelyeket
amelyet
amelynek
ami
amit
amolyan
amíg
amikor
át
abban
ahhoz
annak
arra
arról
az
azok
azon
azt
azzal
azért
aztán
azután
azonban
bár
be
belül
benne
cikk
cikkek
cikkeket
csak
de
e
eddig
egész
egy
egyes
egyetlen
egyéb
egyik
egyre
ekkor
el
elég
ellen
elő
először
előtt
első
én
éppen
ebben
ehhez
emilyen
ennek
erre
ez
ezt
ezek
ezen
ezzel
ezért
és
fel
felé
hanem
hiszen
hogy
hogyan
igen
így
illetve
ill.
ill
ilyen
ilyenkor
ison
ismét
itt
jó
jól
jobban
kell
kellett
keresztül
keressünk
ki
kívül
között
közül
legalább
lehet
lehetett
legyen
lenne
lenni
lesz
lett
maga
magát
majd
majd
már
más
másik
meg
még
mellett
mert
mely
melyek
mi
mit
míg
miért
milyen
mikor
minden
mindent
mindenki
mindig
mint
mintha
mivel
most
nagy
nagyobb
nagyon
ne
néha
nekem
neki
nem
néhány
nélkül
nincs
olyan
ott
össze
ő
ők
őket
pedig
persze
rá
s
saját
sem
semmi
sok
sokat
sokkal
számára
szemben
szerint
szinte
talán
tehát
teljes
tovább
továbbá
több
úgy
ugyanis
új
újabb
újra
után
utána
utolsó
vagy
vagyis
valaki
valami
valamint
való
vagyok
van
vannak
volt
voltam
voltak
voltunk
vissza
vele
viszont
volna
''')


class SearchHungarian(SearchLanguage):
    lang = 'hu'
    language_name = 'Hungarian'
    js_stemmer_rawcode = 'hungarian-stemmer.js'
    stopwords = hungarian_stopwords

    def init(self, options: dict) -> None:
        self.stemmer = snowballstemmer.stemmer('hungarian')

    def stem(self, word: str) -> str:
        return self.stemmer.stemWord(word.lower())
