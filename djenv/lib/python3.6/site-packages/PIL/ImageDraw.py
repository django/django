#
# The Python Imaging Library
# $Id$
#
# drawing interface operations
#
# History:
# 1996-04-13 fl   Created (experimental)
# 1996-08-07 fl   Filled polygons, ellipses.
# 1996-08-13 fl   Added text support
# 1998-06-28 fl   Handle I and F images
# 1998-12-29 fl   Added arc; use arc primitive to draw ellipses
# 1999-01-10 fl   Added shape stuff (experimental)
# 1999-02-06 fl   Added bitmap support
# 1999-02-11 fl   Changed all primitives to take options
# 1999-02-20 fl   Fixed backwards compatibility
# 2000-10-12 fl   Copy on write, when necessary
# 2001-02-18 fl   Use default ink for bitmap/text also in fill mode
# 2002-10-24 fl   Added support for CSS-style color strings
# 2002-12-10 fl   Added experimental support for RGBA-on-RGB drawing
# 2002-12-11 fl   Refactored low-level drawing API (work in progress)
# 2004-08-26 fl   Made Draw() a factory function, added getdraw() support
# 2004-09-04 fl   Added width support to line primitive
# 2004-09-10 fl   Added font mode handling
# 2006-06-19 fl   Added font bearing support (getmask2)
#
# Copyright (c) 1997-2006 by Secret Labs AB
# Copyright (c) 1996-2006 by Fredrik Lundh
#
# See the README file for information on usage and redistribution.
#

import math
import numbers

from . import Image, ImageColor
from ._util import isStringType

"""
A simple 2D drawing interface for PIL images.
<p>
Application code should use the <b>Draw</b> factory, instead of
directly.
"""


class ImageDraw(object):

    def __init__(self, im, mode=None):
        """
        Create a drawing instance.

        :param im: The image to draw in.
        :param mode: Optional mode to use for color values.  For RGB
           images, this argument can be RGB or RGBA (to blend the
           drawing into the image).  For all other modes, this argument
           must be the same as the image mode.  If omitted, the mode
           defaults to the mode of the image.
        """
        im.load()
        if im.readonly:
            im._copy()  # make it writeable
        blend = 0
        if mode is None:
            mode = im.mode
        if mode != im.mode:
            if mode == "RGBA" and im.mode == "RGB":
                blend = 1
            else:
                raise ValueError("mode mismatch")
        if mode == "P":
            self.palette = im.palette
        else:
            self.palette = None
        self.im = im.im
        self.draw = Image.core.draw(self.im, blend)
        self.mode = mode
        if mode in ("I", "F"):
            self.ink = self.draw.draw_ink(1, mode)
        else:
            self.ink = self.draw.draw_ink(-1, mode)
        if mode in ("1", "P", "I", "F"):
            # FIXME: fix Fill2 to properly support matte for I+F images
            self.fontmode = "1"
        else:
            self.fontmode = "L"  # aliasing is okay for other modes
        self.fill = 0
        self.font = None

    def getfont(self):
        """
        Get the current default font.

        :returns: An image font."""
        if not self.font:
            # FIXME: should add a font repository
            from . import ImageFont
            self.font = ImageFont.load_default()
        return self.font

    def _getink(self, ink, fill=None):
        if ink is None and fill is None:
            if self.fill:
                fill = self.ink
            else:
                ink = self.ink
        else:
            if ink is not None:
                if isStringType(ink):
                    ink = ImageColor.getcolor(ink, self.mode)
                if self.palette and not isinstance(ink, numbers.Number):
                    ink = self.palette.getcolor(ink)
                ink = self.draw.draw_ink(ink, self.mode)
            if fill is not None:
                if isStringType(fill):
                    fill = ImageColor.getcolor(fill, self.mode)
                if self.palette and not isinstance(fill, numbers.Number):
                    fill = self.palette.getcolor(fill)
                fill = self.draw.draw_ink(fill, self.mode)
        return ink, fill

    def arc(self, xy, start, end, fill=None, width=0):
        """Draw an arc."""
        ink, fill = self._getink(fill)
        if ink is not None:
            self.draw.draw_arc(xy, start, end, ink, width)

    def bitmap(self, xy, bitmap, fill=None):
        """Draw a bitmap."""
        bitmap.load()
        ink, fill = self._getink(fill)
        if ink is None:
            ink = fill
        if ink is not None:
            self.draw.draw_bitmap(xy, bitmap.im, ink)

    def chord(self, xy, start, end, fill=None, outline=None, width=0):
        """Draw a chord."""
        ink, fill = self._getink(outline, fill)
        if fill is not None:
            self.draw.draw_chord(xy, start, end, fill, 1)
        if ink is not None and ink != fill:
            self.draw.draw_chord(xy, start, end, ink, 0, width)

    def ellipse(self, xy, fill=None, outline=None, width=0):
        """Draw an ellipse."""
        ink, fill = self._getink(outline, fill)
        if fill is not None:
            self.draw.draw_ellipse(xy, fill, 1)
        if ink is not None and ink != fill:
            self.draw.draw_ellipse(xy, ink, 0, width)

    def line(self, xy, fill=None, width=0, joint=None):
        """Draw a line, or a connected sequence of line segments."""
        ink = self._getink(fill)[0]
        if ink is not None:
            self.draw.draw_lines(xy, ink, width)
            if joint == "curve" and width > 4:
                for i in range(1, len(xy)-1):
                    point = xy[i]
                    angles = [
                        math.degrees(math.atan2(
                            end[0] - start[0], start[1] - end[1]
                        )) % 360
                        for start, end in ((xy[i-1], point), (point, xy[i+1]))
                    ]
                    if angles[0] == angles[1]:
                        # This is a straight line, so no joint is required
                        continue

                    def coord_at_angle(coord, angle):
                        x, y = coord
                        angle -= 90
                        distance = width/2 - 1
                        return tuple([
                            p +
                            (math.floor(p_d) if p_d > 0 else math.ceil(p_d))
                            for p, p_d in
                            ((x, distance * math.cos(math.radians(angle))),
                             (y, distance * math.sin(math.radians(angle))))
                        ])
                    flipped = ((angles[1] > angles[0] and
                                angles[1] - 180 > angles[0]) or
                               (angles[1] < angles[0] and
                                angles[1] + 180 > angles[0]))
                    coords = [
                        (point[0] - width/2 + 1, point[1] - width/2 + 1),
                        (point[0] + width/2 - 1, point[1] + width/2 - 1)
                    ]
                    if flipped:
                        start, end = (angles[1] + 90, angles[0] + 90)
                    else:
                        start, end = (angles[0] - 90, angles[1] - 90)
                    self.pieslice(coords, start - 90, end - 90, fill)

                    if width > 8:
                        # Cover potential gaps between the line and the joint
                        if flipped:
                            gapCoords = [
                                coord_at_angle(point, angles[0]+90),
                                point,
                                coord_at_angle(point, angles[1]+90)
                            ]
                        else:
                            gapCoords = [
                                coord_at_angle(point, angles[0]-90),
                                point,
                                coord_at_angle(point, angles[1]-90)
                            ]
                        self.line(gapCoords, fill, width=3)

    def shape(self, shape, fill=None, outline=None):
        """(Experimental) Draw a shape."""
        shape.close()
        ink, fill = self._getink(outline, fill)
        if fill is not None:
            self.draw.draw_outline(shape, fill, 1)
        if ink is not None and ink != fill:
            self.draw.draw_outline(shape, ink, 0)

    def pieslice(self, xy, start, end, fill=None, outline=None, width=0):
        """Draw a pieslice."""
        ink, fill = self._getink(outline, fill)
        if fill is not None:
            self.draw.draw_pieslice(xy, start, end, fill, 1)
        if ink is not None and ink != fill:
            self.draw.draw_pieslice(xy, start, end, ink, 0, width)

    def point(self, xy, fill=None):
        """Draw one or more individual pixels."""
        ink, fill = self._getink(fill)
        if ink is not None:
            self.draw.draw_points(xy, ink)

    def polygon(self, xy, fill=None, outline=None):
        """Draw a polygon."""
        ink, fill = self._getink(outline, fill)
        if fill is not None:
            self.draw.draw_polygon(xy, fill, 1)
        if ink is not None and ink != fill:
            self.draw.draw_polygon(xy, ink, 0)

    def rectangle(self, xy, fill=None, outline=None, width=0):
        """Draw a rectangle."""
        ink, fill = self._getink(outline, fill)
        if fill is not None:
            self.draw.draw_rectangle(xy, fill, 1)
        if ink is not None and ink != fill:
            self.draw.draw_rectangle(xy, ink, 0, width)

    def _multiline_check(self, text):
        """Draw text."""
        split_character = "\n" if isinstance(text, str) else b"\n"

        return split_character in text

    def _multiline_split(self, text):
        split_character = "\n" if isinstance(text, str) else b"\n"

        return text.split(split_character)

    def text(self, xy, text, fill=None, font=None, anchor=None,
             *args, **kwargs):
        if self._multiline_check(text):
            return self.multiline_text(xy, text, fill, font, anchor,
                                       *args, **kwargs)
        ink, fill = self._getink(fill)
        if font is None:
            font = self.getfont()
        if ink is None:
            ink = fill
        if ink is not None:
            try:
                mask, offset = font.getmask2(text, self.fontmode,
                                             *args, **kwargs)
                xy = xy[0] + offset[0], xy[1] + offset[1]
            except AttributeError:
                try:
                    mask = font.getmask(text, self.fontmode, *args, **kwargs)
                except TypeError:
                    mask = font.getmask(text)
            self.draw.draw_bitmap(xy, mask, ink)

    def multiline_text(self, xy, text, fill=None, font=None, anchor=None,
                       spacing=4, align="left", direction=None, features=None):
        widths = []
        max_width = 0
        lines = self._multiline_split(text)
        line_spacing = self.textsize('A', font=font)[1] + spacing
        for line in lines:
            line_width, line_height = self.textsize(line, font)
            widths.append(line_width)
            max_width = max(max_width, line_width)
        left, top = xy
        for idx, line in enumerate(lines):
            if align == "left":
                pass  # left = x
            elif align == "center":
                left += (max_width - widths[idx]) / 2.0
            elif align == "right":
                left += (max_width - widths[idx])
            else:
                raise ValueError('align must be "left", "center" or "right"')
            self.text((left, top), line, fill, font, anchor,
                      direction=direction, features=features)
            top += line_spacing
            left = xy[0]

    def textsize(self, text, font=None, spacing=4, direction=None,
                 features=None):
        """Get the size of a given string, in pixels."""
        if self._multiline_check(text):
            return self.multiline_textsize(text, font, spacing,
                                           direction, features)

        if font is None:
            font = self.getfont()
        return font.getsize(text, direction, features)

    def multiline_textsize(self, text, font=None, spacing=4, direction=None,
                           features=None):
        max_width = 0
        lines = self._multiline_split(text)
        line_spacing = self.textsize('A', font=font)[1] + spacing
        for line in lines:
            line_width, line_height = self.textsize(line, font, spacing,
                                                    direction, features)
            max_width = max(max_width, line_width)
        return max_width, len(lines)*line_spacing - spacing


def Draw(im, mode=None):
    """
    A simple 2D drawing interface for PIL images.

    :param im: The image to draw in.
    :param mode: Optional mode to use for color values.  For RGB
       images, this argument can be RGB or RGBA (to blend the
       drawing into the image).  For all other modes, this argument
       must be the same as the image mode.  If omitted, the mode
       defaults to the mode of the image.
    """
    try:
        return im.getdraw(mode)
    except AttributeError:
        return ImageDraw(im, mode)


# experimental access to the outline API
try:
    Outline = Image.core.outline
except AttributeError:
    Outline = None


def getdraw(im=None, hints=None):
    """
    (Experimental) A more advanced 2D drawing interface for PIL images,
    based on the WCK interface.

    :param im: The image to draw in.
    :param hints: An optional list of hints.
    :returns: A (drawing context, drawing resource factory) tuple.
    """
    # FIXME: this needs more work!
    # FIXME: come up with a better 'hints' scheme.
    handler = None
    if not hints or "nicest" in hints:
        try:
            from . import _imagingagg as handler
        except ImportError:
            pass
    if handler is None:
        from . import ImageDraw2 as handler
    if im:
        im = handler.Draw(im)
    return im, handler


def floodfill(image, xy, value, border=None, thresh=0):
    """
    (experimental) Fills a bounded region with a given color.

    :param image: Target image.
    :param xy: Seed position (a 2-item coordinate tuple). See
        :ref:`coordinate-system`.
    :param value: Fill color.
    :param border: Optional border value.  If given, the region consists of
        pixels with a color different from the border color.  If not given,
        the region consists of pixels having the same color as the seed
        pixel.
    :param thresh: Optional threshold value which specifies a maximum
        tolerable difference of a pixel value from the 'background' in
        order for it to be replaced. Useful for filling regions of
        non-homogeneous, but similar, colors.
    """
    # based on an implementation by Eric S. Raymond
    # amended by yo1995 @20180806
    pixel = image.load()
    x, y = xy
    try:
        background = pixel[x, y]
        if _color_diff(value, background) <= thresh:
            return  # seed point already has fill color
        pixel[x, y] = value
    except (ValueError, IndexError):
        return  # seed point outside image
    edge = {(x, y)}
    # use a set to keep record of current and previous edge pixels
    # to reduce memory consumption
    full_edge = set()
    while edge:
        new_edge = set()
        for (x, y) in edge:  # 4 adjacent method
            for (s, t) in ((x+1, y), (x-1, y), (x, y+1), (x, y-1)):
                if (s, t) in full_edge:
                    continue  # if already processed, skip
                try:
                    p = pixel[s, t]
                except (ValueError, IndexError):
                    pass
                else:
                    full_edge.add((s, t))
                    if border is None:
                        fill = _color_diff(p, background) <= thresh
                    else:
                        fill = p != value and p != border
                    if fill:
                        pixel[s, t] = value
                        new_edge.add((s, t))
        full_edge = edge  # discard pixels processed
        edge = new_edge


def _color_diff(color1, color2):
    """
    Uses 1-norm distance to calculate difference between two values.
    """
    if isinstance(color2, tuple):
        return sum([abs(color1[i]-color2[i]) for i in range(0, len(color2))])
    else:
        return abs(color1-color2)
