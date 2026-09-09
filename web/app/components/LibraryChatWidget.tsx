"use client";

import { type ReactNode, useCallback, useEffect, useRef, useState } from "react";
import {
  ArrowDown,
  ArrowUpRight,
  Bot,
  BrainCircuit,
  Check,
  Copy,
  History,
  LoaderCircle,
  MessageCircle,
  Plus,
  SendHorizontal,
  Sparkles,
  Trash2,
  X
} from "lucide-react";
import { useRouter } from "next/navigation";
import {
  ActionBarPrimitive,
  AssistantRuntimeProvider,
  ComposerPrimitive,
  MessagePartPrimitive,
  MessagePrimitive,
  ThreadPrimitive,
  type AppendMessage,
  type AssistantRuntime,
  type DataMessagePartProps,
  type EmptyMessagePartProps,
  type MessageStatus,
  type TextMessagePartProps,
  type ThreadMessageLike,
  useExternalStoreRuntime
} from "@assistant-ui/react";
import { MarkdownTextPrimitive } from "@assistant-ui/react-markdown";
import {
  createLibraryChatThread,
  deleteLibraryChatThread,
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
const LIBRARY_RESULTS_PART = "library-results";
const MESSAGE_COMPONENTS = {
  UserMessage: LibraryUserMessage,
  AssistantMessage: LibraryAssistantMessage
};

type ChatMessageView = LibraryChatMessage & {
  pending?: boolean;
  failed?: boolean;
};

export function LibraryChatWidget() {
  const [open, setOpen] = useState(false);
  const [threads, setThreads] = useState<LibraryChatThread[]>([]);
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessageView[]>([]);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadingThreads, setLoadingThreads] = useState(false);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [deletingThreadId, setDeletingThreadId] = useState<string | null>(null);
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
    function handleKeyDown(event: globalThis.KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open]);

  const submitContent = useCallback(
    async (rawContent: string, createdAt = new Date()) => {
      const content = rawContent.trim();
      if (!content || streaming || loadingThreads) return;

      const thread = await ensureThread();
      if (!thread) return;

      messageLoadRequestRef.current += 1;
      setLoadingMessages(false);
      let assistantMessageId = `assistant-${Date.now()}`;
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
          created_at: createdAt.toISOString()
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
    },
    [activeThreadId, loadingThreads, streaming, threads]
  );

  const runtime = useExternalStoreRuntime<ChatMessageView>({
    messages,
    convertMessage: toAssistantMessage,
    isLoading: loadingMessages || loadingThreads,
    isRunning: streaming,
    isSendDisabled: streaming || loadingThreads,
    suggestions: messages.length ? [] : EXAMPLE_PROMPTS.map((prompt) => ({ prompt })),
    unstable_capabilities: { copy: true },
    onNew: async (message: AppendMessage) => {
      await submitContent(appendMessageText(message), message.createdAt);
    }
  });

  const LibraryMessagesFooter = useCallback(
    function LibraryMessagesFooter() {
      return (
        <>
          {status ? <div className="libraryChatStatus">{status}</div> : null}
          {error ? (
            <div className="libraryChatError" role="alert">
              {error}
            </div>
          ) : null}
        </>
      );
    },
    [error, status]
  );

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

  async function deleteThread(thread: LibraryChatThread) {
    if (streaming || deletingThreadId) return;
    if (!window.confirm(`确定删除“${thread.title}”吗？删除后聊天记录无法恢复。`)) return;

    setDeletingThreadId(thread.id);
    setError(null);
    hydrateRequestRef.current += 1;
    messageLoadRequestRef.current += 1;
    const remainingThreads = threads.filter((candidate) => candidate.id !== thread.id);

    try {
      await deleteLibraryChatThread(thread.id);
      setThreads(remainingThreads);
      if (thread.id !== activeThreadId) return;

      const nextThread = remainingThreads[0];
      if (nextThread) {
        setActiveThreadId(nextThread.id);
        setMessages([]);
        await loadMessages(nextThread.id);
        return;
      }

      const replacementThread = await createLibraryChatThread();
      setThreads([replacementThread]);
      setActiveThreadId(replacementThread.id);
      setMessages([]);
      setStatus(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "删除会话失败");
    } finally {
      setDeletingThreadId(null);
    }
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
  const isLoading = loadingMessages || loadingThreads;

  return (
    <>
      {open ? (
        <section className="libraryChatPanel" role="dialog" aria-modal="false" aria-label="信息库智能助手">
          <header className="libraryChatHeader">
            <div className="libraryChatTitle">
              <span className="libraryChatMark" aria-hidden="true">
                <BrainCircuit size={18} />
              </span>
              <div>
                <h2>信息库助手</h2>
                <p>{activeThread?.title ?? "智能查询已入库内容"}</p>
              </div>
            </div>
            <div className="libraryChatActions">
              <button
                className="iconButton libraryChatHeaderButton"
                type="button"
                aria-label="新建智能查询会话"
                title="新建会话"
                disabled={streaming}
                onClick={() => void startNewThread()}
              >
                <Plus size={17} />
              </button>
              <button
                className="iconButton libraryChatHeaderButton"
                type="button"
                aria-label="关闭信息库助手"
                title="关闭"
                onClick={close}
              >
                <X size={18} />
              </button>
            </div>
          </header>

          {threads.length ? (
            <div className="libraryChatThreads" aria-label="历史会话">
              <History size={14} aria-hidden="true" />
              {threads.slice(0, 5).map((thread) => (
                <div className="libraryChatThreadItem" key={thread.id}>
                  <button
                    className={`libraryChatThreadSelect ${thread.id === activeThreadId ? "active" : ""}`}
                    type="button"
                    disabled={streaming || deletingThreadId !== null}
                    onClick={() => void selectThread(thread.id)}
                    title={thread.title}
                  >
                    {thread.title}
                  </button>
                  <button
                    className="libraryChatThreadDelete"
                    type="button"
                    aria-label={`删除会话 ${thread.title}`}
                    title="删除会话"
                    disabled={streaming || deletingThreadId !== null}
                    onClick={() => void deleteThread(thread)}
                  >
                    {deletingThreadId === thread.id ? (
                      <LoaderCircle className="spin" size={13} />
                    ) : (
                      <Trash2 size={13} />
                    )}
                  </button>
                </div>
              ))}
            </div>
          ) : null}

          <div className="libraryChatThreadSurface">
            {isLoading ? (
              <div className="libraryChatState">
                <LoaderCircle className="spin" size={18} />
                <span>正在加载聊天记录</span>
              </div>
            ) : (
              <LibraryAssistantThread runtime={runtime} MessagesFooter={LibraryMessagesFooter} />
            )}
          </div>
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
          <Sparkles size={15} aria-hidden="true" />
        </button>
      )}
    </>
  );
}

function LibraryAssistantThread({
  runtime,
  MessagesFooter
}: {
  runtime: AssistantRuntime;
  MessagesFooter: () => ReactNode;
}) {
  return (
    <AssistantRuntimeProvider runtime={runtime}>
      <ThreadPrimitive.Root className="aui-root aui-thread-root">
        <ThreadPrimitive.Viewport className="aui-thread-viewport" autoScroll>
          <LibraryThreadWelcome />
          <ThreadPrimitive.Messages components={MESSAGE_COMPONENTS} />
          <div className="libraryChatThreadSpacer" />
          <ThreadPrimitive.ViewportFooter className="aui-thread-viewport-footer">
            <ThreadPrimitive.ScrollToBottom
              aria-label="滚动到底部"
              behavior="smooth"
              className="aui-button aui-button-outline aui-button-icon aui-thread-scroll-to-bottom"
              title="滚动到底部"
            >
              <ArrowDown size={15} />
            </ThreadPrimitive.ScrollToBottom>
            <MessagesFooter />
            <LibraryComposer />
          </ThreadPrimitive.ViewportFooter>
        </ThreadPrimitive.Viewport>
      </ThreadPrimitive.Root>
    </AssistantRuntimeProvider>
  );
}

function LibraryThreadWelcome() {
  return (
    <ThreadPrimitive.Empty>
      <div className="libraryChatEmpty">
        <span className="libraryChatEmptyIcon" aria-hidden="true">
          <Bot size={20} />
        </span>
        <strong className="libraryChatEmptyTitle">问我信息库里的内容</strong>
        <p>{ASSISTANT_INTRO}</p>
        <div className="aui-thread-welcome-suggestions">
          {EXAMPLE_PROMPTS.map((prompt) => (
            <ThreadPrimitive.Suggestion
              autoSend
              className="aui-thread-welcome-suggestion"
              key={prompt}
              prompt={prompt}
            >
              <span className="aui-thread-welcome-suggestion-text">{prompt}</span>
            </ThreadPrimitive.Suggestion>
          ))}
        </div>
      </div>
    </ThreadPrimitive.Empty>
  );
}

function LibraryUserMessage() {
  return (
    <MessagePrimitive.Root className="aui-user-message-root">
      <div className="aui-user-message-content">
        <MessagePrimitive.Content components={{ Text: LibraryPlainText }} />
      </div>
    </MessagePrimitive.Root>
  );
}

function LibraryAssistantMessage() {
  return (
    <MessagePrimitive.Root className="libraryChatAssistantMessage">
      <span className="libraryChatAvatar" aria-hidden="true">
        <Bot size={15} />
      </span>
      <div className="libraryChatAssistantStack">
        <div className="libraryChatAssistantBubble">
          <MessagePrimitive.Content
            components={{
              Text: LibraryMarkdownText,
              Empty: LibraryEmptyMessagePart,
              data: {
                by_name: {
                  [LIBRARY_RESULTS_PART]: LibraryResultsPart
                }
              }
            }}
          />
        </div>
        <div className="libraryChatMessageTools">
          <ActionBarPrimitive.Root
            autohide="not-last"
            autohideFloat="single-branch"
            className="aui-assistant-action-bar-root"
            hideWhenRunning
          >
            <ActionBarPrimitive.Copy
              aria-label="复制回答"
              className="aui-button libraryChatCopyButton"
              copiedDuration={1600}
              title="复制回答"
            >
              <MessagePrimitive.If copied>
                <Check size={13} />
              </MessagePrimitive.If>
              <MessagePrimitive.If copied={false}>
                <Copy size={13} />
              </MessagePrimitive.If>
            </ActionBarPrimitive.Copy>
          </ActionBarPrimitive.Root>
        </div>
      </div>
    </MessagePrimitive.Root>
  );
}

function LibraryComposer() {
  return (
    <ComposerPrimitive.Root className="libraryChatComposer">
      <ComposerPrimitive.Input
        aria-label="输入信息库查询问题"
        autoFocus
        className="libraryChatComposerInput"
        maxLength={500}
        placeholder="输入查询，例如：最近 7 天 RAG 论文"
        rows={2}
      />
      <ComposerPrimitive.Send
        aria-label="发送智能查询"
        className="libraryChatSend"
        title="发送"
      >
        <SendHorizontal size={17} />
      </ComposerPrimitive.Send>
    </ComposerPrimitive.Root>
  );
}

function LibraryPlainText(_props: TextMessagePartProps) {
  return <MessagePartPrimitive.Text className="aui-text" component="p" />;
}

function LibraryMarkdownText(_props: TextMessagePartProps) {
  return <MarkdownTextPrimitive className="libraryChatMarkdown" />;
}

function LibraryEmptyMessagePart({ status }: EmptyMessagePartProps) {
  if (status.type !== "running") return null;
  return (
    <span className="libraryChatTyping">
      <LoaderCircle className="spin" size={13} />
      正在查询信息库
    </span>
  );
}

function LibraryResultsPart({ data }: DataMessagePartProps<LibraryChatResultPayload>) {
  const router = useRouter();
  return <ResultCards result={data} onOpenLibrary={(libraryUrl) => router.push(libraryUrl)} />;
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

function toAssistantMessage(message: ChatMessageView): ThreadMessageLike {
  const content: Array<
    | { type: "text"; text: string }
    | { type: "data"; name: typeof LIBRARY_RESULTS_PART; data: LibraryChatResultPayload }
  > = [];
  if (message.content.trim()) {
    content.push({ type: "text", text: message.content });
  }
  const result = resultPayloadFromMetadata(message.metadata);
  if (result) {
    content.push({ type: "data", name: LIBRARY_RESULTS_PART, data: result });
  }
  const createdAt = toDate(message.created_at);
  const metadata = { custom: { source: "library-chat" } };

  if (message.role === "assistant") {
    return {
      id: message.id,
      role: "assistant",
      content,
      createdAt,
      status: statusForMessage(message),
      metadata
    };
  }

  return {
    id: message.id,
    role: "user",
    content,
    createdAt,
    metadata
  };
}

function statusForMessage(message: ChatMessageView): MessageStatus {
  if (message.failed) {
    return { type: "incomplete", reason: "error", error: message.content || "智能查询失败" };
  }
  if (message.pending) {
    return { type: "running" };
  }
  return { type: "complete", reason: "stop" };
}

function appendMessageText(message: AppendMessage): string {
  return message.content
    .map((part) => (part.type === "text" ? part.text : ""))
    .join("\n")
    .trim();
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

function toDate(value: string): Date {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? new Date() : date;
}

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleDateString("zh-CN", { month: "2-digit", day: "2-digit" });
}
