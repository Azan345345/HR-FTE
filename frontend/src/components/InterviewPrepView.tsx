import { useState, useEffect, useCallback, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
    Brain, Cpu, UserCheck, Globe, Lightbulb, DollarSign,
    BrainCircuit, Sparkles, Building2, ChevronRight,
    ChevronDown, CheckCircle2, Clock, LayoutList, X,
    MessageSquare, HelpCircle, AlertCircle, RefreshCw,
    Banknote, Star, Target, Zap, Copy, Check, Code2,
    Send, Bot, User2, CalendarDays, Palette, ArrowRight,
    BookOpen, FlaskConical, BarChart3, Layers
} from "lucide-react";
import {
    listApplications, listJobs, listInterviewPreps,
    createInterviewPrep, getInterviewPrep, chatWithInterviewCoach
} from "@/services/api";
import { ScrollArea } from "@/components/ui/scroll-area";
import { toast } from "sonner";

interface InterviewPrepViewProps {
    focusedJobId?: string | null;
}

type TabKey = "overview" | "technical" | "behavioral" | "situational" | "sysdesign" | "coding" | "cultural" | "ask" | "salary" | "plan";

const TABS: { key: TabKey; label: string; icon: any; color: string }[] = [
    { key: "overview",    label: "Overview",      icon: Globe,        color: "blue"    },
    { key: "technical",   label: "Technical",     icon: Cpu,          color: "violet"  },
    { key: "behavioral",  label: "Behavioral",    icon: UserCheck,    color: "rose"    },
    { key: "situational", label: "Situational",   icon: Target,       color: "amber"   },
    { key: "sysdesign",   label: "System Design", icon: Layers,       color: "indigo"  },
    { key: "coding",      label: "Coding",        icon: Code2,        color: "cyan"    },
    { key: "cultural",    label: "Culture",       icon: Palette,      color: "pink"    },
    { key: "ask",         label: "Ask Them",      icon: MessageSquare,color: "green"   },
    { key: "salary",      label: "Salary",        icon: Banknote,     color: "emerald" },
    { key: "plan",        label: "Study Plan",    icon: CalendarDays, color: "orange"  },
];

const DIFFICULTY_STYLE: Record<string, string> = {
    easy:   "bg-green-50 text-green-700 border-green-200",
    medium: "bg-amber-50 text-amber-700 border-amber-200",
    hard:   "bg-red-50 text-red-700 border-red-200",
};

function CopyButton({ text }: { text: string }) {
    const [copied, setCopied] = useState(false);
    const copy = () => {
        navigator.clipboard.writeText(text).then(() => {
            setCopied(true);
            setTimeout(() => setCopied(false), 1500);
        });
    };
    return (
        <button onClick={copy} className="p-1 rounded hover:bg-slate-200 transition-colors flex-shrink-0" title="Copy">
            {copied ? <Check size={12} className="text-green-600" /> : <Copy size={12} className="text-slate-400" />}
        </button>
    );
}

function QuestionCard({ q, index, color }: { q: any; index: number; color: string }) {
    const [open, setOpen] = useState(false);
    const answer = q.answer || q.suggested_approach || q.sample_answer || "";
    const hasExtra = q.follow_up || q.why_asked || q.key_principle || q.what_they_want;

    return (
        <div className={`bg-white rounded-2xl border transition-all overflow-hidden ${open ? `border-${color}-200 shadow-md` : "border-slate-100 hover:border-slate-200"}`}>
            <button
                onClick={() => setOpen(!open)}
                className="w-full flex items-start gap-3 p-4 text-left"
            >
                <span className={`w-6 h-6 rounded-lg flex items-center justify-center text-[10px] font-bold flex-shrink-0 mt-0.5 bg-${color}-50 text-${color}-600`}>
                    {index + 1}
                </span>
                <div className="flex-1 min-w-0">
                    <span className="text-sm font-semibold text-slate-800 leading-snug block">{q.question}</span>
                    {q.topic && <span className="text-[10px] text-slate-400 mt-0.5 block">{q.topic}</span>}
                    {q.competency && <span className="text-[10px] text-slate-400 mt-0.5 block">Competency: {q.competency}</span>}
                </div>
                <div className="flex items-center gap-1.5 flex-shrink-0 ml-2">
                    {q.difficulty && (
                        <span className={`text-[9px] font-bold uppercase tracking-wide px-1.5 py-0.5 rounded-full border ${DIFFICULTY_STYLE[q.difficulty] || DIFFICULTY_STYLE.medium}`}>
                            {q.difficulty}
                        </span>
                    )}
                    {q.framework && (
                        <span className="text-[9px] font-bold uppercase tracking-wide px-1.5 py-0.5 rounded-full bg-rose-50 text-rose-600 border border-rose-100">
                            STAR
                        </span>
                    )}
                    <ChevronDown size={14} className={`text-slate-400 transition-transform duration-200 ${open ? "rotate-180" : ""}`} />
                </div>
            </button>
            <AnimatePresence>
                {open && (
                    <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.2 }}
                        className="border-t border-slate-100"
                    >
                        <div className="p-4 pt-3 bg-slate-50/70 space-y-3">
                            {answer && (
                                <div>
                                    <div className="flex items-start justify-between gap-2 mb-2">
                                        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Model Answer</span>
                                        <CopyButton text={answer} />
                                    </div>
                                    <p className="text-xs text-slate-700 leading-relaxed whitespace-pre-wrap">{answer}</p>
                                </div>
                            )}
                            {q.follow_up && (
                                <div className="p-2.5 bg-violet-50 rounded-xl border border-violet-100">
                                    <span className="text-[9px] font-bold text-violet-500 uppercase tracking-wider block mb-1">Follow-up Question</span>
                                    <p className="text-xs text-slate-700 font-medium">{q.follow_up}</p>
                                </div>
                            )}
                            {q.why_asked && (
                                <div className="flex items-start gap-1.5">
                                    <Lightbulb size={11} className="text-amber-500 flex-shrink-0 mt-0.5" />
                                    <p className="text-[11px] text-slate-500 italic">{q.why_asked}</p>
                                </div>
                            )}
                            {q.key_principle && (
                                <div className="flex items-start gap-1.5">
                                    <Star size={11} className="text-rose-400 flex-shrink-0 mt-0.5" />
                                    <p className="text-[11px] text-slate-500">{q.key_principle}</p>
                                </div>
                            )}
                            {q.what_they_want && (
                                <div className="p-2 bg-amber-50 rounded-lg border border-amber-100">
                                    <span className="text-[9px] font-bold text-amber-600 uppercase tracking-wider">What They Want to See</span>
                                    <p className="text-[11px] text-slate-700 mt-0.5">{q.what_they_want}</p>
                                </div>
                            )}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}

function SystemDesignCard({ q, index }: { q: any; index: number }) {
    const [open, setOpen] = useState(false);
    return (
        <div className={`bg-white rounded-2xl border overflow-hidden transition-all ${open ? "border-indigo-200 shadow-md" : "border-slate-100 hover:border-slate-200"}`}>
            <button onClick={() => setOpen(!open)} className="w-full flex items-start gap-3 p-4 text-left">
                <span className="w-6 h-6 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center text-[10px] font-bold flex-shrink-0 mt-0.5">{index + 1}</span>
                <span className="flex-1 text-sm font-semibold text-slate-800 leading-snug">Design: {q.question}</span>
                <ChevronDown size={14} className={`text-slate-400 transition-transform duration-200 ${open ? "rotate-180" : ""}`} />
            </button>
            <AnimatePresence>
                {open && (
                    <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.2 }} className="border-t border-slate-100">
                        <div className="p-4 pt-3 bg-slate-50/70 space-y-3">
                            {q.approach && (
                                <div>
                                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-2">Architecture Approach</span>
                                    <p className="text-xs text-slate-700 leading-relaxed whitespace-pre-wrap">{q.approach}</p>
                                </div>
                            )}
                            {q.evaluation_criteria && (
                                <div className="p-2.5 bg-emerald-50 rounded-xl border border-emerald-100">
                                    <span className="text-[9px] font-bold text-emerald-600 uppercase tracking-wider block mb-1">Strong vs Weak Answer</span>
                                    <p className="text-xs text-slate-700">{q.evaluation_criteria}</p>
                                </div>
                            )}
                            {(q.common_mistakes || []).length > 0 && (
                                <div className="p-2.5 bg-red-50 rounded-xl border border-red-100">
                                    <span className="text-[9px] font-bold text-red-500 uppercase tracking-wider block mb-1">Common Mistakes to Avoid</span>
                                    <ul className="space-y-1">
                                        {q.common_mistakes.map((m: string, i: number) => (
                                            <li key={i} className="text-xs text-slate-700 flex items-start gap-1.5">
                                                <X size={10} className="text-red-400 flex-shrink-0 mt-0.5" /> {m}
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            )}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}

function CodingChallengeCard({ q, index }: { q: any; index: number }) {
    const [open, setOpen] = useState(false);
    return (
        <div className={`bg-white rounded-2xl border overflow-hidden transition-all ${open ? "border-cyan-200 shadow-md" : "border-slate-100 hover:border-slate-200"}`}>
            <button onClick={() => setOpen(!open)} className="w-full flex items-start gap-3 p-4 text-left">
                <span className="w-6 h-6 rounded-lg bg-cyan-50 text-cyan-600 flex items-center justify-center text-[10px] font-bold flex-shrink-0 mt-0.5">{index + 1}</span>
                <div className="flex-1 min-w-0">
                    <span className="text-sm font-semibold text-slate-800 leading-snug line-clamp-2">{q.problem}</span>
                    {(q.time_complexity || q.space_complexity) && (
                        <div className="flex gap-2 mt-1">
                            {q.time_complexity && <span className="text-[9px] px-1.5 py-0.5 bg-cyan-50 text-cyan-700 border border-cyan-200 rounded-full font-mono">Time: {q.time_complexity}</span>}
                            {q.space_complexity && <span className="text-[9px] px-1.5 py-0.5 bg-blue-50 text-blue-700 border border-blue-200 rounded-full font-mono">Space: {q.space_complexity}</span>}
                        </div>
                    )}
                </div>
                <ChevronDown size={14} className={`text-slate-400 transition-transform duration-200 ${open ? "rotate-180" : ""}`} />
            </button>
            <AnimatePresence>
                {open && (
                    <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.2 }} className="border-t border-slate-100">
                        <div className="p-4 pt-3 bg-slate-50/70 space-y-3">
                            {q.brute_force_approach && (
                                <div>
                                    <span className="text-[10px] font-bold text-amber-500 uppercase tracking-wider block mb-1">Brute Force (Why It's Bad)</span>
                                    <p className="text-xs text-slate-600">{q.brute_force_approach}</p>
                                </div>
                            )}
                            {q.optimal_solution && (
                                <div>
                                    <div className="flex items-center justify-between mb-1">
                                        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Optimal Solution</span>
                                        <CopyButton text={q.optimal_solution} />
                                    </div>
                                    <pre className="text-[11px] text-slate-800 bg-slate-900 text-slate-100 p-3 rounded-xl overflow-x-auto leading-relaxed whitespace-pre-wrap font-mono">{q.optimal_solution}</pre>
                                </div>
                            )}
                            {(q.edge_cases || []).length > 0 && (
                                <div className="p-2.5 bg-amber-50 rounded-xl border border-amber-100">
                                    <span className="text-[9px] font-bold text-amber-600 uppercase tracking-wider block mb-1">Edge Cases to Test</span>
                                    <ul className="space-y-0.5">
                                        {q.edge_cases.map((ec: string, i: number) => (
                                            <li key={i} className="text-xs text-slate-700 flex items-start gap-1.5">
                                                <span className="text-amber-400 flex-shrink-0">·</span> {ec}
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            )}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}

function GeneratingState({ jobTitle, company }: { jobTitle: string; company: string }) {
    const steps = [
        "Researching company culture, tech stack and interview style...",
        "Building salary market range and negotiation scripts...",
        "Crafting 7-day study plan and expert tips...",
        "Generating 12 role-specific technical questions...",
        "Writing STAR behavioral answers from your CV...",
        "Building system design challenges...",
        "Generating situational & culture-fit questions...",
        "Writing optimal coding solutions with complexity analysis...",
        "Analysing salary data and negotiation tactics...",
        "Finalising your elite prep package...",
    ];
    const [step, setStep] = useState(0);
    useEffect(() => {
        const t = setInterval(() => setStep(s => (s + 1) % steps.length), 2500);
        return () => clearInterval(t);
    }, []);
    return (
        <div className="flex-1 flex flex-col items-center justify-center p-8 text-center">
            <div className="relative mb-8">
                <motion.div
                    animate={{ rotate: 360 }}
                    transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
                    className="w-20 h-20 border-4 border-dashed border-rose-200 rounded-full"
                />
                <div className="absolute inset-0 flex items-center justify-center">
                    <BrainCircuit size={28} className="text-rose-600" />
                </div>
            </div>
            <h2 className="text-xl font-bold text-slate-900 mb-1">Building Elite Prep Strategy</h2>
            <p className="text-slate-500 text-sm mb-6">{jobTitle} at {company}</p>
            <AnimatePresence mode="wait">
                <motion.div
                    key={step}
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -6 }}
                    className="flex items-center gap-2 text-xs text-slate-500 bg-slate-50 border border-slate-200 px-4 py-2 rounded-full"
                >
                    <div className="w-1.5 h-1.5 rounded-full bg-rose-500 animate-pulse" />
                    {steps[step]}
                </motion.div>
            </AnimatePresence>
            <p className="text-[10px] text-slate-300 mt-6">Usually takes 1–3 minutes · 3 AI calls running</p>
        </div>
    );
}

// ── AI Coach Chat Panel ────────────────────────────────────────────────────────

interface ChatMsg { role: "user" | "assistant"; content: string }

function CoachChatPanel({ prepId, jobTitle, company }: { prepId: string; jobTitle: string; company: string }) {
    const [messages, setMessages] = useState<ChatMsg[]>([
        { role: "assistant", content: `I'm your personal interview coach for **${jobTitle} at ${company}**.\n\nI can:\n• Give feedback on your practice answers\n• Explain any concept in depth\n• Generate more questions on a topic\n• Share ${company}-specific strategy\n\nWhat would you like to work on?` }
    ]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    const bottomRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLTextAreaElement>(null);

    const scrollBottom = () => bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    useEffect(() => scrollBottom(), [messages]);

    const sendMessage = async () => {
        if (!input.trim() || loading) return;
        const userMsg = input.trim();
        setInput("");
        setMessages(prev => [...prev, { role: "user", content: userMsg }]);
        setLoading(true);
        try {
            const historyForApi = messages.slice(-10).map(m => ({ role: m.role, content: m.content }));
            const resp = await chatWithInterviewCoach(prepId, userMsg, historyForApi);
            setMessages(prev => [...prev, { role: "assistant", content: resp.response }]);
        } catch (err: any) {
            toast.error("Coach unavailable: " + (err.message || "unknown error"));
        } finally {
            setLoading(false);
        }
    };

    const handleKey = (e: React.KeyboardEvent) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    };

    const quickPrompts = [
        "Practice answering: tell me about yourself",
        "What should I research about this company?",
        "Give me 3 harder technical questions",
        "How do I answer salary questions?",
    ];

    return (
        <div className="flex flex-col h-full bg-white border-l border-slate-100">
            {/* Header */}
            <div className="flex items-center gap-2 px-4 py-3 border-b border-slate-100 bg-slate-50 flex-shrink-0">
                <div className="w-7 h-7 rounded-xl bg-rose-600 flex items-center justify-center">
                    <Bot size={14} className="text-white" />
                </div>
                <div>
                    <p className="text-xs font-bold text-slate-900">AI Coach</p>
                    <p className="text-[10px] text-slate-400">Practice · Feedback · Strategy</p>
                </div>
                <div className="ml-auto flex items-center gap-1 px-2 py-0.5 rounded-full bg-green-50 border border-green-200">
                    <div className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
                    <span className="text-[9px] font-bold text-green-700">Live</span>
                </div>
            </div>

            {/* Messages */}
            <ScrollArea className="flex-1 px-3 py-3">
                <div className="space-y-3">
                    {messages.map((msg, i) => (
                        <motion.div
                            key={i}
                            initial={{ opacity: 0, y: 8 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.2 }}
                            className={`flex gap-2 ${msg.role === "user" ? "flex-row-reverse" : ""}`}
                        >
                            <div className={`w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5 ${
                                msg.role === "assistant" ? "bg-rose-100" : "bg-slate-200"
                            }`}>
                                {msg.role === "assistant"
                                    ? <Bot size={12} className="text-rose-600" />
                                    : <User2 size={12} className="text-slate-600" />}
                            </div>
                            <div className={`max-w-[85%] px-3 py-2 rounded-2xl text-xs leading-relaxed whitespace-pre-wrap ${
                                msg.role === "assistant"
                                    ? "bg-slate-50 border border-slate-100 text-slate-700 rounded-tl-sm"
                                    : "bg-rose-600 text-white rounded-tr-sm"
                            }`}>
                                {msg.content}
                            </div>
                        </motion.div>
                    ))}
                    {loading && (
                        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex gap-2">
                            <div className="w-6 h-6 rounded-full bg-rose-100 flex items-center justify-center flex-shrink-0">
                                <Bot size={12} className="text-rose-600" />
                            </div>
                            <div className="px-3 py-2.5 bg-slate-50 border border-slate-100 rounded-2xl rounded-tl-sm">
                                <div className="flex gap-1 items-center">
                                    {[0, 1, 2].map(i => (
                                        <motion.div key={i} className="w-1.5 h-1.5 bg-rose-400 rounded-full"
                                            animate={{ scale: [1, 1.4, 1] }}
                                            transition={{ duration: 0.8, repeat: Infinity, delay: i * 0.15 }} />
                                    ))}
                                </div>
                            </div>
                        </motion.div>
                    )}
                    <div ref={bottomRef} />
                </div>
            </ScrollArea>

            {/* Quick prompts (show only when 1 message = greeting) */}
            {messages.length === 1 && (
                <div className="px-3 pb-2 flex flex-wrap gap-1">
                    {quickPrompts.map((p, i) => (
                        <button key={i} onClick={() => setInput(p)} className="text-[10px] px-2 py-1 bg-slate-100 hover:bg-rose-50 hover:text-rose-700 hover:border-rose-200 border border-slate-200 rounded-lg text-slate-600 transition-all">
                            {p}
                        </button>
                    ))}
                </div>
            )}

            {/* Input */}
            <div className="px-3 pb-3 flex-shrink-0">
                <div className="flex items-end gap-2 bg-slate-50 border border-slate-200 rounded-2xl px-3 py-2 focus-within:border-rose-300 focus-within:ring-2 focus-within:ring-rose-50 transition-all">
                    <textarea
                        ref={inputRef}
                        rows={1}
                        value={input}
                        onChange={e => setInput(e.target.value)}
                        onKeyDown={handleKey}
                        placeholder="Practice an answer or ask a question..."
                        className="flex-1 bg-transparent resize-none text-xs text-slate-700 placeholder-slate-400 outline-none max-h-28 leading-relaxed"
                        style={{ minHeight: "20px" }}
                    />
                    <button
                        onClick={sendMessage}
                        disabled={!input.trim() || loading}
                        className="w-7 h-7 rounded-xl bg-rose-600 hover:bg-rose-700 disabled:opacity-40 flex items-center justify-center flex-shrink-0 transition-all"
                    >
                        <Send size={12} className="text-white" />
                    </button>
                </div>
                <p className="text-[9px] text-slate-300 text-center mt-1">Enter to send · Shift+Enter for newline</p>
            </div>
        </div>
    );
}

// ── Main Component ─────────────────────────────────────────────────────────────

export function InterviewPrepView({ focusedJobId }: InterviewPrepViewProps) {
    const [jobs, setJobs]                   = useState<any[]>([]);
    const [applications, setApplications]   = useState<any[]>([]);
    const [preps, setPreps]                 = useState<any[]>([]);
    const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
    const [activePrep, setActivePrep]       = useState<any | null>(null);
    const [loading, setLoading]             = useState(true);
    const [generating, setGenerating]       = useState(false);
    const [genError, setGenError]           = useState<string | null>(null);
    const [activeTab, setActiveTab]         = useState<TabKey>("overview");
    const [sidebarOpen, setSidebarOpen]     = useState(false);
    const [diffFilter, setDiffFilter]       = useState<string>("all");
    const [chatOpen, setChatOpen]           = useState(false);
    const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

    // ── Data loading ─────────────────────────────────────────────────────────
    useEffect(() => {
        const fetch = async () => {
            try {
                const [jd, ad, pd] = await Promise.all([
                    listJobs(undefined, 100, 0).catch(() => ({ jobs: [] })),
                    listApplications().catch(() => ({ applications: [] })),
                    listInterviewPreps().catch(() => ({ preps: [] })),
                ]);
                setJobs((jd as any).jobs || []);
                setApplications((ad as any).applications || []);
                setPreps((pd as any).preps || []);
            } finally {
                setLoading(false);
            }
        };
        fetch();
    }, []);

    // ── Refresh preps list ───────────────────────────────────────────────────
    const refreshPreps = useCallback(async () => {
        try {
            const pd = await listInterviewPreps().catch(() => ({ preps: [] }));
            setPreps((pd as any).preps || []);
        } catch { /* ignore */ }
    }, []);

    // ── Polling ──────────────────────────────────────────────────────────────
    useEffect(() => {
        if (pollRef.current) clearInterval(pollRef.current);
        if (!activePrep || activePrep.status !== "generating") return;

        let attempts = 0;
        // Poll every 2 seconds — generation takes ≤90s with parallel LLM calls.
        // Give up after 150 attempts (5 minutes) as an absolute safety net.
        pollRef.current = setInterval(async () => {
            attempts++;
            try {
                const fresh = await getInterviewPrep(activePrep.id);

                if (fresh.status === "completed") {
                    clearInterval(pollRef.current!);
                    setActivePrep(fresh);
                    setGenerating(false);
                    setActiveTab("overview");
                    refreshPreps();

                } else if (fresh.status === "failed") {
                    clearInterval(pollRef.current!);
                    refreshPreps();
                    // Even on failure the agent may have written partial data
                    const hasData = (fresh.technical_questions?.length > 0) ||
                        (fresh.behavioral_questions?.length > 0) ||
                        fresh.company_research?.overview;
                    if (hasData) {
                        setActivePrep({ ...fresh, status: "completed" });
                        setGenerating(false);
                        setActiveTab("overview");
                        toast.warning("Some sections incomplete — click Regenerate to retry.");
                    } else {
                        setGenError("The AI couldn't generate content. Please try again.");
                        setGenerating(false);
                    }

                } else if (attempts >= 150) {
                    // 5-minute hard cap — do one last fetch
                    clearInterval(pollRef.current!);
                    try {
                        const last = await getInterviewPrep(activePrep.id);
                        if (last.status === "completed" || last.technical_questions?.length > 0) {
                            setActivePrep({ ...last, status: "completed" });
                            setGenerating(false);
                            setActiveTab("overview");
                            refreshPreps();
                        } else {
                            setGenError("Generation timed out. Please try again.");
                            setGenerating(false);
                        }
                    } catch {
                        setGenError("Generation timed out. Please try again.");
                        setGenerating(false);
                    }
                }
            } catch { /* ignore transient network errors */ }
        }, 2000);

        return () => { if (pollRef.current) clearInterval(pollRef.current); };
    }, [activePrep?.id, activePrep?.status, refreshPreps]);

    const handleSelectJob = useCallback((jobId: string) => {
        setSelectedJobId(jobId);
        setGenError(null);
        setDiffFilter("all");
        setChatOpen(false);
        const existing = preps.find(p => p.job_id === jobId);
        if (existing) {
            setActivePrep(existing);
            setGenerating(existing.status === "generating");
            setActiveTab("overview");
        } else {
            setActivePrep(null);
            setGenerating(false);
        }
        setSidebarOpen(false);
    }, [preps]);

    useEffect(() => {
        if (focusedJobId) handleSelectJob(focusedJobId);
    }, [focusedJobId, handleSelectJob]);

    const handleGenerate = async () => {
        if (!selectedJobId) return;
        setGenerating(true);
        setGenError(null);
        try {
            const resp = await createInterviewPrep(selectedJobId);
            setActivePrep(resp);
        } catch (err: any) {
            const msg = err?.message || "Failed to start prep generation.";
            setGenError(msg);
            setGenerating(false);
            toast.error(msg);
        }
    };

    const selectedJob = jobs.find(j => j.id === selectedJobId)
        || applications.find(a => a.job_id === selectedJobId)?.job;
    const appliedJobIds = new Set(applications.map((a: any) => a.job_id));
    const displayJobs = jobs.length > 0
        ? jobs
        : applications.map(a => ({ ...a.job, id: a.job_id }));

    const techQs    = activePrep?.technical_questions || [];
    const behavQs   = activePrep?.behavioral_questions || [];
    const situQs    = activePrep?.situational_questions || [];
    const askQs     = activePrep?.questions_to_ask || [];
    const tips      = activePrep?.tips || [];
    const salary    = activePrep?.salary_research || {};
    const research  = activePrep?.company_research || {};
    const sysQs     = activePrep?.system_design_questions || [];
    const codeQs    = activePrep?.coding_challenges || [];
    const cultQs    = activePrep?.cultural_questions || [];
    const studyPlan = activePrep?.study_plan || {};

    const filteredTechQs = diffFilter === "all" ? techQs : techQs.filter((q: any) => q.difficulty === diffFilter);
    const totalQuestions = techQs.length + behavQs.length + situQs.length + sysQs.length + codeQs.length + cultQs.length;

    const badgeCount: Record<TabKey, number | null> = {
        overview: null,
        technical: techQs.length || null,
        behavioral: behavQs.length || null,
        situational: situQs.length || null,
        sysdesign: sysQs.length || null,
        coding: codeQs.length || null,
        cultural: cultQs.length || null,
        ask: askQs.length || null,
        salary: null,
        plan: Object.keys(studyPlan).length > 0 ? 7 : null,
    };

    const SidebarContent = () => (
        <div className="flex flex-col h-full bg-slate-50/50">
            <div className="p-4 border-b border-slate-100 bg-white flex items-center justify-between flex-shrink-0">
                <div>
                    <h3 className="text-sm font-bold text-slate-900">Jobs</h3>
                    <p className="text-[10px] text-slate-400 mt-0.5">{displayJobs.length} available</p>
                </div>
                <button onClick={() => setSidebarOpen(false)} className="lg:hidden p-1.5 hover:bg-slate-100 rounded-xl">
                    <X size={15} className="text-slate-400" />
                </button>
            </div>
            <ScrollArea className="flex-1 p-2.5">
                {loading ? (
                    <div className="space-y-2">
                        {Array(5).fill(0).map((_, i) => (
                            <div key={i} className="h-16 bg-white rounded-xl animate-pulse border border-slate-100" />
                        ))}
                    </div>
                ) : displayJobs.length === 0 ? (
                    <div className="text-center py-10">
                        <Building2 className="w-7 h-7 text-slate-200 mx-auto mb-2" />
                        <p className="text-xs text-slate-400 font-medium">No jobs yet</p>
                        <p className="text-[10px] text-slate-300 mt-1">Search for jobs in the chat</p>
                    </div>
                ) : (
                    <div className="space-y-1">
                        {displayJobs.map((job: any) => {
                            const isSelected = selectedJobId === job.id;
                            const jobPrep = preps.find(p => p.job_id === job.id);
                            const hasPrep = !!jobPrep;
                            const prepStatus = jobPrep?.status;
                            return (
                                <button
                                    key={job.id}
                                    onClick={() => handleSelectJob(job.id)}
                                    className={`w-full text-left p-3 rounded-xl border transition-all ${
                                        isSelected
                                            ? "bg-white border-rose-200 shadow-md shadow-rose-100/20 ring-1 ring-rose-50"
                                            : "border-transparent hover:bg-white hover:border-slate-200"
                                    }`}
                                >
                                    <div className="flex items-center gap-2 mb-1">
                                        <div className={`w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold flex-shrink-0 ${isSelected ? "bg-rose-600 text-white" : "bg-slate-200 text-slate-500"}`}>
                                            {(job.company || "?")[0].toUpperCase()}
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <p className={`text-xs font-bold truncate leading-tight ${isSelected ? "text-slate-900" : "text-slate-700"}`}>
                                                {job.title || "Position"}
                                            </p>
                                            <p className="text-[10px] text-slate-400 truncate">{job.company}</p>
                                        </div>
                                        <div className="flex flex-col items-end gap-1 flex-shrink-0">
                                            {hasPrep && (
                                                <div className={`w-2 h-2 rounded-full ${prepStatus === "completed" ? "bg-green-500" : "bg-amber-400 animate-pulse"}`}
                                                    title={prepStatus === "completed" ? "Prep ready" : "Generating..."} />
                                            )}
                                            {appliedJobIds.has(job.id) && (
                                                <span className="text-[7px] font-bold px-1 py-0.5 bg-blue-50 text-blue-500 rounded-full border border-blue-100 leading-none">APP</span>
                                            )}
                                        </div>
                                    </div>
                                </button>
                            );
                        })}
                    </div>
                )}
            </ScrollArea>
        </div>
    );

    // ── Tab content ──────────────────────────────────────────────────────────
    const renderTabContent = () => {
        switch (activeTab) {
            case "overview":
                return (
                    <div className="p-5 lg:p-8 grid grid-cols-1 lg:grid-cols-3 gap-5">
                        <div className="lg:col-span-2 space-y-4">
                            <div className="bg-slate-900 text-white rounded-2xl p-6">
                                <div className="flex items-center gap-2 mb-3">
                                    <Globe size={14} className="text-rose-400" />
                                    <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">Company Intelligence</span>
                                </div>
                                <h3 className="text-xl font-bold mb-3">{selectedJob?.company}</h3>
                                {research.overview && <p className="text-sm text-slate-300 leading-relaxed mb-4">{research.overview}</p>}
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                    {research.culture && (
                                        <div className="p-3 bg-white/5 rounded-xl border border-white/10">
                                            <p className="text-[9px] font-bold text-rose-400 uppercase tracking-wider mb-1">Culture</p>
                                            <p className="text-xs text-slate-300 leading-relaxed">{research.culture}</p>
                                        </div>
                                    )}
                                    {research.tech_stack && (
                                        <div className="p-3 bg-white/5 rounded-xl border border-white/10">
                                            <p className="text-[9px] font-bold text-blue-400 uppercase tracking-wider mb-1">Tech Stack</p>
                                            <p className="text-xs text-slate-300 leading-relaxed">{research.tech_stack}</p>
                                        </div>
                                    )}
                                    {research.interview_style && (
                                        <div className="p-3 bg-white/5 rounded-xl border border-white/10">
                                            <p className="text-[9px] font-bold text-amber-400 uppercase tracking-wider mb-1">Interview Style</p>
                                            <p className="text-xs text-slate-300 leading-relaxed">{research.interview_style}</p>
                                        </div>
                                    )}
                                    {research.recent_news && (
                                        <div className="p-3 bg-white/5 rounded-xl border border-white/10">
                                            <p className="text-[9px] font-bold text-green-400 uppercase tracking-wider mb-1">Recent News</p>
                                            <p className="text-xs text-slate-300 leading-relaxed">{research.recent_news}</p>
                                        </div>
                                    )}
                                </div>
                            </div>

                            <div className="grid grid-cols-3 lg:grid-cols-6 gap-2">
                                {[
                                    { label: "Technical",   val: techQs.length,  color: "text-violet-600", bg: "bg-violet-50", border: "border-violet-100" },
                                    { label: "Behavioral",  val: behavQs.length, color: "text-rose-600",   bg: "bg-rose-50",   border: "border-rose-100"   },
                                    { label: "Situational", val: situQs.length,  color: "text-amber-600",  bg: "bg-amber-50",  border: "border-amber-100"  },
                                    { label: "Sys Design",  val: sysQs.length,   color: "text-indigo-600", bg: "bg-indigo-50", border: "border-indigo-100" },
                                    { label: "Coding",      val: codeQs.length,  color: "text-cyan-600",   bg: "bg-cyan-50",   border: "border-cyan-100"   },
                                    { label: "Culture",     val: cultQs.length,  color: "text-pink-600",   bg: "bg-pink-50",   border: "border-pink-100"   },
                                ].map(s => (
                                    <div key={s.label} className={`${s.bg} border ${s.border} rounded-xl p-2 text-center`}>
                                        <div className={`text-xl font-bold ${s.color}`}>{s.val}</div>
                                        <div className="text-[9px] text-slate-500 mt-0.5 font-medium leading-tight">{s.label}</div>
                                    </div>
                                ))}
                            </div>
                        </div>

                        <div className="space-y-4">
                            {tips.length > 0 && (
                                <div className="bg-white border border-slate-100 rounded-2xl p-5">
                                    <div className="flex items-center gap-2 mb-4">
                                        <div className="p-1.5 bg-amber-50 rounded-lg">
                                            <Lightbulb size={14} className="text-amber-600" />
                                        </div>
                                        <h4 className="text-sm font-bold text-slate-800">Expert Tips</h4>
                                    </div>
                                    <ul className="space-y-2.5">
                                        {tips.map((tip: string, i: number) => (
                                            <li key={i} className="flex gap-2.5 items-start">
                                                <div className="w-5 h-5 rounded-full bg-amber-50 border border-amber-200 flex items-center justify-center flex-shrink-0 mt-0.5">
                                                    <span className="text-[9px] font-bold text-amber-600">{i + 1}</span>
                                                </div>
                                                <p className="text-xs text-slate-600 leading-relaxed">{tip}</p>
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            )}
                            <div className="bg-rose-50 border border-rose-100 rounded-2xl p-4">
                                <div className="flex items-center gap-2 mb-3">
                                    <Zap size={14} className="text-rose-600" />
                                    <h4 className="text-sm font-bold text-slate-800">Quick Navigation</h4>
                                </div>
                                <div className="space-y-1.5">
                                    {TABS.filter(t => t.key !== "overview").map(tab => {
                                        const count = badgeCount[tab.key];
                                        return (
                                            <button key={tab.key} onClick={() => setActiveTab(tab.key)}
                                                className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl hover:bg-white hover:shadow-sm transition-all text-left group">
                                                <tab.icon size={12} className="text-slate-400 group-hover:text-rose-600 transition-colors" />
                                                <span className="text-xs font-medium text-slate-600 flex-1">{tab.label}</span>
                                                {count != null && (
                                                    <span className="text-[9px] font-bold px-1.5 py-0.5 bg-slate-200 text-slate-500 rounded-full">{count}</span>
                                                )}
                                                <ChevronRight size={12} className="text-slate-300 group-hover:text-rose-500 transition-colors" />
                                            </button>
                                        );
                                    })}
                                </div>
                            </div>
                        </div>
                    </div>
                );

            case "technical":
                return (
                    <div className="p-5 lg:p-8">
                        <div className="flex items-center justify-between mb-5">
                            <div>
                                <h3 className="font-bold text-slate-900 text-lg">Technical Questions</h3>
                                <p className="text-xs text-slate-400 mt-0.5">{techQs.length} role-specific questions · click to reveal answer + follow-up</p>
                            </div>
                            <div className="flex items-center gap-1 bg-slate-100 rounded-xl p-1">
                                {["all", "easy", "medium", "hard"].map(d => (
                                    <button key={d} onClick={() => setDiffFilter(d)}
                                        className={`px-2.5 py-1 rounded-lg text-[10px] font-bold capitalize transition-all ${diffFilter === d ? "bg-white text-slate-800 shadow-sm" : "text-slate-500 hover:text-slate-700"}`}>
                                        {d}
                                    </button>
                                ))}
                            </div>
                        </div>
                        {filteredTechQs.length === 0
                            ? <div className="text-center py-10 text-slate-400 text-sm">No {diffFilter} questions.</div>
                            : <div className="space-y-3">{filteredTechQs.map((q: any, i: number) => <QuestionCard key={i} q={q} index={i} color="violet" />)}</div>
                        }
                    </div>
                );

            case "behavioral":
                return (
                    <div className="p-5 lg:p-8">
                        <h3 className="font-bold text-slate-900 text-lg mb-2">Behavioral Questions</h3>
                        <div className="flex items-center gap-2 mb-5 px-3 py-2 bg-rose-50 border border-rose-100 rounded-xl">
                            <Star size={13} className="text-rose-500 flex-shrink-0" />
                            <p className="text-xs text-rose-700">All answers use the <strong>STAR method</strong>. Personalized to your CV if uploaded.</p>
                        </div>
                        <div className="space-y-3">
                            {behavQs.map((q: any, i: number) => <QuestionCard key={i} q={q} index={i} color="rose" />)}
                        </div>
                    </div>
                );

            case "situational":
                return (
                    <div className="p-5 lg:p-8">
                        <h3 className="font-bold text-slate-900 text-lg mb-1">Situational Questions</h3>
                        <p className="text-xs text-slate-400 mb-5">Hypothetical scenarios to test problem-solving and decision-making.</p>
                        {situQs.length === 0
                            ? <div className="text-center py-10 bg-slate-50 rounded-2xl border border-dashed border-slate-200"><HelpCircle className="w-7 h-7 text-slate-200 mx-auto mb-2" /><p className="text-sm text-slate-400">No situational questions.</p></div>
                            : <div className="space-y-3">{situQs.map((q: any, i: number) => <QuestionCard key={i} q={q} index={i} color="amber" />)}</div>
                        }
                    </div>
                );

            case "sysdesign":
                return (
                    <div className="p-5 lg:p-8">
                        <h3 className="font-bold text-slate-900 text-lg mb-1">System Design Questions</h3>
                        <p className="text-xs text-slate-400 mb-5">Architecture challenges — expand each for full approach, evaluation criteria, and common pitfalls.</p>
                        {sysQs.length === 0
                            ? <div className="text-center py-10 bg-slate-50 rounded-2xl border border-dashed border-slate-200"><Layers className="w-7 h-7 text-slate-200 mx-auto mb-2" /><p className="text-sm text-slate-400">No system design questions generated (likely not a senior/technical role).</p></div>
                            : <div className="space-y-3">{sysQs.map((q: any, i: number) => <SystemDesignCard key={i} q={q} index={i} />)}</div>
                        }
                    </div>
                );

            case "coding":
                return (
                    <div className="p-5 lg:p-8">
                        <h3 className="font-bold text-slate-900 text-lg mb-1">Coding Challenges</h3>
                        <p className="text-xs text-slate-400 mb-5">Role-specific problems with optimal solutions, complexity analysis, and edge cases.</p>
                        {codeQs.length === 0
                            ? <div className="text-center py-10 bg-slate-50 rounded-2xl border border-dashed border-slate-200"><Code2 className="w-7 h-7 text-slate-200 mx-auto mb-2" /><p className="text-sm text-slate-400">No coding challenges generated for this role.</p></div>
                            : <div className="space-y-4">{codeQs.map((q: any, i: number) => <CodingChallengeCard key={i} q={q} index={i} />)}</div>
                        }
                    </div>
                );

            case "cultural":
                return (
                    <div className="p-5 lg:p-8">
                        <h3 className="font-bold text-slate-900 text-lg mb-1">Culture & Values Questions</h3>
                        <p className="text-xs text-slate-400 mb-5">Company-specific culture fit questions — what they really want to see.</p>
                        {cultQs.length === 0
                            ? <div className="text-center py-10 bg-slate-50 rounded-2xl border border-dashed border-slate-200"><Palette className="w-7 h-7 text-slate-200 mx-auto mb-2" /><p className="text-sm text-slate-400">No culture questions generated.</p></div>
                            : <div className="space-y-3">{cultQs.map((q: any, i: number) => <QuestionCard key={i} q={q} index={i} color="pink" />)}</div>
                        }
                    </div>
                );

            case "ask":
                return (
                    <div className="p-5 lg:p-8">
                        <h3 className="font-bold text-slate-900 text-lg mb-1">Questions to Ask the Interviewer</h3>
                        <p className="text-xs text-slate-400 mb-5">Smart questions that signal expertise and genuine interest. Mix technical, strategic, and cultural.</p>
                        {askQs.length === 0
                            ? <div className="text-center py-10 bg-slate-50 rounded-2xl border border-dashed border-slate-200"><MessageSquare className="w-7 h-7 text-slate-200 mx-auto mb-2" /><p className="text-sm text-slate-400">No questions generated. Try regenerating.</p></div>
                            : <div className="space-y-3">
                                {askQs.map((q: string, i: number) => (
                                    <div key={i} className="bg-white border border-slate-100 rounded-2xl p-4 flex items-start gap-3 hover:border-green-200 hover:shadow-md transition-all group">
                                        <div className="w-7 h-7 rounded-xl bg-green-50 flex items-center justify-center flex-shrink-0 border border-green-100">
                                            <span className="text-[10px] font-bold text-green-600">{i + 1}</span>
                                        </div>
                                        <p className="flex-1 text-sm text-slate-700 leading-relaxed font-medium">{q}</p>
                                        <CopyButton text={q} />
                                    </div>
                                ))}
                            </div>
                        }
                    </div>
                );

            case "salary":
                return (
                    <div className="p-5 lg:p-8">
                        <h3 className="font-bold text-slate-900 text-lg mb-5">Salary Research & Negotiation</h3>
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                            <div className="bg-gradient-to-br from-emerald-500 to-emerald-600 rounded-2xl p-6 text-white">
                                <div className="flex items-center gap-2 mb-3">
                                    <Banknote size={16} className="text-emerald-100" />
                                    <span className="text-xs font-bold uppercase tracking-wider text-emerald-100">Market Range</span>
                                </div>
                                <div className="text-3xl font-bold mb-2">{salary.market_range || "Research on Glassdoor"}</div>
                                <p className="text-sm text-emerald-100">{selectedJob?.title} at {selectedJob?.company}</p>
                                {salary.counter_offer_script && (
                                    <div className="mt-4 pt-4 border-t border-white/20">
                                        <p className="text-[10px] font-bold text-emerald-200 uppercase tracking-wider mb-1">Counter Offer Script</p>
                                        <p className="text-xs text-white/90 italic">"{salary.counter_offer_script}"</p>
                                    </div>
                                )}
                                <div className="mt-4 pt-4 border-t border-white/20 flex gap-4 text-xs text-emerald-100">
                                    <a href={`https://www.glassdoor.com/Salary/${selectedJob?.company?.replace(/\s+/g, "-")}-Salaries-E0.htm`} target="_blank" rel="noopener noreferrer" className="underline hover:text-white">Glassdoor →</a>
                                    <a href={`https://www.levels.fyi/?compare=${selectedJob?.company}`} target="_blank" rel="noopener noreferrer" className="underline hover:text-white">Levels.fyi →</a>
                                    <a href="https://www.linkedin.com/salary/" target="_blank" rel="noopener noreferrer" className="underline hover:text-white">LinkedIn →</a>
                                </div>
                            </div>
                            <div className="space-y-4">
                                <div className="bg-white border border-slate-100 rounded-2xl p-5">
                                    <div className="flex items-center gap-2 mb-4">
                                        <div className="p-1.5 bg-amber-50 rounded-lg"><Lightbulb size={14} className="text-amber-600" /></div>
                                        <h4 className="font-bold text-slate-800">Negotiation Tactics</h4>
                                    </div>
                                    <ul className="space-y-2.5">
                                        {(salary.negotiation_tips || []).map((tip: string, i: number) => (
                                            <li key={i} className="flex gap-2.5 items-start">
                                                <span className="w-5 h-5 rounded-full bg-emerald-50 border border-emerald-200 flex items-center justify-center text-[9px] font-bold text-emerald-600 flex-shrink-0 mt-0.5">{i + 1}</span>
                                                <p className="text-xs text-slate-600 leading-relaxed">{tip}</p>
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                                {salary.initial_ask_script && (
                                    <div className="bg-blue-50 border border-blue-100 rounded-2xl p-4">
                                        <p className="text-[10px] font-bold text-blue-600 uppercase tracking-wider mb-2">When Asked "What's Your Salary Expectation?"</p>
                                        <p className="text-xs text-slate-700 italic leading-relaxed">"{salary.initial_ask_script}"</p>
                                    </div>
                                )}
                                {(salary.red_flags || []).length > 0 && (
                                    <div className="bg-red-50 border border-red-100 rounded-2xl p-4">
                                        <p className="text-[10px] font-bold text-red-500 uppercase tracking-wider mb-2">Red Flags (Lowball Signs)</p>
                                        <ul className="space-y-1.5">
                                            {salary.red_flags.map((rf: string, i: number) => (
                                                <li key={i} className="text-xs text-slate-700 flex items-start gap-1.5">
                                                    <X size={10} className="text-red-400 flex-shrink-0 mt-0.5" /> {rf}
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                );

            case "plan":
                return (
                    <div className="p-5 lg:p-8">
                        <h3 className="font-bold text-slate-900 text-lg mb-1">7-Day Study Plan</h3>
                        <p className="text-xs text-slate-400 mb-5">Your personalised preparation schedule to ace the interview.</p>
                        {Object.keys(studyPlan).length === 0
                            ? <div className="text-center py-10 bg-slate-50 rounded-2xl border border-dashed border-slate-200"><CalendarDays className="w-7 h-7 text-slate-200 mx-auto mb-2" /><p className="text-sm text-slate-400">No study plan generated.</p></div>
                            : (
                                <div className="space-y-3">
                                    {Object.entries(studyPlan).map(([day, focus]: [string, any], i) => (
                                        <motion.div
                                            key={day}
                                            initial={{ opacity: 0, x: -10 }}
                                            animate={{ opacity: 1, x: 0 }}
                                            transition={{ delay: i * 0.05 }}
                                            className="flex gap-4 items-start bg-white border border-slate-100 rounded-2xl p-4 hover:border-rose-100 hover:shadow-sm transition-all"
                                        >
                                            <div className={`w-10 h-10 rounded-xl flex flex-col items-center justify-center flex-shrink-0 ${
                                                i === 0 ? "bg-rose-100 border border-rose-200" :
                                                i === 6 ? "bg-green-100 border border-green-200" :
                                                "bg-slate-100 border border-slate-200"
                                            }`}>
                                                <span className={`text-[8px] font-bold uppercase ${i === 0 ? "text-rose-500" : i === 6 ? "text-green-600" : "text-slate-500"}`}>Day</span>
                                                <span className={`text-sm font-bold ${i === 0 ? "text-rose-600" : i === 6 ? "text-green-700" : "text-slate-700"}`}>{i + 1}</span>
                                            </div>
                                            <div className="flex-1">
                                                <p className="text-xs font-bold text-slate-800 mb-0.5 capitalize">{day.replace("_", " ").replace(/\b\w/g, l => l.toUpperCase())}</p>
                                                <p className="text-xs text-slate-600 leading-relaxed">{String(focus)}</p>
                                            </div>
                                            {i === 6 && <span className="text-[10px] px-2 py-1 bg-green-100 text-green-700 rounded-full border border-green-200 font-semibold flex-shrink-0">Interview Day</span>}
                                        </motion.div>
                                    ))}
                                </div>
                            )
                        }
                    </div>
                );

            default:
                return null;
        }
    };

    // ── Render ───────────────────────────────────────────────────────────────
    return (
        <div className="h-full flex bg-white overflow-hidden relative">
            {/* Desktop sidebar */}
            <div className="hidden lg:flex w-56 border-r border-slate-100 flex-col flex-shrink-0">
                <SidebarContent />
            </div>

            {/* Mobile sidebar overlay */}
            <AnimatePresence>
                {sidebarOpen && (
                    <>
                        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                            onClick={() => setSidebarOpen(false)}
                            className="lg:hidden absolute inset-0 bg-black/20 z-20" />
                        <motion.div
                            initial={{ x: -260 }} animate={{ x: 0 }} exit={{ x: -260 }}
                            transition={{ type: "spring", damping: 28, stiffness: 300 }}
                            className="lg:hidden absolute left-0 top-0 bottom-0 w-56 z-30 shadow-2xl">
                            <SidebarContent />
                        </motion.div>
                    </>
                )}
            </AnimatePresence>

            {/* Main area */}
            <div className="flex-1 flex flex-col overflow-hidden min-w-0">
                {/* Mobile topbar */}
                <div className="lg:hidden flex items-center gap-2 px-4 py-2.5 border-b border-slate-100 bg-white flex-shrink-0">
                    <button onClick={() => setSidebarOpen(true)}
                        className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl border border-slate-200 text-xs font-semibold text-slate-600 hover:bg-slate-50 transition-all flex-shrink-0">
                        <LayoutList size={12} /> Jobs
                    </button>
                    {selectedJob ? (
                        <div className="flex-1 min-w-0">
                            <p className="text-xs font-bold text-slate-900 truncate">{selectedJob.title}</p>
                            <p className="text-[10px] text-slate-400 truncate">{selectedJob.company}</p>
                        </div>
                    ) : (
                        <p className="text-xs text-slate-400">Select a job to begin</p>
                    )}
                </div>

                <AnimatePresence mode="wait">
                    {!selectedJobId ? (
                        <motion.div key="empty" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                            className="flex-1 flex flex-col items-center justify-center p-8 text-center bg-slate-50/30">
                            <div className="w-20 h-20 bg-white rounded-3xl flex items-center justify-center mb-5 shadow-lg border border-slate-100">
                                <Brain size={36} className="text-rose-500" />
                            </div>
                            <h2 className="text-2xl font-bold text-slate-900 mb-2">Interview Prep</h2>
                            <p className="text-slate-500 text-sm max-w-sm leading-relaxed mb-6">
                                Select a job to generate an elite interview strategy — deep technical questions, STAR behavioral prep, system design, coding challenges, salary strategy, and a 7-day study plan.
                            </p>
                            <button onClick={() => setSidebarOpen(true)}
                                className="lg:hidden px-5 h-10 bg-rose-600 text-white rounded-xl text-sm font-bold flex items-center gap-2 hover:bg-rose-700 transition-all mx-auto shadow-lg shadow-rose-200">
                                <LayoutList size={15} /> Choose a Job
                            </button>
                            <div className="hidden lg:grid grid-cols-3 gap-3 mt-4 w-full max-w-lg">
                                {[
                                    { icon: Cpu,          label: "12+ Technical Qs",   desc: "Role & stack-specific" },
                                    { icon: Layers,       label: "System Design",       desc: "Architecture challenges" },
                                    { icon: Code2,        label: "Coding Challenges",   desc: "With optimal solutions" },
                                    { icon: UserCheck,    label: "STAR Behavioral",     desc: "CV-personalised answers" },
                                    { icon: Bot,          label: "AI Coach Chat",       desc: "Practice & get feedback" },
                                    { icon: CalendarDays, label: "7-Day Study Plan",    desc: "Structured prep schedule" },
                                ].map((f, i) => (
                                    <div key={i} className="p-4 bg-white rounded-2xl border border-slate-100 shadow-sm flex flex-col items-center text-center">
                                        <f.icon className="text-rose-500 mb-2" size={20} />
                                        <span className="text-xs font-bold text-slate-800 mb-1">{f.label}</span>
                                        <span className="text-[10px] text-slate-400">{f.desc}</span>
                                    </div>
                                ))}
                            </div>
                        </motion.div>

                    ) : generating ? (
                        <motion.div key="gen" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex-1 flex flex-col overflow-hidden">
                            <GeneratingState jobTitle={selectedJob?.title || ""} company={selectedJob?.company || ""} />
                        </motion.div>

                    ) : genError ? (
                        <motion.div key="err" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex-1 flex flex-col items-center justify-center p-8 text-center">
                            <div className="w-16 h-16 bg-rose-50 rounded-2xl flex items-center justify-center mb-4">
                                <AlertCircle size={28} className="text-rose-500" />
                            </div>
                            <h3 className="font-bold text-slate-900 mb-2">Generation Failed</h3>
                            <p className="text-sm text-slate-500 mb-5 max-w-xs">{genError}</p>
                            <button onClick={handleGenerate} className="px-5 h-10 bg-rose-600 text-white rounded-xl text-sm font-bold flex items-center gap-2 hover:bg-rose-700 transition-all mx-auto">
                                <RefreshCw size={15} /> Try Again
                            </button>
                        </motion.div>

                    ) : !activePrep ? (
                        <motion.div key="ready" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex-1 flex flex-col items-center justify-center p-8 text-center">
                            <div className="w-16 h-16 bg-amber-50 rounded-2xl flex items-center justify-center mb-5 border border-amber-100">
                                <Sparkles size={28} className="text-amber-500" />
                            </div>
                            <h3 className="text-xl font-bold text-slate-900 mb-2">Ready to Generate</h3>
                            <p className="text-slate-500 text-sm mb-1 max-w-xs">No prep found for <strong>{selectedJob?.company}</strong>.</p>
                            <p className="text-slate-400 text-xs mb-6 max-w-xs">
                                Will generate: 12+ technical Qs, behavioral STAR answers, system design, coding challenges, culture fit, salary strategy, and a 7-day study plan.
                            </p>
                            <button onClick={handleGenerate}
                                className="px-6 h-11 bg-rose-600 text-white rounded-xl font-bold flex items-center gap-2.5 hover:bg-rose-700 shadow-lg shadow-rose-100 transition-all hover:scale-105 active:scale-95 text-sm mx-auto">
                                <Brain size={17} /> Generate Elite Strategy
                            </button>
                            <p className="text-[10px] text-slate-300 mt-4">Usually takes 1–3 minutes</p>
                        </motion.div>

                    ) : activePrep && totalQuestions === 0 && !generating ? (
                        // Prep exists but has no data (previous generation failed silently)
                        <motion.div key="empty-data" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex-1 flex flex-col items-center justify-center p-8 text-center">
                            <div className="w-16 h-16 bg-amber-50 rounded-2xl flex items-center justify-center mb-4 border border-amber-100">
                                <AlertCircle size={28} className="text-amber-500" />
                            </div>
                            <h3 className="font-bold text-slate-900 mb-2">No Questions Generated</h3>
                            <p className="text-sm text-slate-500 mb-5 max-w-xs">
                                The previous generation didn't produce any content. This usually happens when the AI model is overloaded.
                                Click below to try again.
                            </p>
                            <button onClick={handleGenerate} className="px-6 h-11 bg-rose-600 text-white rounded-xl font-bold flex items-center gap-2.5 hover:bg-rose-700 shadow-lg shadow-rose-100 transition-all text-sm mx-auto">
                                <RefreshCw size={15} /> Regenerate Strategy
                            </button>
                        </motion.div>

                    ) : (
                        <motion.div key="content" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="flex-1 flex overflow-hidden">
                            {/* Prep content area */}
                            <div className="flex-1 flex flex-col overflow-hidden min-w-0">
                                {/* Header */}
                                <div className="px-4 lg:px-6 py-3 border-b border-slate-100 bg-white flex-shrink-0">
                                    <div className="flex items-center justify-between gap-3">
                                        <div className="min-w-0">
                                            <div className="flex items-center gap-2 mb-0.5">
                                                <span className="flex items-center gap-1 px-2 py-0.5 bg-green-50 text-green-700 rounded-full text-[9px] font-bold uppercase tracking-wider border border-green-100">
                                                    <CheckCircle2 size={9} /> Ready
                                                </span>
                                                {activePrep.created_at && (
                                                    <span className="text-[10px] text-slate-400 flex items-center gap-1">
                                                        <Clock size={9} />
                                                        {new Date(activePrep.created_at).toLocaleDateString()}
                                                    </span>
                                                )}
                                                <span className="text-[10px] text-slate-400">· {totalQuestions} questions</span>
                                            </div>
                                            <h2 className="text-base font-bold text-slate-900 truncate">
                                                {selectedJob?.title} <span className="text-slate-400 font-normal">at</span> {selectedJob?.company}
                                            </h2>
                                        </div>
                                        <div className="flex items-center gap-2 flex-shrink-0">
                                            {/* AI Coach toggle */}
                                            <motion.button
                                                onClick={() => setChatOpen(!chatOpen)}
                                                whileHover={{ scale: 1.02 }}
                                                whileTap={{ scale: 0.97 }}
                                                className={`flex items-center gap-1.5 px-3 h-8 rounded-xl text-xs font-semibold transition-all shadow-sm ${
                                                    chatOpen
                                                        ? "bg-rose-600 text-white border border-rose-600"
                                                        : "bg-white border border-slate-200 text-slate-600 hover:bg-slate-50"
                                                }`}
                                            >
                                                <Bot size={12} />
                                                AI Coach
                                                {chatOpen && <X size={10} className="ml-0.5" />}
                                            </motion.button>
                                            <button onClick={handleGenerate}
                                                className="flex items-center gap-1.5 px-3 h-8 bg-white border border-slate-200 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-50 transition-all shadow-sm">
                                                <RefreshCw size={11} /> Refresh
                                            </button>
                                        </div>
                                    </div>

                                    {/* Tabs */}
                                    <div className="flex gap-0.5 mt-3 overflow-x-auto pb-0.5" style={{ scrollbarWidth: "none" }}>
                                        {TABS.map(tab => {
                                            const count = badgeCount[tab.key];
                                            const isActive = activeTab === tab.key;
                                            return (
                                                <button key={tab.key} onClick={() => setActiveTab(tab.key)}
                                                    className={`flex-shrink-0 flex items-center gap-1.5 px-3 h-8 rounded-xl text-xs font-semibold transition-all whitespace-nowrap ${
                                                        isActive ? "bg-slate-900 text-white" : "text-slate-500 hover:bg-slate-100"
                                                    }`}>
                                                    <tab.icon size={12} />
                                                    {tab.label}
                                                    {count != null && count > 0 && (
                                                        <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded-full ${isActive ? "bg-white/20 text-white" : "bg-slate-200 text-slate-500"}`}>
                                                            {count}
                                                        </span>
                                                    )}
                                                </button>
                                            );
                                        })}
                                    </div>
                                </div>

                                {/* Tab content */}
                                <ScrollArea className="flex-1">
                                    <AnimatePresence mode="wait">
                                        <motion.div
                                            key={activeTab}
                                            initial={{ opacity: 0, y: 6 }}
                                            animate={{ opacity: 1, y: 0 }}
                                            exit={{ opacity: 0 }}
                                            transition={{ duration: 0.15 }}
                                        >
                                            {renderTabContent()}
                                        </motion.div>
                                    </AnimatePresence>
                                </ScrollArea>
                            </div>

                            {/* AI Coach Panel */}
                            <AnimatePresence>
                                {chatOpen && (
                                    <motion.div
                                        initial={{ width: 0, opacity: 0 }}
                                        animate={{ width: 320, opacity: 1 }}
                                        exit={{ width: 0, opacity: 0 }}
                                        transition={{ type: "spring", damping: 30, stiffness: 300 }}
                                        className="flex-shrink-0 overflow-hidden"
                                        style={{ minWidth: chatOpen ? 320 : 0 }}
                                    >
                                        <CoachChatPanel
                                            prepId={activePrep.id}
                                            jobTitle={selectedJob?.title || ""}
                                            company={selectedJob?.company || ""}
                                        />
                                    </motion.div>
                                )}
                            </AnimatePresence>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>
        </div>
    );
}
