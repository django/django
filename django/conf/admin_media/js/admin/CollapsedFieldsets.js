// Finds all fieldsets with class="collapse", collapses them, and gives each
// one a "Show foo" link that uncollapses it.

function findForm(node) {
	// returns the node of the form containing the given node
	if (node.tagName.toLowerCase() != 'form') {
		return findForm(node.parentNode);
	}
	return node;
}

var CollapsedFieldsets = {
	collapse_re: /\bcollapse\b/,   // Class of fieldsets that should be dealt with.
	collapsed_re: /\bcollapsed\b/, // Class that fieldsets get when they're hidden.
	collapsed_class: 'collapsed',
	init: function() {
		var fieldsets = document.getElementsByTagName('fieldset');
		var collapsed_seen = false;
		for (var i=0; i<fieldsets.length; i++) {
			var fs = fieldsets[i];
			// Collapse this fieldset if it has the correct class, and if it
			// doesn't have any errors. (Collapsing shouldn't apply in the case
			// of error messages.)
			if (fs.className.match(CollapsedFieldsets.collapse_re) && !CollapsedFieldsets.fieldset_has_errors(fs)) {

				collapsed_seen = true;

				// Give it an additional class, used by CSS to hide it.
				fs.className += ' ' + CollapsedFieldsets.collapsed_class;

				// Get plural verbose name of object.
				var verbose_name = fs.getElementsByTagName('h2')[0].innerHTML;

				// <div class="form-row collapse-toggle" id="fieldsetcollapser1">
				// <a href="javascript:toggleDisplay;">Show section priorities&hellip;</a>
				// </div>
				var div = document.createElement('div');

				// Give it a hook so we can remove it later.
				div.id = 'fieldsetcollapser' + i;

				div.className = 'form-row collapse-toggle'; // CSS hook
				var collapse_link = document.createElement('a');
				collapse_link.setAttribute('href', 'javascript:CollapsedFieldsets.display(' + i + ');');
				collapse_link.appendChild(document.createTextNode('Show ' + verbose_name));
				div.appendChild(collapse_link);
				fs.appendChild(div);
			}
		}
		if (collapsed_seen) {
			// Expand all collapsed fieldsets when form is submitted.
			addEvent(findForm(document.getElementsByTagName('fieldset')[0]), 'submit', function() { CollapsedFieldsets.uncollapse_all(); });
		}
	},
	fieldset_has_errors: function(fs) {
		// Returns true if any fields in the fieldset have validation errors.
		var divs = fs.getElementsByTagName('div');
		for (var i=0; i<divs.length; i++) {
			if (divs[i].className.match(/\berror\b/)) {
				return true;
			}
		}
		return false;
	},
	display: function(fieldset_index) {
		var fs = document.getElementsByTagName('fieldset')[fieldset_index];
		// Remove the class name that causes the "display: none".
		fs.className = fs.className.replace(CollapsedFieldsets.collapsed_re, '');
		// Remove the "Show foo" link.
		fs.removeChild(document.getElementById('fieldsetcollapser' + fieldset_index));
	},
	uncollapse_all: function() {
		var fieldsets = document.getElementsByTagName('fieldset');
		for (var i=0; i<fieldsets.length; i++) {
			if (fieldsets[i].className.match(CollapsedFieldsets.collapsed_re)) {
				CollapsedFieldsets.display(i);
			}
		}
	}
}

addEvent(window, 'load', CollapsedFieldsets.init);
