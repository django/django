'use strict';
{
    const inputTags = ['BUTTON', 'INPUT', 'SELECT', 'TEXTAREA'];
    const modelName = document.getElementById('django-admin-form-add-constants').dataset.modelName;
    if (modelName) {
        const form = document.getElementById(modelName + '_form');
        for (const element of form.elements) {
            // HTMLElement.offsetParent returns null when the element is not
            // rendered.
            if (inputTags.includes(element.tagName) && !element.disabled && element.offsetParent) {
                element.focus();
                break;
            }
        }
    }
    // Close collapsibles that don't have the "open" class
    // This is done after autocomplete initialization to prevent width calculation issues (#36336)
    document.querySelectorAll('fieldset.module.collapse:not(.open) details[open]').forEach(details => {
        details.removeAttribute('open');
    });
}
