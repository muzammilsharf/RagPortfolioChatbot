import { useEffect, useMemo, useRef, useState } from "react";
import DOMPurify from "isomorphic-dompurify";
import { marked } from "marked";

import { useSessionId } from "@/hooks/useSessionId";
import { streamChat } from "@/utils/streamChat";

function renderMarkdown(md) {
  const html = marked.parse(md ?? "");
  return DOMPurify.sanitize(html);
}

export default function Chat() {
  const sessionId = useSessionId();
  const [messages, setMessages] = useState([
    { role: "assistant", content: "Hi Welcome! Ask me anything about my portfolio." }
  ]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const scrollRef = useRef(null);

  const canSend = useMemo(() => input.trim().length > 0 && !isStreaming, [input, isStreaming]);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isStreaming]);

  async function onSend(e) {
    e.preventDefault();
    const text = input.trim();
    if (!text || !sessionId || isStreaming) return;

    setInput("");
    setIsStreaming(true);

    setMessages((m) => [...m, { role: "user", content: text }, { role: "assistant", content: "" }]);

    try {
      await streamChat({
        message: text,
        session_id: sessionId,
        onToken: (tok) => {
          setMessages((m) => {
            const copy = [...m];
            const last = copy[copy.length - 1];
            copy[copy.length - 1] = { ...last, content: (last.content || "") + tok };
            return copy;
          });
        }
      });
    } catch (err) {
      const msg =
        (err && typeof err === "object" && "message" in err && typeof err.message === "string"
          ? err.message
          : "") || "Unknown error";
      setMessages((m) => {
        const copy = [...m];
        copy[copy.length - 1] = {
          role: "assistant",
          content: `Ooops! ${msg}. 
                  Please try refreshing the chat or sending your message again. If this keeps happening, reach out out to me through sharfmuzamil@gmail.com`
        };
        return copy;
      });
    } finally {
      setIsStreaming(false);
    }
  }

  return (
    <div className="chat">
      <div className="messages">
        {messages.map((msg, idx) => (
          <div key={idx} className={`bubble ${msg.role}`}>
            <div
              className="bubbleContent"
              dangerouslySetInnerHTML={{ __html: renderMarkdown(msg.content) }}
            />
          </div>
        ))}
        <div ref={scrollRef} />
      </div>

      <form className="composer" onSubmit={onSend}>
        <input
          className="input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type your question…"
        />
        <button className="send" disabled={!canSend} type="submit">
          {isStreaming ? "…" : "Send"}
        </button>
      </form>
    </div>
  );
}

