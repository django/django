module('admin.RelatedObjectLookups');

test('html_unescape', function(assert) {
    function assert_unescape(then, expected, message) {
        assert.equal(html_unescape(then), expected, message);
    }
    assert_unescape('&lt;', '<', 'less thans are unescaped');
    assert_unescape('&gt;', '>', 'greater thans are unescaped');
    assert_unescape('&quot;', '"', 'double quotes are unescaped');
    assert_unescape('&#39;', "'", 'single quotes are unescaped');
    assert_unescape('&amp;', '&', 'ampersands are unescaped');
});

test('id_to_windowname', function(assert) {
    assert.equal(id_to_windowname('.test'), '__dot__test');
    assert.equal(id_to_windowname('misc-test'), 'misc__dash__test');
});

test('windowname_to_id', function(assert) {
    assert.equal(windowname_to_id('__dot__test'), '.test');
    assert.equal(windowname_to_id('misc__dash__test'), 'misc-test');
});
