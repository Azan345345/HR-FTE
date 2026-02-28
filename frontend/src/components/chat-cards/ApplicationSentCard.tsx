import { CheckCircle2, Clock, ChevronRight, BookOpen, Briefcase } from "lucide-react";
import { Button } from "@/components/ui/button";
import { motion } from "framer-motion";

interface NextJobSuggestion {
  title: string;
  company: string;
  match_score?: number;
  job_id: string;
}

interface ApplicationSentMeta {
  type: "application_sent";
  job: { title: string; company: string; id?: string };
  hr_email?: string;
  sent_at?: string;
  mock_send?: boolean;
  next_steps?: string[];
  interview_prep_available?: boolean;
  next_job_suggestion?: NextJobSuggestion;
}

interface Props {
  metadata: ApplicationSentMeta;
  onSendAction: (action: string) => void;
}

export function ApplicationSentCard({ metadata, onSendAction }: Props) {
  const {
    job, hr_email, mock_send, next_steps = [], interview_prep_available, next_job_suggestion,
  } = metadata;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.1 }}
      className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50/40 shadow-sm overflow-hidden"
    >
      {/* Success header */}
      <div className="flex items-center gap-3 px-4 py-4 border-b border-emerald-100">
        <div className="w-10 h-10 rounded-full bg-emerald-100 flex items-center justify-center flex-shrink-0">
          <CheckCircle2 size={20} className="text-emerald-600" />
        </div>
        <div>
          <p className="text-[13px] font-semibold text-emerald-800 font-sans">
            Application {mock_send ? "queued" : "sent"}!
          </p>
          <p className="text-[11px] text-emerald-600 font-sans mt-0.5">
            {job.title} at {job.company}
            {hr_email && ` → ${hr_email}`}
          </p>
          {mock_send && (
            <p className="text-[10px] text-amber-600 font-sans mt-0.5">
              Demo mode — connect Gmail in Settings to send for real
            </p>
          )}
        </div>
      </div>

      {/* Next steps */}
      {next_steps.length > 0 && (
        <div className="px-4 py-3 border-b border-emerald-100">
          <p className="text-[10px] font-bold uppercase tracking-widest text-emerald-600 font-sans mb-2">
            What's next
          </p>
          <div className="space-y-1.5">
            {next_steps.map((step, i) => (
              <div key={i} className="flex items-start gap-2">
                <Clock size={11} className="text-emerald-500 mt-0.5 flex-shrink-0" />
                <p className="text-[11px] text-slate-600 font-sans">{step}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* CTAs */}
      <div className="px-4 py-3 flex flex-col gap-2">
        {interview_prep_available && job.id && (
          <Button
            size="sm"
            className="w-full h-9 text-[12px] font-semibold bg-slate-800 hover:bg-slate-900 text-white gap-1.5 font-sans"
            onClick={() => onSendAction(`__PREP_INTERVIEW__:${job.id}`)}
          >
            <BookOpen size={12} />
            Prepare for Interview
          </Button>
        )}

        {next_job_suggestion && (
          <button
            className="flex items-center gap-3 px-3 py-2.5 rounded-lg border border-slate-200 bg-white hover:border-rose-200 hover:bg-rose-50/30 transition-all text-left"
            onClick={() => onSendAction(`__TAILOR_APPLY__:${next_job_suggestion.job_id}`)}
          >
            <div className="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center flex-shrink-0">
              <Briefcase size={14} className="text-slate-500" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-[11px] font-semibold text-slate-800 font-sans truncate">
                Next: {next_job_suggestion.title} at {next_job_suggestion.company}
              </p>
              {next_job_suggestion.match_score && (
                <p className="text-[10px] text-slate-500 font-sans">
                  {next_job_suggestion.match_score}% match · Click to apply
                </p>
              )}
            </div>
            <ChevronRight size={13} className="text-slate-400 flex-shrink-0" />
          </button>
        )}
      </div>
    </motion.div>
  );
}
