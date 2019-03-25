from . import Image

modules = {
    "pil": "PIL._imaging",
    "tkinter": "PIL._tkinter_finder",
    "freetype2": "PIL._imagingft",
    "littlecms2": "PIL._imagingcms",
    "webp": "PIL._webp",
}


def check_module(feature):
    if not (feature in modules):
        raise ValueError("Unknown module %s" % feature)

    module = modules[feature]

    try:
        __import__(module)
        return True
    except ImportError:
        return False


def get_supported_modules():
    return [f for f in modules if check_module(f)]


codecs = {
    "jpg": "jpeg",
    "jpg_2000": "jpeg2k",
    "zlib": "zip",
    "libtiff": "libtiff"
}


def check_codec(feature):
    if feature not in codecs:
        raise ValueError("Unknown codec %s" % feature)

    codec = codecs[feature]

    return codec + "_encoder" in dir(Image.core)


def get_supported_codecs():
    return [f for f in codecs if check_codec(f)]


features = {
    "webp_anim": ("PIL._webp", 'HAVE_WEBPANIM'),
    "webp_mux": ("PIL._webp", 'HAVE_WEBPMUX'),
    "transp_webp": ("PIL._webp", "HAVE_TRANSPARENCY"),
    "raqm": ("PIL._imagingft", "HAVE_RAQM"),
    "libjpeg_turbo": ("PIL._imaging", "HAVE_LIBJPEGTURBO"),
}


def check_feature(feature):
    if feature not in features:
        raise ValueError("Unknown feature %s" % feature)

    module, flag = features[feature]

    try:
        imported_module = __import__(module, fromlist=['PIL'])
        return getattr(imported_module, flag)
    except ImportError:
        return None


def get_supported_features():
    return [f for f in features if check_feature(f)]


def check(feature):
    return (feature in modules and check_module(feature) or
            feature in codecs and check_codec(feature) or
            feature in features and check_feature(feature))


def get_supported():
    ret = get_supported_modules()
    ret.extend(get_supported_features())
    ret.extend(get_supported_codecs())
    return ret
