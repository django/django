'use strict';
{
    const SelectBox = {
        cache: {},
        init: function(id) {
            const box = document.getElementById(id);
            SelectBox.cache[id] = [];
            const cache = SelectBox.cache[id];
            const noGroup = [];
            if (box.children.length > 0) {
                if (box.children[0].tagName === 'OPTION') {
                    for (const node of box.options) {    
                        noGroup.push({value: node.value, text: node.text, displayed: 1 });
                    }
                    cache.push({ 'group': null, 'items': noGroup });
                }
                if (box.children[0].tagName === 'OPTGROUP') {
                    for (const child of box.children) {    
                        const options = child.children;
                        const group = [];
                        for (const node of options) {    
                            group.push({ value: node.value, text: node.text, displayed: 1 });
                        }
                        cache.push({ 'group': child.label, 'items': group });
                    }
                }
            }
        },
        redisplay: function(id) {
            // Repopulate HTML select box from cache
            const box = document.getElementById(id);
            box.innerHTML = '';
            let referance;
            for (const node of SelectBox.cache[id]) {

                if (node.items.length === 0) {
                    continue; //skip empty groups
                }
                if (node.group === null) {
                    referance = box;
                }
                else {
                    const optgroup = document.createElement("optgroup");
                    optgroup.label = node.group;
                    referance = box.appendChild(optgroup);
                }
                for (const itm of node.items) {    
                    if (itm.displayed) {
                        const option = document.createElement("option");
                        option.value = itm.value;
                        option.text = itm.text;
                        referance.appendChild(option);
                    }
                }
            }
        },
        filter: function(id, text) {
            // Redisplay the HTML select box, displaying only the choices containing ALL
            // the words in text. (It's an AND search.)
            const tokens = text.toLowerCase().split(/\s+/);
            for (const node of SelectBox.cache[id]) {    
                for (const childNode of node.items) {    
                    childNode.displayed = 1;
                    for (const token of tokens) {
                        if (childNode.text.toLowerCase().indexOf(token) < 0) {
                            childNode.displayed = 0;
                            break; // Once the first token isn't found we're done
                        }
                    }
                }
            }
            SelectBox.redisplay(id);
        },
        delete_from_cache: function(id, value) {
            outer:
            for (const referance of SelectBox.cache[id]) {
                const node = referance.items;
                for (let p = 0; p < node.length; p++) {
                    if (node[p].value === value) {
                        node.splice(p, 1);
                        break outer;
                    }
                }
            }
        },
        add_to_cache: function(id, option, group) {
            // Check if an item is contained in the cache
            for (const node of SelectBox.cache[id]) {
                if (node.group === group) {
                    node.items.push({ value: option.value, text: option.text, displayed: 1 });
                    return true;
                }
            }
            SelectBox.cache[id].push({ 'group': group, 'items': [{ value: option.value, text: option.text, displayed: 1 }] });
        },
        move: function(from, to) {
            const from_box = document.getElementById(from);
            for (const option of from_box.options) {
                const option_value = option.value;
                const group = option.parentNode.tagName === 'OPTGROUP' ? option.parentNode.getAttribute('label') : null;
                if (option.selected) {
                    SelectBox.add_to_cache(to, {value: option_value, text: option.text, displayed: 1}, group);
                    SelectBox.delete_from_cache(from, option_value);
                }
            }
            SelectBox.redisplay(from);
            SelectBox.redisplay(to);
        },
        move_all: function(from, to) {
            const from_box = document.getElementById(from);
            for (const option of from_box.options) {
                const option_value = option.value;
                const group = option.parentNode.tagName === 'OPTGROUP' ? option.parentNode.getAttribute('label') : null;
                SelectBox.add_to_cache(to, {value: option_value, text: option.text, displayed: 1}, group);
                SelectBox.delete_from_cache(from, option_value);
            }
            SelectBox.redisplay(from);
            SelectBox.redisplay(to);
        },
        sort: function(id, group) {
            for (const node of SelectBox.cache[id]) {
                if (group === false || node.group === group) {
                    node.items.sort(function(a, b) {
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
                }
            }
        },
        select_all: function(id) {
            const box = document.getElementById(id);
            for (const option of box.options) {
                option.selected = 'selected';
            }
        }
    };
    window.SelectBox = SelectBox;
}
