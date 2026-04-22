function backendUrl() {
  const url = process.env.NEXT_PUBLIC_BACKEND_URL;
  return (url || "http://localhost:8000").replace(/\/$/, "");
}

export async function streamChat({ message, session_id, onToken }) {
  const res = await fetch(`${backendUrl()}/api/v1/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id })
  });
  if (!res.ok || !res.body) {
    const text = await res.text().catch(() => "");
    throw new Error(text || `HTTP ${res.status}`);
  }

  // SSE parsing over fetch streaming response
  const reader = res.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  function extractNextEvent() {
    // Support both \n\n and \r\n\r\n
    const m = buffer.match(/(\r?\n){2}/);
    if (!m || m.index == null) return null;
    const endIdx = m.index;
    const sepLen = m[0].length;
    const rawEvent = buffer.slice(0, endIdx);
    buffer = buffer.slice(endIdx + sepLen);
    return rawEvent;
  }

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // Events separated by blank line
    let rawEvent;
    while ((rawEvent = extractNextEvent()) != null) {
      const lines = rawEvent.split(/\r?\n/).map((l) => l.trimEnd());
      const eventLine = lines.find((l) => l.startsWith("event:"));
      const eventName = eventLine ? eventLine.slice(6).trim() : "";

      const dataLines = lines
        .filter((l) => l.startsWith("data:"))
        .map((l) => l.slice(5).trim());
      if (dataLines.length === 0) continue;

      let payload;
      try {
        payload = JSON.parse(dataLines.join("\n"));
      } catch {
        continue;
      }

      if (payload?.type === "token" && typeof payload.text === "string") {
        onToken(payload.text);
      }

      // Stop early on done/error even if connection lingers.
      if (eventName === "done" || payload?.type === "done") return;
      if (eventName === "error" || payload?.type === "error") {
        throw new Error(payload?.message || "Backend error");
      }
    }
  }
}

