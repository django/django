import json
import os
import re
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.template import Context, Engine
from django.urls import translate_url
from django.utils.formats import get_format
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import check_for_language, get_language
from django.utils.translation.trans_real import DjangoTranslation
from django.views.generic import View

LANGUAGE_QUERY_PARAMETER = "language"


def builtin_template_path(name):
    """
    Return a path to a builtin template.

    Avoid calling this function at the module level or in a class-definition
    because __file__ may not exist, e.g. in frozen environments.
    """
    return Path(__file__).parent / "templates" / name


def set_language(request):
    """
    Redirect to a given URL while setting the chosen language in the language
    cookie. The URL and the language code need to be specified in the request
    parameters.

    Since this view changes how the user will see the rest of the site, it must
    only be accessed as a POST request. If called as a GET request, it will
    redirect to the page in the request (the 'next' parameter) without changing
    any state.
    """
    next_url = request.POST.get("next", request.GET.get("next"))
    if (
        next_url or request.accepts("text/html")
    ) and not url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        next_url = request.META.get("HTTP_REFERER")
        if not url_has_allowed_host_and_scheme(
            url=next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            next_url = "/"
    response = HttpResponseRedirect(next_url) if next_url else HttpResponse(status=204)
    if request.method == "POST":
        lang_code = request.POST.get(LANGUAGE_QUERY_PARAMETER)
        if lang_code and check_for_language(lang_code):
            if next_url:
                next_trans = translate_url(next_url, lang_code)
                if next_trans != next_url:
                    response = HttpResponseRedirect(next_trans)
            response.set_cookie(
                settings.LANGUAGE_COOKIE_NAME,
                lang_code,
                max_age=settings.LANGUAGE_COOKIE_AGE,
                path=settings.LANGUAGE_COOKIE_PATH,
                domain=settings.LANGUAGE_COOKIE_DOMAIN,
                secure=settings.LANGUAGE_COOKIE_SECURE,
                httponly=settings.LANGUAGE_COOKIE_HTTPONLY,
                samesite=settings.LANGUAGE_COOKIE_SAMESITE,
            )
    return response


def get_formats():
    """Return all formats strings required for i18n to work."""
    FORMAT_SETTINGS = (
        "DATE_FORMAT",
        "DATETIME_FORMAT",
        "TIME_FORMAT",
        "YEAR_MONTH_FORMAT",
        "MONTH_DAY_FORMAT",
        "SHORT_DATE_FORMAT",
        "SHORT_DATETIME_FORMAT",
        "FIRST_DAY_OF_WEEK",
        "DECIMAL_SEPARATOR",
        "THOUSAND_SEPARATOR",
        "NUMBER_GROUPING",
        "DATE_INPUT_FORMATS",
        "TIME_INPUT_FORMATS",
        "DATETIME_INPUT_FORMATS",
    )
    return {attr: get_format(attr) for attr in FORMAT_SETTINGS}


class JavaScriptCatalog(View):
    """
    Return the selected language catalog as a JavaScript library.

    Receive the list of packages to check for translations in the `packages`
    kwarg either from the extra dictionary passed to the path() function or as
    a plus-sign delimited string from the request. Default is 'django.conf'.

    You can override the gettext domain for this view, but usually you don't
    want to do that as JavaScript messages go to the djangojs domain. This
    might be needed if you deliver your JavaScript source from Django templates.
    """

    domain = "djangojs"
    packages = None

    def get(self, request, *args, **kwargs):
        locale = get_language()
        domain = kwargs.get("domain", self.domain)
        # If packages are not provided, default to all installed packages, as
        # DjangoTranslation without localedirs harvests them all.
        packages = kwargs.get("packages", "")
        packages = packages.split("+") if packages else self.packages
        paths = self.get_paths(packages) if packages else None
        self.translation = DjangoTranslation(locale, domain=domain, localedirs=paths)
        context = self.get_context_data(**kwargs)
        return self.render_to_response(context)

    def get_paths(self, packages):
        allowable_packages = {
            app_config.name: app_config for app_config in apps.get_app_configs()
        }
        app_configs = [
            allowable_packages[p] for p in packages if p in allowable_packages
        ]
        if len(app_configs) < len(packages):
            excluded = [p for p in packages if p not in allowable_packages]
            raise ValueError(
                "Invalid package(s) provided to JavaScriptCatalog: %s"
                % ",".join(excluded)
            )
        # paths of requested packages
        return [os.path.join(app.path, "locale") for app in app_configs]

    @property
    def _num_plurals(self):
        """
        Return the number of plurals for this catalog language, or 2 if no
        plural string is available.
        """
        match = re.search(r"nplurals=\s*(\d+)", self._plural_string or "")
        if match:
            return int(match[1])
        return 2

    @property
    def _plural_string(self):
        """
        Return the plural string (including nplurals) for this catalog language,
        or None if no plural string is available.
        """
        if "" in self.translation._catalog:
            for line in self.translation._catalog[""].split("\n"):
                if line.startswith("Plural-Forms:"):
                    return line.split(":", 1)[1].strip()
        return None

    def get_plural(self):
        plural = self._plural_string
        if plural is not None:
            # This should be a compiled function of a typical plural-form:
            # Plural-Forms: nplurals=3; plural=n%10==1 && n%100!=11 ? 0 :
            #               n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2;
            plural = [
                el.strip()
                for el in plural.split(";")
                if el.strip().startswith("plural=")
            ][0].split("=", 1)[1]
        return plural

    def get_catalog(self):
        pdict = {}
        catalog = {}
        translation = self.translation
        seen_keys = set()
        while True:
            for key, value in translation._catalog.items():
                if key == "" or key in seen_keys:
                    continue
                if isinstance(key, str):
                    catalog[key] = value
                elif isinstance(key, tuple):
                    msgid, cnt = key
                    pdict.setdefault(msgid, {})[cnt] = value
                else:
                    raise TypeError(key)
                seen_keys.add(key)
            if translation._fallback:
                translation = translation._fallback
            else:
                break

        num_plurals = self._num_plurals
        for k, v in pdict.items():
            catalog[k] = [v.get(i, "") for i in range(num_plurals)]
        return catalog

    def get_context_data(self, **kwargs):
        return {
            "catalog": self.get_catalog(),
            "formats": get_formats(),
            "plural": self.get_plural(),
        }

    def render_to_response(self, context, **response_kwargs):
        def indent(s):
            return s.replace("\n", "\n  ")

        with builtin_template_path("i18n_catalog.js").open(encoding="utf-8") as fh:
            template = Engine().from_string(fh.read())
        context["catalog_str"] = (
            indent(json.dumps(context["catalog"], sort_keys=True, indent=2))
            if context["catalog"]
            else None
        )
        context["formats_str"] = indent(
            json.dumps(context["formats"], sort_keys=True, indent=2)
        )

        return HttpResponse(
            template.render(Context(context)), 'text/javascript; charset="utf-8"'
        )


class JSONCatalog(JavaScriptCatalog):
    """
    Return the selected language catalog as a JSON object.

    Receive the same parameters as JavaScriptCatalog and return a response
    with a JSON object of the following format:

        {
            "catalog": {
                # Translations catalog
            },
            "formats": {
                # Language formats for date, time, etc.
            },
            "plural": '...'  # Expression for plural forms, or null.
        }
    """

    def render_to_response(self, context, **response_kwargs):
        return JsonResponse(context)
