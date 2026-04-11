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
from __future__ import annotations

import math
import struct
from collections.abc import Sequence
from typing import cast

from . import Image, ImageColor, ImageText

TYPE_CHECKING = False
if TYPE_CHECKING:
    from collections.abc import Callable
    from types import ModuleType
    from typing import Any, AnyStr

    from . import ImageDraw2, ImageFont
    from ._typing import Coords, _Ink

# experimental access to the outline API
Outline: Callable[[], Image.core._Outline] = Image.core.outline

"""
A simple 2D drawing interface for PIL images.
<p>
Application code should use the <b>Draw</b> factory, instead of
directly.
"""


class ImageDraw:
    font: (
        ImageFont.ImageFont | ImageFont.FreeTypeFont | ImageFont.TransposedFont | None
    ) = None

    def __init__(self, im: Image.Image, mode: str | None = None) -> None:
        """
        Create a drawing instance.

        :param im: The image to draw in.
        :param mode: Optional mode to use for color values.  For RGB
           images, this argument can be RGB or RGBA (to blend the
           drawing into the image).  For all other modes, this argument
           must be the same as the image mode.  If omitted, the mode
           defaults to the mode of the image.
        """
        im._ensure_mutable()
        blend = 0
        if mode is None:
            mode = im.mode
        if mode != im.mode:
            if mode == "RGBA" and im.mode == "RGB":
                blend = 1
            else:
                msg = "mode mismatch"
                raise ValueError(msg)
        if mode == "P":
            self.palette = im.palette
        else:
            self.palette = None
        self._image = im
        self.im = im.im
        self.draw = Image.core.draw(self.im, blend)
        self.mode = mode
        if mode in ("I", "F"):
            self.ink = self.draw.draw_ink(1)
        else:
            self.ink = self.draw.draw_ink(-1)
        if mode in ("1", "P", "I", "F"):
            # FIXME: fix Fill2 to properly support matte for I+F images
            self.fontmode = "1"
        else:
            self.fontmode = "L"  # aliasing is okay for other modes
        self.fill = False

    def getfont(
        self,
    ) -> ImageFont.ImageFont | ImageFont.FreeTypeFont | ImageFont.TransposedFont:
        """
        Get the current default font.

        To set the default font for this ImageDraw instance::

            from PIL import ImageDraw, ImageFont
            draw.font = ImageFont.truetype("Tests/fonts/FreeMono.ttf")

        To set the default font for all future ImageDraw instances::

            from PIL import ImageDraw, ImageFont
            ImageDraw.ImageDraw.font = ImageFont.truetype("Tests/fonts/FreeMono.ttf")

        If the current default font is ``None``,
        it is initialized with ``ImageFont.load_default()``.

        :returns: An image font."""
        if not self.font:
            # FIXME: should add a font repository
            from . import ImageFont

            self.font = ImageFont.load_default()
        return self.font

    def _getfont(
        self, font_size: float | None
    ) -> ImageFont.ImageFont | ImageFont.FreeTypeFont | ImageFont.TransposedFont:
        if font_size is not None:
            from . import ImageFont

            return ImageFont.load_default(font_size)
        else:
            return self.getfont()

    def _getink(
        self, ink: _Ink | None, fill: _Ink | None = None
    ) -> tuple[int | None, int | None]:
        result_ink = None
        result_fill = None
        if ink is None and fill is None:
            if self.fill:
                result_fill = self.ink
            else:
                result_ink = self.ink
        else:
            if ink is not None:
                if isinstance(ink, str):
                    ink = ImageColor.getcolor(ink, self.mode)
                if self.palette and isinstance(ink, tuple):
                    ink = self.palette.getcolor(ink, self._image)
                result_ink = self.draw.draw_ink(ink)
            if fill is not None:
                if isinstance(fill, str):
                    fill = ImageColor.getcolor(fill, self.mode)
                if self.palette and isinstance(fill, tuple):
                    fill = self.palette.getcolor(fill, self._image)
                result_fill = self.draw.draw_ink(fill)
        return result_ink, result_fill

    def arc(
        self,
        xy: Coords,
        start: float,
        end: float,
        fill: _Ink | None = None,
        width: int = 1,
    ) -> None:
        """Draw an arc."""
        ink, fill = self._getink(fill)
        if ink is not None:
            self.draw.draw_arc(xy, start, end, ink, width)

    def bitmap(
        self, xy: Sequence[int], bitmap: Image.Image, fill: _Ink | None = None
    ) -> None:
        """Draw a bitmap."""
        bitmap.load()
        ink, fill = self._getink(fill)
        if ink is None:
            ink = fill
        if ink is not None:
            self.draw.draw_bitmap(xy, bitmap.im, ink)

    def chord(
        self,
        xy: Coords,
        start: float,
        end: float,
        fill: _Ink | None = None,
        outline: _Ink | None = None,
        width: int = 1,
    ) -> None:
        """Draw a chord."""
        ink, fill_ink = self._getink(outline, fill)
        if fill_ink is not None:
            self.draw.draw_chord(xy, start, end, fill_ink, 1)
        if ink is not None and ink != fill_ink and width != 0:
            self.draw.draw_chord(xy, start, end, ink, 0, width)

    def ellipse(
        self,
        xy: Coords,
        fill: _Ink | None = None,
        outline: _Ink | None = None,
        width: int = 1,
    ) -> None:
        """Draw an ellipse."""
        ink, fill_ink = self._getink(outline, fill)
        if fill_ink is not None:
            self.draw.draw_ellipse(xy, fill_ink, 1)
        if ink is not None and ink != fill_ink and width != 0:
            self.draw.draw_ellipse(xy, ink, 0, width)

    def circle(
        self,
        xy: Sequence[float],
        radius: float,
        fill: _Ink | None = None,
        outline: _Ink | None = None,
        width: int = 1,
    ) -> None:
        """Draw a circle given center coordinates and a radius."""
        ellipse_xy = (xy[0] - radius, xy[1] - radius, xy[0] + radius, xy[1] + radius)
        self.ellipse(ellipse_xy, fill, outline, width)

    def line(
        self,
        xy: Coords,
        fill: _Ink | None = None,
        width: int = 0,
        joint: str | None = None,
    ) -> None:
        """Draw a line, or a connected sequence of line segments."""
        ink = self._getink(fill)[0]
        if ink is not None:
            self.draw.draw_lines(xy, ink, width)
            if joint == "curve" and width > 4:
                points: Sequence[Sequence[float]]
                if isinstance(xy[0], (list, tuple)):
                    points = cast(Sequence[Sequence[float]], xy)
                else:
                    points = [
                        cast(Sequence[float], tuple(xy[i : i + 2]))
                        for i in range(0, len(xy), 2)
                    ]
                for i in range(1, len(points) - 1):
                    point = points[i]
                    angles = [
                        math.degrees(math.atan2(end[0] - start[0], start[1] - end[1]))
                        % 360
                        for start, end in (
                            (points[i - 1], point),
                            (point, points[i + 1]),
                        )
                    ]
                    if angles[0] == angles[1]:
                        # This is a straight line, so no joint is required
                        continue

                    def coord_at_angle(
                        coord: Sequence[float], angle: float
                    ) -> tuple[float, ...]:
                        x, y = coord
                        angle -= 90
                        distance = width / 2 - 1
                        return tuple(
                            p + (math.floor(p_d) if p_d > 0 else math.ceil(p_d))
                            for p, p_d in (
                                (x, distance * math.cos(math.radians(angle))),
                                (y, distance * math.sin(math.radians(angle))),
                            )
                        )

                    flipped = (
                        angles[1] > angles[0] and angles[1] - 180 > angles[0]
                    ) or (angles[1] < angles[0] and angles[1] + 180 > angles[0])
                    coords = [
                        (point[0] - width / 2 + 1, point[1] - width / 2 + 1),
                        (point[0] + width / 2 - 1, point[1] + width / 2 - 1),
                    ]
                    if flipped:
                        start, end = (angles[1] + 90, angles[0] + 90)
                    else:
                        start, end = (angles[0] - 90, angles[1] - 90)
                    self.pieslice(coords, start - 90, end - 90, fill)

                    if width > 8:
                        # Cover potential gaps between the line and the joint
                        if flipped:
                            gap_coords = [
                                coord_at_angle(point, angles[0] + 90),
                                point,
                                coord_at_angle(point, angles[1] + 90),
                            ]
                        else:
                            gap_coords = [
                                coord_at_angle(point, angles[0] - 90),
                                point,
                                coord_at_angle(point, angles[1] - 90),
                            ]
                        self.line(gap_coords, fill, width=3)

    def shape(
        self,
        shape: Image.core._Outline,
        fill: _Ink | None = None,
        outline: _Ink | None = None,
    ) -> None:
        """(Experimental) Draw a shape."""
        shape.close()
        ink, fill_ink = self._getink(outline, fill)
        if fill_ink is not None:
            self.draw.draw_outline(shape, fill_ink, 1)
        if ink is not None and ink != fill_ink:
            self.draw.draw_outline(shape, ink, 0)

    def pieslice(
        self,
        xy: Coords,
        start: float,
        end: float,
        fill: _Ink | None = None,
        outline: _Ink | None = None,
        width: int = 1,
    ) -> None:
        """Draw a pieslice."""
        ink, fill_ink = self._getink(outline, fill)
        if fill_ink is not None:
            self.draw.draw_pieslice(xy, start, end, fill_ink, 1)
        if ink is not None and ink != fill_ink and width != 0:
            self.draw.draw_pieslice(xy, start, end, ink, 0, width)

    def point(self, xy: Coords, fill: _Ink | None = None) -> None:
        """Draw one or more individual pixels."""
        ink, fill = self._getink(fill)
        if ink is not None:
            self.draw.draw_points(xy, ink)

    def polygon(
        self,
        xy: Coords,
        fill: _Ink | None = None,
        outline: _Ink | None = None,
        width: int = 1,
    ) -> None:
        """Draw a polygon."""
        ink, fill_ink = self._getink(outline, fill)
        if fill_ink is not None:
            self.draw.draw_polygon(xy, fill_ink, 1)
        if ink is not None and ink != fill_ink and width != 0:
            if width == 1:
                self.draw.draw_polygon(xy, ink, 0, width)
            elif self.im is not None:
                # To avoid expanding the polygon outwards,
                # use the fill as a mask
                mask = Image.new("1", self.im.size)
                mask_ink = self._getink(1)[0]
                draw = Draw(mask)
                draw.draw.draw_polygon(xy, mask_ink, 1)

                self.draw.draw_polygon(xy, ink, 0, width * 2 - 1, mask.im)

    def regular_polygon(
        self,
        bounding_circle: Sequence[Sequence[float] | float],
        n_sides: int,
        rotation: float = 0,
        fill: _Ink | None = None,
        outline: _Ink | None = None,
        width: int = 1,
    ) -> None:
        """Draw a regular polygon."""
        xy = _compute_regular_polygon_vertices(bounding_circle, n_sides, rotation)
        self.polygon(xy, fill, outline, width)

    def rectangle(
        self,
        xy: Coords,
        fill: _Ink | None = None,
        outline: _Ink | None = None,
        width: int = 1,
    ) -> None:
        """Draw a rectangle."""
        ink, fill_ink = self._getink(outline, fill)
        if fill_ink is not None:
            self.draw.draw_rectangle(xy, fill_ink, 1)
        if ink is not None and ink != fill_ink and width != 0:
            self.draw.draw_rectangle(xy, ink, 0, width)

    def rounded_rectangle(
        self,
        xy: Coords,
        radius: float = 0,
        fill: _Ink | None = None,
        outline: _Ink | None = None,
        width: int = 1,
        *,
        corners: tuple[bool, bool, bool, bool] | None = None,
    ) -> None:
        """Draw a rounded rectangle."""
        if isinstance(xy[0], (list, tuple)):
            (x0, y0), (x1, y1) = cast(Sequence[Sequence[float]], xy)
        else:
            x0, y0, x1, y1 = cast(Sequence[float], xy)
        if x1 < x0:
            msg = "x1 must be greater than or equal to x0"
            raise ValueError(msg)
        if y1 < y0:
            msg = "y1 must be greater than or equal to y0"
            raise ValueError(msg)
        if corners is None:
            corners = (True, True, True, True)

        d = radius * 2

        x0 = round(x0)
        y0 = round(y0)
        x1 = round(x1)
        y1 = round(y1)
        full_x, full_y = False, False
        if all(corners):
            full_x = d >= x1 - x0 - 1
            if full_x:
                # The two left and two right corners are joined
                d = x1 - x0
            full_y = d >= y1 - y0 - 1
            if full_y:
                # The two top and two bottom corners are joined
                d = y1 - y0
            if full_x and full_y:
                # If all corners are joined, that is a circle
                return self.ellipse(xy, fill, outline, width)

        if d == 0 or not any(corners):
            # If the corners have no curve,
            # or there are no corners,
            # that is a rectangle
            return self.rectangle(xy, fill, outline, width)

        r = int(d // 2)
        ink, fill_ink = self._getink(outline, fill)

        def draw_corners(pieslice: bool) -> None:
            parts: tuple[tuple[tuple[float, float, float, float], int, int], ...]
            if full_x:
                # Draw top and bottom halves
                parts = (
                    ((x0, y0, x0 + d, y0 + d), 180, 360),
                    ((x0, y1 - d, x0 + d, y1), 0, 180),
                )
            elif full_y:
                # Draw left and right halves
                parts = (
                    ((x0, y0, x0 + d, y0 + d), 90, 270),
                    ((x1 - d, y0, x1, y0 + d), 270, 90),
                )
            else:
                # Draw four separate corners
                parts = tuple(
                    part
                    for i, part in enumerate(
                        (
                            ((x0, y0, x0 + d, y0 + d), 180, 270),
                            ((x1 - d, y0, x1, y0 + d), 270, 360),
                            ((x1 - d, y1 - d, x1, y1), 0, 90),
                            ((x0, y1 - d, x0 + d, y1), 90, 180),
                        )
                    )
                    if corners[i]
                )
            for part in parts:
                if pieslice:
                    self.draw.draw_pieslice(*(part + (fill_ink, 1)))
                else:
                    self.draw.draw_arc(*(part + (ink, width)))

        if fill_ink is not None:
            draw_corners(True)

            if full_x:
                self.draw.draw_rectangle((x0, y0 + r + 1, x1, y1 - r - 1), fill_ink, 1)
            elif x1 - r - 1 > x0 + r + 1:
                self.draw.draw_rectangle((x0 + r + 1, y0, x1 - r - 1, y1), fill_ink, 1)
            if not full_x and not full_y:
                left = [x0, y0, x0 + r, y1]
                if corners[0]:
                    left[1] += r + 1
                if corners[3]:
                    left[3] -= r + 1
                self.draw.draw_rectangle(left, fill_ink, 1)

                right = [x1 - r, y0, x1, y1]
                if corners[1]:
                    right[1] += r + 1
                if corners[2]:
                    right[3] -= r + 1
                self.draw.draw_rectangle(right, fill_ink, 1)
        if ink is not None and ink != fill_ink and width != 0:
            draw_corners(False)

            if not full_x:
                top = [x0, y0, x1, y0 + width - 1]
                if corners[0]:
                    top[0] += r + 1
                if corners[1]:
                    top[2] -= r + 1
                self.draw.draw_rectangle(top, ink, 1)

                bottom = [x0, y1 - width + 1, x1, y1]
                if corners[3]:
                    bottom[0] += r + 1
                if corners[2]:
                    bottom[2] -= r + 1
                self.draw.draw_rectangle(bottom, ink, 1)
            if not full_y:
                left = [x0, y0, x0 + width - 1, y1]
                if corners[0]:
                    left[1] += r + 1
                if corners[3]:
                    left[3] -= r + 1
                self.draw.draw_rectangle(left, ink, 1)

                right = [x1 - width + 1, y0, x1, y1]
                if corners[1]:
                    right[1] += r + 1
                if corners[2]:
                    right[3] -= r + 1
                self.draw.draw_rectangle(right, ink, 1)

    def text(
        self,
        xy: tuple[float, float],
        text: AnyStr | ImageText.Text,
        fill: _Ink | None = None,
        font: (
            ImageFont.ImageFont
            | ImageFont.FreeTypeFont
            | ImageFont.TransposedFont
            | None
        ) = None,
        anchor: str | None = None,
        spacing: float = 4,
        align: str = "left",
        direction: str | None = None,
        features: list[str] | None = None,
        language: str | None = None,
        stroke_width: float = 0,
        stroke_fill: _Ink | None = None,
        embedded_color: bool = False,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Draw text."""
        if isinstance(text, ImageText.Text):
            image_text = text
        else:
            if font is None:
                font = self._getfont(kwargs.get("font_size"))
            image_text = ImageText.Text(
                text, font, self.mode, spacing, direction, features, language
            )
            if embedded_color:
                image_text.embed_color()
            if stroke_width:
                image_text.stroke(stroke_width, stroke_fill)

        def getink(fill: _Ink | None) -> int:
            ink, fill_ink = self._getink(fill)
            if ink is None:
                assert fill_ink is not None
                return fill_ink
            return ink

        ink = getink(fill)
        if ink is None:
            return

        stroke_ink = None
        if image_text.stroke_width:
            stroke_ink = (
                getink(image_text.stroke_fill)
                if image_text.stroke_fill is not None
                else ink
            )

        for xy, anchor, line in image_text._split(xy, anchor, align):

            def draw_text(ink: int, stroke_width: float = 0) -> None:
                mode = self.fontmode
                if stroke_width == 0 and embedded_color:
                    mode = "RGBA"
                coord = []
                for i in range(2):
                    coord.append(int(xy[i]))
                start = (math.modf(xy[0])[0], math.modf(xy[1])[0])
                try:
                    mask, offset = image_text.font.getmask2(  # type: ignore[union-attr,misc]
                        line,
                        mode,
                        direction=direction,
                        features=features,
                        language=language,
                        stroke_width=stroke_width,
                        stroke_filled=True,
                        anchor=anchor,
                        ink=ink,
                        start=start,
                        *args,
                        **kwargs,
                    )
                    coord = [coord[0] + offset[0], coord[1] + offset[1]]
                except AttributeError:
                    try:
                        mask = image_text.font.getmask(  # type: ignore[misc]
                            line,
                            mode,
                            direction,
                            features,
                            language,
                            stroke_width,
                            anchor,
                            ink,
                            start=start,
                            *args,
                            **kwargs,
                        )
                    except TypeError:
                        mask = image_text.font.getmask(line)
                if mode == "RGBA":
                    # image_text.font.getmask2(mode="RGBA")
                    # returns color in RGB bands and mask in A
                    # extract mask and set text alpha
                    color, mask = mask, mask.getband(3)
                    ink_alpha = struct.pack("i", ink)[3]
                    color.fillband(3, ink_alpha)
                    x, y = coord
                    if self.im is not None:
                        self.im.paste(
                            color, (x, y, x + mask.size[0], y + mask.size[1]), mask
                        )
                else:
                    self.draw.draw_bitmap(coord, mask, ink)

            if stroke_ink is not None:
                # Draw stroked text
                draw_text(stroke_ink, image_text.stroke_width)

                # Draw normal text
                if ink != stroke_ink:
                    draw_text(ink)
            else:
                # Only draw normal text
                draw_text(ink)

    def multiline_text(
        self,
        xy: tuple[float, float],
        text: AnyStr,
        fill: _Ink | None = None,
        font: (
            ImageFont.ImageFont
            | ImageFont.FreeTypeFont
            | ImageFont.TransposedFont
            | None
        ) = None,
        anchor: str | None = None,
        spacing: float = 4,
        align: str = "left",
        direction: str | None = None,
        features: list[str] | None = None,
        language: str | None = None,
        stroke_width: float = 0,
        stroke_fill: _Ink | None = None,
        embedded_color: bool = False,
        *,
        font_size: float | None = None,
    ) -> None:
        return self.text(
            xy,
            text,
            fill,
            font,
            anchor,
            spacing,
            align,
            direction,
            features,
            language,
            stroke_width,
            stroke_fill,
            embedded_color,
            font_size=font_size,
        )

    def textlength(
        self,
        text: AnyStr,
        font: (
            ImageFont.ImageFont
            | ImageFont.FreeTypeFont
            | ImageFont.TransposedFont
            | None
        ) = None,
        direction: str | None = None,
        features: list[str] | None = None,
        language: str | None = None,
        embedded_color: bool = False,
        *,
        font_size: float | None = None,
    ) -> float:
        """Get the length of a given string, in pixels with 1/64 precision."""
        if font is None:
            font = self._getfont(font_size)
        image_text = ImageText.Text(
            text,
            font,
            self.mode,
            direction=direction,
            features=features,
            language=language,
        )
        if embedded_color:
            image_text.embed_color()
        return image_text.get_length()

    def textbbox(
        self,
        xy: tuple[float, float],
        text: AnyStr,
        font: (
            ImageFont.ImageFont
            | ImageFont.FreeTypeFont
            | ImageFont.TransposedFont
            | None
        ) = None,
        anchor: str | None = None,
        spacing: float = 4,
        align: str = "left",
        direction: str | None = None,
        features: list[str] | None = None,
        language: str | None = None,
        stroke_width: float = 0,
        embedded_color: bool = False,
        *,
        font_size: float | None = None,
    ) -> tuple[float, float, float, float]:
        """Get the bounding box of a given string, in pixels."""
        if font is None:
            font = self._getfont(font_size)
        image_text = ImageText.Text(
            text, font, self.mode, spacing, direction, features, language
        )
        if embedded_color:
            image_text.embed_color()
        if stroke_width:
            image_text.stroke(stroke_width)
        return image_text.get_bbox(xy, anchor, align)

    def multiline_textbbox(
        self,
        xy: tuple[float, float],
        text: AnyStr,
        font: (
            ImageFont.ImageFont
            | ImageFont.FreeTypeFont
            | ImageFont.TransposedFont
            | None
        ) = None,
        anchor: str | None = None,
        spacing: float = 4,
        align: str = "left",
        direction: str | None = None,
        features: list[str] | None = None,
        language: str | None = None,
        stroke_width: float = 0,
        embedded_color: bool = False,
        *,
        font_size: float | None = None,
    ) -> tuple[float, float, float, float]:
        return self.textbbox(
            xy,
            text,
            font,
            anchor,
            spacing,
            align,
            direction,
            features,
            language,
            stroke_width,
            embedded_color,
            font_size=font_size,
        )


def Draw(im: Image.Image, mode: str | None = None) -> ImageDraw:
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
        return getattr(im, "getdraw")(mode)
    except AttributeError:
        return ImageDraw(im, mode)


def getdraw(im: Image.Image | None = None) -> tuple[ImageDraw2.Draw | None, ModuleType]:
    """
    :param im: The image to draw in.
    :returns: A (drawing context, drawing resource factory) tuple.
    """
    from . import ImageDraw2

    draw = ImageDraw2.Draw(im) if im is not None else None
    return draw, ImageDraw2


def floodfill(
    image: Image.Image,
    xy: tuple[int, int],
    value: float | tuple[int, ...],
    border: float | tuple[int, ...] | None = None,
    thresh: float = 0,
) -> None:
    """
    .. warning:: This method is experimental.

    Fills a bounded region with a given color.

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
    assert pixel is not None
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
        for x, y in edge:  # 4 adjacent method
            for s, t in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                # If already processed, or if a coordinate is negative, skip
                if (s, t) in full_edge or s < 0 or t < 0:
                    continue
                try:
                    p = pixel[s, t]
                except (ValueError, IndexError):
                    pass
                else:
                    full_edge.add((s, t))
                    if border is None:
                        fill = _color_diff(p, background) <= thresh
                    else:
                        fill = p not in (value, border)
                    if fill:
                        pixel[s, t] = value
                        new_edge.add((s, t))
        full_edge = edge  # discard pixels processed
        edge = new_edge


def _compute_regular_polygon_vertices(
    bounding_circle: Sequence[Sequence[float] | float], n_sides: int, rotation: float
) -> list[tuple[float, float]]:
    """
    Generate a list of vertices for a 2D regular polygon.

    :param bounding_circle: The bounding circle is a sequence defined
        by a point and radius. The polygon is inscribed in this circle.
        (e.g. ``bounding_circle=(x, y, r)`` or ``((x, y), r)``)
    :param n_sides: Number of sides
        (e.g. ``n_sides=3`` for a triangle, ``6`` for a hexagon)
    :param rotation: Apply an arbitrary rotation to the polygon
        (e.g. ``rotation=90``, applies a 90 degree rotation)
    :return: List of regular polygon vertices
        (e.g. ``[(25, 50), (50, 50), (50, 25), (25, 25)]``)

    How are the vertices computed?
    1. Compute the following variables
        - theta: Angle between the apothem & the nearest polygon vertex
        - side_length: Length of each polygon edge
        - centroid: Center of bounding circle (1st, 2nd elements of bounding_circle)
        - polygon_radius: Polygon radius (last element of bounding_circle)
        - angles: Location of each polygon vertex in polar grid
            (e.g. A square with 0 degree rotation => [225.0, 315.0, 45.0, 135.0])

    2. For each angle in angles, get the polygon vertex at that angle
        The vertex is computed using the equation below.
            X= xcos(φ) + ysin(φ)
            Y= −xsin(φ) + ycos(φ)

        Note:
            φ = angle in degrees
            x = 0
            y = polygon_radius

        The formula above assumes rotation around the origin.
        In our case, we are rotating around the centroid.
        To account for this, we use the formula below
            X = xcos(φ) + ysin(φ) + centroid_x
            Y = −xsin(φ) + ycos(φ) + centroid_y
    """
    # 1. Error Handling
    # 1.1 Check `n_sides` has an appropriate value
    if not isinstance(n_sides, int):
        msg = "n_sides should be an int"  # type: ignore[unreachable]
        raise TypeError(msg)
    if n_sides < 3:
        msg = "n_sides should be an int > 2"
        raise ValueError(msg)

    # 1.2 Check `bounding_circle` has an appropriate value
    if not isinstance(bounding_circle, (list, tuple)):
        msg = "bounding_circle should be a sequence"
        raise TypeError(msg)

    if len(bounding_circle) == 3:
        if not all(isinstance(i, (int, float)) for i in bounding_circle):
            msg = "bounding_circle should only contain numeric data"
            raise ValueError(msg)

        *centroid, polygon_radius = cast(list[float], list(bounding_circle))
    elif len(bounding_circle) == 2 and isinstance(bounding_circle[0], (list, tuple)):
        if not all(
            isinstance(i, (int, float)) for i in bounding_circle[0]
        ) or not isinstance(bounding_circle[1], (int, float)):
            msg = "bounding_circle should only contain numeric data"
            raise ValueError(msg)

        if len(bounding_circle[0]) != 2:
            msg = "bounding_circle centre should contain 2D coordinates (e.g. (x, y))"
            raise ValueError(msg)

        centroid = cast(list[float], list(bounding_circle[0]))
        polygon_radius = cast(float, bounding_circle[1])
    else:
        msg = (
            "bounding_circle should contain 2D coordinates "
            "and a radius (e.g. (x, y, r) or ((x, y), r) )"
        )
        raise ValueError(msg)

    if polygon_radius <= 0:
        msg = "bounding_circle radius should be > 0"
        raise ValueError(msg)

    # 1.3 Check `rotation` has an appropriate value
    if not isinstance(rotation, (int, float)):
        msg = "rotation should be an int or float"  # type: ignore[unreachable]
        raise ValueError(msg)

    # 2. Define Helper Functions
    def _apply_rotation(point: list[float], degrees: float) -> tuple[float, float]:
        return (
            round(
                point[0] * math.cos(math.radians(360 - degrees))
                - point[1] * math.sin(math.radians(360 - degrees))
                + centroid[0],
                2,
            ),
            round(
                point[1] * math.cos(math.radians(360 - degrees))
                + point[0] * math.sin(math.radians(360 - degrees))
                + centroid[1],
                2,
            ),
        )

    def _compute_polygon_vertex(angle: float) -> tuple[float, float]:
        start_point = [polygon_radius, 0]
        return _apply_rotation(start_point, angle)

    def _get_angles(n_sides: int, rotation: float) -> list[float]:
        angles = []
        degrees = 360 / n_sides
        # Start with the bottom left polygon vertex
        current_angle = (270 - 0.5 * degrees) + rotation
        for _ in range(n_sides):
            angles.append(current_angle)
            current_angle += degrees
            if current_angle > 360:
                current_angle -= 360
        return angles

    # 3. Variable Declarations
    angles = _get_angles(n_sides, rotation)

    # 4. Compute Vertices
    return [_compute_polygon_vertex(angle) for angle in angles]


def _color_diff(
    color1: float | tuple[int, ...], color2: float | tuple[int, ...]
) -> float:
    """
    Uses 1-norm distance to calculate difference between two values.
    """
    first = color1 if isinstance(color1, tuple) else (color1,)
    second = color2 if isinstance(color2, tuple) else (color2,)

    return sum(abs(first[i] - second[i]) for i in range(len(second)))
