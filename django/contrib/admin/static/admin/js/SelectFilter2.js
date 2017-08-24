/*global SelectBox, gettext, interpolate, quickElement, SelectFilter*/
/*
SelectFilter2 - Turns a multiple-select box into a filter interface.

Requires jQuery, core.js, and SelectBox.js.
*/
(function($) {
    'use strict';
    function findForm(node) {
        // returns the node of the form containing the given node
        if (node.tagName.toLowerCase() !== 'form') {
            return findForm(node.parentNode);
        }
        return node;
    }

    window.SelectFilter = {
        init: function(field_id, field_name, is_stacked) {
            if (field_id.match(/__prefix__/)) {
                // Don't initialize on empty forms.
                return;
            }
            var from_box = document.getElementById(field_id);
            from_box.id += '_from'; // change its ID
            from_box.className = 'filtered';

            var ps = from_box.parentNode.getElementsByTagName('p');
            for (var i = 0; i < ps.length; i++) {
                if (ps[i].className.indexOf("info") !== -1) {
                    // Remove <p class="info">, because it just gets in the way.
                    from_box.parentNode.removeChild(ps[i]);
                } else if (ps[i].className.indexOf("help") !== -1) {
                    // Move help text up to the top so it isn't below the select
                    // boxes or wrapped off on the side to the right of the add
                    // button:
                    from_box.parentNode.insertBefore(ps[i], from_box.parentNode.firstChild);
                }
            }

            // <div class="selector"> or <div class="selector stacked">
            var selector_div = quickElement('div', from_box.parentNode);
            selector_div.className = is_stacked ? 'selector stacked' : 'selector';

            // <div class="selector-available">
            var selector_available = quickElement('div', selector_div);
            selector_available.className = 'selector-available';
            var title_available = quickElement('h2', selector_available, interpolate(gettext('Available %s') + ' ', [field_name]));
            quickElement(
                'span', title_available, '',
                'class', 'help help-tooltip help-icon',
                'title', interpolate(
                    gettext(
                        'This is the list of available %s. You may choose some by ' +
                        'selecting them in the box below and then clicking the ' +
                        '"Choose" arrow between the two boxes.'
                    ),
                    [field_name]
                )
            );

            var filter_p = quickElement('p', selector_available, '', 'id', field_id + '_filter');
            filter_p.className = 'selector-filter';

            var search_filter_label = quickElement('label', filter_p, '', 'for', field_id + '_input');

            quickElement(
                'span', search_filter_label, '',
                'class', 'help-tooltip search-label-icon',
                'title', interpolate(gettext("Type into this box to filter down the list of available %s."), [field_name])
            );

            filter_p.appendChild(document.createTextNode(' '));

            var filter_input = quickElement('input', filter_p, '', 'type', 'text', 'placeholder', gettext("Filter"));
            filter_input.id = field_id + '_input';

            selector_available.appendChild(from_box);
            var choose_all = quickElement('a', selector_available, gettext('Choose all'), 'title', interpolate(gettext('Click to choose all %s at once.'), [field_name]), 'href', '#', 'id', field_id + '_add_all_link');
            choose_all.className = 'selector-chooseall';

            // <ul class="selector-chooser">
            var selector_chooser = quickElement('ul', selector_div);
            selector_chooser.className = 'selector-chooser';
            var add_link = quickElement('a', quickElement('li', selector_chooser), gettext('Choose'), 'title', gettext('Choose'), 'href', '#', 'id', field_id + '_add_link');
            add_link.className = 'selector-add';
            var remove_link = quickElement('a', quickElement('li', selector_chooser), gettext('Remove'), 'title', gettext('Remove'), 'href', '#', 'id', field_id + '_remove_link');
            remove_link.className = 'selector-remove';

            // <div class="selector-chosen">
            var selector_chosen = quickElement('div', selector_div);
            selector_chosen.className = 'selector-chosen';
            var title_chosen = quickElement('h2', selector_chosen, interpolate(gettext('Chosen %s') + ' ', [field_name]));
            quickElement(
                'span', title_chosen, '',
                'class', 'help help-tooltip help-icon',
                'title', interpolate(
                    gettext(
                        'This is the list of chosen %s. You may remove some by ' +
                        'selecting them in the box below and then clicking the ' +
                        '"Remove" arrow between the two boxes.'
                    ),
                    [field_name]
                )
            );

            var to_box = quickElement('select', selector_chosen, '', 'id', field_id + '_to', 'multiple', 'multiple', 'size', from_box.size, 'name', from_box.getAttribute('name'));
            to_box.className = 'filtered';
            var clear_all = quickElement('a', selector_chosen, gettext('Remove all'), 'title', interpolate(gettext('Click to remove all chosen %s at once.'), [field_name]), 'href', '#', 'id', field_id + '_remove_all_link');
            clear_all.className = 'selector-clearall';

            from_box.setAttribute('name', from_box.getAttribute('name') + '_old');

            // Set up the JavaScript event handlers for the select box filter interface
            var move_selection = function(e, elem, move_func, from, to) {
                if (elem.className.indexOf('active') !== -1) {
                    move_func(from, to);
                    SelectFilter.refresh_icons(field_id);
                }
                e.preventDefault();
            };
            choose_all.addEventListener('click', function(e) {
                move_selection(e, this, SelectBox.move_all, field_id + '_from', field_id + '_to');
            });
            add_link.addEventListener('click', function(e) {
                move_selection(e, this, SelectBox.move, field_id + '_from', field_id + '_to');
            });
            remove_link.addEventListener('click', function(e) {
                move_selection(e, this, SelectBox.move, field_id + '_to', field_id + '_from');
            });
            clear_all.addEventListener('click', function(e) {
                move_selection(e, this, SelectBox.move_all, field_id + '_to', field_id + '_from');
            });
            filter_input.addEventListener('keypress', function(e) {
                SelectFilter.filter_key_press(e, field_id);
            });
            filter_input.addEventListener('keyup', function(e) {
                SelectFilter.filter_key_up(e, field_id);
            });
            filter_input.addEventListener('keydown', function(e) {
                SelectFilter.filter_key_down(e, field_id);
            });
            selector_div.addEventListener('change', function(e) {
                if (e.target.tagName === 'SELECT') {
                    SelectFilter.refresh_icons(field_id);
                }
            });
            selector_div.addEventListener('dblclick', function(e) {
                if (e.target.tagName === 'OPTION') {
                    if (e.target.closest('select').id === field_id + '_to') {
                        SelectBox.move(field_id + '_to', field_id + '_from');
                    } else {
                        SelectBox.move(field_id + '_from', field_id + '_to');
                    }
                    SelectFilter.refresh_icons(field_id);
                }
            });
            findForm(from_box).addEventListener('submit', function() {
                SelectBox.select_all(field_id + '_to');
            });
            SelectBox.init(field_id + '_from');
            SelectBox.init(field_id + '_to');
            // Move selected from_box options to to_box
            SelectBox.move(field_id + '_from', field_id + '_to');

            if (!is_stacked) {
                // In horizontal mode, give the same height to the two boxes.
                var j_from_box = $(from_box);
                var j_to_box = $(to_box);
                var resize_filters = function() { j_to_box.height($(filter_p).outerHeight() + j_from_box.outerHeight()); };
                if (j_from_box.outerHeight() > 0) {
                    resize_filters(); // This fieldset is already open. Resize now.
                } else {
                    // This fieldset is probably collapsed. Wait for its 'show' event.
                    j_to_box.closest('fieldset').one('show.fieldset', resize_filters);
                }
            }

            // Initial icon refresh
            SelectFilter.refresh_icons(field_id);
        },
        any_selected: function(field) {
            var any_selected = false;
            try {
                // Temporarily add the required attribute and check validity.
                // This is much faster in WebKit browsers than the fallback.
                field.attr('required', 'required');
                any_selected = field.is(':valid');
                field.removeAttr('required');
            } catch (e) {
                // Browsers that don't support :valid (IE < 10)
                any_selected = field.find('option:selected').length > 0;
            }
            return any_selected;
        },
        refresh_icons: function(field_id) {
            var from = $('#' + field_id + '_from');
            var to = $('#' + field_id + '_to');
            // Active if at least one item is selected
            $('#' + field_id + '_add_link').toggleClass('active', SelectFilter.any_selected(from));
            $('#' + field_id + '_remove_link').toggleClass('active', SelectFilter.any_selected(to));
            // Active if the corresponding box isn't empty
            $('#' + field_id + '_add_all_link').toggleClass('active', from.find('option').length > 0);
            $('#' + field_id + '_remove_all_link').toggleClass('active', to.find('option').length > 0);
        },
        filter_key_press: function(event, field_id) {
            var from = document.getElementById(field_id + '_from');
            // don't submit form if user pressed Enter
            if ((event.which && event.which === 13) || (event.keyCode && event.keyCode === 13)) {
                from.selectedIndex = 0;
                SelectBox.move(field_id + '_from', field_id + '_to');
                from.selectedIndex = 0;
                event.preventDefault();
                return false;
            }
        },
        filter_key_up: function(event, field_id) {
            var from = document.getElementById(field_id + '_from');
            var temp = from.selectedIndex;
            SelectBox.filter(field_id + '_from', document.getElementById(field_id + '_input').value);
            from.selectedIndex = temp;
            return true;
        },
        filter_key_down: function(event, field_id) {
            var from = document.getElementById(field_id + '_from');
            // right arrow -- move across
            if ((event.which && event.which === 39) || (event.keyCode && event.keyCode === 39)) {
                var old_index = from.selectedIndex;
                SelectBox.move(field_id + '_from', field_id + '_to');
                from.selectedIndex = (old_index === from.length) ? from.length - 1 : old_index;
                return false;
            }
            // down arrow -- wrap around
            if ((event.which && event.which === 40) || (event.keyCode && event.keyCode === 40)) {
                from.selectedIndex = (from.length === from.selectedIndex + 1) ? 0 : from.selectedIndex + 1;
            }
            // up arrow -- wrap around
            if ((event.which && event.which === 38) || (event.keyCode && event.keyCode === 38)) {
                from.selectedIndex = (from.selectedIndex === 0) ? from.length - 1 : from.selectedIndex - 1;
            }
            return true;
        }
    };

    window.addEventListener('load', function(e) {
        $('select.selectfilter, select.selectfilterstacked').each(function() {
            var $el = $(this),
                data = $el.data();
            SelectFilter.init($el.attr('id'), data.fieldName, parseInt(data.isStacked, 10));
        });
    });

})(django.jQuery);
