/**
 * Load the shared admin globals in the same order as js_tests/tests.html:
 * jQuery, the django.jQuery namespace shim, the i18n mocks and core.js.
 * Import this module for its side effects before loading any admin script
 * that depends on those globals.
 */
import core from "../../django/contrib/admin/static/admin/js/core.js?raw";
import jqueryInit from "../../django/contrib/admin/static/admin/js/jquery.init.js?raw";
import jquery from "../../django/contrib/admin/static/admin/js/vendor/jquery/jquery.min.js?raw";
import jsi18nMocks from "../admin/jsi18n-mocks.test.js?raw";
import { loadClassicScript } from "./helpers.js";

for (const source of [jquery, jqueryInit, jsi18nMocks, core]) {
    loadClassicScript(source);
}
