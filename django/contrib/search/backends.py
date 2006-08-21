from default import DefaultIndexer

try:
    from xapian import XapianIndexer
except ImportError:
    print "Xapian backend will not be available due to an ImportError. " \
          "Do you have Xapian and Xapwrap installed?"

try:
    from lucene import LuceneIndexer
except ImportError:
    print "Lucene backend will not be available due to an ImportError. " \
          "Do you have Lucene and PyLucene installed?"

try:
    from hype import HypeIndexer
except ImportError:
    print "Hyper Estraier backend will not be available due to an importError. " \
          "Do you have Hyper Estraier and Hype installed?"
