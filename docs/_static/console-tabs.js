import "https://esm.sh/@github/tab-container-element@4.9.0";

const STORAGE_KEY = "django.console-tabs.platform";
const TAB_INDEXES = {
    unix: 0,
    win: 1,
};
const TAB_NAMES = Object.keys(TAB_INDEXES);
const DEFAULT_TAB_NAME = TAB_NAMES[0];

let selectedTabName = readSavedTabName() || DEFAULT_TAB_NAME;

function isTabName(value) {
    return TAB_NAMES.includes(value);
}

function readSavedTabName() {
    try {
        const savedTabName = localStorage.getItem(STORAGE_KEY);
        return isTabName(savedTabName) ? savedTabName : null;
    } catch {
        return null;
    }
}

function saveTabName(tabName) {
    try {
        localStorage.setItem(STORAGE_KEY, tabName);
    } catch {
        // Ignore storage failures. The tabs still work for the current page.
    }
}

function createTab(radio, label, tabName) {
    const tab = document.createElement("button");
    tab.type = "button";
    tab.id = radio.id;
    tab.dataset.tabName = tabName;
    tab.setAttribute("role", "tab");
    const span = document.createElement("span");
    span.textContent = label.textContent.trim();
    tab.appendChild(span);

    if (tabName === selectedTabName) {
        tab.setAttribute("aria-selected", "true");
    } else {
        tab.tabIndex = -1;
    }

    return tab;
}

function createPanel(section, tab) {
    const panel = document.createElement("section");
    panel.setAttribute("role", "tabpanel");
    panel.setAttribute("aria-labelledby", tab.id);

    while (section.firstChild) {
        panel.appendChild(section.firstChild);
    }

    if (tab.getAttribute("aria-selected") !== "true") {
        panel.hidden = true;
    }

    return panel;
}

function convertConsoleBlock(consoleBlock) {
    const unixRadio = consoleBlock.querySelector(":scope > .c-tab-unix");
    const unixLabel =
        unixRadio &&
        consoleBlock.querySelector(
            `:scope > label[for="${CSS.escape(unixRadio.id)}"]`,
        );
    const unixSection = consoleBlock.querySelector(":scope > .c-content-unix");
    const winRadio = consoleBlock.querySelector(":scope > .c-tab-win");
    const winLabel =
        winRadio &&
        consoleBlock.querySelector(
            `:scope > label[for="${CSS.escape(winRadio.id)}"]`,
        );
    const winSection = consoleBlock.querySelector(":scope > .c-content-win");

    if (
        !unixRadio ||
        !unixLabel ||
        !unixSection ||
        !winRadio ||
        !winLabel ||
        !winSection
    ) {
        return null;
    }

    const tabContainer = document.createElement("tab-container");
    tabContainer.classList.add("console-block");
    const unixTab = createTab(unixRadio, unixLabel, "unix");
    const winTab = createTab(winRadio, winLabel, "win");

    tabContainer.appendChild(unixTab);
    tabContainer.appendChild(winTab);
    tabContainer.appendChild(createPanel(unixSection, unixTab));
    tabContainer.appendChild(createPanel(winSection, winTab));

    consoleBlock.replaceWith(tabContainer);
    return tabContainer;
}

let inSyncTabs = false;

function syncTabs(tabName, changedTabContainer = null) {
    if (!isTabName(tabName)) {
        return;
    }

    if (inSyncTabs) {
        return;
    }
    inSyncTabs = true;
    try {
        selectedTabName = tabName;
        const tabIndex = TAB_INDEXES[tabName];
        for (const tabContainer of document.querySelectorAll("tab-container")) {
            if (tabContainer !== changedTabContainer) {
                tabContainer.selectTab(tabIndex, { focus: false });
            }
        }
    } finally {
        inSyncTabs = false;
    }
}

function enhanceConsoleTabs() {
    for (const consoleBlock of document.querySelectorAll(".console-block")) {
        convertConsoleBlock(consoleBlock);
    }
    syncTabs(selectedTabName);
}

function restoreSavedTab() {
    const savedTabName = readSavedTabName();

    if (savedTabName && savedTabName !== selectedTabName) {
        syncTabs(savedTabName);
    }
}

async function init() {
    await customElements.whenDefined("tab-container");
    enhanceConsoleTabs();

    document.addEventListener("tab-container-changed", (event) => {
        const tabName = event.tab.dataset.tabName;
        if (!tabName) {
            return;
        }

        selectedTabName = tabName;
        saveTabName(tabName);
        syncTabs(tabName, event.target);
    });

    window.addEventListener("pageshow", restoreSavedTab);
    window.addEventListener("storage", (event) => {
        if (event.key === STORAGE_KEY && isTabName(event.newValue)) {
            syncTabs(event.newValue);
        }
    });
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
} else {
    void init();
}
