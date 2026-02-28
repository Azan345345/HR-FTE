import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Paperclip, ArrowUp, Copy, ThumbsUp, ThumbsDown, RefreshCw,
  Pencil, Sparkles, Search, FileText, Mail, Zap, Bot,
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
    <div className="w-8 h-8 rounded-xl bg-primary flex items-center justify-center flex-shrink-0 shadow-sm">
      <Bot size={14} className="text-white" />
    </div>
  );
}

function AgentLabel({ time }: { time: string }) {
  return (
    <div className="flex items-center gap-2 mb-2 opacity-50 group-hover:opacity-100 transition-opacity duration-200">
      <AgentAvatar />
      <span className="text-[11px] font-semibold text-primary tracking-wide">CareerAgent</span>
      <span className="text-[10px] text-slate-400">· {time}</span>
    </div>
  );
}

function UserLabel({ time }: { time: string }) {
  return (
    <p className="text-[11px] text-slate-400 font-sans text-right mb-2 opacity-50 group-hover:opacity-100 transition-opacity duration-200">
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
      initial={{ opacity: 0, x: 16, y: 8 }}
      animate={{ opacity: 1, x: 0, y: 0 }}
      transition={{ duration: 0.25, ease: "easeOut" }}
      className="ml-auto max-w-[62%] group relative"
    >
      <UserLabel time={time} />
      <div className="relative">
        <div className="bg-gradient-to-br from-slate-800 to-slate-900 rounded-2xl rounded-tr-sm px-5 py-3.5 shadow-md">
          <p className="text-[14px] text-white font-sans leading-relaxed">{children}</p>
        </div>
        {/* Hover actions */}
        <div className="absolute -top-3 right-0 opacity-0 group-hover:opacity-100 transition-all duration-150 flex gap-0.5 bg-white border border-slate-100 shadow-md rounded-xl p-1 z-10">
          <button
            onClick={handleCopy}
            className="p-1.5 hover:bg-slate-50 rounded-lg transition-colors"
            title={copied ? "Copied!" : "Copy"}
          >
            <Copy size={11} className={copied ? "text-primary" : "text-slate-400"} />
          </button>
          {onEdit && (
            <button
              onClick={() => onEdit(content)}
              className="p-1.5 hover:bg-slate-50 rounded-lg text-slate-400 hover:text-slate-600 transition-colors"
              title="Edit & Resend"
            >
              <Pencil size={11} />
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
      initial={{ opacity: 0, x: -16, y: 8 }}
      animate={{ opacity: 1, x: 0, y: 0 }}
      transition={{ duration: 0.25, ease: "easeOut" }}
      className="max-w-[78%] group relative"
    >
      <AgentLabel time={time} />
      <div className="relative">
        <div className="bg-white border border-slate-100 rounded-2xl rounded-tl-sm px-5 py-4 shadow-sm relative overflow-hidden">
          {/* Subtle left accent stripe */}
          <div className="absolute left-0 top-3 bottom-3 w-0.5 bg-primary rounded-full" />
          <div className="pl-3">
            {children}
          </div>
        </div>
        {/* Hover actions */}
        <div className="absolute -top-3 right-0 opacity-0 group-hover:opacity-100 transition-all duration-150 flex gap-0.5 bg-white border border-slate-100 shadow-md rounded-xl p-1 z-10">
          {content && (
            <button
              onClick={handleCopy}
              className="p-1.5 hover:bg-slate-50 rounded-lg transition-colors"
              title={copied ? "Copied!" : "Copy"}
            >
              <Copy size={11} className={copied ? "text-primary" : "text-slate-400"} />
            </button>
          )}
          <button
            onClick={() => setThumbed(thumbed === "up" ? null : "up")}
            className="p-1.5 hover:bg-slate-50 rounded-lg transition-colors"
            title="Good response"
          >
            <ThumbsUp size={11} className={thumbed === "up" ? "text-primary" : "text-slate-400 hover:text-primary"} />
          </button>
          <button
            onClick={() => setThumbed(thumbed === "down" ? null : "down")}
            className="p-1.5 hover:bg-slate-50 rounded-lg transition-colors"
            title="Needs improvement"
          >
            <ThumbsDown size={11} className={thumbed === "down" ? "text-slate-700" : "text-slate-400 hover:text-slate-600"} />
          </button>
          {onRegenerate && (
            <button
              onClick={onRegenerate}
              className="p-1.5 hover:bg-slate-50 rounded-lg text-slate-400 hover:text-slate-600 transition-colors"
              title="Regenerate response"
            >
              <RefreshCw size={11} />
            </button>
          )}
        </div>
      </div>
    </motion.div>
  );
}

function ThinkingBubble() {
  return (
    <motion.div
      initial={{ opacity: 0, x: -16, y: 8 }}
      animate={{ opacity: 1, x: 0, y: 0 }}
      className="max-w-[78%]"
    >
      <div className="flex items-center gap-2 mb-2 opacity-70">
        <AgentAvatar />
        <span className="text-[11px] font-semibold text-primary tracking-wide">CareerAgent</span>
      </div>
      <div className="bg-white border border-slate-100 rounded-2xl rounded-tl-sm px-5 py-4 shadow-sm overflow-hidden relative">
        <div className="absolute left-0 top-3 bottom-3 w-0.5 bg-primary rounded-full" />
        <div className="pl-3 flex items-center gap-1.5">
          {[0, 1, 2].map(i => (
            <motion.span
              key={i}
              className="w-2 h-2 rounded-full bg-primary"
              animate={{ scale: [1, 1.5, 1], opacity: [0.5, 1, 0.5] }}
              transition={{ duration: 1.2, repeat: Infinity, delay: i * 0.2 }}
            />
          ))}
          <span className="text-xs text-slate-400 ml-2">Thinking…</span>
        </div>
      </div>
    </motion.div>
  );
}

const SUGGESTIONS = [
  {
    icon: Search,
    label: "Job Search",
    text: "Find Senior React roles in New York",
    gradient: "from-violet-500 to-indigo-500",
    bg: "from-violet-50 to-indigo-50",
    border: "border-violet-100 hover:border-violet-200",
  },
  {
    icon: FileText,
    label: "Resume",
    text: "Parse and analyze my uploaded resume",
    gradient: "from-primary to-emerald-400",
    bg: "from-[hsl(195,94%,97%)] to-[hsl(195,90%,93%)]",
    border: "border-[hsl(195,90%,93%)] hover:border-primary/30",
  },
  {
    icon: Mail,
    label: "Outreach",
    text: "Draft cold emails to hiring managers",
    gradient: "from-amber-500 to-orange-500",
    bg: "from-amber-50 to-orange-50",
    border: "border-amber-100 hover:border-amber-200",
  },
  {
    icon: Zap,
    label: "Match",
    text: "Match my profile against open positions",
    gradient: "from-emerald-500 to-teal-500",
    bg: "from-emerald-50 to-teal-50",
    border: "border-emerald-100 hover:border-emerald-200",
  },
];

interface CenterPanelProps {
  activeSessionId: string | null;
  onSessionCreated: (id: string) => void;
  onNavigateToInterview?: (jobId: string | null) => void;
}

export function CenterPanel({ activeSessionId, onSessionCreated, onNavigateToInterview }: CenterPanelProps) {
  const [inputValue, setInputValue] = useState("");
  const [showScrollBtn, setShowScrollBtn] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isSending, setIsSending] = useState(false);
  const [isUploading, setIsUploading] = useState(false);

  const chatEndRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const sessionIdRef = useRef<string | null>(activeSessionId);
  useEffect(() => { sessionIdRef.current = activeSessionId; }, [activeSessionId]);

  useEffect(() => {
    if (activeSessionId) {
      setMessages([]);
      setIsSending(true);
      getChatHistory(activeSessionId)
        .then((data) => {
          const formattedMessages: ChatMessage[] = data.messages
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
        .catch(() => setIsSending(false));
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
      setShowScrollBtn(scrollHeight - scrollTop - clientHeight > 120);
    }
  };

  const scrollToBottom = () => chatEndRef.current?.scrollIntoView({ behavior: "smooth" });

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
          content: "⚠️ Couldn't reach the backend. Make sure it's running on `http://localhost:8080`.",
          time: new Date().toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" }),
        },
      ]);
    } finally {
      setIsSending(false);
    }
  };

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
      alert("File is too large. Max 5MB allowed.");
      return;
    }
    const ext = file.name.split(".").pop()?.toLowerCase();
    if (!["pdf", "docx", "txt", "md"].includes(ext || "")) {
      alert("Supported: PDF, DOCX, TXT, MD");
      return;
    }

    setIsUploading(true);
    const tempId = crypto.randomUUID();
    setMessages((prev) => [
      ...prev,
      {
        id: tempId,
        role: "assistant",
        content: `📎 Attaching **${file.name}** to context…`,
        time: new Date().toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" }),
      },
    ]);

    try {
      const { uploadChatContext } = await import("@/services/api");
      const resp = await uploadChatContext(file);
      setMessages((prev) =>
        prev.map((m) =>
          m.id === tempId
            ? { ...m, content: `✅ Context loaded from **${file.name}**.` }
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
            ? { ...m, content: `❌ Failed to load **${file.name}**: ${err.message || "Unknown error"}` }
            : m
        )
      );
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  function renderMetadataCard(msg: ChatMessage) {
    const meta = msg.metadata;
    if (!meta || !meta.type) return null;
    switch (meta.type) {
      case "job_results":     return <JobResultsCard metadata={meta as any} onSendAction={sendAction} />;
      case "cv_review":       return <CVReviewCard metadata={meta as any} onSendAction={sendAction} />;
      case "email_review":    return <EmailReviewCard metadata={meta as any} onSendAction={sendAction} />;
      case "application_sent":return <ApplicationSentCard metadata={meta as any} onSendAction={sendAction} />;
      case "interview_ready": return <InterviewPrepCard metadata={meta as any} onSendAction={sendAction} onNavigateToInterview={onNavigateToInterview} />;
      default: return null;
    }
  }

  const lastUserContent = [...messages].reverse().find(m => m.role === "user" && !m.content.startsWith("__"))?.content;

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
        className="flex-1 overflow-y-auto px-6 py-6 space-y-5"
        style={{ background: "linear-gradient(180deg, #f8fafc 0%, #ffffff 60%)" }}
      >
        {/* Empty State */}
        {messages.length === 0 && !isSending && (
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, ease: "easeOut" }}
            className="flex flex-col items-center justify-center h-full min-h-[420px] px-4"
          >
            {/* Brand mark */}
            <div className="relative mb-8">
              <div
                className="w-[72px] h-[72px] rounded-[22px] bg-primary flex items-center justify-center"
                style={{ boxShadow: "0 8px 32px -4px hsl(195 94% 45% / 40%), 0 2px 8px -2px hsl(195 94% 45% / 20%)" }}
              >
                <Bot size={30} className="text-white" />
              </div>
              <motion.div
                className="absolute -bottom-1.5 -right-1.5 w-6 h-6 rounded-lg bg-gradient-to-br from-emerald-400 to-teal-500 flex items-center justify-center"
                style={{ boxShadow: "0 2px 8px rgba(16,185,129,0.40)" }}
                animate={{ scale: [1, 1.15, 1] }}
                transition={{ duration: 2.5, repeat: Infinity }}
              >
                <Sparkles size={11} className="text-white" />
              </motion.div>
            </div>

            <h2 className="text-[26px] font-serif tracking-tight text-slate-900 mb-2 text-center">
              <span className="text-slate-800">Career</span>
              <span className="text-primary">Agent</span>
              <span className="text-slate-800"> is ready</span>
            </h2>
            <p className="text-[13px] text-slate-500 max-w-[340px] text-center mb-8 leading-[1.65]">
              Job search · Resume tailoring · HR outreach · Interview prep — all in one conversation.
            </p>

            {/* Suggestion cards */}
            <div className="grid grid-cols-2 gap-2.5 w-full max-w-[420px]">
              {SUGGESTIONS.map((s, i) => (
                <motion.button
                  key={i}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.15 + i * 0.07, duration: 0.35, ease: [0.16, 1, 0.32, 1] }}
                  onClick={() => handleSend(s.text)}
                  className={`flex flex-col gap-3 p-4 bg-gradient-to-br ${s.bg} border ${s.border} rounded-2xl text-left hover:shadow-card hover:scale-[1.02] active:scale-[0.98] transition-all duration-200 group`}
                >
                  <div className={`w-8 h-8 rounded-xl bg-gradient-to-br ${s.gradient} flex items-center justify-center`}
                    style={{ boxShadow: "0 2px 8px rgba(0,0,0,0.15)" }}>
                    <s.icon size={14} className="text-white" />
                  </div>
                  <div>
                    <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-[0.07em] mb-1">{s.label}</p>
                    <p className="text-[12px] font-medium text-slate-700 leading-snug">{s.text}</p>
                  </div>
                </motion.button>
              ))}
            </div>
          </motion.div>
        )}

        {/* Messages */}
        {messages.map((msg) => {
          if (msg.role === "user" && msg.content.startsWith("__")) return null;

          return msg.role === "user" ? (
            <UserBubble
              key={msg.id}
              time={msg.time}
              content={msg.content}
              onEdit={(text) => {
                setInputValue(text);
                inputRef.current?.focus();
              }}
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
              <div className="prose prose-sm prose-slate max-w-none prose-p:leading-relaxed prose-p:my-2 prose-ul:my-2 prose-ol:my-2 prose-li:my-0.5 prose-headings:font-sans prose-headings:font-bold prose-a:text-primary prose-code:bg-slate-100 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-primary prose-code:text-xs prose-pre:bg-slate-900 prose-pre:rounded-xl">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {msg.content}
                </ReactMarkdown>
              </div>
              {renderMetadataCard(msg)}
            </AgentBubble>
          );
        })}

        {/* Animated thinking indicator */}
        {(isSending || isUploading) && <ThinkingBubble />}

        <div ref={chatEndRef} />
      </div>

      {/* Scroll to bottom */}
      <AnimatePresence>
        {showScrollBtn && (
          <motion.button
            initial={{ opacity: 0, scale: 0.8, y: 8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.8, y: 8 }}
            onClick={scrollToBottom}
            className="absolute bottom-24 left-1/2 -translate-x-1/2 z-20 bg-white shadow-lg border border-slate-100 rounded-full px-4 py-2 flex items-center gap-2 hover:bg-slate-50 transition-colors text-xs font-semibold text-slate-600"
          >
            ↓ Latest
          </motion.button>
        )}
      </AnimatePresence>

      {/* Input Area */}
      <div className="px-5 py-4 border-t border-black/[0.05] bg-white/98 backdrop-blur-sm flex-shrink-0">
        <div
          className="relative w-full bg-white rounded-2xl transition-all duration-200 focus-within:ring-[3px] focus-within:ring-primary/10"
          style={{ border: "1px solid rgba(0,0,0,0.09)", boxShadow: "var(--shadow-card)" }}
        >
          <textarea
            ref={inputRef}
            rows={1}
            value={inputValue}
            onChange={(e) => {
              setInputValue(e.target.value);
              // auto-resize
              e.target.style.height = "auto";
              e.target.style.height = Math.min(e.target.scrollHeight, 160) + "px";
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            disabled={isSending}
            placeholder="Message CareerAgent… (Enter to send, Shift+Enter for newline)"
            className="w-full px-5 pt-3.5 pb-12 bg-transparent text-[13px] text-foreground placeholder:text-slate-400 outline-none resize-none leading-relaxed disabled:opacity-50 max-h-40"
            style={{ minHeight: "52px" }}
          />
          {/* Bottom toolbar */}
          <div className="absolute bottom-2.5 left-3 right-3 flex items-center justify-between">
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploading}
              className="p-2 hover:bg-slate-50 rounded-xl transition-colors disabled:opacity-40 flex items-center gap-1.5 text-slate-400 hover:text-slate-600"
              title="Attach file (PDF, DOCX, TXT, MD)"
            >
              <Paperclip size={15} />
              <span className="text-[11px] font-medium hidden sm:block">Attach</span>
            </button>
            <button
              onClick={() => handleSend()}
              disabled={!inputValue.trim() || isSending}
              className={`flex items-center gap-1.5 px-4 py-2 rounded-xl text-[12px] font-semibold transition-all duration-200 active:scale-[0.96] ${
                inputValue.trim() && !isSending
                  ? "bg-primary text-white hover:brightness-110"
                  : "bg-slate-100 text-slate-300 cursor-not-allowed"
              }`}
              style={inputValue.trim() && !isSending ? { boxShadow: "var(--shadow-brand-sm)" } : {}}
            >
              <ArrowUp size={13} />
              Send
            </button>
          </div>
        </div>
      </div>
    </main>
  );
}
