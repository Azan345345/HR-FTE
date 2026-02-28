import { Code, Users, FileCode, ArrowRight, DollarSign } from "lucide-react";
import { Button } from "@/components/ui/button";
import { motion } from "framer-motion";

interface PrepCategory {
  name: string;
  count: number;
  icon: string;
}

interface InterviewReadyMeta {
  type: "interview_ready";
  job: { title: string; company: string };
  categories: PrepCategory[];
  prep_id?: string;
  salary_range?: string;
  questions_to_ask?: string[];
}

interface Props {
  metadata: InterviewReadyMeta;
  onSendAction: (action: string) => void;
}

const ICON_MAP: Record<string, React.FC<any>> = {
  code: Code,
  users: Users,
  "file-code": FileCode,
};

const CATEGORY_COLORS = [
  "bg-blue-50 border-blue-200 text-blue-700",
  "bg-purple-50 border-purple-200 text-purple-700",
  "bg-amber-50 border-amber-200 text-amber-700",
];

export function InterviewPrepCard({ metadata, onSendAction }: Props) {
  const { job, categories, prep_id, salary_range, questions_to_ask = [] } = metadata;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.1 }}
      className="mt-4 rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden"
    >
      {/* Header */}
      <div className="px-4 py-3 border-b border-slate-100 bg-slate-50">
        <p className="text-[12px] font-semibold text-slate-800 font-sans">
          Interview Prep Ready
        </p>
        <p className="text-[10px] text-slate-500 font-sans mt-0.5">
          {job.title} at {job.company}
        </p>
      </div>

      {/* Category cards */}
      <div className="grid grid-cols-3 gap-2.5 px-4 py-3">
        {categories.map((cat, idx) => {
          const IconComp = ICON_MAP[cat.icon] || Code;
          const color = CATEGORY_COLORS[idx % CATEGORY_COLORS.length];
          return (
            <motion.div
              key={cat.name}
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.15 + idx * 0.07 }}
              className={`flex flex-col items-center gap-1.5 p-3 rounded-xl border ${color} text-center`}
            >
              <IconComp size={16} />
              <span className="text-[18px] font-bold leading-none">{cat.count}</span>
              <span className="text-[10px] font-medium leading-tight">{cat.name}</span>
            </motion.div>
          );
        })}
      </div>

      {/* Salary info */}
      {salary_range && (
        <div className="flex items-center gap-2 px-4 py-2 border-t border-slate-100 bg-slate-50/50">
          <DollarSign size={12} className="text-emerald-500" />
          <span className="text-[11px] text-slate-600 font-sans">
            Market range: <span className="font-semibold text-slate-800">{salary_range}</span>
          </span>
        </div>
      )}

      {/* Smart questions to ask */}
      {questions_to_ask.length > 0 && (
        <div className="px-4 py-2.5 border-t border-slate-100">
          <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400 font-sans mb-1.5">
            Questions to ask them
          </p>
          {questions_to_ask.slice(0, 2).map((q, i) => (
            <p key={i} className="text-[11px] text-slate-600 font-sans flex gap-1.5 mb-1">
              <span className="text-rose-400 flex-shrink-0">›</span> {q}
            </p>
          ))}
        </div>
      )}

      {/* CTA */}
      <div className="px-4 py-3 border-t border-slate-100">
        <Button
          size="sm"
          className="w-full h-9 text-[12px] font-semibold bg-slate-800 hover:bg-slate-900 text-white gap-1.5 font-sans"
          onClick={() => {
            // Navigate to interview prep view — send a navigation hint
            onSendAction(`Show me the interview prep for prep_id:${prep_id}`);
          }}
        >
          Start Mock Interview
          <ArrowRight size={12} />
        </Button>
      </div>
    </motion.div>
  );
}
