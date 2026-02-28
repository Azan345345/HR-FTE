import { useEffect, useState } from "react";
import { Star } from "lucide-react";

interface JobCardProps {
  company: string;
  title: string;
  location: string;
  salary: string;
  type: string;
  matchScore: number;
  logoInitial: string;
  logoBg: string;
  logoText: string;
  reasons: string[];
  ringColor?: string;
}

function MatchRing({ score, color = "hsl(350 94% 72%)" }: { score: number; color?: string }) {
  const [animated, setAnimated] = useState(false);
  const radius = 22;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (animated ? score / 100 : 0) * circumference;

  useEffect(() => {
    const t = setTimeout(() => setAnimated(true), 400);
    return () => clearTimeout(t);
  }, []);

  return (
    <div className="relative w-[52px] h-[52px] flex-shrink-0">
      <svg className="w-[52px] h-[52px] -rotate-90" viewBox="0 0 52 52">
        <circle cx="26" cy="26" r={radius} fill="none" stroke="hsl(var(--border))" strokeWidth="3" />
        <circle
          cx="26" cy="26" r={radius} fill="none"
          stroke={color} strokeWidth="3" strokeLinecap="round"
          strokeDasharray={circumference} strokeDashoffset={offset}
          style={{ transition: "stroke-dashoffset 1s cubic-bezier(0.4, 0, 0.2, 1)" }}
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <span className="text-sm font-bold text-primary font-sans">{score}%</span>
      </div>
    </div>
  );
}

export function JobCard({
  company, title, location, salary, type, matchScore, logoInitial, logoBg, logoText, reasons, ringColor,
}: JobCardProps) {
  return (
    <div className="bg-white border border-slate-200 rounded-xl p-5 hover:border-rose-200 hover:shadow-md hover:-translate-y-px transition-all duration-200 cursor-pointer">
      {/* Top row */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div
            className="w-11 h-11 rounded-full flex items-center justify-center text-base font-bold font-sans"
            style={{ backgroundColor: logoBg, color: logoText }}
          >
            {logoInitial}
          </div>
          <div>
            <p className="text-[13px] font-medium text-slate-500 font-sans">{company}</p>
            <p className="text-base font-semibold text-foreground font-sans">{title}</p>
            <div className="flex items-center gap-2 mt-1 text-[13px] text-slate-500 font-sans">
              <span>📍 {location}</span>
              <span>·</span>
              <span className="font-medium text-green-600">💰 {salary}</span>
              <span>·</span>
              <span>🏢 {type}</span>
            </div>
          </div>
        </div>
        <MatchRing score={matchScore} color={ringColor} />
      </div>

      {/* Reasons */}
      <div className="mt-4">
        <p className="text-[13px] font-medium text-slate-700 font-sans mb-2">Why you match:</p>
        <ul className="space-y-1">
          {reasons.map((r, i) => (
            <li key={i} className="text-[13px] text-slate-600 font-sans pl-4 relative before:content-['•'] before:absolute before:left-0 before:text-primary">
              {r}
            </li>
          ))}
        </ul>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-3 mt-4">
        <button className="text-[13px] font-medium text-slate-500 hover:bg-slate-100 px-3 py-1.5 rounded-lg transition-colors font-sans">
          Skip
        </button>
        <button className="text-[13px] font-medium text-slate-700 border border-slate-200 px-3 py-1.5 rounded-lg hover:bg-slate-50 transition-colors font-sans">
          View Details
        </button>
        <button className="text-[13px] font-semibold text-white bg-primary px-4 py-1.5 rounded-lg hover:bg-rose-700 hover:shadow-sm transition-all font-sans flex items-center gap-1.5 ml-auto">
          <Star size={14} />
          Tailor CV & Apply
        </button>
      </div>
    </div>
  );
}
