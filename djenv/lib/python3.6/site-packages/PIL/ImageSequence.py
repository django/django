#
# The Python Imaging Library.
# $Id$
#
# sequence support classes
#
# history:
# 1997-02-20 fl     Created
#
# Copyright (c) 1997 by Secret Labs AB.
# Copyright (c) 1997 by Fredrik Lundh.
#
# See the README file for information on usage and redistribution.
#

##


class Iterator(object):
    """
    This class implements an iterator object that can be used to loop
    over an image sequence.

    You can use the ``[]`` operator to access elements by index. This operator
    will raise an :py:exc:`IndexError` if you try to access a nonexistent
    frame.

    :param im: An image object.
    """

    def __init__(self, im):
        if not hasattr(im, "seek"):
            raise AttributeError("im must have seek method")
        self.im = im
        self.position = 0

    def __getitem__(self, ix):
        try:
            self.im.seek(ix)
            return self.im
        except EOFError:
            raise IndexError  # end of sequence

    def __iter__(self):
        return self

    def __next__(self):
        try:
            self.im.seek(self.position)
            self.position += 1
            return self.im
        except EOFError:
            raise StopIteration

    def next(self):
        return self.__next__()
