/**
 * Parse SSE (Server-Sent Events) text into structured event objects.
 * @param {string} text - Raw SSE response text with "event:" and "data:" lines
 * @returns {Array<{type: string, data: object}>} Parsed events
 */
function parseSse(text) {
  return text
    .trim()
    .split("\n\n")
    .map(function(block) {
      var event = {};
      var lines = block.split("\n");
      for (var i = 0; i < lines.length; i++) {
        var line = lines[i];
        if (line.startsWith("event: ")) event.type = line.slice(7);
        if (line.startsWith("data: ")) event.data = JSON.parse(line.slice(6));
      }
      return event;
    })
    .filter(function(event) { return event.type; });
}

/**
 * Process an SSE stream from a ReadableStream reader, calling lifecycle
 * callbacks for each event type as it arrives.
 *
 * The conversation_history for the current thread is attached to the fetch
 * POST body upstream (in app.js submitQuery) so the backend receives full
 * multi-turn context with every request.
 *
 * @param {ReadableStreamDefaultReader} reader - Response body reader
 * @param {object} callbacks - Event callbacks
 * @param {function} callbacks.onStarted - Called on 'started' event
 * @param {function} callbacks.onToken - Called on 'token' event with data.text
 * @param {function} callbacks.onRetrieval - Called on 'retrieval' event with data
 * @param {function} callbacks.onCitation - Called on 'citation' event with data
 * @param {function} callbacks.onError - Called on 'error' event with data
 * @param {function} callbacks.onDone - Called on 'done' event with data
 * @param {function} callbacks.onStreamError - Called on fetch/parse error
 * @param {function} callbacks.onComplete - Called when stream fully consumed
 * @param {Array} [conversationHistory] - Optional conversation history array
 *        for callbacks that need access to the current thread context.
 */
function processSseStream(reader, callbacks, conversationHistory) {
  var decoder = new TextDecoder();
  var buffer = "";
  var reading = true;
  var terminal = false;

  function dispatch(block) {
    if (terminal) return;
    var type = processBlock(block, callbacks);
    terminal = type === "done" || type === "error";
  }

  function readChunk() {
    if (!reading) return;
    reader.read().then(function(result) {
      if (result.done) {
        reading = false;
        buffer += decoder.decode();
        // Flush any remaining event in the buffer
        if (buffer.trim().length > 0) {
          dispatch(buffer);
        }
        if (!terminal) throw new Error("Stream ended before its final response");
        if (callbacks.onComplete) callbacks.onComplete();
        return;
      }

      buffer += decoder.decode(result.value, { stream: true });

      // Split on double newline (SSE event boundary)
      var parts = buffer.split(/\r?\n\r?\n/);
      // Keep the last (possibly incomplete) part in the buffer
      buffer = parts.pop() || "";

      for (var i = 0; i < parts.length; i++) {
        dispatch(parts[i]);
      }

      readChunk();
    }).catch(function(err) {
      reading = false;
      if (!terminal && callbacks.onStreamError) callbacks.onStreamError(err);
      if (callbacks.onComplete) callbacks.onComplete();
    });
  }

  readChunk();
}

/**
 * Process a single SSE block (one event) and dispatch to the appropriate callback.
 * @param {string} block - A single SSE event block
 * @param {object} callbacks - Event callbacks (same as processSseStream)
 */
function processBlock(block, callbacks) {
  var eventType = "";
  var eventData = null;
  var lines = block.split(/\r?\n/);
  var dataLines = [];

  for (var i = 0; i < lines.length; i++) {
    var line = lines[i];
    if (line.startsWith("event: ")) eventType = line.slice(7);
    if (line.startsWith("data: ")) {
      dataLines.push(line.slice(6));
    }
  }

  if (!eventType) return;
  eventData = JSON.parse(dataLines.join("\n"));
  if (!eventData || typeof eventData !== "object" || Array.isArray(eventData)) {
    throw new Error("Invalid stream event payload");
  }
  if (eventType === "done" && (typeof eventData.answer !== "string" || !eventData.answer.trim() ||
      ["COMPLIANT", "NON_COMPLIANT", "PARTIALLY_COMPLIANT", "INSUFFICIENT_DATA", "CLARIFICATION_NEEDED"].indexOf(eventData.status) < 0)) {
    throw new Error("Invalid final stream response");
  }

  switch (eventType) {
    case "started":
      if (callbacks.onStarted) callbacks.onStarted(eventData || {});
      break;
    case "token":
      if (callbacks.onToken) callbacks.onToken(eventData || {});
      break;
    case "retrieval":
      if (callbacks.onRetrieval) callbacks.onRetrieval(eventData || {});
      break;
    case "citation":
      if (callbacks.onCitation) callbacks.onCitation(eventData || {});
      break;
    case "error":
      if (callbacks.onError) callbacks.onError(eventData || {});
      break;
    case "done":
      if (callbacks.onDone) callbacks.onDone(eventData || {});
      break;
    default:
      break;
  }
  return eventType;
}
