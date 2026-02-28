import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Eye, Mail, RefreshCw, Play, Square, Clock, Inbox,
  CheckCircle2, AlertCircle, Activity, Wifi, WifiOff, Zap, ShieldCheck
} from "lucide-react";
import { getGmailWatcherStatus, toggleGmailWatcher, getIntegrationStatus } from "@/services/api";

export function SeeingInView() {
  const [watcher, setWatcher] = useState<any>(null);
  const [gmailConnected, setGmailConnected] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(true);
  const [toggling, setToggling] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const refresh = async () => {
    try {
      const [status, integrations] = await Promise.all([
        getGmailWatcherStatus(),
        getIntegrationStatus(),
      ]);
      setWatcher(status);
      setGmailConnected((integrations as any).integrations?.google_gmail ?? false);
    } catch {
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
    // Poll every 10s to show live check count
    pollRef.current = setInterval(refresh, 10_000);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, []);

  const handleToggle = async () => {
    setToggling(true);
    try {
      const result = await toggleGmailWatcher();
      setWatcher((prev: any) => ({ ...prev, is_running: result.is_running }));
    } catch {
    } finally {
      setToggling(false);
    }
  };

  const apps: any[] = watcher?.watched_applications ?? [];
  const isRunning = watcher?.is_running ?? false;
  const lastCheck = watcher?.last_check_at
    ? new Date(watcher.last_check_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })
    : null;

  return (
    <div className="h-full flex flex-col bg-slate-50 overflow-hidden">
      {/* Header */}
      <div className="bg-white border-b border-slate-100 px-6 py-4 flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-indigo-50 border border-indigo-100 flex items-center justify-center">
            <Eye size={18} className="text-indigo-600" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-slate-900">Seeing In</h2>
            <p className="text-xs text-slate-400 mt-0.5">Gmail inbox watcher — monitors HR replies to your applications</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={refresh}
            className="p-2 rounded-xl hover:bg-slate-100 transition-colors"
            title="Refresh"
          >
            <RefreshCw size={14} className="text-slate-400" />
          </button>
          <button
            onClick={handleToggle}
            disabled={toggling}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
              isRunning
                ? "bg-red-50 border border-red-200 text-red-600 hover:bg-red-100"
                : "bg-indigo-600 text-white hover:bg-indigo-700 shadow-sm shadow-indigo-200"
            } disabled:opacity-50`}
          >
            {toggling ? (
              <RefreshCw size={13} className="animate-spin" />
            ) : isRunning ? (
              <Square size={13} />
            ) : (
              <Play size={13} />
            )}
            {isRunning ? "Stop Watcher" : "Start Watcher"}
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6 space-y-6">

        {/* Status Card */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden"
        >
          <div className="px-6 py-4 border-b border-slate-50">
            <p className="text-xs font-bold uppercase tracking-wider text-slate-400">Watcher Status</p>
          </div>
          <div className="px-6 py-5 grid grid-cols-2 md:grid-cols-4 gap-6">
            {/* Running state */}
            <div className="flex flex-col gap-1.5">
              <div className="flex items-center gap-2">
                {isRunning ? (
                  <div className="flex items-center gap-1.5">
                    <Wifi size={14} className="text-emerald-500" />
                    <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                  </div>
                ) : (
                  <WifiOff size={14} className="text-slate-300" />
                )}
                <span className={`text-sm font-bold ${isRunning ? "text-emerald-600" : "text-slate-400"}`}>
                  {loading ? "—" : isRunning ? "Running" : "Stopped"}
                </span>
              </div>
              <p className="text-[10px] text-slate-400">Service state</p>
            </div>

            {/* Poll interval */}
            <div className="flex flex-col gap-1.5">
              <div className="flex items-center gap-2">
                <Clock size={14} className="text-slate-400" />
                <span className="text-sm font-bold text-slate-700">
                  {watcher?.interval_seconds ?? 60}s
                </span>
              </div>
              <p className="text-[10px] text-slate-400">Check interval</p>
            </div>

            {/* Total checks */}
            <div className="flex flex-col gap-1.5">
              <div className="flex items-center gap-2">
                <Activity size={14} className="text-blue-500" />
                <span className="text-sm font-bold text-slate-700">
                  {watcher?.total_checks ?? 0}
                </span>
              </div>
              <p className="text-[10px] text-slate-400">Total checks</p>
            </div>

            {/* Replies detected */}
            <div className="flex flex-col gap-1.5">
              <div className="flex items-center gap-2">
                <Zap size={14} className="text-amber-500" />
                <span className="text-sm font-bold text-slate-700">
                  {watcher?.replies_detected ?? 0}
                </span>
              </div>
              <p className="text-[10px] text-slate-400">Replies detected</p>
            </div>
          </div>

          {/* Last check banner */}
          <div className={`px-6 py-3 border-t border-slate-50 flex items-center justify-between ${isRunning ? "bg-emerald-50/50" : "bg-slate-50"}`}>
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <Clock size={11} className="text-slate-400" />
              {lastCheck ? `Last inbox check: ${lastCheck}` : "Not checked yet"}
            </div>
            {isRunning && (
              <div className="flex items-center gap-1.5 text-[10px] text-emerald-600 font-medium">
                <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-ping" />
                Actively monitoring
              </div>
            )}
          </div>
        </motion.div>

        {/* How it works */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05 }}
          className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5"
        >
          <p className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-4">How It Works</p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[
              { icon: Mail,         color: "bg-blue-50 text-blue-600",   title: "Polls Gmail",      desc: "Checks your inbox every 60 seconds for new messages in application threads." },
              { icon: Eye,          color: "bg-indigo-50 text-indigo-600", title: "Detects Replies", desc: "Identifies HR replies and interview invitations by keyword and sender match." },
              { icon: Zap,          color: "bg-amber-50 text-amber-600",  title: "Triggers Actions", desc: "Automatically triggers interview prep when an interview is offered." },
            ].map(item => (
              <div key={item.title} className="flex items-start gap-3">
                <div className={`w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 ${item.color}`}>
                  <item.icon size={14} />
                </div>
                <div>
                  <p className="text-[11px] font-bold text-slate-800">{item.title}</p>
                  <p className="text-[10px] text-slate-500 mt-0.5 leading-relaxed">{item.desc}</p>
                </div>
              </div>
            ))}
          </div>

          {/* Gmail integration status */}
          {gmailConnected === true && (
            <div className="mt-4 flex items-center gap-2 px-3 py-2.5 bg-emerald-50 border border-emerald-200 rounded-xl">
              <ShieldCheck size={13} className="text-emerald-600 flex-shrink-0" />
              <p className="text-[10px] text-emerald-700 font-medium">
                Gmail is connected via Google OAuth2 — the watcher can read your inbox and detect HR replies.
              </p>
            </div>
          )}
          {gmailConnected === false && (
            <div className="mt-4 flex items-start gap-2 px-3 py-2.5 bg-amber-50 border border-amber-200 rounded-xl">
              <AlertCircle size={13} className="text-amber-500 flex-shrink-0 mt-0.5" />
              <p className="text-[10px] text-amber-700 leading-relaxed">
                Gmail is <span className="font-semibold">not connected</span>. The watcher is running but cannot read actual emails.
                Connect your Google account in <span className="font-semibold">Settings → Integrations</span> to enable full inbox monitoring.
              </p>
            </div>
          )}
        </motion.div>

        {/* Watched Applications */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden"
        >
          <div className="px-6 py-4 border-b border-slate-50 flex items-center justify-between">
            <div>
              <p className="text-xs font-bold uppercase tracking-wider text-slate-400">Watched Applications</p>
              <p className="text-[10px] text-slate-400 mt-0.5">Sent applications awaiting an HR reply</p>
            </div>
            <div className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-50 border border-indigo-100 rounded-full">
              <Inbox size={11} className="text-indigo-500" />
              <span className="text-[10px] font-semibold text-indigo-600">{watcher?.apps_watched ?? 0} watching</span>
            </div>
          </div>

          {loading ? (
            <div className="p-6 space-y-3">
              {Array(3).fill(0).map((_, i) => (
                <div key={i} className="h-14 bg-slate-50 rounded-xl animate-pulse" />
              ))}
            </div>
          ) : apps.length === 0 ? (
            <div className="px-6 py-10 text-center">
              <Inbox className="w-8 h-8 text-slate-200 mx-auto mb-2" />
              <p className="text-xs font-medium text-slate-400">No sent applications to watch</p>
              <p className="text-[10px] text-slate-300 mt-1">Applications you send will appear here</p>
            </div>
          ) : (
            <div className="divide-y divide-slate-50">
              {apps.map((app: any, i: number) => (
                <motion.div
                  key={app.id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.04 }}
                  className="px-6 py-4 flex items-center gap-4 hover:bg-slate-50 transition-colors"
                >
                  <div className="w-9 h-9 rounded-xl bg-indigo-50 border border-indigo-100 flex items-center justify-center flex-shrink-0">
                    <Mail size={14} className="text-indigo-500" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-[12px] font-semibold text-slate-800 truncate">
                      {app.job_title || "Position"} at {app.company || "Company"}
                    </p>
                    <p className="text-[10px] text-slate-400 truncate">
                      Sent {app.created_at ? new Date(app.created_at).toLocaleDateString([], { month: "short", day: "numeric", year: "numeric" }) : "—"}
                      {app.hr_email && ` · ${app.hr_email}`}
                    </p>
                  </div>
                  <div className="flex items-center gap-1.5 px-2 py-1 bg-blue-50 border border-blue-100 rounded-full flex-shrink-0">
                    <div className={`w-1.5 h-1.5 rounded-full ${isRunning ? "bg-blue-500 animate-pulse" : "bg-slate-300"}`} />
                    <span className="text-[9px] font-semibold text-blue-600">
                      {isRunning ? "Watching" : "Paused"}
                    </span>
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </motion.div>
      </div>
    </div>
  );
}
