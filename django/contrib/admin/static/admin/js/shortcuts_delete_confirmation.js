'use strict';
{
    let confirmButton = null;
    let cancelButton = null;

    function setUpShortcuts() {
        confirmButton = document.querySelector("#content input[type=submit]");
        cancelButton = document.querySelector(".cancel-link");
    }

    function confirmDeletion() {
        confirmButton.click();
    }

    function cancelDeletion() {
        cancelButton.click();
    }

    function handleKeyDown(event) {
        switch (event.code) {
        case "KeyY":
            if (event.altKey) {
                confirmDeletion();
            }
            break;
        case "KeyN":
            if (event.altKey) {
                cancelDeletion();
            }
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
