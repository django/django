/* global URLify */
import { describe, expect, test } from "vitest";
import urlify from "../../../django/contrib/admin/static/admin/js/urlify.js?raw";
import xregexp from "../../../django/contrib/admin/static/admin/js/vendor/xregexp/xregexp.min.js?raw";
import { loadClassicScript } from "../helpers.js";

// urlify.js relies on the XRegExp global when allowUnicode is true.
loadClassicScript(xregexp);
loadClassicScript(urlify);

describe("admin.URLify", () => {
    test("empty string", () => {
        expect(URLify("", 8, true)).toBe("");
    });

    test("preserve nonessential words", () => {
        expect(URLify("the D is silent", 15, true)).toBe("the-d-is-silent");
    });

    test("strip non-URL characters", () => {
        expect(URLify("D#silent@", 7, true)).toBe("dsilent");
    });

    test("merge adjacent whitespace", () => {
        expect(URLify("D   silent", 8, true)).toBe("d-silent");
    });

    test("trim trailing hyphens", () => {
        expect(URLify("D silent always", 9, true)).toBe("d-silent");
    });

    test("non-ASCII string", () => {
        expect(URLify("Kaupa-miða", 255, true)).toBe("kaupa-miða");
    });
});
