"use strict";
// Fallback JS for browsers which do not support :has selector used in
// admin/css/unusable_password_fields.css
// Remove file once all supported browsers support :has selector
try {
    // If browser does not support :has selector this will raise an error
    document.querySelector("form:has(input)");
} catch (error) {
    console.log("Defaulting to javascript for usable password form management: " + error);
    // JS replacement for unsupported :has selector
    document.querySelectorAll('input[name="usable_password"]').forEach(option => {
        option.addEventListener('change', function() {
            const usablePassword = (this.value === "true" ? this.checked : !this.checked);
            const submit1 = document.querySelector('input[type="submit"].set-password');
            const submit2 = document.querySelector('input[type="submit"].unset-password');
            const messages = document.querySelector('#id_unusable_warning');
            document.getElementById('id_password1').closest('.form-row').hidden = !usablePassword;
            document.getElementById('id_password2').closest('.form-row').hidden = !usablePassword;
            if (messages) {
                messages.hidden = usablePassword;
            }
            if (submit1 && submit2) {
                submit1.hidden = !usablePassword;
                submit2.hidden = usablePassword;
            }
        });
        option.dispatchEvent(new Event('change'));
    });
}
