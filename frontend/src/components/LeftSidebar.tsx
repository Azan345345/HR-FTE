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
      className="w-[280px] h-full bg-white border-r border-black/[0.06] flex flex-col flex-shrink-0"
      style={{ boxShadow: "inset -1px 0 0 rgba(0,0,0,0.03)" }}
      initial={{ opacity: 0, x: -40 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ type: "spring", stiffness: 100, damping: 22, delay: 0.1 }}
    >
      <div className="flex-1 overflow-y-auto p-4 space-y-6 mt-4">
        {/* Core Navigation */}
        <div>
          <label className="px-3 text-[10px] font-semibold uppercase tracking-[0.08em] text-slate-400 mb-2 block">
            Navigation
          </label>
          <div className="space-y-0.5">
            {NAV_ITEMS.map((item) => {
              const isActive = activeView === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => onViewChange(item.id)}
                  className={`relative w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-150 ${
                    isActive
                      ? "bg-primary/[0.08] text-primary"
                      : "text-slate-600 hover:bg-slate-50 hover:text-slate-900 active:scale-[0.98]"
                  }`}
                >
                  {/* Left accent bar for active item */}
                  {isActive && (
                    <motion.div
                      layoutId="nav-accent"
                      className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 rounded-r-full bg-primary"
                      transition={{ type: "spring", stiffness: 400, damping: 30 }}
                    />
                  )}
                  <item.icon
                    size={16}
                    className={isActive ? "text-primary" : "text-slate-400"}
                  />
                  <span className={isActive ? "font-semibold" : ""}>{item.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Chat History */}
        {activeView === "chat" && (
          <div className="px-0 relative">
            <div className="flex items-center justify-between px-3 mb-2">
              <label className="text-[10px] font-semibold uppercase tracking-[0.08em] text-slate-400">
                Recent Chats
              </label>
              <button
                onClick={() => onSessionChange(null)}
                className="text-slate-400 hover:text-primary transition-colors rounded-lg p-0.5 hover:bg-primary/5"
                title="New Chat"
              >
                <MessageSquarePlus size={13} />
              </button>
            </div>

            <div className="space-y-0.5">
              {/* New Conversation button */}
              <button
                onClick={() => onSessionChange(null)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-medium transition-all border ${
                  !activeSessionId
                    ? "bg-white text-primary border-primary/15 shadow-xs font-semibold"
                    : "text-slate-500 border-transparent hover:bg-slate-50 hover:text-slate-700"
                }`}
              >
                <Plus size={13} className={!activeSessionId ? "text-primary" : "text-slate-400"} />
                New Conversation
              </button>

              {loading ? (
                <div className="px-3 py-3 space-y-2.5 opacity-50">
                  <div className="h-2.5 w-3/4 bg-slate-100 rounded-full animate-pulse" />
                  <div className="h-2.5 w-1/2 bg-slate-100 rounded-full animate-pulse" />
                  <div className="h-2.5 w-2/3 bg-slate-100 rounded-full animate-pulse" />
                </div>
              ) : sessions.length === 0 ? (
                <p className="px-3 py-3 text-[10px] text-slate-400 italic">No recent chats yet</p>
              ) : (
                sessions.map((session) => {
                  const isActive = activeSessionId === session.session_id;
                  return (
                    <button
                      key={session.session_id}
                      onClick={() => onSessionChange(session.session_id)}
                      className={`w-full text-left px-3 py-2.5 rounded-xl text-xs flex flex-col gap-0.5 transition-all border ${
                        isActive
                          ? "bg-white border-slate-200/80 shadow-xs"
                          : "border-transparent text-slate-500 hover:bg-slate-50 hover:text-slate-700"
                      }`}
                    >
                      <span className={`font-semibold truncate ${isActive ? "text-slate-900" : "text-slate-600"}`}>
                        {session.title}
                      </span>
                      <span className="text-[9px] text-slate-400 flex items-center gap-1 mt-0.5">
                        <Clock size={9} />
                        {new Date(session.updated_at).toLocaleDateString([], { month: "short", day: "numeric" })}
                      </span>
                    </button>
                  );
                })
              )}
            </div>
          </div>
        )}
      </div>

      {/* Bottom Actions */}
      <div className="p-4 border-t border-black/[0.05] space-y-2 flex-shrink-0">
        {/* Upgrade button */}
        <button
          className="w-full h-10 bg-primary text-white rounded-xl text-xs font-semibold hover:brightness-110 active:scale-[0.98] transition-all flex items-center justify-center gap-2"
          style={{ boxShadow: "var(--shadow-brand-sm)" }}
        >
          <Sparkles className="w-3.5 h-3.5" />
          Upgrade to Plus
        </button>

        {/* Settings button */}
        <button
          onClick={onOpenSettings}
          className="w-full h-10 bg-slate-50 border border-black/[0.06] text-slate-600 rounded-xl text-xs font-medium hover:bg-slate-100 hover:text-slate-900 active:scale-[0.98] transition-all flex items-center justify-center gap-2"
        >
          <Settings size={14} />
          Settings
        </button>
      </div>
    </motion.aside>
  );
}
