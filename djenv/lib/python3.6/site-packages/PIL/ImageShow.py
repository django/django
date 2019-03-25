#
# The Python Imaging Library.
# $Id$
#
# im.show() drivers
#
# History:
# 2008-04-06 fl   Created
#
# Copyright (c) Secret Labs AB 2008.
#
# See the README file for information on usage and redistribution.
#

from __future__ import print_function

from PIL import Image
import os
import sys
import subprocess
import tempfile

if sys.version_info.major >= 3:
    from shlex import quote
else:
    from pipes import quote

_viewers = []


def register(viewer, order=1):
    try:
        if issubclass(viewer, Viewer):
            viewer = viewer()
    except TypeError:
        pass  # raised if viewer wasn't a class
    if order > 0:
        _viewers.append(viewer)
    elif order < 0:
        _viewers.insert(0, viewer)


def show(image, title=None, **options):
    r"""
    Display a given image.

    :param image: An image object.
    :param title: Optional title.  Not all viewers can display the title.
    :param \**options: Additional viewer options.
    :returns: True if a suitable viewer was found, false otherwise.
    """
    for viewer in _viewers:
        if viewer.show(image, title=title, **options):
            return 1
    return 0


class Viewer(object):
    """Base class for viewers."""

    # main api

    def show(self, image, **options):

        # save temporary image to disk
        if image.mode[:4] == "I;16":
            # @PIL88 @PIL101
            # "I;16" isn't an 'official' mode, but we still want to
            # provide a simple way to show 16-bit images.
            base = "L"
            # FIXME: auto-contrast if max() > 255?
        else:
            base = Image.getmodebase(image.mode)
        if base != image.mode and image.mode != "1" and image.mode != "RGBA":
            image = image.convert(base)

        return self.show_image(image, **options)

    # hook methods

    format = None
    options = {}

    def get_format(self, image):
        """Return format name, or None to save as PGM/PPM"""
        return self.format

    def get_command(self, file, **options):
        raise NotImplementedError

    def save_image(self, image):
        """Save to temporary file, and return filename"""
        return image._dump(format=self.get_format(image), **self.options)

    def show_image(self, image, **options):
        """Display given image"""
        return self.show_file(self.save_image(image), **options)

    def show_file(self, file, **options):
        """Display given file"""
        os.system(self.get_command(file, **options))
        return 1

# --------------------------------------------------------------------


if sys.platform == "win32":

    class WindowsViewer(Viewer):
        format = "BMP"

        def get_command(self, file, **options):
            return ('start "Pillow" /WAIT "%s" '
                    '&& ping -n 2 127.0.0.1 >NUL '
                    '&& del /f "%s"' % (file, file))

    register(WindowsViewer)

elif sys.platform == "darwin":

    class MacViewer(Viewer):
        format = "PNG"
        options = {'compress_level': 1}

        def get_command(self, file, **options):
            # on darwin open returns immediately resulting in the temp
            # file removal while app is opening
            command = "open -a /Applications/Preview.app"
            command = "(%s %s; sleep 20; rm -f %s)&" % (command, quote(file),
                                                        quote(file))
            return command

        def show_file(self, file, **options):
            """Display given file"""
            fd, path = tempfile.mkstemp()
            with os.fdopen(fd, 'w') as f:
                f.write(file)
            with open(path, "r") as f:
                subprocess.Popen([
                    'im=$(cat);'
                    'open -a /Applications/Preview.app $im;'
                    'sleep 20;'
                    'rm -f $im'
                ], shell=True, stdin=f)
            os.remove(path)
            return 1

    register(MacViewer)

else:

    # unixoids

    def which(executable):
        path = os.environ.get("PATH")
        if not path:
            return None
        for dirname in path.split(os.pathsep):
            filename = os.path.join(dirname, executable)
            if os.path.isfile(filename) and os.access(filename, os.X_OK):
                return filename
        return None

    class UnixViewer(Viewer):
        format = "PNG"
        options = {'compress_level': 1}

        def get_command(self, file, **options):
            command = self.get_command_ex(file, **options)[0]
            return "(%s %s; rm -f %s)&" % (command, quote(file), quote(file))

        def show_file(self, file, **options):
            """Display given file"""
            fd, path = tempfile.mkstemp()
            with os.fdopen(fd, 'w') as f:
                f.write(file)
            with open(path, "r") as f:
                command = self.get_command_ex(file, **options)[0]
                subprocess.Popen([
                    'im=$(cat);' +
                    command+' $im;'
                    'rm -f $im'
                ], shell=True, stdin=f)
            os.remove(path)
            return 1

    # implementations

    class DisplayViewer(UnixViewer):
        def get_command_ex(self, file, **options):
            command = executable = "display"
            return command, executable

    if which("display"):
        register(DisplayViewer)

    class EogViewer(UnixViewer):
        def get_command_ex(self, file, **options):
            command = executable = "eog"
            return command, executable

    if which("eog"):
        register(EogViewer)

    class XVViewer(UnixViewer):
        def get_command_ex(self, file, title=None, **options):
            # note: xv is pretty outdated.  most modern systems have
            # imagemagick's display command instead.
            command = executable = "xv"
            if title:
                command += " -name %s" % quote(title)
            return command, executable

    if which("xv"):
        register(XVViewer)

if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("Syntax: python ImageShow.py imagefile [title]")
        sys.exit()

    print(show(Image.open(sys.argv[1]), *sys.argv[2:]))
