import os


class MediaTypes(object):

    def __init__(self, default='application/octet-stream', extra_types=None):
        self.types_map = default_types()
        self.default = default
        if extra_types:
            self.types_map.update(extra_types)

    def get_type(self, path):
        name = os.path.basename(path).lower()
        media_type = self.types_map.get(name)
        if media_type is not None:
            return media_type
        extension = os.path.splitext(name)[1]
        return self.types_map.get(extension, self.default)


def default_types():
    """
    We use our own set of default media types rather than the system-supplied
    ones. This ensures consistent media type behaviour across varied
    environments.  The defaults are based on those shipped with nginx, with
    some custom additions.
    """

    return {
        '.3gp': 'video/3gpp',
        '.3gpp': 'video/3gpp',
        '.7z': 'application/x-7z-compressed',
        '.ai': 'application/postscript',
        '.asf': 'video/x-ms-asf',
        '.asx': 'video/x-ms-asf',
        '.atom': 'application/atom+xml',
        '.avi': 'video/x-msvideo',
        '.bmp': 'image/x-ms-bmp',
        '.cco': 'application/x-cocoa',
        '.crt': 'application/x-x509-ca-cert',
        '.css': 'text/css',
        '.der': 'application/x-x509-ca-cert',
        '.doc': 'application/msword',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.ear': 'application/java-archive',
        '.eot': 'application/vnd.ms-fontobject',
        '.eps': 'application/postscript',
        '.flv': 'video/x-flv',
        '.gif': 'image/gif',
        '.hqx': 'application/mac-binhex40',
        '.htc': 'text/x-component',
        '.htm': 'text/html',
        '.html': 'text/html',
        '.ico': 'image/x-icon',
        '.jad': 'text/vnd.sun.j2me.app-descriptor',
        '.jar': 'application/java-archive',
        '.jardiff': 'application/x-java-archive-diff',
        '.jng': 'image/x-jng',
        '.jnlp': 'application/x-java-jnlp-file',
        '.jpeg': 'image/jpeg',
        '.jpg': 'image/jpeg',
        '.js': 'application/javascript',
        '.json': 'application/json',
        '.kar': 'audio/midi',
        '.kml': 'application/vnd.google-earth.kml+xml',
        '.kmz': 'application/vnd.google-earth.kmz',
        '.m3u8': 'application/vnd.apple.mpegurl',
        '.m4a': 'audio/x-m4a',
        '.m4v': 'video/x-m4v',
        '.mid': 'audio/midi',
        '.midi': 'audio/midi',
        '.mml': 'text/mathml',
        '.mng': 'video/x-mng',
        '.mov': 'video/quicktime',
        '.mp3': 'audio/mpeg',
        '.mp4': 'video/mp4',
        '.mpeg': 'video/mpeg',
        '.mpg': 'video/mpeg',
        '.ogg': 'audio/ogg',
        '.pdb': 'application/x-pilot',
        '.pdf': 'application/pdf',
        '.pem': 'application/x-x509-ca-cert',
        '.pl': 'application/x-perl',
        '.pm': 'application/x-perl',
        '.png': 'image/png',
        '.ppt': 'application/vnd.ms-powerpoint',
        '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        '.prc': 'application/x-pilot',
        '.ps': 'application/postscript',
        '.ra': 'audio/x-realaudio',
        '.rar': 'application/x-rar-compressed',
        '.rpm': 'application/x-redhat-package-manager',
        '.rss': 'application/rss+xml',
        '.rtf': 'application/rtf',
        '.run': 'application/x-makeself',
        '.sea': 'application/x-sea',
        '.shtml': 'text/html',
        '.sit': 'application/x-stuffit',
        '.svg': 'image/svg+xml',
        '.svgz': 'image/svg+xml',
        '.swf': 'application/x-shockwave-flash',
        '.tcl': 'application/x-tcl',
        '.tif': 'image/tiff',
        '.tiff': 'image/tiff',
        '.tk': 'application/x-tcl',
        '.ts': 'video/mp2t',
        '.txt': 'text/plain',
        '.war': 'application/java-archive',
        '.wbmp': 'image/vnd.wap.wbmp',
        '.webm': 'video/webm',
        '.webp': 'image/webp',
        '.wml': 'text/vnd.wap.wml',
        '.wmlc': 'application/vnd.wap.wmlc',
        '.wmv': 'video/x-ms-wmv',
        '.woff': 'application/font-woff',
        '.woff2': 'font/woff2',
        '.xhtml': 'application/xhtml+xml',
        '.xls': 'application/vnd.ms-excel',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.xml': 'text/xml',
        '.xpi': 'application/x-xpinstall',
        '.xspf': 'application/xspf+xml',
        '.zip': 'application/zip',
        'apple-app-site-association': 'application/pkc7-mime',
        # Adobe Products - see:
        # https://www.adobe.com/devnet-docs/acrobatetk/tools/AppSec/xdomain.html#policy-file-host-basics
        'crossdomain.xml': 'text/x-cross-domain-policy'
    }
