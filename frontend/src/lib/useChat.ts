import { useEffect, useState } from "react";

import { ApiError, request } from "./api";
import type { ChatMessage } from "./types";

type Messages = { messages: ChatMessage[] };

/** The conversation. `onSettled` runs after every send, because actions may have executed. */
export function useChat(onSettled: () => void) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [pending, setPending] = useState<string | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let mounted = true;
    request<Messages>("/api/chat").then(
      (body) => {
        // Anything sent while this loaded is newer: keep it.
        if (mounted) setMessages((current) => (current.length ? current : body.messages));
      },
      () => {
        if (mounted) setError("Chat history is unavailable.");
      },
    );
    return () => {
      mounted = false;
    };
  }, []);

  /** Resolves true when the message was answered, so the input can be cleared. */
  async function send(text: string): Promise<boolean> {
    setPending(text);
    setError("");
    try {
      const body = await request<Messages>("/api/chat", "POST", { message: text });
      setMessages((current) => [...current, ...body.messages]);
      return true;
    } catch (failure) {
      setError(
        failure instanceof ApiError
          ? failure.message
          : "No reply. Check your positions before trying again.",
      );
      return false;
    } finally {
      setPending(null);
      onSettled();
    }
  }

  return { messages, pending, error, send };
}
