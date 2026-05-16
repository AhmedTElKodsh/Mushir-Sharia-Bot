/**
 * StorageAdapter — testable wrapper around the Web Storage API.
 *
 * - Backs the disclaimer banner persistence (P1-S3).
 * - Provides a schemaVersion field that enables safe migration from N → N+1.
 * - Ships MockStorage (Map-backed) for unit tests.
 *
 * Usage:
 *   var store = new StorageAdapter();
 *   store.set("my_key", "my_value");
 *   console.log(store.get("my_key"));   // "my_value"
 *
 * Testing:
 *   var mock = new MockStorage();
 *   var store = new StorageAdapter(mock);
 */

/* ===================================================================
 * StorageAdapter
 * =================================================================== */

/**
 * @param {Storage} [storage=sessionStorage] — Any object exposing
 *   getItem / setItem / removeItem / clear (Web Storage API).
 * @param {number} [schemaVersion=1] — Opaque version marker for future
 *   data migration. Bump when the shape of persisted values changes.
 */
function StorageAdapter(storage, schemaVersion) {
  this._storage = storage || sessionStorage;
  this.schemaVersion = schemaVersion !== undefined ? schemaVersion : 1;
}

/**
 * Retrieve a value by key.
 * @param {string} key
 * @returns {string|null}
 */
StorageAdapter.prototype.get = function (key) {
  try {
    return this._storage.getItem(key);
  } catch (_) {
    return null;
  }
};

/**
 * Persist a value.
 * @param {string} key
 * @param {string} value
 */
StorageAdapter.prototype.set = function (key, value) {
  try {
    this._storage.setItem(key, String(value));
  } catch (_) {
    /* Storage full, quota exceeded, or unavailable — silently ignore. */
  }
};

/**
 * Remove a single key.
 * @param {string} key
 */
StorageAdapter.prototype.remove = function (key) {
  try {
    this._storage.removeItem(key);
  } catch (_) {
    /* noop */
  }
};

/**
 * Clear all keys managed by the underlying storage.
 */
StorageAdapter.prototype.clear = function () {
  try {
    this._storage.clear();
  } catch (_) {
    /* noop */
  }
};

/**
 * Placeholder for future schema migrations.
 *
 * Subclasses or future versions override this to transform persisted
 * data between schemaVersion N and N+1.  The base implementation is a
 * no-op that returns true to indicate "nothing to migrate".
 *
 * @param {number} fromVersion
 * @param {number} toVersion
 * @returns {boolean} true if migration succeeded (or was unnecessary).
 */
StorageAdapter.prototype.migrate = function (fromVersion, toVersion) {
  /* Base implementation: no migrations defined yet. */
  return true;
};

/* ===================================================================
 * MockStorage — Map-backed substitute implementing the Web Storage API
 * =================================================================== */

/**
 * In-memory storage that mirrors the sessionStorage / localStorage API
 * using a plain Map.  Useful for unit-testing StorageAdapter without
 * a browser environment or for isolating test state.
 */
function MockStorage() {
  this._map = {};
}

MockStorage.prototype.getItem = function (key) {
  return Object.prototype.hasOwnProperty.call(this._map, key)
    ? this._map[key]
    : null;
};

MockStorage.prototype.setItem = function (key, value) {
  this._map[key] = String(value);
};

MockStorage.prototype.removeItem = function (key) {
  delete this._map[key];
};

MockStorage.prototype.clear = function () {
  this._map = {};
};

/* ===================================================================
 * Disclaimer persistence — convenience API
 * =================================================================== */

var STORAGE_KEY_DISCLAIMER_DISMISSED = "mushir_disclaimer_dismissed";

/**
 * Backward-compatible legacy API.
 *
 * Keeps existing callers (app.js disclaimer handler, any third-party
 * scripts that reference ``Storage.*``) working without changes.
 *
 * @deprecated Use ``StorageAdapter`` directly in new code.
 */
var Storage = Storage || {};

Storage.isDisclaimerDismissed = function () {
  return sessionStorage.getItem(STORAGE_KEY_DISCLAIMER_DISMISSED) === "true";
};

Storage.dismissDisclaimer = function () {
  sessionStorage.setItem(STORAGE_KEY_DISCLAIMER_DISMISSED, "true");
};

Storage.resetDisclaimer = function () {
  sessionStorage.removeItem(STORAGE_KEY_DISCLAIMER_DISMISSED);
};

/* ===================================================================
 * Conversation persistence
 * =================================================================== */

/** Fixed storage key for the legacy current session's conversation data. */
var CONVERSATION_KEY = "mushir_conversation";
var CONVERSATION_INDEX_KEY = "mushir_conversations_index";
var CONVERSATION_ITEM_PREFIX = "mushir_conversation_";

/**
 * Store a JavaScript value as JSON.
 * Handles quota errors gracefully (console.warn, app continues).
 * @param {string} key
 * @param {*} value
 */
StorageAdapter.prototype.setObject = function (key, value) {
  try {
    this._storage.setItem(key, JSON.stringify(value));
  } catch (e) {
    console.warn("StorageAdapter: quota exceeded or unavailable \u2014", e.message);
  }
};

/**
 * Retrieve and parse a JSON value from storage.
 * @param {string} key
 * @returns {*|null}
 */
StorageAdapter.prototype.getObject = function (key) {
  try {
    var raw = this._storage.getItem(key);
    return raw ? JSON.parse(raw) : null;
  } catch (_) {
    return null;
  }
};

/**
 * Persist the full conversation array.
 * Schema: { messages: [{role, content, timestamp, status, citations}], session_id, timestamp }
 *
 * @param {string} sessionId
 * @param {Array} messages
 */
StorageAdapter.prototype.saveConversation = function (sessionId, messages) {
  var title = this._conversationTitle(messages);
  var data = {
    messages: messages,
    session_id: sessionId,
    title: title,
    timestamp: Date.now()
  };
  this.setObject(CONVERSATION_ITEM_PREFIX + sessionId, data);
  this.setObject(CONVERSATION_KEY, data);
  this._upsertConversationIndex({
    session_id: sessionId,
    title: title,
    timestamp: data.timestamp,
    message_count: messages.length
  });
};

/**
 * Restore the persisted conversation object, or null if none exists.
 * @param {string} sessionId — Used for forward-compatibility; the key name is fixed.
 * @returns {{messages: Array, session_id: string, timestamp: number}|null}
 */
StorageAdapter.prototype.restoreConversation = function (sessionId) {
  if (sessionId) {
    return this.getObject(CONVERSATION_ITEM_PREFIX + sessionId);
  }
  return this.getObject(CONVERSATION_KEY);
};

/**
 * Remove the conversation data from storage.
 */
StorageAdapter.prototype.clearConversation = function () {
  try {
    this._storage.removeItem(CONVERSATION_KEY);
  } catch (_) {
    /* noop */
  }
};

StorageAdapter.prototype.listConversations = function () {
  var index = this.getObject(CONVERSATION_INDEX_KEY);
  if (!Array.isArray(index)) return [];
  return index.sort(function (a, b) {
    return (b.timestamp || 0) - (a.timestamp || 0);
  });
};

StorageAdapter.prototype.deleteConversation = function (sessionId) {
  this.remove(CONVERSATION_ITEM_PREFIX + sessionId);
  var index = this.listConversations().filter(function (item) {
    return item.session_id !== sessionId;
  });
  this.setObject(CONVERSATION_INDEX_KEY, index);
};

StorageAdapter.prototype._upsertConversationIndex = function (entry) {
  var index = this.listConversations().filter(function (item) {
    return item.session_id !== entry.session_id;
  });
  index.unshift(entry);
  this.setObject(CONVERSATION_INDEX_KEY, index.slice(0, 30));
};

StorageAdapter.prototype._conversationTitle = function (messages) {
  var fallback = "New conversation";
  if (!Array.isArray(messages)) return fallback;
  for (var i = 0; i < messages.length; i++) {
    if (messages[i].role === "user" && messages[i].content) {
      return messages[i].content.slice(0, 72);
    }
  }
  return fallback;
};
