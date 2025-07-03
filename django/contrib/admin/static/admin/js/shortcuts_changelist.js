'use strict';
{
    let checkboxes = null;
    let currentCheckbox = null;

    function setUpShortcuts() {
        checkboxes = Array.from(
            document.querySelectorAll("#action-toggle, .action-select")
        );
    }

    function focusPreviousCheckbox() {
        if (!checkboxes.length) {
            return;
        }
        if (!currentCheckbox || currentCheckbox === checkboxes[0]) {
            currentCheckbox = checkboxes[checkboxes.length - 1];
        } else {
            currentCheckbox = checkboxes[checkboxes.indexOf(currentCheckbox) - 1];
        }
        currentCheckbox.focus();
    }

    function focusNextCheckbox() {
        if (!checkboxes.length) {
            return;
        }
        if (!currentCheckbox || currentCheckbox === checkboxes[checkboxes.length - 1]) {
            currentCheckbox = checkboxes[0];
        } else {
            currentCheckbox = checkboxes[checkboxes.indexOf(currentCheckbox) + 1];
        }
        currentCheckbox.focus();
    }

    function selectCheckbox() {
        if (currentCheckbox) {
            currentCheckbox.click();
        }
    }

    function selectActionsSelect() {
        const actionsSelect = document.querySelector("select[name=action]");
        actionsSelect.focus();
    }

    function handleKeyDown(event) {
        if (window.advShortcutsEnabled === 'false') { return; }
        if (window.isFocusedTextField()) { return; }
        switch (event.code) {
        case "KeyK":
            focusPreviousCheckbox();
            break;
        case "KeyJ":
            focusNextCheckbox();
            break;
        case "KeyX":
            selectCheckbox();
            break;
        case "KeyA":
            selectActionsSelect();
            break;
        }
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", setUpShortcuts);
    } else {
        setUpShortcuts();
    }
    document.addEventListener("keydown", handleKeyDown);
}
