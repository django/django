'use strict';

(function() {
    // Buttons for actions
    const saveButton = document.querySelector("input[name=_save]");
    const saveAndAddButton = document.querySelector("input[name=_addanother]");
    const saveAndContinueButton = document.querySelector("input[name=_continue]");
    const deleteButton = document.querySelector(".deletelink");
    const addLink = document.querySelector('a.addlink');

    // Handle keypress events
    function handleKeyDown(event) {
        if (isTyping()) {return;}

        const key = event.key.toLowerCase();

        // Check for ALT key combinations
        if (event.altKey) {
            switch (key) {
            case "s":
                saveButton && saveButton.click();
                break;
            case "a":
                saveAndAddButton && saveAndAddButton.click();
                break;
            case "c":
                saveAndContinueButton && saveAndContinueButton.click();
                break;
            case "d":
                deleteButton && deleteButton.click();
                break;
            case "n":
                addLink && addLink.click();
            }
        }
    }

    // Check if user is typing (input or textarea)
    function isTyping() {
        const activeElement = document.activeElement;
        return activeElement.tagName === "INPUT" || activeElement.tagName === "TEXTAREA";
    }

    // Handle Ctrl+K to focus the existing search bar
    function handleCtrlK(event) {
        if (event.ctrlKey && event.key.toLowerCase() === "k") {
            event.preventDefault();

            // Find the search input field in the admin panel
            const searchInput = document.querySelector('input[name="q"]');
            if (searchInput) {
                searchInput.focus(); // Focus on the search input field
            }
        }
    }
    // Handle '?' key to show the shortcuts panel
    function handleQuestionMark(event) {

        const shortcutsPanel = document.getElementById("shortcuts-panel");
        if (event.key === "?") {
            event.preventDefault(); // Prevent default action
    
            // Show the shortcuts panel
            if (shortcutsPanel) {
                shortcutsPanel.style.display = 'block'; // Show the modal
            }
        }
    
        // Close the modal when Escape key is pressed
        if (event.key === "Escape" && shortcutsPanel) {
            shortcutsPanel.style.display = "none"; // Hide the modal
        }
    }
    


    // Wait for DOM to be ready before attaching event listeners
    document.addEventListener("DOMContentLoaded", function() {
        // Add event listener for Ctrl + K to focus the existing search bar
        document.addEventListener("keydown", handleCtrlK);
        document.addEventListener("keydown", handleQuestionMark);
    });

    // Handle general keypresses (for other shortcuts)
    document.addEventListener("keydown", handleKeyDown);
})();
