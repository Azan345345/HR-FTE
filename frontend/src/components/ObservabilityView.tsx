import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Network, Cpu, Search, Wand2, Mail, Brain,
  FileText, UserCheck, X, CheckCircle2, XCircle,
  Clock, Activity, Zap, Key, TrendingUp, ArrowDownUp, AlertCircle,
  ChevronDown, ChevronUp
} from "lucide-react";
import { getExecutionLogs, getApiUsage } from "@/services/api";

const NODE_W = 148;
const NODE_H = 58;

const NODES = [
  { id: "supervisor",     label: "Supervisor",    icon: Network,   color: "rose",   x: 306, y: 10  },
  { id: "cv_parser",      label: "CV Parser",     icon: Cpu,       color: "blue",   x: 60,  y: 145 },
  { id: "job_hunter",     label: "Job Hunter",    icon: Search,    color: "green",  x: 306, y: 145 },
  { id: "cv_tailor",      label: "CV Tailor",     icon: Wand2,     color: "violet", x: 552, y: 145 },
  { id: "hr_finder",      label: "HR Finder",     icon: UserCheck, color: "amber",  x: 60,  y: 290 },
  { id: "doc_generator",  label: "Doc Generator", icon: FileText,  color: "cyan",   x: 306, y: 290 },
  { id: "email_sender",   label: "Email Sender",  icon: Mail,      color: "orange", x: 552, y: 290 },
  { id: "interview_prep", label: "Interview Prep",icon: Brain,     color: "pink",   x: 306, y: 420 },
] as const;

type NodeId = (typeof NODES)[number]["id"];

const EDGES: [NodeId, NodeId][] = [
  ["supervisor", "cv_parser"],
  ["supervisor", "job_hunter"],
  ["supervisor", "cv_tailor"],
  ["cv_parser",  "hr_finder"],
  ["job_hunter", "doc_generator"],
  ["cv_tailor",  "email_sender"],
  ["hr_finder",  "interview_prep"],
  ["doc_generator", "interview_prep"],
  ["email_sender",  "interview_prep"],
];

const COLORS: Record<string, { bg: string; border: string; icon: string; selBg: string }> = {
  rose:   { bg: "bg-rose-50",   border: "border-rose-200",   icon: "text-rose-600",   selBg: "bg-rose-600"   },
  blue:   { bg: "bg-blue-50",   border: "border-blue-200",   icon: "text-blue-600",   selBg: "bg-blue-600"   },
  green:  { bg: "bg-green-50",  border: "border-green-200",  icon: "text-green-600",  selBg: "bg-green-600"  },
  violet: { bg: "bg-violet-50", border: "border-violet-200", icon: "text-violet-600", selBg: "bg-violet-600" },
  amber:  { bg: "bg-amber-50",  border: "border-amber-200",  icon: "text-amber-600",  selBg: "bg-amber-600"  },
  cyan:   { bg: "bg-cyan-50",   border: "border-cyan-200",   icon: "text-cyan-600",   selBg: "bg-cyan-600"   },
  orange: { bg: "bg-orange-50", border: "border-orange-200", icon: "text-orange-600", selBg: "bg-orange-600" },
  pink:   { bg: "bg-pink-50",   border: "border-pink-200",   icon: "text-pink-600",   selBg: "bg-pink-600"   },
};

function centerOf(node: typeof NODES[number]) {
  return { x: node.x + NODE_W / 2, y: node.y + NODE_H / 2 };
}

function makePath(fromNode: typeof NODES[number], toNode: typeof NODES[number]) {
  const fx = fromNode.x + NODE_W / 2;
  const fy = fromNode.y + NODE_H;
  const tx = toNode.x + NODE_W / 2;
  const ty = toNode.y;
  const dy = Math.abs(ty - fy) * 0.55;
  return `M ${fx} ${fy} C ${fx} ${fy + dy} ${tx} ${ty - dy} ${tx} ${ty}`;
}

const PROVIDER_COLORS: Record<string, string> = {
  groq:    "text-orange-600 bg-orange-50 border-orange-200",
  google:  "text-blue-600 bg-blue-50 border-blue-200",
  unknown: "text-slate-500 bg-slate-50 border-slate-200",
};

function providerOf(modelId: string): string {
  if (modelId.includes("gemini")) return "google";
  if (modelId.includes("gpt") || modelId.includes("llama") || modelId.includes("mixtral")) return "groq";
  return "unknown";
}

export function ObservabilityView() {
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState<NodeId | null>(null);
  const [apiUsage, setApiUsage] = useState<{ models: any[]; quota: any[] } | null>(null);
  const [expandedLogs, setExpandedLogs] = useState<Set<string>>(new Set());
  const [apiExpanded, setApiExpanded] = useState(false);

  const toggleLog = (id: string) =>
    setExpandedLogs(prev => { const n = new Set(prev); n.has(id) ? n.delete(id) : n.add(id); return n; });

  useEffect(() => {
    getExecutionLogs()
      .then(data => { setLogs(data.executions || []); setLoading(false); })
      .catch(() => setLoading(false));
    getApiUsage()
      .then(data => setApiUsage(data))
      .catch(() => {});
  }, []);

  // agent_name is stored as "cv_parser", action as "pipeline_step_cv_parser" or "supervisor"
  function matchesNode(log: any, id: string) {
    const name = (log.agent_name || "").toLowerCase();
    const action = (log.action || "").toLowerCase();
    return name === id || name.includes(id) || action.includes(id);
  }

  function nodeStatus(id: string): "success" | "error" | "idle" {
    const matching = logs.filter(l => matchesNode(l, id));
    if (!matching.length) return "idle";
    return matching[0].status === "success" ? "success" : matching[0].status === "failed" ? "error" : "idle";
  }

  function nodeLogs(id: string) {
    return logs.filter(l => matchesNode(l, id));
  }

  const selected = NODES.find(n => n.id === selectedId);
  const selLogs = selectedId ? nodeLogs(selectedId) : [];

  const GRAPH_W = 760;
  const GRAPH_H = 510;

  return (
    <div className="h-full flex flex-col bg-slate-50 overflow-hidden">
      {/* Header */}
      <div className="bg-white border-b border-slate-100 px-6 py-4 flex items-center justify-between flex-shrink-0">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Agent Pipeline</h2>
          <p className="text-xs text-slate-400 mt-0.5">Click any node to inspect its execution logs</p>
        </div>
        <div className="flex items-center gap-3 text-xs">
          <div className="flex items-center gap-1.5 px-3 py-1.5 bg-green-50 rounded-full border border-green-100">
            <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
            <span className="text-green-700 font-medium">Pipeline Active</span>
          </div>
          <div className="px-3 py-1.5 bg-slate-100 rounded-full text-slate-500 font-medium">
            <Zap size={12} className="inline mr-1" />
            {logs.length} executions
          </div>
        </div>
      </div>

      {/* Main area: graph + optional log panel */}
      <div className="flex flex-1 overflow-hidden">
        {/* Graph */}
        <div className="flex-1 overflow-auto p-8 flex items-start justify-center">
          <div className="relative bg-white rounded-3xl border border-slate-100 shadow-sm overflow-hidden"
            style={{ width: GRAPH_W, height: GRAPH_H, minWidth: GRAPH_W }}>
            {/* Dot grid background */}
            <div className="absolute inset-0 opacity-[0.035] pointer-events-none"
              style={{ backgroundImage: "radial-gradient(#64748b 1px, transparent 1px)", backgroundSize: "28px 28px" }} />

            {/* SVG edges */}
            <svg className="absolute inset-0 pointer-events-none" width={GRAPH_W} height={GRAPH_H}>
              <defs>
                <marker id="arr" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
                  <polygon points="0 0,8 3,0 6" fill="#CBD5E1" />
                </marker>
                <marker id="arr-active" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
                  <polygon points="0 0,8 3,0 6" fill="#6366f1" />
                </marker>
              </defs>
              {EDGES.map(([fId, tId]) => {
                const fNode = NODES.find(n => n.id === fId)!;
                const tNode = NODES.find(n => n.id === tId)!;
                const isActive = selectedId === fId || selectedId === tId;
                const d = makePath(fNode, tNode);
                return (
                  <path key={`${fId}-${tId}`} d={d} fill="none"
                    stroke={isActive ? "#6366f1" : "#E2E8F0"}
                    strokeWidth={isActive ? 2.5 : 1.5}
                    markerEnd={isActive ? "url(#arr-active)" : "url(#arr)"}
                    className="transition-all duration-300"
                    opacity={selectedId && !isActive ? 0.3 : 1}
                  />
                );
              })}
              {/* Animated dots along active edges */}
              {selectedId && EDGES
                .filter(([f, t]) => f === selectedId || t === selectedId)
                .map(([fId, tId]) => {
                  const fNode = NODES.find(n => n.id === fId)!;
                  const tNode = NODES.find(n => n.id === tId)!;
                  return (
                    <circle key={`dot-${fId}-${tId}`} r="5" fill="#6366f1" opacity="0.8">
                      <animateMotion dur="1.4s" repeatCount="indefinite" path={makePath(fNode, tNode)} />
                    </circle>
                  );
                })}
            </svg>

            {/* Node cards */}
            {NODES.map((node) => {
              const cc = COLORS[node.color];
              const status = nodeStatus(node.id);
              const isSelected = selectedId === node.id;
              const IconComp = node.icon;
              return (
                <motion.button
                  key={node.id}
                  style={{ position: "absolute", left: node.x, top: node.y, width: NODE_W, height: NODE_H, zIndex: 10 }}
                  whileHover={{ scale: 1.06, y: -2 }}
                  whileTap={{ scale: 0.97 }}
                  onClick={() => setSelectedId(isSelected ? null : node.id as NodeId)}
                  className={`rounded-2xl border-2 flex items-center gap-3 px-3.5 shadow-md transition-all duration-200 ${
                    isSelected
                      ? "bg-slate-900 border-indigo-400 shadow-indigo-300/30 shadow-xl"
                      : `bg-white ${cc.border} hover:shadow-lg hover:shadow-${node.color}-100/30`
                  }`}
                >
                  <div className={`w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 ${isSelected ? "bg-indigo-600" : cc.bg}`}>
                    <IconComp size={15} className={isSelected ? "text-white" : cc.icon} />
                  </div>
                  <div className="text-left flex-1 min-w-0">
                    <div className={`text-[11px] font-bold truncate ${isSelected ? "text-white" : "text-slate-800"}`}>{node.label}</div>
                    <div className="flex items-center gap-1.5 mt-0.5">
                      <div className={`w-1.5 h-1.5 rounded-full ${
                        status === "success" ? "bg-green-500" :
                        status === "error"   ? "bg-red-500" : "bg-slate-300"
                      }`} />
                      <span className={`text-[9px] font-semibold capitalize ${isSelected ? "text-slate-400" : "text-slate-400"}`}>{status}</span>
                    </div>
                  </div>
                </motion.button>
              );
            })}
          </div>
        </div>

        {/* Log detail panel */}
        <AnimatePresence>
          {selectedId && selected && (
            <motion.div
              initial={{ x: 320, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: 320, opacity: 0 }}
              transition={{ type: "spring", damping: 26, stiffness: 280 }}
              className="w-72 flex-shrink-0 border-l border-slate-200 bg-white flex flex-col overflow-hidden"
            >
              <div className="p-4 border-b border-slate-100 flex items-center justify-between bg-white flex-shrink-0">
                <div className="flex items-center gap-3">
                  <div className={`w-9 h-9 rounded-xl flex items-center justify-center ${COLORS[selected.color].bg}`}>
                    <selected.icon size={17} className={COLORS[selected.color].icon} />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-slate-900">{selected.label}</h3>
                    <p className="text-[10px] text-slate-400 uppercase tracking-widest font-medium">Logs</p>
                  </div>
                </div>
                <button onClick={() => setSelectedId(null)} className="p-1.5 hover:bg-slate-100 rounded-xl transition-colors">
                  <X size={15} className="text-slate-400" />
                </button>
              </div>

              <div className="flex-1 overflow-y-auto p-3 space-y-2.5">
                {loading ? (
                  Array(3).fill(0).map((_, i) => (
                    <div key={i} className="h-16 bg-slate-50 rounded-xl animate-pulse" />
                  ))
                ) : selLogs.length === 0 ? (
                  <div className="text-center py-10">
                    <Activity className="w-7 h-7 text-slate-200 mx-auto mb-2" />
                    <p className="text-xs text-slate-400 font-medium">No executions yet</p>
                    <p className="text-[10px] text-slate-300 mt-1">Run the pipeline to see logs</p>
                  </div>
                ) : (
                  selLogs.map((log, i) => {
                    const logId = log.id || String(i);
                    const isExpanded = expandedLogs.has(logId);
                    const hasReasoning = log.input_summary || log.output_summary || log.error_message;
                    return (
                      <div key={i} className="bg-slate-50 rounded-xl border border-slate-100 hover:border-slate-200 transition-colors overflow-hidden">
                        <div className="p-3.5">
                          <div className="flex items-center justify-between gap-2 mb-2">
                            <div className="flex items-center gap-2 min-w-0">
                              {log.status === "success"
                                ? <CheckCircle2 size={13} className="text-green-500 flex-shrink-0" />
                                : <XCircle size={13} className="text-red-500 flex-shrink-0" />
                              }
                              <span className="text-[11px] font-bold text-slate-700 truncate">{log.action || "Execution"}</span>
                            </div>
                            {log.execution_time_ms != null && (
                              <div className="flex items-center gap-1 flex-shrink-0">
                                <Clock size={9} className="text-slate-300" />
                                <span className="text-[9px] font-mono text-slate-400">{log.execution_time_ms}ms</span>
                              </div>
                            )}
                          </div>

                          {log.llm_model && (
                            <span className="inline-block text-[9px] font-mono text-indigo-600 bg-indigo-50 border border-indigo-100 px-1.5 py-0.5 rounded-full mb-1.5">
                              {log.llm_model}
                            </span>
                          )}

                          {log.created_at && (
                            <p className="text-[9px] text-slate-300">{new Date(log.created_at).toLocaleString()}</p>
                          )}

                          {hasReasoning && (
                            <button
                              onClick={() => toggleLog(logId)}
                              className="flex items-center gap-1 text-[10px] font-semibold text-indigo-600 mt-2 hover:underline"
                            >
                              {isExpanded ? <ChevronUp size={10} /> : <ChevronDown size={10} />}
                              {isExpanded ? "Hide Reasoning" : "Show Reasoning"}
                            </button>
                          )}
                        </div>

                        <AnimatePresence>
                          {isExpanded && hasReasoning && (
                            <motion.div
                              initial={{ height: 0, opacity: 0 }}
                              animate={{ height: "auto", opacity: 1 }}
                              exit={{ height: 0, opacity: 0 }}
                              className="border-t border-slate-200 bg-white overflow-hidden"
                            >
                              <div className="p-3 space-y-2">
                                {log.input_summary && (
                                  <div>
                                    <p className="text-[9px] font-bold uppercase text-slate-400 mb-1">Input</p>
                                    <p className="text-[10px] text-slate-600 leading-relaxed whitespace-pre-wrap">{log.input_summary}</p>
                                  </div>
                                )}
                                {log.output_summary && (
                                  <div>
                                    <p className="text-[9px] font-bold uppercase text-slate-400 mb-1">Output</p>
                                    <p className="text-[10px] text-slate-600 leading-relaxed whitespace-pre-wrap italic">{log.output_summary}</p>
                                  </div>
                                )}
                                {log.error_message && (
                                  <div>
                                    <p className="text-[9px] font-bold uppercase text-red-400 mb-1">Error</p>
                                    <p className="text-[10px] text-red-600 font-mono leading-relaxed">{log.error_message}</p>
                                  </div>
                                )}
                                {(log.tokens_input || log.tokens_output) && (
                                  <p className="text-[9px] font-mono text-slate-400 pt-1 border-t border-slate-100">
                                    {log.tokens_input ?? 0} in · {log.tokens_output ?? 0} out tokens
                                  </p>
                                )}
                              </div>
                            </motion.div>
                          )}
                        </AnimatePresence>
                      </div>
                    );
                  })
                )}
              </div>

              <div className="p-3 border-t border-slate-100 flex items-center justify-between text-[10px] text-slate-400 flex-shrink-0">
                <span>{selLogs.length} runs</span>
                <span>{selLogs.filter(l => l.status === "success").length} OK · {selLogs.filter(l => l.status === "failed").length} failed</span>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Bottom stats bar */}
      <div className="border-t border-slate-200 bg-white px-6 py-2.5 flex items-center gap-8 text-xs flex-shrink-0">
        {[
          { label: "Total Runs", val: logs.length },
          { label: "Successful", val: logs.filter(l => l.status === "success").length },
          { label: "Failed", val: logs.filter(l => l.status === "failed").length },
          { label: "Avg Time", val: logs.length ? `${Math.round(logs.reduce((a, l) => a + (l.execution_time_ms || 0), 0) / logs.length)}ms` : "—" },
        ].map(m => (
          <div key={m.label} className="flex items-center gap-1.5">
            <span className="text-slate-400">{m.label}:</span>
            <span className="font-bold text-slate-700">{m.val}</span>
          </div>
        ))}
      </div>

      {/* ── API Usage Section ── */}
      <div className="border-t border-slate-200 bg-slate-50 flex-shrink-0">
        {/* Collapsible header */}
        <button
          onClick={() => setApiExpanded(!apiExpanded)}
          className="w-full px-6 py-3.5 flex items-center justify-between hover:bg-white/60 transition-colors group"
        >
          <div className="flex items-center gap-2">
            <Key size={14} className="text-slate-400 group-hover:text-slate-600 transition-colors" />
            <span className="text-xs font-bold text-slate-700">API Key Usage &amp; Model Stats</span>
            {apiUsage && apiUsage.models.length > 0 && (
              <span className="text-[9px] font-mono bg-indigo-50 text-indigo-500 border border-indigo-100 px-1.5 py-0.5 rounded-full">
                {apiUsage.models.length} models
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-slate-400">last 500 calls</span>
            {apiExpanded
              ? <ChevronUp size={14} className="text-slate-400" />
              : <ChevronDown size={14} className="text-slate-400" />
            }
          </div>
        </button>

        <AnimatePresence initial={false}>
          {apiExpanded && (
            <motion.div
              key="api-usage-body"
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.22, ease: "easeInOut" }}
              className="overflow-hidden"
            >
              {!apiUsage ? (
                <div className="px-6 pb-5 grid grid-cols-2 md:grid-cols-4 gap-3">
                  {Array(4).fill(0).map((_, i) => (
                    <div key={i} className="h-24 bg-white rounded-2xl border border-slate-100 animate-pulse" />
                  ))}
                </div>
              ) : apiUsage.models.length === 0 ? (
                <div className="px-6 pb-5 flex items-center gap-2 text-xs text-slate-400 py-4">
                  <AlertCircle size={13} />
                  No API calls recorded yet — run the agent pipeline to see stats here.
                </div>
              ) : (
                <div className="px-6 pb-5 grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                  {apiUsage.models.map((m: any) => {
                    const provider = providerOf(m.model);
                    const pColor = PROVIDER_COLORS[provider] || PROVIDER_COLORS.unknown;
                    const successPct = m.success_rate ?? 0;
                    const barColor = successPct >= 80 ? "bg-emerald-500" : successPct >= 50 ? "bg-amber-500" : "bg-red-500";
                    return (
                      <motion.div
                        key={m.model}
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="bg-white rounded-2xl border border-slate-100 p-4 shadow-sm hover:shadow-md transition-shadow"
                      >
                        <div className="flex items-center justify-between mb-3">
                          <span className={`text-[9px] font-bold px-2 py-0.5 rounded-full border uppercase ${pColor}`}>
                            {provider}
                          </span>
                          <span className="text-[9px] font-mono text-slate-400">{m.calls} calls</span>
                        </div>
                        <p className="text-[11px] font-bold text-slate-800 truncate mb-0.5">{m.model}</p>

                        <div className="flex items-center gap-2 mb-3 mt-2">
                          <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                            <div className={`h-full rounded-full ${barColor}`} style={{ width: `${successPct}%` }} />
                          </div>
                          <span className="text-[9px] font-semibold text-slate-600 w-8 text-right">{successPct}%</span>
                        </div>

                        <div className="grid grid-cols-2 gap-x-2 gap-y-1 text-[9px] text-slate-500">
                          <div className="flex items-center gap-1">
                            <CheckCircle2 size={9} className="text-emerald-500" />
                            <span>{m.success} OK</span>
                          </div>
                          <div className="flex items-center gap-1">
                            <XCircle size={9} className="text-red-400" />
                            <span>{m.failed} fail</span>
                          </div>
                          <div className="flex items-center gap-1">
                            <Clock size={9} className="text-slate-400" />
                            <span>{m.avg_latency_ms}ms avg</span>
                          </div>
                          <div className="flex items-center gap-1">
                            <ArrowDownUp size={9} className="text-slate-400" />
                            <span>{((m.tokens_in + m.tokens_out) / 1000).toFixed(1)}K tok</span>
                          </div>
                        </div>
                      </motion.div>
                    );
                  })}
                </div>
              )}

              {/* Quota bars */}
              {apiUsage && apiUsage.quota && apiUsage.quota.length > 0 && (
                <div className="px-6 pb-5">
                  <div className="flex items-center gap-2 mb-3">
                    <TrendingUp size={12} className="text-slate-400" />
                    <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Daily Quota (RPD)</p>
                  </div>
                  <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-2">
                    {apiUsage.quota.map((q: any) => {
                      const pct = q.percentage ?? 0;
                      const barColor = pct >= 80 ? "bg-red-400" : pct >= 50 ? "bg-amber-400" : "bg-emerald-400";
                      return (
                        <div key={q.model} className="bg-white rounded-xl border border-slate-100 p-3">
                          <p className="text-[9px] font-semibold text-slate-600 truncate mb-1.5">{q.model}</p>
                          <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden mb-1">
                            <div className={`h-full rounded-full ${barColor}`} style={{ width: `${Math.min(pct, 100)}%` }} />
                          </div>
                          <p className="text-[9px] text-slate-400">{q.used}/{q.limit} · {pct}%</p>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
