/* global QUnit, RelatedObjectLookups */
'use strict';
QUnit.module('admin.RelatedObjectLookups');

QUnit.test('quote value', function(assert) {
    const result = customEncodeURIComponent('_40');
    const expected = '_5F40';
    assert.equal(result, expected, "expected _5F40");

});

function quoteSpecialChars(specialCharsList = ['c>h<e%e[s]e_40', 'on/ion?t@w$mw+', 'sa:la"m,i\nw;th=', '?_3A_40', 'qwerttyuiop12345', '?a=b']) {
    const quotedChars = [];
    for(let i = 0; i < specialCharsList.length; i++) {
        const charToQuote = specialCharsList[i];
        const quotedChar = customEncodeURIComponent(charToQuote);
        quotedChars.push(quotedChar);
    }
    return quotedChars;
}

QUnit.test('quoteSpecialChars', function(assert) {
    assert.equal(quoteSpecialChars().toString(), ['c_3Eh_3Ce_25e_5Bs_5De_5F40', 'on_2Fion_3Ft_40w_24mw_2B', 'sa_3Ala_22m_2Ci_0Aw_3Bth_3D', '_3F_5F3A_5F40', 'qwerttyuiop12345', '_3Fa_3Db'].toString(), "passed");
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

