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
 */
function processSseStream(reader, callbacks) {
  var decoder = new TextDecoder();
  var buffer = "";
  var reading = true;

  function readChunk() {
    if (!reading) return;
    reader.read().then(function(result) {
      if (result.done) {
        reading = false;
        // Flush any remaining event in the buffer
        if (buffer.trim().length > 0) {
          processBlock(buffer, callbacks);
        }
        if (callbacks.onComplete) callbacks.onComplete();
        return;
      }

      buffer += decoder.decode(result.value, { stream: true });

      // Split on double newline (SSE event boundary)
      var parts = buffer.split("\n\n");
      // Keep the last (possibly incomplete) part in the buffer
      buffer = parts.pop() || "";

      for (var i = 0; i < parts.length; i++) {
        processBlock(parts[i], callbacks);
      }

      readChunk();
    }).catch(function(err) {
      reading = false;
      if (callbacks.onStreamError) callbacks.onStreamError(err);
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
  var lines = block.split("\n");

  for (var i = 0; i < lines.length; i++) {
    var line = lines[i];
    if (line.startsWith("event: ")) eventType = line.slice(7);
    if (line.startsWith("data: ")) {
      try {
        eventData = JSON.parse(line.slice(6));
      } catch (e) {
        eventData = { raw: line.slice(6) };
      }
    }
  }

  if (!eventType) return;

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
}
