/**
 * Message persistence — sessionStorage API.
 * Reserved for Phase 2-S3 implementation.
 */

var Storage = Storage || {};

/** Key for disclaimer dismissal flag in sessionStorage. */
var STORAGE_KEY_DISCLAIMER_DISMISSED = "mushir_disclaimer_dismissed";

/**
 * Check whether the user has dismissed the disclaimer banner this session.
 * @returns {boolean}
 */
Storage.isDisclaimerDismissed = function () {
  return sessionStorage.getItem(STORAGE_KEY_DISCLAIMER_DISMISSED) === "true";
};

/**
 * Mark the disclaimer banner as dismissed for the current session.
 */
Storage.dismissDisclaimer = function () {
  sessionStorage.setItem(STORAGE_KEY_DISCLAIMER_DISMISSED, "true");
};

/**
 * Reset the disclaimer-dismissed flag so the banner reappears.
 * Called when user clicks "New Chat".
 */
Storage.resetDisclaimer = function () {
  sessionStorage.removeItem(STORAGE_KEY_DISCLAIMER_DISMISSED);
};
