/*global gettext, interpolate, ngettext, Actions*/
'use strict';
{
    function show(selector) {
        document.querySelectorAll(selector).forEach(function(el) {
            el.classList.remove('hidden');
        });
    }

    function hide(selector) {
        document.querySelectorAll(selector).forEach(function(el) {
            el.classList.add('hidden');
        });
    }

    function showQuestion(options) {
        hide(options.acrossClears);
        show(options.acrossQuestions);
        hide(options.allContainer);
    }

    function showClear(options) {
        show(options.acrossClears);
        hide(options.acrossQuestions);
        document.querySelector(options.actionContainer).classList.remove(options.selectedClass);
        show(options.allContainer);
        hide(options.counterContainer);
    }

    function reset(options) {
        hide(options.acrossClears);
        hide(options.acrossQuestions);
        hide(options.allContainer);
        show(options.counterContainer);
    }

    function clearAcross(options) {
        reset(options);
        const acrossInputs = document.querySelectorAll(options.acrossInput);
        acrossInputs.forEach(function(acrossInput) {
            acrossInput.value = 0;
        });
        document.querySelector(options.actionContainer).classList.remove(options.selectedClass);
    }

    function checker(actionCheckboxes, options, checked) {
        if (checked) {
            showQuestion(options);
        } else {
            reset(options);
        }
        actionCheckboxes.forEach(function(el) {
            el.checked = checked;
            el.closest('tr').classList.toggle(options.selectedClass, checked);
        });
    }

    function updateCounter(actionCheckboxes, options) {
        const sel = Array.from(actionCheckboxes).filter(function(el) {
            return el.checked;
        }).length;
        const counter = document.querySelector(options.counterContainer);
        // data-actions-icnt is defined in the generated HTML
        // and contains the total amount of objects in the queryset
        const actions_icnt = Number(counter.dataset.actionsIcnt);
        counter.textContent = interpolate(
            ngettext('%(sel)s of %(cnt)s selected', '%(sel)s of %(cnt)s selected', sel), {
                sel: sel,
                cnt: actions_icnt
            }, true);
        const allToggle = document.getElementById(options.allToggleId);
        allToggle.checked = sel === actionCheckboxes.length;
        if (allToggle.checked) {
            showQuestion(options);
        } else {
            clearAcross(options);
        }
    }

    const defaults = {
        actionContainer: "div.actions",
        counterContainer: "span.action-counter",
        allContainer: "div.actions span.all",
        acrossInput: "div.actions input.select-across",
        acrossQuestions: "div.actions span.question",
        acrossClears: "div.actions span.clear",
        allToggleId: "action-toggle",
        selectedClass: "selected",
        inline: false,
    };

    window.Actions = function(actionCheckboxes, options) {
        options = Object.assign({}, defaults, options);
        let list_editable_changed = false;
        let lastChecked = null;
        let shiftPressed = false;

        document.addEventListener('keydown', (event) => {
            shiftPressed = event.shiftKey;
        });

        document.addEventListener('keyup', (event) => {
            shiftPressed = event.shiftKey;
        });

        function affectedCheckboxes(target, withModifier) {
            const multiSelect = (lastChecked && withModifier && lastChecked !== target);
            if (!multiSelect) {
                return [target];
            }
            const checkboxes = Array.from(actionCheckboxes);
            const targetIndex = checkboxes.findIndex(el => el === target);
            const lastCheckedIndex = checkboxes.findIndex(el => el === lastChecked);
            const startIndex = Math.min(targetIndex, lastCheckedIndex);
            const endIndex = Math.max(targetIndex, lastCheckedIndex);
            return checkboxes.filter((el, index) => (startIndex <= index) && (index <= endIndex));
        }

        if (!options.inline) {
            document.querySelectorAll(options.acrossQuestions + " a").forEach(function(el) {
                el.addEventListener('click', function(event) {
                    event.preventDefault();
                    const acrossInputs = document.querySelectorAll(options.acrossInput);
                    acrossInputs.forEach(function(acrossInput) {
                        acrossInput.value = 1;
                    });
                    showClear(options);
                });
            });
            document.querySelectorAll(options.acrossClears + " a").forEach(function(el) {
                el.addEventListener('click', function(event) {
                    event.preventDefault();
                    document.getElementById(options.allToggleId).checked = false;
                    clearAcross(options);
                    checker(actionCheckboxes, options, false);
                    updateCounter(actionCheckboxes, options);
                });
            });
            document.getElementById(options.allToggleId).addEventListener('click', function(event) {
                checker(actionCheckboxes, options, this.checked);
                updateCounter(actionCheckboxes, options);
            });

            Array.from(document.getElementById('result_list').tBodies).forEach(
                function(el) {
                    el.addEventListener('change', function(event) {
                        const target = event.target;
                        if (target.classList.contains('action-select')) {
                            const checkboxes = affectedCheckboxes(target, shiftPressed);
                            checker(checkboxes, options, target.checked);
                            updateCounter(actionCheckboxes, options);
                            lastChecked = target;
                        } else {
                            list_editable_changed = true;
                        }
                    });
                });

            document.querySelector('#changelist-form button[name=index]').addEventListener('click', function(event) {
                if (list_editable_changed) {
                    const confirmed = confirm(gettext("You have unsaved changes on individual editable fields. If you run an action, your unsaved changes will be lost."));
                    if (!confirmed) {
                        event.preventDefault();
                    }
                }
            });
            // Sync counter when navigating to the page, such as through the back
            // button.
            window.addEventListener('pageshow', (event) => updateCounter(actionCheckboxes, options));
        } else if (options.inline) {
            const handleCheckboxChange = (event) => {
                const target = event.target;

                if (!lastChecked || !target.name.endsWith('-DELETE')) {
                    lastChecked = target;
                    return;
                }

                if (lastChecked.name.slice(0, -9) === target.name.slice(0, -9)) {
                    // Checking for if clicked checkboxes are in the same form with forms common prefix.
                    const checkboxes = affectedCheckboxes(target, shiftPressed);
                    checker(checkboxes, options, target.checked);
                }

                lastChecked = target;
            };

            const attachChangeListener = (element) => {
                if (!element) {
                    return;
                }
                element.addEventListener('change', handleCheckboxChange);
            };

            // Handle tabular inline tables
            document.querySelectorAll('.tabular tbody').forEach(attachChangeListener);

            // Handle stacked inlines
            document.querySelectorAll('.inline-related').forEach(attachChangeListener);
        }

        const el = document.querySelector('#changelist-form input[name=_save]');
        // The button does not exist if no fields are editable.
        if (el) {
            el.addEventListener('click', function(event) {
                if (document.querySelector('[name=action]').value) {
                    const text = list_editable_changed
                        ? gettext("You have selected an action, but you haven’t saved your changes to individual fields yet. Please click OK to save. You’ll need to re-run the action.")
                        : gettext("You have selected an action, and you haven’t made any changes on individual fields. You’re probably looking for the Go button rather than the Save button.");
                    if (!confirm(text)) {
                        event.preventDefault();
                    }
                }
            });
        }
    };

    // Call function fn when the DOM is loaded and ready. If it is already
    // loaded, call the function now.
    // http://youmightnotneedjquery.com/#ready
    function ready(fn) {
        if (document.readyState !== 'loading') {
            fn();
        } else {
            document.addEventListener('DOMContentLoaded', fn);
        }
    }

    ready(function() {
        const actionsEls = document.querySelectorAll('tr input.action-select');
        if (actionsEls.length > 0) {
            Actions(actionsEls);
        }
        const tabularActionsEls = document.querySelectorAll(
            'td.delete input[type="checkbox"]');
        if (tabularActionsEls.length > 0) {
            defaults.inline = true;
            Actions(tabularActionsEls);
        }
        const stackedActionsEls = document.querySelectorAll('span.delete input[type="checkbox"]');
        if (stackedActionsEls.length > 0) {
            defaults.inline = true;
            Actions(stackedActionsEls);
        }
    });
}
