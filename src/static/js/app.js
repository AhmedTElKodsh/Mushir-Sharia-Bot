/**
 * App orchestrator — initializes DOM references, handles form submission,
 * and dispatches SSE events to the renderer.
 */

const form = document.getElementById("chat-form");
const promptInput = document.getElementById("prompt");
const messages = document.getElementById("messages");
const send = document.getElementById("send");
const disclaimer = document.getElementById("disclaimer");
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
var currentAssistantNode = null;
var streamActive = false;

form.addEventListener("submit", async function(event) {
  event.preventDefault();
  submitQuery();
});

if (disclaimer) {
  send.disabled = !disclaimer.checked;
  disclaimer.addEventListener("change", function() {
    send.disabled = !disclaimer.checked;
  });
}

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
  var _assistantCitations = [];
  var firstTokenReceived = false;
  currentAssistantNode = null;
  streamActive = true;

  try {
    appState.streaming = true;
    renderTypingIndicator();
    var response = await fetch("/api/v1/query/stream", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        query: query,
        context: Object.assign({}, context, {
          disclaimer_acknowledged: Boolean(disclaimer && disclaimer.checked)
        }),
        conversation_history: messagesArray
      })
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
        // Accumulate full assistant content for persistence
        _assistantContent += data.text || "";
        if (!firstTokenReceived) {
          // First token: remove typing indicator, create assistant bubble
          removeTypingIndicator();
          currentAssistantNode = addMessage("assistant", "");
          renderTypewriter(data.text || "", currentAssistantNode);
          firstTokenReceived = true;
        } else if (currentAssistantNode) {
          /* Extend typewriter buffer with accumulated content so later tokens'
             text (including citation markers) renders into the DOM. */
          extendTypewriterBuffer(_assistantContent);
        }
      },

      onRetrieval: function(data) {
        var confidence = Number(data.confidence || 0).toFixed(2);
        addEvent("Confidence " + confidence);
      },

      onCitation: function(data) {
        /* Track citations for persistence */
        _assistantCitations.push({
          standard: data.standard_number || data.document_id || "AAOIFI source",
          section: data.section_number || null,
          title: data.section_title || null,
          excerpt: data.excerpt || data.text || null
        });
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

        // Persist the error as an assistant message
        messagesArray.push({
          role: "assistant",
          content: data.message || "An unexpected error occurred.",
          timestamp: Date.now(),
          status: "error",
          citations: []
        });
        conversationStore.saveConversation(sessionId, messagesArray);
      },

      onDone: function(data) {
        streamActive = false;
        appState.streaming = false;
        abortTypewriter();

        /* Post-process citations: replace [N] markers with interactive anchors */
        if (currentAssistantNode && _assistantCitations.length > 0) {
          renderCitations(currentAssistantNode, _assistantCitations);
        }

        if (!firstTokenReceived) {
          removeTypingIndicator();
        }
        if (data.clarification_question && data.clarification_question !== _assistantContent) {
          addMessage("assistant", data.clarification_question);
        }
        context = data.metadata || context;
        /* Render compliance badge from done event status (retrieval event lacks status) */
        if (data.status) renderBadge(data.status);
        addEvent("Complete - " + data.status);

        // Persist the completed assistant message
        var assistantContent = _assistantContent || data.answer || data.clarification_question || "";
        if (assistantContent) {
          messagesArray.push({
            role: "assistant",
            content: assistantContent,
            timestamp: Date.now(),
            status: data.status,
            citations: _assistantCitations
          });
        }
        conversationStore.saveConversation(sessionId, messagesArray);
      },

      onStreamError: function(err) {
        streamActive = false;
        appState.streaming = false;
        abortTypewriter();
        removeTypingIndicator();
        renderErrorBubble("Connection lost: " + err.message);

        // Persist the connection error
        messagesArray.push({
          role: "assistant",
          content: "Connection lost: " + err.message,
          timestamp: Date.now(),
          status: "error",
          citations: []
        });
        conversationStore.saveConversation(sessionId, messagesArray);
      },

      onComplete: function() {
        if (streamActive) {
          removeTypingIndicator();
          renderErrorBubble("Stream ended unexpectedly.");
        }
        send.disabled = Boolean(disclaimer && !disclaimer.checked);
        send.textContent = "Ask Mushir";
      }
    });
  } catch (error) {
    appState.streaming = false;
    abortTypewriter();
    removeTypingIndicator();
    renderErrorBubble("Request failed: " + error.message);

    // Persist the network error
    messagesArray.push({
      role: "assistant",
      content: "Request failed: " + error.message,
      timestamp: Date.now(),
      status: "error",
      citations: []
    });
    conversationStore.saveConversation(sessionId, messagesArray);

    send.disabled = Boolean(disclaimer && !disclaimer.checked);
    send.textContent = "Ask Mushir";
  }
}

/* ===== New Chat Handler ===== */
(function() {
  var newChatBtn = document.getElementById("new-chat");
  if (!newChatBtn) return;
  newChatBtn.addEventListener("click", function() {
    /* Clear the DOM message container */
    messages.innerHTML = "";
    /* Clear persisted conversation data */
    conversationStore.clearConversation();
    /* Reset application state */
    messagesArray = [];
    context = {};
    if (disclaimer) {
      disclaimer.checked = false;
      send.disabled = true;
    }
    /* Restore the welcome message */
    var welcome = document.createElement("div");
    welcome.className = "message assistant";
    welcome.setAttribute("dir", "auto");
    welcome.textContent = "Ask a Sharia compliance question in English or Arabic.";
    messages.appendChild(welcome);
  });
})();

/* ===== Keyboard Shortcuts ===== */
Shortcuts.init();
