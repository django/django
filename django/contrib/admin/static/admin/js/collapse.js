/*global gettext*/
(function() {
    'use strict';
    var closestElem = function(elem, tagName) {
        if (elem.nodeName === tagName.toUpperCase()) {
            return elem;
        }
        if (elem.parentNode.nodeName === 'BODY') {
            return null;
        }
        return elem.parentNode && closestElem(elem.parentNode, tagName);
    };

    window.addEventListener('load', function() {
        // Add anchor tag for Show/Hide link
        var fieldsets = document.querySelectorAll('fieldset.collapse');
        for (var i = 0; i < fieldsets.length; i++) {
            var elem = fieldsets[i];
            // Don't hide if fields in this fieldset have errors
            if (elem.querySelectorAll('div.errors').length === 0) {
                elem.classList.add('collapsed');
                var h2 = elem.querySelector('h2');
                var link = document.createElement('a');
                link.setAttribute('id', 'fieldsetcollapser' + i);
                link.setAttribute('class', 'collapse-toggle');
                link.setAttribute('href', '#');
                link.textContent = gettext('Show');
                h2.appendChild(document.createTextNode(' ('));
                h2.appendChild(link);
                h2.appendChild(document.createTextNode(')'));
            }
        }
        // Add toggle to anchor tag
        var toggles = document.querySelectorAll('fieldset.collapse a.collapse-toggle');
        var toggleFunc = function(ev) {
            ev.preventDefault();
            var fieldset = closestElem(this, 'fieldset');
            if (fieldset.classList.contains('collapsed')) {
                // Show
                this.textContent = gettext('Hide');
                fieldset.classList.remove('collapsed');
            } else {
                // Hide
                this.textContent = gettext('Show');
                fieldset.classList.add('collapsed');
            }
        };
        for (i = 0; i < toggles.length; i++) {
            toggles[i].addEventListener('click', toggleFunc);
        }
    });
})();
