import { useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Lock, Loader2, ArrowRight, CheckCircle } from "lucide-react";
import { resetPassword } from "@/services/api";

export default function ResetPassword() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const token = params.get("token") || "";

  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password.length < 6) { setError("Password must be at least 6 characters."); return; }
    if (password !== confirm) { setError("Passwords do not match."); return; }
    setLoading(true);
    setError("");
    try {
      await resetPassword(token, password);
      setDone(true);
    } catch (err: any) {
      setError(err.message || "Reset failed. The link may have expired.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-slate-50"
      style={{ backgroundImage: "radial-gradient(circle, rgba(0,0,0,0.05) 1px, transparent 1px)", backgroundSize: "24px 24px" }}>

      <motion.div
        initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.32, 1] }}
        className="w-[min(420px,90vw)]"
        style={{ background: "rgba(255,255,255,0.90)", backdropFilter: "blur(16px)", WebkitBackdropFilter: "blur(16px)", border: "1px solid rgba(255,255,255,0.80)", borderRadius: "20px", padding: "28px 24px", boxShadow: "0 8px 40px -8px rgba(0,0,0,0.12), 0 2px 8px -2px rgba(0,0,0,0.06)" }}
      >
        {done ? (
          <div className="flex flex-col items-center gap-4 py-4">
            <CheckCircle size={40} className="text-green-500" />
            <p className="text-[15px] font-semibold text-slate-700">Password updated!</p>
            <p className="text-[13px] text-slate-500 text-center">Your password has been reset. You can now sign in.</p>
            <button
              onClick={() => navigate("/")}
              className="mt-2 h-11 w-full rounded-xl bg-primary text-white font-semibold text-[14px] hover:brightness-110 active:scale-[0.98] transition-all"
              style={{ boxShadow: "var(--shadow-brand-sm)" }}
            >
              Go to Sign In
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="flex flex-col gap-3">
            <div className="mb-1">
              <h1 className="text-[16px] font-semibold text-slate-700">Set a new password</h1>
              <p className="text-[12px] text-slate-500 mt-0.5">Choose a strong password for your CareerAgent account.</p>
            </div>

            {!token && (
              <p className="text-[13px] text-red-500 bg-red-50 rounded-lg px-3 py-2">
                Invalid reset link. Please request a new one.
              </p>
            )}

            {error && <p className="text-[12px] text-red-500">{error}</p>}

            <div className="h-12 bg-white/70 border border-black/[0.09] rounded-xl flex items-center px-4 gap-3 focus-within:border-primary focus-within:ring-[3px] focus-within:ring-primary/10 focus-within:bg-white">
              <Lock size={15} className="text-slate-400 flex-shrink-0" />
              <input
                type="password"
                value={password}
                onChange={(e) => { setPassword(e.target.value); setError(""); }}
                placeholder="New password"
                className="flex-1 bg-transparent border-none outline-none text-[14px] font-sans text-foreground placeholder:text-slate-400 caret-primary"
                required
                minLength={6}
                autoFocus
              />
            </div>

            <div className="h-12 bg-white/70 border border-black/[0.09] rounded-xl flex items-center px-4 gap-3 focus-within:border-primary focus-within:ring-[3px] focus-within:ring-primary/10 focus-within:bg-white">
              <Lock size={15} className="text-slate-400 flex-shrink-0" />
              <input
                type="password"
                value={confirm}
                onChange={(e) => { setConfirm(e.target.value); setError(""); }}
                placeholder="Confirm new password"
                className="flex-1 bg-transparent border-none outline-none text-[14px] font-sans text-foreground placeholder:text-slate-400 caret-primary"
                required
              />
            </div>

            <button
              type="submit"
              disabled={!password || !confirm || !token || loading}
              className="h-12 mt-1 rounded-xl flex items-center justify-center gap-2 bg-primary text-white hover:brightness-110 active:scale-[0.98] disabled:opacity-40 disabled:pointer-events-none transition-all"
              style={{ boxShadow: "var(--shadow-brand-sm)" }}
            >
              {loading ? <Loader2 size={18} className="animate-spin" /> : (
                <><span className="font-semibold text-[14px]">Reset Password</span><ArrowRight size={16} /></>
              )}
            </button>

            <div className="text-center">
              <button type="button" onClick={() => navigate("/")} className="text-[12px] text-slate-500 hover:text-primary transition-colors">
                Back to sign in
              </button>
            </div>
          </form>
        )}
      </motion.div>
    </div>
  );
}
