import { ExternalLink, Briefcase, MapPin, DollarSign, Zap, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { motion } from "framer-motion";

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

function MatchRing({ score }: { score: number }) {
  const color =
    score >= 80 ? "text-emerald-600" : score >= 60 ? "text-amber-500" : "text-slate-400";
  return (
    <div className={`flex flex-col items-center justify-center w-12 h-12 rounded-full border-2 ${score >= 80 ? "border-emerald-200 bg-emerald-50" : score >= 60 ? "border-amber-200 bg-amber-50" : "border-slate-200 bg-slate-50"} flex-shrink-0`}>
      <span className={`text-[13px] font-bold ${color} leading-none`}>{score}%</span>
      <span className="text-[8px] text-slate-400 leading-none mt-0.5">match</span>
    </div>
  );
}

export function JobResultsCard({ metadata, onSendAction }: Props) {
  const { jobs } = metadata;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay: 0.1 }}
      className="mt-4 space-y-3"
    >
      {jobs.map((job, idx) => (
        <motion.div
          key={job.id}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.1 + idx * 0.07 }}
          className={`rounded-xl border transition-all ${job.hr_found === false
            ? "border-red-200 bg-red-50/40 opacity-80"
            : "border-slate-200 bg-slate-50 hover:border-rose-200 hover:bg-rose-50/30"}`}
        >
          <div className="p-4">
            <div className="flex items-start gap-3">
              {/* Match ring */}
              <MatchRing score={job.match_score || 0} />

              {/* Job info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h4 className="text-[14px] font-semibold text-slate-900 font-sans leading-tight">
                      {job.title}
                    </h4>
                    <p className="text-[12px] text-slate-600 font-sans mt-0.5 font-medium">
                      {job.company}
                    </p>
                  </div>
                  {job.job_type && (
                    <Badge variant="secondary" className="text-[10px] flex-shrink-0 bg-white border-slate-200">
                      {job.job_type}
                    </Badge>
                  )}
                </div>

                {/* Meta row */}
                <div className="flex flex-wrap gap-3 mt-2">
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
                  <div className="mt-2 space-y-0.5">
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
                  <div className="flex flex-wrap gap-1 mt-2">
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
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-2 mt-3 pt-3 border-t border-slate-100">
              {job.hr_found === false ? (
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
      ))}
    </motion.div>
  );
}
