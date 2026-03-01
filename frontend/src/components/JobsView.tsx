import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Briefcase, MapPin, Building2, Clock, CheckCircle2,
  MessageCircle, ExternalLink, Search, Sparkles, Brain, Send,
  ChevronDown, DollarSign, Layers, RefreshCw, X, TrendingUp,
  Bookmark, Filter, ChevronRight, FileText
} from "lucide-react";
import { listJobs, listApplications, sendChatMessage, downloadTailoredCV } from "@/services/api";
import { ScrollArea } from "@/components/ui/scroll-area";

interface JobsViewProps {
  onNavigateToInterview?: (jobId: string) => void;
}

type TabType = "discovered" | "applied" | "interview" | "rejected";

const STATUS_STYLES: Record<string, string> = {
  interview:  "bg-amber-50 border-amber-200 text-amber-700",
  rejected:   "bg-rose-50 border-rose-200 text-rose-700",
  sent:       "bg-emerald-50 border-emerald-200 text-emerald-700",
  pending_approval: "bg-violet-50 border-violet-200 text-violet-700",
  applied:    "bg-blue-50 border-blue-200 text-blue-700",
};

export function JobsView({ onNavigateToInterview }: JobsViewProps) {
  const [activeTab, setActiveTab] = useState<TabType>("discovered");
  const [jobs, setJobs] = useState<any[]>([]);
  const [applications, setApplications] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [expandedJob, setExpandedJob] = useState<string | null>(null);

  // Inline chat
  const [chatInput, setChatInput] = useState("");
  const [chatMessages, setChatMessages] = useState<{ role: "user" | "agent"; text: string }[]>([]);
  const [chatOpen, setChatOpen] = useState(false);
  const [chatSending, setChatSending] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const sessionRef = useRef<string>(`jobs-${Date.now()}`);
  const inputRef = useRef<HTMLInputElement>(null);

  const fetchData = () => {
    setLoading(true);
    Promise.all([
      listJobs(undefined, 100, 0).catch(() => ({ jobs: [] })),
      listApplications().catch(() => ({ applications: [] })),
    ]).then(([j, a]) => {
      setJobs((j as any).jobs || []);
      setApplications((a as any).applications || []);
      setLoading(false);
    });
  };

  useEffect(() => { fetchData(); }, []);
  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [chatMessages]);

  // "Actually applied" = email sent or manually marked applied, interview, rejected
  // "pending_approval" = AI prepared it but user hasn't approved the send yet → stays in Discovered
  const TRULY_APPLIED_STATUSES = new Set(["sent", "applied", "interview", "rejected"]);
  const trulyAppliedJobIds  = new Set(
    applications.filter(a => TRULY_APPLIED_STATUSES.has(a.status)).map((a: any) => a.job_id)
  );
  const pendingApprovalJobIds = new Set(
    applications.filter(a => a.status === "pending_approval").map((a: any) => a.job_id)
  );

  const q = searchQuery.toLowerCase();
  const matchesSearch = (job: any) =>
    !q || job?.title?.toLowerCase().includes(q) || job?.company?.toLowerCase().includes(q);

  const tabData = {
    // Discovered: jobs NOT yet truly applied to (pending_approval stays here with a badge)
    discovered: jobs.filter(j => !trulyAppliedJobIds.has(j.id) && matchesSearch(j)),

    // Applied: only applications where the email was actually sent
    applied: applications.filter(a => {
      if (a.status !== "sent" && a.status !== "applied") return false;
      const j = a.job ?? jobs.find((jj: any) => jj.id === a.job_id);
      return matchesSearch(j);
    }),

    interview: applications.filter(a => a.status === "interview"),
    rejected:  applications.filter(a => a.status === "rejected"),
  };

  const TABS = [
    { key: "discovered" as TabType, label: "Discovered", count: tabData.discovered.length, emoji: "🔍" },
    { key: "applied"    as TabType, label: "Applied",    count: tabData.applied.length,    emoji: "📨" },
    { key: "interview"  as TabType, label: "Interview",  count: tabData.interview.length,  emoji: "🎯" },
    { key: "rejected"   as TabType, label: "Rejected",   count: tabData.rejected.length,   emoji: "❌" },
  ];

  const handleSendChat = async () => {
    if (!chatInput.trim() || chatSending) return;
    const msg = chatInput.trim();
    setChatInput("");
    setChatMessages(prev => [...prev, { role: "user", text: msg }]);
    setChatSending(true);
    try {
      // Build a compact job context so the AI only answers about the current list
      const jobList = jobs.slice(0, 20).map(j => {
        const match = j.match_score != null ? ` [${Math.round(j.match_score * 100)}% match]` : "";
        const loc = j.location ? ` · ${j.location}` : "";
        const sal = (j.salary_min || j.salary_max)
          ? ` · $${j.salary_min ? Math.round(j.salary_min / 1000) + "k" : ""}${j.salary_max ? "–" + Math.round(j.salary_max / 1000) + "k" : ""}`
          : "";
        const type = j.job_type ? ` · ${j.job_type}` : "";
        const desc = j.description ? ` — ${j.description.slice(0, 120)}` : "";
        return `• [ID:${j.id}] ${j.title} at ${j.company}${loc}${sal}${type}${match}${desc}`;
      }).join("\n");

      const contextualMsg = jobList
        ? `[JOBS_VIEW]\nYou are a specialized jobs assistant. Answer ONLY questions about the jobs listed below. If the question is unrelated to these specific jobs, say "I don't have context for that in the current job list."\n\nCurrent jobs:\n${jobList}\n\nUser: ${msg}`
        : msg;

      const res = await sendChatMessage(contextualMsg, sessionRef.current);
      setChatMessages(prev => [...prev, { role: "agent", text: res.content }]);
    } catch {
      setChatMessages(prev => [...prev, { role: "agent", text: "Sorry, something went wrong." }]);
    } finally {
      setChatSending(false);
    }
  };

  const startApply = (job: any, jobId: string) => {
    const msg = `Tailor my CV and apply for ${job.title} at ${job.company} (job ID: ${jobId})`;
    setChatInput(msg);
    setChatOpen(true);
    setTimeout(() => inputRef.current?.focus(), 100);
  };

  const renderJobCard = (item: any, isApplication = false) => {
    const job = isApplication ? (item.job ?? jobs.find((j: any) => j.id === item.job_id)) : item;
    if (!job) return null;

    const jobId = isApplication ? item.job_id : item.id;
    const cardKey = isApplication ? item.id : item.id;
    const appStatus = isApplication
      ? item.status
      : pendingApprovalJobIds.has(item.id)
        ? "pending_approval"
        : null;
    const isExpanded = expandedJob === cardKey;

    const matchPct = job.match_score != null ? Math.round(job.match_score * 100) : null;
    const matchColor =
      matchPct == null ? "" :
      matchPct >= 80 ? "bg-emerald-500 text-white" :
      matchPct >= 60 ? "bg-amber-500 text-white" :
      "bg-slate-200 text-slate-600";

    return (
      <motion.div
        key={cardKey}
        layout
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-white rounded-2xl border border-slate-100 hover:border-rose-200 hover:shadow-md transition-all overflow-hidden group"
      >
        <div className="p-4 flex gap-3">
          {/* Left: logo area */}
          <div className="flex-shrink-0 relative">
            <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-slate-50 to-slate-100 border border-slate-200 flex items-center justify-center shadow-sm">
              <span className="text-lg font-bold text-slate-400">
                {(job.company || "?")[0].toUpperCase()}
              </span>
            </div>
            {matchPct != null && (
              <div className={`absolute -top-1.5 -right-1.5 text-[9px] font-bold px-1.5 py-0.5 rounded-full shadow-sm ${matchColor}`}>
                {matchPct}%
              </div>
            )}
          </div>

          {/* Center: info */}
          <div className="flex-1 min-w-0">
            <div className="flex flex-wrap items-start gap-1.5 mb-1">
              <h4 className="font-bold text-slate-900 text-sm leading-tight truncate max-w-[280px]">
                {job.title || "Unknown Position"}
              </h4>
              {appStatus && (
                <span className={`text-[9px] font-bold uppercase tracking-wide px-1.5 py-0.5 rounded-full border flex-shrink-0 ${STATUS_STYLES[appStatus] || STATUS_STYLES.applied}`}>
                  {appStatus.replace(/_/g, " ")}
                </span>
              )}
            </div>

            <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-slate-500">
              <span className="font-semibold text-slate-700">{job.company}</span>
              {job.location && (
                <span className="flex items-center gap-1">
                  <MapPin size={10} className="text-slate-400" />
                  {job.location}
                </span>
              )}
              {job.job_type && (
                <span className="flex items-center gap-1">
                  <Layers size={10} className="text-slate-400" />
                  {job.job_type}
                </span>
              )}
              {(job.salary_min || job.salary_max) && (
                <span className="flex items-center gap-1 text-emerald-600 font-semibold">
                  <DollarSign size={10} />
                  {job.salary_min && job.salary_max
                    ? `$${(job.salary_min / 1000).toFixed(0)}k–$${(job.salary_max / 1000).toFixed(0)}k`
                    : job.salary_min
                      ? `From $${(job.salary_min / 1000).toFixed(0)}k`
                      : `Up to $${(job.salary_max / 1000).toFixed(0)}k`}
                </span>
              )}
            </div>

            {/* Matching skills pills */}
            {job.matching_skills?.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-2">
                {job.matching_skills.slice(0, 4).map((s: string) => (
                  <span key={s} className="text-[9px] font-medium px-1.5 py-0.5 bg-emerald-50 text-emerald-700 border border-emerald-100 rounded-full">
                    {s}
                  </span>
                ))}
                {job.matching_skills.length > 4 && (
                  <span className="text-[9px] text-slate-400">+{job.matching_skills.length - 4} more</span>
                )}
              </div>
            )}
          </div>

          {/* Right: actions */}
          <div className="flex-shrink-0 flex flex-col items-end gap-2">
            <div className="flex items-center gap-1">
              {job.application_url && (
                <a href={job.application_url} target="_blank" rel="noopener noreferrer"
                  className="w-7 h-7 rounded-lg bg-slate-50 text-slate-400 hover:bg-rose-50 hover:text-rose-600 transition-all flex items-center justify-center border border-slate-200 hover:border-rose-200"
                >
                  <ExternalLink size={12} />
                </a>
              )}
              <button
                onClick={() => setExpandedJob(isExpanded ? null : cardKey)}
                className="w-7 h-7 rounded-lg bg-slate-50 text-slate-400 hover:bg-slate-100 transition-all flex items-center justify-center border border-slate-200"
              >
                <ChevronDown size={12} className={`transition-transform duration-200 ${isExpanded ? "rotate-180" : ""}`} />
              </button>
            </div>

            <div className="flex items-center gap-1">
              {/* View tailored CV PDF — shown on applied cards that have one */}
              {isApplication && item.tailored_cv_id && (
                <button
                  onClick={() => downloadTailoredCV(item.tailored_cv_id).catch(console.error)}
                  className="h-7 px-2.5 rounded-lg bg-rose-50 text-rose-600 border border-rose-200 text-[10px] font-bold hover:bg-rose-100 transition-all flex items-center gap-1"
                  title="View tailored CV PDF"
                >
                  <FileText size={10} /> CV
                </button>
              )}
              {onNavigateToInterview && (
                <button
                  onClick={() => onNavigateToInterview(jobId)}
                  className="h-7 px-2.5 rounded-lg bg-violet-50 text-violet-700 border border-violet-200 text-[10px] font-bold hover:bg-violet-100 transition-all flex items-center gap-1"
                >
                  <Brain size={10} /> Prep
                </button>
              )}
              {!isApplication && (
                <button
                  onClick={() => startApply(job, jobId)}
                  className="h-7 px-2.5 rounded-lg bg-slate-900 text-white text-[10px] font-bold hover:bg-rose-600 transition-all flex items-center gap-1"
                >
                  <Sparkles size={10} className="text-rose-300" />
                  Apply
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Expanded description */}
        <AnimatePresence>
          {isExpanded && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="border-t border-slate-100 bg-slate-50/60"
            >
              <div className="px-4 py-3 space-y-2">
                {job.description && (
                  <p className="text-xs text-slate-600 leading-relaxed">{job.description}</p>
                )}
                {job.missing_skills?.length > 0 && (
                  <div>
                    <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wider">Skill gaps</span>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {job.missing_skills.slice(0, 5).map((s: string) => (
                        <span key={s} className="text-[9px] px-1.5 py-0.5 bg-rose-50 text-rose-600 border border-rose-100 rounded-full">
                          {s}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {job.source && (
                  <p className="text-[9px] text-slate-400 uppercase tracking-wide">Source: {job.source}</p>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    );
  };

  const currentItems = tabData[activeTab];
  const matchAvg = (() => {
    const scored = jobs.filter(j => j.match_score != null);
    if (!scored.length) return "—";
    return `${Math.round(scored.reduce((a, j) => a + j.match_score, 0) / scored.length * 100)}%`;
  })();
  const statsRow = [
    { label: "Discovered", val: tabData.discovered.length, color: "text-violet-600", bg: "bg-violet-50" },
    { label: "Applied",    val: tabData.applied.length,    color: "text-blue-600",   bg: "bg-blue-50"   },
    { label: "Interview",  val: tabData.interview.length,  color: "text-amber-600",  bg: "bg-amber-50"  },
    { label: "Match Avg",  val: matchAvg,                  color: "text-emerald-600", bg: "bg-emerald-50" },
  ];

  return (
    <div className="h-full flex flex-col bg-slate-50 relative overflow-hidden">
      {/* Header */}
      <div className="bg-white border-b border-slate-100 px-4 lg:px-6 py-4 flex-shrink-0">
        <div className="flex items-center justify-between gap-3 mb-4">
          <div>
            <h2 className="text-xl font-bold text-slate-900">Job Pipeline</h2>
            <p className="text-xs text-slate-400 mt-0.5">{tabData.discovered.length} to apply · {tabData.applied.length} sent · {tabData.interview.length} interview</p>
          </div>
          <div className="flex items-center gap-2">
            <div className="relative">
              <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
              <input
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                type="text"
                placeholder="Search..."
                className="pl-8 pr-3 h-8 border border-slate-200 rounded-xl text-xs outline-none focus:border-rose-400 focus:ring-2 focus:ring-rose-50 transition-all w-36 lg:w-48 bg-slate-50"
              />
            </div>
            <button
              onClick={fetchData}
              className="h-8 w-8 rounded-xl border border-slate-200 flex items-center justify-center hover:bg-slate-50 transition-all text-slate-400 hover:text-slate-600"
              title="Refresh"
            >
              <RefreshCw size={13} />
            </button>
          </div>
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-4 gap-2 mb-4">
          {statsRow.map(s => (
            <div key={s.label} className={`${s.bg} rounded-xl px-3 py-2 text-center`}>
              <div className={`text-lg font-bold ${s.color}`}>{s.val}</div>
              <div className="text-[9px] text-slate-500 uppercase tracking-wide font-medium">{s.label}</div>
            </div>
          ))}
        </div>

        {/* Tabs */}
        <div className="flex gap-1 overflow-x-auto pb-0.5" style={{ scrollbarWidth: "none" }}>
          {TABS.map(tab => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`flex-shrink-0 flex items-center gap-1.5 px-3 h-8 rounded-xl text-xs font-semibold transition-all whitespace-nowrap ${
                activeTab === tab.key
                  ? "bg-slate-900 text-white shadow-sm"
                  : "bg-transparent text-slate-500 hover:bg-slate-100"
              }`}
            >
              <span>{tab.emoji}</span>
              {tab.label}
              <span className={`px-1.5 py-0.5 rounded-full text-[9px] font-bold ${activeTab === tab.key ? "bg-white/20 text-white" : "bg-slate-200 text-slate-500"}`}>
                {tab.count}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Job list */}
      <ScrollArea className="flex-1 px-3 lg:px-5 pt-3 pb-24">
        {loading ? (
          <div className="flex flex-col gap-3">
            {Array(4).fill(0).map((_, i) => (
              <div key={i} className="h-24 bg-white rounded-2xl animate-pulse border border-slate-100" />
            ))}
          </div>
        ) : currentItems.length === 0 ? (
          <div className="text-center py-16 bg-white rounded-3xl border border-dashed border-slate-200 mt-1">
            <Briefcase size={28} className="text-slate-200 mx-auto mb-3" />
            <p className="text-slate-500 font-semibold text-sm">
              {activeTab === "discovered" ? "No jobs found yet" : "Nothing here yet"}
            </p>
            <p className="text-slate-400 text-xs mt-1 max-w-xs mx-auto">
              {activeTab === "discovered"
                ? 'Use the chat to say "Find me jobs in [your field]"'
                : "Complete the application flow to see jobs here"}
            </p>
            {activeTab === "discovered" && (
              <button
                onClick={() => setChatOpen(true)}
                className="mt-4 px-4 h-9 bg-slate-900 text-white rounded-xl text-xs font-bold hover:bg-rose-600 transition-all inline-flex items-center gap-2"
              >
                <MessageCircle size={13} /> Ask the Agent
              </button>
            )}
          </div>
        ) : (
          <div className="flex flex-col gap-2.5 pb-2">
            {activeTab === "discovered"
              ? currentItems.map((job: any) => renderJobCard(job, false))
              : currentItems.map((app: any) => renderJobCard(app, true))}
          </div>
        )}
      </ScrollArea>

      {/* Floating chat panel */}
      <AnimatePresence>
        {chatOpen && (
          <motion.div
            initial={{ y: "100%", opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: "100%", opacity: 0 }}
            transition={{ type: "spring", damping: 30, stiffness: 320 }}
            className="absolute bottom-0 left-0 right-0 bg-white border-t border-slate-200 shadow-2xl rounded-t-3xl z-20 flex flex-col"
            style={{ maxHeight: "60%" }}
          >
            {/* Handle */}
            <div className="flex justify-center pt-2 pb-1">
              <div className="w-10 h-1 rounded-full bg-slate-200" />
            </div>

            <div className="flex items-center justify-between px-4 pb-3">
              <div className="flex items-center gap-2">
                <div className="w-7 h-7 bg-slate-900 rounded-xl flex items-center justify-center">
                  <Sparkles size={13} className="text-rose-300" />
                </div>
                <div>
                  <span className="text-sm font-bold text-slate-800">CareerAgent</span>
                  <span className="text-xs text-slate-400 ml-2">· Jobs context</span>
                </div>
              </div>
              <button onClick={() => setChatOpen(false)} className="p-1.5 hover:bg-slate-100 rounded-xl transition-colors">
                <X size={15} className="text-slate-400" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto px-4 space-y-3 min-h-0">
              {chatMessages.length === 0 && (
                <div className="text-center py-4">
                  <p className="text-xs text-slate-400 mb-3">Ask anything about jobs or apply directly</p>
                  <div className="flex flex-wrap gap-1.5 justify-center">
                    {["Find AI engineer roles", "Which job matches me best?", "Tailor my CV"].map(s => (
                      <button key={s} onClick={() => setChatInput(s)}
                        className="text-xs px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-full text-slate-600 hover:border-rose-300 hover:bg-rose-50 transition-all">
                        {s}
                      </button>
                    ))}
                  </div>
                </div>
              )}
              {chatMessages.map((m, i) => (
                <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                  <div className={`max-w-[85%] px-3.5 py-2.5 rounded-2xl text-xs leading-relaxed ${
                    m.role === "user"
                      ? "bg-slate-900 text-white rounded-br-md"
                      : "bg-slate-50 text-slate-800 border border-slate-100 rounded-bl-md"
                  }`}>
                    {m.text}
                  </div>
                </div>
              ))}
              {chatSending && (
                <div className="flex justify-start">
                  <div className="bg-slate-50 border border-slate-100 px-4 py-3 rounded-2xl rounded-bl-md flex gap-1">
                    {[0,1,2].map(i => (
                      <div key={i} className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: `${i * 0.12}s` }} />
                    ))}
                  </div>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>

            <div className="px-4 py-3 border-t border-slate-100 mt-2">
              <div className="flex items-center gap-2 bg-slate-50 rounded-2xl border border-slate-200 focus-within:border-rose-400 focus-within:ring-2 focus-within:ring-rose-50 transition-all px-3 py-2">
                <input
                  ref={inputRef}
                  value={chatInput}
                  onChange={e => setChatInput(e.target.value)}
                  onKeyDown={e => e.key === "Enter" && !e.shiftKey && handleSendChat()}
                  placeholder="Ask about jobs, salary, or apply..."
                  className="flex-1 bg-transparent text-sm outline-none text-slate-800 placeholder:text-slate-400"
                />
                <button
                  onClick={handleSendChat}
                  disabled={chatSending || !chatInput.trim()}
                  className="w-7 h-7 bg-slate-900 rounded-xl flex items-center justify-center text-white hover:bg-rose-600 transition-all disabled:opacity-30 flex-shrink-0"
                >
                  <Send size={12} />
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Bottom chat trigger */}
      {!chatOpen && (
        <div className="absolute bottom-0 left-0 right-0 px-3 lg:px-5 pb-3 pt-6 bg-gradient-to-t from-slate-50 via-slate-50/90 to-transparent pointer-events-none flex-shrink-0">
          <button
            onClick={() => { setChatOpen(true); setTimeout(() => inputRef.current?.focus(), 100); }}
            className="pointer-events-auto w-full flex items-center gap-3 bg-white border border-slate-200 hover:border-rose-300 hover:shadow-md rounded-2xl px-4 py-3 text-sm text-slate-400 hover:text-slate-600 transition-all shadow-sm group"
          >
            <div className="w-7 h-7 bg-slate-900 rounded-xl flex items-center justify-center flex-shrink-0 group-hover:bg-rose-600 transition-colors">
              <MessageCircle size={13} className="text-white" />
            </div>
            <span className="flex-1 text-left text-xs">Ask the agent about these jobs...</span>
            <kbd className="text-[10px] bg-slate-100 px-2 py-0.5 rounded-lg font-mono text-slate-400">⌘K</kbd>
          </button>
        </div>
      )}
    </div>
  );
}
