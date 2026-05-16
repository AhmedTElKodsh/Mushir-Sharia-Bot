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
  _twState.node.classList.remove("typewriter-active");
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
      s.node.classList.remove("typewriter-active");
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

  // Add cursor class for blinking indicator during animation
  node.classList.add("typewriter-active");

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

/**
 * Render a compliance status badge as a pill before answer text.
 * @param {string} status - COMPLIANT | NON_COMPLIANT | PARTIALLY_COMPLIANT | INSUFFICIENT_DATA
 * @returns {HTMLElement|null} The badge element, or null if status is unknown
 */
function renderBadge(status) {
  var VALID = {COMPLIANT:1, NON_COMPLIANT:1, PARTIALLY_COMPLIANT:1, INSUFFICIENT_DATA:1};
  if (!VALID[status]) return null;

  var normalized = status.toLowerCase().replace(/_/g, "-");
  var labels = {
    COMPLIANT:           "Compliant",
    NON_COMPLIANT:       "Non-Compliant",
    PARTIALLY_COMPLIANT: "Partially Compliant",
    INSUFFICIENT_DATA:   "Insufficient Data"
  };

  /* Remove any existing badge (from a prior started/retrieval event) */
  var existing = messages.querySelector(".badge");
  if (existing) existing.remove();

  var badge  = document.createElement("div");
  badge.className = "badge " + normalized;
  badge.setAttribute("data-status", normalized);
  badge.setAttribute("role", "status");
  badge.setAttribute("aria-label", "Compliance status: " + (labels[status] || status));

  /* Icon */
  var icon = document.createElement("span");
  icon.className = "badge-icon";
  icon.setAttribute("aria-hidden", "true");

  switch (status) {
    case "COMPLIANT":
      icon.innerHTML = '<svg width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M2 6L5 9L10 3" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>';
      break;
    case "NON_COMPLIANT":
      icon.innerHTML = '<svg width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M3 3L9 9M9 3L3 9" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>';
      break;
    case "PARTIALLY_COMPLIANT":
      icon.innerHTML = '<svg width="12" height="12" viewBox="0 0 12 12" fill="none"><circle cx="6" cy="6" r="5" stroke="currentColor" stroke-width="1.5"/><path d="M6 1a5 5 0 010 10V1z" fill="currentColor" opacity="0.4"/></svg>';
      break;
    case "INSUFFICIENT_DATA":
      icon.innerHTML = '<svg width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M3 6h6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>';
      break;
  }
  badge.appendChild(icon);

  /* Label */
  var label = document.createElement("span");
  label.textContent = labels[status] || status;
  badge.appendChild(label);

  messages.appendChild(badge);
  messages.scrollTop = messages.scrollHeight;
  return badge;
}

// ---- Typing indicator & Error bubble (P2-S1) -------------------------------

/**
 * Reference to the current typing-indicator node (set by renderTypingIndicator,
 * cleared by removeTypingIndicator). Used to track whether the placeholder
 * should be replaced by the first token.
 * @type {HTMLElement|null}
 */
var typingNode = null;

/**
 * Render a typing indicator inside an assistant bubble placeholder.
 * Shows three animated dots by default.
 * Respects `prefers-reduced-motion`: shows static "Mushir is composing..." text.
 * @returns {HTMLElement} The created DOM node
 */
function renderTypingIndicator() {
  var node = document.createElement("div");
  node.className = "message assistant";

  var indicator = document.createElement("span");
  indicator.className = "typing-indicator";
  for (var i = 0; i < 3; i++) {
    var dot = document.createElement("span");
    dot.className = "dot";
    indicator.appendChild(dot);
  }

  // prefers-reduced-motion: CSS hides dots and shows static text
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    indicator.classList.add("static-text");
  }

  node.appendChild(indicator);
  messages.appendChild(node);
  messages.scrollTop = messages.scrollHeight;
  typingNode = node;
  return node;
}

/**
 * Remove the typing indicator placeholder from the DOM.
 * Safe to call when no typing indicator is showing.
 */
function removeTypingIndicator() {
  if (typingNode) {
    typingNode.remove();
    typingNode = null;
  }
}

/**
 * Render an error bubble with a red border, error icon, message, and "Retry" button.
 * Removes the typing indicator if it is still present.
 * @param {string} message - Error description from the SSE error event
 * @returns {HTMLElement} The created DOM node
 */
function renderErrorBubble(message) {
  // Remove typing indicator if it's still showing
  removeTypingIndicator();

  var node = document.createElement("div");
  node.className = "error-bubble";

  var header = document.createElement("div");
  header.className = "error-header";

  var icon = document.createElement("span");
  icon.className = "error-icon";
  icon.textContent = "!";
  header.appendChild(icon);

  var title = document.createElement("span");
  title.textContent = "Error";
  header.appendChild(title);

  node.appendChild(header);

  var msg = document.createElement("div");
  msg.className = "error-message";
  msg.textContent = message;
  node.appendChild(msg);

  var retry = document.createElement("button");
  retry.className = "retry-button";
  retry.textContent = "Retry";
  retry.addEventListener("click", retryHandler);
  node.appendChild(retry);

  messages.appendChild(node);
  messages.scrollTop = messages.scrollHeight;
  return node;
}

/**
 * Retry handler — re-submits the last user query through the form submit flow.
 * Removes the current error bubble, restores the prompt value, and dispatches
 * a new submit event.
 */
function retryHandler() {
  if (!window.lastQuery) return;

  // Remove the error bubble
  var errorBubble = document.querySelector(".error-bubble");
  if (errorBubble) errorBubble.remove();

  // Restore the last query to the input and re-submit
  promptInput.value = window.lastQuery;
  form.dispatchEvent(new Event("submit", { cancelable: true }));
}

/**
 * Restore previously persisted messages into the chat container.
 * Called synchronously before first paint to avoid flash-of-empty.
 * @param {Array<{role: string, content: string}>} savedMessages
 */
function restoreMessages(savedMessages) {
  for (var i = 0; i < savedMessages.length; i++) {
    addMessage(savedMessages[i].role, savedMessages[i].content);
  }
  messages.scrollTop = messages.scrollHeight;
}
