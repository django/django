'use strict';
{
    window.addEventListener('load', function(e) {

        function setTheme(mode) {
            if (mode !== "light" && mode !== "dark" && mode !== "auto") {
                console.error(`Got invalid theme mode: ${mode}. Resetting to auto.`);
                mode = "auto";
            }
            document.documentElement.dataset.theme = mode;
            localStorage.setItem("theme", mode);
        }

        function cycleTheme() {
            const currentTheme = localStorage.getItem("theme") || "auto";
            const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;

            if (prefersDark) {
                // Auto (dark) -> Light -> Dark
                if (currentTheme === "auto") {
                    setTheme("light");
                } else if (currentTheme === "light") {
                    setTheme("dark");
                } else {
                    setTheme("auto");
                }
            } else {
                // Auto (light) -> Dark -> Light
                if (currentTheme === "auto") {
                    setTheme("dark");
                } else if (currentTheme === "dark") {
                    setTheme("light");
                } else {
                    setTheme("auto");
                }
            }
        }

        function initTheme() {
            // set theme defined in localStorage if there is one, or fallback to auto mode
            const currentTheme = localStorage.getItem("theme");
            currentTheme ? setTheme(currentTheme) : setTheme("auto");
        }

        function setupTheme() {
            // Attach event handlers for toggling themes
            const buttons = document.getElementsByClassName("theme-toggle");
            Array.from(buttons).forEach((btn) => {
                btn.addEventListener("click", cycleTheme);
            });
            initTheme();
        }

        setupTheme();
    });
}
