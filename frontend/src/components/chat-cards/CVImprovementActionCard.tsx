import { Wand2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { motion } from "framer-motion";

interface Props {
  onSendAction: (action: string) => void;
}

export function CVImprovementActionCard({ onSendAction }: Props) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: 0.15 }}
      className="mt-4 rounded-xl border border-violet-200 bg-violet-50/50 p-3.5"
    >
      <p className="text-[12px] text-slate-600 font-sans mb-3 leading-snug">
        Ready to apply these improvements directly to your CV?
      </p>
      <Button
        size="sm"
        className="w-full h-8 text-[12px] font-semibold bg-violet-600 hover:bg-violet-700 text-white gap-1.5 font-sans"
        onClick={() => onSendAction("__APPLY_CV_IMPROVEMENTS__")}
      >
        <Wand2 size={12} />
        Apply improvements to my CV
      </Button>
    </motion.div>
  );
}
