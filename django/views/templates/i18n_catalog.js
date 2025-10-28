{% autoescape off %}
'use strict';
{
  const globals = this;
  const django = globals.django || (globals.django = {});

  {% if plural %}
  django.pluralidx = function(n) {
    const v = {{ plural }};
    if (typeof v === 'boolean') {
      return v ? 1 : 0;
    } else {
      return v;
    }
  };
  {% else %}
  django.pluralidx = function(count) { return (count == 1) ? 0 : 1; };
  {% endif %}

  /* gettext library */

  django.catalog = django.catalog || {};
  {% if catalog_str %}
  const newcatalog = {{ catalog_str }};
  for (const key in newcatalog) {
    django.catalog[key] = newcatalog[key];
  }
  {% endif %}

  function getValueFromCatalog(msgid, index) {
    const value = django.catalog[msgid];

    // if value in catalog is a string, return it
    if (typeof value === 'string' && value) {
      return value;
    }

    // if value in catalog is an array and index is present, return the array index if exists
    if (value && value.constructor === Array && index !== undefined) {
      const text = value[index];

      if (typeof text === 'string' && text) {
        return text;
      }
    }

    return undefined;
  }

  if (!django.jsi18n_initialized) {
    django.gettext = function(msgid) {
      const value = getValueFromCatalog(msgid, 0);

      return value !== undefined ? value : msgid;
    };

    django.ngettext = function(singular, plural, count) {
      const value = getValueFromCatalog(singular, django.pluralidx(count));

      if (value !== undefined) {
        return value;
      } else {
        return (count == 1) ? singular : plural;
      }
    };

    django.gettext_noop = function(msgid) { return msgid; };

    django.pgettext = function(context, msgid) {
      let value = django.gettext(context + '\x04' + msgid);
      if (value.includes('\x04')) {
        value = msgid;
      }
      return value;
    };

    django.npgettext = function(context, singular, plural, count) {
      let value = django.ngettext(context + '\x04' + singular, context + '\x04' + plural, count);
      if (value.includes('\x04')) {
        value = django.ngettext(singular, plural, count);
      }
      return value;
    };

    django.interpolate = function(fmt, obj, named) {
      if (named) {
        return fmt.replace(/%\(\w+\)s/g, function(match){return String(obj[match.slice(2,-2)])});
      } else {
        return fmt.replace(/%s/g, function(match){return String(obj.shift())});
      }
    };


    /* formatting library */

    django.formats = {{ formats_str }};

    django.get_format = function(format_type) {
      const value = django.formats[format_type];
      if (typeof value === 'undefined') {
        return format_type;
      } else {
        return value;
      }
    };

    /* add to global namespace */
    globals.pluralidx = django.pluralidx;
    globals.gettext = django.gettext;
    globals.ngettext = django.ngettext;
    globals.gettext_noop = django.gettext_noop;
    globals.pgettext = django.pgettext;
    globals.npgettext = django.npgettext;
    globals.interpolate = django.interpolate;
    globals.get_format = django.get_format;

    django.jsi18n_initialized = true;
  }
};
{% endautoescape %}
