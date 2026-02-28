import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  MessageSquare, Briefcase, BarChart2, Settings, Plus, MessageSquarePlus, Clock, Sparkles, Brain, Eye
} from "lucide-react";
import { listChatSessions } from "@/services/api";

export type ViewType = "chat" | "jobs" | "observability" | "interview_prep" | "seeing_in";

interface LeftSidebarProps {
  onOpenSettings: () => void;
  activeView: ViewType;
  onViewChange: (view: ViewType) => void;
  activeSessionId: string | null;
  onSessionChange: (id: string | null) => void;
  sessions: any[];
  loading?: boolean;
}

const NAV_ITEMS = [
  { id: "chat",          label: "Chat",          icon: MessageSquare },
  { id: "jobs",          label: "Jobs",          icon: Briefcase },
  { id: "observability", label: "Observability", icon: BarChart2 },
  { id: "interview_prep",label: "Inter Prep",    icon: Brain },
  { id: "seeing_in",     label: "Seeing In",     icon: Eye },
] as const;

export function LeftSidebar({
  onOpenSettings,
  activeView,
  onViewChange,
  activeSessionId,
  onSessionChange,
  sessions,
  loading = false
}: LeftSidebarProps) {

  return (
    <motion.aside
      className="w-[280px] h-full bg-slate-50 border-r border-slate-100 flex flex-col flex-shrink-0"
      initial={{ opacity: 0, x: -40 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ type: "spring", stiffness: 100, damping: 22, delay: 0.1 }}
    >
      <div className="flex-1 overflow-y-auto p-4 space-y-6 mt-4">
        <div>
          <label className="px-4 text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-2 block">
            Core Navigation
          </label>
          <div className="space-y-1">
            {NAV_ITEMS.map((item) => (
              <button
                key={item.id}
                onClick={() => onViewChange(item.id)}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all ${
                  activeView === item.id
                    ? "bg-primary/10 text-primary shadow-sm"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                }`}
              >
                <item.icon
                  size={18}
                  className={activeView === item.id ? "text-primary" : "text-slate-400"}
                />
                {item.label}
              </button>
            ))}
          </div>
        </div>

        {activeView === "chat" && (
          <div className="px-0 relative">
            <div className="flex items-center justify-between px-4 mb-2">
              <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                Recent History
              </label>
              <button
                onClick={() => onSessionChange(null)}
                className="text-slate-400 hover:text-primary transition-colors"
                title="New Chat"
              >
                <MessageSquarePlus size={14} />
              </button>
            </div>

            <div className="space-y-1">
              <button
                onClick={() => onSessionChange(null)}
                className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-xl text-xs font-semibold transition-all border border-transparent ${
                  !activeSessionId
                    ? "bg-white text-primary border-primary/20 shadow-sm"
                    : "text-slate-500 hover:bg-slate-100 hover:text-slate-700"
                }`}
              >
                <Plus size={14} className={!activeSessionId ? "text-primary" : "text-slate-400"} />
                New Conversation
              </button>

              {loading ? (
                <div className="px-4 py-3 space-y-2 opacity-50">
                  <div className="h-3 w-3/4 bg-slate-200 rounded animate-pulse" />
                  <div className="h-3 w-1/2 bg-slate-200 rounded animate-pulse" />
                </div>
              ) : sessions.length === 0 ? (
                <p className="px-4 py-3 text-[10px] text-slate-400 italic">No recent chats</p>
              ) : (
                sessions.map((session) => (
                  <button
                    key={session.session_id}
                    onClick={() => onSessionChange(session.session_id)}
                    className={`w-full text-left px-4 py-2.5 rounded-xl text-xs flex flex-col gap-0.5 transition-all group border border-transparent ${
                      activeSessionId === session.session_id
                        ? "bg-white text-slate-900 border-slate-200 shadow-sm"
                        : "text-slate-500 hover:bg-slate-100 hover:text-slate-700"
                    }`}
                  >
                    <span className={`font-bold truncate ${activeSessionId === session.session_id ? "text-slate-900" : "text-slate-600"}`}>
                      {session.title}
                    </span>
                    <span className="text-[9px] text-slate-400 flex items-center gap-1">
                      <Clock size={10} />
                      {new Date(session.updated_at).toLocaleDateString([], { month: "short", day: "numeric" })}
                    </span>
                  </button>
                ))
              )}
            </div>
          </div>
        )}
      </div>

      {/* Bottom Actions */}
      <div className="p-4 border-t border-slate-100 space-y-2 flex-shrink-0 bg-white/50">
        <button
          className="w-full h-10 bg-primary text-white rounded-xl text-xs font-bold hover:brightness-95 active:brightness-90 transition-all flex items-center justify-center gap-2 shadow-sm"
          style={{ boxShadow: "0 2px 12px -2px hsl(195 94% 45% / 35%)" }}
        >
          <Sparkles className="w-3.5 h-3.5" />
          Upgrade to Plus
        </button>
        <button
          onClick={onOpenSettings}
          className="w-full h-10 bg-white border border-slate-200 text-slate-600 rounded-xl text-xs font-semibold hover:bg-slate-50 transition-colors flex items-center justify-center gap-2"
        >
          <Settings size={14} />
          Settings
        </button>
      </div>
    </motion.aside>
  );
}
