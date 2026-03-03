import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowRight, Mail, Lock, Loader2, CheckCircle } from "lucide-react";
import { useAuthStore } from "@/hooks/useAuth";
import { forgotPassword } from "@/services/api";

const GREETING_WORDS = "Sign in to CareerAgent".split(" ");

interface WelcomeScreenProps {
  onSubmit: () => void;
  isExiting: boolean;
}

export const WelcomeScreen = ({ onSubmit, isExiting }: WelcomeScreenProps) => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLogin, setIsLogin] = useState(true);
  const [view, setView] = useState<"auth" | "forgot" | "forgot_sent">("auth");
  const [forgotEmail, setForgotEmail] = useState("");
  const [forgotLoading, setForgotLoading] = useState(false);
  const [forgotError, setForgotError] = useState("");

  const emailRef = useRef<HTMLInputElement>(null);

  const { login, signup, isLoading, error, clearError } = useAuthStore();

  const handleForgotSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!forgotEmail.trim()) return;
    setForgotLoading(true);
    setForgotError("");
    try {
      await forgotPassword(forgotEmail.trim());
      setView("forgot_sent");
    } catch (err: any) {
      setForgotError(err.message || "Something went wrong. Please try again.");
    } finally {
      setForgotLoading(false);
    }
  };

  useEffect(() => {
    const timer = setTimeout(() => emailRef.current?.focus(), 2000);
    return () => clearTimeout(timer);
  }, []);

  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!email.trim() || !password.trim()) return;

    try {
      if (isLogin) {
        await login(email, password);
      } else {
        await signup(email.split("@")[0], email, password);
      }
      onSubmit();
    } catch (err) {
      console.error("Auth error", err);
    }
  };

  return (
    <div className="relative w-full h-screen flex flex-col items-center justify-center overflow-hidden bg-slate-50">

      {/* Subtle dot-grid backdrop */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          backgroundImage: "radial-gradient(circle, rgba(0,0,0,0.05) 1px, transparent 1px)",
          backgroundSize: "24px 24px",
        }}
      />

      {/* Ambient blob 1 — top-right */}
      <motion.div
        className="absolute top-[12%] right-[12%] w-[520px] h-[520px] rounded-full bg-rose-50 opacity-60 pointer-events-none"
        style={{ filter: "blur(90px)", animation: "drift 22s ease-in-out infinite" }}
        animate={isExiting ? { opacity: 0 } : {}}
        transition={{ duration: 0.6 }}
      />

      {/* Ambient blob 2 — bottom-left */}
      <motion.div
        className="absolute bottom-[8%] left-[8%] w-[440px] h-[440px] rounded-full bg-primary/10 opacity-50 pointer-events-none"
        style={{ filter: "blur(90px)", animation: "drift-reverse 18s ease-in-out infinite" }}
        animate={isExiting ? { opacity: 0 } : {}}
        transition={{ duration: 0.6 }}
      />

      {/* Brand mark */}
      <motion.div
        className="flex flex-col items-center relative z-10"
        initial={{ opacity: 0, y: -15, scale: 0.94 }}
        animate={isExiting ? { opacity: 0, y: -30, filter: "blur(4px)" } : { opacity: 1, y: 0, scale: 1 }}
        transition={isExiting ? { duration: 0.5, delay: 0.3 } : { duration: 0.8, ease: [0.16, 1, 0.32, 1], delay: 0.2 }}
        style={{ willChange: "transform" }}
      >
        <motion.div
          animate={isExiting ? {} : { y: [0, -8, 0] }}
          transition={{ duration: 6, ease: "easeInOut", repeat: Infinity, repeatType: "loop" }}
          style={{ willChange: "transform" }}
        >
          <h1 className="text-5xl font-serif font-normal tracking-tight">
            <span className="text-foreground">Career</span>
            <span className="text-primary">Agent</span>
          </h1>
          <p className="mt-2 text-[11px] text-slate-400 uppercase tracking-[0.18em] text-center font-sans font-medium">
            AI-Powered Job Assistant
          </p>
        </motion.div>
      </motion.div>

      {/* Animated greeting */}
      <motion.div
        className="mt-8 flex flex-wrap justify-center gap-x-2"
        initial="initial"
        animate={isExiting ? "exit" : "animate"}
        variants={{
          animate: { transition: { staggerChildren: 0.08, delayChildren: 0.8 } },
          exit: { transition: { staggerChildren: 0.04 } },
        }}
      >
        {GREETING_WORDS.map((word, i) => (
          <motion.span
            key={i}
            className="text-[22px] font-serif text-slate-700"
            variants={{
              initial: { opacity: 0, y: 12, filter: "blur(4px)" },
              animate: { opacity: 1, y: 0, filter: "blur(0px)", transition: { duration: 0.5, ease: [0.16, 1, 0.32, 1] } },
              exit: { opacity: 0, filter: "blur(4px)", transition: { duration: 0.3 } },
            }}
          >
            {word}
          </motion.span>
        ))}
      </motion.div>

      {/* Subtitle */}
      <motion.p
        className="mt-3 text-[14px] text-slate-500 font-sans max-w-md text-center leading-relaxed"
        initial={{ opacity: 0, y: 8 }}
        animate={isExiting ? { opacity: 0, filter: "blur(4px)" } : { opacity: 1, y: 0 }}
        transition={isExiting ? { duration: 0.3, delay: 0.1 } : { duration: 0.6, delay: 1.2, ease: "easeOut" }}
      >
        {isLogin ? "Welcome back. Let's find your next role." : "Create an account to automate your job search."}
      </motion.p>

      {/* Error */}
      {error && (
        <motion.p
          className="mt-2 text-[13px] text-red-500 font-medium"
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
        >
          {error}
        </motion.p>
      )}

      {/* Auth form — glass card */}
      <AnimatePresence mode="wait">

        {/* ── Forgot password sent ── */}
        {view === "forgot_sent" && (
          <motion.div
            key="forgot-sent"
            className="mt-8 w-[min(420px,90vw)] flex flex-col items-center gap-4 relative z-10"
            initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            style={{ background:"rgba(255,255,255,0.85)", backdropFilter:"blur(16px)", WebkitBackdropFilter:"blur(16px)", border:"1px solid rgba(255,255,255,0.80)", borderRadius:"20px", padding:"28px 24px", boxShadow:"0 8px 40px -8px rgba(0,0,0,0.12)" }}
          >
            <CheckCircle size={36} className="text-green-500" />
            <p className="text-[15px] font-semibold text-slate-700 text-center">Check your inbox</p>
            <p className="text-[13px] text-slate-500 text-center leading-relaxed">
              If <span className="font-medium">{forgotEmail}</span> is registered, we've sent a reset link. It expires in 1 hour.
            </p>
            <button
              type="button"
              onClick={() => setView("auth")}
              className="text-[12px] text-primary hover:underline font-medium"
            >
              Back to sign in
            </button>
          </motion.div>
        )}

        {/* ── Forgot password form ── */}
        {view === "forgot" && (
          <motion.form
            key="forgot-form"
            onSubmit={handleForgotSubmit}
            className="mt-8 w-[min(420px,90vw)] flex flex-col gap-3 relative z-10"
            initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            style={{ background:"rgba(255,255,255,0.85)", backdropFilter:"blur(16px)", WebkitBackdropFilter:"blur(16px)", border:"1px solid rgba(255,255,255,0.80)", borderRadius:"20px", padding:"24px", boxShadow:"0 8px 40px -8px rgba(0,0,0,0.12)" }}
          >
            <p className="text-[14px] font-semibold text-slate-700">Reset your password</p>
            <p className="text-[12px] text-slate-500 -mt-1">Enter your email and we'll send you a reset link.</p>

            {forgotError && <p className="text-[12px] text-red-500">{forgotError}</p>}

            <div className="h-12 bg-white/70 border border-black/[0.09] rounded-xl flex items-center px-4 gap-3 focus-within:border-primary focus-within:ring-[3px] focus-within:ring-primary/10 focus-within:bg-white">
              <Mail size={15} className="text-slate-400 flex-shrink-0" />
              <input
                type="email"
                value={forgotEmail}
                onChange={(e) => setForgotEmail(e.target.value)}
                placeholder="Email address"
                className="flex-1 bg-transparent border-none outline-none text-[14px] font-sans text-foreground placeholder:text-slate-400 caret-primary"
                required
                autoFocus
              />
            </div>

            <button
              type="submit"
              disabled={!forgotEmail.trim() || forgotLoading}
              className="h-12 mt-1 rounded-xl flex items-center justify-center gap-2 bg-primary text-white hover:brightness-110 active:scale-[0.98] disabled:opacity-40 disabled:pointer-events-none transition-all"
              style={{ boxShadow: "var(--shadow-brand-sm)" }}
            >
              {forgotLoading ? <Loader2 size={18} className="animate-spin" /> : (
                <><span className="font-semibold text-[14px]">Send Reset Link</span><ArrowRight size={16} /></>
              )}
            </button>

            <div className="text-center">
              <button type="button" onClick={() => setView("auth")} className="text-[12px] text-slate-500 hover:text-primary transition-colors font-medium">
                Back to sign in
              </button>
            </div>
          </motion.form>
        )}

        {/* ── Main auth form ── */}
        {view === "auth" && (
        <motion.form
          key="auth-form"
          onSubmit={handleSubmit}
          className="mt-8 w-[min(420px,90vw)] flex flex-col gap-3 relative z-10"
          initial={{ opacity: 0, y: 24, scale: 0.97 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ type: "spring", stiffness: 140, damping: 22, delay: 1.4 }}
          style={{
            background: "rgba(255,255,255,0.85)",
            backdropFilter: "blur(16px)",
            WebkitBackdropFilter: "blur(16px)",
            border: "1px solid rgba(255,255,255,0.80)",
            borderRadius: "20px",
            padding: "24px",
            boxShadow: "0 8px 40px -8px rgba(0,0,0,0.12), 0 2px 8px -2px rgba(0,0,0,0.06), inset 0 1px 0 rgba(255,255,255,0.9)",
          }}
        >
          {/* Email input */}
          <div className="h-12 bg-white/70 border border-black/[0.09] rounded-xl flex items-center px-4 gap-3 transition-all duration-200 focus-within:border-primary focus-within:ring-[3px] focus-within:ring-primary/10 focus-within:bg-white">
            <Mail size={15} className="text-slate-400 flex-shrink-0" />
            <input
              ref={emailRef}
              type="email"
              value={email}
              onChange={(e) => { setEmail(e.target.value); clearError(); }}
              placeholder="Email address"
              className="flex-1 bg-transparent border-none outline-none text-[14px] font-sans text-foreground placeholder:text-slate-400 caret-primary"
              required
            />
          </div>

          {/* Password input */}
          <div className="h-12 bg-white/70 border border-black/[0.09] rounded-xl flex items-center px-4 gap-3 transition-all duration-200 focus-within:border-primary focus-within:ring-[3px] focus-within:ring-primary/10 focus-within:bg-white">
            <Lock size={15} className="text-slate-400 flex-shrink-0" />
            <input
              type="password"
              value={password}
              onChange={(e) => { setPassword(e.target.value); clearError(); }}
              placeholder="Password"
              className="flex-1 bg-transparent border-none outline-none text-[14px] font-sans text-foreground placeholder:text-slate-400 caret-primary"
              required
            />
          </div>

          {/* Forgot password */}
          {isLogin && (
            <div className="text-right -mt-1">
              <button
                type="button"
                onClick={() => { setView("forgot"); setForgotEmail(email); clearError(); }}
                className="text-[11px] text-slate-400 hover:text-primary transition-colors"
              >
                Forgot password?
              </button>
            </div>
          )}

          {/* Submit */}
          <button
            type="submit"
            disabled={!email.trim() || !password.trim() || isLoading}
            className="h-12 mt-1 rounded-xl flex items-center justify-center gap-2 transition-all duration-200 disabled:opacity-40 disabled:pointer-events-none bg-primary text-white hover:brightness-110 active:scale-[0.98]"
            style={{ boxShadow: "var(--shadow-brand-sm)" }}
          >
            {isLoading ? <Loader2 size={18} className="animate-spin" /> : (
              <>
                <span className="font-semibold text-[14px]">{isLogin ? "Sign In" : "Create Account"}</span>
                <ArrowRight size={16} />
              </>
            )}
          </button>

          {/* Toggle */}
          <div className="text-center mt-1">
            <button
              type="button"
              onClick={() => { setIsLogin(!isLogin); clearError(); }}
              className="text-[12px] text-slate-500 hover:text-primary transition-colors font-medium"
            >
              {isLogin ? "Don't have an account? Sign up" : "Already have an account? Sign in"}
            </button>
          </div>
        </motion.form>
        )}
      </AnimatePresence>

      {/* Footer */}
      <motion.p
        className="absolute bottom-6 text-[11px] font-sans text-slate-400 tracking-wide"
        initial={{ opacity: 0 }}
        animate={isExiting ? { opacity: 0 } : { opacity: 1 }}
        transition={isExiting ? { duration: 0.3 } : { delay: 2.5, duration: 0.6 }}
      >
        Powered by LangGraph · LangSmith · OpenAI
      </motion.p>
    </div>
  );
};
