"""Portuguese search language: includes the JS Portuguese stemmer."""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict

import snowballstemmer

from sphinx.search import SearchLanguage, parse_stop_word

portuguese_stopwords = parse_stop_word('''
| source: http://snowball.tartarus.org/algorithms/portuguese/stop.txt
de             |  of, from
a              |  the; to, at; her
o              |  the; him
que            |  who, that
e              |  and
do             |  de + o
da             |  de + a
em             |  in
um             |  a
para           |  for
  | é          from SER
com            |  with
não            |  not, no
uma            |  a
os             |  the; them
no             |  em + o
se             |  himself etc
na             |  em + a
por            |  for
mais           |  more
as             |  the; them
dos            |  de + os
como           |  as, like
mas            |  but
  | foi        from SER
ao             |  a + o
ele            |  he
das            |  de + as
  | tem        from TER
à              |  a + a
seu            |  his
sua            |  her
ou             |  or
  | ser        from SER
quando         |  when
muito          |  much
  | há         from HAV
nos            |  em + os; us
já             |  already, now
  | está       from EST
eu             |  I
também         |  also
só             |  only, just
pelo           |  per + o
pela           |  per + a
até            |  up to
isso           |  that
ela            |  he
entre          |  between
  | era        from SER
depois         |  after
sem            |  without
mesmo          |  same
aos            |  a + os
  | ter        from TER
seus           |  his
quem           |  whom
nas            |  em + as
me             |  me
esse           |  that
eles           |  they
  | estão      from EST
você           |  you
  | tinha      from TER
  | foram      from SER
essa           |  that
num            |  em + um
nem            |  nor
suas           |  her
meu            |  my
às             |  a + as
minha          |  my
  | têm        from TER
numa           |  em + uma
pelos          |  per + os
elas           |  they
  | havia      from HAV
  | seja       from SER
qual           |  which
  | será       from SER
nós            |  we
  | tenho      from TER
lhe            |  to him, her
deles          |  of them
essas          |  those
esses          |  those
pelas          |  per + as
este           |  this
  | fosse      from SER
dele           |  of him

 | other words. There are many contractions such as naquele = em+aquele,
 | mo = me+o, but they are rare.
 | Indefinite article plural forms are also rare.

tu             |  thou
te             |  thee
vocês          |  you (plural)
vos            |  you
lhes           |  to them
meus           |  my
minhas
teu            |  thy
tua
teus
tuas
nosso          | our
nossa
nossos
nossas

dela           |  of her
delas          |  of them

esta           |  this
estes          |  these
estas          |  these
aquele         |  that
aquela         |  that
aqueles        |  those
aquelas        |  those
isto           |  this
aquilo         |  that

               | forms of estar, to be (not including the infinitive):
estou
está
estamos
estão
estive
esteve
estivemos
estiveram
estava
estávamos
estavam
estivera
estivéramos
esteja
estejamos
estejam
estivesse
estivéssemos
estivessem
estiver
estivermos
estiverem

               | forms of haver, to have (not including the infinitive):
hei
há
havemos
hão
houve
houvemos
houveram
houvera
houvéramos
haja
hajamos
hajam
houvesse
houvéssemos
houvessem
houver
houvermos
houverem
houverei
houverá
houveremos
houverão
houveria
houveríamos
houveriam

               | forms of ser, to be (not including the infinitive):
sou
somos
são
era
éramos
eram
fui
foi
fomos
foram
fora
fôramos
seja
sejamos
sejam
fosse
fôssemos
fossem
for
formos
forem
serei
será
seremos
serão
seria
seríamos
seriam

               | forms of ter, to have (not including the infinitive):
tenho
tem
temos
tém
tinha
tínhamos
tinham
tive
teve
tivemos
tiveram
tivera
tivéramos
tenha
tenhamos
tenham
tivesse
tivéssemos
tivessem
tiver
tivermos
tiverem
terei
terá
teremos
terão
teria
teríamos
teriam
''')


class SearchPortuguese(SearchLanguage):
    lang = 'pt'
    language_name = 'Portuguese'
    js_stemmer_rawcode = 'portuguese-stemmer.js'
    stopwords = portuguese_stopwords

    def init(self, options: dict) -> None:
        self.stemmer = snowballstemmer.stemmer('portuguese')

    def stem(self, word: str) -> str:
        return self.stemmer.stemWord(word.lower())
