import { useState } from "react";
import { ArrowLeft, MoreHorizontal, Plus } from "lucide-react";

interface ApplicationTrackerProps {
  onBack: () => void;
}

export function ApplicationTracker({ onBack }: ApplicationTrackerProps) {
  return (
    <div className="flex flex-col h-full bg-slate-50">
      {/* Header */}
      <div className="flex items-center justify-between px-8 py-4 bg-white border-b border-slate-200 flex-shrink-0">
        <div className="flex items-center gap-4">
          <button 
            onClick={onBack}
            className="text-sm font-medium text-rose-600 hover:text-rose-700 flex items-center gap-1 font-sans transition-colors"
          >
            <ArrowLeft size={16} /> Back to Chat
          </button>
          <div className="h-4 w-px bg-slate-200" />
          <h2 className="text-lg font-semibold text-slate-800 font-sans">Application Tracker</h2>
        </div>
        <div className="flex items-center gap-3">
          <button className="flex items-center gap-2 bg-white border border-slate-200 text-slate-600 px-3 py-1.5 rounded-lg text-sm font-medium font-sans hover:bg-slate-50 transition-colors">
            <MoreHorizontal size={16} />
            Filter
          </button>
          <button className="flex items-center gap-2 bg-primary text-white px-3 py-1.5 rounded-lg text-sm font-medium font-sans hover:bg-rose-700 transition-colors">
            <Plus size={16} />
            Add Application
          </button>
        </div>
      </div>

      {/* Kanban Board */}
      <div className="flex-1 overflow-x-auto overflow-y-hidden p-6">
        <div className="flex h-full gap-6 min-w-max">
          {/* Column 1: Discovered */}
          <div className="w-[280px] flex flex-col h-full">
            <div className="flex items-center justify-between mb-3 px-1">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider font-sans">Discovered</span>
              <span className="bg-slate-200 text-slate-600 text-[10px] font-bold px-2 py-0.5 rounded-full font-sans">142</span>
            </div>
            <div className="flex-1 bg-slate-100/50 rounded-xl p-2 space-y-2 overflow-y-auto border border-slate-200/50">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="bg-white p-3 rounded-lg shadow-sm border border-slate-200 cursor-grab hover:shadow-md transition-all">
                  <div className="flex justify-between items-start mb-1">
                    <span className="font-semibold text-slate-700 text-sm font-sans">TechCorp {i}</span>
                    <span className="bg-rose-50 text-rose-600 text-[10px] font-bold px-1.5 py-0.5 rounded-full font-sans">7{i}%</span>
                  </div>
                  <p className="text-xs text-slate-500 font-sans truncate">Senior Frontend Engineer</p>
                </div>
              ))}
              <div className="py-2 text-center">
                <span className="text-xs text-slate-400 font-sans hover:text-rose-600 cursor-pointer transition-colors">+ 137 more</span>
              </div>
            </div>
          </div>

          {/* Column 2: Matched */}
          <div className="w-[280px] flex flex-col h-full">
            <div className="flex items-center justify-between mb-3 px-1">
              <span className="text-xs font-semibold text-amber-600 uppercase tracking-wider font-sans">Matched</span>
              <span className="bg-amber-100 text-amber-700 text-[10px] font-bold px-2 py-0.5 rounded-full font-sans">3</span>
            </div>
            <div className="flex-1 bg-amber-50/30 rounded-xl p-2 space-y-2 overflow-y-auto border border-amber-100/50">
              {[
                { company: "Stripe", score: 94, role: "Staff UI Engineer" },
                { company: "Vercel", score: 88, role: "Senior Frontend Dev" },
                { company: "Airbnb", score: 82, role: "Frontend Engineer III" }
              ].map((job) => (
                <div key={job.company} className="bg-white p-3 rounded-lg shadow-sm border border-l-4 border-l-amber-400 border-y-slate-200 border-r-slate-200 cursor-grab hover:shadow-md transition-all">
                  <div className="flex justify-between items-start mb-1">
                    <span className="font-semibold text-slate-800 text-sm font-sans">{job.company}</span>
                    <span className="bg-rose-50 text-rose-600 text-[10px] font-bold px-1.5 py-0.5 rounded-full font-sans">{job.score}%</span>
                  </div>
                  <p className="text-xs text-slate-500 font-sans truncate mb-2">{job.role}</p>
                  <button className="text-[11px] font-medium text-rose-600 hover:underline font-sans">
                    Apply →
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* Column 3: Applied */}
          <div className="w-[280px] flex flex-col h-full">
            <div className="flex items-center justify-between mb-3 px-1">
              <span className="text-xs font-semibold text-rose-600 uppercase tracking-wider font-sans">Applied</span>
              <span className="bg-rose-100 text-rose-700 text-[10px] font-bold px-2 py-0.5 rounded-full font-sans">1</span>
            </div>
            <div className="flex-1 bg-rose-50/30 rounded-xl p-2 space-y-2 overflow-y-auto border border-rose-100/50">
              <div className="bg-white p-3 rounded-lg shadow-sm border border-l-4 border-l-rose-500 border-y-slate-200 border-r-slate-200 cursor-grab hover:shadow-md transition-all">
                <div className="flex justify-between items-start mb-1">
                  <span className="font-semibold text-slate-800 text-sm font-sans">Stripe</span>
                  <span className="text-[10px] text-slate-400 font-sans">2m ago</span>
                </div>
                <p className="text-xs text-slate-500 font-sans truncate mb-2">Staff UI Engineer</p>
                <div className="flex items-center gap-1.5">
                  <div className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                  <span className="text-[10px] text-slate-500 font-sans">Awaiting reply</span>
                </div>
              </div>
            </div>
          </div>

          {/* Column 4: Interviewing */}
          <div className="w-[280px] flex flex-col h-full">
            <div className="flex items-center justify-between mb-3 px-1">
              <span className="text-xs font-semibold text-green-600 uppercase tracking-wider font-sans">Interviewing</span>
              <span className="bg-green-100 text-green-700 text-[10px] font-bold px-2 py-0.5 rounded-full font-sans">0</span>
            </div>
            <div className="flex-1 bg-green-50/30 rounded-xl p-2 space-y-2 overflow-y-auto border border-green-100/50 flex flex-col items-center justify-center">
              <div className="w-full h-24 border-2 border-dashed border-slate-300 rounded-lg flex items-center justify-center">
                <p className="text-xs text-slate-400 font-sans">No interviews yet</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
