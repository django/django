import globals from "globals";
import pluginJs from "@eslint/js";

/** @type {import('eslint').Linter.Config[]} */
export default [
  // Include browser globals (e.g., window, document) and node globals if needed
  {
    languageOptions: {
      globals: {
        ...globals.browser, // Adds browser-specific globals like window, document
        django: "readonly", // Declares django as a global variable
        updateSelectFilter: "readonly", // Declares updateSelectFilter as a global variable
      },
    },
  },
  pluginJs.configs.recommended, // Use recommended JavaScript rules
];
