# Django Core Package (`django`)

## 1. Module Identity
The `django` package is the central entry point of the Django web framework. It provides version information, a helper `setup()` routine that initializes Django’s configuration, logging and app registry, and re‑exports the most commonly used public classes (`AppConfig`, `apps`) and settings utilities.

## 2. Interface Contract
### Exported symbols (``django/__init__.py``)
| Name | Type | Description |
|------|------|-------------|
| `VERSION` | tuple | Raw version tuple `(major, minor, micro, releaselevel, serial)`. |
| `__version__` | str | Human‑readable version string produced by `django.utils.version.get_version`. |
| `setup(set_prefix=True)` | function | Initializes Django: configures logging, sets the URL script prefix, and populates the app registry. |
| `AppConfig` | class (re‑export) | Base class for application configuration objects (`django.apps.config.AppConfig`). |
| `apps` | `django.apps.registry.Apps` instance | Global application registry. |

### Settings utilities (``django/conf/__init__.py``)
* `SettingsReference` – string subclass that serialises to a settings attribute reference.
* `LazySettings` – lazy proxy that loads the settings module on first access.
* Constants: `ENVIRONMENT_VARIABLE`, `DEFAULT_STORAGE_ALIAS`, `STATICFILES_STORAGE_ALIAS`.

## 3. Logic Flow
1. **Import time** – Importing `django` triggers the import of `django.utils.version.get_version` to compute `__version__`.
2. **`setup()` execution** –
   a. Imports `django.apps.apps` and `django.conf.settings`.
   b. Calls `django.utils.log.configure_logging` with the project's `LOGGING_CONFIG` and `LOGGING` dict.
   c. If `set_prefix` is true, determines the script prefix (`"/"` or `settings.FORCE_SCRIPT_NAME`) and calls `django.urls.set_script_prefix`.
   d. Finally, invokes `apps.populate(settings.INSTALLED_APPS)` to register all installed applications.
3. **App registry** – `django.apps.registry.Apps` maintains a mapping of app labels to `AppConfig` instances. The registry is populated during `setup()` and is later used by Django’s internals (model loading, URL resolution, etc.).
4. **Settings handling** – `django.conf.__init__` defines `LazySettings`, which lazily imports the module named by the `DJANGO_SETTINGS_MODULE` environment variable. When accessed, it merges user settings with `django.conf.global_settings`. `SettingsReference` objects allow deferred resolution of setting values.
5. **Locale information** – `django/conf/locale/__init__.py` provides `LANG_INFO`, a dictionary used by the internationalisation subsystem to map language codes to metadata (bidi flag, display names, etc.).

## 4. Dependencies
| Dependent Module | Reason |
|------------------|--------|
| `django.utils.version` | Generates the public version string. |
| `django.apps` (config, registry) | Provides `AppConfig` class and the global `apps` registry used by `setup()`. |
| `django.conf.settings` | User‑defined settings module accessed by `LazySettings`. |
| `django.utils.log` | Configures logging according to the project's `LOGGING` configuration. |
| `django.urls` | Sets the script prefix for URL resolution. |
| `django.core.exceptions` | Used in `conf/__init__.py` for error handling (e.g., `ImproperlyConfigured`). |
| `django.utils.functional` | Supplies `LazyObject` base class for `LazySettings`. |
| `django.conf.global_settings` | Base set of default settings merged with user settings. |
| `django.conf.locale` | Supplies language metadata for i18n. |

These dependencies are internal to the Django code‑base; the package does not rely on any third‑party libraries at import time.

---
*This README is generated automatically by the Documentation Consistency Enforcer to reflect the current implementation of the `django` core package.*