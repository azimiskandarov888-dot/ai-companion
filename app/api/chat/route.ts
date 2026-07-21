import Anthropic from "@anthropic-ai/sdk";
import { COMPANION_SYSTEM_PROMPT } from "@/lib/companion";

// Run on the Node.js runtime so the Anthropic SDK works as expected.
export const runtime = "nodejs";
// Never cache chat responses.
export const dynamic = "force-dynamic";

const MODEL = process.env.ANTHROPIC_MODEL || "claude-opus-4-8";

// Keep the last N turns to bound cost/latency. Adjust to taste.
const MAX_HISTORY = 40;

type Role = "user" | "assistant";
interface IncomingMessage {
  role: Role;
  content: string;
}

/** Only allow well-formed user/assistant text turns through to the API. */
function sanitize(messages: unknown): IncomingMessage[] {
  if (!Array.isArray(messages)) return [];
  const cleaned = messages
    .filter(
      (m): m is IncomingMessage =>
        !!m &&
        (m.role === "user" || m.role === "assistant") &&
        typeof m.content === "string" &&
        m.content.trim().length > 0,
    )
    .map((m) => ({ role: m.role, content: m.content }));
  return cleaned.slice(-MAX_HISTORY);
}

export async function POST(req: Request): Promise<Response> {
  if (!process.env.ANTHROPIC_API_KEY) {
    return Response.json(
      {
        error:
          "The server is missing ANTHROPIC_API_KEY. Add it to .env.local and restart.",
      },
      { status: 500 },
    );
  }

  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return Response.json({ error: "Invalid JSON body." }, { status: 400 });
  }

  const messages = sanitize((body as { messages?: unknown })?.messages);
  if (messages.length === 0) {
    return Response.json(
      { error: "Send at least one message." },
      { status: 400 },
    );
  }

  const client = new Anthropic();

  const encoder = new TextEncoder();
  const stream = new ReadableStream<Uint8Array>({
    async start(controller) {
      try {
        const claudeStream = client.messages.stream({
          model: MODEL,
          max_tokens: 1024,
          system: COMPANION_SYSTEM_PROMPT,
          messages,
        });

        for await (const event of claudeStream) {
          if (
            event.type === "content_block_delta" &&
            event.delta.type === "text_delta"
          ) {
            controller.enqueue(encoder.encode(event.delta.text));
          }
        }
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Unexpected error.";
        // Surface the error inline so the UI can show it to the user.
        controller.enqueue(
          encoder.encode(`\n\n[error] ${message}`),
        );
      } finally {
        controller.close();
      }
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "Cache-Control": "no-cache, no-transform",
    },
  });
}
