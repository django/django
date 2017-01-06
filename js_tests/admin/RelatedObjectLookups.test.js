/* global QUnit, id_to_windowname,
   windowname_to_id, dismissAddRelatedObjectPopup */
/* eslint global-strict: 0, strict: 0 */
'use strict';

QUnit.module('admin.RelatedObjectLookups', {
    beforeEach: function() {
        this.win = {name: 'id_teacher', close: function() {}};
    }
});

QUnit.test('id_to_windowname', function(assert) {
    assert.equal(id_to_windowname('.test'), '__dot__test');
    assert.equal(id_to_windowname('misc-test'), 'misc__dash__test');
});

QUnit.test('windowname_to_id', function(assert) {
    assert.equal(windowname_to_id('__dot__test'), '.test');
    assert.equal(windowname_to_id('misc__dash__test'), 'misc-test');
});

QUnit.test('dismissAddRelatedObjectPopup/Select', function(assert) {
    var $ = django.jQuery;
    $('<div class="related-widget-wrapper"></div>').appendTo('#qunit-fixture');
    $('<select id="id_teacher" name="teacher"></select>').appendTo('div.related-widget-wrapper');
    $('<option value="" selected="">---------</option>').appendTo('#id_teacher');

    dismissAddRelatedObjectPopup(this.win, '1', 'Alex');
    assert.equal($('#id_teacher').find('option').length, 2);
    assert.equal($('#id_teacher').find('option').last().text(), 'Alex');
    assert.ok($('#id_teacher').find('option').last()[0].selected);

    dismissAddRelatedObjectPopup(this.win, '1', 'Susan');
    assert.equal($('#id_teacher').find('option').length, 3);
    assert.equal($('#id_teacher').find('option').last().text(), 'Susan');
    // Only the last new item is marked as checked.
    assert.equal($('#id_teacher').find('option:selected').length, 1);
    assert.ok($('#id_teacher').find('option').last()[0].selected);
});

QUnit.test('dismissAddRelatedObjectPopup/SelectMultiple', function(assert) {
    var $ = django.jQuery;
    $('<div class="related-widget-wrapper"></div>').appendTo('#qunit-fixture');
    $('<select multiple="multiple" id="id_teacher" name="teacher"></select>').appendTo('div.related-widget-wrapper');

    dismissAddRelatedObjectPopup(this.win, '1', 'Alex');
    assert.equal($('#id_teacher').find('option').length, 1);
    assert.equal($('#id_teacher').find('option').first().text(), 'Alex');
    assert.ok($('#id_teacher').find('option').first()[0].selected);

    dismissAddRelatedObjectPopup(this.win, '2', 'Susan');
    assert.equal($('#id_teacher').find('option').length, 2);
    assert.equal($('#id_teacher').find('option').last().text(), 'Susan');
    // All new items are marked as checked.
    assert.equal($('#id_teacher').find('option:selected').length, 2);
    assert.ok($('#id_teacher').find('option').first()[0].selected);
    assert.ok($('#id_teacher').find('option').last()[0].selected);
});

QUnit.test('dismissAddRelatedObjectPopup/TextInput', function(assert) {
    var $ = django.jQuery;
    $('<div class="related-widget-wrapper"></div>').appendTo('#qunit-fixture');
    $('<input id="id_teacher" name="teacher" type="text" value="">').appendTo('div.related-widget-wrapper');

    dismissAddRelatedObjectPopup(this.win, '1', 'Alex');
    assert.equal($('#id_teacher').val(), '1');

    dismissAddRelatedObjectPopup(this.win, '2', 'Susan');
    assert.equal($('#id_teacher').val(), '2');
});

QUnit.test('dismissAddRelatedObjectPopup/TextInput.vManyToManyRawIdAdminField', function(assert) {
    var $ = django.jQuery;
    $('<div class="related-widget-wrapper"></div>').appendTo('#qunit-fixture');
    $('<input id="id_teacher" name="teacher" type="text" value="" class="vManyToManyRawIdAdminField">').appendTo(
        'div.related-widget-wrapper'
    );

    dismissAddRelatedObjectPopup(this.win, '1', 'Alex');
    assert.equal($('#id_teacher').val(), '1');

    dismissAddRelatedObjectPopup(this.win, '2', 'Susan');
    assert.equal($('#id_teacher').val(), '1,2');
});

QUnit.test('dismissAddRelatedObjectPopup/RadioSelect', function(assert) {
    var $ = django.jQuery;
    $('<div class="related-widget-wrapper"></div>').appendTo('#qunit-fixture');
    $('<ul id="id_teacher" data-wrap-label="true" data-multiple="false"></ul>').appendTo('div.related-widget-wrapper');

    // Add the first item.
    dismissAddRelatedObjectPopup(this.win, '1', 'Alex');
    assert.equal($('#id_teacher').find('li').length, 1);
    assert.equal($('input#id_teacher_0').length, 1);
    assert.equal($('input#id_teacher_0').val(), 1);
    assert.equal($('#id_teacher').find('li').last().find('label').text(), ' Alex');
    assert.equal($('#id_teacher').find('input').last()[0].type, "radio");
    assert.ok($('#id_teacher').find('input').last()[0].checked);

    // Add the other item.
    dismissAddRelatedObjectPopup(this.win, '2', 'Susan');
    assert.equal($('#id_teacher').find('li').length, 2);
    assert.equal($('input#id_teacher_1').length, 1);
    assert.equal($('input#id_teacher_1').val(), 2);
    assert.equal($('#id_teacher').find('li').last().find('label').text(), ' Susan');
    assert.equal($('#id_teacher').find('input').last()[0].type, "radio");
    // Only the last new item is marked as checked like the select behavior.
    assert.equal($('#id_teacher').find('input:checked').length, 1);
    assert.notOk($('#id_teacher').find('input').first()[0].checked);
    assert.ok($('#id_teacher').find('input').last()[0].checked);
});

QUnit.test('dismissAddRelatedObjectPopup/CheckboxSelectMultiple', function(assert) {
    var $ = django.jQuery;
    $('<div class="related-widget-wrapper"></div>').appendTo('#qunit-fixture');
    $('<ul id="id_teacher" data-wrap-label="true" data-multiple="true"></ul>').appendTo('div.related-widget-wrapper');

    // Add the first item.
    dismissAddRelatedObjectPopup(this.win, '1', 'Alex');
    assert.equal($('#id_teacher').find('li').length, 1);
    assert.equal($('input#id_teacher_0').length, 1);
    assert.equal($('input#id_teacher_0').val(), 1);
    assert.equal($('#id_teacher').find('li').first().find('label').text(), ' Alex');
    assert.equal($('#id_teacher').find('input').first()[0].type, "checkbox");
    assert.ok($('#id_teacher').find('input').first()[0].checked);

    // Add the other item.
    dismissAddRelatedObjectPopup(this.win, '2', 'Susan');
    assert.equal($('#id_teacher').find('li').length, 2);
    assert.equal($('input#id_teacher_1').length, 1);
    assert.equal($('input#id_teacher_1').val(), 2);
    assert.equal($('#id_teacher').find('li').last().find('label').text(), ' Susan');
    assert.equal($('#id_teacher').find('input').last()[0].type, "checkbox");
    // All new items are marked as checked like the select multiple behavior.
    assert.equal($('#id_teacher').find('input:checked').length, 2);
    assert.ok($('#id_teacher').find('input').first()[0].checked);
    assert.ok($('#id_teacher').find('input').last()[0].checked);
});

