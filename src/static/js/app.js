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

/* ===== Conversation Persistence State ===== */

/**
 * @type {Array<{role: string, content: string, timestamp?: number, status?: string, citations?: Array}>}
 */
var messagesArray = [];
var sessionId = "session_" + Date.now();
var conversationStore = new StorageAdapter();

/* ===== Restore Conversation on Load (synchronous, before first paint) ===== */

(function restoreOnLoad() {
  var saved = conversationStore.restoreConversation(sessionId);
  if (saved && Array.isArray(saved.messages) && saved.messages.length > 0) {
    messagesArray = saved.messages;
    /* Clear the HTML-wired welcome message and render saved messages */
    messages.innerHTML = "";
    restoreMessages(messagesArray);
  }
  /* If no saved conversation, the welcome message in index.html remains visible */
})();

/**
 * Configurable parameters shared across modules.
 * @type {{ typewriterSpeed: number }}
 */
var config = { typewriterSpeed: 25 };

window.lastQuery = "";
var firstTokenReceived = false;

form.addEventListener("submit", async function(event) {
  event.preventDefault();
  submitQuery();
});

/**
 * Core query submission — sends the user's message via SSE streaming.
 * Handles typing indicator, error recovery, and retry flow.
 * @param {string} [queryOverride] - Optional override for retry
 */
async function submitQuery() {
  var query = promptInput.value.trim() || window.lastQuery;
  if (!query) return;
  window.lastQuery = query;
  promptInput.value = "";

  // Abort any in-progress typewriter from a previous response
  appState.streaming = false;
  abortTypewriter();

  addMessage("user", query);
  /* Track user message in conversation array */
  messagesArray.push({role: "user", content: query, timestamp: Date.now()});

  send.disabled = true;
  send.textContent = "Streaming...";
  var thinkingMessage = null;
  var _assistantContent = "";

  try {
    appState.streaming = true;
    var response = await fetch("/api/v1/query/stream", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({query: query, context: context})
    });

    if (!response.ok) {
      removeTypingIndicator();
      renderErrorBubble("Server returned " + response.status + ": " + response.statusText);
      send.disabled = false;
      send.textContent = "Ask Mushir";
      return;
    }

    var reader = response.body.getReader();

    processSseStream(reader, {
      onStarted: function() {
        // Typing indicator already showing — first token will swap it
      },

      onToken: function(data) {
        if (!firstTokenReceived) {
          // First token: remove typing indicator, create assistant bubble
          removeTypingIndicator();
          currentAssistantNode = addMessage("assistant", "");
          renderTypewriter(data.text || "", currentAssistantNode);
          firstTokenReceived = true;
        } else if (currentAssistantNode) {
          // Subsequent tokens: typewriter handles appending
        }
      },

      onRetrieval: function(data) {
        if (data.status) renderBadge(data.status);
        var confidence = Number(data.confidence || 0).toFixed(2);
        addEvent("Confidence " + confidence);
      },

      onCitation: function(data) {
        var standard = data.standard_number || data.document_id || "AAOIFI source";
        var section = data.section_number ? " \u00a7" + data.section_number : "";
        var sourceFile = data.document_id && data.document_id !== standard
          ? " \u2014 " + data.document_id : "";
        var pageNum = (data.section_title && /\bp\.?\s*\d+/i.test(data.section_title))
          ? " (" + data.section_title + ")" : "";
        addEvent("\ud83d\udcd6 " + standard + section + pageNum + sourceFile);
      },

      onError: function(data) {
        streamActive = false;
        appState.streaming = false;
        abortTypewriter();
        removeTypingIndicator();
        renderErrorBubble(data.message || "An unexpected error occurred.");
      },

      onDone: function(data) {
        streamActive = false;
        appState.streaming = false;
        abortTypewriter();
        if (!firstTokenReceived) {
          removeTypingIndicator();
        }
        if (data.clarification_question) {
          addMessage("assistant", data.clarification_question);
        }
        context = data.metadata || context;
        addEvent("Complete - " + data.status);
      },

      onStreamError: function(err) {
        streamActive = false;
        appState.streaming = false;
        abortTypewriter();
        removeTypingIndicator();
        renderErrorBubble("Connection lost: " + err.message);
      },

      onComplete: function() {
        if (streamActive) {
          removeTypingIndicator();
          renderErrorBubble("Stream ended unexpectedly.");
        }
        send.disabled = false;
        send.textContent = "Ask Mushir";
      }
    });
  } catch (error) {
    appState.streaming = false;
    abortTypewriter();
    removeTypingIndicator();
    renderErrorBubble("Request failed: " + error.message);
    send.disabled = false;
    send.textContent = "Ask Mushir";
  }
}

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
