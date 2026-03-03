import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { AlertTriangle, Trash2, X } from "lucide-react";

interface ConfirmModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: () => void | Promise<void>;

  /** Modal variant — controls icon and colour scheme */
  variant?: "danger" | "warning";

  title: string;
  description: string;

  /**
   * If provided, the user must type this exact string before the confirm
   * button becomes active. Useful for destructive, irreversible actions.
   */
  confirmText?: string;

  /** Label shown in the confirmation input placeholder */
  confirmPlaceholder?: string;

  confirmLabel?: string;
  cancelLabel?: string;
  loading?: boolean;
}

export function ConfirmModal({
  open,
  onOpenChange,
  onConfirm,
  variant = "danger",
  title,
  description,
  confirmText,
  confirmPlaceholder,
  confirmLabel = "Delete",
  cancelLabel = "Cancel",
  loading = false,
}: ConfirmModalProps) {
  const [typed, setTyped] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Reset typed value whenever modal opens
  useEffect(() => {
    if (open) setTyped("");
  }, [open]);

  const canConfirm = confirmText ? typed === confirmText : true;

  const handleConfirm = async () => {
    if (!canConfirm || isSubmitting) return;
    setIsSubmitting(true);
    try {
      await onConfirm();
    } finally {
      setIsSubmitting(false);
    }
  };

  const isBusy = loading || isSubmitting;

  const accentRed = variant === "danger";

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div
            key="backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.18 }}
            className="fixed inset-0 z-[60] bg-black/40 backdrop-blur-sm"
            onClick={() => !isBusy && onOpenChange(false)}
          />

          {/* Panel */}
          <motion.div
            key="panel"
            initial={{ opacity: 0, scale: 0.94, y: 12 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.94, y: 12 }}
            transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
            className="fixed inset-0 z-[61] flex items-center justify-center p-4 pointer-events-none"
          >
            <div
              className="pointer-events-auto w-full max-w-md bg-white rounded-2xl shadow-2xl border border-black/[0.06] overflow-hidden"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Top accent bar */}
              <div className={`h-1 w-full ${accentRed ? "bg-gradient-to-r from-red-500 to-rose-600" : "bg-gradient-to-r from-amber-400 to-orange-500"}`} />

              <div className="p-6">
                {/* Header */}
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${accentRed ? "bg-red-50" : "bg-amber-50"}`}>
                      {accentRed ? (
                        <Trash2 className="w-5 h-5 text-red-500" />
                      ) : (
                        <AlertTriangle className="w-5 h-5 text-amber-500" />
                      )}
                    </div>
                    <h2 className="text-[16px] font-bold text-slate-900 font-sans leading-tight">{title}</h2>
                  </div>
                  <button
                    onClick={() => !isBusy && onOpenChange(false)}
                    disabled={isBusy}
                    className="w-7 h-7 flex items-center justify-center rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors disabled:opacity-40"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>

                {/* Description */}
                <p className="text-[13px] text-slate-500 font-sans leading-relaxed mb-5">
                  {description}
                </p>

                {/* Typed confirmation field */}
                {confirmText && (
                  <div className="mb-5 space-y-2">
                    <p className="text-[12px] font-semibold text-slate-600 font-sans">
                      Type{" "}
                      <code className={`px-1.5 py-0.5 rounded text-[11px] font-mono ${accentRed ? "bg-red-50 text-red-600" : "bg-amber-50 text-amber-700"}`}>
                        {confirmText}
                      </code>{" "}
                      to confirm:
                    </p>
                    <input
                      autoFocus
                      type="text"
                      value={typed}
                      onChange={(e) => setTyped(e.target.value)}
                      onKeyDown={(e) => e.key === "Enter" && handleConfirm()}
                      placeholder={confirmPlaceholder ?? confirmText}
                      className={`w-full h-10 px-3 rounded-xl border text-[13px] font-mono outline-none transition-all ${
                        typed && !canConfirm
                          ? "border-red-300 bg-red-50/50 focus:ring-2 focus:ring-red-200"
                          : canConfirm && typed
                          ? "border-green-300 bg-green-50/30 focus:ring-2 focus:ring-green-200"
                          : "border-slate-200 bg-slate-50 focus:border-slate-400 focus:ring-2 focus:ring-slate-100"
                      }`}
                    />
                  </div>
                )}

                {/* Actions */}
                <div className="flex gap-2 justify-end">
                  <button
                    onClick={() => onOpenChange(false)}
                    disabled={isBusy}
                    className="px-4 py-2 rounded-xl text-[13px] font-semibold text-slate-600 bg-slate-100 hover:bg-slate-200 transition-colors disabled:opacity-50 active:scale-[0.97]"
                  >
                    {cancelLabel}
                  </button>
                  <button
                    onClick={handleConfirm}
                    disabled={!canConfirm || isBusy}
                    className={`px-4 py-2 rounded-xl text-[13px] font-semibold text-white transition-all active:scale-[0.97] disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-2 ${
                      accentRed
                        ? "bg-gradient-to-b from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 shadow-sm shadow-red-200"
                        : "bg-gradient-to-b from-amber-500 to-amber-600 hover:from-amber-600 hover:to-amber-700 shadow-sm shadow-amber-200"
                    }`}
                  >
                    {isBusy && (
                      <div className="w-3.5 h-3.5 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                    )}
                    {isBusy ? "Deleting..." : confirmLabel}
                  </button>
                </div>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
