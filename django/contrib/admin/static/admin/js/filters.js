/**
 * Expand/collapse change list filters
 * Filter with choices > CHOICES_EXPANDED_LIMIT are automatically collapsed
 */
'use strict';
{
    function ready(fn) {
        if (document.readyState !== 'loading') {
            fn();
        } else {
            document.addEventListener('DOMContentLoaded', fn);
        }
    }

    ready(function() {
        const CHOICES_EXPANDED_LIMIT = 10;
        const filters = document.querySelectorAll('[data-toggle]');
        const hide = function(element) {
            element.classList.add('hidden');
        };
        const toggle = function(element) {
            element.classList.toggle('hidden');
        };

        filters.forEach(function(filter) {
            const field = filter.dataset.toggle;
            const target = `[data-target=${field}]`;
            const expanded = document.querySelector(`[data-expanded=${field}]`); // - symbol
            const collapsed = document.querySelector(`[data-collapsed=${field}]`); // + symbol
            const collapsable = document.querySelector(target); // target to be collapsed
            const choices = collapsable.querySelectorAll(`li`);

            if (choices.length > CHOICES_EXPANDED_LIMIT) {
                hide(expanded);
                hide(collapsable);
            } else {
                hide(collapsed);
            }

            filter.addEventListener('click', function() {
                toggle(collapsed);
                toggle(expanded);
                toggle(collapsable);
            });
        });
    });
}