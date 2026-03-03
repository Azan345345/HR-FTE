import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Upload, Linkedin, Mail, ArrowRight, Check, Loader2, ChevronRight } from "lucide-react";
import { uploadCV, getGoogleAuthUrl, getIntegrationStatus, saveProfile } from "@/services/api";
import { useAuthStore } from "@/hooks/useAuth";

interface OnboardingFlowProps {
  onComplete: () => void;
}

const STEPS = ["Profile", "Upload CV", "Gmail", "Tour"] as const;
type Step = 0 | 1 | 2 | 3;

const TOUR_CARDS = [
  {
    icon: "💬",
    title: "Search & Apply",
    desc: 'Type a role and location in chat — the AI hunts jobs, tailors your CV, finds HR contacts, and sends your application. Try "/apply Frontend Engineer London".',
  },
  {
    icon: "📄",
    title: "Tailor Your CV",
    desc: 'Paste a job description or use "/tailor" to generate a CV optimised for that role. Download it as a polished PDF in one click.',
  },
  {
    icon: "🎤",
    title: "Interview Prep",
    desc: 'Use "/interview" to get company research, likely questions, and salary benchmarks. Chat with the coach to practise your answers.',
  },
];

export function OnboardingFlow({ onComplete }: OnboardingFlowProps) {
  const { user } = useAuthStore();
  const [step, setStep] = useState<Step>(0);

  // Step 1 — Profile
  const [name, setName] = useState(user?.name ?? "");
  const [birthdate, setBirthdate] = useState("");
  const [linkedinUrl, setLinkedinUrl] = useState("");

  // Step 2 — CV Upload
  const [cvFile, setCvFile] = useState<File | null>(null);
  const [uploadState, setUploadState] = useState<"idle" | "uploading" | "done" | "error">("idle");
  const [uploadError, setUploadError] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const dropRef = useRef<HTMLDivElement>(null);

  // Step 3 — Gmail
  const [gmailState, setGmailState] = useState<"idle" | "connecting" | "connected" | "error">("idle");
  const [gmailError, setGmailError] = useState("");

  // Step 4 — Tour
  const [tourCard, setTourCard] = useState(0);
  const [tourProgress, setTourProgress] = useState(0);
  const tourTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Check URL params for Gmail OAuth return
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("gmail_connected") === "1") {
      setGmailState("connected");
      setStep(2);
      window.history.replaceState({}, "", window.location.pathname);
    } else if (params.get("gmail_error")) {
      setGmailError(params.get("gmail_error") ?? "Connection failed");
      setGmailState("error");
      setStep(2);
      window.history.replaceState({}, "", window.location.pathname);
    }
  }, []);

  // Check if Gmail already connected
  useEffect(() => {
    if (step === 2 && gmailState === "idle") {
      getIntegrationStatus()
        .then((res) => {
          if (res.integrations?.google || res.integrations?.gmail) {
            setGmailState("connected");
          }
        })
        .catch(() => {});
    }
  }, [step, gmailState]);

  // Tour auto-advance
  useEffect(() => {
    if (step !== 3) return;
    setTourProgress(0);
    const duration = 2500;
    const tick = 50;
    let elapsed = 0;
    tourTimerRef.current = setInterval(() => {
      elapsed += tick;
      setTourProgress(Math.min((elapsed / duration) * 100, 100));
      if (elapsed >= duration) {
        clearInterval(tourTimerRef.current!);
        setTourCard((c) => {
          if (c < TOUR_CARDS.length - 1) return (c + 1) as typeof c;
          return c;
        });
      }
    }, tick);
    return () => clearInterval(tourTimerRef.current!);
  }, [step, tourCard]);

  // ── Handlers ──────────────────────────────────────────────────────────────

  const handleProfileNext = () => {
    if (!name.trim()) return;
    // Save profile data (fire-and-forget; onboarding_completed set at the very end)
    saveProfile({
      name: name.trim(),
      ...(birthdate && { birthdate }),
      ...(linkedinUrl.trim() && { linkedin_url: linkedinUrl.trim() }),
    }).catch(() => {});
    setStep(1);
  };

  const handleFilePick = (file: File) => {
    if (!file.name.match(/\.(pdf|doc|docx)$/i)) {
      setUploadError("Please upload a PDF or Word document.");
      return;
    }
    setCvFile(file);
    setUploadError("");
    handleUpload(file);
  };

  const handleUpload = async (file: File) => {
    setUploadState("uploading");
    try {
      await uploadCV(file);
      setUploadState("done");
    } catch (e: any) {
      setUploadState("error");
      setUploadError(e.message ?? "Upload failed. Please try again.");
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (file) handleFilePick(file);
  };

  const handleGmailConnect = async () => {
    setGmailState("connecting");
    try {
      const res = await getGoogleAuthUrl();
      if (res.auth_url) {
        window.location.href = res.auth_url;
      } else {
        setGmailError(res.error ?? "Unable to get auth URL");
        setGmailState("error");
      }
    } catch (e: any) {
      setGmailError(e.message ?? "Connection failed");
      setGmailState("error");
    }
  };

  const advanceTourCard = (idx: number) => {
    clearInterval(tourTimerRef.current!);
    setTourCard(idx);
    setTourProgress(0);
  };

  // ── Render ────────────────────────────────────────────────────────────────

  const stepVariants = {
    enter: { opacity: 0, x: 40 },
    center: { opacity: 1, x: 0 },
    exit: { opacity: 0, x: -40 },
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background">
      {/* Background gradient blobs */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -left-40 w-80 h-80 bg-primary/10 rounded-full blur-3xl" />
        <div className="absolute -bottom-40 -right-40 w-96 h-96 bg-purple-500/8 rounded-full blur-3xl" />
      </div>

      <div className="relative w-full max-w-lg mx-4">
        {/* Step indicator */}
        <div className="flex items-center justify-center gap-2 mb-8">
          {STEPS.map((label, i) => (
            <div key={label} className="flex items-center gap-2">
              <div
                className={`flex items-center justify-center w-7 h-7 rounded-full text-xs font-semibold transition-all duration-300 ${
                  i < step
                    ? "bg-primary text-primary-foreground"
                    : i === step
                    ? "bg-primary/20 text-primary ring-2 ring-primary"
                    : "bg-muted text-muted-foreground"
                }`}
              >
                {i < step ? <Check className="w-3.5 h-3.5" /> : i + 1}
              </div>
              <span
                className={`text-xs hidden sm:block transition-colors ${
                  i === step ? "text-foreground font-medium" : "text-muted-foreground"
                }`}
              >
                {label}
              </span>
              {i < STEPS.length - 1 && (
                <div className={`w-6 h-px transition-colors ${i < step ? "bg-primary" : "bg-border"}`} />
              )}
            </div>
          ))}
        </div>

        {/* Card */}
        <div className="bg-card border border-border rounded-2xl shadow-xl overflow-hidden">
          <AnimatePresence mode="wait">
            {/* ── Step 1: Profile ── */}
            {step === 0 && (
              <motion.div
                key="profile"
                variants={stepVariants}
                initial="enter"
                animate="center"
                exit="exit"
                transition={{ duration: 0.25 }}
                className="p-8"
              >
                <div className="mb-6">
                  <h2 className="text-2xl font-bold text-foreground mb-1">Welcome! Let's set up your profile</h2>
                  <p className="text-sm text-muted-foreground">This helps CareerAgent personalise your applications.</p>
                </div>

                <div className="space-y-4">
                  <div>
                    <label className="text-sm font-medium text-foreground block mb-1.5">Full name *</label>
                    <input
                      type="text"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="e.g. Alex Johnson"
                      className="w-full px-3 py-2.5 rounded-lg bg-background border border-border text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 text-sm"
                      onKeyDown={(e) => e.key === "Enter" && handleProfileNext()}
                    />
                  </div>

                  <div>
                    <label className="text-sm font-medium text-foreground block mb-1.5">Date of birth</label>
                    <input
                      type="date"
                      value={birthdate}
                      onChange={(e) => setBirthdate(e.target.value)}
                      className="w-full px-3 py-2.5 rounded-lg bg-background border border-border text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 text-sm"
                    />
                  </div>

                  <div>
                    <label className="text-sm font-medium text-foreground block mb-1.5">
                      <Linkedin className="w-4 h-4 inline mr-1 text-blue-500" />
                      LinkedIn URL
                    </label>
                    <input
                      type="url"
                      value={linkedinUrl}
                      onChange={(e) => setLinkedinUrl(e.target.value)}
                      placeholder="https://linkedin.com/in/yourprofile"
                      className="w-full px-3 py-2.5 rounded-lg bg-background border border-border text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 text-sm"
                    />
                  </div>
                </div>

                <button
                  onClick={handleProfileNext}
                  disabled={!name.trim()}
                  className="mt-6 w-full flex items-center justify-center gap-2 py-2.5 rounded-lg bg-primary text-primary-foreground font-medium text-sm transition-opacity disabled:opacity-40 hover:opacity-90"
                >
                  Continue <ArrowRight className="w-4 h-4" />
                </button>
              </motion.div>
            )}

            {/* ── Step 2: CV Upload ── */}
            {step === 1 && (
              <motion.div
                key="cv"
                variants={stepVariants}
                initial="enter"
                animate="center"
                exit="exit"
                transition={{ duration: 0.25 }}
                className="p-8"
              >
                <div className="mb-6">
                  <h2 className="text-2xl font-bold text-foreground mb-1">Upload your CV</h2>
                  <p className="text-sm text-muted-foreground">
                    CareerAgent reads your CV to tailor every application. PDF or Word, max 10 MB.
                  </p>
                </div>

                <div
                  ref={dropRef}
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={handleDrop}
                  onClick={() => uploadState === "idle" || uploadState === "error" ? fileInputRef.current?.click() : undefined}
                  className={`relative flex flex-col items-center justify-center gap-3 border-2 border-dashed rounded-xl p-10 cursor-pointer transition-colors ${
                    uploadState === "done"
                      ? "border-green-500 bg-green-500/5"
                      : uploadState === "error"
                      ? "border-red-500 bg-red-500/5"
                      : "border-border hover:border-primary/50 hover:bg-primary/5"
                  }`}
                >
                  {uploadState === "uploading" ? (
                    <>
                      <Loader2 className="w-10 h-10 text-primary animate-spin" />
                      <p className="text-sm text-muted-foreground">Parsing your CV…</p>
                    </>
                  ) : uploadState === "done" ? (
                    <>
                      <div className="w-12 h-12 rounded-full bg-green-500/15 flex items-center justify-center">
                        <Check className="w-6 h-6 text-green-500" />
                      </div>
                      <p className="text-sm font-medium text-foreground">{cvFile?.name}</p>
                      <p className="text-xs text-green-600">CV uploaded and parsed successfully</p>
                    </>
                  ) : (
                    <>
                      <div className="w-12 h-12 rounded-full bg-muted flex items-center justify-center">
                        <Upload className="w-6 h-6 text-muted-foreground" />
                      </div>
                      <div className="text-center">
                        <p className="text-sm font-medium text-foreground">Drop your CV here or click to browse</p>
                        <p className="text-xs text-muted-foreground mt-1">PDF, DOC, DOCX • Max 10 MB</p>
                      </div>
                    </>
                  )}
                </div>

                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,.doc,.docx"
                  className="hidden"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) handleFilePick(file);
                  }}
                />

                {uploadError && (
                  <p className="mt-2 text-xs text-red-500">{uploadError}</p>
                )}

                {uploadState === "error" && (
                  <button
                    onClick={() => { setUploadState("idle"); setCvFile(null); setUploadError(""); }}
                    className="mt-2 text-xs text-primary underline"
                  >
                    Try again
                  </button>
                )}

                <button
                  onClick={() => setStep(2)}
                  disabled={uploadState !== "done"}
                  className="mt-6 w-full flex items-center justify-center gap-2 py-2.5 rounded-lg bg-primary text-primary-foreground font-medium text-sm transition-opacity disabled:opacity-40 hover:opacity-90"
                >
                  Continue <ArrowRight className="w-4 h-4" />
                </button>
              </motion.div>
            )}

            {/* ── Step 3: Gmail ── */}
            {step === 2 && (
              <motion.div
                key="gmail"
                variants={stepVariants}
                initial="enter"
                animate="center"
                exit="exit"
                transition={{ duration: 0.25 }}
                className="p-8"
              >
                <div className="mb-6">
                  <h2 className="text-2xl font-bold text-foreground mb-1">Connect Gmail</h2>
                  <p className="text-sm text-muted-foreground">
                    CareerAgent can send applications directly from your inbox and track replies. You can always connect later in Settings.
                  </p>
                </div>

                <div className="flex flex-col items-center gap-4 py-6">
                  {gmailState === "connected" ? (
                    <div className="flex flex-col items-center gap-3">
                      <div className="w-16 h-16 rounded-full bg-green-500/15 flex items-center justify-center">
                        <Check className="w-8 h-8 text-green-500" />
                      </div>
                      <p className="text-sm font-medium text-foreground">Gmail connected!</p>
                    </div>
                  ) : (
                    <>
                      <div className="w-16 h-16 rounded-full bg-red-500/10 flex items-center justify-center">
                        <Mail className="w-8 h-8 text-red-500" />
                      </div>

                      <button
                        onClick={handleGmailConnect}
                        disabled={gmailState === "connecting"}
                        className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-white border border-gray-300 text-gray-700 font-medium text-sm shadow-sm hover:bg-gray-50 disabled:opacity-60 transition-colors"
                      >
                        {gmailState === "connecting" ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <svg className="w-4 h-4" viewBox="0 0 24 24">
                            <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                            <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                            <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                            <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                          </svg>
                        )}
                        Connect Gmail
                      </button>

                      {gmailState === "error" && (
                        <p className="text-xs text-red-500 text-center">{gmailError}</p>
                      )}
                    </>
                  )}
                </div>

                <button
                  onClick={() => setStep(3)}
                  className="mt-2 w-full flex items-center justify-center gap-2 py-2.5 rounded-lg bg-primary text-primary-foreground font-medium text-sm hover:opacity-90"
                >
                  {gmailState === "connected" ? (
                    <>Continue <ArrowRight className="w-4 h-4" /></>
                  ) : (
                    "Skip for now"
                  )}
                </button>
              </motion.div>
            )}

            {/* ── Step 4: Tour ── */}
            {step === 3 && (
              <motion.div
                key="tour"
                variants={stepVariants}
                initial="enter"
                animate="center"
                exit="exit"
                transition={{ duration: 0.25 }}
                className="p-8"
              >
                <div className="mb-6">
                  <h2 className="text-2xl font-bold text-foreground mb-1">Here's what CareerAgent can do</h2>
                  <p className="text-sm text-muted-foreground">A quick look at the features waiting for you.</p>
                </div>

                {/* Tour card */}
                <div className="relative overflow-hidden">
                  <AnimatePresence mode="wait">
                    <motion.div
                      key={tourCard}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -20 }}
                      transition={{ duration: 0.3 }}
                      className="bg-muted/40 border border-border rounded-xl p-6 min-h-[140px]"
                    >
                      <div className="text-4xl mb-3">{TOUR_CARDS[tourCard].icon}</div>
                      <h3 className="text-base font-semibold text-foreground mb-2">{TOUR_CARDS[tourCard].title}</h3>
                      <p className="text-sm text-muted-foreground leading-relaxed">{TOUR_CARDS[tourCard].desc}</p>
                    </motion.div>
                  </AnimatePresence>
                </div>

                {/* Progress bar */}
                <div className="mt-4 h-1 bg-muted rounded-full overflow-hidden">
                  <motion.div
                    className="h-full bg-primary rounded-full"
                    style={{ width: `${tourProgress}%` }}
                    transition={{ duration: 0.05 }}
                  />
                </div>

                {/* Dot nav */}
                <div className="flex justify-center gap-2 mt-3">
                  {TOUR_CARDS.map((_, i) => (
                    <button
                      key={i}
                      onClick={() => advanceTourCard(i)}
                      className={`w-2 h-2 rounded-full transition-all ${
                        i === tourCard ? "bg-primary w-5" : "bg-muted-foreground/30 hover:bg-muted-foreground/50"
                      }`}
                    />
                  ))}
                </div>

                {tourCard < TOUR_CARDS.length - 1 ? (
                  <button
                    onClick={() => advanceTourCard(tourCard + 1)}
                    className="mt-6 w-full flex items-center justify-center gap-2 py-2.5 rounded-lg border border-border text-foreground font-medium text-sm hover:bg-muted transition-colors"
                  >
                    Next <ChevronRight className="w-4 h-4" />
                  </button>
                ) : (
                  <button
                    onClick={onComplete}
                    className="mt-6 w-full flex items-center justify-center gap-2 py-2.5 rounded-lg bg-primary text-primary-foreground font-medium text-sm hover:opacity-90 transition-opacity"
                  >
                    Start using CareerAgent <ArrowRight className="w-4 h-4" />
                  </button>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
