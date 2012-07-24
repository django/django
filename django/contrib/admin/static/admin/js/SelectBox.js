var SelectBox = {
    initialised: false,
    options: new Object(),
    init: function(id) {
        var box = document.getElementById(id + '_from'),
            node;

        SelectBox.options[id] = new Array();
        for (var i = 0; (node = box.options[i]); i++) {
            node.order = i; // Record the initial order
            if (django.jQuery.browser.msie) node.text_copy = node.text;
            node.displayed = true;
            node.select_boxed = false;
            SelectBox.add_to_options(id, node);
        }

        SelectBox.move(id);
        // This prevents a jump on focus if options have been moved out
        box.selectedIndex = -1;

        SelectBox.register_onpopstate();
        SelectBox.initialised = true;
    },
    redisplay: function(id, large, all, webkit_repair) {
        // Repopulate HTML select box from options
        var from_fragment = document.createDocumentFragment(),
            to_fragment = document.createDocumentFragment(),
            from_box = document.getElementById(id + '_from'),
            to_box = document.getElementById(id + '_to'),
            node, add_to;

        // Setting innerHTML doubles the speed by making it unnecessary for the
        // browser to compliment appendChild with removeChild. For example, in
        // Chrome it literally doubles the speed of moving nodes up the DOM but
        // has no effect on moving nodes down the DOM.
        //
        // However it also deletes the text nodes under the option nodes in all
        // versions of IE. Even deep cloning doesn't fix it so we have to
        // recreate them.
        from_box.innerHTML = '';
        if (large) to_box.innerHTML = '';

        for (var i = 0, j = SelectBox.options[id].length; i < j; i++) {
            node = SelectBox.options[id][i];
            if (node.displayed) {
                if (webkit_repair) {
                    node.select_boxed = node.selected;
                } else if (!all && node.selected) {
                    node.select_boxed = !node.select_boxed;
                }
                node.selected = false;
                add_to = (!node.select_boxed) ? from_fragment : (large || webkit_repair) ? to_fragment : null;
                if (add_to) {
                    if (django.jQuery.browser.msie) {
                        node.appendChild(document.createTextNode(node.text_copy));
                    }
                    add_to.appendChild(node);
                }
            }
        }

        from_box.appendChild(from_fragment); 
        from_box.selectedIndex = -1;
        to_box.appendChild(to_fragment); 
        to_box.selectedIndex = -1;
    },
    is_filter_match: function(tokens, text) {
        var token;
        for (var j = 0; (token = tokens[j]); j++) {
            if (text.toLowerCase().indexOf(token) == -1) {
                return false;
            }
        }
        return true;
    },
    filter: function(id, text) {
        // Redisplay the HTML select box, displaying only the choices containing ALL
        // the words in text. (It's an AND search.)
        var tokens = text.toLowerCase().split(/\s+/),
            node;
        for (var i = 0; i < SelectBox.options[id].length; i++) {
            node = SelectBox.options[id][i];
            if (node) node.displayed = SelectBox.is_filter_match(tokens, node.text);
        }
        
        SelectBox.redisplay(id);

        // Sometimes Chrome doesn't scroll up after a filter which makes it look
        // like there's no results even when there are
        document.getElementById(id + '_from').scrollTop = 0;
    },
    add_new: function(id, option) {
        var from_box = document.getElementById(id + '_from'),
            to_box = document.getElementById(id + '_to');
        if (django.jQuery.browser.msie) {
            option.text_copy = option.text;
            option.appendChild(document.createTextNode(option.text));
        }
        option.displayed = true;
        option.select_boxed = true;
        SelectBox.add_to_options(id, option);
        // We could order alphabetically but what if the data isn't meant to be
        // alphabetical? Just adding to the end is more predictable, not to
        // mention it avoids ordering differences between browsers, databases
        // and l10n.
        option.order = SelectBox.options[id].length;
        SelectBox.insert_option(to_box, option, 0, true);
        SelectBox.replace_state();
    },
    add_to_options: function(id, option) {
        SelectBox.options[id].push(option);
    },
    insert_option: function(to_box, option, i, no_search) {
        var old_index = to_box.selectedIndex;

        if (!no_search) {
            for (var i = i; (next_option = to_box.options[i]); i++) {
                if (next_option.order > option.order) {
                    next_option.parentNode.insertBefore(option, next_option);
                    if ((to_box.selectedIndex > -1) && (i < to_box.selectedIndex)) {
                        // Maintains the old index to prevent a jump when the box
                        // regains focus
                        to_box.selectedIndex = old_index + 1;
                    }
                    return i;
                }
            }
        }

        to_box.appendChild(option);
        return ++i;
    },
    move: function(id, reverse, all) {
        var from_box = document.getElementById(id + ((!reverse) ? '_from' : '_to')),
            to_box = document.getElementById(id + ((reverse) ? '_from' : '_to')),
            num_selected = 0,
            last_compare_position = 0,
            old_selected_index = from_box.selectedIndex,
            option, compare_text, large_movement, filter_text, filter_tokens;

        if (all) {
            num_selected = from_box.options.length;
        } else {
            if (typeof from_box.selectedOptions !== 'undefined') {
                // Fast method for browsers that support it (Chrome)
                num_selected = from_box.selectedOptions.length;
            } else {
                for (var i = 0; (option = from_box.options[i]); i++) {
                    if (option.selected) num_selected++;
                }
            }
        }

        all = all || num_selected == from_box.options.length;
        // Eventually, moving one node at a time becomes slower than a total redisplay
        large_movement = num_selected > 1000;

        if (reverse) {
            filter_text = document.getElementById(to_box.id.slice(0, -5) + '_input').value;
            if (filter_text) filter_tokens = filter_text.toLowerCase().split(/\s+/);
        }

        if (all && large_movement) {
            for (var i = 0; (option = from_box.options[i]); i++) {
                option.select_boxed = !reverse;
            }
        }

        if (large_movement) {
            SelectBox.redisplay(id, large_movement, all);
        } else {
            for (var i = 0; (option = from_box.options[i]); i++) {
                if (all || option.selected) {
                    option.select_boxed = !option.select_boxed;

                    // Take the option out of the DOM otherwise setting selected to false
                    // is the slowest thing out of all this code in all browsers except Firefox
                    from_box.removeChild(option);
                    option.selected = false;

                    // Don't add to to_box if there's a filter applied that doesn't match
                    if (!filter_tokens || SelectBox.is_filter_match(filter_tokens, option.text)) {
                        last_compare_position = SelectBox.insert_option(
                            to_box, option, last_compare_position, to_box.options.length == 0
                        );
                    }

                    i--; // We have to decrement because we're modifying as iterating
                }
            }
        }

        // This forces the list to scroll to the top of your previous selection
        // after a chunk movement. Without it you often end up in the middle 
        // of nowhere and lost.
        //
        // 13 and 70 were chosen based on the height of the boxes in the default
        // Django theme and will place the top of your previous selection in
        // about the middle. It needs a slight delay to fire properly in most
        // browsers.
        //
        // It doesn't work in Opera because Opera doesn't let you set scrollTop on
        // select elements. But Opera does almost the same by default anyway
        // (basically it won't have the -70).
        if (!django.jQuery.browser.opera && (large_movement || num_selected > 13)) {
            setTimeout(function() {
                from_box.selectedIndex = old_selected_index;
                var scroll_position = from_box.scrollTop - 70;
                from_box.selectedIndex = -1;
                from_box.scrollTop = scroll_position;
            }, 10);
        }

        SelectBox.replace_state();
    },
    move_all: function(id, reverse) {
        SelectBox.move(id, reverse, true);
    },
    select_all: function(id) {
        var box = document.getElementById(id);
        for (var i = 0; i < box.options.length; i++) {
            box.options[i].selected = true;
        }
    },
    replace_state: function() {
        if (!django.jQuery.browser.webkit) return;
        // Make Webkit fire a distinct onpopstate on back button
        history.replaceState({}, null);
    },
    register_onpopstate: function() {
        if (SelectBox.initialised || !django.jQuery.browser.webkit) return;

        var initial_state = {content: django.jQuery('#content').html()},
            popped = ('state' in window.history),
            state;

        django.jQuery(window).bind('popstate', function(e) {
            if (!popped) {
                // Ignore first page loads
                popped = true;
            }
            if (e.originalEvent.state != null) {
                for (id in SelectBox.options) {
                    SelectBox.redisplay(id, false, false, true);
                }
            }
        });
    }
}
