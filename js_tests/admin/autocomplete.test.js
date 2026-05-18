QUnit.module("admin.inlines.autocomplete: tabular formset autocomplete id consistency", {
    beforeEach: function () {
        const $ = django.jQuery;
        $("#qunit-fixture").append($("#tabular-formset-with-autocomplete").text());
        this.table = $("table.inline");
        this.inlineRows = this.table.find("tr.form-row");

        $(".admin-autocomplete").not("[name*=__prefix__]").djangoAdminSelect2();
        this.inlineRows.tabularFormset("table.inline tr.form-row", {
            prefix: "auto",
            deleteText: "Remove",
        });
    },
});

QUnit.test(
    "after row deletion, select2 aria-owns matches renumbered select id",
    function (assert) {
        const $ = django.jQuery;
        assert.equal(
            $("#auto-2").find("select.admin-autocomplete").attr("id"),
            "id_auto-2-fk",
            "precondition: third row select has id auto-2-fk"
        );

        // Delete the n-1 row
        const deleteLink = this.table.find("#auto-1 .inline-deletelink");
        deleteLink.trigger($.Event("click", { target: deleteLink }));

        // Ensure that the n row is renumbered to n-1 and that the select2 aria-owns attribute is updated accordingly.
        const renumberedSelect = $("#auto-1").find("select.admin-autocomplete");
        assert.equal(
            renumberedSelect.attr("id"),
            "id_auto-1-fk",
            "select id is renumbered after deletion"
        );

        renumberedSelect.select2("open");
        const $selection = renumberedSelect
            .next(".select2-container")
            .find(".select2-selection");
        const ariaOwns = $selection.attr("aria-owns");
        assert.ok(ariaOwns, "aria-owns attribute is present when open");
        assert.ok(
            ariaOwns.indexOf("auto-1-fk") !== -1,
            "aria-owns references the renumbered id (auto-1), not the old id (auto-2)"
        );
        renumberedSelect.select2("close");
    }
);
