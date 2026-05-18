'use strict';
{
    let saveButton = null;
    let saveAndAddButton = null;
    let saveAndContinueButton = null;
    let deleteButton = null;

    function setUpShortcuts() {
        saveButton = document.querySelector("input[name=_save]");
        saveAndAddButton = document.querySelector("input[name=_addanother]");
        saveAndContinueButton = document.querySelector("input[name=_continue]");
        deleteButton = document.querySelector(".deletelink");
    }

    function handleKeyDown(event) {
        switch (event.code) {
        case "KeyS":
            if (event.altKey) {
                saveButton.click();
            }
            break;
        case "KeyA":
            if (event.altKey) {
                saveAndAddButton.click();
            }
            break;
        case "KeyC":
            if (event.altKey) {
                saveAndContinueButton.click();
            }
            break;
        case "KeyD":
            if (event.altKey) {
                deleteButton.click();
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
