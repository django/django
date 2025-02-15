{% autoescape off %}
'use strict';
{
  const globals = this;
  const thibaud = globals.thibaud || (globals.thibaud = {});

  {% if plural %}
  thibaud.pluralidx = function(n) {
    const v = {{ plural }};
    if (typeof v === 'boolean') {
      return v ? 1 : 0;
    } else {
      return v;
    }
  };
  {% else %}
  thibaud.pluralidx = function(count) { return (count == 1) ? 0 : 1; };
  {% endif %}

  /* gettext library */

  thibaud.catalog = thibaud.catalog || {};
  {% if catalog_str %}
  const newcatalog = {{ catalog_str }};
  for (const key in newcatalog) {
    thibaud.catalog[key] = newcatalog[key];
  }
  {% endif %}

  if (!thibaud.jsi18n_initialized) {
    thibaud.gettext = function(msgid) {
      const value = thibaud.catalog[msgid];
      if (typeof value === 'undefined') {
        return msgid;
      } else {
        return (typeof value === 'string') ? value : value[0];
      }
    };

    thibaud.ngettext = function(singular, plural, count) {
      const value = thibaud.catalog[singular];
      if (typeof value === 'undefined') {
        return (count == 1) ? singular : plural;
      } else {
        return value.constructor === Array ? value[thibaud.pluralidx(count)] : value;
      }
    };

    thibaud.gettext_noop = function(msgid) { return msgid; };

    thibaud.pgettext = function(context, msgid) {
      let value = thibaud.gettext(context + '\x04' + msgid);
      if (value.includes('\x04')) {
        value = msgid;
      }
      return value;
    };

    thibaud.npgettext = function(context, singular, plural, count) {
      let value = thibaud.ngettext(context + '\x04' + singular, context + '\x04' + plural, count);
      if (value.includes('\x04')) {
        value = thibaud.ngettext(singular, plural, count);
      }
      return value;
    };

    thibaud.interpolate = function(fmt, obj, named) {
      if (named) {
        return fmt.replace(/%\(\w+\)s/g, function(match){return String(obj[match.slice(2,-2)])});
      } else {
        return fmt.replace(/%s/g, function(match){return String(obj.shift())});
      }
    };


    /* formatting library */

    thibaud.formats = {{ formats_str }};

    thibaud.get_format = function(format_type) {
      const value = thibaud.formats[format_type];
      if (typeof value === 'undefined') {
        return format_type;
      } else {
        return value;
      }
    };

    /* add to global namespace */
    globals.pluralidx = thibaud.pluralidx;
    globals.gettext = thibaud.gettext;
    globals.ngettext = thibaud.ngettext;
    globals.gettext_noop = thibaud.gettext_noop;
    globals.pgettext = thibaud.pgettext;
    globals.npgettext = thibaud.npgettext;
    globals.interpolate = thibaud.interpolate;
    globals.get_format = thibaud.get_format;

    thibaud.jsi18n_initialized = true;
  }
};
{% endautoescape %}
