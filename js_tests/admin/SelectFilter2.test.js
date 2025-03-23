/* global QUnit, SelectFilter */
'use strict';

QUnit.module('admin.SelectFilter2');

QUnit.test('init', function(assert) {
    const $ = django.jQuery;
    $('<form id="test"></form>').appendTo('#qunit-fixture');
    $('<label for="id_id">Test</label>').appendTo('#test');
    $('<div class="helptext">This is helpful.</div>').appendTo('#test');
    $('<select id="id"><option value="0">A</option></select>').appendTo('#test');
    SelectFilter.init('id', 'things', 0);
    assert.equal($('#test').children().first().prop("tagName"), "DIV");
    assert.equal($('#test').children().first().attr("class"), "selector");
    assert.equal($('.selector-available label').text().trim(), "Available things");
    assert.equal($('.selector-chosen label').text().trim(), "Chosen things");
    assert.equal($('.selector-chosen select')[0].getAttribute('multiple'), '');
    assert.equal($('.selector-chooseall').text(), "Choose all things");
    assert.equal($('.selector-chooseall').prop("tagName"), "BUTTON");
    assert.equal($('.selector-add').text(), "Choose selected things");
    assert.equal($('.selector-add').prop("tagName"), "BUTTON");
    assert.equal($('.selector-remove').text(), "Remove selected chosen things");
    assert.equal($('.selector-remove').prop("tagName"), "BUTTON");
    assert.equal($('.selector-clearall').text(), "Remove all things");
    assert.equal($('.selector-clearall').prop("tagName"), "BUTTON");
    assert.equal($('.selector-available .filtered').attr("aria-labelledby"), "id_from_title");
    assert.equal($('.selector-available .selector-available-title label').text(), "Available things ");
    assert.equal($('.selector-available .selector-available-title .helptext').text(), 'Choose things by selecting them and then select the "Choose" arrow button.');
    assert.equal($('.selector-chosen .filtered').attr("aria-labelledby"), "id_to_title");
    assert.equal($('.selector-chosen .selector-chosen-title label').text(), "Chosen things ");
    assert.equal($('.selector-chosen .selector-chosen-title .helptext').text(), 'Remove things by selecting them and then select the "Remove" arrow button.');
    assert.equal($('.selector-filter label .help-tooltip')[0].getAttribute("aria-label"), "Type into this box to filter down the list of available things.");
    assert.equal($('.selector-filter label .help-tooltip')[1].getAttribute("aria-label"), "Type into this box to filter down the list of selected things.");
});

QUnit.test('filtering available options', function(assert) {
    const $ = django.jQuery;
    $('<form><select multiple id="select"></select></form>').appendTo('#qunit-fixture');
    $('<option value="1" title="Red">Red</option>').appendTo('#select');
    $('<option value="2" title="Blue">Blue</option>').appendTo('#select');
    $('<option value="3" title="Green">Green</option>').appendTo('#select');
    SelectFilter.init('select', 'items', 0);
    assert.equal($('#select_from option').length, 3);
    assert.equal($('#select_to option').length, 0);
    const done = assert.async();
    const search_term = 'r';
    const event = new KeyboardEvent('keyup', {'key': search_term});
    $('#select_input').val(search_term);
    SelectFilter.filter_key_up(event, 'select', '_from');
    setTimeout(() => {
        assert.equal($('#select_from option').length, 2);
        assert.equal($('#select_to option').length, 0);
        assert.equal($('#select_from option')[0].value, '1');
        assert.equal($('#select_from option')[1].value, '3');
        done();
    });
});

QUnit.test('filtering selected options', function(assert) {
    const $ = django.jQuery;
    $('<form><select multiple id="select"></select></form>').appendTo('#qunit-fixture');
    $('<option selected value="1" title="Red">Red</option>').appendTo('#select');
    $('<option selected value="2" title="Blue">Blue</option>').appendTo('#select');
    $('<option selected value="3" title="Green">Green</option>').appendTo('#select');
    SelectFilter.init('select', 'items', 0);
    assert.equal($('#select_from option').length, 0);
    assert.equal($('#select_to option').length, 3);
    const done = assert.async();
    const search_term = 'r';
    const event = new KeyboardEvent('keyup', {'key': search_term});
    $('#select_selected_input').val(search_term);
    SelectFilter.filter_key_up(event, 'select', '_to', '_selected_input');
    setTimeout(() => {
        assert.equal($('#select_from option').length, 0);
        assert.equal($('#select_to option').length, 2);
        assert.equal($('#select_to option')[0].value, '1');
        assert.equal($('#select_to option')[1].value, '3');
        done();
    });
});

QUnit.test('filtering available options to nothing', function(assert) {
    const $ = django.jQuery;
    $('<form><select multiple id="select"></select></form>').appendTo('#qunit-fixture');
    $('<option value="1" title="Red">Red</option>').appendTo('#select');
    $('<option value="2" title="Blue">Blue</option>').appendTo('#select');
    $('<option value="3" title="Green">Green</option>').appendTo('#select');
    SelectFilter.init('select', 'items', 0);
    assert.equal($('#select_from option').length, 3);
    assert.equal($('#select_to option').length, 0);
    const done = assert.async();
    const search_term = 'x';
    const event = new KeyboardEvent('keyup', {'key': search_term});
    $('#select_input').val(search_term);
    SelectFilter.filter_key_up(event, 'select', '_from');
    setTimeout(() => {
        assert.equal($('#select_from option').length, 0);
        assert.equal($('#select_to option').length, 0);
        done();
    });
});

QUnit.test('filtering selected options to nothing', function(assert) {
    const $ = django.jQuery;
    $('<form><select multiple id="select"></select></form>').appendTo('#qunit-fixture');
    $('<option selected value="1" title="Red">Red</option>').appendTo('#select');
    $('<option selected value="2" title="Blue">Blue</option>').appendTo('#select');
    $('<option selected value="3" title="Green">Green</option>').appendTo('#select');
    SelectFilter.init('select', 'items', 0);
    assert.equal($('#select_from option').length, 0);
    assert.equal($('#select_to option').length, 3);
    const done = assert.async();
    const search_term = 'x';
    const event = new KeyboardEvent('keyup', {'key': search_term});
    $('#select_selected_input').val(search_term);
    SelectFilter.filter_key_up(event, 'select', '_to', '_selected_input');
    setTimeout(() => {
        assert.equal($('#select_from option').length, 0);
        assert.equal($('#select_to option').length, 0);
        done();
    });
});

QUnit.test('selecting option', function(assert) {
    const $ = django.jQuery;
    $('<form><select multiple id="select"></select></form>').appendTo('#qunit-fixture');
    $('<option value="1" title="Red">Red</option>').appendTo('#select');
    $('<option value="2" title="Blue">Blue</option>').appendTo('#select');
    $('<option value="3" title="Green">Green</option>').appendTo('#select');
    SelectFilter.init('select', 'items', 0);
    assert.equal($('#select_from option').length, 3);
    assert.equal($('#select_to option').length, 0);
    // move to the right
    const done = assert.async();
    $('#select_from')[0].selectedIndex = 0;
    const event = new KeyboardEvent('keydown', {'keyCode': 39, 'charCode': 39});
    SelectFilter.filter_key_down(event, 'select', '_from', '_to');
    setTimeout(() => {
        assert.equal($('#select_from option').length, 2);
        assert.equal($('#select_to option').length, 1);
        assert.equal($('#select_to option')[0].value, '1');
        done();
    });
});

QUnit.test('deselecting option', function(assert) {
    const $ = django.jQuery;
    $('<form><select multiple id="select"></select></form>').appendTo('#qunit-fixture');
    $('<option selected value="1" title="Red">Red</option>').appendTo('#select');
    $('<option value="2" title="Blue">Blue</option>').appendTo('#select');
    $('<option value="3" title="Green">Green</option>').appendTo('#select');
    SelectFilter.init('select', 'items', 0);
    assert.equal($('#select_from option').length, 2);
    assert.equal($('#select_to option').length, 1);
    assert.equal($('#select_to option')[0].value, '1');
    // move back to the left
    const done_left = assert.async();
    $('#select_to')[0].selectedIndex = 0;
    const event_left = new KeyboardEvent('keydown', {'keyCode': 37, 'charCode': 37});
    SelectFilter.filter_key_down(event_left, 'select', '_to', '_from');
    setTimeout(() => {
        assert.equal($('#select_from option').length, 3);
        assert.equal($('#select_to option').length, 0);
        done_left();
    });
});
