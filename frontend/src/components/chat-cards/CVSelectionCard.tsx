import { useState } from "react";
import { FileText, CheckCircle2, Star } from "lucide-react";

interface CV {
  id: string;
  file_name: string;
  file_type: string;
  is_primary: boolean;
  created_at: string | null;
}

interface CVSelectionCardProps {
  metadata: {
    type: "cv_selection";
    pending_intent: string;
    pending_context: string;
    cvs: CV[];
  };
  onSendAction: (action: string) => void;
}

export function CVSelectionCard({ metadata, onSendAction }: CVSelectionCardProps) {
  const { cvs, pending_intent, pending_context } = metadata;
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const handleSelect = (cvId: string) => {
    setSelectedId(cvId);
    onSendAction(`__SELECT_CV__:${cvId}:${pending_intent}:${pending_context}`);
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return "";
    try {
      return new Date(dateStr).toLocaleDateString(undefined, {
        month: "short", day: "numeric", year: "numeric",
      });
    } catch { return ""; }
  };

  return (
    <div className="rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden w-full max-w-md">
      {/* Header */}
      <div className="px-4 py-3 bg-gradient-to-r from-rose-50 to-slate-50 border-b border-slate-100 flex items-center gap-2">
        <div className="w-7 h-7 rounded-lg bg-rose-100 flex items-center justify-center">
          <FileText size={14} className="text-rose-500" />
        </div>
        <div>
          <p className="text-[13px] font-bold text-slate-800 font-sans">Select a CV</p>
          <p className="text-[11px] text-slate-400 font-sans">
            Choose which CV to use — you won't be asked again
          </p>
        </div>
      </div>

      {/* CV list */}
      <div className="p-3 space-y-2">
        {cvs.map((cv) => {
          const isHovered = hoveredId === cv.id;
          const isSelected = selectedId === cv.id;
          const showTick = isHovered || isSelected;

          return (
            <button
              key={cv.id}
              onClick={() => handleSelect(cv.id)}
              onMouseEnter={() => setHoveredId(cv.id)}
              onMouseLeave={() => setHoveredId(null)}
              disabled={!!selectedId}
              className={`w-full flex items-center justify-between p-3 rounded-xl border transition-all text-left
                ${isSelected
                  ? "border-rose-400 bg-rose-50"
                  : isHovered
                    ? "border-rose-200 bg-rose-50/60"
                    : "border-slate-100 bg-slate-50"
                }
                disabled:cursor-default`}
            >
              <div className="flex items-center gap-3 min-w-0">
                <div className={`w-8 h-8 rounded-lg border flex items-center justify-center flex-shrink-0 transition-colors
                  ${isSelected ? "bg-rose-100 border-rose-200" : isHovered ? "bg-white border-slate-200" : "bg-white border-slate-200"}`}>
                  <FileText size={15} className={isSelected ? "text-rose-500" : "text-rose-400"} />
                </div>
                <div className="min-w-0">
                  <p className="text-[13px] font-semibold text-slate-800 font-sans truncate max-w-[200px]">
                    {cv.file_name}
                  </p>
                  <div className="flex items-center gap-1.5 mt-0.5 flex-wrap">
                    <span className="text-[10px] text-slate-400 uppercase font-bold">{cv.file_type}</span>
                    {cv.created_at && (
                      <span className="text-[10px] text-slate-300 font-sans">· {formatDate(cv.created_at)}</span>
                    )}
                    {cv.is_primary && (
                      <span className="flex items-center gap-0.5 text-[10px] text-amber-600 bg-amber-50 px-1.5 py-0.5 rounded font-bold uppercase tracking-wider">
                        <Star size={8} className="fill-amber-500 text-amber-500" />
                        Primary
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* Tick circle — controlled by state, not CSS group-hover */}
              <div className={`flex-shrink-0 ml-2 w-6 h-6 rounded-full border-2 flex items-center justify-center transition-all
                ${isSelected
                  ? "border-rose-500 bg-rose-500"
                  : isHovered
                    ? "border-rose-400 bg-rose-400"
                    : "border-slate-200 bg-transparent"
                }`}
              >
                {showTick && (
                  <CheckCircle2 size={14} className="text-white" strokeWidth={2.5} />
                )}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
