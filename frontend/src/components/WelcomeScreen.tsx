import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowRight, Mail, Lock, Loader2 } from "lucide-react";
import { useAuthStore } from "@/hooks/useAuth";

const GREETING_WORDS = "Sign in to CareerAgent".split(" ");

interface WelcomeScreenProps {
  onSubmit: () => void;
  isExiting: boolean;
}

export const WelcomeScreen = ({ onSubmit, isExiting }: WelcomeScreenProps) => {
  const [email, setEmail] = useState("azanmian123123@gmail.com");
  const [password, setPassword] = useState("");
  const [isLogin, setIsLogin] = useState(true);

  const emailRef = useRef<HTMLInputElement>(null);

  const { login, signup, isLoading, error, clearError } = useAuthStore();

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
    <div className="relative w-full h-screen flex flex-col items-center justify-center overflow-hidden bg-background">
      {/* Ambient blob 1 — top-right */}
      <motion.div
        className="absolute top-[15%] right-[15%] w-[600px] h-[600px] rounded-full bg-rose-50 opacity-30 pointer-events-none"
        style={{ filter: "blur(80px)", animation: "drift 20s ease-in-out infinite" }}
        animate={isExiting ? { opacity: 0 } : {}}
        transition={{ duration: 0.6 }}
      />

      {/* Ambient blob 2 — bottom-left */}
      <motion.div
        className="absolute bottom-[10%] left-[10%] w-[500px] h-[500px] rounded-full bg-slate-100 opacity-20 pointer-events-none"
        style={{ filter: "blur(80px)", animation: "drift-reverse 18s ease-in-out infinite" }}
        animate={isExiting ? { opacity: 0 } : {}}
        transition={{ duration: 0.6 }}
      />

      {/* Floating brand logo */}
      <motion.div
        className="flex flex-col items-center relative z-10"
        initial={{ opacity: 0, y: -15, scale: 0.92 }}
        animate={isExiting ? { opacity: 0, y: -30, filter: "blur(4px)" } : { opacity: 1, y: 0, scale: 1 }}
        transition={isExiting ? { duration: 0.5, delay: 0.3 } : { duration: 0.8, ease: "easeOut", delay: 0.2 }}
        style={{ willChange: "transform" }}
      >
        <motion.div
          animate={isExiting ? {} : { y: [0, -8, 0] }}
          transition={{ duration: 6, ease: "easeInOut", repeat: Infinity, repeatType: "loop" }}
          style={{ willChange: "transform" }}
        >
          <h1 className="text-5xl font-serif font-bold tracking-tight">
            <span className="text-foreground">Career</span>
            <span className="text-primary">Agent</span>
          </h1>
          <p className="mt-1 text-xs text-slate-400 uppercase tracking-[0.15em] text-center font-sans">
            AI-Powered Job Assistant
          </p>
        </motion.div>
      </motion.div>

      {/* Greeting — word-by-word stagger */}
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
            className="text-2xl font-serif text-slate-700"
            variants={{
              initial: { opacity: 0, y: 12, filter: "blur(4px)" },
              animate: { opacity: 1, y: 0, filter: "blur(0px)", transition: { duration: 0.5, ease: "easeOut" } },
              exit: { opacity: 0, filter: "blur(4px)", transition: { duration: 0.3 } },
            }}
          >
            {word}
          </motion.span>
        ))}
      </motion.div>

      {/* Subtitle */}
      <motion.p
        className="mt-3 text-base text-muted-foreground font-sans max-w-md text-center"
        initial={{ opacity: 0, y: 8 }}
        animate={isExiting ? { opacity: 0, filter: "blur(4px)" } : { opacity: 1, y: 0 }}
        transition={isExiting ? { duration: 0.3, delay: 0.1 } : { duration: 0.6, delay: 1.2, ease: "easeOut" }}
      >
        {isLogin ? "Welcome back. Let's find your next role." : "Create an account to automate your job search."}
      </motion.p>

      {error && (
        <motion.p
          className="mt-2 text-sm text-red-500 font-medium"
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
        >
          {error}
        </motion.p>
      )}

      {/* Central Auth Form */}
      <AnimatePresence mode="wait">
        <motion.form
          key="auth-form"
          onSubmit={handleSubmit}
          className="mt-8 w-[min(400px,90vw)] flex flex-col gap-4 relative z-10"
          initial={{ opacity: 0, y: 30, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ type: "spring", stiffness: 120, damping: 20, delay: 1.4 }}
        >
          <div className="h-14 bg-background border border-border rounded-xl shadow-sm flex items-center px-4 gap-3 transition-all duration-200 focus-within:border-primary focus-within:ring-[3px] focus-within:ring-primary/10">
            <Mail size={18} className="text-slate-400 flex-shrink-0" />
            <input
              ref={emailRef}
              type="email"
              value={email}
              onChange={(e) => { setEmail(e.target.value); clearError(); }}
              placeholder="Email address"
              className="flex-1 bg-transparent border-none outline-none text-base font-sans text-foreground placeholder:text-slate-400 caret-primary"
              required
            />
          </div>

          <div className="h-14 bg-background border border-border rounded-xl shadow-sm flex items-center px-4 gap-3 transition-all duration-200 focus-within:border-primary focus-within:ring-[3px] focus-within:ring-primary/10">
            <Lock size={18} className="text-slate-400 flex-shrink-0" />
            <input
              type="password"
              value={password}
              onChange={(e) => { setPassword(e.target.value); clearError(); }}
              placeholder="Password"
              className="flex-1 bg-transparent border-none outline-none text-base font-sans text-foreground placeholder:text-slate-400 caret-primary"
              required
            />
          </div>

          <button
            type="submit"
            disabled={!email.trim() || !password.trim() || isLoading}
            className="h-14 mt-2 rounded-xl flex items-center justify-center gap-2 transition-all duration-200 disabled:bg-slate-100 disabled:text-slate-400 disabled:pointer-events-none bg-primary text-primary-foreground hover:bg-rose-700 hover:shadow-glow-rose active:scale-[0.98]"
          >
            {isLoading ? <Loader2 size={20} className="animate-spin" /> : (
              <>
                <span className="font-medium text-base">{isLogin ? "Sign In" : "Create Account"}</span>
                <ArrowRight size={18} />
              </>
            )}
          </button>

          <div className="text-center mt-2">
            <button
              type="button"
              onClick={() => { setIsLogin(!isLogin); clearError(); }}
              className="text-sm text-slate-500 hover:text-primary transition-colors"
            >
              {isLogin ? "Don't have an account? Sign up" : "Already have an account? Sign in"}
            </button>
          </div>
        </motion.form>
      </AnimatePresence>

      {/* Footer */}
      <motion.p
        className="absolute bottom-6 text-[11px] font-sans text-slate-400"
        initial={{ opacity: 0 }}
        animate={isExiting ? { opacity: 0 } : { opacity: 1 }}
        transition={isExiting ? { duration: 0.3 } : { delay: 2.5, duration: 0.6 }}
      >
        Powered by LangGraph · LangSmith · OpenAI
      </motion.p>
    </div>
  );
};
