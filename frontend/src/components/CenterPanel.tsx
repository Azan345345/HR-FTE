import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Paperclip, ArrowUp, Mic, Copy, ThumbsUp, ThumbsDown, RefreshCw,
  Pencil, Loader2, Sparkles, Search, FileText, Mail,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { sendChatMessage, getChatHistory } from "@/services/api";
import { useAgentStore } from "@/stores/agent-store";
import { JobResultsCard } from "./chat-cards/JobResultsCard";
import { CVReviewCard } from "./chat-cards/CVReviewCard";
import { EmailReviewCard } from "./chat-cards/EmailReviewCard";
import { ApplicationSentCard } from "./chat-cards/ApplicationSentCard";
import { InterviewPrepCard } from "./chat-cards/InterviewPrepCard";

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  time: string;
  metadata?: Record<string, any> | null;
}

function AgentAvatar() {
  return (
    <div className="w-7 h-7 rounded-full bg-rose-100 flex items-center justify-center flex-shrink-0">
      <span className="text-[10px] font-bold text-primary font-sans">CA</span>
    </div>
  );
}

function AgentLabel({ time }: { time: string }) {
  return (
    <div className="flex items-center gap-2 mb-1.5 opacity-40 group-hover:opacity-100 transition-opacity duration-200">
      <AgentAvatar />
      <span className="text-[11px] text-primary font-sans">CareerAgent · {time}</span>
    </div>
  );
}

function UserLabel({ time }: { time: string }) {
  return (
    <p className="text-[11px] text-slate-400 font-sans text-right mb-1.5 opacity-40 group-hover:opacity-100 transition-opacity duration-200">
      You · {time}
    </p>
  );
}

function UserBubble({
  children, time, content, onEdit,
}: {
  children: React.ReactNode;
  time: string;
  content: string;
  onEdit?: (text: string) => void;
}) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(content).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      className="ml-auto max-w-[65%] group relative"
    >
      <UserLabel time={time} />
      <div className="bg-slate-50 border border-slate-200 rounded-2xl rounded-br-sm px-5 py-4 shadow-sm relative">
        <p className="text-[15px] text-slate-900 font-sans leading-relaxed">{children}</p>
        <div className="absolute -top-3 right-0 opacity-0 group-hover:opacity-100 transition-all duration-200 flex gap-1 bg-white border border-slate-100 shadow-sm rounded-lg p-1">
          <button
            onClick={handleCopy}
            className="p-1 hover:bg-slate-50 rounded transition-colors"
            title={copied ? "Copied!" : "Copy message"}
          >
            <Copy size={12} className={copied ? "text-emerald-500" : "text-slate-400 hover:text-slate-600"} />
          </button>
          {onEdit && (
            <button
              onClick={() => onEdit(content)}
              className="p-1 hover:bg-slate-50 rounded text-slate-400 hover:text-slate-600 transition-colors"
              title="Edit & Resend"
            >
              <Pencil size={12} />
            </button>
          )}
        </div>
      </div>
    </motion.div>
  );
}

function AgentBubble({
  children, time, content, onRegenerate,
}: {
  children: React.ReactNode;
  time: string;
  content?: string;
  onRegenerate?: () => void;
}) {
  const [copied, setCopied] = useState(false);
  const [thumbed, setThumbed] = useState<"up" | "down" | null>(null);

  const handleCopy = () => {
    if (!content) return;
    navigator.clipboard.writeText(content).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      className="max-w-[80%] group relative"
    >
      <AgentLabel time={time} />
      <div className="bg-white border border-slate-100 border-l-[3px] border-l-rose-300 rounded-tr-2xl rounded-br-2xl rounded-bl-2xl rounded-tl-sm px-5 py-4 shadow-md relative">
        {children}
        <div className="absolute -top-3 right-0 opacity-0 group-hover:opacity-100 transition-all duration-200 flex gap-1 bg-white border border-slate-100 shadow-sm rounded-lg p-1">
          {content && (
            <button
              onClick={handleCopy}
              className="p-1 hover:bg-slate-50 rounded transition-colors"
              title={copied ? "Copied!" : "Copy"}
            >
              <Copy size={12} className={copied ? "text-emerald-500" : "text-slate-400 hover:text-slate-600"} />
            </button>
          )}
          <button
            onClick={() => setThumbed(thumbed === "up" ? null : "up")}
            className="p-1 hover:bg-slate-50 rounded transition-colors"
            title="Good response"
          >
            <ThumbsUp size={12} className={thumbed === "up" ? "text-rose-500" : "text-slate-400 hover:text-rose-500"} />
          </button>
          <button
            onClick={() => setThumbed(thumbed === "down" ? null : "down")}
            className="p-1 hover:bg-slate-50 rounded transition-colors"
            title="Bad response"
          >
            <ThumbsDown size={12} className={thumbed === "down" ? "text-slate-600" : "text-slate-400 hover:text-slate-600"} />
          </button>
          {onRegenerate && (
            <button
              onClick={onRegenerate}
              className="p-1 hover:bg-slate-50 rounded text-slate-400 hover:text-slate-600 transition-colors"
              title="Regenerate response"
            >
              <RefreshCw size={12} />
            </button>
          )}
        </div>
      </div>
    </motion.div>
  );
}

const SUGGESTIONS = [
  { emoji: "🔍", text: "Find Senior React roles in New York", icon: Search },
  { emoji: "📄", text: "Parse and analyze my uploaded resume", icon: FileText },
  { emoji: "📧", text: "Draft cold emails to hiring managers", icon: Mail },
  { emoji: "🎯", text: "Match my profile against open positions", icon: Sparkles },
];

interface CenterPanelProps {
  activeSessionId: string | null;
  onSessionCreated: (id: string) => void;
}

export function CenterPanel({ activeSessionId, onSessionCreated }: CenterPanelProps) {
  const [inputValue, setInputValue] = useState("");
  const [showScrollTop, setShowScrollTop] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isSending, setIsSending] = useState(false);
  const [isUploading, setIsUploading] = useState(false);

  const chatEndRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Track current session id inside the component for sendAction closures
  const sessionIdRef = useRef<string | null>(activeSessionId);
  useEffect(() => { sessionIdRef.current = activeSessionId; }, [activeSessionId]);

  // Fetch history when session changes
  useEffect(() => {
    if (activeSessionId) {
      setMessages([]);
      setIsSending(true);
      getChatHistory(activeSessionId)
        .then((data) => {
          const formattedMessages: ChatMessage[] = data.messages
            // Hide internal action prefix messages from the chat
            .filter((m) => !(m.role === "user" && m.content.startsWith("__")))
            .map((m) => ({
              id: m.id,
              role: m.role as "user" | "assistant",
              content: m.content,
              metadata: m.metadata ?? null,
              time: m.created_at
                ? new Date(m.created_at).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" })
                : "Now",
            }));
          setMessages(formattedMessages);
          setIsSending(false);
        })
        .catch((err) => {
          console.error("Failed to load history:", err);
          setIsSending(false);
        });
    } else {
      setMessages([]);
    }
  }, [activeSessionId]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleScroll = () => {
    if (scrollContainerRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = scrollContainerRef.current;
      setShowScrollTop(scrollHeight - scrollTop - clientHeight > 100);
    }
  };

  const scrollToBottom = () => chatEndRef.current?.scrollIntoView({ behavior: "smooth" });

  /** Send a visible user message + get AI response */
  const handleSend = async (overrideText?: string) => {
    const text = (overrideText || inputValue).trim();
    if (!text || (isSending && !overrideText)) return;

    if (!overrideText) setInputValue("");

    const newMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: text,
      time: new Date().toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, newMsg]);
    setIsSending(true);

    try {
      const targetSessionId = sessionIdRef.current || activeSessionId || crypto.randomUUID();
      const resp = await sendChatMessage(text, targetSessionId);

      if (!activeSessionId) onSessionCreated(targetSessionId);

      setMessages((prev) => [
        ...prev,
        {
          id: resp.id || crypto.randomUUID(),
          role: "assistant",
          content: resp.content,
          metadata: resp.metadata ?? null,
          time: new Date().toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" }),
        },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: "⚠️ I couldn't connect to the backend server. Please make sure it's running on `http://localhost:8080`.",
          time: new Date().toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" }),
        },
      ]);
    } finally {
      setIsSending(false);
    }
  };

  /**
   * Send a programmatic action (card button click) without showing the
   * raw action prefix in the chat. Only the AI response is shown.
   */
  const sendAction = async (action: string) => {
    setIsSending(true);
    try {
      const targetSessionId = sessionIdRef.current || activeSessionId || crypto.randomUUID();
      const resp = await sendChatMessage(action, targetSessionId);

      if (!activeSessionId) onSessionCreated(targetSessionId);

      setMessages((prev) => [
        ...prev,
        {
          id: resp.id || crypto.randomUUID(),
          role: "assistant",
          content: resp.content,
          metadata: resp.metadata ?? null,
          time: new Date().toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" }),
        },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: "⚠️ Failed to process action. Please try again.",
          time: new Date().toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" }),
        },
      ]);
    } finally {
      setIsSending(false);
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (file.size > 5 * 1024 * 1024) {
      alert("File is too large. Max 5MB allowed for context.");
      return;
    }
    const ext = file.name.split(".").pop()?.toLowerCase();
    const validExts = ["pdf", "docx", "txt", "md"];
    if (!validExts.includes(ext || "")) {
      alert("Supported context files: PDF, DOCX, TXT, MD");
      return;
    }

    setIsUploading(true);
    const tempId = crypto.randomUUID();
    setMessages((prev) => [
      ...prev,
      {
        id: tempId,
        role: "assistant",
        content: `📎 Attaching **${file.name}** to conversation context...`,
        time: new Date().toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" }),
      },
    ]);

    try {
      const { uploadChatContext } = await import("@/services/api");
      const resp = await uploadChatContext(file);

      setMessages((prev) =>
        prev.map((m) =>
          m.id === tempId
            ? { ...m, content: `✅ Added context from **${file.name}**. I've indexed the file content.` }
            : m
        )
      );

      await handleSend(
        `[CONTEXT UPLOAD: ${file.name}]\n\nContent:\n${resp.content.slice(0, 5000)}\n\nPlease acknowledge this information.`
      );
    } catch (err: any) {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === tempId
            ? { ...m, content: `❌ Failed to add context from **${file.name}**: ${err.message || "Unknown error"}` }
            : m
        )
      );
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  /** Render the appropriate rich card based on metadata.type */
  function renderMetadataCard(msg: ChatMessage) {
    const meta = msg.metadata;
    if (!meta || !meta.type) return null;

    switch (meta.type) {
      case "job_results":
        return <JobResultsCard metadata={meta as any} onSendAction={sendAction} />;
      case "cv_review":
        return <CVReviewCard metadata={meta as any} onSendAction={sendAction} />;
      case "email_review":
        return <EmailReviewCard metadata={meta as any} onSendAction={sendAction} />;
      case "application_sent":
        return <ApplicationSentCard metadata={meta as any} onSendAction={sendAction} />;
      case "interview_ready":
        return <InterviewPrepCard metadata={meta as any} onSendAction={sendAction} />;
      default:
        return null;
    }
  }

  return (
    <main className="flex flex-col h-full bg-white relative">
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileUpload}
        className="hidden"
        accept=".pdf,.docx,.txt,.md"
      />

      {/* Chat Messages */}
      <div
        ref={scrollContainerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto px-8 py-6 space-y-6"
      >
        {/* Empty State */}
        {messages.length === 0 && !isSending && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease: "easeOut" }}
            className="flex flex-col items-center justify-center h-full min-h-[400px]"
          >
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-rose-100 to-rose-50 flex items-center justify-center mb-6 shadow-sm">
              <Sparkles size={28} className="text-rose-500" />
            </div>
            <h2 className="text-2xl font-serif font-bold text-slate-800 mb-2">
              <span className="text-foreground">Career</span>
              <span className="text-primary">Agent</span> is ready
            </h2>
            <p className="text-sm text-slate-500 font-sans max-w-md text-center mb-8 leading-relaxed">
              Send a message to get started. I can search for jobs, tailor your resume, contact hiring managers, and prepare you for interviews — all in one conversation.
            </p>
            <div className="grid grid-cols-2 gap-3 max-w-lg w-full">
              {SUGGESTIONS.map((s, i) => (
                <motion.button
                  key={i}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.3 + i * 0.1, duration: 0.3 }}
                  onClick={() => handleSend(s.text)}
                  className="flex items-center gap-3 px-4 py-3.5 bg-slate-50 border border-slate-200 rounded-xl text-left hover:bg-rose-50 hover:border-rose-200 hover:shadow-sm transition-all group"
                >
                  <div className="w-8 h-8 rounded-lg bg-white border border-slate-100 flex items-center justify-center flex-shrink-0 group-hover:border-rose-200 transition-colors">
                    <s.icon size={16} className="text-slate-500 group-hover:text-rose-500 transition-colors" />
                  </div>
                  <span className="text-[13px] font-medium text-slate-700 font-sans group-hover:text-rose-700 transition-colors leading-tight">
                    {s.emoji} {s.text}
                  </span>
                </motion.button>
              ))}
            </div>
          </motion.div>
        )}

        {/* Messages */}
        {(() => {
          // Find the last user message for Regenerate
          const lastUserContent = [...messages].reverse().find(m => m.role === "user" && !m.content.startsWith("__"))?.content;

          return messages.map((msg) => {
            // Hide raw action-prefix user messages (they show up when reloading history)
            if (msg.role === "user" && msg.content.startsWith("__")) return null;

            return msg.role === "user" ? (
              <UserBubble
                key={msg.id}
                time={msg.time}
                content={msg.content}
                onEdit={(text) => setInputValue(text)}
              >
                {msg.content}
              </UserBubble>
            ) : (
              <AgentBubble
                key={msg.id}
                time={msg.time}
                content={msg.content}
                onRegenerate={lastUserContent ? () => handleSend(lastUserContent) : undefined}
              >
                <div className="prose prose-sm prose-slate max-w-none prose-p:leading-relaxed prose-p:my-2 prose-ul:my-2 prose-ol:my-2 prose-li:my-0.5 prose-headings:font-sans prose-headings:font-bold prose-a:text-primary prose-code:bg-slate-100 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-rose-600 prose-code:text-xs prose-pre:bg-slate-900 prose-pre:rounded-xl">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {msg.content}
                  </ReactMarkdown>
                </div>
                {/* Rich metadata card rendered below the text */}
                {renderMetadataCard(msg)}
              </AgentBubble>
            );
          });
        })()}

        {/* Thinking indicator */}
        {(isSending || isUploading) && (
          <div className="flex items-center gap-2 p-4">
            <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
            <span className="text-sm text-muted-foreground">
              {isUploading ? "Uploading file..." : "Thinking..."}
            </span>
          </div>
        )}

        <div ref={chatEndRef} />
      </div>

      {/* Scroll to Bottom */}
      <AnimatePresence>
        {showScrollTop && (
          <motion.button
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            onClick={scrollToBottom}
            className="absolute bottom-24 left-1/2 -translate-x-1/2 z-20 bg-white shadow-lg border border-slate-100 rounded-full px-4 py-2 flex items-center gap-2 hover:bg-slate-50 transition-colors"
          >
            <span className="text-xs font-medium text-slate-600 font-sans">↓ Latest</span>
          </motion.button>
        )}
      </AnimatePresence>

      {/* Input Area */}
      <div className="px-8 py-4 border-t border-slate-100 bg-white flex-shrink-0">
        <AnimatePresence mode="wait">
          <motion.div
            key="input-box"
            layoutId="main-input"
            className="w-full h-14 bg-slate-50 border border-slate-200 rounded-2xl shadow-sm flex items-center px-5 gap-3 focus-within:border-rose-400 focus-within:ring-2 focus-within:ring-rose-100 focus-within:bg-white transition-all"
          >
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploading}
              className="p-1 hover:bg-slate-100 rounded-lg transition-colors disabled:opacity-50"
            >
              <Paperclip size={18} className="text-slate-400 hover:text-slate-600 cursor-pointer transition-colors" />
            </button>
            <Mic size={18} className="text-slate-400 hover:text-slate-600 cursor-pointer transition-colors flex-shrink-0" />
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              disabled={isSending}
              placeholder="Send a message to CareerAgent..."
              className="flex-1 bg-transparent text-sm text-foreground font-sans placeholder:text-slate-400 outline-none caret-primary disabled:opacity-50"
            />
            <button
              onClick={() => handleSend()}
              disabled={!inputValue.trim() || isSending}
              className={`w-10 h-10 rounded-full flex items-center justify-center transition-all duration-200 flex-shrink-0 ${
                inputValue.trim()
                  ? "bg-rose-600 hover:bg-rose-700 hover:scale-105 cursor-pointer shadow-sm"
                  : "bg-slate-100 cursor-not-allowed"
              }`}
            >
              <ArrowUp size={18} className={inputValue.trim() ? "text-white" : "text-slate-300"} />
            </button>
          </motion.div>
        </AnimatePresence>
      </div>
    </main>
  );
}
