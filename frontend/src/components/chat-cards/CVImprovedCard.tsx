import { Download, Edit3, CheckCircle2, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { motion } from "framer-motion";

interface CVImprovedMeta {
  type: "cv_improved";
  tailored_cv_id: string;
  has_pdf: boolean;
  name?: string;
}

interface Props {
  metadata: CVImprovedMeta;
  onSendAction: (action: string) => void;
}

export function CVImprovedCard({ metadata, onSendAction }: Props) {
  const { tailored_cv_id, has_pdf, name } = metadata;

  const handleDownload = async () => {
    const token = localStorage.getItem("token");
    const base = (import.meta as any).env?.VITE_API_URL || "http://localhost:8080";
    const url = `${base}/api/cv/tailored/${tailored_cv_id}/download`;
    try {
      const res = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Download failed");
      const blob = await res.blob();
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = name
        ? `Improved_CV_${name.replace(/\s+/g, "_")}.pdf`
        : "Improved_CV.pdf";
      link.click();
      URL.revokeObjectURL(link.href);
    } catch {
      alert("Could not download the PDF. Please try again.");
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
        {has_pdf
          ? "Your updated CV is ready. Download the PDF or open the editor to fine-tune any section."
          : "Your updated CV data has been saved. Open the editor to review and make any final adjustments."}
      </p>

      <div className="flex gap-2">
        {has_pdf && (
          <Button
            size="sm"
            className="flex-1 h-8 text-[12px] font-semibold bg-emerald-600 hover:bg-emerald-700 text-white gap-1.5 font-sans"
            onClick={handleDownload}
          >
            <Download size={12} />
            Download PDF
          </Button>
        )}
        <Button
          size="sm"
          variant="outline"
          className="flex-1 h-8 text-[12px] font-sans border-slate-200 text-slate-600 hover:text-slate-900 hover:border-slate-300 gap-1"
          onClick={() => onSendAction(`__EDIT_CV__:${tailored_cv_id}:{}`)}
        >
          <Edit3 size={11} />
          Edit in Modal
        </Button>
      </div>

      {!has_pdf && (
        <p className="text-[10px] text-slate-400 font-sans mt-2 text-center">
          <FileText size={9} className="inline mr-0.5" />
          PDF generation encountered an issue — editing is still fully available.
        </p>
      )}
    </motion.div>
  );
}
