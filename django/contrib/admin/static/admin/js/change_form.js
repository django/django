'use strict';
{
    const inputTags = ['BUTTON', 'INPUT', 'SELECT', 'TEXTAREA'];
    const modelName = document.getElementById('django-admin-form-add-constants').dataset.modelName;
    if (modelName) {
        const form = document.getElementById(modelName + '_form');
        for (let i = 0; i < form.elements.length; i++) {
            const element = form.elements[i];
            // HTMLElement.offsetParent returns null when the element is not
            // rendered.
            if (inputTags.includes(element.tagName) && !element.disabled && element.offsetParent) {
                element.focus();
                break;
            }
        }
    }
}
