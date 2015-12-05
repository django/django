from django.conf import settings


def from_settings():
    return {
        'default-src': getattr(settings, 'CSP_DEFAULT_SRC', ["'self'"]),
        'script-src': getattr(settings, 'CSP_SCRIPT_SRC', None),
        'object-src': getattr(settings, 'CSP_OBJECT_SRC', None),
        'style-src': getattr(settings, 'CSP_STYLE_SRC', None),
        'img-src': getattr(settings, 'CSP_IMG_SRC', None),
        'media-src': getattr(settings, 'CSP_MEDIA_SRC', None),
        'frame-src': getattr(settings, 'CSP_FRAME_SRC', None),
        'font-src': getattr(settings, 'CSP_FONT_SRC', None),
        'connect-src': getattr(settings, 'CSP_CONNECT_SRC', None),
        'sandbox': getattr(settings, 'CSP_SANDBOX', None),
        'report-uri': getattr(settings, 'CSP_REPORT_URI', None),
    }


def build_policy(config=None, update=None, replace=None):
    """Builds the policy as a string from the settings."""

    if config is None:
        config = from_settings()

    # Update rules from settings.
    if update is not None:
        for k, v in update.items():
            if not isinstance(v, (list, tuple)):
                v = (v,)
            if config[k] is not None:
                config[k] += v
            else:
                config[k] = v

    # Replace rules from settings.
    if replace is not None:
        for k, v in replace.items():
            if v is not None and not isinstance(v, (list, tuple)):
                v = [v]
            config[k] = v

    report_uri = config.pop('report-uri', None)
    policy = ['%s %s' % (k, ' '.join(v)) for k, v in
              config.items() if v is not None]
    if report_uri:
        policy.append('report-uri %s' % report_uri)
    return '; '.join(policy)
