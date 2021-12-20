'use strict';
{
    const inputTags = ['BUTTON', 'INPUT', 'SELECT', 'TEXTAREA'];
    const modelName = document.getElementById('django-admin-form-add-constants').dataset.modelName;
    const submitButtons = document.querySelectorAll('input[type=submit]');

    if (modelName) {
        const form = document.getElementById(modelName + '_form');

        form.addEventListener('submit', function(event) {
            event.preventDefault();
            submitButtons.forEach(button => {
                button.setAttribute('disabled', true);
            });
            event.target.submit();
        });

        for (const element of form.elements) {
            // HTMLElement.offsetParent returns null when the element is not
            // rendered.
            if (inputTags.includes(element.tagName) && !element.disabled && element.offsetParent) {
                element.focus();
                break;
            }
        }
    }
}
