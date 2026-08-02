/* global QUnit */
"use strict";

QUnit.module("admin.autocomplete", {
    beforeEach: function () {
        const $ = django.jQuery;

        $("#qunit-fixture").append(
            $("#tabular-formset-with-autocomplete").text(),
        );
        this.table = $("table.inline");
        this.inlineRows = this.table.find("tr.form-row");
        this.inlineRows.tabularFormset("table.inline tr.form-row", {
            prefix: "autocomplete",
            addText: "Add another",
            deleteText: "Remove",
        });
        this.table
            .find(".admin-autocomplete")
            .not("[name*=__prefix__]")
            .djangoAdminSelect2();
    },
    afterEach: function () {
        django
            .jQuery(".admin-autocomplete.select2-hidden-accessible")
            .select2("destroy");
    },
});

QUnit.test(
    "autocomplete is reinitialized after deleting an inline row",
    function (assert) {
        const $ = django.jQuery;
        assert.expect(7);
        const addButton = this.table.find("tr.add-row a");
        addButton.trigger($.Event("click", { target: addButton }));

        const addedSelect = this.table.find("#id_autocomplete-2-products");
        const initialContainer = addedSelect.next(".select2").get(0);
        assert.ok(addedSelect.hasClass("select2-hidden-accessible"));
        assert.equal(this.table.find(".select2").length, 3);

        const deleteLink = this.table.find(
            "#autocomplete-1 .inline-deletelink",
        );
        deleteLink.trigger($.Event("click", { target: deleteLink }));

        const reindexedSelect = this.table.find("#id_autocomplete-1-products");
        assert.equal(reindexedSelect.attr("name"), "autocomplete-1-products");
        assert.ok(reindexedSelect.hasClass("select2-hidden-accessible"));
        assert.equal(this.table.find(".select2").length, 2);
        assert.notEqual(
            reindexedSelect.next(".select2").get(0),
            initialContainer,
        );
        assert.equal(this.table.find("#autocomplete-empty .select2").length, 0);
    },
);
