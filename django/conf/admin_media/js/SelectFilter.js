/*
SelectFilter - Turns a multiple-select box into a filter interface.

Requires SelectBox.js and addevent.js.
*/

function findForm(node) {
    // returns the node of the form containing the given node
    if (node.tagName.toLowerCase() != 'form') {
        return findForm(node.parentNode);
    }
    return node;
}

var SelectFilter = {
    init: function(field_id) {
        var from_box = document.getElementById(field_id);
        from_box.id += '_from'; // change its ID
        // Create the INPUT input box
        var input_box = document.createElement('input');
        input_box.id = field_id + '_input';
        input_box.setAttribute('type', 'text');
        from_box.parentNode.insertBefore(input_box, from_box);
        from_box.parentNode.insertBefore(document.createElement('br'), input_box.nextSibling);
        // Create the TO box
        var to_box = document.createElement('select');
        to_box.id = field_id + '_to';
        to_box.setAttribute('multiple', 'multiple');
        to_box.setAttribute('size', from_box.size);
        from_box.parentNode.insertBefore(to_box, from_box.nextSibling);
        to_box.setAttribute('name', from_box.getAttribute('name'));
        from_box.setAttribute('name', from_box.getAttribute('name') + '_old');
        // Give the filters a CSS hook
        from_box.setAttribute('class', 'filtered');
        to_box.setAttribute('class', 'filtered');
        // Set up the JavaScript event handlers for the select box filter interface
        addEvent(input_box, 'keyup', function(e) { SelectFilter.filter_key_up(e, field_id); });
        addEvent(input_box, 'keydown', function(e) { SelectFilter.filter_key_down(e, field_id); });
        addEvent(from_box, 'dblclick', function() { SelectBox.move(field_id + '_from', field_id + '_to'); });
        addEvent(from_box, 'focus', function() { input_box.focus(); });
        addEvent(to_box, 'dblclick', function() { SelectBox.move(field_id + '_to', field_id + '_from'); });
        addEvent(findForm(from_box), 'submit', function() { SelectBox.select_all(field_id + '_to'); });
        SelectBox.init(field_id + '_from');
        SelectBox.init(field_id + '_to');
        // Move selected from_box options to to_box
        SelectBox.move(field_id + '_from', field_id + '_to');
    },
    filter_key_up: function(event, field_id) {
        from = document.getElementById(field_id + '_from');
        // don't submit form if user pressed Enter
        if ((event.which && event.which == 13) || (event.keyCode && event.keyCode == 13)) {
            from.selectedIndex = 0;
            SelectBox.move(field_id + '_from', field_id + '_to');
            from.selectedIndex = 0;
            return false;
        }
        var temp = from.selectedIndex;
        SelectBox.filter(field_id + '_from', document.getElementById(field_id + '_input').value);
        from.selectedIndex = temp;
        return true;
    },
    filter_key_down: function(event, field_id) {
        from = document.getElementById(field_id + '_from');
        // right arrow -- move across
        if ((event.which && event.which == 39) || (event.keyCode && event.keyCode == 39)) {
            var old_index = from.selectedIndex;
            SelectBox.move(field_id + '_from', field_id + '_to');
            from.selectedIndex = (old_index == from.length) ? from.length - 1 : old_index;
            return false;
        }
        // down arrow -- wrap around
        if ((event.which && event.which == 40) || (event.keyCode && event.keyCode == 40)) {
            from.selectedIndex = (from.length == from.selectedIndex + 1) ? 0 : from.selectedIndex + 1;
        }
        // up arrow -- wrap around
        if ((event.which && event.which == 38) || (event.keyCode && event.keyCode == 38)) {
            from.selectedIndex = (from.selectedIndex == 0) ? from.length - 1 : from.selectedIndex - 1;
        }
        return true;
    }
}
