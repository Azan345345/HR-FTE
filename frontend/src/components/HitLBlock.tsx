import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Mail, Edit3, CheckCircle, ChevronDown, ChevronUp, FileText, Send, Loader2 } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import { motion, AnimatePresence } from "framer-motion";
import { useAgentStore, AgentName } from "@/stores/agent-store";
import { approveApplication } from "@/services/api";

// Fallback dummy data removed to use real state

export function HitLBlock({
  agentName,
  onApprove,
  onEdit
}: {
  agentName: AgentName;
  onApprove?: (company: string) => void;
  onEdit?: (type: string, content: string) => void;
}) {
  const { agents, setAgentStatus } = useAgentStore();
  const agentInfo = agents[agentName];
  const drafts = agentInfo?.drafts;

  const [cvExpanded, setCvExpanded] = useState(true);
  const [approved, setApproved] = useState(false);
  const [cvText, setCvText] = useState(JSON.stringify(drafts?.cv || {}, null, 2));
  const [clText, setClText] = useState(drafts?.cover_letter || "");
  const [emailText, setEmailText] = useState(drafts?.email || "");

  const [isEditingCV, setIsEditingCV] = useState(false);
  const [isEditingCL, setIsEditingCL] = useState(false);
  const [isEditingEmail, setIsEditingEmail] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);

  // Sync state if drafts change
  useEffect(() => {
    if (drafts) {
      setCvText(JSON.stringify(drafts.cv || {}, null, 2));
      setClText(drafts.cover_letter || "");
      setEmailText(drafts.email || "");
    }
  }, [drafts]);

  const handleSaveCV = () => {
    try {
      const parsed = JSON.parse(cvText);
      // Instead of just updating local store, send edit to backend
      onEdit?.("CV", cvText);
      useAgentStore.getState().setAgentDrafts(agentName, { ...drafts, cv: parsed });
      toast.success("CV Edit Sent to Agent");
      setIsEditingCV(false);
    } catch (e) {
      toast.error("Invalid JSON format");
    }
  };

  const handleSaveCL = () => {
    onEdit?.("Cover Letter", clText);
    useAgentStore.getState().setAgentDrafts(agentName, { ...drafts, cover_letter: clText });
    toast.success("Cover Letter Edit Sent to Agent");
    setIsEditingCL(false);
  };

  const handleSaveEmail = () => {
    onEdit?.("Email", emailText);
    useAgentStore.getState().setAgentDrafts(agentName, { ...drafts, email: emailText });
    toast.success("Email Edit Sent to Agent");
    setIsEditingEmail(false);
  };

  const handleApprove = async () => {
    if (!drafts?.application_id) {
      toast.error("No application context found");
      return;
    }

    setIsProcessing(true);
    try {
      await approveApplication(drafts.application_id, "Application Draft", emailText);
      setApproved(true);
      setAgentStatus(agentName, { status: "completed" });
      toast.success("Application approved and sent!");
      onApprove?.("Current Job"); // We can pass real company if known
    } catch (err: any) {
      toast.error(err.message || "Failed to approve application");
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <motion.div
      className="rounded-2xl border border-border bg-card shadow-elevated overflow-hidden"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.6, duration: 0.5 }}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-border bg-secondary/40">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
            <FileText size={15} className="text-primary" />
          </div>
          <div>
            <p className="text-sm font-semibold text-foreground font-sans">
              Review: Multi-Agent Application Draft
            </p>
            <p className="text-[11px] text-muted-foreground font-sans">
              Tailored CV + Cover Letter for current job
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-amber-50 border border-amber-200">
          <div className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
          <span className="text-[10px] font-semibold text-amber-700 font-sans">Awaiting Review</span>
        </div>
      </div>

      {/* CV Section */}
      <div className="border-b border-border">
        <button
          onClick={() => setCvExpanded(!cvExpanded)}
          className="w-full flex items-center justify-between px-5 py-3 hover:bg-secondary/30 transition-colors"
        >
          <span className="text-xs font-semibold text-foreground font-sans flex items-center gap-2">
            <span className="w-5 h-5 rounded bg-primary/10 inline-flex items-center justify-center text-primary text-[10px] font-bold">CV</span>
            Tailored Curriculum Vitae — Google_CV_Tailored.pdf
          </span>
          {cvExpanded ? <ChevronUp size={14} className="text-muted-foreground" /> : <ChevronDown size={14} className="text-muted-foreground" />}

          <Dialog open={isEditingCV} onOpenChange={setIsEditingCV}>
            <DialogTrigger asChild>
              <Button variant="ghost" size="icon" className="h-6 w-6 ml-auto mr-2" onClick={(e) => e.stopPropagation()}>
                <Edit3 size={12} className="text-muted-foreground" />
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[700px]">
              <DialogHeader>
                <DialogTitle>Edit Tailored CV JSON</DialogTitle>
              </DialogHeader>
              <div className="grid gap-4 py-4">
                <Textarea
                  value={cvText}
                  onChange={(e) => setCvText(e.target.value)}
                  className="min-h-[400px] font-mono text-xs"
                />
              </div>
              <DialogFooter>
                <Button onClick={handleSaveCV}>Save Changes</Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </button>

        <AnimatePresence>
          {cvExpanded && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.3 }}
              style={{ overflow: "hidden" }}
            >
              <ScrollArea className="h-64">
                <div className="px-5 pb-5 font-sans text-[11px] leading-relaxed text-foreground space-y-4">
                  {/* Name & Contact */}
                  <div className="border-b border-border pb-3">
                    <h2 className="font-serif text-base font-bold text-foreground">{drafts?.cv?.name || "Candidate Name"}</h2>
                    <p className="text-[10px] text-muted-foreground mt-0.5">{drafts?.cv?.contact || "Email · Phone · Location"}</p>
                  </div>

                  {/* Summary */}
                  <div>
                    <p className="text-[9px] font-bold uppercase tracking-widest text-muted-foreground mb-1.5">Professional Summary</p>
                    <p className="text-[11px] text-foreground leading-relaxed">{drafts?.cv?.summary || "No summary provided"}</p>
                  </div>

                  {/* Experience */}
                  <div>
                    <p className="text-[9px] font-bold uppercase tracking-widest text-muted-foreground mb-2">Experience</p>
                    <div className="space-y-3">
                      {(drafts?.cv?.experience || []).map((exp: any, idx: number) => (
                        <div key={idx}>
                          <div className="flex items-baseline justify-between">
                            <p className="text-[11px] font-semibold text-foreground">{exp.role} — {exp.company}</p>
                            <span className="text-[10px] text-muted-foreground ml-2 flex-shrink-0">{exp.period}</span>
                          </div>
                          <ul className="mt-1 space-y-0.5 pl-3">
                            {(exp.bullets || []).map((b: string, i: number) => (
                              <li key={i} className="text-[10px] text-muted-foreground leading-relaxed before:content-['·'] before:mr-1.5 before:text-primary">
                                {b}
                              </li>
                            ))}
                          </ul>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Skills */}
                  <div>
                    <p className="text-[9px] font-bold uppercase tracking-widest text-muted-foreground mb-1.5">Technical Skills</p>
                    <p className="text-[11px] text-foreground">{drafts?.cv?.skills || ""}</p>
                  </div>

                  {/* Education */}
                  <div>
                    <p className="text-[9px] font-bold uppercase tracking-widest text-muted-foreground mb-1.5">Education</p>
                    <p className="text-[11px] text-foreground">{drafts?.cv?.education || "Degree information"}</p>
                  </div>
                </div>
              </ScrollArea>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Cover Letter */}
      <div className="border-b border-border">
        <div className="px-5 py-3 flex items-center gap-2 border-b border-border/50">
          <span className="w-5 h-5 rounded bg-blue-50 inline-flex items-center justify-center text-blue-500 text-[10px] font-bold">CL</span>
          <span className="text-xs font-semibold text-foreground font-sans">Cover Letter Preview</span>

          <Dialog open={isEditingCL} onOpenChange={setIsEditingCL}>
            <DialogTrigger asChild>
              <Button variant="ghost" size="icon" className="h-6 w-6 ml-auto">
                <Edit3 size={12} className="text-muted-foreground" />
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[600px]">
              <DialogHeader>
                <DialogTitle>Edit Cover Letter</DialogTitle>
              </DialogHeader>
              <div className="grid gap-4 py-4">
                <Textarea
                  value={clText}
                  onChange={(e) => setClText(e.target.value)}
                  className="min-h-[300px] font-sans text-sm"
                />
              </div>
              <DialogFooter>
                <Button onClick={handleSaveCL}>Save Cover Letter</Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
        <ScrollArea className="h-36">
          <div className="px-5 py-3 font-sans">
            <pre className="text-[11px] text-muted-foreground leading-relaxed whitespace-pre-wrap font-sans">
              {clText}
            </pre>
          </div>
        </ScrollArea>
      </div>

      {/* Actions */}
      <div className="px-5 py-4 flex items-center gap-3">
        <AnimatePresence mode="wait">
          {!approved ? (
            <motion.div
              key="actions"
              className="flex items-center gap-3 w-full"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <motion.div className="flex-1" whileHover={{ scale: 1.01 }}>
                <Button
                  className="w-full gap-2 bg-primary hover:bg-primary/90 text-primary-foreground text-sm font-semibold shadow-rose animate-shimmer-pulse font-sans disabled:opacity-50"
                  onClick={handleApprove}
                  disabled={isProcessing}
                >
                  {isProcessing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Mail size={15} />}
                  Approve & Send Application
                </Button>
              </motion.div>
              <Dialog open={isEditingEmail} onOpenChange={setIsEditingEmail}>
                <DialogTrigger asChild>
                  <motion.div whileHover={{ scale: 1.01 }}>
                    <Button
                      variant="outline"
                      size="sm"
                      className="gap-1.5 text-xs border-border text-muted-foreground hover:text-foreground font-sans"
                    >
                      <Edit3 size={13} />
                      Edit Email
                    </Button>
                  </motion.div>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Edit Application Email</DialogTitle>
                  </DialogHeader>
                  <div className="grid gap-4 py-4">
                    <Textarea
                      value={emailText}
                      onChange={(e) => setEmailText(e.target.value)}
                      className="min-h-[200px] font-sans text-sm"
                    />
                  </div>
                  <DialogFooter>
                    <Button onClick={handleSaveEmail}>Save Email</Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            </motion.div>
          ) : (
            <motion.div
              key="confirmed"
              className="flex items-center gap-2 w-full justify-center py-1"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
            >
              <CheckCircle size={16} className="text-emerald-500" />
              <span className="text-sm font-semibold text-emerald-600 font-sans">
                Application approved and sent successfully!
              </span>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}
