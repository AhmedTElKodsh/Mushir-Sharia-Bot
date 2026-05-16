/**
 * App orchestrator: initializes DOM references, handles form submission,
 * dispatches SSE events to the renderer, and manages local chat history.
 */

const form = document.getElementById("chat-form");
const promptInput = document.getElementById("prompt");
const messages = document.getElementById("messages");
const send = document.getElementById("send");
const conversationList = document.getElementById("conversation-list");
const disclaimerAck = document.getElementById("disclaimer-ack");
let context = {};

/**
 * Global application state shared across modules.
 * @type {{ streaming: boolean }}
 */
var appState = { streaming: false };

/**
 * @type {Array<{role: string, content: string, timestamp?: number, status?: string, citations?: Array}>}
 */
var messagesArray = [];
var sessionId = "session_" + Date.now();
var conversationStore = new StorageAdapter();

/**
 * Configurable parameters shared across modules.
 * @type {{ typewriterSpeed: number }}
 */
var config = { typewriterSpeed: 25 };

window.lastQuery = "";
var currentAssistantNode = null;
var streamActive = false;

(function restoreOnLoad() {
  var conversations = conversationStore.listConversations();
  var activeId = conversations.length ? conversations[0].session_id : null;
  var saved = activeId ? conversationStore.restoreConversation(activeId) : null;
  if (saved && Array.isArray(saved.messages) && saved.messages.length > 0) {
    sessionId = saved.session_id || activeId || sessionId;
    messagesArray = saved.messages;
    messages.innerHTML = "";
    restoreMessages(messagesArray);
  }
  renderConversationList();
})();

form.addEventListener("submit", async function(event) {
  event.preventDefault();
  submitQuery();
});

/**
 * Core query submission: sends the user's message via SSE streaming.
 */
async function submitQuery() {
  var query = promptInput.value.trim() || window.lastQuery;
  if (!query) return;
  window.lastQuery = query;
  promptInput.value = "";

  appState.streaming = false;
  abortTypewriter();

  addMessage("user", query);
  messagesArray.push({role: "user", content: query, timestamp: Date.now()});
  persistConversation();

  if (disclaimerAck && !disclaimerAck.checked) {
    var disclaimerMessage = "Before I answer, please tick the acknowledgement above. Mushir provides informational guidance from retrieved AAOIFI excerpts only. It is not a binding fatwa, legal advice, or financial advice.";
    addMessage("assistant", disclaimerMessage);
    messagesArray.push({
      role: "assistant",
      content: disclaimerMessage,
      timestamp: Date.now(),
      status: "CLARIFICATION_NEEDED",
      citations: []
    });
    persistConversation();
    return;
  }

  send.disabled = true;
  send.textContent = "Streaming...";
  var _assistantContent = "";
  var _assistantCitations = [];
  var firstTokenReceived = false;
  var currentRequestId = "";
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
        session_id: sessionId,
        context: Object.assign({}, context, {
          disclaimer_acknowledged: Boolean(disclaimerAck && disclaimerAck.checked)
        }),
        conversation_history: messagesArray
      })
    });

    if (!response.ok) {
      removeTypingIndicator();
      var responseRequestId = response.headers.get("X-Request-ID") || "";
      renderErrorBubble(await formatHttpError(response, responseRequestId));
      send.disabled = false;
      send.textContent = "Ask Mushir";
      return;
    }

    var reader = response.body.getReader();

    processSseStream(reader, {
      onStarted: function(data) {
        currentRequestId = data.request_id || "";
      },

      onToken: function(data) {
        _assistantContent += data.text || "";
        if (!firstTokenReceived) {
          removeTypingIndicator();
          currentAssistantNode = addMessage("assistant", "");
          renderTypewriter(data.text || "", currentAssistantNode);
          firstTokenReceived = true;
        } else if (currentAssistantNode) {
          extendTypewriterBuffer(_assistantContent);
        }
      },

      onRetrieval: function(data) {
        var confidence = Number(data.confidence || 0).toFixed(2);
        addEvent("Retrieved AAOIFI evidence - confidence " + confidence);
      },

      onCitation: function(data) {
        _assistantCitations.push({
          standard: data.standard_number || data.document_id || "AAOIFI source",
          section: data.section_number || null,
          title: data.section_title || null,
          excerpt: data.excerpt || data.text || null
        });
        var standard = data.standard_number || data.document_id || "AAOIFI source";
        var section = data.section_number ? " section " + data.section_number : "";
        var sourceFile = data.document_id && data.document_id !== standard
          ? " - " + data.document_id : "";
        var pageNum = (data.section_title && /\bp\.?\s*\d+/i.test(data.section_title))
          ? " (" + data.section_title + ")" : "";
        addEvent("AAOIFI source: " + standard + section + pageNum + sourceFile);
      },

      onError: function(data) {
        streamActive = false;
        appState.streaming = false;
        abortTypewriter();
        removeTypingIndicator();
        var errorMessage = formatSafeStreamError(data, currentRequestId);
        renderErrorBubble(errorMessage);
        messagesArray.push({
          role: "assistant",
          content: errorMessage,
          timestamp: Date.now(),
          status: "error",
          citations: []
        });
        persistConversation();
      },

      onDone: function(data) {
        streamActive = false;
        appState.streaming = false;
        abortTypewriter();

        if (currentAssistantNode && _assistantCitations.length > 0) {
          renderCitations(currentAssistantNode, _assistantCitations);
        }

        if (!firstTokenReceived) {
          removeTypingIndicator();
        }
        if (data.status !== "CLARIFICATION_NEEDED" && data.clarification_question && data.clarification_question !== _assistantContent) {
          addMessage("assistant", data.clarification_question);
        }
        context = data.metadata || context;
        if (data.status) renderBadge(data.status, currentAssistantNode);
        addEvent("Review complete: " + formatStatusLabel(data.status));

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
        persistConversation();
      },

      onStreamError: function(err) {
        streamActive = false;
        appState.streaming = false;
        abortTypewriter();
        removeTypingIndicator();
        var connectionMessage = "Connection interrupted before Mushir finished. Please retry." + formatRequestIdSuffix(currentRequestId);
        renderErrorBubble(connectionMessage);
        messagesArray.push({
          role: "assistant",
          content: connectionMessage,
          timestamp: Date.now(),
          status: "error",
          citations: []
        });
        persistConversation();
      },

      onComplete: function() {
        if (streamActive) {
          removeTypingIndicator();
          renderErrorBubble("Connection interrupted before Mushir finished. Please retry." + formatRequestIdSuffix(currentRequestId));
        }
        send.disabled = false;
        send.textContent = "Ask Mushir";
      }
    });
  } catch (error) {
    appState.streaming = false;
    abortTypewriter();
    removeTypingIndicator();
    var requestMessage = "Could not reach the answer service. Please check your connection and retry.";
    renderErrorBubble(requestMessage);
    messagesArray.push({
      role: "assistant",
      content: requestMessage,
      timestamp: Date.now(),
      status: "error",
      citations: []
    });
    persistConversation();
    send.disabled = false;
    send.textContent = "Ask Mushir";
  }
}

async function formatHttpError(response, requestId) {
  var message = "The request could not be processed.";
  var code = "";
  try {
    var payload = await response.clone().json();
    if (payload && payload.error) {
      message = payload.error.message || message;
      code = payload.error.code || "";
      requestId = payload.error.request_id || requestId;
    }
  } catch (_) {
    if (response.status === 429) {
      message = "Too many requests. Please wait a moment and try again.";
    }
  }
  if (code === "VALIDATION_ERROR") {
    return "I couldn't process that question: " + message + formatRequestIdSuffix(requestId);
  }
  return message + formatRequestIdSuffix(requestId);
}

function formatSafeStreamError(data, fallbackRequestId) {
  var message = (data && data.message) || "The answer service could not complete the request. Please try again later.";
  return message + formatRequestIdSuffix((data && data.request_id) || fallbackRequestId);
}

function formatRequestIdSuffix(requestId) {
  return requestId ? " Request ID: " + requestId + "." : "";
}

(function() {
  var newChatBtn = document.getElementById("new-chat");
  if (!newChatBtn) return;
  newChatBtn.addEventListener("click", function() {
    startNewChat();
  });
})();

function persistConversation() {
  conversationStore.saveConversation(sessionId, messagesArray);
  renderConversationList();
}

function startNewChat() {
  messages.innerHTML = "";
  sessionId = "session_" + Date.now();
  window.lastQuery = "";
  currentAssistantNode = null;
  streamActive = false;
  appState.streaming = false;
  abortTypewriter();
  removeTypingIndicator();
  promptInput.value = "";
  send.disabled = false;
  send.textContent = "Ask Mushir";
  messagesArray = [];
  context = {};
  renderWelcomeMessage();
  renderConversationList();
}

function loadConversation(targetSessionId) {
  if (!targetSessionId || targetSessionId === sessionId) return;
  var saved = conversationStore.restoreConversation(targetSessionId);
  if (!saved || !Array.isArray(saved.messages)) return;
  appState.streaming = false;
  abortTypewriter();
  removeTypingIndicator();
  sessionId = saved.session_id || targetSessionId;
  messagesArray = saved.messages;
  context = {};
  promptInput.value = "";
  send.disabled = false;
  send.textContent = "Ask Mushir";
  messages.innerHTML = "";
  if (messagesArray.length) {
    restoreMessages(messagesArray);
  } else {
    renderWelcomeMessage();
  }
  renderConversationList();
}

function renderWelcomeMessage() {
  var welcome = document.createElement("div");
  welcome.className = "message assistant";
  welcome.setAttribute("dir", "auto");
  welcome.textContent = "Ask a Sharia compliance question in English or Arabic.";
  messages.appendChild(welcome);
}

function renderConversationList() {
  if (!conversationList) return;
  var conversations = conversationStore.listConversations();
  conversationList.innerHTML = "";
  if (!conversations.length) {
    var empty = document.createElement("div");
    empty.className = "empty-history";
    empty.textContent = "No previous chats yet.";
    conversationList.appendChild(empty);
    return;
  }
  conversations.forEach(function(item) {
    var button = document.createElement("button");
    button.type = "button";
    button.className = "conversation-item" + (item.session_id === sessionId ? " active" : "");
    button.setAttribute("role", "listitem");
    button.setAttribute("title", item.title || "Conversation");
    button.addEventListener("click", function() {
      loadConversation(item.session_id);
    });

    var title = document.createElement("span");
    title.className = "conversation-title";
    title.textContent = item.title || "Conversation";

    var meta = document.createElement("span");
    meta.className = "conversation-meta";
    meta.textContent = formatConversationTime(item.timestamp);

    button.appendChild(title);
    button.appendChild(meta);
    conversationList.appendChild(button);
  });
}

function formatConversationTime(timestamp) {
  if (!timestamp) return "";
  try {
    return new Date(timestamp).toLocaleString([], {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit"
    });
  } catch (_) {
    return "";
  }
}

Shortcuts.init();

function formatStatusLabel(status) {
  var labels = {
    COMPLIANT: "Compliant",
    NON_COMPLIANT: "Non-compliant",
    PARTIALLY_COMPLIANT: "Partially compliant",
    INSUFFICIENT_DATA: "Needs more information",
    CLARIFICATION_NEEDED: "Needs clarification"
  };
  return labels[status] || "Finished";
}
