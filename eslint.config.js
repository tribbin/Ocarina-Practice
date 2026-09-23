// Flat eslint config (no package.json in this repo — scripts stay classic
// globals on purpose, so there is intentionally NO no-undef: every file
// shares top-level bindings through the global scope by design). First
// flight rule set: hard-error rules only for defects that are definitely
// bugs; no-unused-vars starts at warn (various intentionally-unused positional
// args and caught errors live in the codebase) — tighten to error once CI
// prints its first counts.
module.exports = [
  {
    files: ["js/**/*.js", "tests/**/*.js"],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "script",
      globals: {
        window: "readonly",
        document: "readonly",
        navigator: "readonly",
        location: "readonly",
        history: "readonly",
        localStorage: "readonly",
        sessionStorage: "readonly",
        console: "readonly",
        fetch: "readonly",
        Promise: "readonly",
        URL: "readonly",
        URLSearchParams: "readonly",
        Blob: "readonly",
        Event: "readonly",
        CustomEvent: "readonly",
        KeyboardEvent: "readonly",
        MouseEvent: "readonly",
        AudioContext: "readonly",
        webkitAudioContext: "readonly",
        AudioParam: "readonly",
        MutationObserver: "readonly",
        ResizeObserver: "readonly",
        IntersectionObserver: "readonly",
        requestAnimationFrame: "readonly",
        cancelAnimationFrame: "readonly",
        setTimeout: "readonly",
        setInterval: "readonly",
        clearTimeout: "readonly",
        clearInterval: "readonly",
        alert: "readonly",
        confirm: "readonly",
        prompt: "readonly",
        RegExp: "readonly",
        Float32Array: "readonly",
        getComputedStyle: "readonly",
        matchMedia: "readonly"
      }
    },
    rules: {
      // defect class: real bugs, safe to error on first flight
      "no-const-assign": "error",
      "no-dupe-args": "error",
      "no-dupe-keys": "error",
      "no-ex-assign": "error",
      "no-func-assign": "error",
      "no-async-promise-executor": "error",
      "no-compare-neg-zero": "error",
      "no-loss-of-precision": "error",
      "no-self-assign": "error",
      "no-unsafe-negation": "error",
      "no-unsafe-optional-chaining": "error",
      "no-unreachable": "error",
      "no-useless-catch": "error",
      "no-fallthrough": "error",
      "no-template-curly-in-string": "error",
      "no-prototype-builtins": "error",
      // hygiene: surfaces counts in the CI log without failing the run
      "no-unused-vars": ["warn", { args: "none", caughtErrors: "none" }]
    }
  }
];
