"use client";

import { useEffect, useRef, useState } from "react";

const COMPANION_NAME = process.env.NEXT_PUBLIC_COMPANION_NAME || "Aria";

interface Message {
  role: "user" | "assistant";
  content: string;
}

const SUGGESTIONS = [
  "How was your day going?",
  "I need to think something through",
  "Tell me something interesting",
  "I'm feeling a bit stuck",
];

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const scrollRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to the newest message.
  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, loading]);

  // Auto-grow the textarea.
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [input]);

  async function send(text: string) {
    const trimmed = text.trim();
    if (!trimmed || loading) return;

    const nextMessages: Message[] = [
      ...messages,
      { role: "user", content: trimmed },
    ];
    setMessages(nextMessages);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: nextMessages }),
      });

      if (!res.ok || !res.body) {
        const data = await res.json().catch(() => null);
        throw new Error(
          data?.error || `Request failed (${res.status}). Try again.`,
        );
      }

      // Start an empty assistant message we fill in as tokens stream in.
      setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

      const reader = res.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        setMessages((prev) => {
          const copy = [...prev];
          const last = copy[copy.length - 1];
          if (last && last.role === "assistant") {
            copy[copy.length - 1] = {
              ...last,
              content: last.content + chunk,
            };
          }
          return copy;
        });
      }
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Something went wrong.";
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `Sorry — I couldn't reach my brain just now. (${message})`,
        },
      ]);
    } finally {
      setLoading(false);
      textareaRef.current?.focus();
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    void send(input);
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void send(input);
    }
  }

  const initial = COMPANION_NAME.charAt(0).toUpperCase();
  const isEmpty = messages.length === 0;
  // Show the typing indicator only while we wait for the first token.
  const waitingForFirstToken =
    loading &&
    (messages.length === 0 ||
      messages[messages.length - 1].role === "user");

  return (
    <div className="app">
      <header className="header">
        <div className="avatar">{initial}</div>
        <div className="header-text">
          <h1>{COMPANION_NAME}</h1>
          <p>
            <span className="status-dot" />
            here for you
          </p>
        </div>
      </header>

      <div className="messages" ref={scrollRef}>
        {isEmpty ? (
          <div className="welcome">
            <h2>Hi, I&apos;m {COMPANION_NAME} 👋</h2>
            <p>
              I&apos;m your companion — someone to talk to, think out loud with,
              or just pass the time. What&apos;s on your mind?
            </p>
            <div className="suggestions">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  className="chip"
                  onClick={() => void send(s)}
                  type="button"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((m, i) => (
            <div key={i} className={`row ${m.role}`}>
              <div className="bubble">{m.content}</div>
            </div>
          ))
        )}

        {waitingForFirstToken && (
          <div className="row assistant">
            <div className="bubble">
              <div className="typing">
                <span />
                <span />
                <span />
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="composer">
        <form onSubmit={handleSubmit}>
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={`Message ${COMPANION_NAME}…`}
            rows={1}
            disabled={loading}
          />
          <button
            className="send"
            type="submit"
            disabled={loading || input.trim().length === 0}
            aria-label="Send message"
          >
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M22 2 11 13" />
              <path d="M22 2 15 22l-4-9-9-4 20-7z" />
            </svg>
          </button>
        </form>
        <div className="hint">
          Enter to send · Shift+Enter for a new line
        </div>
      </div>
    </div>
  );
}
