import { useState, useRef } from "react";
import { Send, Edit3, X, Paperclip, ShieldCheck, User, Sparkles, Wand2, GitCompare, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "sonner";
import { aiRewriteEmail } from "@/services/api";

interface HRContact {
  name?: string;
  email?: string;
  title?: string;
  confidence_score?: number;
  source?: string;
}

interface EmailData {
  subject: string;
  body: string;
  cc?: string;
}

interface EmailReviewMeta {
  type: "email_review";
  application_id: string;
  hr_contact: HRContact;
  email: EmailData;
  pdf_filename?: string;
}

interface Props {
  metadata: EmailReviewMeta;
  onSendAction: (action: string) => void;
}

// ── Line-level diff ────────────────────────────────────────────────────────────
interface DiffLine {
  text: string;
  status: "unchanged" | "added" | "removed";
}

function computeLineDiff(oldText: string, newText: string): DiffLine[] {
  const oldLines = oldText.split("\n");
  const newLines = newText.split("\n");
  const oldSet = new Set(oldLines.map(l => l.trim()).filter(Boolean));
  const newSet = new Set(newLines.map(l => l.trim()).filter(Boolean));

  const result: DiffLine[] = [];

  // Lines in old but not new → removed
  for (const line of oldLines) {
    if (line.trim() && !newSet.has(line.trim())) {
      result.push({ text: line, status: "removed" });
    }
  }

  // All new lines, marking which are actually new
  for (const line of newLines) {
    if (!line.trim()) {
      result.push({ text: line, status: "unchanged" });
    } else if (!oldSet.has(line.trim())) {
      result.push({ text: line, status: "added" });
    } else {
      result.push({ text: line, status: "unchanged" });
    }
  }

  return result;
}

function countChangedLines(diff: DiffLine[]): number {
  return diff.filter(l => l.status !== "unchanged").length;
}

export function EmailReviewCard({ metadata, onSendAction }: Props) {
  const { application_id, hr_contact, email, pdf_filename } = metadata;

  const [editOpen, setEditOpen] = useState(false);
  const [editedBody, setEditedBody] = useState(email.body);
  const [editedSubject, setEditedSubject] = useState(email.subject);
  const [cancelled, setCancelled] = useState(false);
  const [aiInstruction, setAiInstruction] = useState("");
  const [aiLoading, setAiLoading] = useState(false);
  const aiInputRef = useRef<HTMLInputElement>(null);

  // ── Diff tracking state ─────────────────────────────────────────────────────
  const [diffLines, setDiffLines] = useState<DiffLine[]>([]);
  const [prevSubject, setPrevSubject] = useState<string | null>(null);
  const [showDiff, setShowDiff] = useState(false);
  const [rewriteCount, setRewriteCount] = useState(0);

  const changedLineCount = diffLines.filter(l => l.status !== "unchanged").length;

  // ── AI rewrite — applies to card preview immediately ───────────────────────
  const handleAiRewrite = async () => {
    if (!aiInstruction.trim() || aiLoading) return;
    setAiLoading(true);
    const instruction = aiInstruction.trim();
    setAiInstruction("");
    try {
      const resp = await aiRewriteEmail({
        subject: editedSubject,
        body: editedBody,
        instruction,
        job_title: "",
        job_company: hr_contact.name || "",
      });

      // Compute diff before applying changes
      const diff = computeLineDiff(editedBody, resp.body);

      setPrevSubject(editedSubject !== resp.subject ? editedSubject : null);
      setEditedSubject(resp.subject);
      setEditedBody(resp.body);
      setDiffLines(diff);
      setShowDiff(true);
      setRewriteCount(c => c + 1);

      const changed = countChangedLines(diff);
      toast.success(`Email rewritten — ${changed} line${changed !== 1 ? "s" : ""} changed · preview updated`);
    } catch (err: any) {
      toast.error("AI rewrite failed: " + (err.message || "unknown error"));
    } finally {
      setAiLoading(false);
    }
  };

  const confidence = hr_contact.confidence_score
    ? Math.round(hr_contact.confidence_score * 100)
    : null;

  const confidenceColor =
    confidence && confidence >= 80
      ? "text-emerald-600 bg-emerald-50 border-emerald-200"
      : confidence && confidence >= 50
      ? "text-amber-600 bg-amber-50 border-amber-200"
      : "text-slate-500 bg-slate-50 border-slate-200";

  if (cancelled) {
    return (
      <div className="mt-4 px-4 py-3 rounded-xl border border-slate-100 bg-slate-50 text-center">
        <p className="text-[12px] text-slate-500 font-sans">Email cancelled. Search for another job or regenerate.</p>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.1 }}
      className="mt-4 rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-slate-50 border-b border-slate-100">
        <div>
          <p className="text-[12px] font-semibold text-slate-800 font-sans">Application Email</p>
          <p className="text-[10px] text-slate-500 font-sans mt-0.5">
            {rewriteCount > 0 ? `Rewritten ${rewriteCount}x by AI · ` : ""}Ready to send — review before confirming
          </p>
        </div>
        <div className="flex items-center gap-1.5">
          {/* AI change badge — clickable to toggle diff */}
          {rewriteCount > 0 && (
            <motion.button
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              onClick={() => setShowDiff(v => !v)}
              className="flex items-center gap-1 px-2 py-1 rounded-full bg-green-50 border border-green-200 hover:bg-green-100 transition-colors"
            >
              <GitCompare size={9} className="text-green-600" />
              <span className="text-[9px] font-bold text-green-700">
                {changedLineCount} line{changedLineCount !== 1 ? "s" : ""} changed
              </span>
            </motion.button>
          )}
          <div className="flex items-center gap-1.5 px-2 py-1 rounded-full bg-blue-50 border border-blue-200">
            <div className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
            <span className="text-[10px] font-semibold text-blue-700 font-sans">Draft Ready</span>
          </div>
        </div>
      </div>

      {/* HR Contact row */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-slate-100 bg-slate-50/50">
        <div className="w-8 h-8 rounded-full bg-rose-100 flex items-center justify-center flex-shrink-0">
          <User size={14} className="text-rose-600" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-[12px] font-semibold text-slate-800 font-sans truncate">
            {hr_contact.name || "HR Team"}
          </p>
          <p className="text-[10px] text-slate-500 font-sans truncate">
            {hr_contact.email || "hr@company.com"} — {hr_contact.title || "Recruiter"}
          </p>
        </div>
        {confidence !== null && (
          <div className={`flex items-center gap-1 px-2 py-1 rounded-full border text-[10px] font-semibold ${confidenceColor}`}>
            <ShieldCheck size={10} />
            {confidence}% verified
          </div>
        )}
      </div>

      {/* ── Live Diff Panel ─────────────────────────────────────────────────── */}
      <AnimatePresence>
        {showDiff && diffLines.length > 0 && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.22 }}
            style={{ overflow: "hidden" }}
            className="border-b border-green-100 bg-green-50/30"
          >
            <div className="px-4 py-2.5">
              <div className="flex items-center justify-between mb-2">
                <p className="text-[9px] font-bold uppercase tracking-widest text-green-700 flex items-center gap-1">
                  <GitCompare size={9} /> What AI changed
                </p>
                <button onClick={() => setShowDiff(false)} className="text-slate-400 hover:text-slate-600">
                  <X size={11} />
                </button>
              </div>

              {/* Subject change */}
              {prevSubject !== null && prevSubject !== editedSubject && (
                <div className="mb-2 space-y-0.5">
                  <p className="text-[9px] font-semibold text-slate-500 uppercase tracking-wide">Subject</p>
                  <p className="text-[10px] bg-red-50 border border-red-100 rounded px-2 py-1 text-red-600 line-through">{prevSubject}</p>
                  <p className="text-[10px] bg-green-50 border border-green-200 rounded px-2 py-1 text-green-800 font-medium">{editedSubject}</p>
                </div>
              )}

              {/* Line diff for body */}
              <p className="text-[9px] font-semibold text-slate-500 uppercase tracking-wide mb-1">Body Changes</p>
              <ScrollArea className="max-h-36">
                <div className="font-mono text-[10px] space-y-0.5 pr-2">
                  {diffLines.filter(l => l.status !== "unchanged" || !l.text.trim()).map((line, i) => {
                    if (line.status === "removed") {
                      return (
                        <div key={i} className="flex gap-1.5 items-start bg-red-50 rounded px-1.5 py-0.5 border-l-2 border-red-300">
                          <span className="text-red-400 flex-shrink-0 font-bold text-[9px] mt-0.5">−</span>
                          <span className="text-red-600 line-through leading-relaxed">{line.text || " "}</span>
                        </div>
                      );
                    }
                    if (line.status === "added") {
                      return (
                        <div key={i} className="flex gap-1.5 items-start bg-green-50 rounded px-1.5 py-0.5 border-l-2 border-green-400">
                          <span className="text-green-500 flex-shrink-0 font-bold text-[9px] mt-0.5">+</span>
                          <span className="text-green-800 leading-relaxed">{line.text || " "}</span>
                        </div>
                      );
                    }
                    return null;
                  })}
                </div>
              </ScrollArea>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Email preview — live, reflects AI rewrites instantly */}
      <div className="px-4 py-3 border-b border-slate-100">
        {/* To / CC / Subject */}
        <div className="space-y-1 mb-3">
          <div className="flex gap-2 text-[11px]">
            <span className="text-slate-400 font-sans w-10 flex-shrink-0">To:</span>
            <span className="text-slate-700 font-sans font-medium">{hr_contact.email || "hr@company.com"}</span>
          </div>
          {email.cc && (
            <div className="flex gap-2 text-[11px]">
              <span className="text-slate-400 font-sans w-10 flex-shrink-0">CC:</span>
              <span className="text-slate-600 font-sans">{email.cc}</span>
            </div>
          )}
          <div className="flex gap-2 text-[11px] items-center">
            <span className="text-slate-400 font-sans w-10 flex-shrink-0">Subj:</span>
            <span className={`font-sans font-semibold transition-colors ${prevSubject !== null ? "text-green-800" : "text-slate-800"}`}>
              {editedSubject}
            </span>
            {prevSubject !== null && (
              <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-full bg-green-100 text-green-700 border border-green-200 text-[8px] font-bold uppercase tracking-wider">
                <Sparkles size={7} /> AI
              </span>
            )}
          </div>
        </div>

        {/* Body — diff-highlighted when AI has rewritten */}
        <ScrollArea className="h-36">
          {showDiff && diffLines.length > 0 ? (
            // Diff view: show all lines with color-coded status
            <div className="font-sans text-[11px] leading-relaxed space-y-0.5 pr-2">
              {diffLines.map((line, i) => {
                if (line.status === "added") {
                  return (
                    <div key={i} className="bg-green-50 border-l-2 border-green-400 pl-2 rounded-r text-green-800">
                      {line.text || <br />}
                    </div>
                  );
                }
                if (line.status === "removed") {
                  return (
                    <div key={i} className="bg-red-50 border-l-2 border-red-300 pl-2 rounded-r text-red-500 line-through opacity-60">
                      {line.text || <br />}
                    </div>
                  );
                }
                return (
                  <div key={i} className="text-slate-700 pl-2">
                    {line.text || <span className="block h-2" />}
                  </div>
                );
              })}
            </div>
          ) : (
            // Normal preview
            <pre className="text-[11px] text-slate-700 font-sans leading-relaxed whitespace-pre-wrap">
              {editedBody}
            </pre>
          )}
        </ScrollArea>

        {/* Toggle diff view */}
        {rewriteCount > 0 && (
          <button
            onClick={() => setShowDiff(v => !v)}
            className="mt-2 flex items-center gap-1 text-[9px] text-slate-400 hover:text-green-600 transition-colors font-sans"
          >
            <GitCompare size={10} />
            {showDiff ? "Hide diff" : `Show ${changedLineCount} changed lines`}
          </button>
        )}

        {/* Attachment pill */}
        {pdf_filename && (
          <div className="flex items-center gap-1.5 mt-2 px-2.5 py-1.5 bg-slate-100 rounded-lg w-fit">
            <Paperclip size={11} className="text-slate-500" />
            <span className="text-[10px] text-slate-600 font-sans">{pdf_filename}</span>
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="px-4 py-3 flex items-center gap-2">
        <Button
          size="sm"
          className="flex-1 h-9 text-[12px] font-semibold bg-rose-600 hover:bg-rose-700 text-white gap-1.5 font-sans"
          onClick={() => onSendAction(`__SEND_EMAIL__:${application_id}`)}
        >
          <Send size={12} />
          Send via Gmail
        </Button>
        <Button
          size="sm"
          variant="outline"
          className="h-9 text-[11px] font-sans border-slate-200 text-slate-600 hover:text-slate-900 gap-1.5"
          onClick={() => setEditOpen(true)}
        >
          <Edit3 size={11} />
          Edit
        </Button>
        <Button
          size="sm"
          variant="ghost"
          className="h-9 text-[11px] font-sans text-slate-400 hover:text-red-500 gap-1"
          onClick={() => {
            setCancelled(true);
            toast.info("Email cancelled.");
          }}
        >
          <X size={11} />
        </Button>
      </div>

      {/* ── Edit Dialog ──────────────────────────────────────────────────────── */}
      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent className="sm:max-w-[600px]">
          <DialogHeader>
            <DialogTitle className="font-sans text-sm flex items-center gap-2">
              Edit Application Email
              {rewriteCount > 0 && (
                <span className="flex items-center gap-1 px-2 py-0.5 bg-green-100 border border-green-200 rounded-full text-[9px] font-bold text-green-700">
                  <Sparkles size={8} /> AI rewritten ×{rewriteCount}
                </span>
              )}
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-3 py-2">
            <div>
              <label className="text-[11px] font-semibold text-slate-600 font-sans block mb-1 flex items-center gap-1.5">
                Subject
                {prevSubject !== null && (
                  <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-full bg-green-100 text-green-700 border border-green-200 text-[8px] font-bold">
                    <Sparkles size={7} /> AI
                  </span>
                )}
              </label>
              <input
                className={`w-full border rounded-lg px-3 py-2 text-sm font-sans outline-none focus:border-rose-300 transition-colors ${
                  prevSubject !== null ? "border-green-300 bg-green-50/30" : "border-slate-200"
                }`}
                value={editedSubject}
                onChange={(e) => setEditedSubject(e.target.value)}
              />
            </div>
            <div>
              <label className="text-[11px] font-semibold text-slate-600 font-sans block mb-1 flex items-center gap-1.5">
                Body
                {rewriteCount > 0 && (
                  <span className="text-[9px] text-green-600 font-normal">{changedLineCount} lines changed by AI</span>
                )}
              </label>
              <Textarea
                value={editedBody}
                onChange={(e) => setEditedBody(e.target.value)}
                className={`min-h-[240px] font-sans text-sm transition-colors ${
                  rewriteCount > 0 ? "border-green-300 bg-green-50/20" : ""
                }`}
              />
            </div>
          </div>

          {/* AI Chat Input */}
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15, duration: 0.3 }}
            className="border-t border-slate-100 pt-3"
          >
            <div className="flex items-center gap-1 mb-1.5">
              <Wand2 size={10} className="text-rose-500" />
              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                Ask AI to rewrite — changes apply live to preview
              </span>
            </div>
            <div className="flex items-center gap-2 bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 focus-within:border-rose-300 focus-within:ring-2 focus-within:ring-rose-50 transition-all">
              <Sparkles size={13} className={`flex-shrink-0 ${aiLoading ? "text-rose-400 animate-spin" : "text-slate-400"}`} />
              <input
                ref={aiInputRef}
                value={aiInstruction}
                onChange={e => setAiInstruction(e.target.value)}
                onKeyDown={e => e.key === "Enter" && handleAiRewrite()}
                placeholder="e.g. Make it shorter and more confident. Add urgency..."
                disabled={aiLoading}
                className="flex-1 bg-transparent text-xs text-slate-700 placeholder-slate-400 outline-none"
              />
              <button
                onClick={handleAiRewrite}
                disabled={!aiInstruction.trim() || aiLoading}
                className="w-6 h-6 rounded-lg bg-rose-600 hover:bg-rose-700 disabled:opacity-40 flex items-center justify-center transition-all flex-shrink-0"
              >
                {aiLoading ? <RefreshCw size={10} className="text-white animate-spin" /> : <Send size={10} className="text-white" />}
              </button>
            </div>
          </motion.div>

          <DialogFooter>
            <Button
              size="sm"
              className="bg-rose-600 hover:bg-rose-700 text-white font-sans text-sm"
              onClick={() => {
                toast.success("Email updated");
                setEditOpen(false);
              }}
            >
              Save Changes
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </motion.div>
  );
}
