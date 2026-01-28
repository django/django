/* global QUnit, SelectBox */
'use strict';

QUnit.module('admin.SelectBox');

QUnit.test('init: no options', function(assert) {
    const $ = django.jQuery;
    $('<select id="id"></select>').appendTo('#qunit-fixture');
    SelectBox.init('id');
    assert.equal(SelectBox.cache.id.length, 0);
});

QUnit.test('filter', function(assert) {
    const $ = django.jQuery;
    $('<select id="id"></select>').appendTo('#qunit-fixture');
    $('<option value="0">A</option>').appendTo('#id');
    $('<option value="1">B</option>').appendTo('#id');
    SelectBox.init('id');
    assert.equal($('#id option').length, 2);
    SelectBox.filter('id', "A");
    assert.equal($('#id option').length, 1);
    assert.equal($('#id option').text(), "A");
});

QUnit.test('preserve scroll position', function(assert) {
    const $ = django.jQuery;
    const optionsCount = 100;
    $('<select id="from_id" multiple></select>').appendTo('#qunit-fixture');
    $('<select id="to_id" multiple></select>').appendTo('#qunit-fixture');
    const fromSelectBox = document.getElementById('from_id');
    const toSelectBox = document.getElementById('to_id');
    for (let i = 0; i < optionsCount; i++) {
        fromSelectBox.appendChild(new Option());
    }
    SelectBox.init('from_id');
    SelectBox.init('to_id');
    const selectedOptions = [97, 98, 99];
    for (const index of selectedOptions) {
        fromSelectBox.options[index].selected = true;
        fromSelectBox.options[index].scrollIntoView();
    }
    assert.equal(fromSelectBox.options.length, optionsCount);
    SelectBox.move('from_id', 'to_id');
    assert.equal(fromSelectBox.options.length, optionsCount - selectedOptions.length);
    assert.equal(toSelectBox.options.length, selectedOptions.length);
    assert.notEqual(fromSelectBox.scrollTop, 0);
});

QUnit.test('retain optgroups', function(assert) {
    const $ = django.jQuery;
    $('<select id="id"></select>').appendTo('#qunit-fixture');
    const grp = $('<optgroup label="group one">').appendTo('#id');
    $('<option value="0">A</option>').appendTo(grp);
    $('</optgroup>').appendTo('#id');
    $('<option value="1">B</option>').appendTo('#id');
    SelectBox.init('id');
    SelectBox.redisplay('id');
    assert.equal($('#id option').length, 2);
    assert.equal($('#id optgroup').length, 1);
});

QUnit.test('sort optgroups', function(assert) {
    const $ = django.jQuery;
    $('<select id="id"></select>').appendTo('#qunit-fixture');
    // Add optgroups in non-alphabetical order
    const grp2 = $('<optgroup label="Group B">').appendTo('#id');
    $('<option value="3">Item 3</option>').appendTo(grp2);
    $('<option value="4">Item 4</option>').appendTo(grp2);
    const grp1 = $('<optgroup label="Group A">').appendTo('#id');
    $('<option value="1">Item 1</option>').appendTo(grp1);
    $('<option value="2">Item 2</option>').appendTo(grp1);

    SelectBox.init('id');

    // Verify cache is sorted by group then by item
    assert.equal(SelectBox.cache.id.length, 4);
    assert.equal(SelectBox.cache.id[0].group, 'Group A');
    assert.equal(SelectBox.cache.id[0].text, 'Item 1');
    assert.equal(SelectBox.cache.id[1].group, 'Group A');
    assert.equal(SelectBox.cache.id[1].text, 'Item 2');
    assert.equal(SelectBox.cache.id[2].group, 'Group B');
    assert.equal(SelectBox.cache.id[2].text, 'Item 3');
    assert.equal(SelectBox.cache.id[3].group, 'Group B');
    assert.equal(SelectBox.cache.id[3].text, 'Item 4');
});

QUnit.test('do not sort when no optgroups', function(assert) {
    const $ = django.jQuery;
    $('<select id="id"></select>').appendTo('#qunit-fixture');
    // Add options in non-alphabetical order
    $('<option value="3">Zebra</option>').appendTo('#id');
    $('<option value="1">Apple</option>').appendTo('#id');
    $('<option value="2">Banana</option>').appendTo('#id');

    SelectBox.init('id');

    // Verify cache preserves original order (not sorted)
    assert.equal(SelectBox.cache.id.length, 3);
    assert.equal(SelectBox.cache.id[0].text, 'Zebra');
    assert.equal(SelectBox.cache.id[1].text, 'Apple');
    assert.equal(SelectBox.cache.id[2].text, 'Banana');
});

QUnit.test('move with optgroups sorts', function(assert) {
    const $ = django.jQuery;
    $('<select id="from_id"></select>').appendTo('#qunit-fixture');
    $('<select id="to_id"></select>').appendTo('#qunit-fixture');

    // Add options with optgroups to from_id in non-alphabetical order
    const grp2 = $('<optgroup label="Group B">').appendTo('#from_id');
    $('<option value="2">Item 2</option>').appendTo(grp2);
    const grp1 = $('<optgroup label="Group A">').appendTo('#from_id');
    $('<option value="1">Item 1</option>').appendTo(grp1);

    SelectBox.init('from_id');
    SelectBox.init('to_id');

    // Select and move item
    document.getElementById('from_id').options[0].selected = true;
    SelectBox.move('from_id', 'to_id');

    // Verify to_id cache is sorted (even though we only added one item)
    assert.equal(SelectBox.cache.to_id.length, 1);
    assert.equal(SelectBox.cache.to_id[0].group, 'Group B');
    assert.equal(SelectBox.cache.to_id[0].text, 'Item 2');
});

QUnit.test('move without optgroups does not sort', function(assert) {
    const $ = django.jQuery;
    $('<select id="from_id"></select>').appendTo('#qunit-fixture');
    $('<select id="to_id"></select>').appendTo('#qunit-fixture');

    // Add options without optgroups in non-alphabetical order
    $('<option value="3">Zebra</option>').appendTo('#from_id');
    $('<option value="1">Apple</option>').appendTo('#from_id');

    SelectBox.init('from_id');
    SelectBox.init('to_id');

    // Select and move first item (Zebra)
    document.getElementById('from_id').options[0].selected = true;
    SelectBox.move('from_id', 'to_id');

    // Verify to_id cache preserves order (not sorted)
    assert.equal(SelectBox.cache.to_id.length, 1);
    assert.equal(SelectBox.cache.to_id[0].text, 'Zebra');

    // Move second item (Apple)
    document.getElementById('from_id').options[0].selected = true;
    SelectBox.move('from_id', 'to_id');

    // Verify items are in order they were added, not alphabetical
    assert.equal(SelectBox.cache.to_id.length, 2);
    assert.equal(SelectBox.cache.to_id[0].text, 'Zebra');
    assert.equal(SelectBox.cache.to_id[1].text, 'Apple');
});

QUnit.test('move_all with optgroups sorts', function(assert) {
    const $ = django.jQuery;
    $('<select id="from_id"></select>').appendTo('#qunit-fixture');
    $('<select id="to_id"></select>').appendTo('#qunit-fixture');

    // Add options with optgroups in non-alphabetical order
    const grp2 = $('<optgroup label="Group B">').appendTo('#from_id');
    $('<option value="3">Zebra</option>').appendTo(grp2);
    const grp1 = $('<optgroup label="Group A">').appendTo('#from_id');
    $('<option value="1">Apple</option>').appendTo(grp1);
    $('<option value="2">Banana</option>').appendTo(grp1);

    SelectBox.init('from_id');
    SelectBox.init('to_id');

    // Move all items
    SelectBox.move_all('from_id', 'to_id');

    // Verify to_id cache is sorted by group
    assert.equal(SelectBox.cache.to_id.length, 3);
    assert.equal(SelectBox.cache.to_id[0].group, 'Group A');
    assert.equal(SelectBox.cache.to_id[0].text, 'Apple');
    assert.equal(SelectBox.cache.to_id[1].group, 'Group A');
    assert.equal(SelectBox.cache.to_id[1].text, 'Banana');
    assert.equal(SelectBox.cache.to_id[2].group, 'Group B');
    assert.equal(SelectBox.cache.to_id[2].text, 'Zebra');
});

QUnit.test('move_all without optgroups does not sort', function(assert) {
    const $ = django.jQuery;
    $('<select id="from_id"></select>').appendTo('#qunit-fixture');
    $('<select id="to_id"></select>').appendTo('#qunit-fixture');

    // Add options without optgroups in non-alphabetical order
    $('<option value="3">Zebra</option>').appendTo('#from_id');
    $('<option value="1">Apple</option>').appendTo('#from_id');
    $('<option value="2">Banana</option>').appendTo('#from_id');

    SelectBox.init('from_id');
    SelectBox.init('to_id');

    // Move all items
    SelectBox.move_all('from_id', 'to_id');

    // Verify to_id cache preserves original order (not sorted)
    assert.equal(SelectBox.cache.to_id.length, 3);
    assert.equal(SelectBox.cache.to_id[0].text, 'Zebra');
    assert.equal(SelectBox.cache.to_id[1].text, 'Apple');
    assert.equal(SelectBox.cache.to_id[2].text, 'Banana');
});
