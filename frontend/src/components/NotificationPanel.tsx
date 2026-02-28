import { motion } from "framer-motion";
import { CheckCircle, Star, FileText, Mail, AlertTriangle, Bell } from "lucide-react";

export function NotificationPanel() {
  return (
    <motion.div
      initial={{ opacity: 0, y: -8, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -8, scale: 0.95 }}
      transition={{ type: "spring", stiffness: 300, damping: 25 }}
      className="absolute top-12 right-0 w-[380px] max-h-[480px] bg-white rounded-xl shadow-lg border border-slate-200 overflow-hidden flex flex-col z-50"
    >
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100 bg-white sticky top-0 z-10">
        <span className="text-[15px] font-semibold text-black font-sans">Notifications</span>
        <button className="text-xs text-rose-600 hover:underline font-sans font-medium">
          Mark all read
        </button>
      </div>

      <div className="overflow-y-auto">
        {/* Notification 1 (Unread) */}
        <div className="flex gap-3 px-4 py-3 bg-rose-50/30 border-l-[3px] border-l-rose-500 hover:bg-rose-50/50 transition-colors cursor-pointer">
          <div className="mt-0.5">
            <CheckCircle size={18} className="text-green-600" />
          </div>
          <div>
            <p className="text-[13px] font-semibold text-slate-800 font-sans leading-tight">Application sent to Stripe</p>
            <p className="text-xs text-slate-500 font-sans mt-1 leading-snug">Your tailored CV was emailed to sarah.baker@stripe.com</p>
            <p className="text-[11px] text-slate-400 font-sans mt-1.5">2 minutes ago</p>
          </div>
        </div>

        {/* Notification 2 (Unread) */}
        <div className="flex gap-3 px-4 py-3 bg-rose-50/30 border-l-[3px] border-l-transparent hover:bg-rose-50/50 transition-colors cursor-pointer">
          <div className="mt-0.5">
            <Star size={18} className="text-amber-500" />
          </div>
          <div>
            <p className="text-[13px] font-semibold text-slate-800 font-sans leading-tight">New high-match job found</p>
            <p className="text-xs text-slate-500 font-sans mt-1 leading-snug">Shopify — React Lead (79% match) was added to your pipeline.</p>
            <p className="text-[11px] text-slate-400 font-sans mt-1.5">15 minutes ago</p>
          </div>
        </div>

        {/* Notification 3 (Read) */}
        <div className="flex gap-3 px-4 py-3 bg-white hover:bg-slate-50 transition-colors cursor-pointer">
          <div className="mt-0.5">
            <FileText size={18} className="text-slate-500" />
          </div>
          <div>
            <p className="text-[13px] font-semibold text-slate-800 font-sans leading-tight">Resume indexed successfully</p>
            <p className="text-xs text-slate-500 font-sans mt-1 leading-snug">John_Doe_Resume_2024.pdf has been processed and vectorized.</p>
            <p className="text-[11px] text-slate-400 font-sans mt-1.5">2 hours ago</p>
          </div>
        </div>

        {/* Notification 4 (Read) */}
        <div className="flex gap-3 px-4 py-3 bg-white hover:bg-slate-50 transition-colors cursor-pointer">
          <div className="mt-0.5">
            <Mail size={18} className="text-blue-500" />
          </div>
          <div>
            <p className="text-[13px] font-semibold text-slate-800 font-sans leading-tight">Gmail connected</p>
            <p className="text-xs text-slate-500 font-sans mt-1 leading-snug">johndoe.careers@gmail.com is now linked for outreach.</p>
            <p className="text-[11px] text-slate-400 font-sans mt-1.5">3 hours ago</p>
          </div>
        </div>

        {/* Notification 5 (Read) */}
        <div className="flex gap-3 px-4 py-3 bg-white hover:bg-slate-50 transition-colors cursor-pointer">
          <div className="mt-0.5">
            <AlertTriangle size={18} className="text-amber-500" />
          </div>
          <div>
            <p className="text-[13px] font-semibold text-slate-800 font-sans leading-tight">Hunter.io credits running low</p>
            <p className="text-xs text-slate-500 font-sans mt-1 leading-snug">42 of 500 monthly credits remaining. Consider upgrading.</p>
            <p className="text-[11px] text-slate-400 font-sans mt-1.5">5 hours ago</p>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
