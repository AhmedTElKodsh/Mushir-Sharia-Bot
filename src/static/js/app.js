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
    placeholder: "Ask about an Islamic finance transaction...",
    composerHint: "Add the transaction type, parties, payment terms, and the exact point you want checked.",
    ask: "Ask Mushir",
    streaming: "Streaming...",
    emptyHistory: "No previous chats yet.",
    conversation: "Conversation",
    evidenceStatus: "Evidence status: {status}",
    captureUnknown: "Source capture date and age: unknown",
    captureAge: "{source} — captured: {date}; age: {age} days",
    evidenceClarification: "Clarification required",
    evidenceInsufficient: "Insufficient evidence",
    evidenceSources: "Sources available",
    evidenceNone: "No sources",
    evidenceUnknown: "Evidence status unavailable",
    unknownSource: "Unnamed source",
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
    statusCompliant: "Supported by retrieved evidence",
    statusNonCompliant: "Contradicted by retrieved evidence",
    statusPartiallyCompliant: "Requires scholar review",
    statusInsufficientData: "Insufficient source evidence",
    statusClarificationNeeded: "Needs clarification",
    statusFinished: "Finished",
    composing: "Mushir is composing...",
    error: "Error",
    retry: "Retry",
    traceTitle: "How this response was determined",
    traceUnderstood: "Understood as",
    traceLane_described_operation: "A described transaction",
    traceLane_structure: "A transaction structure question",
    traceLane_definition: "A definition request",
    traceLane_general: "A general request",
    traceKnown: "Information supplied",
    traceMissing: "Information still needed",
    traceQuestion: "Question asked",
    traceSources: "Cited references",
    traceNoSources: "No references cited for this response",
    traceDecision: "Response gate",
    traceDecide: "Details that would matter",
    traceLegend: "Symbols show information availability, not whether a rule is satisfied.",
    traceObserved: "Observed in source",
    traceReported: "You reported",
    traceUnknown: "Unknown",
    traceConflicting: "Conflicting information",
    traceMechanismUnknown: "Mechanism unknown",
    traceSlot_asset: "Asset",
    traceSlot_seller: "Seller",
    traceSlot_sales_channel: "Sales channel",
    traceSlot_late_payment_clause: "Late-payment clause",
    traceSlot_late_fee_beneficiary: "Recipient of late fees",
    traceSlot_insurance_leg: "Insurance arrangement",
    traceSlot_ownership_risk_sequence: "Ownership and risk sequence",
    traceSlot_early_settlement: "Early settlement",
    traceSlot_refund_terms: "Refund terms",
    traceSlot_resale_arranger: "Party arranging the onward sale",
    traceSlot_underlying_sukuk_contract: "Underlying Sukuk contract",
    traceReason_scope_refusal: "The requested binding ruling exceeds the informational scope.",
    traceReason_empty_request: "A question is needed before analysis can start.",
    traceReason_scholar_review_required: "The available evidence still requires scholar review.",
    traceReason_unsupported_asset: "The available sources do not establish support for this asset scenario.",
    traceReason_structure_evidence_incomplete: "The reply still requires transaction documents and an applicable approved rule.",
    traceReason_financing_party_unknown: "The financing party is not known.",
    traceReason_conflicting_user_facts: "Supplied details conflict.",
    traceReason_payment_total_discrepancy: "The stated total differs from the supplied payment schedule.",
    traceReason_mechanism_unknown: "The contract mechanism is not established.",
    traceReason_approved_rule_evaluated_overall_gates_pending: "An overall conclusion still needs review.",
    traceReason_material_evidence_incomplete: "Material details or approved rules are incomplete.",
    traceReason_disclaimer_required: "Please acknowledge the informational scope first.",
    traceReason_structure_details_needed: "A material structural detail needs clarification.",
    traceReason_approved_rule_missing: "No applicable approved rule is available.",
    traceReason_retrieval_unavailable: "The evidence service was unavailable.",
    traceReason_no_sources: "No cited source supports a response here.",
    traceReason_definition_cited: "A definition was located in a cited source.",
    traceReason_definition_support_unavailable: "No literal passage defining the requested concept was found.",
    traceReason_private_reasoning_requested: "A brief evidence explanation is available; private internal reasoning is unavailable.",
    traceReason_generated_claim_unverified: "The generated claim could not be verified against the cited passage and was withheld.",
    traceReason_literal_passage_cited: "The displayed quotation matches the cited source passage; assessment remains withheld.",
    traceReason_purpose_needed: "The purpose of the request needs clarification.",
    traceReason_purpose_unavailable: "The purpose of the request remains unknown.",
    traceReason_scenario_switch_confirmation: "Please confirm whether this describes a separate purchase.",
    traceReason_scenario_scope_unresolved: "The transaction scope is unresolved.",
    traceReason_current_offer_unverified: "Current offer documents are not verified.",
    traceReason_source_versions_conflict: "The applicable source version is unresolved.",
    traceReason_clarification_requested: "A clarifying question was requested; see below.",
    traceReason_assessment_withheld: "Sources were found, but assessment remains withheld.",
    traceReason_cited_answer: "This response includes cited references.",
    traceReason_legacy_trace_unavailable: "The decision details were not saved with this older response.",
    traceSlot_financing_party: "Financing party",
    traceSlot_contract_family: "Contract mechanism",
    traceSlot_cash_price: "Cash price",
    traceSlot_financed_or_final_price: "Final amount payable",
    traceSlot_down_payment: "Down payment",
    traceSlot_instalment_count: "Number of instalments",
    traceSlot_instalment_amount: "Instalment amount",
    traceSlot_additional_fees: "Additional fees"
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
    welcome: "اسأل عن أدلة أيوفي لمعاملة مالية بالعربية أو الإنجليزية.",
    welcomeKicker: "مساعد مستند إلى معايير أيوفي",
    placeholder: "اسأل عن معاملة مالية إسلامية...",
    composerHint: "أضف نوع المعاملة، والأطراف، وشروط السداد، والنقطة التي تريد فحصها بدقة.",
    ask: "اسأل مشير",
    streaming: "جارٍ التحليل...",
    emptyHistory: "لا توجد محادثات سابقة بعد.",
    conversation: "محادثة",
    evidenceStatus: "حالة الأدلة: {status}",
    captureUnknown: "تاريخ جمع المصدر وعمره: غير معروف",
    captureAge: "{source} — تاريخ الجمع: {date}؛ العمر: {age} يوم",
    evidenceClarification: "يلزم توضيح",
    evidenceInsufficient: "أدلة غير كافية",
    evidenceSources: "مصادر متاحة",
    evidenceNone: "لا توجد مصادر",
    evidenceUnknown: "حالة الأدلة غير متاحة",
    unknownSource: "مصدر غير مسمى",
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
    statusCompliant: "مدعوم بالأدلة المسترجعة",
    statusNonCompliant: "تعارضه الأدلة المسترجعة",
    statusPartiallyCompliant: "يتطلب مراجعة عالم شرعي",
    statusInsufficientData: "أدلة المصدر غير كافية",
    statusClarificationNeeded: "يحتاج إلى توضيح",
    statusFinished: "اكتمل",
    composing: "مشير يكتب الإجابة...",
    error: "خطأ",
    retry: "أعد المحاولة",
    traceTitle: "كيف تحددت هذه الاستجابة",
    traceUnderstood: "فهم الطلب على أنه",
    traceLane_described_operation: "معاملة موصوفة",
    traceLane_structure: "سؤال عن هيكل المعاملة",
    traceLane_definition: "طلب تعريف",
    traceLane_general: "طلب عام",
    traceKnown: "المعلومات المقدمة",
    traceMissing: "معلومات ما زالت مطلوبة",
    traceQuestion: "السؤال المطروح",
    traceSources: "المراجع المذكورة",
    traceNoSources: "لا توجد مراجع مذكورة لهذه الاستجابة",
    traceDecision: "ضابط الاستجابة",
    traceDecide: "تفاصيل قد تؤثر في التقييم",
    traceLegend: "الرموز تبين توافر المعلومات ولا تعني استيفاء قاعدة شرعية.",
    traceObserved: "مرصود في مصدر",
    traceReported: "ذكرتَ ذلك",
    traceUnknown: "غير معروف",
    traceConflicting: "معلومات متعارضة",
    traceMechanismUnknown: "آلية العقد غير معروفة",
    traceSlot_asset: "الأصل",
    traceSlot_seller: "البائع",
    traceSlot_sales_channel: "قناة البيع",
    traceSlot_late_payment_clause: "بند التأخر في السداد",
    traceSlot_late_fee_beneficiary: "الجهة المستفيدة من رسوم التأخير",
    traceSlot_insurance_leg: "ترتيب التأمين",
    traceSlot_ownership_risk_sequence: "تسلسل الملكية والمخاطر",
    traceSlot_early_settlement: "التسوية المبكرة",
    traceSlot_refund_terms: "شروط الاسترداد",
    traceSlot_resale_arranger: "الجهة التي ترتب إعادة البيع",
    traceSlot_underlying_sukuk_contract: "العقد الأساسي للصكوك",
    traceReason_scope_refusal: "الحكم الملزم المطلوب يتجاوز النطاق المعلوماتي.",
    traceReason_empty_request: "يلزم طرح سؤال قبل بدء التحليل.",
    traceReason_scholar_review_required: "الأدلة المتاحة ما زالت تحتاج إلى مراجعة شرعية.",
    traceReason_unsupported_asset: "المصادر المتاحة لا تثبت دعماً لحالة هذا الأصل.",
    traceReason_structure_evidence_incomplete: "الإجابة تحتاج إلى مستندات المعاملة وقاعدة معتمدة منطبقة.",
    traceReason_financing_party_unknown: "جهة التمويل غير معروفة.",
    traceReason_conflicting_user_facts: "التفاصيل المقدمة متعارضة.",
    traceReason_payment_total_discrepancy: "الإجمالي المذكور يختلف عن جدول السداد المقدم.",
    traceReason_mechanism_unknown: "آلية العقد غير مثبتة.",
    traceReason_approved_rule_evaluated_overall_gates_pending: "لا تزال الخلاصة العامة بحاجة إلى مراجعة.",
    traceReason_material_evidence_incomplete: "تنقص تفاصيل مهمة أو قواعد معتمدة.",
    traceReason_disclaimer_required: "يرجى الإقرار بنطاق المعلومات أولاً.",
    traceReason_structure_details_needed: "تحتاج تفاصيل جوهرية إلى توضيح.",
    traceReason_approved_rule_missing: "لا توجد قاعدة معتمدة منطبقة.",
    traceReason_retrieval_unavailable: "خدمة الأدلة غير متاحة.",
    traceReason_no_sources: "لا يوجد مصدر مذكور لهذه الاستجابة.",
    traceReason_definition_cited: "عُثر على تعريف في مصدر مذكور.",
    traceReason_definition_support_unavailable: "لم يُعثر على مقطع حرفي يعرّف المفهوم المطلوب.",
    traceReason_private_reasoning_requested: "يتوفر شرح موجز للأدلة؛ التفكير الداخلي الخاص غير متاح.",
    traceReason_generated_claim_unverified: "لم يُتحقق من الادعاء المولّد في المقطع المستشهد به، لذلك حُجب.",
    traceReason_literal_passage_cited: "الاقتباس المعروض يطابق المقطع المستشهد به؛ التقييم ما زال محجوبًا.",
    traceReason_purpose_needed: "يلزم توضيح الغرض من الطلب.",
    traceReason_purpose_unavailable: "الغرض من الطلب ما زال غير معلوم.",
    traceReason_scenario_switch_confirmation: "يرجى تأكيد ما إذا كان هذا شراءً منفصلًا.",
    traceReason_scenario_scope_unresolved: "نطاق المعاملة لم يُحسم.",
    traceReason_current_offer_unverified: "مستندات العرض الحالي غير موثقة.",
    traceReason_source_versions_conflict: "نسخة المصدر المناسبة لم تُحسم.",
    traceReason_clarification_requested: "طُلب توضيح؛ انظر السؤال أدناه.",
    traceReason_assessment_withheld: "عُثر على مصادر لكن التقييم ما زال معلقاً.",
    traceReason_cited_answer: "تتضمن هذه الاستجابة مراجع مذكورة.",
    traceReason_legacy_trace_unavailable: "لم تُحفظ تفاصيل القرار مع هذه الاستجابة القديمة.",
    traceSlot_financing_party: "جهة التمويل",
    traceSlot_contract_family: "آلية العقد",
    traceSlot_cash_price: "السعر النقدي",
    traceSlot_financed_or_final_price: "الإجمالي المستحق",
    traceSlot_down_payment: "المقدم",
    traceSlot_instalment_count: "عدد الأقساط",
    traceSlot_instalment_amount: "قيمة القسط",
    traceSlot_additional_fees: "الرسوم الإضافية"
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
  var failureRecorded = false;

  function failStream(message) {
    if (failureRecorded) return;
    failureRecorded = true;
    streamActive = false;
    appState.streaming = false;
    abortTypewriter();
    removeTypingIndicator();
    if (currentAssistantNode) currentAssistantNode.remove();
    currentAssistantNode = null;
    renderErrorBubble(message);
    messagesArray.push({role: "assistant", content: message, timestamp: Date.now(), status: "error", citations: []});
    persistConversation();
  }

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
      var responseRequestId = response.headers.get("X-Request-ID") || "";
      failStream(await formatHttpError(response, responseRequestId));
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
        var displayText = stripAnswerStatusPrefix(data.text || "");
        _assistantContent += displayText;
        if (!firstTokenReceived) {
          removeTypingIndicator();
          currentAssistantNode = addMessage("assistant", "");
          renderTypewriter(displayText, currentAssistantNode);
          firstTokenReceived = true;
        } else if (currentAssistantNode) {
          extendTypewriterBuffer(_assistantContent);
        }
      },

      onRetrieval: function(data) {
        addEvent(formatEvidence(data.evidence));
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
        var errorMessage = formatSafeStreamError(data, currentRequestId);
        failStream(errorMessage);
      },

      onDone: function(data) {
        streamActive = false;
        appState.streaming = false;
        abortTypewriter();
        removeTypingIndicator();
        // The final response is the committed canonical answer; tokens are provisional.
        _assistantContent = stripAnswerStatusPrefix(data.answer);
        if (!currentAssistantNode) currentAssistantNode = addMessage("assistant", _assistantContent);
        else {
          currentAssistantNode.textContent = _assistantContent;
          _applyDirection(currentAssistantNode, _assistantContent);
        }

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
        renderTrace(data.metadata && data.metadata.decision_trace, currentAssistantNode);
        renderEvidence(currentAssistantNode, data.metadata && data.metadata.evidence);
        addEvent(t("reviewComplete", {status: formatStatusLabel(data.status)}));

        var assistantContent = _assistantContent || data.answer || data.clarification_question || "";
        if (assistantContent) {
          messagesArray.push({
            role: "assistant",
            content: assistantContent,
            timestamp: Date.now(),
            status: data.status,
            citations: _assistantCitations,
            evidence: data.metadata && data.metadata.evidence,
            decision_trace: data.metadata && data.metadata.decision_trace
          });
        }
        persistConversation();
      },

      onStreamError: function(err) {
        var connectionMessage = t("connectionInterrupted") + formatRequestIdSuffix(currentRequestId);
        failStream(connectionMessage);
      },

      onComplete: function() {
        if (streamActive) {
          failStream(t("connectionInterrupted") + formatRequestIdSuffix(currentRequestId));
        }
        send.disabled = false;
        send.textContent = t("ask");
      }
    });
  } catch (error) {
    var requestMessage = t("serviceUnavailable");
    failStream(requestMessage);
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

function stripAnswerStatusPrefix(text) {
  return String(text || "").replace(
    /^(?:COMPLIANT|NON_COMPLIANT|NON-COMPLIANT|PARTIALLY_COMPLIANT|CONDITIONALLY COMPLIANT|SUPPORTED_BY_RETRIEVED_EVIDENCE|CONTRADICTED_BY_RETRIEVED_EVIDENCE|REQUIRES_SCHOLAR_REVIEW|INSUFFICIENT_DATA|CLARIFICATION_NEEDED)\s*:\s*/i,
    ""
  );
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
}

function welcomeCardMarkup() {
  return [
    '<div class="welcome-kicker">' + escapeHtml(t("welcomeKicker")) + '</div>',
    '<div class="welcome-title">' + escapeHtml(t("welcome")) + '</div>'
  ].join("");
}

function refreshWelcomeCards() {
  var cards = messages.querySelectorAll(".welcome-card[data-welcome='true']");
  for (var i = 0; i < cards.length; i++) {
    cards[i].innerHTML = welcomeCardMarkup();
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
