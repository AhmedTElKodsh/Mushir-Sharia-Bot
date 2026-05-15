/**
 * Render chat messages and status events into the DOM.
 * Relies on global `messages` (DOM element) defined in app.js.
 */

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
  // Auto-detect Arabic text and apply RTL direction
  if (kind !== "event") {
    var arabicChars = (text.match(/[\u0600-\u06ff]/g) || []).length;
    var ratio = arabicChars / Math.max(text.length, 1);
    if (ratio > 0.3) {
      node.setAttribute("dir", "rtl");
      node.style.textAlign = "right";
      node.style.fontFamily = "'Noto Sans Arabic', 'Segoe UI', sans-serif";
    }
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
