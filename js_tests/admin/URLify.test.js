/* global QUnit, URLify */
/* eslint global-strict: 0, strict: 0 */
'use strict';

QUnit.module('admin.URLify');

QUnit.test('empty string', function(assert) {
    assert.strictEqual(URLify('', 8, true), '');
});

QUnit.test('strip nonessential words', function(assert) {
    assert.strictEqual(URLify('the D is silent', 8, true), 'd-silent');
});

QUnit.test('strip non-URL characters', function(assert) {
    assert.strictEqual(URLify('D#silent@', 7, true), 'dsilent');
});

QUnit.test('merge adjacent whitespace', function(assert) {
    assert.strictEqual(URLify('D   silent', 8, true), 'd-silent');
});

QUnit.test('trim trailing hyphens', function(assert) {
    assert.strictEqual(URLify('D silent always', 9, true), 'd-silent');
});

QUnit.test('do not remove English words if the string contains non-ASCII', function(assert) {
    // If removing English words wasn't skipped, the last 'a' would be removed.
    assert.strictEqual(URLify('Kaupa-miða', 255, true), 'kaupa-miða');
});
