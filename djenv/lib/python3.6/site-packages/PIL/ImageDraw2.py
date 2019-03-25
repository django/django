#
# The Python Imaging Library
# $Id$
#
# WCK-style drawing interface operations
#
# History:
# 2003-12-07 fl   created
# 2005-05-15 fl   updated; added to PIL as ImageDraw2
# 2005-05-15 fl   added text support
# 2005-05-20 fl   added arc/chord/pieslice support
#
# Copyright (c) 2003-2005 by Secret Labs AB
# Copyright (c) 2003-2005 by Fredrik Lundh
#
# See the README file for information on usage and redistribution.
#

from . import Image, ImageColor, ImageDraw, ImageFont, ImagePath


class Pen(object):
    def __init__(self, color, width=1, opacity=255):
        self.color = ImageColor.getrgb(color)
        self.width = width


class Brush(object):
    def __init__(self, color, opacity=255):
        self.color = ImageColor.getrgb(color)


class Font(object):
    def __init__(self, color, file, size=12):
        # FIXME: add support for bitmap fonts
        self.color = ImageColor.getrgb(color)
        self.font = ImageFont.truetype(file, size)


class Draw(object):

    def __init__(self, image, size=None, color=None):
        if not hasattr(image, "im"):
            image = Image.new(image, size, color)
        self.draw = ImageDraw.Draw(image)
        self.image = image
        self.transform = None

    def flush(self):
        return self.image

    def render(self, op, xy, pen, brush=None):
        # handle color arguments
        outline = fill = None
        width = 1
        if isinstance(pen, Pen):
            outline = pen.color
            width = pen.width
        elif isinstance(brush, Pen):
            outline = brush.color
            width = brush.width
        if isinstance(brush, Brush):
            fill = brush.color
        elif isinstance(pen, Brush):
            fill = pen.color
        # handle transformation
        if self.transform:
            xy = ImagePath.Path(xy)
            xy.transform(self.transform)
        # render the item
        if op == "line":
            self.draw.line(xy, fill=outline, width=width)
        else:
            getattr(self.draw, op)(xy, fill=fill, outline=outline)

    def settransform(self, offset):
        (xoffset, yoffset) = offset
        self.transform = (1, 0, xoffset, 0, 1, yoffset)

    def arc(self, xy, start, end, *options):
        self.render("arc", xy, start, end, *options)

    def chord(self, xy, start, end, *options):
        self.render("chord", xy, start, end, *options)

    def ellipse(self, xy, *options):
        self.render("ellipse", xy, *options)

    def line(self, xy, *options):
        self.render("line", xy, *options)

    def pieslice(self, xy, start, end, *options):
        self.render("pieslice", xy, start, end, *options)

    def polygon(self, xy, *options):
        self.render("polygon", xy, *options)

    def rectangle(self, xy, *options):
        self.render("rectangle", xy, *options)

    def text(self, xy, text, font):
        if self.transform:
            xy = ImagePath.Path(xy)
            xy.transform(self.transform)
        self.draw.text(xy, text, font=font.font, fill=font.color)

    def textsize(self, text, font):
        return self.draw.textsize(text, font=font.font)
