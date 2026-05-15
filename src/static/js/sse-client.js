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
