/**
 * App orchestrator: initializes DOM references, handles form submission,
 * dispatches SSE events to the renderer, and manages local chat history.
 */

const form = document.getElementById("chat-form");
const promptInput = document.getElementById("prompt");
const messages = document.getElementById("messages");
const send = document.getElementById("send");
const conversationList = document.getElementById("conversation-list");
const languageToggle = document.getElementById("language-toggle");
const themeToggle = document.getElementById("theme-toggle");
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
var requestedLanguage = new URLSearchParams(window.location.search).get("lang");
var currentLanguage = requestedLanguage || conversationStore.get("mushir_ui_language") || "en";
var currentTheme = conversationStore.get("mushir_ui_theme") || "light";

var I18N = {
  en: {
    appTitle: "Mushir Sharia Chatbot",
    chatControls: "Chat controls",
    switchLanguageTitle: "Switch to Arabic",
    languageToggle: "العربية",
    switchThemeTitle: "Switch to {theme} theme",
    themeLight: "Light",
    themeDark: "Dark",
    newChat: "New Chat",
    newChatTitle: "Start a new conversation",
    historyLabel: "Previous chats",
    sidebarHeading: "Previous chats",
    chatLabel: "Current chat",
    messagesLabel: "Chat messages",
    formLabel: "Chat input form",
    welcome: "Ask a Sharia compliance question in English or Arabic.",
    welcomeKicker: "AAOIFI-grounded assistant",
    welcomeCopy: "Mushir checks retrieved standard excerpts, asks for missing facts, and keeps answers informational.",
    examplesLabel: "Example questions",
    exampleMurabahaLabel: "Murabaha delay",
    exampleMurabaha: "Can a customer delay payment in a murabaha contract?",
    exampleIjaraLabel: "Ijara facts",
    exampleIjara: "What information is needed to assess an ijara transaction?",
    exampleArabicLabel: "Arabic question",
    exampleArabic: "هل يجوز فرض غرامة تأخير في عقد مرابحة؟",
    placeholder: "Ask about an Islamic finance transaction...",
    composerHint: "Add the transaction type, parties, payment terms, and the exact point you want checked.",
    ask: "Ask Mushir",
    streaming: "Streaming...",
    emptyHistory: "No previous chats yet.",
    conversation: "Conversation",
    retrieved: "Retrieved AAOIFI evidence - confidence {confidence}",
    source: "AAOIFI source: {standard}{section}{page}{source}",
    sourceSection: " section {section}",
    reviewComplete: "Review complete: {status}",
    connectionInterrupted: "Connection interrupted before Mushir finished. Please retry.",
    serviceUnavailable: "Could not reach the answer service. Please check your connection and retry.",
    requestFailed: "The request could not be processed.",
    validationPrefix: "I couldn't process that question: ",
    tooManyRequests: "Too many requests. Please wait a moment and try again.",
    streamError: "The answer service could not complete the request. Please try again later.",
    requestId: " Request ID: {requestId}.",
    statusCompliant: "Compliant",
    statusNonCompliant: "Non-compliant",
    statusPartiallyCompliant: "Partially compliant",
    statusInsufficientData: "Needs more information",
    statusClarificationNeeded: "Needs clarification",
    statusFinished: "Finished",
    composing: "Mushir is composing...",
    error: "Error",
    retry: "Retry"
  },
  ar: {
    appTitle: "مستشار مشير الشرعي",
    chatControls: "أدوات المحادثة",
    switchLanguageTitle: "Switch to English",
    languageToggle: "English",
    switchThemeTitle: "التبديل إلى المظهر {theme}",
    themeLight: "فاتح",
    themeDark: "داكن",
    newChat: "محادثة جديدة",
    newChatTitle: "ابدأ محادثة جديدة",
    historyLabel: "المحادثات السابقة",
    sidebarHeading: "المحادثات السابقة",
    chatLabel: "المحادثة الحالية",
    messagesLabel: "رسائل المحادثة",
    formLabel: "نموذج إدخال المحادثة",
    welcome: "اسأل عن الالتزام الشرعي في المعاملات المالية بالعربية أو الإنجليزية.",
    welcomeKicker: "مساعد مستند إلى معايير أيوفي",
    welcomeCopy: "يفحص مشير مقتطفات المعايير المسترجعة، ويطلب الحقائق الناقصة، ويحافظ على الإجابات في نطاق المعلومات.",
    examplesLabel: "أسئلة مقترحة",
    exampleMurabahaLabel: "تأخير المرابحة",
    exampleMurabaha: "هل يجوز للعميل تأخير السداد في عقد مرابحة؟",
    exampleIjaraLabel: "بيانات الإجارة",
    exampleIjara: "ما المعلومات المطلوبة لتقييم معاملة إجارة؟",
    exampleArabicLabel: "سؤال عربي",
    exampleArabic: "هل يجوز فرض غرامة تأخير في عقد مرابحة؟",
    placeholder: "اسأل عن معاملة مالية إسلامية...",
    composerHint: "أضف نوع المعاملة، والأطراف، وشروط السداد، والنقطة التي تريد فحصها بدقة.",
    ask: "اسأل مشير",
    streaming: "جارٍ التحليل...",
    emptyHistory: "لا توجد محادثات سابقة بعد.",
    conversation: "محادثة",
    retrieved: "تم العثور على أدلة من أيوفي - درجة الثقة {confidence}",
    source: "مصدر أيوفي: {standard}{section}{page}{source}",
    sourceSection: " القسم {section}",
    reviewComplete: "اكتملت المراجعة: {status}",
    connectionInterrupted: "انقطع الاتصال قبل أن ينهي مشير الإجابة. يرجى المحاولة مرة أخرى.",
    serviceUnavailable: "تعذر الوصول إلى خدمة الإجابة. تحقق من الاتصال ثم أعد المحاولة.",
    requestFailed: "تعذر معالجة الطلب.",
    validationPrefix: "تعذر معالجة السؤال: ",
    tooManyRequests: "طلبات كثيرة جدًا. انتظر قليلًا ثم حاول مرة أخرى.",
    streamError: "تعذر على خدمة الإجابة إكمال الطلب. يرجى المحاولة لاحقًا.",
    requestId: " رقم الطلب: {requestId}.",
    statusCompliant: "متوافق",
    statusNonCompliant: "غير متوافق",
    statusPartiallyCompliant: "متوافق جزئيًا",
    statusInsufficientData: "يحتاج إلى معلومات إضافية",
    statusClarificationNeeded: "يحتاج إلى توضيح",
    statusFinished: "اكتمل",
    composing: "مشير يكتب الإجابة...",
    error: "خطأ",
    retry: "أعد المحاولة"
  }
};

function t(key, values) {
  var catalog = I18N[currentLanguage] || I18N.en;
  var text = catalog[key] || I18N.en[key] || key;
  values = values || {};
  return text.replace(/\{(\w+)\}/g, function(_, name) {
    return values[name] == null ? "" : String(values[name]);
  });
}

function applyLanguage(language) {
  currentLanguage = language === "ar" ? "ar" : "en";
  conversationStore.set("mushir_ui_language", currentLanguage);
  document.documentElement.lang = currentLanguage;
  document.documentElement.dir = currentLanguage === "ar" ? "rtl" : "ltr";
  document.title = t("appTitle");

  var heading = document.querySelector("h1");
  if (heading) heading.textContent = t("appTitle");

  var headerActions = document.querySelector(".header-actions");
  if (headerActions) headerActions.setAttribute("aria-label", t("chatControls"));

  if (languageToggle) {
    languageToggle.textContent = t("languageToggle");
    languageToggle.setAttribute("title", t("switchLanguageTitle"));
  }
  updateThemeToggle();

  var newChatBtn = document.getElementById("new-chat");
  if (newChatBtn) {
    newChatBtn.textContent = t("newChat");
    newChatBtn.setAttribute("title", t("newChatTitle"));
  }

  var sidebar = document.getElementById("history-sidebar");
  if (sidebar) sidebar.setAttribute("aria-label", t("historyLabel"));

  var sidebarHeading = document.querySelector(".sidebar-heading");
  if (sidebarHeading) sidebarHeading.textContent = t("sidebarHeading");

  var chatPanel = document.querySelector(".chat-panel");
  if (chatPanel) chatPanel.setAttribute("aria-label", t("chatLabel"));

  messages.setAttribute("aria-label", t("messagesLabel"));
  form.setAttribute("aria-label", t("formLabel"));
  promptInput.setAttribute("placeholder", t("placeholder"));
  if (!send.disabled) send.textContent = t("ask");
  var composerHint = document.getElementById("composer-hint");
  if (composerHint) composerHint.textContent = t("composerHint");

  var welcomeNodes = messages.querySelectorAll("[data-welcome='true']");
  for (var i = 0; i < welcomeNodes.length; i++) {
    welcomeNodes[i].setAttribute("dir", currentLanguage === "ar" ? "rtl" : "ltr");
  }
  refreshWelcomeCards();
  bindPromptChips();
  renderConversationList();
}

applyLanguage(currentLanguage);
applyTheme(currentTheme);

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

  send.disabled = true;
  send.textContent = t("streaming");
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
          disclaimer_acknowledged: true
        }),
        conversation_history: messagesArray
      })
    });

    if (!response.ok) {
      removeTypingIndicator();
      var responseRequestId = response.headers.get("X-Request-ID") || "";
      renderErrorBubble(await formatHttpError(response, responseRequestId));
      send.disabled = false;
      send.textContent = t("ask");
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
        addEvent(t("retrieved", {confidence: confidence}));
      },

      onCitation: function(data) {
        _assistantCitations.push({
          standard: data.standard_number || data.document_id || "AAOIFI source",
          section: data.section_number || null,
          title: data.section_title || null,
          excerpt: data.excerpt || data.text || null
        });
        var standard = data.standard_number || data.document_id || "AAOIFI source";
        var section = data.section_number ? t("sourceSection", {section: data.section_number}) : "";
        var sourceFile = data.document_id && data.document_id !== standard
          ? " - " + data.document_id : "";
        var pageNum = (data.section_title && /\bp\.?\s*\d+/i.test(data.section_title))
          ? " (" + data.section_title + ")" : "";
        addEvent(t("source", {standard: standard, section: section, page: pageNum, source: sourceFile}));
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
        addEvent(t("reviewComplete", {status: formatStatusLabel(data.status)}));

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
        var connectionMessage = t("connectionInterrupted") + formatRequestIdSuffix(currentRequestId);
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
          renderErrorBubble(t("connectionInterrupted") + formatRequestIdSuffix(currentRequestId));
        }
        send.disabled = false;
        send.textContent = t("ask");
      }
    });
  } catch (error) {
    appState.streaming = false;
    abortTypewriter();
    removeTypingIndicator();
    var requestMessage = t("serviceUnavailable");
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
    send.textContent = t("ask");
  }
}

async function formatHttpError(response, requestId) {
  var message = t("requestFailed");
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
      message = t("tooManyRequests");
    }
  }
  if (code === "VALIDATION_ERROR") {
    return t("validationPrefix") + message + formatRequestIdSuffix(requestId);
  }
  return message + formatRequestIdSuffix(requestId);
}

function formatSafeStreamError(data, fallbackRequestId) {
  var message = (data && data.message) || t("streamError");
  return message + formatRequestIdSuffix((data && data.request_id) || fallbackRequestId);
}

function formatRequestIdSuffix(requestId) {
  return requestId ? t("requestId", {requestId: requestId}) : "";
}

(function() {
  var newChatBtn = document.getElementById("new-chat");
  if (!newChatBtn) return;
  newChatBtn.addEventListener("click", function() {
    startNewChat();
  });
})();

if (languageToggle) {
  languageToggle.addEventListener("click", function() {
    applyLanguage(currentLanguage === "ar" ? "en" : "ar");
  });
}

if (themeToggle) {
  themeToggle.addEventListener("click", function() {
    applyTheme(currentTheme === "dark" ? "light" : "dark");
  });
}

function applyTheme(theme) {
  currentTheme = theme === "dark" ? "dark" : "light";
  conversationStore.set("mushir_ui_theme", currentTheme);
  document.documentElement.setAttribute("data-theme", currentTheme);
  updateThemeToggle();
}

function updateThemeToggle() {
  if (!themeToggle) return;
  var nextTheme = currentTheme === "dark" ? "light" : "dark";
  var label = nextTheme === "dark" ? t("themeDark") : t("themeLight");
  themeToggle.textContent = label;
  themeToggle.setAttribute("title", t("switchThemeTitle", {theme: label}));
}

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
  send.textContent = t("ask");
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
  send.textContent = t("ask");
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
  welcome.className = "welcome-card";
  welcome.setAttribute("dir", currentLanguage === "ar" ? "rtl" : "ltr");
  welcome.setAttribute("data-welcome", "true");
  welcome.innerHTML = welcomeCardMarkup();
  messages.appendChild(welcome);
  bindPromptChips();
}

function welcomeCardMarkup() {
  return [
    '<div class="welcome-kicker">' + escapeHtml(t("welcomeKicker")) + '</div>',
    '<div class="welcome-title">' + escapeHtml(t("welcome")) + '</div>',
    '<div class="welcome-copy">' + escapeHtml(t("welcomeCopy")) + '</div>',
    '<div class="prompt-chips" aria-label="' + escapeHtml(t("examplesLabel")) + '">',
      '<button class="prompt-chip" type="button" data-example="' + escapeHtml(t("exampleMurabaha")) + '">' + escapeHtml(t("exampleMurabahaLabel")) + '</button>',
      '<button class="prompt-chip" type="button" data-example="' + escapeHtml(t("exampleIjara")) + '">' + escapeHtml(t("exampleIjaraLabel")) + '</button>',
      '<button class="prompt-chip" type="button" data-example="' + escapeHtml(t("exampleArabic")) + '">' + escapeHtml(t("exampleArabicLabel")) + '</button>',
    '</div>'
  ].join("");
}

function refreshWelcomeCards() {
  var cards = messages.querySelectorAll(".welcome-card[data-welcome='true']");
  for (var i = 0; i < cards.length; i++) {
    cards[i].innerHTML = welcomeCardMarkup();
  }
}

function bindPromptChips() {
  var chips = messages.querySelectorAll(".prompt-chip");
  for (var i = 0; i < chips.length; i++) {
    if (chips[i].dataset.bound === "true") continue;
    chips[i].dataset.bound = "true";
    chips[i].addEventListener("click", function() {
      promptInput.value = this.getAttribute("data-example") || "";
      promptInput.focus();
    });
  }
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, function(character) {
    return {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;"
    }[character];
  });
}

function renderConversationList() {
  if (!conversationList) return;
  var conversations = conversationStore.listConversations();
  conversationList.innerHTML = "";
  if (!conversations.length) {
    var empty = document.createElement("div");
    empty.className = "empty-history";
    empty.textContent = t("emptyHistory");
    conversationList.appendChild(empty);
    return;
  }
  conversations.forEach(function(item) {
    var button = document.createElement("button");
    button.type = "button";
    button.className = "conversation-item" + (item.session_id === sessionId ? " active" : "");
    button.setAttribute("role", "listitem");
    button.setAttribute("title", item.title || t("conversation"));
    button.addEventListener("click", function() {
      loadConversation(item.session_id);
    });

    var title = document.createElement("span");
    title.className = "conversation-title";
    title.textContent = item.title || t("conversation");

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
    return new Date(timestamp).toLocaleString(currentLanguage === "ar" ? "ar" : [], {
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
    COMPLIANT: t("statusCompliant"),
    NON_COMPLIANT: t("statusNonCompliant"),
    PARTIALLY_COMPLIANT: t("statusPartiallyCompliant"),
    INSUFFICIENT_DATA: t("statusInsufficientData"),
    CLARIFICATION_NEEDED: t("statusClarificationNeeded")
  };
  return labels[status] || t("statusFinished");
}
