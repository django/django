"""Russian search language: includes the JS Russian stemmer."""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict

import snowballstemmer

from sphinx.search import SearchLanguage, parse_stop_word

russian_stopwords = parse_stop_word('''
| source: http://snowball.tartarus.org/algorithms/russian/stop.txt
и              | and
в              | in/into
во             | alternative form
не             | not
что            | what/that
он             | he
на             | on/onto
я              | i
с              | from
со             | alternative form
как            | how
а              | milder form of `no' (but)
то             | conjunction and form of `that'
все            | all
она            | she
так            | so, thus
его            | him
но             | but
да             | yes/and
ты             | thou
к              | towards, by
у              | around, chez
же             | intensifier particle
вы             | you
за             | beyond, behind
бы             | conditional/subj. particle
по             | up to, along
только         | only
ее             | her
мне            | to me
было           | it was
вот            | here is/are, particle
от             | away from
меня           | me
еще            | still, yet, more
нет            | no, there isnt/arent
о              | about
из             | out of
ему            | to him
теперь         | now
когда          | when
даже           | even
ну             | so, well
вдруг          | suddenly
ли             | interrogative particle
если           | if
уже            | already, but homonym of `narrower'
или            | or
ни             | neither
быть           | to be
был            | he was
него           | prepositional form of его
до             | up to
вас            | you accusative
нибудь         | indef. suffix preceded by hyphen
опять          | again
уж             | already, but homonym of `adder'
вам            | to you
сказал         | he said
ведь           | particle `after all'
там            | there
потом          | then
себя           | oneself
ничего         | nothing
ей             | to her
может          | usually with `быть' as `maybe'
они            | they
тут            | here
где            | where
есть           | there is/are
надо           | got to, must
ней            | prepositional form of  ей
для            | for
мы             | we
тебя           | thee
их             | them, their
чем            | than
была           | she was
сам            | self
чтоб           | in order to
без            | without
будто          | as if
человек        | man, person, one
чего           | genitive form of `what'
раз            | once
тоже           | also
себе           | to oneself
под            | beneath
жизнь          | life
будет          | will be
ж              | short form of intensifer particle `же'
тогда          | then
кто            | who
этот           | this
говорил        | was saying
того           | genitive form of `that'
потому         | for that reason
этого          | genitive form of `this'
какой          | which
совсем         | altogether
ним            | prepositional form of `его', `они'
здесь          | here
этом           | prepositional form of `этот'
один           | one
почти          | almost
мой            | my
тем            | instrumental/dative plural of `тот', `то'
чтобы          | full form of `in order that'
нее            | her (acc.)
кажется        | it seems
сейчас         | now
были           | they were
куда           | where to
зачем          | why
сказать        | to say
всех           | all (acc., gen. preposn. plural)
никогда        | never
сегодня        | today
можно          | possible, one can
при            | by
наконец        | finally
два            | two
об             | alternative form of `о', about
другой         | another
хоть           | even
после          | after
над            | above
больше         | more
тот            | that one (masc.)
через          | across, in
эти            | these
нас            | us
про            | about
всего          | in all, only, of all
них            | prepositional form of `они' (they)
какая          | which, feminine
много          | lots
разве          | interrogative particle
сказала        | she said
три            | three
эту            | this, acc. fem. sing.
моя            | my, feminine
впрочем        | moreover, besides
хорошо         | good
свою           | ones own, acc. fem. sing.
этой           | oblique form of `эта', fem. `this'
перед          | in front of
иногда         | sometimes
лучше          | better
чуть           | a little
том            | preposn. form of `that one'
нельзя         | one must not
такой          | such a one
им             | to them
более          | more
всегда         | always
конечно        | of course
всю            | acc. fem. sing of `all'
между          | between


  | b: some paradigms
  |
  | personal pronouns
  |
  | я  меня  мне  мной  [мною]
  | ты  тебя  тебе  тобой  [тобою]
  | он  его  ему  им  [него, нему, ним]
  | она  ее  эи  ею  [нее, нэи, нею]
  | оно  его  ему  им  [него, нему, ним]
  |
  | мы  нас  нам  нами
  | вы  вас  вам  вами
  | они  их  им  ими  [них, ним, ними]
  |
  |   себя  себе  собой   [собою]
  |
  | demonstrative pronouns: этот (this), тот (that)
  |
  | этот  эта  это  эти
  | этого  эты  это  эти
  | этого  этой  этого  этих
  | этому  этой  этому  этим
  | этим  этой  этим  [этою]  этими
  | этом  этой  этом  этих
  |
  | тот  та  то  те
  | того  ту  то  те
  | того  той  того  тех
  | тому  той  тому  тем
  | тем  той  тем  [тою]  теми
  | том  той  том  тех
  |
  | determinative pronouns
  |
  | (a) весь (all)
  |
  | весь  вся  все  все
  | всего  всю  все  все
  | всего  всей  всего  всех
  | всему  всей  всему  всем
  | всем  всей  всем  [всею]  всеми
  | всем  всей  всем  всех
  |
  | (b) сам (himself etc)
  |
  | сам  сама  само  сами
  | самого саму  само  самих
  | самого самой самого  самих
  | самому самой самому  самим
  | самим  самой  самим  [самою]  самими
  | самом самой самом  самих
  |
  | stems of verbs `to be', `to have', `to do' and modal
  |
  | быть  бы  буд  быв  есть  суть
  | име
  | дел
  | мог   мож  мочь
  | уме
  | хоч  хот
  | долж
  | можн
  | нужн
  | нельзя
''')


class SearchRussian(SearchLanguage):
    lang = 'ru'
    language_name = 'Russian'
    js_stemmer_rawcode = 'russian-stemmer.js'
    stopwords = russian_stopwords

    def init(self, options: dict) -> None:
        self.stemmer = snowballstemmer.stemmer('russian')

    def stem(self, word: str) -> str:
        return self.stemmer.stemWord(word.lower())
