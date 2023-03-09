/* global QUnit, RelatedObjectLookups */
'use strict';
QUnit.module('admin.RelatedObjectLookups');

QUnit.test('quote value', function(assert) {
    const result = customEncodeURIComponent('_40');
    const expected = '_5F40';
    assert.equal(result, expected, "expected _5F40");

});

QUnit.test('updateRelatedObjectLinks properly quotes URL value', function(assert) {
    const $ = django.jQuery;
    const triggeringLink = $('<input class="vForeignKeyRawIdAdminField" type="text" value="_40">');
    const relatedLink = $(`<a href="#" data-href-template="/admin_widgets/house/change/?name__iexact=__fk__">change</a>`);
    relatedLink.addClass('view-related change-related delete-related');

    const parent = $('<div class="vForeignKeyRawIdAdminField"></div>');
    parent.append(triggeringLink);
    parent.append(relatedLink);
    $('body').append(parent);

    relatedLink.appendTo(triggeringLink.parent());

    updateRelatedObjectLinks(triggeringLink);
    const href = relatedLink.attr('href');
    const expectedValue = '/admin_widgets/house/change/?name__iexact=_5F40';
    // expected value with encoded underscore

    assert.equal(href, expectedValue, 'URL value is properly quoted');
});





