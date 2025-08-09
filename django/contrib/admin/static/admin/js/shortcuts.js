'use strict';
{
    /**
     * Django Admin Keyboard Shortcuts
     * Provides keyboard shortcuts for common admin form actions
     */
    const DjangoAdminShortcuts = {
        // Selector constants for form buttons
        SELECTORS: {
            CONTINUE: 'input[name="_continue"]',
            SAVE: 'input[name="_save"]',
            ADD_ANOTHER: 'input[name="_addanother"]'
        },

        // Platform detection
        isMac: navigator.platform.toUpperCase().indexOf('MAC') >= 0,

        /**
         * Initialize the shortcuts system
         */
        init() {
            this.setupButtonHints();
            this.setupKeyboardListeners();
        },

        /**
         * Add tooltip hints to buttons showing available shortcuts
         */
        setupButtonHints() {
            const modifierKey = this.isMac ? 'Command' : 'Ctrl';

            const shortcuts = [
                { selector: this.SELECTORS.CONTINUE, hint: `${modifierKey} + S` },
                { selector: this.SELECTORS.SAVE, hint: `${modifierKey} + Shift + S` },
                { selector: this.SELECTORS.ADD_ANOTHER, hint: `${modifierKey} + Alt + S` }
            ];

            shortcuts.forEach(shortcut => {
                this.setButtonHint(shortcut.selector, shortcut.hint);
            });
        },

        /**
         * Set tooltip hint on a button element
         * @param {string} selector - CSS selector for the button
         * @param {string} hint - Tooltip text to display
         */
        setButtonHint(selector, hint) {
            const button = document.querySelector(selector);
            if (button) {
                const existingTitle = button.getAttribute('title');
                const newTitle = existingTitle ? `${existingTitle} (${hint})` : hint;
                button.setAttribute('title', newTitle);
            }
        },

        /**
         * Setup keyboard event listeners for shortcuts
         */
        setupKeyboardListeners() {
            document.addEventListener('keydown', (event) => {
                this.handleKeyboardEvent(event);
            });
        },

        /**
         * Handle keyboard events and trigger appropriate actions
         * @param {KeyboardEvent} event - The keyboard event
         */
        handleKeyboardEvent(event) {
            // Only handle Ctrl/Cmd key combinations
            if (!(event.ctrlKey || event.metaKey)) {
                return;
            }

            // Only handle 's' key
            if (event.key !== 's') {
                return;
            }

            // Prevent conflicts with browser shortcuts in input fields
            if (this.isEditableElement(event.target)) {
                return;
            }

            // Determine which action to take based on modifier keys
            let targetSelector = null;

            if (!event.shiftKey && !event.altKey) {
                // Ctrl/Cmd + S: Save and continue editing
                targetSelector = this.SELECTORS.CONTINUE;
            } else if (event.shiftKey && !event.altKey) {
                // Ctrl/Cmd + Shift + S: Save and exit
                targetSelector = this.SELECTORS.SAVE;
            } else if (!event.shiftKey && event.altKey) {
                // Ctrl/Cmd + Alt + S: Save and add another
                targetSelector = this.SELECTORS.ADD_ANOTHER;
            }

            if (targetSelector && this.clickIfExists(targetSelector)) {
                event.preventDefault();
            }
        },

        /**
         * Check if an element is editable (input, textarea, contenteditable)
         * @param {Element} element - The element to check
         * @returns {boolean} True if the element is editable
         */
        isEditableElement(element) {
            if (!element) {
                return false;
            }

            const tagName = element.tagName.toLowerCase();
            const editableTags = ['input', 'textarea', 'select'];

            return editableTags.includes(tagName) ||
                   element.contentEditable === 'true' ||
                   element.isContentEditable;
        },

        /**
         * Click a button if it exists and is visible
         * @param {string} selector - CSS selector for the button
         * @returns {boolean} True if button was found and clicked
         */
        clickIfExists(selector) {
            const button = document.querySelector(selector);
            if (button && this.isElementVisible(button) && !button.disabled) {
                button.click();
                return true;
            }
            return false;
        },

        /**
         * Check if an element is visible to the user
         * @param {Element} element - The element to check
         * @returns {boolean} True if the element is visible
         */
        isElementVisible(element) {
            return element.offsetParent !== null &&
                   getComputedStyle(element).display !== 'none' &&
                   getComputedStyle(element).visibility !== 'hidden';
        }
    };

    // Initialize shortcuts when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            DjangoAdminShortcuts.init();
        });
    } else {
        DjangoAdminShortcuts.init();
    }

    // Export for testing purposes (if needed)
    if (typeof window !== 'undefined') {
        window.DjangoAdminShortcuts = DjangoAdminShortcuts;
    }
}
