/* global QUnit */
'use strict';

QUnit.module('admin.sidebar: filter', {
    beforeEach: function() {
        const $ = django.jQuery;
        $('#qunit-fixture').append($('#nav-sidebar-filter').text());
        this.navSidebar = $('#nav-sidebar');
        this.navFilter = $('#nav-filter');
        initSidebarQuickFilter();
    }
});

QUnit.test('filter by a model name', function(assert) {
    assert.equal(this.navSidebar.find('th[scope=row] a').length, 2);

    this.navFilter.val('us'); // Matches 'users'.
    this.navFilter[0].dispatchEvent(new Event('change'));
    assert.equal(this.navSidebar.find('tr[class^="model-"]:visible').length, 1);

    this.navFilter.val('nonexistent');
    this.navFilter[0].dispatchEvent(new Event('change'));
    assert.equal(this.navSidebar.find('tr[class^="model-"]:visible').length, 0);
});
