/* global QUnit */
'use strict';

QUnit.module('admin.inlines: tabular formsets', {
    beforeEach: function() {
        const $ = django.jQuery;
        const that = this;
        this.addText = 'Add another';

        $('#qunit-fixture').append($('#tabular-formset').text());
        this.table = $('table.inline');
        this.inlineRow = this.table.find('tr');
        this.inlineRow.tabularFormset('table.inline tr.form-row', {
            prefix: 'first',
            addText: that.addText,
            deleteText: 'Remove'
        });
    }
});

QUnit.test('no forms', function(assert) {
    assert.ok(this.inlineRow.hasClass('dynamic-first'));
    assert.equal(this.table.find('.add-row a').text(), this.addText);
});

QUnit.test('add form', function(assert) {
    const addButton = this.table.find('.add-row a');
    assert.equal(addButton.text(), this.addText);
    addButton.click();
    assert.ok(this.table.find('#first-1'));
});

QUnit.test('added form has remove button', function(assert) {
    const addButton = this.table.find('.add-row a');
    assert.equal(addButton.text(), this.addText);
    addButton.click();
    assert.equal(this.table.find('#first-1 .inline-deletelink').length, 1);
});

QUnit.test('add/remove form events', function(assert) {
    assert.expect(5);
    const addButton = this.table.find('.add-row a');
    document.addEventListener('formset:added', (event) => {
        assert.ok(true, 'event `formset:added` triggered');
        assert.equal(true, event.target.matches('#first-1'));
        assert.equal(event.detail.formsetName, 'first');
    }, {once: true});
    addButton.click();
    const deleteLink = this.table.find('.inline-deletelink');
    document.addEventListener('formset:removed', (event) => {
        assert.ok(true, 'event `formset:removed` triggered');
        assert.equal(event.detail.formsetName, 'first');
    }, {once: true});
    deleteLink.click();
});

QUnit.test('existing add button', function(assert) {
    const $ = django.jQuery;
    $('#qunit-fixture').empty(); // Clear the table added in beforeEach
    $('#qunit-fixture').append($('#tabular-formset').text());
    this.table = $('table.inline');
    this.inlineRow = this.table.find('tr');
    this.table.append('<i class="add-button"></i>');
    const addButton = this.table.find('.add-button');
    this.inlineRow.tabularFormset('table.inline tr', {
        prefix: 'first',
        deleteText: 'Remove',
        addButton: addButton
    });
    assert.equal(this.table.find('.add-row a').length, 0);
    addButton.click();
    assert.ok(this.table.find('#first-1'));
});


QUnit.module('admin.inlines: tabular formsets with validation errors', {
    beforeEach: function() {
        const $ = django.jQuery;

        $('#qunit-fixture').append($('#tabular-formset-with-validation-error').text());
        this.table = $('table.inline');
        this.inlineRows = this.table.find('tr.form-row');
        this.inlineRows.tabularFormset('table.inline tr.form-row', {
            prefix: 'second'
        });
    }
});

QUnit.test('first form has delete checkbox and no button', function(assert) {
    const tr = this.inlineRows.slice(0, 1);
    assert.ok(tr.hasClass('dynamic-second'));
    assert.ok(tr.hasClass('has_original'));
    assert.equal(tr.find('td.delete input').length, 1);
    assert.equal(tr.find('td.delete .inline-deletelink').length, 0);
});

QUnit.test('dynamic form has remove button', function(assert) {
    const tr = this.inlineRows.slice(1, 2);
    assert.ok(tr.hasClass('dynamic-second'));
    assert.notOk(tr.hasClass('has_original'));
    assert.equal(tr.find('.inline-deletelink').length, 1);
});

QUnit.test('dynamic template has nothing', function(assert) {
    const tr = this.inlineRows.slice(2, 3);
    assert.ok(tr.hasClass('empty-form'));
    assert.notOk(tr.hasClass('dynamic-second'));
    assert.notOk(tr.hasClass('has_original'));
    assert.equal(tr.find('td.delete')[0].innerHTML, '');
});

QUnit.test('removing a form-row also removed related row with non-field errors', function(assert) {
    const $ = django.jQuery;
    assert.ok(this.table.find('.row-form-errors').length);
    const tr = this.inlineRows.slice(1, 2);
    const trWithErrors = tr.prev();
    assert.ok(trWithErrors.hasClass('row-form-errors'));
    const deleteLink = tr.find('a.inline-deletelink');
    deleteLink.trigger($.Event('click', {target: deleteLink}));
    assert.notOk(this.table.find('.row-form-errors').length);
});

QUnit.module('admin.inlines: tabular formsets with max_num', {
    beforeEach: function() {
        const $ = django.jQuery;
        $('#qunit-fixture').append($('#tabular-formset-with-validation-error').text());
        this.table = $('table.inline');
        this.maxNum = $('input.id_second-MAX_NUM_FORMS');
        this.maxNum.val(2);
        this.inlineRows = this.table.find('tr.form-row');
        this.inlineRows.tabularFormset('table.inline tr.form-row', {
            prefix: 'second'
        });
    }
});

QUnit.test('does not show the add button if already at max_num', function(assert) {
    const addButton = this.table.find('tr.add_row > td > a');
    assert.notOk(addButton.is(':visible'));
});

QUnit.test('make addButton visible again', function(assert) {
    const $ = django.jQuery;
    const addButton = this.table.find('tr.add_row > td > a');
    const removeButton = this.table.find('tr.form-row:first').find('a.inline-deletelink');
    removeButton.trigger($.Event( "click", { target: removeButton } ));
    assert.notOk(addButton.is(':visible'));
});


QUnit.module('admin.inlines: tabular formsets with min_num', {
    beforeEach: function() {
        const $ = django.jQuery;
        $('#qunit-fixture').append($('#tabular-formset-with-validation-error').text());
        this.table = $('table.inline');
        this.minNum = $('input#id_second-MIN_NUM_FORMS');
        this.minNum.val(2);
        this.inlineRows = this.table.find('tr.form-row');
        this.inlineRows.tabularFormset('table.inline tr.form-row', {
            prefix: 'second'
        });
    }
});

QUnit.test('does not show the remove buttons if already at min_num', function(assert) {
    assert.notOk(this.table.find('.inline-deletelink:visible').length);
});

QUnit.test('make removeButtons visible again', function(assert) {
    const $ = django.jQuery;
    const addButton = this.table.find('tr.add-row > td > a');
    addButton.trigger($.Event( "click", { target: addButton } ));
    assert.equal(this.table.find('.inline-deletelink:visible').length, 2);
});
