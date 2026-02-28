import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, ChevronUp, ArrowRight } from "lucide-react";
import { useAgentStore, LogEntry } from "@/stores/agent-store";

const FILTER_TABS = ["All", "Planner", "Scraper", "Evaluator", "Writer", "Errors"];

function LogNode({ entry, expanded, onToggle }: { entry: LogEntry; expanded: boolean; onToggle: () => void }) {
  const statusBadge: Record<string, { bg: string; text: string; label: string }> = {
    done: { bg: "bg-green-50", text: "text-green-600", label: "Done" },
    running: { bg: "bg-rose-50", text: "text-primary", label: "Running" },
    waiting: { bg: "bg-amber-50", text: "text-amber-600", label: "Paused" },
    error: { bg: "bg-red-50", text: "text-red-600", label: "Error" },
  };

  const dotColor: Record<string, string> = {
    done: "bg-primary",
    running: "bg-primary",
    waiting: "bg-amber-400",
    error: "bg-red-500",
  };

  const badge = statusBadge[entry.status] || statusBadge.running;
  const dot = dotColor[entry.status] || dotColor.running;

  return (
    <motion.div
      layout
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: "auto" }}
      exit={{ opacity: 0, height: 0 }}
      className="relative flex gap-3 mb-3"
    >
      {/* Timeline dot */}
      <div className="flex flex-col items-center flex-shrink-0 pt-3">
        <div className="relative">
          <div className={`w-2.5 h-2.5 rounded-full ${dot}`} />
          {entry.status === "running" && (
            <div className="absolute inset-0 w-2.5 h-2.5 rounded-full bg-primary animate-ping opacity-40" />
          )}
        </div>
      </div>

      {/* Card */}
      <div className="flex-1 bg-white border border-slate-100 rounded-lg p-3 shadow-sm hover:shadow-md hover:border-slate-200 transition-all">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-[11px] text-slate-400 font-mono">{entry.time}</span>
            <span className="text-[11px] font-semibold text-slate-700 font-sans">{entry.emoji} {entry.agent}</span>
          </div>
          <div className="flex items-center gap-2">
            {entry.duration && (
              <span className="bg-slate-50 text-slate-500 rounded-full px-2 py-0.5 text-[10px] font-sans">
                {entry.duration}
              </span>
            )}
            <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${badge.bg} ${badge.text}`}>
              {badge.label}
            </span>
          </div>
        </div>
        <p className="text-[13px] font-semibold text-slate-800 font-sans mt-1.5 leading-snug">{entry.title}</p>
        <p className="text-xs text-slate-500 font-sans leading-snug">{entry.desc}</p>
        {entry.tokens && (
          <p className="text-[10px] text-slate-400 font-mono mt-1">{entry.tokens}</p>
        )}

        {entry.thought && (
          <>
            <button
              onClick={onToggle}
              className="flex items-center gap-1 text-xs font-medium text-primary font-sans mt-2 hover:underline"
            >
              {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
              {expanded ? "Hide Reasoning" : "Show Reasoning"}
            </button>
            {expanded && (
              <div className="mt-2 bg-slate-50 border-l-2 border-rose-200 rounded-md p-3">
                <pre className="text-[11px] text-slate-600 font-mono whitespace-pre-wrap leading-relaxed">
                  {entry.thought}
                </pre>
              </div>
            )}
          </>
        )}
      </div>
    </motion.div>
  );
}

export function RightSidebar() {
  const [activeTab, setActiveTab] = useState("All");
  const scrollRef = useRef<HTMLDivElement>(null);
  const [expandedLogs, setExpandedLogs] = useState<Set<string>>(new Set());

  const logs = useAgentStore((state) => state.logs);
  const activeAgent = useAgentStore((state) => state.activeAgent);
  const completedNodes = useAgentStore((state) => state.completedNodes);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs]);

  const toggleLog = (id: string) => {
    setExpandedLogs((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const filteredLogs = logs.filter((log) => {
    if (activeTab === "All") return true;
    if (activeTab === "Planner") return log.agent === "supervisor";
    if (activeTab === "Scraper") return log.agent === "job_hunter";
    if (activeTab === "Evaluator") return log.agent === "cv_parser";
    if (activeTab === "Writer") return log.agent === "cv_tailor" || log.agent === "email_sender";
    if (activeTab === "Errors") return log.status === "error";
    return true;
  });

  return (
    <motion.aside
      className="w-[400px] h-full bg-[#FAFAFA] border-l border-slate-100 flex flex-col flex-shrink-0"
      initial={{ opacity: 0, x: 40 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ type: "spring", stiffness: 100, damping: 22, delay: 0.5 }}
    >
      <div className="p-5 flex-shrink-0">
        {/* Header */}
        <div className="flex items-center justify-between">
          <span className="text-[15px] font-semibold text-foreground font-sans">Agent Activity</span>
          <div className="flex items-center gap-1.5">
            <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
            <span className="text-[11px] font-semibold text-green-600 font-sans">Live</span>
          </div>
        </div>

        {/* Filter Tabs */}
        <div className="flex gap-2 mt-3 overflow-x-auto pb-1 no-scrollbar">
          {FILTER_TABS.map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-3 py-1 rounded-full text-[11px] font-medium font-sans whitespace-nowrap transition-colors ${activeTab === tab
                ? "bg-primary text-white"
                : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                }`}
            >
              {tab}
            </button>
          ))}
        </div>

        {/* Mini Agent Graph */}
        <div className="mt-4 flex items-center gap-2 overflow-x-auto pb-2 no-scrollbar">
          {[
            { name: "Parser", id: "cv_parser" },
            { name: "Scraper", id: "job_hunter" },
            { name: "Evaluator", id: "supervisor" },
            { name: "Tailor", id: "cv_tailor" },
            { name: "Comms", id: "hr_finder" },
          ].map((agent, i, arr) => (
            <div key={agent.name} className="flex items-center gap-2 flex-shrink-0">
              <div className={`px-3 py-1.5 rounded-full text-[10px] font-medium font-sans border ${activeAgent === agent.id
                ? "bg-rose-600 text-white border-rose-600 animate-pulse"
                : completedNodes.includes(agent.id)
                  ? "bg-rose-50 text-rose-600 border-rose-100"
                  : "bg-slate-50 text-slate-400 border-slate-100"
                }`}>
                {agent.name}
              </div>
              {i < arr.length - 1 && <ArrowRight size={10} className="text-slate-300" />}
            </div>
          ))}
        </div>

      </div>

      {/* Log Timeline */}
      <div className="flex-1 overflow-y-auto px-5 pb-4" ref={scrollRef}>
        <div className="relative">
          {/* Vertical line */}
          <div className="absolute left-[5px] top-3 bottom-0 w-0.5 bg-slate-200" />
          <AnimatePresence initial={false}>
            {filteredLogs.map((entry) => (
              <LogNode
                key={entry.id}
                entry={entry}
                expanded={expandedLogs.has(entry.id)}
                onToggle={() => toggleLog(entry.id)}
              />
            ))}
            {filteredLogs.length === 0 && (
              <div className="flex flex-col items-center justify-center py-10 opacity-60">
                <span className="text-2xl mb-2">📡</span>
                <p className="text-xs text-slate-500 font-sans text-center">Waiting for agent activity...</p>
              </div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Pipeline Tracker Removed as requested */}
    </motion.aside>
  );
}
