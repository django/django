"""
Utility functions for generating "lorem ipsum" Latin text.
"""

import random

COMMON_P = (
    'Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod '
    'tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim '
    'veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea '
    'commodo consequat. Duis aute irure dolor in reprehenderit in voluptate '
    'velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint '
    'occaecat cupidatat non proident, sunt in culpa qui officia deserunt '
    'mollit anim id est laborum.'
)

WORDS = (
    'exercitationem', 'perferendis', 'perspiciatis', 'laborum', 'eveniet',
    'sunt', 'iure', 'nam', 'nobis', 'eum', 'cum', 'officiis', 'excepturi',
    'odio', 'consectetur', 'quasi', 'aut', 'quisquam', 'vel', 'eligendi',
    'itaque', 'non', 'odit', 'tempore', 'quaerat', 'dignissimos',
    'facilis', 'neque', 'nihil', 'expedita', 'vitae', 'vero', 'ipsum',
    'nisi', 'animi', 'cumque', 'pariatur', 'velit', 'modi', 'natus',
    'iusto', 'eaque', 'sequi', 'illo', 'sed', 'ex', 'et', 'voluptatibus',
    'tempora', 'veritatis', 'ratione', 'assumenda', 'incidunt', 'nostrum',
    'placeat', 'aliquid', 'fuga', 'provident', 'praesentium', 'rem',
    'necessitatibus', 'suscipit', 'adipisci', 'quidem', 'possimus',
    'voluptas', 'debitis', 'sint', 'accusantium', 'unde', 'sapiente',
    'voluptate', 'qui', 'aspernatur', 'laudantium', 'soluta', 'amet',
    'quo', 'aliquam', 'saepe', 'culpa', 'libero', 'ipsa', 'dicta',
    'reiciendis', 'nesciunt', 'doloribus', 'autem', 'impedit', 'minima',
    'maiores', 'repudiandae', 'ipsam', 'obcaecati', 'ullam', 'enim',
    'totam', 'delectus', 'ducimus', 'quis', 'voluptates', 'dolores',
    'molestiae', 'harum', 'dolorem', 'quia', 'voluptatem', 'molestias',
    'magni', 'distinctio', 'omnis', 'illum', 'dolorum', 'voluptatum', 'ea',
    'quas', 'quam', 'corporis', 'quae', 'blanditiis', 'atque', 'deserunt',
    'laboriosam', 'earum', 'consequuntur', 'hic', 'cupiditate',
    'quibusdam', 'accusamus', 'ut', 'rerum', 'error', 'minus', 'eius',
    'ab', 'ad', 'nemo', 'fugit', 'officia', 'at', 'in', 'id', 'quos',
    'reprehenderit', 'numquam', 'iste', 'fugiat', 'sit', 'inventore',
    'beatae', 'repellendus', 'magnam', 'recusandae', 'quod', 'explicabo',
    'doloremque', 'aperiam', 'consequatur', 'asperiores', 'commodi',
    'optio', 'dolor', 'labore', 'temporibus', 'repellat', 'veniam',
    'architecto', 'est', 'esse', 'mollitia', 'nulla', 'a', 'similique',
    'eos', 'alias', 'dolore', 'tenetur', 'deleniti', 'porro', 'facere',
    'maxime', 'corrupti',
)

COMMON_WORDS = (
    'lorem', 'ipsum', 'dolor', 'sit', 'amet', 'consectetur',
    'adipisicing', 'elit', 'sed', 'do', 'eiusmod', 'tempor', 'incididunt',
    'ut', 'labore', 'et', 'dolore', 'magna', 'aliqua',
)


def sentence():
    """
    Return a randomly generated sentence of lorem ipsum text.

    The first word is capitalized, and the sentence ends in either a period or
    question mark. Commas are added at random.
    """
    # Determine the number of comma-separated sections and number of words in
    # each section for this sentence.
    sections = [' '.join(random.sample(WORDS, random.randint(3, 12))) for i in range(random.randint(1, 5))]
    s = ', '.join(sections)
    # Convert to sentence case and add end punctuation.
    return '%s%s%s' % (s[0].upper(), s[1:], random.choice('?.'))


def paragraph():
    """
    Return a randomly generated paragraph of lorem ipsum text.

    The paragraph consists of between 1 and 4 sentences, inclusive.
    """
    return ' '.join(sentence() for i in range(random.randint(1, 4)))


def paragraphs(count, common=True):
    """
    Return a list of paragraphs as returned by paragraph().

    If `common` is True, then the first paragraph will be the standard
    'lorem ipsum' paragraph. Otherwise, the first paragraph will be random
    Latin text. Either way, subsequent paragraphs will be random Latin text.
    """
    paras = []
    for i in range(count):
        if common and i == 0:
            paras.append(COMMON_P)
        else:
            paras.append(paragraph())
    return paras


def words(count, common=True):
    """
    Return a string of `count` lorem ipsum words separated by a single space.

    If `common` is True, then the first 19 words will be the standard
    'lorem ipsum' words. Otherwise, all words will be selected randomly.
    """
    word_list = list(COMMON_WORDS) if common else []
    c = len(word_list)
    if count > c:
        count -= c
        while count > 0:
            c = min(count, len(WORDS))
            count -= c
            word_list += random.sample(WORDS, c)
    else:
        word_list = word_list[:count]
    return ' '.join(word_list)
