"""Danish search language: includes the JS Danish stemmer."""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict

import snowballstemmer

from sphinx.search import SearchLanguage, parse_stop_word

danish_stopwords = parse_stop_word('''
| source: http://snowball.tartarus.org/algorithms/danish/stop.txt
og           | and
i            | in
jeg          | I
det          | that (dem. pronoun)/it (pers. pronoun)
at           | that (in front of a sentence)/to (with infinitive)
en           | a/an
den          | it (pers. pronoun)/that (dem. pronoun)
til          | to/at/for/until/against/by/of/into, more
er           | present tense of "to be"
som          | who, as
på           | on/upon/in/on/at/to/after/of/with/for, on
de           | they
med          | with/by/in, along
han          | he
af           | of/by/from/off/for/in/with/on, off
for          | at/for/to/from/by/of/ago, in front/before, because
ikke         | not
der          | who/which, there/those
var          | past tense of "to be"
mig          | me/myself
sig          | oneself/himself/herself/itself/themselves
men          | but
et           | a/an/one, one (number), someone/somebody/one
har          | present tense of "to have"
om           | round/about/for/in/a, about/around/down, if
vi           | we
min          | my
havde        | past tense of "to have"
ham          | him
hun          | she
nu           | now
over         | over/above/across/by/beyond/past/on/about, over/past
da           | then, when/as/since
fra          | from/off/since, off, since
du           | you
ud           | out
sin          | his/her/its/one's
dem          | them
os           | us/ourselves
op           | up
man          | you/one
hans         | his
hvor         | where
eller        | or
hvad         | what
skal         | must/shall etc.
selv         | myself/yourself/herself/ourselves etc., even
her          | here
alle         | all/everyone/everybody etc.
vil          | will (verb)
blev         | past tense of "to stay/to remain/to get/to become"
kunne        | could
ind          | in
når          | when
være         | present tense of "to be"
dog          | however/yet/after all
noget        | something
ville        | would
jo           | you know/you see (adv), yes
deres        | their/theirs
efter        | after/behind/according to/for/by/from, later/afterwards
ned          | down
skulle       | should
denne        | this
end          | than
dette        | this
mit          | my/mine
også         | also
under        | under/beneath/below/during, below/underneath
have         | have
dig          | you
anden        | other
hende        | her
mine         | my
alt          | everything
meget        | much/very, plenty of
sit          | his, her, its, one's
sine         | his, her, its, one's
vor          | our
mod          | against
disse        | these
hvis         | if
din          | your/yours
nogle        | some
hos          | by/at
blive        | be/become
mange        | many
ad           | by/through
bliver       | present tense of "to be/to become"
hendes       | her/hers
været        | be
thi          | for (conj)
jer          | you
sådan        | such, like this/like that
''')


class SearchDanish(SearchLanguage):
    lang = 'da'
    language_name = 'Danish'
    js_stemmer_rawcode = 'danish-stemmer.js'
    stopwords = danish_stopwords

    def init(self, options: dict) -> None:
        self.stemmer = snowballstemmer.stemmer('danish')

    def stem(self, word: str) -> str:
        return self.stemmer.stemWord(word.lower())
