(function() {
    'use strict';
    const SelectBox = {
        cache: {},
        init: function(id) {
            const box = document.getElementById(id);
            SelectBox.cache[id] = [];
            const cache = SelectBox.cache[id];
            const boxOptions = box.options;
            const boxOptionsLength = boxOptions.length;
            for (let i = 0, j = boxOptionsLength; i < j; i++) {
                const node = boxOptions[i];
                cache.push({value: node.value, text: node.text, displayed: 1});
            }
        },
        redisplay: function(id) {
            // Repopulate HTML select box from cache
            const box = document.getElementById(id);
            box.innerHTML = '';
            const cache = SelectBox.cache[id];
            for (let i = 0, j = cache.length; i < j; i++) {
                const node = cache[i];
                if (node.displayed) {
                    const new_option = new Option(node.text, node.value, false, false);
                    // Shows a tooltip when hovering over the option
                    new_option.title = node.text;
                    box.appendChild(new_option);
                }
            }
        },
        filter: function(id, text) {
            // Redisplay the HTML select box, displaying only the choices containing ALL
            // the words in text. (It's an AND search.)
            const tokens = text.toLowerCase().split(/\s+/);
            const cache = SelectBox.cache[id];
            for (let i = 0, j = cache.length; i < j; i++) {
                const node = cache[i];
                node.displayed = 1;
                const node_text = node.text.toLowerCase();
                const numTokens = tokens.length;
                for (let k = 0; k < numTokens; k++) {
                    const token = tokens[k];
                    if (node_text.indexOf(token) === -1) {
                        node.displayed = 0;
                        break; // Once the first token isn't found we're done
                    }
                }
            }
            SelectBox.redisplay(id);
        },
        delete_from_cache: function(id, value) {
            let delete_index = null;
            const cache = SelectBox.cache[id];
            for (let i = 0, j = cache.length; i < j; i++) {
                const node = cache[i];
                if (node.value === value) {
                    delete_index = i;
                    break;
                }
            }
            cache.splice(delete_index, 1);
        },
        add_to_cache: function(id, option) {
            SelectBox.cache[id].push({value: option.value, text: option.text, displayed: 1});
        },
        cache_contains: function(id, value) {
            // Check if an item is contained in the cache
            const cache = SelectBox.cache[id];
            for (let i = 0, j = cache.length; i < j; i++) {
                const node = cache[i];
                if (node.value === value) {
                    return true;
                }
            }
            return false;
        },
        move: function(from, to) {
            const from_box = document.getElementById(from);
            const boxOptions = from_box.options;
            const boxOptionsLength = boxOptions.length;
            for (let i = 0, j = boxOptionsLength; i < j; i++) {
                const option = boxOptions[i];
                const option_value = option.value;
                if (option.selected && SelectBox.cache_contains(from, option_value)) {
                    SelectBox.add_to_cache(to, {value: option_value, text: option.text, displayed: 1});
                    SelectBox.delete_from_cache(from, option_value);
                }
            }
            SelectBox.redisplay(from);
            SelectBox.redisplay(to);
        },
        move_all: function(from, to) {
            const from_box = document.getElementById(from);
            const boxOptions = from_box.options;
            const boxOptionsLength = boxOptions.length;
            for (let i = 0, j = boxOptionsLength; i < j; i++) {
                const option = boxOptions[i];
                const option_value = option.value;
                if (SelectBox.cache_contains(from, option_value)) {
                    SelectBox.add_to_cache(to, {value: option_value, text: option.text, displayed: 1});
                    SelectBox.delete_from_cache(from, option_value);
                }
            }
            SelectBox.redisplay(from);
            SelectBox.redisplay(to);
        },
        sort: function(id) {
            SelectBox.cache[id].sort(function(a, b) {
                a = a.text.toLowerCase();
                b = b.text.toLowerCase();
                if (a > b) {
                    return 1;
                }
                if (a < b) {
                    return -1;
                }
                return 0;
            } );
        },
        select_all: function(id) {
            const box = document.getElementById(id);
            const boxOptions = box.options;
            const boxOptionsLength = boxOptions.length;
            for (let i = 0; i < boxOptionsLength; i++) {
                boxOptions[i].selected = 'selected';
            }
        }
    };
    window.SelectBox = SelectBox;
})();
