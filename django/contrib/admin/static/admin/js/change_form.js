(function() {
    'use strict';
    var inputTags = ['BUTTON', 'INPUT', 'SELECT', 'TEXTAREA'];
    var modelName = document.getElementById('django-admin-form-add-constants').dataset.modelName;
    if (modelName) {
        var form = document.getElementById(modelName + '_form');
        for (var i = 0; i < form.elements.length; i++) {
            var element = form.elements[i];
            // HTMLElement.offsetParent returns null when the element is not
            // rendered.
            if (inputTags.includes(element.tagName) && !element.disabled && element.offsetParent) {
                element.focus();
                break;
            }
        }
    }
})();
