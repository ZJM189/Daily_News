"use client";

import {
  FormEvent,
  useEffect,
  useRef,
  useState
} from "react";
import {
  ArrowUpRight,
  Bot,
  LoaderCircle,
  MessageCircle,
  Plus,
  SendHorizontal,
  Sparkles,
  X
} from "lucide-react";
import { useRouter } from "next/navigation";
import {
  createLibraryChatThread,
  listLibraryChatMessages,
  listLibraryChatThreads,
  streamLibraryChatMessage
} from "../../lib/api";
import type {
  LibraryChatMessage,
  LibraryChatResultPayload,
  LibraryChatStreamEvent,
  LibraryChatThread,
  LibraryItem
} from "../../lib/types";

const EXAMPLE_PROMPTS = ["最近 7 天 RAG 相关论文", "GitHub 上高分 Agent 项目", "总结这些结果"];
const ASSISTANT_INTRO =
  "我可以按自然语言查询已入库的 AI 论文、开源项目、产品发布和产业动态。";

type ChatMessageView = LibraryChatMessage & {
  pending?: boolean;
  failed?: boolean;
};

export function LibraryChatWidget() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [threads, setThreads] = useState<LibraryChatThread[]>([]);
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessageView[]>([]);
  const [input, setInput] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadingThreads, setLoadingThreads] = useState(false);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const messagesRef = useRef<HTMLDivElement>(null);
  const activeThreadIdRef = useRef<string | null>(null);
  const hydrateRequestRef = useRef(0);
  const messageLoadRequestRef = useRef(0);

  useEffect(() => {
    if (!open) return;
    void hydrateChat();
  }, [open]);

  useEffect(() => {
    activeThreadIdRef.current = activeThreadId;
  }, [activeThreadId]);

  useEffect(() => {
    if (!open) return;
    inputRef.current?.focus();
  }, [open, activeThreadId]);

  useEffect(() => {
    messagesRef.current?.scrollTo({
      top: messagesRef.current.scrollHeight,
      behavior: "smooth"
    });
  }, [messages, status, open]);

  useEffect(() => {
    if (!open) return;
    function handleKeyDown(event: globalThis.KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open]);

  async function hydrateChat() {
    const requestId = ++hydrateRequestRef.current;
    setLoadingThreads(true);
    setError(null);
    try {
      const loadedThreads = await listLibraryChatThreads();
      if (requestId !== hydrateRequestRef.current) return;
      setThreads(loadedThreads);
      const preferredThreadId = activeThreadIdRef.current;
      const nextThread = loadedThreads.find((thread) => thread.id === preferredThreadId) ?? loadedThreads[0];
      if (nextThread) {
        setActiveThreadId(nextThread.id);
        await loadMessages(nextThread.id);
      } else {
        const createdThread = await createLibraryChatThread();
        if (requestId !== hydrateRequestRef.current) return;
        setThreads([createdThread]);
        setActiveThreadId(createdThread.id);
        setMessages([]);
      }
    } catch (err) {
      if (requestId === hydrateRequestRef.current) {
        setError(err instanceof Error ? err.message : "聊天记录加载失败");
      }
    } finally {
      if (requestId === hydrateRequestRef.current) {
        setLoadingThreads(false);
      }
    }
  }

  async function loadMessages(threadId: string) {
    const requestId = ++messageLoadRequestRef.current;
    setLoadingMessages(true);
    setError(null);
    try {
      const nextMessages = await listLibraryChatMessages(threadId);
      if (requestId !== messageLoadRequestRef.current) return;
      setMessages(nextMessages.map((message) => ({ ...message })));
    } catch (err) {
      if (requestId === messageLoadRequestRef.current) {
        setError(err instanceof Error ? err.message : "消息加载失败");
      }
    } finally {
      if (requestId === messageLoadRequestRef.current) {
        setLoadingMessages(false);
      }
    }
  }

  async function startNewThread() {
    if (streaming) return;
    hydrateRequestRef.current += 1;
    messageLoadRequestRef.current += 1;
    setLoadingThreads(false);
    setLoadingMessages(false);
    setError(null);
    try {
      const thread = await createLibraryChatThread();
      setThreads((current) => [thread, ...current]);
      setActiveThreadId(thread.id);
      setMessages([]);
      setStatus(null);
      setOpen(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "新建会话失败");
    }
  }

  async function selectThread(threadId: string) {
    if (threadId === activeThreadId || streaming) return;
    setActiveThreadId(threadId);
    setStatus(null);
    await loadMessages(threadId);
  }

  async function ensureThread(): Promise<LibraryChatThread | null> {
    if (activeThreadId) {
      return threads.find((thread) => thread.id === activeThreadId) ?? {
        id: activeThreadId,
        user_id: "",
        title: "当前会话",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      };
    }
    const thread = await createLibraryChatThread();
    setThreads((current) => [thread, ...current]);
    setActiveThreadId(thread.id);
    return thread;
  }

  async function submit(event?: FormEvent<HTMLFormElement>, prompt?: string) {
    event?.preventDefault();
    const content = (prompt ?? input).trim();
    if (!content || streaming || loadingThreads) return;

    const thread = await ensureThread();
    if (!thread) return;

    messageLoadRequestRef.current += 1;
    setLoadingMessages(false);
    const now = new Date().toISOString();
    let assistantMessageId = `assistant-${Date.now()}`;
    setInput("");
    setStatus(null);
    setError(null);
    setStreaming(true);
    setMessages((current) => [
      ...current,
      {
        id: `user-${Date.now()}`,
        thread_id: thread.id,
        user_id: thread.user_id,
        role: "user",
        content,
        metadata: {},
        created_at: now
      }
    ]);

    try {
      await streamLibraryChatMessage(thread.id, content, (eventPayload) => {
        handleStreamEvent(thread.id, assistantMessageId, eventPayload, (nextId) => {
          assistantMessageId = nextId;
        });
      });
      await refreshAfterStream(thread.id).catch(() => undefined);
    } catch (err) {
      upsertAssistantMessage(thread.id, assistantMessageId, {
        content: err instanceof Error ? err.message : "智能查询失败",
        pending: false,
        failed: true,
        metadata: { mode: "error" }
      });
      setError(err instanceof Error ? err.message : "智能查询失败");
    } finally {
      setStatus(null);
      setStreaming(false);
    }
  }

  function handleStreamEvent(
    threadId: string,
    currentAssistantId: string,
    eventPayload: LibraryChatStreamEvent,
    setAssistantId: (messageId: string) => void
  ) {
    if (eventPayload.event === "status") {
      setStatus(eventPayload.data.message);
      return;
    }
    if (eventPayload.event === "delta") {
      setAssistantId(eventPayload.data.message_id);
      appendAssistantText(threadId, currentAssistantId, eventPayload.data.message_id, eventPayload.data.text);
      return;
    }
    if (eventPayload.event === "results") {
      setAssistantId(eventPayload.data.message_id);
      upsertAssistantMessage(threadId, eventPayload.data.message_id, {
        pending: true,
        metadata: resultPayloadToMetadata(eventPayload.data)
      });
      return;
    }
    if (eventPayload.event === "rejected") {
      setAssistantId(eventPayload.data.message_id);
      upsertAssistantMessage(threadId, eventPayload.data.message_id, {
        content: eventPayload.data.message,
        pending: false,
        metadata: { mode: "rejected", intent: eventPayload.data.intent }
      });
      return;
    }
    if (eventPayload.event === "error") {
      const messageId = eventPayload.data.message_id ?? currentAssistantId;
      setAssistantId(messageId);
      upsertAssistantMessage(threadId, messageId, {
        content: eventPayload.data.message,
        pending: false,
        failed: true,
        metadata: { mode: "error" }
      });
      return;
    }
    if (eventPayload.event === "done") {
      setAssistantId(eventPayload.data.message_id);
      upsertAssistantMessage(threadId, eventPayload.data.message_id, { pending: false });
    }
  }

  function appendAssistantText(threadId: string, previousId: string, messageId: string, text: string) {
    setMessages((current) => {
      const index = current.findIndex((message) => message.id === messageId || message.id === previousId);
      const base = index >= 0 ? current[index] : emptyAssistantMessage(threadId, messageId);
      const updated = {
        ...base,
        id: messageId,
        content: `${base.content}${text}`,
        pending: true
      };
      if (index < 0) return [...current, updated];
      return replaceAt(current, index, updated);
    });
  }

  function upsertAssistantMessage(
    threadId: string,
    messageId: string,
    patch: Partial<ChatMessageView>
  ) {
    setMessages((current) => {
      const index = current.findIndex((message) => message.id === messageId);
      const base = index >= 0 ? current[index] : emptyAssistantMessage(threadId, messageId);
      const updated = { ...base, ...patch, id: messageId, role: "assistant" as const };
      if (index < 0) return [...current, updated];
      return replaceAt(current, index, updated);
    });
  }

  async function refreshAfterStream(threadId: string) {
    const nextThreads = await listLibraryChatThreads();
    setThreads(nextThreads);
    setActiveThreadId(threadId);
  }

  function close() {
    setOpen(false);
    setError(null);
  }

  const activeThread = threads.find((thread) => thread.id === activeThreadId);

  return (
    <>
      {open ? (
        <section className="libraryChatPanel" role="dialog" aria-modal="false" aria-label="信息库智能助手">
          <header className="libraryChatHeader">
            <div className="libraryChatTitle">
              <span className="libraryChatMark" aria-hidden="true">
                <Sparkles size={17} />
              </span>
              <div>
                <h2>信息库助手</h2>
                <p>{activeThread?.title ?? "智能查询已入库内容"}</p>
              </div>
            </div>
            <div className="libraryChatActions">
              <button
                className="iconButton"
                type="button"
                aria-label="新建智能查询会话"
                title="新建会话"
                disabled={streaming}
                onClick={() => void startNewThread()}
              >
                <Plus size={17} />
              </button>
              <button className="iconButton" type="button" aria-label="关闭信息库助手" title="关闭" onClick={close}>
                <X size={18} />
              </button>
            </div>
          </header>

          {threads.length > 1 ? (
            <div className="libraryChatThreads" aria-label="历史会话">
              {threads.slice(0, 4).map((thread) => (
                <button
                  className={thread.id === activeThreadId ? "active" : ""}
                  type="button"
                  key={thread.id}
                  disabled={streaming}
                  onClick={() => void selectThread(thread.id)}
                  title={thread.title}
                >
                  {thread.title}
                </button>
              ))}
            </div>
          ) : null}

          <div className="libraryChatMessages" ref={messagesRef}>
            {loadingMessages || loadingThreads ? (
              <div className="libraryChatState">
                <LoaderCircle className="spin" size={18} />
                <span>正在加载聊天记录</span>
              </div>
            ) : messages.length ? (
              messages.map((message) => (
                <ChatMessageBubble
                  key={message.id}
                  message={message}
                  onOpenLibrary={(libraryUrl) => router.push(libraryUrl)}
                />
              ))
            ) : (
              <div className="libraryChatEmpty">
                <span className="libraryChatEmptyIcon" aria-hidden="true">
                  <Bot size={20} />
                </span>
                <strong>问我信息库里的内容</strong>
                <p>{ASSISTANT_INTRO}</p>
                <div className="libraryChatExamples">
                  {EXAMPLE_PROMPTS.map((prompt) => (
                    <button
                      type="button"
                      key={prompt}
                      disabled={streaming}
                      onClick={() => void submit(undefined, prompt)}
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {status ? <div className="libraryChatStatus">{status}</div> : null}
          {error ? <div className="libraryChatError" role="alert">{error}</div> : null}

          <form className="libraryChatComposer" onSubmit={(event) => void submit(event)}>
            <textarea
              ref={inputRef}
              aria-label="输入信息库查询问题"
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  void submit();
                }
              }}
              placeholder="输入查询，例如：最近 7 天 RAG 论文"
              maxLength={500}
              rows={2}
            />
            <button
              className="libraryChatSend"
              type="submit"
              aria-label="发送智能查询"
              title="发送"
              disabled={!input.trim() || streaming || loadingThreads}
            >
              {streaming ? <LoaderCircle className="spin" size={17} /> : <SendHorizontal size={17} />}
            </button>
          </form>
        </section>
      ) : (
        <button
          className="libraryChatTrigger"
          type="button"
          aria-label="打开信息库智能助手"
          onClick={() => setOpen(true)}
        >
          <MessageCircle size={18} aria-hidden="true" />
          <span>信息库助手</span>
        </button>
      )}
    </>
  );
}

function ChatMessageBubble({
  message,
  onOpenLibrary
}: {
  message: ChatMessageView;
  onOpenLibrary: (libraryUrl: string) => void;
}) {
  const result = resultPayloadFromMetadata(message.metadata);
  return (
    <article className={`libraryChatMessage ${message.role} ${message.failed ? "failed" : ""}`}>
      {message.role === "assistant" ? (
        <span className="libraryChatAvatar" aria-hidden="true">
          <Bot size={15} />
        </span>
      ) : null}
      <div className="libraryChatBubble">
        <p>{message.content}</p>
        {message.pending ? <span className="libraryChatTyping">生成中</span> : null}
        {result ? <ResultCards result={result} onOpenLibrary={onOpenLibrary} /> : null}
      </div>
    </article>
  );
}

function ResultCards({
  result,
  onOpenLibrary
}: {
  result: LibraryChatResultPayload;
  onOpenLibrary: (libraryUrl: string) => void;
}) {
  return (
    <div className="libraryChatResults">
      <div className="libraryChatResultMeta">
        <span>{result.mode === "llm" ? "智能解析" : "关键词兜底"}</span>
        <strong>{result.meta.total} 条</strong>
      </div>
      {result.chips.length ? (
        <div className="libraryChatChips">
          {result.chips.map((chip) => (
            <span key={chip.key}>{chip.label}</span>
          ))}
        </div>
      ) : null}
      {result.items.length ? (
        <div className="libraryChatCards">
          {result.items.slice(0, 4).map((item) => (
            <a className="libraryChatCard" href={item.url} target="_blank" rel="noreferrer" key={item.id}>
              <strong>{item.title}</strong>
              <span>
                {item.source.name} · {item.score.toFixed(1)} 分{item.published_at ? ` · ${formatDate(item.published_at)}` : ""}
              </span>
            </a>
          ))}
        </div>
      ) : (
        <div className="libraryChatNoResults">信息库中没有找到匹配内容</div>
      )}
      <button
        aria-label="在信息库查看全部"
        className="libraryChatLibraryLink"
        type="button"
        onClick={() => onOpenLibrary(result.library_url)}
      >
        在信息库查看全部
        <ArrowUpRight size={15} aria-hidden="true" />
      </button>
    </div>
  );
}

function resultPayloadToMetadata(result: LibraryChatResultPayload): Record<string, unknown> {
  return {
    mode: result.mode,
    items: result.items,
    meta: result.meta,
    library_url: result.library_url,
    chips: result.chips,
    llm: result.llm
  };
}

function resultPayloadFromMetadata(metadata: Record<string, unknown>): LibraryChatResultPayload | null {
  if (!metadata || typeof metadata !== "object") {
    return null;
  }
  const items = metadata.items;
  const meta = metadata.meta;
  const libraryUrl = metadata.library_url;
  const mode = metadata.mode;
  const chips = metadata.chips;
  if (!Array.isArray(items) || !isPageMeta(meta) || typeof libraryUrl !== "string") {
    return null;
  }
  return {
    message_id: "",
    items: items.filter(isLibraryItem),
    meta,
    library_url: libraryUrl,
    mode: mode === "fallback" ? "fallback" : "llm",
    chips: Array.isArray(chips) ? chips.filter(isChip) : [],
    llm: null
  };
}

function isLibraryItem(value: unknown): value is LibraryItem {
  if (!value || typeof value !== "object") return false;
  const item = value as Partial<LibraryItem>;
  const source = item.source as Partial<LibraryItem["source"]> | undefined;
  return (
    typeof item.id === "string" &&
    typeof item.title === "string" &&
    typeof item.url === "string" &&
    typeof item.score === "number" &&
    Boolean(source) &&
    typeof source?.name === "string"
  );
}

function isPageMeta(value: unknown): value is { page: number; page_size: number; total: number } {
  if (!value || typeof value !== "object") return false;
  const meta = value as { page?: unknown; page_size?: unknown; total?: unknown };
  return typeof meta.page === "number" && typeof meta.page_size === "number" && typeof meta.total === "number";
}

function isChip(value: unknown): value is { key: string; label: string } {
  if (!value || typeof value !== "object") return false;
  const chip = value as { key?: unknown; label?: unknown };
  return typeof chip.key === "string" && typeof chip.label === "string";
}

function emptyAssistantMessage(threadId: string, messageId: string): ChatMessageView {
  return {
    id: messageId,
    thread_id: threadId,
    user_id: "",
    role: "assistant",
    content: "",
    metadata: {},
    created_at: new Date().toISOString(),
    pending: true
  };
}

function replaceAt<T>(items: T[], index: number, value: T): T[] {
  return [...items.slice(0, index), value, ...items.slice(index + 1)];
}

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleDateString("zh-CN", { month: "2-digit", day: "2-digit" });
}
