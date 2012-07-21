var SelectBox = {
    cache: new Object(),
    cache_map: new Object(),
    initialised: new Object(),
    init: function(id) {
        var box = document.getElementById(id),
            node;
        SelectBox.cache[id] = new Array();
        SelectBox.cache_map[id] = new Object();
        for (var i = 0; (node = box.options[i]); i++) {
            SelectBox.add_to_cache(id, {value: node.value, text: node.text, displayed: 1});
        }
    },
    redisplay: function(id) {
        // Repopulate HTML select box from cache
        var box = document.getElementById(id);
        box.innerHTML = ''; // clear all options 
        var fragment = document.createDocumentFragment();
        for (var i = 0, j = SelectBox.cache[id].length; i < j; i++) {
            var node = SelectBox.cache[id][i];
            if (node.displayed) {
                fragment.appendChild(new Option(node.text, node.value, false, false)); 
            }
        }
        box.appendChild(fragment.cloneNode(true)); 
    },
    filter: function(id, text) {
        // Redisplay the HTML select box, displaying only the choices containing ALL
        // the words in text. (It's an AND search.)
        var tokens = text.toLowerCase().split(/\s+/),
            node, token;
        for (var i = 0; (node = SelectBox.cache[id][i]); i++) {
            node.displayed = 1;
            for (var j = 0; (token = tokens[j]); j++) {
                if (node.text.toLowerCase().indexOf(token) == -1) {
                    node.displayed = 0;
                }
            }
        }
        SelectBox.redisplay(id);
    },
    delete_from_cache: function(id, option) {
        var j = SelectBox.cache[id].length - 1,
            option;
        for (var i = SelectBox.cache_map[id][option.value]; i < j; i++) {
            option = SelectBox.cache[id][i + 1];
            SelectBox.cache[id][i] = option;
            SelectBox.cache_map[id][option.value] = i;
        }
        SelectBox.cache[id].length--;
        delete SelectBox.cache_map[id][option.value];
    },
    add_to_cache: function(id, option) {
        SelectBox.cache[id].push({value: option.value, text: option.text, displayed: 1});
        SelectBox.cache_map[id][option.value] = SelectBox.cache[id].length - 1;
    },
    cache_contains: function(id, option) {
        return SelectBox.cache_map[id][option.value] !== 'undefined';
    },
    merge_cache: function(from, to) {
        SelectBox.cache[to] = SelectBox.cache[to].concat(SelectBox.cache[from]);
        SelectBox.cache_map[to] = Object();
        for (var i = 0; (option = SelectBox.cache[to][i]); i++) {
            SelectBox.cache_map[to][option.value] = i;
        }
        SelectBox.cache[from] = Array();
        SelectBox.cache_map[from] = Object();
    },
    move: function(from, to, all) {
        var from_box = document.getElementById(from),
            to_box = document.getElementById(to),
            num_selected = 0,
            initial = typeof SelectBox.initialised[from] === 'undefined',
            option, compare_text, large_movement;

        if (!all) {
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
        large_movement = all || num_selected > 100;

        if (all) {
            SelectBox.merge_cache(from, to);
        } else {
            for (var i = 0; (option = from_box.options[i]); i++) {
                if (option.selected && SelectBox.cache_contains(from, option)) {
                    SelectBox.add_to_cache(to, option);
                    SelectBox.delete_from_cache(from, option);
                    option.selected = '';

                    // It's faster to redisplay for large movements
                    if (!large_movement) {
                        // Initial data should already be alphabetical
                        if (!initial) {
                            compare_text = option.text.toLowerCase();
                            for (var j = 0; (next_option = to_box.options[j]); j++) {
                                if (next_option.text.toLowerCase() > compare_text) {
                                    next_option.parentNode.insertBefore(option, next_option);
                                    i--; // We have to decrement because we're modifying as iterating
                                    option = null;
                                    break;
                                }
                            }
                        }

                        if (option != null) {
                            to_box.appendChild(option);
                            i--; // We have to decrement because we're modifying as iterating
                        }
                    }
                }
            }
        }

        if (large_movement) {
            if (!initial) {
                SelectBox.sort(from);
                SelectBox.sort(to);
            }
            SelectBox.redisplay(from);
            SelectBox.redisplay(to);
        }

        if (initial) {
            SelectBox.initialised[from] = true;
            SelectBox.initialised[to] = true;
        }
    },
    move_all: function(from, to) {
        SelectBox.move(from, to, true);
    },
    sort: function(id) {
        SelectBox.cache[id].sort( function(a, b) {
            a = a.text.toLowerCase();
            b = b.text.toLowerCase();
            try {
                if (a > b) return 1;
                if (a < b) return -1;
            }
            catch (e) {
                // silently fail on IE 'unknown' exception
            }
            return 0;
        } );
    },
    select_all: function(id) {
        // Selecting too many options will lock up every browser except Firefox for a couple of minutes
        var box = document.getElementById(id);
        for (var i = 0; i < box.options.length; i++) {
            box.options[i].selected = 'selected';
        }
    }
}
