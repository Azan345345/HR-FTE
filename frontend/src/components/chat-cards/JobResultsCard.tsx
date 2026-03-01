import { useState } from "react";
import { ExternalLink, Briefcase, MapPin, DollarSign, Zap, XCircle, ChevronDown, ChevronUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { motion, AnimatePresence } from "framer-motion";

interface Job {
  id: string;
  title: string;
  company: string;
  location?: string;
  salary_range?: string;
  job_type?: string;
  match_score?: number;
  matching_skills?: string[];
  missing_skills?: string[];
  why_match?: string[];
  application_url?: string;
  hr_found?: boolean;
}

interface JobResultsMeta {
  type: "job_results";
  search_id: string;
  jobs: Job[];
}

interface Props {
  metadata: JobResultsMeta;
  onSendAction: (action: string) => void;
}

function MatchBadge({ score }: { score: number }) {
  const color =
    score >= 80
      ? "bg-emerald-50 border-emerald-200 text-emerald-700"
      : score >= 60
      ? "bg-amber-50 border-amber-200 text-amber-700"
      : "bg-slate-50 border-slate-200 text-slate-500";
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full border text-[11px] font-bold flex-shrink-0 ${color}`}>
      {score}%
    </span>
  );
}

export function JobResultsCard({ metadata, onSendAction }: Props) {
  const { jobs } = metadata;
  const [expandedJobs, setExpandedJobs] = useState<Set<string>>(new Set());

  const toggle = (id: string) =>
    setExpandedJobs((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay: 0.1 }}
      className="mt-4 space-y-2"
    >
      {jobs.map((job, idx) => {
        const isExpanded = expandedJobs.has(job.id);
        const isNoHR = job.hr_found === false;

        return (
          <motion.div
            key={job.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: 0.1 + idx * 0.07 }}
            className={`rounded-xl border transition-colors ${
              isNoHR
                ? "border-red-200 bg-red-50/40 opacity-80"
                : "border-slate-200 bg-slate-50 hover:border-rose-200 hover:bg-rose-50/30"
            }`}
          >
            {/* ── Collapsed header (always visible) ── */}
            <button
              onClick={() => toggle(job.id)}
              className="w-full flex items-center gap-3 px-4 py-3 text-left"
            >
              <div className="flex-1 min-w-0">
                <p className="text-[13px] font-semibold text-slate-900 font-sans leading-tight truncate">
                  {job.title}
                </p>
                <p className="text-[11px] text-slate-500 font-sans truncate">{job.company}</p>
              </div>
              <MatchBadge score={job.match_score || 0} />
              {job.job_type && (
                <Badge variant="secondary" className="text-[10px] flex-shrink-0 bg-white border-slate-200 hidden sm:inline-flex">
                  {job.job_type}
                </Badge>
              )}
              {isExpanded ? (
                <ChevronUp size={15} className="text-slate-400 flex-shrink-0" />
              ) : (
                <ChevronDown size={15} className="text-slate-400 flex-shrink-0" />
              )}
            </button>

            {/* ── Expanded details ── */}
            <AnimatePresence initial={false}>
              {isExpanded && (
                <motion.div
                  key="details"
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.22, ease: "easeInOut" }}
                  style={{ overflow: "hidden" }}
                >
                  <div className="px-4 pb-4 space-y-3 border-t border-slate-100 pt-3">
                    {/* Meta row */}
                    <div className="flex flex-wrap gap-3">
                      {job.location && (
                        <span className="flex items-center gap-1 text-[11px] text-slate-500 font-sans">
                          <MapPin size={10} /> {job.location}
                        </span>
                      )}
                      {job.salary_range && (
                        <span className="flex items-center gap-1 text-[11px] text-slate-500 font-sans">
                          <DollarSign size={10} /> {job.salary_range}
                        </span>
                      )}
                    </div>

                    {/* Why match bullets */}
                    {job.why_match && job.why_match.length > 0 && (
                      <div className="space-y-0.5">
                        {job.why_match.slice(0, 2).map((reason, i) => (
                          <p key={i} className="text-[11px] text-slate-500 font-sans flex items-start gap-1">
                            <span className="text-rose-400 mt-0.5 flex-shrink-0">·</span>
                            {reason}
                          </p>
                        ))}
                      </div>
                    )}

                    {/* Skills matched */}
                    {job.matching_skills && job.matching_skills.length > 0 && (
                      <div className="flex flex-wrap gap-1">
                        {job.matching_skills.slice(0, 5).map((skill) => (
                          <span
                            key={skill}
                            className="inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-emerald-50 text-emerald-700 border border-emerald-100 rounded text-[10px] font-medium font-sans"
                          >
                            <Zap size={8} /> {skill}
                          </span>
                        ))}
                      </div>
                    )}

                    {/* Actions */}
                    <div className="flex items-center gap-2 pt-1 border-t border-slate-100">
                      {isNoHR ? (
                        <div className="flex-1 flex items-center gap-1.5 text-[11px] text-red-500 font-sans font-medium">
                          <XCircle size={13} className="flex-shrink-0" />
                          No verified HR email — direct application unavailable
                        </div>
                      ) : (
                        <Button
                          size="sm"
                          className="flex-1 h-8 text-[12px] font-semibold bg-rose-600 hover:bg-rose-700 text-white gap-1.5 font-sans"
                          onClick={() => onSendAction(`__TAILOR_APPLY__:${job.id}`)}
                        >
                          <Briefcase size={12} />
                          Tailor CV & Apply
                        </Button>
                      )}
                      {job.application_url && (
                        <Button
                          size="sm"
                          variant="outline"
                          className="h-8 text-[11px] font-sans border-slate-200 text-slate-600 hover:text-slate-900 gap-1"
                          onClick={() => window.open(job.application_url, "_blank")}
                        >
                          <ExternalLink size={11} />
                          View
                        </Button>
                      )}
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        );
      })}
    </motion.div>
  );
}
