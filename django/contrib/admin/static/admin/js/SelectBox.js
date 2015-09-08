(function() {
    'use strict';
    var SelectBox = {
        cache: {},
        init: function(id) {
            var box = document.getElementById(id);
            var node;
            SelectBox.cache[id] = [];
            var cache = SelectBox.cache[id];
            for (var i = 0, j = box.options.length; i < j; i++) {
                node = box.options[i];
                cache.push({value: node.value, text: node.text, displayed: 1});
            }
        },
        redisplay: function(id) {
            // Repopulate HTML select box from cache
            var box = document.getElementById(id);
            var node;
            box.options.length = 0; // clear all options
            var cache = SelectBox.cache[id];
            for (var i = 0, j = cache.length; i < j; i++) {
                node = cache[i];
                if (node.displayed) {
                    var new_option = new Option(node.text, node.value, false, false);
                    // Shows a tooltip when hovering over the option
                    new_option.setAttribute("title", node.text);
                    box.options[box.options.length] = new_option;
                }
            }
        },
        filter: function(id, text) {
            // Redisplay the HTML select box, displaying only the choices containing ALL
            // the words in text. (It's an AND search.)
            var tokens = text.toLowerCase().split(/\s+/);
            var node, token;
            var cache = SelectBox.cache[id];
            for (var i = 0, j = cache.length; i < j; i++) {
                node = cache[i];
                node.displayed = 1;
                var numTokens = tokens.length;
                for (var k = 0; k < numTokens; k++) {
                    token = tokens[k];
                    if (node.text.toLowerCase().indexOf(token) === -1) {
                        node.displayed = 0;
                    }
                }
            }
            SelectBox.redisplay(id);
        },
        delete_from_cache: function(id, value) {
            var node, delete_index = null;
            var cache = SelectBox.cache[id];
            for (var i = 0, j = cache.length; i < j; i++) {
                node = cache[i];
                if (node.value === value) {
                    delete_index = i;
                    break;
                }
            }
            var k = cache.length - 1;
            for (i = delete_index; i < k; i++) {
                cache[i] = cache[i + 1];
            }
            cache.length--;
        },
        add_to_cache: function(id, option) {
            SelectBox.cache[id].push({value: option.value, text: option.text, displayed: 1});
        },
        cache_contains: function(id, value) {
            // Check if an item is contained in the cache
            var node;
            var cache = SelectBox.cache[id];
            for (var i = 0, j = cache.length; i < j; i++) {
                node = cache[i];
                if (node.value === value) {
                    return true;
                }
            }
            return false;
        },
        move: function(from, to) {
            var from_box = document.getElementById(from);
            var option;
            var boxOptions = from_box.options;
            for (var i = 0, j = boxOptions.length; i < j; i++) {
                option = boxOptions[i];
                if (option.selected && SelectBox.cache_contains(from, option.value)) {
                    SelectBox.add_to_cache(to, {value: option.value, text: option.text, displayed: 1});
                    SelectBox.delete_from_cache(from, option.value);
                }
            }
            SelectBox.redisplay(from);
            SelectBox.redisplay(to);
        },
        move_all: function(from, to) {
            var from_box = document.getElementById(from);
            var option;
            var boxOptions = from_box.options;
            for (var i = 0, j = boxOptions.length; i < j; i++) {
                option = boxOptions[i];
                if (SelectBox.cache_contains(from, option.value)) {
                    SelectBox.add_to_cache(to, {value: option.value, text: option.text, displayed: 1});
                    SelectBox.delete_from_cache(from, option.value);
                }
            }
            SelectBox.redisplay(from);
            SelectBox.redisplay(to);
        },
        sort: function(id) {
            SelectBox.cache[id].sort(function(a, b) {
                a = a.text.toLowerCase();
                b = b.text.toLowerCase();
                try {
                    if (a > b) {
                        return 1;
                    }
                    if (a < b) {
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
                box.options[i].selected = 'selected';
            }
        }
    };
    window.SelectBox = SelectBox;
})();
