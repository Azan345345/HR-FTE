import { useState, useEffect } from "react";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { X, Eye, EyeOff, ShieldCheck, Database, Zap, Plus, Trash2, FileText, CheckCircle2, Star, Brain, Sparkles, BookOpen, Link, Linkedin, Mail, CheckCheck, AlertCircle, RefreshCw } from "lucide-react";
import { getSettingsConfig, listCVs, uploadCV, deleteCV, setPrimaryCV, getSkills, getGoogleAuthUrl, getProfile, saveProfile, getIntegrationStatus, disconnectGoogle } from "@/services/api";
import { useAuthStore } from "@/hooks/useAuth";

interface SettingsModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const TABS = ["Profile", "API Keys", "Integrations", "Data Sources", "Skills", "About"];

export function SettingsModal({ open, onOpenChange }: SettingsModalProps) {
  const [activeTab, setActiveTab] = useState("Profile");
  const [showKey, setShowKey] = useState<Record<string, boolean>>({});
  const [config, setConfig] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { user } = useAuthStore();
  const [cvs, setCvs] = useState<any[]>([]);
  const [cvLoading, setCvLoading] = useState(false);
  const [uploadingCv, setUploadingCv] = useState(false);
  const [settingPrimary, setSettingPrimary] = useState<string | null>(null);
  const [skills, setSkills] = useState<any>(null);
  const [skillsLoading, setSkillsLoading] = useState(false);
  const [connectingGmail, setConnectingGmail] = useState(false);
  const [disconnectingGmail, setDisconnectingGmail] = useState(false);
  const [gmailConnected, setGmailConnected] = useState(false);
  const [profileName, setProfileName] = useState("");
  const [linkedinUrl, setLinkedinUrl] = useState("");
  const [savingProfile, setSavingProfile] = useState(false);
  const [profileSaved, setProfileSaved] = useState(false);

  useEffect(() => {
    if (open) {
      setLoading(true);
      setError(null);
      Promise.all([
        getSettingsConfig(),
        getProfile(),
      ])
        .then(([cfg, prof]) => {
          setConfig(cfg);
          setProfileName(prof.name || "");
          setLinkedinUrl(prof.linkedin_url || "");
        })
        .catch((err) => {
          console.error(err);
          setError("Failed to load configuration");
        })
        .finally(() => setLoading(false));
    }
  }, [open]);

  useEffect(() => {
    if (open && activeTab === "Data Sources") {
      fetchCVs();
    }
    if (open && activeTab === "Skills") {
      fetchSkills();
    }
    if (open && activeTab === "Integrations") {
      getIntegrationStatus()
        .then((data) => setGmailConnected(data.integrations?.google_gmail ?? false))
        .catch(() => {});
    }
  }, [open, activeTab]);

  const fetchSkills = async () => {
    try {
      setSkillsLoading(true);
      const data = await getSkills();
      setSkills(data);
    } catch (err) {
      console.error("Failed to fetch skills:", err);
    } finally {
      setSkillsLoading(false);
    }
  };

  const fetchCVs = async () => {
    try {
      setCvLoading(true);
      const data = await listCVs();
      setCvs(data.cvs);
    } catch (err) {
      console.error("Failed to fetch CVs:", err);
    } finally {
      setCvLoading(false);
    }
  };

  const handleCVUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      setUploadingCv(true);
      await uploadCV(file);
      await fetchCVs();
    } catch (err) {
      console.error("Upload failed:", err);
      alert("Failed to upload CV");
    } finally {
      setUploadingCv(false);
    }
  };

  const handleCVDelete = async (id: string) => {
    if (!confirm("Delete this CV? This will also remove all tailored versions and generated PDFs linked to it.")) return;
    try {
      await deleteCV(id);
      await fetchCVs();
    } catch (err: any) {
      console.error("Delete failed:", err);
      alert(`Failed to delete CV: ${err?.message || "Unknown error"}`);
    }
  };

  const handleSetPrimary = async (id: string) => {
    try {
      setSettingPrimary(id);
      await setPrimaryCV(id);
      await fetchCVs();
    } catch (err) {
      console.error("Set primary failed:", err);
    } finally {
      setSettingPrimary(null);
    }
  };

  const toggleKey = (key: string) => {
    setShowKey(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const handleSaveProfile = async () => {
    setSavingProfile(true);
    try {
      await saveProfile({ name: profileName, linkedin_url: linkedinUrl });
      setProfileSaved(true);
      setTimeout(() => setProfileSaved(false), 2500);
    } catch (err) {
      console.error("Failed to save profile:", err);
    } finally {
      setSavingProfile(false);
    }
  };

  const handleConnectGmail = async () => {
    try {
      setConnectingGmail(true);
      const data = await getGoogleAuthUrl();
      if (data.error || !data.auth_url) {
        alert(data.error || "Failed to generate auth URL. Check server configuration.");
        return;
      }
      // Navigate away — Google will redirect back to the backend callback,
      // which then redirects to /?gmail_connected=1
      window.location.href = data.auth_url;
    } catch (err) {
      console.error("Failed to get Google auth URL:", err);
      alert("Failed to start Gmail connection.");
    } finally {
      setConnectingGmail(false);
    }
  };

  const handleDisconnectGmail = async () => {
    if (!confirm("Disconnect Gmail? The app will no longer be able to send emails on your behalf.")) return;
    setDisconnectingGmail(true);
    try {
      await disconnectGoogle();
      setGmailConnected(false);
    } catch (err) {
      console.error("Failed to disconnect Gmail:", err);
    } finally {
      setDisconnectingGmail(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="max-w-[720px] p-0 overflow-hidden h-[580px] flex flex-col gap-0 border-none rounded-2xl"
        style={{ boxShadow: "var(--shadow-dialog)" }}
      >
        <div className="flex flex-1 h-full">
          {/* Sidebar */}
          <div className="w-[176px] bg-slate-50/80 border-r border-black/[0.06] flex flex-col pt-5">
            <div className="px-5 mb-5">
              <h2 className="font-serif text-[18px] tracking-tight">Settings</h2>
            </div>
            <div className="flex flex-col gap-0.5 px-2">
              {TABS.map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`relative px-3 py-2.5 text-left text-[13px] font-medium transition-all rounded-xl ${
                    activeTab === tab
                      ? "bg-white text-primary shadow-xs border border-black/[0.05]"
                      : "text-slate-600 hover:bg-white/60 hover:text-slate-900"
                  }`}
                >
                  {activeTab === tab && (
                    <div className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-4 rounded-r-full bg-primary" />
                  )}
                  {tab}
                </button>
              ))}
            </div>
          </div>

          {/* Content */}
          <div className="flex-1 bg-white p-8 overflow-y-auto">
            <div className="flex justify-between items-center mb-6">
              <h3 className="text-[20px] font-serif tracking-tight text-slate-900">{activeTab}</h3>
            </div>

            {loading ? (
              <div className="flex flex-col items-center justify-center h-64 space-y-4">
                <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
                <p className="text-sm text-slate-400 font-sans">Loading configuration...</p>
              </div>
            ) : error ? (
              <div className="flex flex-col items-center justify-center h-64 space-y-4">
                <p className="text-sm text-rose-500 font-sans">{error}</p>
                <button onClick={() => getSettingsConfig().then(setConfig).catch(err => setError("Failed to load configuration"))} className="text-xs text-primary underline">Retry</button>
              </div>
            ) : (
              <>
                {activeTab === "Profile" && (
                  <div className="space-y-5">
                    <div className="grid gap-1.5">
                      <label className="text-[12px] font-semibold text-slate-500 uppercase tracking-wide">Full Name</label>
                      <input
                        type="text"
                        value={profileName}
                        onChange={e => setProfileName(e.target.value)}
                        className="h-10 px-3 rounded-xl border border-black/[0.09] bg-slate-50/80 text-[13px] font-sans focus:border-primary focus:bg-white focus:ring-[3px] focus:ring-primary/10 transition-all outline-none"
                      />
                    </div>
                    <div className="grid gap-1.5">
                      <label className="text-[12px] font-semibold text-slate-500 uppercase tracking-wide">Email</label>
                      <input
                        type="email"
                        defaultValue={user?.email || ""}
                        readOnly
                        className="h-10 px-3 rounded-xl border border-black/[0.07] bg-slate-100/80 text-slate-400 text-[13px] font-sans cursor-not-allowed outline-none"
                      />
                    </div>
                    <div className="grid gap-1.5">
                      <label className="text-[12px] font-semibold text-slate-500 uppercase tracking-wide flex items-center gap-2">
                        <Linkedin size={13} className="text-blue-600" />
                        LinkedIn URL
                      </label>
                      <input
                        type="url"
                        value={linkedinUrl}
                        onChange={e => setLinkedinUrl(e.target.value)}
                        placeholder="https://linkedin.com/in/your-profile"
                        className="h-10 w-full px-3 rounded-xl border border-black/[0.09] bg-slate-50/80 text-[13px] font-sans focus:border-primary focus:bg-white focus:ring-[3px] focus:ring-primary/10 transition-all outline-none"
                      />
                      <p className="text-[11px] text-slate-400 font-sans">
                        Included in every application email sent on your behalf.
                      </p>
                    </div>
                    <div className="pt-1">
                      <button
                        onClick={handleSaveProfile}
                        disabled={savingProfile}
                        className={`px-5 py-2 rounded-xl text-[13px] font-semibold transition-all active:scale-[0.97] disabled:opacity-60 ${
                          profileSaved
                            ? "bg-green-500 text-white"
                            : "bg-primary text-white hover:brightness-110"
                        }`}
                        style={{ boxShadow: "var(--shadow-brand-sm)" }}
                      >
                        {savingProfile ? "Saving..." : profileSaved ? "✓ Saved" : "Save Changes"}
                      </button>
                    </div>
                  </div>
                )}

                {activeTab === "API Keys" && (
                  <div className="space-y-6">
                    <p className="text-xs text-slate-400 font-sans bg-slate-50 p-3 rounded-lg border border-slate-100 flex gap-2 items-start">
                      <ShieldCheck size={14} className="mt-0.5 text-primary" />
                      API keys are managed via your environment variables (.env). These values are read-only for security.
                    </p>
                    {config?.api_keys?.map((item: any) => (
                      <div key={item.key} className="grid gap-2">
                        <div className="flex items-center justify-between">
                          <label className="text-sm font-medium text-slate-700 font-sans">{item.label}</label>
                          <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wider ${item.active ? "bg-green-100 text-green-700" : "bg-slate-100 text-slate-400"
                            }`}>
                            {item.active ? "Active" : "Missing"}
                          </span>
                        </div>
                        <div className="relative">
                          <input
                            type={showKey[item.key] ? "text" : "password"}
                            value={item.val}
                            readOnly
                            className="w-full h-10 px-3 pr-10 rounded-lg border border-slate-200 bg-slate-100 text-sm font-mono text-slate-500 cursor-not-allowed outline-none"
                          />
                          <button
                            onClick={() => toggleKey(item.key)}
                            className="absolute right-3 top-2.5 text-slate-400 hover:text-slate-600"
                          >
                            {showKey[item.key] ? <EyeOff size={16} /> : <Eye size={16} />}
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {activeTab === "Integrations" && (
                  <div className="space-y-6">
                    {/* Gmail Card */}
                    <div className="rounded-2xl border border-slate-100 overflow-hidden">
                      {/* Header */}
                      <div className="flex items-center justify-between px-5 py-4 bg-slate-50/80 border-b border-slate-100">
                        <div className="flex items-center gap-2.5">
                          <div className="w-8 h-8 rounded-lg bg-white border border-slate-100 shadow-sm flex items-center justify-center">
                            <Mail size={16} className="text-rose-500" />
                          </div>
                          <div>
                            <p className="text-[13px] font-bold text-slate-800 font-sans">Gmail</p>
                            <p className="text-[11px] text-slate-400 font-sans">Send job application emails</p>
                          </div>
                        </div>
                        {gmailConnected ? (
                          <span className="flex items-center gap-1.5 text-[11px] px-2.5 py-1 bg-green-50 text-green-700 rounded-full font-bold uppercase tracking-wider border border-green-100">
                            <CheckCheck size={11} />
                            Connected
                          </span>
                        ) : (
                          <span className="flex items-center gap-1.5 text-[11px] px-2.5 py-1 bg-slate-100 text-slate-500 rounded-full font-bold uppercase tracking-wider">
                            <AlertCircle size={11} />
                            Not connected
                          </span>
                        )}
                      </div>

                      {/* Body */}
                      <div className="px-5 py-4 bg-white space-y-4">
                        {gmailConnected ? (
                          <p className="text-[12px] text-slate-500 font-sans">
                            CareerAgent can send application emails through your Gmail account.
                            Disconnect if you want to revoke access.
                          </p>
                        ) : (
                          <p className="text-[12px] text-slate-500 font-sans">
                            Connect your Gmail account to let CareerAgent send job application
                            emails on your behalf. You'll be redirected to Google to approve access.
                          </p>
                        )}

                        <div className="flex items-center gap-3">
                          {gmailConnected ? (
                            <>
                              <button
                                onClick={handleConnectGmail}
                                disabled={connectingGmail}
                                className="flex items-center gap-2 px-4 py-2 rounded-xl text-[13px] font-semibold bg-white border border-slate-200 text-slate-700 hover:border-primary hover:text-primary transition-all active:scale-[0.97] disabled:opacity-50"
                              >
                                <RefreshCw size={13} className={connectingGmail ? "animate-spin" : ""} />
                                {connectingGmail ? "Redirecting..." : "Reconnect"}
                              </button>
                              <button
                                onClick={handleDisconnectGmail}
                                disabled={disconnectingGmail}
                                className="flex items-center gap-2 px-4 py-2 rounded-xl text-[13px] font-semibold bg-white border border-slate-200 text-rose-500 hover:border-rose-300 hover:bg-rose-50 transition-all active:scale-[0.97] disabled:opacity-50"
                              >
                                {disconnectingGmail ? "Disconnecting..." : "Disconnect"}
                              </button>
                            </>
                          ) : (
                            <button
                              onClick={handleConnectGmail}
                              disabled={connectingGmail}
                              className="flex items-center gap-2 px-5 py-2 rounded-xl text-[13px] font-semibold bg-primary text-white hover:brightness-110 transition-all active:scale-[0.97] disabled:opacity-60"
                              style={{ boxShadow: "var(--shadow-brand-sm)" }}
                            >
                              <Mail size={14} />
                              {connectingGmail ? "Redirecting to Google..." : "Connect Gmail"}
                            </button>
                          )}
                        </div>

                        {!gmailConnected && (
                          <p className="text-[11px] text-slate-400 font-sans">
                            You'll be redirected to Google's secure sign-in page. CareerAgent only
                            requests permission to send emails — it cannot read your inbox.
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                )}

                {activeTab === "Data Sources" && (
                  <div className="space-y-6">
                    <div className="flex items-center justify-between">
                      <p className="text-xs text-slate-400 font-sans">
                        Manage the resumes and data sources your agent uses for tailoring and job matching.
                      </p>
                    </div>

                    <div className="space-y-3">
                      <div className="flex items-center justify-between mb-2">
                        <h4 className="text-sm font-bold text-slate-700 font-sans flex items-center gap-2">
                          <FileText size={16} className="text-primary" />
                          Uploaded CVs
                        </h4>
                        <label className={`cursor-pointer flex items-center gap-1.5 px-3 py-1.5 bg-rose-50 text-rose-600 rounded-lg text-xs font-bold hover:bg-rose-100 transition-colors ${uploadingCv ? 'opacity-50 cursor-not-allowed' : ''}`}>
                          <Plus size={14} />
                          {uploadingCv ? "Uploading..." : "Add New"}
                          <input type="file" className="hidden" accept=".pdf,.docx" onChange={handleCVUpload} disabled={uploadingCv} />
                        </label>
                      </div>

                      {cvLoading ? (
                        <div className="h-20 flex items-center justify-center bg-slate-50 rounded-xl border border-dashed border-slate-200">
                          <p className="text-xs text-slate-400">Loading CVs...</p>
                        </div>
                      ) : cvs.length === 0 ? (
                        <div className="h-24 flex flex-col items-center justify-center bg-slate-50 rounded-xl border border-dashed border-slate-200">
                          <p className="text-xs text-slate-400 font-sans text-center mb-1">No CVs uploaded yet.</p>
                          <p className="text-[10px] text-slate-300 font-sans">Your primary CV is used for high-accuracy job matches.</p>
                        </div>
                      ) : (
                        <div className="space-y-3">
                          {cvs.map((cv) => (
                            <div key={cv.id} className="flex items-center justify-between p-3 bg-white border border-slate-100 rounded-xl shadow-sm group">
                              <div className="flex items-center gap-3">
                                <div className="w-8 h-8 bg-rose-50 rounded-lg flex items-center justify-center">
                                  <FileText size={16} className="text-rose-500" />
                                </div>
                                <div className="overflow-hidden max-w-[240px]">
                                  <p className="text-sm font-semibold text-slate-800 font-sans truncate">{cv.file_name}</p>
                                  <div className="flex items-center gap-2">
                                    <span className="text-[10px] text-slate-400 uppercase font-bold">{cv.file_type}</span>
                                    {cv.is_primary && (
                                      <span className="text-[10px] text-green-600 flex items-center gap-0.5 font-bold uppercase tracking-wider bg-green-50 px-1.5 py-0.5 rounded">
                                        <CheckCircle2 size={10} />
                                        Primary
                                      </span>
                                    )}
                                  </div>
                                </div>
                              </div>
                              <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                {!cv.is_primary && (
                                  <button
                                    onClick={() => handleSetPrimary(cv.id)}
                                    disabled={settingPrimary === cv.id}
                                    className="p-1.5 text-slate-400 hover:text-amber-500 hover:bg-amber-50 rounded-lg transition-all disabled:opacity-50"
                                    title="Set as primary CV"
                                  >
                                    <Star size={14} />
                                  </button>
                                )}
                                <button
                                  onClick={() => handleCVDelete(cv.id)}
                                  className="p-1.5 text-slate-400 hover:text-rose-500 hover:bg-rose-50 rounded-lg transition-all"
                                  title="Delete CV permanently"
                                >
                                  <Trash2 size={14} />
                                </button>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                    <div className="pt-4 border-t border-slate-100">
                      <h4 className="text-sm font-bold text-slate-700 font-sans mb-3 flex items-center gap-2">
                        <Database size={16} className="text-blue-500" />
                        System Integrations
                      </h4>
                      <div className="space-y-3">
                        {config?.data_sources?.filter((s: any) => s.name !== "Uploaded CVs").map((source: any, i: number) => (
                          <div key={i} className="flex items-center justify-between p-4 bg-slate-50 border border-slate-100 rounded-xl">
                            <div className="flex items-center gap-3">
                              <div className="w-10 h-10 bg-white rounded-lg flex items-center justify-center border border-slate-100 shadow-sm">
                                <Database size={18} className="text-primary" />
                              </div>
                              <div>
                                <p className="text-sm font-semibold text-slate-800 font-sans">{source.name}</p>
                                <p className="text-xs text-slate-400 font-sans">
                                  {source.count !== undefined ? `${source.count} records indexed` : "System integration"}
                                </p>
                              </div>
                            </div>
                            <div className="flex items-center gap-2">
                              <div className={`w-2 h-2 rounded-full ${source.status === "Connected" || source.status === "Active" ? "bg-green-500" : "bg-slate-300"}`} />
                              <span className="text-xs font-medium text-slate-600 font-sans">{source.status}</span>
                              {source.name === "Gmail (OAuth2)" && (
                                <button
                                  onClick={handleConnectGmail}
                                  disabled={connectingGmail}
                                  className={`ml-2 flex items-center gap-1 px-2.5 py-1 border rounded-lg text-xs font-bold transition-colors disabled:opacity-50 ${
                                    source.status === "Connected"
                                      ? "bg-slate-50 text-slate-500 border-slate-200 hover:bg-rose-50 hover:text-rose-600 hover:border-rose-200"
                                      : "bg-rose-50 text-rose-600 border-rose-200 hover:bg-rose-100"
                                  }`}
                                >
                                  <Link size={11} />
                                  {connectingGmail ? "..." : source.status === "Connected" ? "Reconnect" : "Connect"}
                                </button>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                {activeTab === "Skills" && (
                  <div className="space-y-6">
                    <div className="p-5 bg-gradient-to-br from-rose-50 to-indigo-50 rounded-2xl border border-rose-100 relative overflow-hidden">
                      <div className="relative z-10">
                        <div className="flex items-center gap-2 mb-2">
                          <Sparkles size={16} className="text-rose-500" />
                          <h4 className="text-sm font-bold text-slate-800 font-sans">AI Agent Persona</h4>
                        </div>
                        <p className="text-xl font-serif font-bold text-slate-900 mb-1">{skills?.persona?.role || "Career Strategist"}</p>
                        <p className="text-sm text-slate-600 font-sans italic">"{skills?.persona?.tone || "Confident, specific, human"}"</p>
                      </div>
                      <Brain size={120} className="absolute -right-8 -bottom-8 text-rose-500 opacity-[0.05]" />
                    </div>

                    <div className="grid gap-4">
                      <h4 className="text-sm font-bold text-slate-700 font-sans flex items-center gap-2">
                        <Zap size={16} className="text-amber-500" />
                        Core Principles
                      </h4>
                      <div className="grid grid-cols-1 gap-2">
                        {skills?.principles?.map((principle: string, i: number) => (
                          <div key={i} className="flex gap-3 p-3 bg-slate-50 rounded-xl border border-slate-100 text-sm font-sans text-slate-700">
                            <span className="text-rose-500 font-bold">0{i + 1}</span>
                            {principle}
                          </div>
                        ))}
                      </div>
                    </div>

                    <div className="space-y-4 pt-2">
                      <h4 className="text-sm font-bold text-slate-700 font-sans flex items-center gap-2">
                        <BookOpen size={16} className="text-indigo-500" />
                        Specialized Career Skills
                      </h4>
                      {skillsLoading ? (
                        <div className="h-40 flex items-center justify-center">
                          <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                        </div>
                      ) : (
                        <div className="grid grid-cols-2 gap-3">
                          {skills?.skills?.map((skill: any) => (
                            <div key={skill.id} className="p-4 bg-white border border-slate-100 rounded-xl shadow-sm hover:border-rose-200 transition-colors">
                              <p className="text-sm font-bold text-slate-800 font-sans mb-1">{skill.name}</p>
                              <p className="text-[11px] text-slate-400 font-sans line-clamp-2">{skill.description}</p>
                              <div className="mt-3 flex items-center justify-between">
                                <span className="text-[10px] px-2 py-0.5 bg-slate-100 text-slate-500 rounded-full font-bold uppercase tracking-wider">
                                  Priority {skill.priority}
                                </span>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {activeTab === "About" && (
                  <div className="space-y-6 text-center pt-10">
                    <h1 className="font-serif text-3xl font-bold text-primary">CareerAgent</h1>
                    <p className="font-mono text-xs text-slate-400">v1.0.0-beta</p>
                    <p className="text-sm text-slate-500 font-sans max-w-xs mx-auto">
                      Powered by OpenAI GPT-4o · Advanced Multi-Agent AI.
                    </p>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
