import { useEffect, useState } from "react";
import { v4 as uuidv4 } from "uuid";

export function useSessionId() {
  const [sessionId, setSessionId] = useState(null);

  useEffect(() => {
    try {
      const existing = window.sessionStorage.getItem("portfolio_session_id");
      if (existing) {
        setSessionId(existing);
        return;
      }
      const id = uuidv4();
      window.sessionStorage.setItem("portfolio_session_id", id);
      setSessionId(id);
    } catch {
      // If sessionStorage is blocked, still work with an ephemeral id.
      setSessionId(uuidv4());
    }
  }, []);

  return sessionId;
}

