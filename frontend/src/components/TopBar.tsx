import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Bell, User, LogOut, Github, ChevronDown, Cpu, Check, Zap, Sparkles } from "lucide-react";
import { NotificationPanel } from "./NotificationPanel";
import { useAgentStore } from "@/stores/agent-store";
import { useAuthStore } from "@/hooks/useAuth";
import { getPreferredModel, setPreferredModel } from "@/services/api";

const MODELS = [
  { id: "auto",                    label: "Auto",             provider: "Auto",   tier: "recommended", color: "text-indigo-600 bg-indigo-50 border-indigo-200", isAuto: true },
  { id: "gpt-4o",                  label: "GPT-4o",           provider: "OpenAI", tier: "smart",       color: "text-green-600 bg-green-50 border-green-200" },
  { id: "gpt-4o-mini",             label: "GPT-4o Mini",      provider: "OpenAI", tier: "fast",        color: "text-green-600 bg-green-50 border-green-200" },
  { id: "o3-mini",                 label: "o3 Mini",          provider: "OpenAI", tier: "reasoning",   color: "text-emerald-600 bg-emerald-50 border-emerald-200" },
  { id: "gemini-2.5-flash",        label: "Gemini 2.5 Flash", provider: "Google", tier: "smart",       color: "text-blue-600 bg-blue-50 border-blue-200" },
  { id: "llama-3.3-70b-versatile", label: "Llama 3.3 70B",   provider: "Groq",   tier: "fast",        color: "text-orange-600 bg-orange-50 border-orange-200" },
  { id: "mixtral-8x7b-32768",      label: "Mixtral 8x7B",    provider: "Groq",   tier: "balanced",    color: "text-purple-600 bg-purple-50 border-purple-200" },
  { id: "llama-3.1-8b-instant",    label: "Llama 3.1 8B",    provider: "Groq",   tier: "lite",        color: "text-slate-600 bg-slate-50 border-slate-200" },
];

export function TopBar() {
  const [time, setTime] = useState("");
  const [showNotifications, setShowNotifications] = useState(false);
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const [showModelPicker, setShowModelPicker] = useState(false);
  const [selectedModel, setSelectedModel] = useState("auto");
  const modelPickerRef = useRef<HTMLDivElement>(null);
  const activeAgent = useAgentStore((state) => state.activeAgent);
  const completedNodes = useAgentStore((state) => state.completedNodes);
  const { user, logout } = useAuthStore();

  const PIPELINE_STEPS = [
    { label: "Search",   done: completedNodes.includes("job_hunter"),  current: activeAgent === "job_hunter" },
    { label: "Match",    done: completedNodes.includes("supervisor"),   current: activeAgent === "supervisor" },
    { label: "Tailor",   done: completedNodes.includes("cv_tailor"),   current: activeAgent === "cv_tailor" },
    { label: "Outreach", done: completedNodes.includes("email_sender"), current: activeAgent === "email_sender" },
  ];

  useEffect(() => {
    const updateTime = () => {
      setTime(new Date().toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" }));
    };
    updateTime();
    const interval = setInterval(updateTime, 60000);
    return () => clearInterval(interval);
  }, []);

  // Load preferred model from backend
  useEffect(() => {
    getPreferredModel()
      .then(d => setSelectedModel(d.preferred_model))
      .catch(() => {});
  }, []);

  // Close model picker on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (modelPickerRef.current && !modelPickerRef.current.contains(e.target as Node)) {
        setShowModelPicker(false);
      }
    }
    if (showModelPicker) document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [showModelPicker]);

  const handleSelectModel = async (modelId: string) => {
    setSelectedModel(modelId);
    setShowModelPicker(false);
    try { await setPreferredModel(modelId); } catch {}
  };

  const currentModel = MODELS.find(m => m.id === selectedModel) || MODELS[0];

  return (
    <motion.header
      className="h-[60px] w-full flex items-center justify-between px-6 border-b border-slate-100 backdrop-blur-md bg-white/90 z-50 flex-shrink-0"
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.3, ease: "easeOut" }}
    >
      {/* Left */}
      <div className="flex items-center">
        <h1 className="font-serif text-lg font-bold tracking-tight">
          <span className="text-foreground">Career</span>
          <span className="text-primary">Agent</span>
        </h1>
        <div className="w-px h-6 bg-slate-200 mx-4" />
        <span className="text-sm font-medium text-slate-700 font-sans mr-2">
          Auto Job Assistant
        </span>
        <span className="px-2 py-0.5 bg-blue-50 text-blue-600 rounded-full text-[10px] font-bold uppercase tracking-wider border border-blue-100">
          Dev Mode
        </span>
        <div className={`w-2 h-2 rounded-full ml-3 ${activeAgent ? "bg-green-500 animate-pulse" : "bg-slate-300"}`} />

        {/* Command Palette Trigger */}
        <div
          className="ml-6 px-2 py-0.5 bg-slate-100 border border-slate-200 rounded-md text-[11px] font-mono text-slate-400 cursor-pointer hover:bg-slate-200 transition-colors"
          onClick={() => document.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', metaKey: true }))}
        >
          ⌘K
        </div>
      </div>

      {/* Center — Pipeline */}
      <div className="flex items-center gap-1">
        {PIPELINE_STEPS.map((step, i) => (
          <div key={step.label} className="flex items-center group cursor-pointer">
            <div className="flex flex-col items-center">
              <div className="relative">
                <div
                  className={`w-2 h-2 rounded-full transition-colors ${step.done
                    ? "bg-primary"
                    : step.current
                      ? "bg-primary group-hover:scale-125 transition-transform"
                      : "bg-slate-200 group-hover:bg-slate-300"
                    }`}
                />
                {step.current && (
                  <div className="absolute inset-0 w-2 h-2 rounded-full bg-primary animate-ping opacity-40" />
                )}
              </div>
              <span className={`text-[10px] font-medium mt-1 font-sans group-hover:underline ${step.current ? "text-primary" : "text-slate-500"}`}>
                {step.label}
              </span>
            </div>
            {i < PIPELINE_STEPS.length - 1 && (
              <div className={`w-6 h-0.5 mx-1 mb-4 ${step.done ? "bg-primary" : "bg-slate-200"}`} />
            )}
          </div>
        ))}
      </div>

      {/* Right */}
      <div className="flex items-center gap-3">

        {/* Model Picker */}
        <div className="relative" ref={modelPickerRef}>
          <button
            onClick={() => setShowModelPicker(!showModelPicker)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 transition-colors text-xs font-medium text-slate-700 group"
          >
            {(currentModel as any).isAuto
              ? <Sparkles size={13} className="text-indigo-400" />
              : <Cpu size={13} className="text-slate-400 group-hover:text-slate-600 transition-colors" />
            }
            <span className="hidden sm:inline max-w-[110px] truncate">{currentModel.label}</span>
            <span className={`hidden md:inline text-[9px] font-bold px-1.5 py-0.5 rounded-full border ${currentModel.color}`}>
              {(currentModel as any).isAuto ? "GPT-4o" : currentModel.provider}
            </span>
            <ChevronDown size={11} className={`text-slate-400 transition-transform ${showModelPicker ? "rotate-180" : ""}`} />
          </button>

          <AnimatePresence>
            {showModelPicker && (
              <motion.div
                initial={{ opacity: 0, y: 8, scale: 0.96 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 8, scale: 0.96 }}
                transition={{ duration: 0.15 }}
                className="absolute right-0 mt-2 w-68 bg-white border border-slate-100 rounded-2xl shadow-xl shadow-slate-200/60 p-2 z-[70]"
                style={{ width: 272 }}
              >
                <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400 px-3 py-1.5">Select Model</p>
                {MODELS.map((model, idx) => {
                  const isSelected = model.id === selectedModel;
                  const showDivider = idx === 1; // divider after Auto (before OpenAI models)
                  return (
                    <div key={model.id}>
                      {showDivider && <div className="my-1.5 border-t border-slate-100" />}
                      <button
                        onClick={() => handleSelectModel(model.id)}
                        className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-left transition-colors ${
                          isSelected ? "bg-slate-900" : "hover:bg-slate-50"
                        }`}
                      >
                        <div className="flex items-center gap-2.5 min-w-0">
                          {(model as any).isAuto
                            ? <Sparkles size={12} className={isSelected ? "text-indigo-400" : "text-indigo-400"} />
                            : <Zap size={12} className={isSelected ? "text-indigo-400" : "text-slate-300"} />
                          }
                          <div className="min-w-0">
                            <div className="flex items-center gap-1.5">
                              <p className={`text-[11px] font-semibold truncate ${isSelected ? "text-white" : "text-slate-800"}`}>
                                {model.label}
                              </p>
                              {(model as any).isAuto && (
                                <span className="text-[8px] font-bold px-1.5 py-0.5 rounded-full bg-green-100 text-green-700 border border-green-200">
                                  GPT-4o primary
                                </span>
                              )}
                            </div>
                            <p className={`text-[9px] ${isSelected ? "text-slate-400" : "text-slate-400"}`}>
                              {(model as any).isAuto ? "GPT-4o primary · full fallback chain" : `${model.provider} · ${model.tier}`}
                            </p>
                          </div>
                        </div>
                        {isSelected && <Check size={13} className="text-indigo-400 flex-shrink-0" />}
                      </button>
                    </div>
                  );
                })}
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Clock */}
        <span className="text-xs font-mono text-slate-400 min-w-[60px] text-right">
          {time}
        </span>

        <div className="relative">
          <div
            className="relative cursor-pointer"
            onClick={() => setShowNotifications(!showNotifications)}
          >
            <Bell size={16} className={`transition-colors ${showNotifications ? "text-slate-700" : "text-slate-500 hover:text-slate-700"}`} />
            <div className="absolute -top-1 -right-1 w-1.5 h-1.5 rounded-full bg-red-500" />
          </div>
          <AnimatePresence>
            {showNotifications && <NotificationPanel />}
          </AnimatePresence>
        </div>

        <div className="relative">
          <button
            onClick={() => setShowProfileMenu(!showProfileMenu)}
            className={`w-9 h-9 rounded-full flex items-center justify-center transition-all border-2 ${showProfileMenu ? "bg-rose-50 border-rose-200 shadow-sm shadow-rose-100" : "bg-slate-100 border-slate-200 hover:border-slate-300"}`}
          >
            <User size={18} className={showProfileMenu ? "text-rose-600" : "text-slate-500"} />
          </button>

          <AnimatePresence>
            {showProfileMenu && (
              <motion.div
                initial={{ opacity: 0, y: 10, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 10, scale: 0.95 }}
                className="absolute right-0 mt-2 w-56 bg-white border border-slate-100 rounded-2xl shadow-xl shadow-slate-200/50 p-2 z-[60]"
              >
                <div className="px-3 py-2 border-b border-slate-50 mb-1">
                  <p className="text-xs font-bold text-slate-900 truncate">{user?.name || "User"}</p>
                  <p className="text-[10px] text-slate-400 truncate">{user?.email || "user@example.com"}</p>
                </div>
                <a
                  href="https://github.com/Azan345345/HR-FTE.git"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-medium text-slate-600 hover:bg-slate-50 hover:text-slate-900 transition-all"
                >
                  <Github size={14} className="text-slate-400" />
                  View Repository
                </a>
                <button
                  onClick={() => { logout(); setShowProfileMenu(false); }}
                  className="w-full flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-medium text-rose-600 hover:bg-rose-50 transition-all text-left"
                >
                  <LogOut size={14} className="text-rose-500" />
                  Sign Out
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </motion.header>
  );
}
