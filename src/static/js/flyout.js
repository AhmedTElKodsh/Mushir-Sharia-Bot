/**
 * Citation flyout panel (P2-S5).
 * Right-side overlay panel displaying AAOIFI citation details.
 *
 * API:
 *   Flyout.open(citation)   — opens the flyout with citation data
 *   Flyout.close()          — closes the flyout, restores focus
 *   Flyout.isOpen()         — returns true if the flyout is currently open
 *
 * Handles:
 *   - Backdrop overlay (tap to close)
 *   - Escape key to close
 *   - Focus trap while open
 *   - Content swap (tap different anchors)
 *   - prefers-reduced-motion: instant open/close, no slide
 *   - Mobile responsive (85 % width at < 640px)
 */
var Flyout = Flyout || {};

(function () {
  /** @type {HTMLElement|null} */
  var flyoutEl = null;

  /** @type {HTMLElement|null} */
  var backdropEl = null;

  /** @type {Element|null} */
  var previousFocusEl = null;

  /** Focusable element selector within the flyout */
  var FOCUSABLE =
    'a[href], button, textarea, input, select, [tabindex]:not([tabindex="-1"])';

  // ---- DOM construction (lazy, on first open) ---------------------------

  /**
   * Create the flyout DOM structure if it does not already exist.
   * Backdrop + panel + close button + focus-trap sentinels.
   */
  function _ensureDOM() {
    if (flyoutEl) return;

    /* ---- Backdrop ---- */
    backdropEl = document.createElement("div");
    backdropEl.className = "flyout-backdrop";
    backdropEl.setAttribute("aria-hidden", "true");
    document.body.appendChild(backdropEl);

    /* ---- Flyout panel ---- */
    flyoutEl = document.createElement("aside");
    flyoutEl.className = "flyout-panel";
    flyoutEl.setAttribute("role", "dialog");
    flyoutEl.setAttribute("aria-modal", "true");
    flyoutEl.setAttribute("aria-label", "Citation details");

    /* Close button */
    var closeBtn = document.createElement("button");
    closeBtn.className = "flyout-close";
    closeBtn.setAttribute("aria-label", "Close citation");
    closeBtn.innerHTML = "&times;";
    closeBtn.addEventListener("click", close);
    flyoutEl.appendChild(closeBtn);

    /* Content area — filled dynamically on open() */
    var content = document.createElement("div");
    content.className = "flyout-content";
    flyoutEl.appendChild(content);

    /* Focus-trap sentinel (start) — invisible, catches Shift+Tab from first element */
    var sentinelStart = document.createElement("span");
    sentinelStart.className = "flyout-sentinel";
    sentinelStart.tabIndex = 0;
    sentinelStart.setAttribute("aria-hidden", "true");
    sentinelStart.addEventListener("focus", function () {
      _focusLast();
    });
    flyoutEl.insertBefore(sentinelStart, flyoutEl.firstChild);

    /* Focus-trap sentinel (end) — catches Tab from last element */
    var sentinelEnd = document.createElement("span");
    sentinelEnd.className = "flyout-sentinel";
    sentinelEnd.tabIndex = 0;
    sentinelEnd.setAttribute("aria-hidden", "true");
    sentinelEnd.addEventListener("focus", function () {
      _focusFirst();
    });
    flyoutEl.appendChild(sentinelEnd);

    document.body.appendChild(flyoutEl);

    /* Backdrop click → close */
    backdropEl.addEventListener("click", close);

    /* Escape key → close (global listener, only acts when flyout is open) */
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && isOpen()) {
        close();
        e.preventDefault();
      }
    });
  }

  // ---- Focus helpers ----------------------------------------------------

  /** Focus the first visible focusable element inside the flyout. */
  function _focusFirst() {
    var focusable = flyoutEl.querySelectorAll(FOCUSABLE);
    for (var i = 0; i < focusable.length; i++) {
      if (focusable[i].offsetParent !== null && focusable[i].tabIndex >= 0) {
        focusable[i].focus();
        return;
      }
    }
  }

  /** Focus the last visible focusable element inside the flyout. */
  function _focusLast() {
    var focusable = flyoutEl.querySelectorAll(FOCUSABLE);
    for (var i = focusable.length - 1; i >= 0; i--) {
      if (focusable[i].offsetParent !== null && focusable[i].tabIndex >= 0) {
        focusable[i].focus();
        return;
      }
    }
  }

  // ---- Core API ---------------------------------------------------------

  /**
   * Open the flyout and display citation details.
   * Creates the DOM on first call (lazy init).
   * Saves the currently focused element for restoration on close.
   *
   * @param {Object} citation
   * @param {string} [citation.standard]  — AAOIFI standard name / number
   * @param {string} [citation.section]   — Section number
   * @param {string} [citation.title]     — Section title
   * @param {string} [citation.excerpt]   — Excerpt text
   */
  function open(citation) {
    _ensureDOM();

    previousFocusEl = document.activeElement;

    /* ---- Build citation card ---- */
    var content = flyoutEl.querySelector(".flyout-content");
    content.innerHTML = "";

    var card = document.createElement("div");
    card.className = "citation-card";

    /* Standard name */
    var standardEl = document.createElement("div");
    standardEl.className = "citation-standard";
    standardEl.textContent = citation.standard || "AAOIFI Standard";
    card.appendChild(standardEl);

    /* Section number */
    if (citation.section) {
      var sectionEl = document.createElement("div");
      sectionEl.className = "citation-section";
      sectionEl.textContent = "\u00a7 " + citation.section;
      card.appendChild(sectionEl);
    }

    /* Title / excerpt — prefer excerpt, fall back to title, then raw text */
    var bodyText =
      citation.excerpt || citation.title || citation.text || "";
    if (bodyText) {
      var bodyEl = document.createElement("div");
      bodyEl.className = "citation-excerpt";
      bodyEl.textContent = bodyText;
      card.appendChild(bodyEl);
    }

    content.appendChild(card);

    /* ---- Show ---- */
    document.body.classList.add("flyout-open");
    flyoutEl.setAttribute("aria-hidden", "false");
    if (backdropEl) backdropEl.classList.add("visible");

    /* Focus the close button (first meaningful focusable) */
    var closeBtn = flyoutEl.querySelector(".flyout-close");
    if (closeBtn) closeBtn.focus();
  }

  /**
   * Close the flyout and restore focus to the previously active element.
   * Safe to call when the flyout is not open.
   */
  function close() {
    if (!flyoutEl) return;

    document.body.classList.remove("flyout-open");
    flyoutEl.setAttribute("aria-hidden", "true");
    if (backdropEl) backdropEl.classList.remove("visible");

    /* Restore focus to the element that had it before the flyout opened */
    if (previousFocusEl) {
      try {
        previousFocusEl.focus();
      } catch (_) {
        /* Element may have been removed — safe to ignore */
      }
      previousFocusEl = null;
    }
  }

  /**
   * Check whether the citation flyout is currently open.
   * @returns {boolean}
   */
  function isOpen() {
    return document.body.classList.contains("flyout-open");
  }

  // ---- Public API -------------------------------------------------------
  Flyout.open = open;
  Flyout.close = close;
  Flyout.isOpen = isOpen;
})();
