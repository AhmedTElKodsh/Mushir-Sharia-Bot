/**
 * App orchestrator — initializes DOM references, handles form submission,
 * and dispatches SSE events to the renderer.
 */

const form = document.getElementById("chat-form");
const promptInput = document.getElementById("prompt");
const messages = document.getElementById("messages");
const send = document.getElementById("send");
let context = {};

/**
 * Global application state shared across modules.
 * @type {{ streaming: boolean }}
 */
var appState = { streaming: false };

/**
 * Configurable parameters shared across modules.
 * @type {{ typewriterSpeed: number }}
 */
var config = { typewriterSpeed: 25 };

form.addEventListener("submit", async function(event) {
  event.preventDefault();
  var query = promptInput.value.trim();
  if (!query) return;

  // Abort any in-progress typewriter from a previous response
  appState.streaming = false;
  abortTypewriter();

  addMessage("user", query);
  send.disabled = true;
  send.textContent = "Streaming...";
  var thinkingMessage = null;

  try {
    appState.streaming = true;
    var response = await fetch("/api/v1/query/stream", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({query: query, context: context})
    });
    var events = parseSse(await response.text());

    for (var i = 0; i < events.length; i++) {
      var item = events[i];
      var data = item.data || {};

      if (item.type === "started") {
        thinkingMessage = addEvent("Thinking...");
      }

      if (item.type === "retrieval") {
        if (thinkingMessage) thinkingMessage.remove();
        thinkingMessage = null;
        addEvent("Confidence " + Number(data.confidence || 0).toFixed(2));
      }

      if (item.type === "token") {
        // Create the assistant bubble then render via typewriter
        var node = addMessage("assistant", "");
        renderTypewriter(data.text, node);
      }

      if (item.type === "citation") {
        var standard = data.standard_number || data.document_id || "AAOIFI source";
        var section = data.section_number ? " \u00a7" + data.section_number : "";
        var sourceFile = data.document_id && data.document_id !== standard
          ? " \u2014 " + data.document_id : "";
        var pageNum = (data.section_title && /\bp\.?\s*\d+/i.test(data.section_title))
          ? " (" + data.section_title + ")" : "";
        addEvent("\ud83d\udcd6 " + standard + section + pageNum + sourceFile);
      }

      if (item.type === "error") {
        if (thinkingMessage) thinkingMessage.remove();
        thinkingMessage = null;
        addMessage("assistant", data.message);
      }

      if (item.type === "done") {
        if (thinkingMessage) thinkingMessage.remove();
        thinkingMessage = null;
        // Flush remaining typewriter text instantly on completion
        appState.streaming = false;
        abortTypewriter();
        if (data.clarification_question) addMessage("assistant", data.clarification_question);
        context = data.metadata || context;
        addEvent("Complete - " + data.status);
      }
    }
  } catch (error) {
    if (thinkingMessage) thinkingMessage.remove();
    appState.streaming = false;
    abortTypewriter();
    addMessage("assistant", "Request failed: " + error.message);
  } finally {
    send.disabled = false;
    send.textContent = "Ask Mushir";
  }
});

/* ===== Disclaimer Banner Logic ===== */
(function () {
  var banner = document.getElementById("disclaimer-banner");
  var dismissBtn = document.getElementById("dismiss-disclaimer");
  var prefStore = new StorageAdapter();

  if (!banner || !dismissBtn) return;

  /* On load: hide banner if already dismissed this session */
  if (prefStore.get(STORAGE_KEY_DISCLAIMER_DISMISSED) === "true") {
    banner.style.display = "none";
  }

  /* Dismiss handler: mark dismissed + hide banner */
  dismissBtn.addEventListener("click", function () {
    prefStore.set(STORAGE_KEY_DISCLAIMER_DISMISSED, "true");
    banner.style.display = "none";
  });

  /**
   * Global reset for "New Chat" feature.
   * Clears the dismissed flag and re-shows the banner.
   * Callers: future "New Chat" button handler.
   */
  window.resetDisclaimerBanner = function () {
    prefStore.remove(STORAGE_KEY_DISCLAIMER_DISMISSED);
    if (banner) banner.style.display = "";
  };
})();

/* ===== Keyboard Shortcuts ===== */
Shortcuts.init();
