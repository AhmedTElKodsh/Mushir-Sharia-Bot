/**
 * Render chat messages and status events into the DOM.
 * Relies on global `messages` (DOM element) and globals `appState`, `config`
 * defined in app.js.
 *
 * Typewriter effect (P2-S4):
 *   renderTypewriter(text, node) — renders text character-by-character
 *   via requestAnimationFrame at config.typewriterSpeed ms/char.
 *   abortTypewriter() — cancels active typewriter, renders remaining text.
 */

// ---- Shared helpers -------------------------------------------------------

/**
 * Detect Arabic-heavy text and apply RTL direction + font on the node.
 * @param {HTMLElement} node
 * @param {string} text
 * @returns {boolean} true if RTL was applied
 */
function _applyDirection(node, text) {
  var arabicChars = (text.match(/[\u0600-\u06ff]/g) || []).length;
  var ratio = arabicChars / Math.max(text.length, 1);
  if (ratio > 0.3) {
    node.setAttribute("dir", "rtl");
    node.style.textAlign = "right";
    node.style.fontFamily = "'Noto Sans Arabic', 'Segoe UI', sans-serif";
    return true;
  }
  return false;
}

// ---- Typewriter engine (P2-S4) --------------------------------------------

/**
 * @typedef {Object} TwState
 * @property {HTMLElement} node - The assistant message DOM element
 * @property {string} fullText - Complete answer text to render
 * @property {number} pos - Current character position (0..fullText.length)
 * @property {number|null} rafId - requestAnimationFrame ID
 * @property {boolean} done - true when all characters have been rendered
 * @property {number} lastTick - High-res timestamp of last character advance
 */

/** @type {TwState|null} */
var _twState = null;

/**
 * Abort any active typewriter and render remaining text instantly.
 * Safe to call when no typewriter is running.
 */
function abortTypewriter() {
  if (!_twState) return;
  if (_twState.rafId !== null) {
    cancelAnimationFrame(_twState.rafId);
    _twState.rafId = null;
  }
  _flushTypewriter();
  _twState = null;
}

/**
 * Render all remaining typewriter text instantly into the node.
 * Does NOT cancel the RAF — caller is responsible for that.
 */
function _flushTypewriter() {
  if (!_twState || _twState.done) return;
  _twState.node.textContent = _twState.fullText;
  _twState.done = true;
  messages.scrollTop = messages.scrollHeight;
}

/**
 * requestAnimationFrame callback.
 * Advances one character per `config.typewriterSpeed` milliseconds.
 * Checks `appState.streaming` — if false, flushes remaining text immediately.
 * @param {number} timestamp - DOMHighResTimeStamp from rAF
 */
function _twTick(timestamp) {
  if (!_twState || _twState.done) return;

  // Abort check: streaming was turned off (new submit or SSE done)
  if (typeof appState !== "undefined" && !appState.streaming) {
    if (_twState.pos < _twState.fullText.length) {
      _flushTypewriter();
    }
    _twState = null;
    return;
  }

  var s = _twState;
  if (!s.lastTick) s.lastTick = timestamp;

  var elapsed = timestamp - s.lastTick;
  var speed = (typeof config !== "undefined" && config.typewriterSpeed) || 25;

  if (elapsed >= speed) {
    s.pos++;
    s.lastTick = timestamp;
    s.node.textContent = s.fullText.slice(0, s.pos);
    // Keep the chat scrolled to the latest content
    messages.scrollTop = messages.scrollHeight;

    if (s.pos >= s.fullText.length) {
      s.done = true;
      _twState = null;
      return;
    }
  }

  s.rafId = requestAnimationFrame(_twTick);
}

/**
 * Render assistant answer text with a typewriter animation.
 *
 * - Buffers the full answer text
 * - Renders one character per `config.typewriterSpeed` ms via rAF
 * - Respects `prefers-reduced-motion`: renders full text instantly
 * - Aborts any previously running typewriter first
 *
 * @param {string} text - Full answer text to display
 * @param {HTMLElement} node - Assistant message DOM element (already appended)
 */
function renderTypewriter(text, node) {
  // Terminate any in-progress typewriter
  abortTypewriter();

  // Apply text direction based on content
  _applyDirection(node, text);

  // Accessibility: prefers-reduced-motion → instant render
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    node.textContent = text;
    messages.scrollTop = messages.scrollHeight;
    return;
  }

  // Initialise typewriter state
  _twState = {
    node: node,
    fullText: text,
    pos: 0,
    rafId: null,
    done: false,
    lastTick: 0
  };

  // Start the RAF loop
  _twState.rafId = requestAnimationFrame(_twTick);
}

// ---- Message rendering ----------------------------------------------------

/**
 * Add a message or event bubble to the chat container.
 * @param {string} kind - "user", "assistant", or "event"
 * @param {string} text - Message text content
 * @returns {HTMLElement} The created DOM node
 */
function addMessage(kind, text) {
  var node = document.createElement("div");
  node.className = kind === "event" ? "event" : "message " + kind;
  node.textContent = text;
  if (kind !== "event") {
    _applyDirection(node, text);
  }
  messages.appendChild(node);
  messages.scrollTop = messages.scrollHeight;
  return node;
}

/**
 * Add a status event message (loading, confidence, etc.).
 * @param {string} text - Event text content
 * @returns {HTMLElement} The created DOM node
 */
function addEvent(text) {
  return addMessage("event", text);
}
