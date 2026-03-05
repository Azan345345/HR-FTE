import { Download, Edit3, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { useAuthStore } from "@/hooks/useAuth";

interface CVImprovedMeta {
  type: "cv_improved";
  tailored_cv_id: string;
  has_pdf?: boolean;
  name?: string;
}

interface Props {
  metadata: CVImprovedMeta;
  onSendAction: (action: string) => void;
  actionInFlight?: string | null;
}

export function CVImprovedCard({ metadata, onSendAction, actionInFlight }: Props) {
  // C5 fix: Null guards
  const tailored_cv_id = metadata?.tailored_cv_id ?? "";
  const name = metadata?.name;

  const handleDownload = async () => {
    const token = useAuthStore.getState().token;
    const url = `/api/cv/tailored/${tailored_cv_id}/download`;
    try {
      const res = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        // L12 fix: Handle 401 with redirect instead of stale token error
        if (res.status === 401) {
          localStorage.removeItem("digital-fte-auth");
          if (!sessionStorage.getItem("auth_redirect")) {
            sessionStorage.setItem("auth_redirect", "1");
            window.location.href = "/";
          }
          return;
        }
        const errBody = await res.json().catch(() => null);
        const detail = errBody?.detail || `Server error ${res.status}`;
        throw new Error(detail);
      }
      const blob = await res.blob();
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = name
        ? `Tailored_CV_${name.replace(/\s+/g, "_")}.pdf`
        : "Tailored_CV.pdf";
      link.style.display = "none";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      setTimeout(() => URL.revokeObjectURL(link.href), 10000);
    } catch (err: any) {
      toast.error(err.message || "Could not download the PDF.", {
        duration: 6000,
      });
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay: 0.1 }}
      className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50/40 p-4"
    >
      {/* Header */}
      <div className="flex items-center gap-2 mb-2">
        <CheckCircle2 size={15} className="text-emerald-500 flex-shrink-0" />
        <span className="text-[14px] font-semibold text-slate-800 font-sans">
          CV Improvements Applied
        </span>
      </div>

      <p className="text-[12px] text-slate-500 font-sans leading-snug mb-4">
        Your updated CV is ready. Download the PDF or open the editor to fine-tune any section.
      </p>

      <div className="flex gap-2">
        <Button
          size="sm"
          className="flex-1 h-8 text-[12px] font-semibold bg-emerald-600 hover:bg-emerald-700 text-white gap-1.5 font-sans"
          onClick={handleDownload}
        >
          <Download size={12} />
          Download PDF
        </Button>
        <Button
          size="sm"
          variant="outline"
          disabled={!!actionInFlight}
          className="flex-1 h-8 text-[12px] font-sans border-slate-200 text-slate-600 hover:text-slate-900 hover:border-slate-300 gap-1 disabled:opacity-50"
          onClick={() => onSendAction(`__EDIT_CV__:${tailored_cv_id}:{}`)}
        >
          <Edit3 size={11} />
          Edit in Modal
        </Button>
      </div>
    </motion.div>
  );
}
