var SelectBox = {
    cache: new Object(),
    initialised: new Object(),
    init: function(id) {
        var box = document.getElementById(id),
            node;
        SelectBox.cache[id] = new Array();
        for (var i = 0; (node = box.options[i]); i++) {
            node.order = i; // Record the initial order
            if (django.jQuery.browser.msie) node.text_copy = node.text;
            node.displayed = true;
            SelectBox.add_to_cache(id, node);
        }
    },
    redisplay: function(box, also_wipe) {
        // Repopulate HTML select box from cache
        var fragment = document.createDocumentFragment(),
            node;

        // Setting innerHTML doubles the speed by making it unnecessary for the
        // browser to compliment appendChild with removeChild. For example, in
        // Chrome it literally doubles the speed of moving nodes up the DOM but
        // has no effect on moving nodes down the DOM.
        //
        // However it also deletes the text nodes under the option nodes in all
        // versions of IE. Even deep cloning doesn't fix it so we have to
        // recreate them.
        box.innerHTML = '';
        if (also_wipe) also_wipe.innerHTML = '';

        for (var i = 0, j = SelectBox.cache[box.id].length; i < j; i++) {
            node = SelectBox.cache[box.id][i];
            if (node && node.displayed) {
                if (django.jQuery.browser.msie) {
                    node.appendChild(document.createTextNode(node.text_copy));
                }
                fragment.appendChild(node);
            }
        }
        box.appendChild(fragment); 
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
        for (var i = 0; i < SelectBox.cache[id].length; i++) {
            node = SelectBox.cache[id][i];
            if (node) node.displayed = SelectBox.is_filter_match(tokens, node.text);
        }
        
        var box = document.getElementById(id);
        SelectBox.redisplay(box);
        // Sometimes Chrome doesn't scroll up after a filter which makes it look
        // like there's no results even when there are
        box.scrollTop = 0;
    },
    add_new: function(id, option) {
        var from_box = document.getElementById(id + '_from'),
            to_box = document.getElementById(id + '_to');
        if (django.jQuery.browser.msie) {
            option.text_copy = option.text;
            option.appendChild(document.createTextNode(option.text));
        }
        SelectBox.add_to_cache(id + '_to', option);
        // We could order alphabetically but what if the data isn't meant to be
        // alphabetical? Just adding to the end is more predictable, not to
        // mention it avoids ordering differences between browsers, databases
        // and l10n.
        option.order = to_box.options.length + from_box.options.length;
        SelectBox.insert_option(to_box, option, 0, true);
    },
    delete_from_cache: function(id, option) {
        delete SelectBox.cache[id][option.cache_key];
        delete option.cache_key;
    },
    swap_cache: function(from, to, option) {
        SelectBox.delete_from_cache(from, option);
        SelectBox.add_to_cache(to, option);
    },
    add_to_cache: function(id, option) {
        SelectBox.cache[id].push(option);
        option.cache_key = SelectBox.cache[id].length - 1;
    },
    merge_cache: function(from, to) {
        SelectBox.cache[to] = SelectBox.cache[to].concat(SelectBox.cache[from]);
        SelectBox.cache[from] = Array();
    },
    insert_option: function(to_box, option, i, no_search) {
        if (!no_search) {
            for (var i = i; (next_option = to_box.options[i]); i++) {
                if (next_option.order > option.order) {
                    next_option.parentNode.insertBefore(option, next_option);
                    return i;
                }
            }
        }

        to_box.appendChild(option);
        return ++i;
    },
    move: function(from, to, all) {
        var from_box = document.getElementById(from),
            to_box = document.getElementById(to),
            num_selected = 0,
            last_compare_position = 0,
            to_needs_sort = false,
            initial = typeof SelectBox.initialised[from] === 'undefined',
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

        // Eventually, moving one node at a time becomes slower than a total redisplay
        large_movement = num_selected > 4000;

        if (/_from$/.test(to_box.id)) {
            filter_text = document.getElementById(to_box.id.slice(0, -5) + '_input').value;
            if (filter_text) filter_tokens = filter_text.toLowerCase().split(/\s+/);
        }

        if (all && large_movement) {
            SelectBox.merge_cache(from, to);
        } else {
            for (var i = 0; (option = from_box.options[i]); i++) {
                if (all || option.selected) {
                    SelectBox.swap_cache(from, to, option);

                    // Take the option out of the DOM otherwise setting selected to false
                    // is the slowest thing out of all this code in all browsers except Firefox
                    from_box.removeChild(option);
                    option.selected = false;

                    // Don't add to to_box if there's a filter applied that doesn't match
                    if (!filter_tokens || SelectBox.is_filter_match(filter_tokens, option.text)) {
                        last_compare_position = SelectBox.insert_option(
                            to_box, option, last_compare_position, initial
                        );
                    } else {
                        // Because we didn't move the option into the sorted HTML
                        // we will need to sort the cache instead
                        to_needs_sort = true;
                    }

                    i--; // We have to decrement because we're modifying as iterating
                }
            }
        }

        SelectBox.sort(to);

        if (large_movement) {
            if (!initial) {
                SelectBox.sort(from);
                SelectBox.sort(to);
            }
            SelectBox.redisplay(from_box, to_box);
            SelectBox.redisplay(to_box);
        }

        if (initial) {
            SelectBox.initialised[from] = true;
            SelectBox.initialised[to] = true;
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
    },
    move_all: function(from, to) {
        SelectBox.move(from, to, true);
    },
    sort: function(id) {
        SelectBox.cache[id].sort(function(a, b) {
            try {
                if (a.order > b.order) {
                    a.cache_key++;
                    return 1;
                } else if (a.order < b.order) {
                    a.cache_key--;
                    return -1;
                }
            }
            catch (e) {
                // silently fail on IE 'unknown' exception
            }
            return 0;
        } );
    },
    select_all: function(id) {
        var box = document.getElementById(id);
        for (var i = 0; i < box.options.length; i++) {
            box.options[i].selected = true;
        }
    }
}
