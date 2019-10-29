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
        // Add toggle to hide/show anchor tag
        var toggleFunc = function(ev) {
            if (ev.target.matches('.collapse-toggle')) {
                ev.preventDefault();
                ev.stopPropagation();
                var fieldset = closestElem(ev.target, 'fieldset');
                if (fieldset.classList.contains('collapsed')) {
                    // Show
                    ev.target.textContent = gettext('Hide');
                    fieldset.classList.remove('collapsed');
                } else {
                    // Hide
                    ev.target.textContent = gettext('Show');
                    fieldset.classList.add('collapsed');
                }
            }
        };
        var inlineDivs = document.querySelectorAll('fieldset.module');
        for (i = 0; i < inlineDivs.length; i++) {
            inlineDivs[i].addEventListener('click', toggleFunc);
        }
    });
})();
