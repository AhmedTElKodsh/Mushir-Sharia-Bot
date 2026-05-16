/**
 * Keyboard shortcuts and keybindings.
 *
 * Shortcuts.init()  — bind keydown listener on document
 * Shortcuts.destroy() — unbind listener
 *
 * Binds:
 *   Ctrl/Cmd+Enter   Submit the chat form (send message)
 *   /                Focus prompt input (when not already focused)
 *   Escape           Blur input; closes citation flyout if open
 *
 * Guards:
 *   No shortcuts fire while a <dialog> is open.
 *   When the flyout is open (body.flyout-open) only Escape works.
 *   When the input is focused, only Ctrl+Enter and Escape fire.
 *   The "/" key is ignored when input is already focused.
 */

var Shortcuts = Shortcuts || {};

(function () {
  /** @type {function(Event):void|null} */
  var _handler = null;

  // ---- helpers -----------------------------------------------------------

  /**
   * Check whether a native <dialog> is currently open.
   * @returns {boolean}
   */
  function _isDialogOpen() {
    return document.querySelector("dialog[open]") !== null;
  }

  /**
   * Check whether the citation flyout is open (class on <body>).
   * @returns {boolean}
   */
  function _isFlyoutOpen() {
    return document.body.classList.contains("flyout-open");
  }

  // ---- keydown handler ---------------------------------------------------

  /**
   * Handle keydown events.
   * @param {KeyboardEvent} event
   */
  function _onKeyDown(event) {
    var input = /** @type {HTMLTextAreaElement|null} */ (
      document.getElementById("prompt")
    );
    if (!input) return;

    var ctrlEnter =
      (event.ctrlKey || event.metaKey) && event.key === "Enter";
    var isEscape = event.key === "Escape";
    var isSlash =
      event.key === "/" && !event.ctrlKey && !event.metaKey && !event.altKey;

    // ---- Guards -----------------------------------------------------------

    // 1. Native <dialog> open → block ALL shortcuts
    if (_isDialogOpen()) return;

    // 2. Citation flyout open → only Escape may close it
    if (_isFlyoutOpen()) {
      if (isEscape) {
        document.body.classList.remove("flyout-open");
        if (input) input.blur();
        event.preventDefault();
      }
      return; // block everything else while flyout is open
    }

    // 3. Input is focused → only Ctrl+Enter and Escape fire
    if (document.activeElement === input) {
      if (ctrlEnter) {
        event.preventDefault();
        _submitForm();
        return;
      }
      if (isEscape) {
        input.blur();
        event.preventDefault();
        return;
      }
      return; // swallow other shortcuts when typing
    }

    // ---- Input NOT focused ------------------------------------------------

    // Ctrl+Enter — send message (also works from outside the input)
    if (ctrlEnter) {
      event.preventDefault();
      _submitForm();
      return;
    }

    // "/" — focus input
    if (isSlash) {
      event.preventDefault();
      input.focus();
      return;
    }
  }

  /**
   * Programmatically submit the chat form.
   */
  function _submitForm() {
    var form = document.getElementById("chat-form");
    if (form) {
      form.dispatchEvent(new Event("submit"));
    }
  }

  // ---- public API --------------------------------------------------------

  /**
   * Bind keyboard shortcuts.
   * Safe to call multiple times — subsequent calls are no-ops.
   */
  Shortcuts.init = function () {
    if (_handler) return; // already initialised
    _handler = _onKeyDown;
    document.addEventListener("keydown", _handler);
  };

  /**
   * Unbind keyboard shortcuts.
   */
  Shortcuts.destroy = function () {
    if (_handler) {
      document.removeEventListener("keydown", _handler);
      _handler = null;
    }
  };
})();
