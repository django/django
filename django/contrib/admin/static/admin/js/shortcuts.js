'use strict';
{
    const inputNonTextFieldTypes = ['submit', 'reset', 'checkbox', 'radio', 'file', 'button'];

    function isFocusedTextField() {
        const tag = document.activeElement.nodeName;
        const type = document.activeElement.type;
        const isContentEditable = document.activeElement.isContentEditable;
        return (
            tag === 'TEXTAREA' ||
            tag === 'SELECT' ||
            (tag === 'INPUT' && !inputNonTextFieldTypes.includes(type)) ||
            isContentEditable
        );
    }

    let previousKey = undefined;
    const shortcutFunctions = new Map();

    function registerDeclarativeShortcuts() {
        const elements = document.querySelectorAll('[aria-keyshortcuts]');
        for (const element of elements) {
            shortcutFunctions.set(element.getAttribute('aria-keyshortcuts'), () => {
                element.click();
            });
        }
    }

    function isApple() {
        return (navigator.platform.indexOf("Mac") === 0 || navigator.platform === "iPhone");
    }

    function removePreviousKey(key) {
        if (previousKey === key) {
            previousKey = undefined;
        }
    }

    function storePreviousKey(key) {
        previousKey = key;
        setTimeout(function() {
            removePreviousKey(key);
        }, 5000);
    }

    function showDialog(id) {
        const dialog = document.getElementById(id);
        dialog.showModal();
    }

    function showShortcutsDialog() {
        showDialog("shortcuts-dialog");
    }

    function showDialogOnClick() {
        const dialogButton = document.getElementById("open-shortcuts");
        if(!dialogButton) {
            return;
        }
        dialogButton.addEventListener("click", showShortcutsDialog);
    }

    function handleKeyDown(event) {
        // If we're in a focused text field, don't apply keyboard shortcuts
        if (isFocusedTextField()) {
            return;
        }

        // If there's a previous key, we first check whether the combination of the
        // previous key followed by the current key are a shortcut
        const shortcutWithPreviousKey = previousKey ? `${previousKey} ${event.key}` : null;
        if (shortcutWithPreviousKey && shortcutFunctions.has(shortcutWithPreviousKey)) {
            shortcutFunctions.get(shortcutWithPreviousKey)();
            return;
        }

        // Otherwise, check if the new key has a shortcut, e.g `?`
        if (shortcutFunctions.has(event.key)) {
            shortcutFunctions.get(event.key)();
            return;
        }

        // Simply store the key for the next keyDown
        storePreviousKey(event.key);

    }

    function replaceModifiers() {
        if (isApple()) {
            document.querySelectorAll(".shortcut-keys .alt").forEach(function(modifier) {
                modifier.innerHTML = "⌥";
            });
        }
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", showDialogOnClick);
        document.addEventListener("DOMContentLoaded", replaceModifiers);
        document.addEventListener("DOMContentLoaded", registerDeclarativeShortcuts);
    } else {
        showDialogOnClick();
        replaceModifiers();
        registerDeclarativeShortcuts();
    }
    document.addEventListener("keydown", handleKeyDown);
}
