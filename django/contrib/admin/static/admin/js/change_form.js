'use strict';
{
    const inputTags = ['BUTTON', 'INPUT', 'SELECT', 'TEXTAREA'];
    const modelName = document.getElementById('django-admin-form-add-constants').dataset.modelName;
    const buttons = document.querySelectorAll('input[type=submit]');
    const disableSubmitButtons = () => {
        buttons.forEach(button => {
            button.setAttribute('disabled', true);
        });
    };
    const enableSubmitButtons = () => {
        buttons.forEach(button => {
            button.removeAttribute('disabled');
        });
    };

    // Enable buttons when browser displays the page
    // In case the user is navigating forward
    // and backward through history
    window.addEventListener('pageshow', () => {
        enableSubmitButtons();
    });

    if (modelName) {
        const form = document.getElementById(modelName + '_form');

        // Disable buttons during submit to avoid multiple submissions
        form.addEventListener('submit', (event) => {
            event.preventDefault();
            disableSubmitButtons();
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
