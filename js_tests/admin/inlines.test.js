/* global QUnit */
/* eslint global-strict: 0, strict: 0 */
'use strict';

QUnit.module('admin.inlines: tabular formsets', {
    beforeEach: function() {
        var $ = django.jQuery;
        var that = this;
        this.addText = 'Add another';

        $('#qunit-fixture').append($('#tabular-formset').text());
        this.table = $('table.inline');
        this.inlineRow = this.table.find('tr');
        that.inlineRow.tabularFormset('table.inline tr', {
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
    var addButton = this.table.find('.add-row a');
    assert.equal(addButton.text(), this.addText);
    addButton.click();
    assert.ok(this.table.find('#first-1').hasClass('row2'));
});

QUnit.test('add/remove form events', function(assert) {
    assert.expect(6);
    var $ = django.jQuery;
    var $document = $(document);
    var addButton = this.table.find('.add-row a');
    $document.on('formset:added', function(event, $row, formsetName) {
        assert.ok(true, 'event `formset:added` triggered');
        assert.equal(true, $row.is($('.row2')));
        assert.equal(formsetName, 'first');
    });
    addButton.click();
    var deletedRow = $('.row2');
    var deleteLink = this.table.find('.inline-deletelink');
    $document.on('formset:removed', function(event, $row, formsetName) {
        assert.ok(true, 'event `formset:removed` triggered');
        assert.equal(true, $row.is(deletedRow));
        assert.equal(formsetName, 'first');
    });
    deleteLink.click();
});

QUnit.test('existing add button', function(assert) {
    var $ = django.jQuery;
    $('#qunit-fixture').empty();  // Clear the table added in beforeEach
    $('#qunit-fixture').append($('#tabular-formset').text());
    this.table = $('table.inline');
    this.inlineRow = this.table.find('tr');
    this.table.append('<i class="add-button"></i>');
    var addButton = this.table.find('.add-button');
    this.inlineRow.tabularFormset('table.inline tr', {
        prefix: 'first',
        deleteText: 'Remove',
        addButton: addButton
    });
    assert.equal(this.table.find('.add-row a').length, 0);
    addButton.click();
    assert.ok(this.table.find('#first-1').hasClass('row2'));
});
