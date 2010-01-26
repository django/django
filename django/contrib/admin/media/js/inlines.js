/**
 * Django admin inlines
 *
 * Based on jQuery Formset 1.1
 * @author Stanislaus Madueke (stan DOT madueke AT gmail DOT com)
 * @requires jQuery 1.2.6 or later
 *
 * Copyright (c) 2009, Stanislaus Madueke
 * All rights reserved.
 *
 * Spiced up with Code from Zain Memon's GSoC project 2009
 * and modified for Django by Jannis Leidel
 *
 * Licensed under the New BSD License
 * See: http://www.opensource.org/licenses/bsd-license.php
 */
(function($) {
	$.fn.formset = function(opts) {
		var options = $.extend({}, $.fn.formset.defaults, opts);
		var updateElementIndex = function(el, prefix, ndx) {
			var id_regex = new RegExp("(" + prefix + "-\\d+)");
			var replacement = prefix + "-" + ndx;
			if ($(el).attr("for")) $(el).attr("for", $(el).attr("for").replace(id_regex, replacement));
			if (el.id) el.id = el.id.replace(id_regex, replacement);
			if (el.name) el.name = el.name.replace(id_regex, replacement);
		};
		var totalForms = $("#id_" + options.prefix + "-TOTAL_FORMS");
		var initialForms = $("#id_" + options.prefix + "-INITIAL_FORMS");
		var maxForms = parseInt(totalForms.val());
		// only show the add button if we are allowed to add more items
		var showAddButton = (maxForms - parseInt(initialForms.val())) > 0;
		var selectedItems = this;
		$(this).each(function(i) {
			$(this).not("." + options.emptyCssClass).addClass(options.formCssClass);
			// hide the extras, but only if there were no form errors
			if (!$(".errornote").html()) {
				var relatedItems = $(selectedItems).not("." + options.emptyCssClass);
				extraRows = relatedItems.length;
				if (parseInt(initialForms.val()) >= 0) {
					$(relatedItems).slice(initialForms.val()).remove();
				} else {
					$(relatedItems).remove();
				}
				totalForms.val(parseInt(initialForms.val()));
			}
		});
		if ($(this).length && showAddButton) {
			var addButton;
			if ($(this).attr("tagName") == "TR") {
				// If forms are laid out as table rows, insert the
				// "add" button in a new table row:
				var numCols = this.eq(0).children().length;
				$(this).parent().append('<tr class="' + options.addCssClass + '"><td colspan="' + numCols + '"><a href="javascript:void(0)">' + options.addText + "</a></tr>");
				addButton = $(this).parent().find("tr:last a");
			} else {
				// Otherwise, insert it immediately after the last form:
				$(this).filter(":last").after('<div class="' + options.addCssClass + '"><a href="javascript:void(0)">' + options.addText + "</a></div>");
				addButton = $(this).filter(":last").next().find("a");
			}
			addButton.click(function() {
				var totalForms = parseInt($("#id_" + options.prefix + "-TOTAL_FORMS").val());
				var initialForms = parseInt($("#id_" + options.prefix + "-INITIAL_FORMS").val());
				var nextIndex = totalForms + 1;
				var template = $("#" + options.prefix + "-empty");
				var row = template.clone(true).get(0);
				$(row).removeClass(options.emptyCssClass).removeAttr("id").insertBefore($(template));
				$(row).html($(row).html().replace(/__prefix__/g, nextIndex));
				$(row).addClass(options.formCssClass).attr("id", options.prefix + nextIndex);
				if ($(row).is("TR")) {
					// If the forms are laid out in table rows, insert
					// the remove button into the last table cell:
					$(row).children(":last").append('<div><a class="' + options.deleteCssClass +'" href="javascript:void(0)">' + options.deleteText + "</a></div>");
				} else if ($(row).is("UL") || $(row).is("OL")) {
					// If they're laid out as an ordered/unordered list,
					// insert an <li> after the last list item:
					$(row).append('<li><a class="' + options.deleteCssClass +'" href="javascript:void(0)">' + options.deleteText + "</a></li>");
				} else {
					// Otherwise, just insert the remove button as the
					// last child element of the form's container:
					$(row).children(":first").append('<span><a class="' + options.deleteCssClass + '" href="javascript:void(0)">' + options.deleteText + "</a></span>");
				}
				// Update number of total forms
				$("#id_" + options.prefix + "-TOTAL_FORMS").val(nextIndex);
				// Hide add button in case we've hit the max
				if (maxForms <= nextIndex) {
					addButton.parent().hide();
				}
				// The delete button of each row triggers a bunch of other things
				$(row).find("a." + options.deleteCssClass).click(function() {
					// Remove the parent form containing this button:
					var row = $(this).parents("." + options.formCssClass);
					row.remove();
					// If a post-delete callback was provided, call it with the deleted form:
					if (options.removed) options.removed(row);
					// Update the TOTAL_FORMS form count.
					var forms = $("." + options.formCssClass);
					$("#id_" + options.prefix + "-TOTAL_FORMS").val(forms.length);
					// Show add button again once we drop below max
					if (maxForms >= forms.length) {
						addButton.parent().show();
					}
					// Also, update names and ids for all remaining form controls
					// so they remain in sequence:
					for (var i=0, formCount=forms.length; i<formCount; i++) {
						$(forms.get(i)).find("input,select,textarea,label").each(function() {
							updateElementIndex(this, options.prefix, i);
						});
					}
					return false;
				});
				$(row).find("input,select,textarea,label").each(function() {
					updateElementIndex(this, options.prefix, totalForms);
				});
				// If a post-add callback was supplied, call it with the added form:
				if (options.added) options.added($(row));
				return false;
			});
		}
		return $(this);
	}

	/* Setup plugin defaults */
	$.fn.formset.defaults = {
		prefix: "form",					 // The form prefix for your django formset
		addText: "add another",			 // Text for the add link
		deleteText: "remove",			 // Text for the delete link
		addCssClass: "add-row",			 // CSS class applied to the add link
		deleteCssClass: "delete-row",	 // CSS class applied to the delete link
		emptyCssClass: "empty-row",		 // CSS class applied to the empty row
		formCssClass: "dynamic-form",	 // CSS class applied to each form in a formset
		added: null,					 // Function called each time a new form is added
		removed: null					 // Function called each time a form is deleted
	}
})(jQuery)
