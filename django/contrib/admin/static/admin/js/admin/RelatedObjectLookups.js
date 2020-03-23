/*global SelectBox, interpolate*/
// Handles related-objects functionality: lookup link for raw_id_fields
// and Add Another links.

(function($) {
    'use strict';

    function showAdminPopup(triggeringLink, name_regexp, add_popup) {
        var name = triggeringLink.id.replace(name_regexp, '');
        var href = triggeringLink.href;
        if (add_popup) {
            if (href.indexOf('?') === -1) {
                href += '?_popup=1';
            } else {
                href += '&_popup=1';
            }
        }
        var win = window.open(href, name, 'height=500,width=800,resizable=yes,scrollbars=yes');
        win.focus();
        return false;
    }

    function showRelatedObjectLookupPopup(triggeringLink) {
        return showAdminPopup(triggeringLink, /^lookup_/, true);
    }

    function dismissRelatedLookupPopup(win, chosenId) {
        var name = win.name;
        var elem = document.getElementById(name);
        if (elem.classList.contains('vManyToManyRawIdAdminField') && elem.value) {
            elem.value += ',' + chosenId;
        } else {
            document.getElementById(name).value = chosenId;
        }
        win.close();
    }

    function showRelatedObjectPopup(triggeringLink) {
        return showAdminPopup(triggeringLink, /^(change|add|delete)_/, false);
    }

    function updateRelatedObjectLinks(triggeringLink) {
        var $this = $(triggeringLink);
        var siblings = $this.nextAll('.view-related, .change-related, .delete-related');
        if (!siblings.length) {
            return;
        }
        var value = $this.val();
        if (value) {
            siblings.each(function() {
                var elm = $(this);
                elm.attr('href', elm.attr('data-href-template').replace('__fk__', value));
            });
        } else {
            siblings.removeAttr('href');
        }
    }

    function dismissAddRelatedObjectPopup(win, newId, newRepr) {
        var name = win.name;
        var elem = document.getElementById(name);
        if (elem) {
            var elemName = elem.nodeName.toUpperCase();
            if (elemName === 'SELECT') {
                elem.options[elem.options.length] = new Option(newRepr, newId, true, true);
            } else if (elemName === 'INPUT') {
                if (elem.classList.contains('vManyToManyRawIdAdminField') && elem.value) {
                    elem.value += ',' + newId;
                } else {
                    elem.value = newId;
                }
            }
            // Trigger a change event to update related links if required.
            $(elem).trigger('change');
        } else {
            var toId = name + "_to";
            var o = new Option(newRepr, newId);
            SelectBox.add_to_cache(toId, o);
            SelectBox.redisplay(toId);
        }
        win.close();
    }

    function dismissChangeRelatedObjectPopup(win, objId, newRepr, newId) {
        var id = win.name.replace(/^edit_/, '');
        var selectsSelector = interpolate('#%s, #%s_from, #%s_to', [id, id, id]);
        var selects = $(selectsSelector);
        selects.find('option').each(function() {
            if (this.value === objId) {
                this.textContent = newRepr;
                this.value = newId;
            }
        });
        selects.next().find('.select2-selection__rendered').each(function() {
            // The element can have a clear button as a child.
            // Use the lastChild to modify only the displayed value.
            this.lastChild.textContent = newRepr;
            this.title = newRepr;
        });
        win.close();
    }

    function dismissDeleteRelatedObjectPopup(win, objId) {
        var id = win.name.replace(/^delete_/, '');
        var selectsSelector = interpolate('#%s, #%s_from, #%s_to', [id, id, id]);
        var selects = $(selectsSelector);
        selects.find('option').each(function() {
            if (this.value === objId) {
                $(this).remove();
            }
        }).trigger('change');
        win.close();
    }

    window.showRelatedObjectLookupPopup = showRelatedObjectLookupPopup;
    window.dismissRelatedLookupPopup = dismissRelatedLookupPopup;
    window.showRelatedObjectPopup = showRelatedObjectPopup;
    window.updateRelatedObjectLinks = updateRelatedObjectLinks;
    window.dismissAddRelatedObjectPopup = dismissAddRelatedObjectPopup;
    window.dismissChangeRelatedObjectPopup = dismissChangeRelatedObjectPopup;
    window.dismissDeleteRelatedObjectPopup = dismissDeleteRelatedObjectPopup;

    // Kept for backward compatibility
    window.showAddAnotherPopup = showRelatedObjectPopup;
    window.dismissAddAnotherPopup = dismissAddRelatedObjectPopup;

    $(document).ready(function() {
        $("a[data-popup-opener]").on('click', function(event) {
            event.preventDefault();
            opener.dismissRelatedLookupPopup(window, $(this).data("popup-opener"));
        });
        $('body').on('click', '.related-widget-wrapper-link', function(e) {
            e.preventDefault();
            if (this.href) {
                var event = $.Event('django:show-related', {href: this.href});
                $(this).trigger(event);
                if (!event.isDefaultPrevented()) {
                    showRelatedObjectPopup(this);
                }
            }
        });
        $('body').on('change', '.related-widget-wrapper select', function(e) {
            var event = $.Event('django:update-related');
            $(this).trigger(event);
            if (!event.isDefaultPrevented()) {
                updateRelatedObjectLinks(this);
            }
        });
        $('.related-widget-wrapper select').trigger('change');
        $('body').on('click', '.related-lookup', function(e) {
            e.preventDefault();
            var event = $.Event('django:lookup-related');
            $(this).trigger(event);
            if (!event.isDefaultPrevented()) {
                showRelatedObjectLookupPopup(this);
            }
        });
    });

})(django.jQuery);
