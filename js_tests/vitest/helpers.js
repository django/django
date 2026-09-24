/**
 * Helpers for running Django's classic (non-module) admin scripts under
 * Vitest browser mode.
 */

/**
 * Execute a classic script in the global scope.
 *
 * Vite serves every import as an ES module, so a plain `import` of core.js
 * would keep its top-level function declarations (quickElement, ...) scoped
 * to that module instead of exposing them on `window`, and jsi18n-mocks
 * relies on `this` being `window`. Injecting the source as an inline
 * <script> runs it exactly as js_tests/tests.html does. Inline scripts
 * execute synchronously on insertion, so globals are available as soon as
 * this function returns.
 */
export function loadClassicScript(source) {
    const script = document.createElement("script");
    script.textContent = source;
    document.head.appendChild(script);
    script.remove();
}

/** Resolve on the next macrotask, mirroring `setTimeout(fn)` in QUnit tests. */
export function nextTick() {
    return new Promise((resolve) => setTimeout(resolve));
}
