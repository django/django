module('admin.DateTimeShortcuts');

test('init', function(assert) {
    var $ = django.jQuery;

    var dateField = $('<input type="text" class="vDateField" value="2015-03-16"><br>');
    $('#qunit-fixture').append(dateField);

    DateTimeShortcuts.init();

    var shortcuts = $('.datetimeshortcuts');
    assert.equal(shortcuts.length, 1);
    assert.equal(shortcuts.find('a:first').text(), 'Today');
    assert.equal(shortcuts.find('a:last .date-icon').length, 1);
});
