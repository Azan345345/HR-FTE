import { useState, useRef, useEffect } from "react";
import {
  CheckCircle, RefreshCw, Edit3, ChevronDown, ChevronUp,
  Target, Zap, Save, Plus, Trash2, X, AlertTriangle,
  TrendingUp, Award, Lightbulb, BarChart3, Brain,
  Send, Sparkles, Wand2, GitCompare,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "sonner";
import { updateTailoredCV, aiRewriteCVSection } from "@/services/api";

// ── Types ──────────────────────────────────────────────────────────────────────

interface ExperienceEntry {
  company: string;
  role: string;
  duration: string;
  location?: string;
  achievements: string[];
}

interface CertificationEntry {
  name: string;
  issuer: string;
  date: string;
  expiry?: string;
  credential_id?: string;
}

interface TailoredCVPreview {
  name?: string;
  contact?: string;
  summary?: string;
  experience?: ExperienceEntry[];
  skills?: string;
  skills_raw?: Record<string, string[]>;
  education?: any[];
  certifications?: any[];
  projects?: any[];
}

interface CVReviewMeta {
  type: "cv_review";
  application_id: string;
  tailored_cv_id?: string;
  job_id?: string;
  auto_open_edit?: boolean;
  job: { id?: string; title: string; company: string; location?: string };
  tailored_cv: TailoredCVPreview;
  ats_score?: number;
  match_score?: number;
  keywords_matched?: number;
  keywords_total?: number;
  changes_made?: string[];
  cover_letter?: string;
  industry?: string;
  skills_analysis?: {
    matched_skills?: string[];
    missing_skills?: string[];
    nice_to_have_skills?: string[];
  };
  writing_quality?: {
    passive_voice_instances?: { original: string; active_version: string; location: string }[];
    weak_phrases?: { weak_phrase: string; stronger_alternative: string; reason: string }[];
    action_verbs?: { weak_verbs_used?: string[]; recommended_power_verbs?: string[] };
  };
  red_flags?: { issue: string; severity: "low" | "medium" | "high"; recommendation: string }[];
  overall_feedback?: { strengths?: string[]; weaknesses?: string[]; quick_wins?: string[] };
  score_breakdown?: { skills_score?: number; experience_score?: number; education_score?: number; projects_score?: number };
}

interface Props {
  metadata: CVReviewMeta;
  onSendAction: (action: string) => void;
}

// ── AI change tracking ─────────────────────────────────────────────────────────
interface AiChanges {
  fields: Set<string>;        // 'summary' | 'cover' | 'skills' | 'experience' | 'certifications'
  addedSkills: Set<string>;   // skill strings added by AI
  addedBullets: Set<string>;  // bullet strings added by AI
  addedCerts: Set<string>;    // cert names added by AI
  prevSummary: string;
  prevCover: string;
  count: number;
}

// ── Diff helpers ───────────────────────────────────────────────────────────────
function parseBulletsFromText(text: string): string[] {
  return text
    .split("\n")
    .map((l) => l.replace(/^[\s]*[•\-\*\d\.]+[\s]*/u, "").trim())
    .filter((l) => l.length > 15);
}

// ── Score Pill ─────────────────────────────────────────────────────────────────
function ScorePill({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full border ${color}`}>
      <span className="text-[11px] font-medium font-sans">{label}</span>
      <span className="text-[13px] font-bold font-sans">{value}%</span>
    </div>
  );
}

// ── Score Bar ──────────────────────────────────────────────────────────────────
function MiniScoreBar({ label, value, max, color }: { label: string; value: number; max: number; color: string }) {
  const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0;
  return (
    <div className="flex items-center gap-2">
      <span className="text-[10px] text-slate-500 w-20 flex-shrink-0 font-sans">{label}</span>
      <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-[10px] font-semibold text-slate-600 w-10 text-right font-sans">{value}/{max}</span>
    </div>
  );
}

// ── Severity badge ─────────────────────────────────────────────────────────────
const SEVERITY_STYLE: Record<string, string> = {
  high: "bg-red-50 text-red-700 border-red-200",
  medium: "bg-amber-50 text-amber-700 border-amber-200",
  low: "bg-slate-50 text-slate-600 border-slate-200",
};

// ── AI Changed Badge ───────────────────────────────────────────────────────────
function AiBadge({ label = "AI" }: { label?: string }) {
  return (
    <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-full bg-green-100 text-green-700 border border-green-200 text-[8px] font-bold uppercase tracking-wider flex-shrink-0">
      <Sparkles size={7} />
      {label}
    </span>
  );
}

// ── Main Component ─────────────────────────────────────────────────────────────

export function CVReviewCard({ metadata, onSendAction }: Props) {
  const {
    application_id, tailored_cv_id, job_id, job,
    tailored_cv, ats_score = 0, match_score = 0,
    keywords_matched = 0, keywords_total = 0,
    changes_made = [], cover_letter = "",
    industry, skills_analysis, writing_quality, red_flags = [],
    overall_feedback, score_breakdown,
  } = metadata;

  const [cvExpanded, setCvExpanded] = useState(true);
  const [changesExpanded, setChangesExpanded] = useState(false);
  const [analysisExpanded, setAnalysisExpanded] = useState(false);
  const [diffExpanded, setDiffExpanded] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [saving, setSaving] = useState(false);

  const [editedSummary, setEditedSummary] = useState(tailored_cv.summary || "");
  const [editedExperience, setEditedExperience] = useState<ExperienceEntry[]>(
    tailored_cv.experience?.map(e => ({
      ...e,
      achievements: Array.isArray(e.achievements) ? [...e.achievements] : [],
    })) || []
  );
  const [editedSkillsRaw, setEditedSkillsRaw] = useState<Record<string, string[]>>(
    (() => {
      const raw = tailored_cv.skills_raw || {};
      const filtered: Record<string, string[]> = {};
      for (const [k, v] of Object.entries(raw)) {
        if (!k.startsWith("_") && k !== "all") filtered[k] = v;
      }
      if (Object.keys(filtered).length === 0) {
        filtered.technical = (tailored_cv.skills || "").split(",").map(s => s.trim()).filter(Boolean);
        filtered.soft = [];
        filtered.tools = [];
      }
      return filtered;
    })()
  );
  const [editedCoverLetter, setEditedCoverLetter] = useState(cover_letter);
  const [editedCertifications, setEditedCertifications] = useState<CertificationEntry[]>(
    (tailored_cv.certifications || []).map((c: any) => ({
      name: c.name || c.title || "",
      issuer: c.issuer || c.organization || c.issued_by || "",
      date: c.date || c.year || c.obtained || "",
      expiry: c.expiry || c.expires || "",
      credential_id: c.credential_id || c.id || "",
    }))
  );
  const [activeEditTab, setActiveEditTab] = useState<"summary" | "experience" | "skills" | "certifications" | "cover">("summary");
  const [aiInstruction, setAiInstruction] = useState("");
  const [aiLoading, setAiLoading] = useState(false);
  const aiInputRef = useRef<HTMLInputElement>(null);

  // ── Auto-open edit dialog when triggered from "Edit in Modal" button ──────
  useEffect(() => {
    if (metadata.auto_open_edit) setEditOpen(true);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // ── AI change tracking ─────────────────────────────────────────────────────
  const [aiChanges, setAiChanges] = useState<AiChanges>({
    fields: new Set(),
    addedSkills: new Set(),
    addedBullets: new Set(),
    addedCerts: new Set(),
    prevSummary: tailored_cv.summary || "",
    prevCover: cover_letter,
    count: 0,
  });

  // ── Save edits ───────────────────────────────────────────────────────────────
  const handleSaveEdits = async () => {
    const edits = {
      summary: editedSummary,
      experience: editedExperience,
      skills: editedSkillsRaw,
      cover_letter: editedCoverLetter,
      certifications: editedCertifications,
    };
    if (!tailored_cv_id) {
      onSendAction(`__EDIT_CV__:${tailored_cv_id || application_id}:${JSON.stringify(edits)}`);
      toast.success("CV changes saved!");
      setEditOpen(false);
      return;
    }
    setSaving(true);
    try {
      await updateTailoredCV(tailored_cv_id, edits);
      toast.success("CV edits saved successfully!");
      setEditOpen(false);
    } catch (err: any) {
      toast.error(`Failed to save: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  // ── AI rewrite — applies changes immediately to preview ─────────────────────
  const handleAiRewrite = async () => {
    if (!aiInstruction.trim() || aiLoading) return;
    setAiLoading(true);
    const instruction = aiInstruction.trim();
    setAiInstruction("");

    try {
      const sectionMap: Record<string, string> = {
        summary: "summary",
        cover: "cover_letter",
        skills: "skills",
        experience: "experience",
        certifications: "certifications",
      };
      const section = sectionMap[activeEditTab] || activeEditTab;

      let currentContent = "";
      if (activeEditTab === "summary") currentContent = editedSummary;
      else if (activeEditTab === "cover") currentContent = editedCoverLetter;
      else if (activeEditTab === "skills")
        currentContent = Object.entries(editedSkillsRaw).map(([k, v]) => `${k}: ${v.join(", ")}`).join("\n");
      else if (activeEditTab === "experience")
        currentContent = editedExperience.map(e => `${e.role} at ${e.company}:\n${e.achievements.map(a => `• ${a}`).join("\n")}`).join("\n\n");
      else if (activeEditTab === "certifications")
        currentContent = editedCertifications.map(c => `${c.name} | ${c.issuer} | ${c.date}`).join("\n");

      const resp = await aiRewriteCVSection({
        section,
        content: currentContent,
        instruction,
        job_title: job.title,
        job_company: job.company,
      });

      if (activeEditTab === "summary") {
        // Track the change, apply immediately to preview
        setAiChanges(prev => ({
          ...prev,
          fields: new Set([...prev.fields, "summary"]),
          prevSummary: editedSummary,
          count: prev.count + 1,
        }));
        setEditedSummary(resp.content);
        setDiffExpanded(true);
        toast.success("Summary rewritten — preview updated live");

      } else if (activeEditTab === "cover") {
        setAiChanges(prev => ({
          ...prev,
          fields: new Set([...prev.fields, "cover"]),
          prevCover: editedCoverLetter,
          count: prev.count + 1,
        }));
        setEditedCoverLetter(resp.content);
        setDiffExpanded(true);
        toast.success("Cover letter rewritten — preview updated live");

      } else if (activeEditTab === "skills") {
        // Parse new skills list and identify which ones are net-new
        const newSkillList = resp.content.split(",").map(s => s.trim()).filter(Boolean);
        const existingSet = new Set(
          Object.values(editedSkillsRaw).flat().map(s => s.toLowerCase())
        );
        const addedSkills = newSkillList.filter(s => !existingSet.has(s.toLowerCase()));

        setEditedSkillsRaw(prev => ({ ...prev, technical: newSkillList }));
        setAiChanges(prev => ({
          ...prev,
          fields: new Set([...prev.fields, "skills"]),
          addedSkills: new Set([...prev.addedSkills, ...addedSkills]),
          count: prev.count + addedSkills.length,
        }));
        setDiffExpanded(true);
        toast.success(`Skills updated — ${addedSkills.length} new skill(s) added`);

      } else if (activeEditTab === "experience") {
        // Parse bullet points from AI response and apply to ALL experience entries
        const bullets = parseBulletsFromText(resp.content);

        if (bullets.length > 0) {
          // Distribute bullets across experience entries (most to first/most recent)
          const perEntry = Math.ceil(bullets.length / Math.max(editedExperience.length, 1));
          setEditedExperience(prev =>
            prev.map((exp, idx) => {
              const slice = bullets.slice(idx * perEntry, (idx + 1) * perEntry);
              return slice.length > 0
                ? { ...exp, achievements: [...exp.achievements, ...slice] }
                : exp;
            })
          );
          setAiChanges(prev => ({
            ...prev,
            fields: new Set([...prev.fields, "experience"]),
            addedBullets: new Set([...prev.addedBullets, ...bullets]),
            count: prev.count + bullets.length,
          }));
          setDiffExpanded(true);
          toast.success(`${bullets.length} AI bullets applied to experience — visible in preview`);
        } else {
          toast.info("AI suggestion (apply manually): " + resp.content.slice(0, 120));
        }

      } else if (activeEditTab === "certifications") {
        // Parse "Name | Issuer | Date" lines or JSON from AI response
        const existingNames = new Set(editedCertifications.map(c => c.name.toLowerCase()));
        let parsed: CertificationEntry[] = [];

        // Try JSON first
        try {
          const json = JSON.parse(resp.content.replace(/```json|```/g, "").trim());
          const arr = Array.isArray(json) ? json : [json];
          parsed = arr.map((c: any) => ({
            name: c.name || c.title || "",
            issuer: c.issuer || c.organization || c.issued_by || "",
            date: c.date || c.year || "",
            expiry: c.expiry || "",
            credential_id: c.credential_id || "",
          })).filter((c: CertificationEntry) => c.name);
        } catch {
          // Fallback: parse "Name | Issuer | Date" text lines
          parsed = resp.content
            .split("\n")
            .map(l => l.replace(/^[\s\-\*•]+/, "").trim())
            .filter(l => l.length > 3)
            .map(l => {
              const parts = l.split("|").map(p => p.trim());
              return { name: parts[0] || l, issuer: parts[1] || "", date: parts[2] || "" };
            })
            .filter(c => c.name);
        }

        if (parsed.length > 0) {
          const newNames = parsed.filter(c => !existingNames.has(c.name.toLowerCase())).map(c => c.name);
          setEditedCertifications(prev => {
            // Update existing certs and append new ones
            const updated = [...prev];
            for (const cert of parsed) {
              const idx = updated.findIndex(c => c.name.toLowerCase() === cert.name.toLowerCase());
              if (idx >= 0) updated[idx] = { ...updated[idx], ...cert };
              else updated.push(cert);
            }
            return updated;
          });
          setAiChanges(prev => ({
            ...prev,
            fields: new Set([...prev.fields, "certifications"]),
            addedCerts: new Set([...prev.addedCerts, ...newNames]),
            count: prev.count + newNames.length,
          }));
          setDiffExpanded(true);
          toast.success(`${parsed.length} certification(s) updated — ${newNames.length} new`);
        } else {
          toast.info("AI suggestion: " + resp.content.slice(0, 120));
        }
      }
    } catch (err: any) {
      toast.error("AI rewrite failed: " + (err.message || "unknown error"));
    } finally {
      setAiLoading(false);
    }
  };

  const updateBullet = (expIdx: number, bulletIdx: number, value: string) =>
    setEditedExperience(prev => prev.map((e, i) => i === expIdx ? { ...e, achievements: e.achievements.map((a, j) => j === bulletIdx ? value : a) } : e));
  const addBullet = (expIdx: number) =>
    setEditedExperience(prev => prev.map((e, i) => i === expIdx ? { ...e, achievements: [...e.achievements, ""] } : e));
  const removeBullet = (expIdx: number, bulletIdx: number) =>
    setEditedExperience(prev => prev.map((e, i) => i === expIdx ? { ...e, achievements: e.achievements.filter((_, j) => j !== bulletIdx) } : e));
  const updateSkillCategory = (category: string, value: string) =>
    setEditedSkillsRaw(prev => ({ ...prev, [category]: value.split(",").map(s => s.trim()).filter(Boolean) }));

  const addCert = () =>
    setEditedCertifications(prev => [...prev, { name: "", issuer: "", date: "", expiry: "", credential_id: "" }]);
  const removeCert = (idx: number) =>
    setEditedCertifications(prev => prev.filter((_, i) => i !== idx));
  const updateCert = (idx: number, field: keyof CertificationEntry, value: string) =>
    setEditedCertifications(prev => prev.map((c, i) => i === idx ? { ...c, [field]: value } : c));

  const highFlags = red_flags.filter(f => f.severity === "high");
  const hasAiChanges = aiChanges.count > 0;

  // ── Render ───────────────────────────────────────────────────────────────────
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
          <p className="text-[12px] font-semibold text-slate-800 font-sans">
            Tailored CV — {job.title} at {job.company}
          </p>
          <p className="text-[10px] text-slate-500 font-sans mt-0.5">
            {industry ? `Industry: ${industry} · ` : ""}Edit sections or approve to generate PDF
          </p>
        </div>
        <div className="flex items-center gap-1.5">
          {hasAiChanges && (
            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              className="flex items-center gap-1 px-2 py-1 rounded-full bg-green-50 border border-green-200 cursor-pointer"
              onClick={() => setDiffExpanded(v => !v)}
            >
              <GitCompare size={9} className="text-green-600" />
              <span className="text-[9px] font-bold text-green-700">
                {aiChanges.count} AI change{aiChanges.count > 1 ? "s" : ""}
              </span>
            </motion.div>
          )}
          {highFlags.length > 0 && (
            <div className="flex items-center gap-1 px-2 py-1 rounded-full bg-red-50 border border-red-200">
              <AlertTriangle size={9} className="text-red-500" />
              <span className="text-[9px] font-bold text-red-600">{highFlags.length} flag{highFlags.length > 1 ? "s" : ""}</span>
            </div>
          )}
          <div className="flex items-center gap-1.5 px-2 py-1 rounded-full bg-amber-50 border border-amber-200">
            <div className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
            <span className="text-[10px] font-semibold text-amber-700 font-sans">Awaiting Review</span>
          </div>
        </div>
      </div>

      {/* Score bar — hidden for general CV edits (no job context) */}
      {job.id !== "" && (
        <>
          <div className="flex items-center gap-2 px-4 py-2.5 border-b border-slate-100 flex-wrap">
            <ScorePill label="ATS" value={Math.round(ats_score)} color="bg-emerald-50 border-emerald-200 text-emerald-700" />
            <ScorePill label="Match" value={Math.round(match_score)} color="bg-rose-50 border-rose-200 text-rose-700" />
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full border bg-blue-50 border-blue-200 text-blue-700">
              <Target size={11} />
              <span className="text-[11px] font-medium font-sans">{keywords_matched}/{keywords_total} keywords</span>
            </div>
          </div>

          {/* Score breakdown */}
          {score_breakdown && Object.keys(score_breakdown).length > 0 && (
            <div className="px-4 py-3 border-b border-slate-100 space-y-1.5">
              <p className="text-[9px] font-bold uppercase tracking-widest text-slate-400 mb-2 font-sans flex items-center gap-1">
                <BarChart3 size={9} /> Score Breakdown
              </p>
              <MiniScoreBar label="Skills" value={score_breakdown.skills_score || 0} max={35} color="bg-violet-400" />
              <MiniScoreBar label="Experience" value={score_breakdown.experience_score || 0} max={25} color="bg-blue-400" />
              <MiniScoreBar label="Education" value={score_breakdown.education_score || 0} max={15} color="bg-emerald-400" />
              <MiniScoreBar label="Projects" value={score_breakdown.projects_score || 0} max={15} color="bg-amber-400" />
            </div>
          )}
        </>
      )}

      {/* ── Live AI Diff Panel ───────────────────────────────────────────────── */}
      <AnimatePresence>
        {hasAiChanges && diffExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.22 }}
            style={{ overflow: "hidden" }}
            className="border-b border-green-100 bg-green-50/40"
          >
            <div className="px-4 py-3 space-y-3">
              <div className="flex items-center justify-between">
                <p className="text-[9px] font-bold uppercase tracking-widest text-green-700 flex items-center gap-1">
                  <GitCompare size={9} /> What AI changed
                </p>
                <button onClick={() => setDiffExpanded(false)} className="text-slate-400 hover:text-slate-600">
                  <X size={11} />
                </button>
              </div>

              {/* Summary diff */}
              {aiChanges.fields.has("summary") && (
                <div className="space-y-1">
                  <p className="text-[9px] font-semibold text-slate-500 uppercase tracking-wide">Summary</p>
                  <div className="text-[10px] bg-red-50 border border-red-100 rounded-lg px-2.5 py-1.5 text-red-600 line-through leading-relaxed">
                    {aiChanges.prevSummary.slice(0, 160)}{aiChanges.prevSummary.length > 160 ? "…" : ""}
                  </div>
                  <div className="text-[10px] bg-green-50 border border-green-200 rounded-lg px-2.5 py-1.5 text-green-800 leading-relaxed">
                    {editedSummary.slice(0, 160)}{editedSummary.length > 160 ? "…" : ""}
                  </div>
                </div>
              )}

              {/* Cover diff */}
              {aiChanges.fields.has("cover") && (
                <div className="space-y-1">
                  <p className="text-[9px] font-semibold text-slate-500 uppercase tracking-wide">Cover Letter</p>
                  <div className="text-[10px] bg-red-50 border border-red-100 rounded-lg px-2.5 py-1.5 text-red-600 line-through leading-relaxed line-clamp-2">
                    {aiChanges.prevCover.slice(0, 140)}…
                  </div>
                  <div className="text-[10px] bg-green-50 border border-green-200 rounded-lg px-2.5 py-1.5 text-green-800 leading-relaxed line-clamp-2">
                    {editedCoverLetter.slice(0, 140)}…
                  </div>
                </div>
              )}

              {/* New skills */}
              {aiChanges.addedSkills.size > 0 && (
                <div className="space-y-1">
                  <p className="text-[9px] font-semibold text-slate-500 uppercase tracking-wide">
                    Skills Added ({aiChanges.addedSkills.size})
                  </p>
                  <div className="flex flex-wrap gap-1">
                    {[...aiChanges.addedSkills].map((s, i) => (
                      <span key={i} className="px-2 py-0.5 bg-green-100 text-green-800 border border-green-300 rounded-full text-[9px] font-semibold">
                        + {s}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* New experience bullets */}
              {aiChanges.addedBullets.size > 0 && (
                <div className="space-y-1">
                  <p className="text-[9px] font-semibold text-slate-500 uppercase tracking-wide">
                    Experience Bullets Added ({aiChanges.addedBullets.size})
                  </p>
                  {[...aiChanges.addedBullets].slice(0, 3).map((b, i) => (
                    <p key={i} className="text-[10px] text-green-800 bg-green-50 border border-green-100 rounded-lg px-2.5 py-1.5 flex items-start gap-1.5">
                      <span className="text-green-500 flex-shrink-0 font-bold">+</span> {b}
                    </p>
                  ))}
                  {aiChanges.addedBullets.size > 3 && (
                    <p className="text-[9px] text-slate-400">+{aiChanges.addedBullets.size - 3} more bullets in Experience tab</p>
                  )}
                </div>
              )}

              {/* New certifications */}
              {aiChanges.addedCerts.size > 0 && (
                <div className="space-y-1">
                  <p className="text-[9px] font-semibold text-slate-500 uppercase tracking-wide">
                    Certifications Added ({aiChanges.addedCerts.size})
                  </p>
                  <div className="flex flex-wrap gap-1">
                    {[...aiChanges.addedCerts].map((c, i) => (
                      <span key={i} className="px-2 py-0.5 bg-amber-50 text-amber-800 border border-amber-200 rounded-full text-[9px] font-semibold">
                        + {c}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── CV Preview (live — reflects all edits instantly) ──────────────────── */}
      <div className="border-b border-slate-100">
        <button onClick={() => setCvExpanded(!cvExpanded)} className="w-full flex items-center justify-between px-4 py-2.5 hover:bg-slate-50 transition-colors">
          <span className="text-[11px] font-semibold text-slate-700 font-sans flex items-center gap-2">
            <span className="w-5 h-5 rounded bg-rose-100 inline-flex items-center justify-center text-rose-600 text-[9px] font-bold">CV</span>
            CV Preview
            {hasAiChanges && <span className="text-[9px] text-green-600 font-normal">· live</span>}
          </span>
          {cvExpanded ? <ChevronUp size={13} className="text-slate-400" /> : <ChevronDown size={13} className="text-slate-400" />}
        </button>
        <AnimatePresence>
          {cvExpanded && (
            <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.25 }} style={{ overflow: "hidden" }}>
              <ScrollArea className="h-64">
                <div className="px-4 pb-4 space-y-3 font-sans text-[11px]">
                  {/* Name / contact */}
                  <div className="pt-2 pb-2 border-b border-slate-100">
                    <p className="text-[14px] font-bold text-slate-900">{tailored_cv.name || "Candidate"}</p>
                    <p className="text-[10px] text-slate-500 mt-0.5">{tailored_cv.contact || ""}</p>
                  </div>

                  {/* Summary — green highlight when AI edited */}
                  {editedSummary && (
                    <div className={`transition-all duration-300 ${aiChanges.fields.has("summary") ? "border-l-2 border-green-400 pl-2 bg-green-50/30 rounded-r-lg py-1" : ""}`}>
                      <p className="text-[9px] font-bold uppercase tracking-widest text-slate-400 mb-1 flex items-center gap-1.5">
                        Summary {aiChanges.fields.has("summary") && <AiBadge />}
                      </p>
                      <p className="text-[11px] text-slate-700 leading-relaxed line-clamp-4">{editedSummary}</p>
                    </div>
                  )}

                  {/* Skills — AI-added chips highlighted green */}
                  {(tailored_cv.skills || Object.keys(editedSkillsRaw).length > 0) && (
                    <div className={`transition-all duration-300 ${aiChanges.fields.has("skills") ? "border-l-2 border-green-400 pl-2 bg-green-50/30 rounded-r-lg py-1" : ""}`}>
                      <p className="text-[9px] font-bold uppercase tracking-widest text-slate-400 mb-1 flex items-center gap-1.5">
                        Skills {aiChanges.fields.has("skills") && <AiBadge />}
                      </p>
                      <div className="flex flex-wrap gap-1">
                        {Object.entries(editedSkillsRaw).flatMap(([, v]) => v).slice(0, 16).map((s, i) => {
                          const isNew = aiChanges.addedSkills.has(s);
                          return (
                            <span
                              key={i}
                              className={`inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] transition-colors ${
                                isNew
                                  ? "bg-green-100 text-green-800 border border-green-300 font-semibold"
                                  : "bg-slate-100 text-slate-600"
                              }`}
                            >
                              {isNew ? <Plus size={8} className="text-green-600" /> : <Zap size={8} className="text-rose-400" />}
                              {s}
                            </span>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {/* Experience — AI-added bullets highlighted */}
                  {editedExperience.length > 0 && (
                    <div className={`transition-all duration-300 ${aiChanges.fields.has("experience") ? "border-l-2 border-green-400 pl-2" : ""}`}>
                      <p className="text-[9px] font-bold uppercase tracking-widest text-slate-400 mb-1 flex items-center gap-1.5">
                        Experience {aiChanges.fields.has("experience") && <AiBadge />}
                      </p>
                      {editedExperience.slice(0, 2).map((exp, idx) => (
                        <div key={idx} className="mb-2.5">
                          <p className="text-[11px] font-semibold text-slate-800">{exp.role} — {exp.company}</p>
                          <p className="text-[10px] text-slate-400 mb-1">{exp.duration}</p>
                          {exp.achievements?.slice(0, 4).map((ach, i) => {
                            const isAiAdded = aiChanges.addedBullets.has(ach);
                            return (
                              <p
                                key={i}
                                className={`text-[10px] ml-2 leading-relaxed line-clamp-1 mb-0.5 flex items-start gap-1 ${
                                  isAiAdded ? "text-green-800 bg-green-50 px-1 rounded" : "text-slate-600"
                                }`}
                              >
                                <span className={`flex-shrink-0 font-bold ${isAiAdded ? "text-green-500" : "text-rose-400"}`}>
                                  {isAiAdded ? "+" : "·"}
                                </span>
                                {ach}
                              </p>
                            );
                          })}
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Certifications — AI-added ones highlighted */}
                  {editedCertifications.length > 0 && (
                    <div className={`transition-all duration-300 ${aiChanges.fields.has("certifications") ? "border-l-2 border-green-400 pl-2 bg-green-50/30 rounded-r-lg py-1" : ""}`}>
                      <p className="text-[9px] font-bold uppercase tracking-widest text-slate-400 mb-1.5 flex items-center gap-1.5">
                        Certifications {aiChanges.fields.has("certifications") && <AiBadge />}
                      </p>
                      {editedCertifications.map((cert, i) => {
                        const isNew = aiChanges.addedCerts.has(cert.name);
                        return (
                          <div
                            key={i}
                            className={`mb-1.5 flex items-start gap-1.5 ${isNew ? "bg-green-50 px-1.5 py-0.5 rounded border border-green-100" : ""}`}
                          >
                            <span className={`text-[10px] flex-shrink-0 font-bold mt-0.5 ${isNew ? "text-green-500" : "text-amber-400"}`}>
                              {isNew ? "+" : "★"}
                            </span>
                            <div>
                              <p className="text-[10px] font-semibold text-slate-800 leading-tight">{cert.name}</p>
                              <p className="text-[9px] text-slate-400">
                                {cert.issuer}{cert.date ? ` · ${cert.date}` : ""}{cert.expiry ? ` → ${cert.expiry}` : ""}
                              </p>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              </ScrollArea>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* BowJob Analysis Panel */}
      {(skills_analysis || writing_quality || red_flags.length > 0 || overall_feedback) && (
        <div className="border-b border-slate-100">
          <button onClick={() => setAnalysisExpanded(!analysisExpanded)} className="w-full flex items-center justify-between px-4 py-2.5 hover:bg-slate-50 transition-colors">
            <span className="text-[11px] font-semibold text-slate-700 font-sans flex items-center gap-2">
              <Brain size={12} className="text-violet-500" /> AI Analysis Report
            </span>
            {analysisExpanded ? <ChevronUp size={13} className="text-slate-400" /> : <ChevronDown size={13} className="text-slate-400" />}
          </button>
          <AnimatePresence>
            {analysisExpanded && (
              <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.2 }} style={{ overflow: "hidden" }}>
                <div className="max-h-96 overflow-y-auto overscroll-contain scrollbar-thin scrollbar-thumb-slate-200 scrollbar-track-transparent hover:scrollbar-thumb-slate-300">
                  <div className="px-4 pb-4 space-y-4 font-sans text-[11px]">
                    {skills_analysis && (
                      <div className="space-y-2">
                        <p className="text-[9px] font-bold uppercase tracking-widest text-slate-400 flex items-center gap-1 pt-2">
                          <TrendingUp size={9} /> Skills Gap
                        </p>
                        {(skills_analysis.matched_skills || []).length > 0 && (
                          <div>
                            <p className="text-[9px] text-emerald-600 font-semibold mb-1">✓ Matched ({skills_analysis.matched_skills!.length})</p>
                            <div className="flex flex-wrap gap-1">
                              {skills_analysis.matched_skills!.slice(0, 8).map((s, i) => (
                                <span key={i} className="px-1.5 py-0.5 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded text-[9px]">{s}</span>
                              ))}
                            </div>
                          </div>
                        )}
                        {(skills_analysis.missing_skills || []).length > 0 && (
                          <div>
                            <p className="text-[9px] text-red-500 font-semibold mb-1">✗ Missing ({skills_analysis.missing_skills!.length})</p>
                            <div className="flex flex-wrap gap-1">
                              {skills_analysis.missing_skills!.slice(0, 8).map((s, i) => (
                                <span key={i} className="px-1.5 py-0.5 bg-red-50 text-red-600 border border-red-200 rounded text-[9px]">{s}</span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                    {red_flags.length > 0 && (
                      <div className="space-y-1.5">
                        <p className="text-[9px] font-bold uppercase tracking-widest text-slate-400 flex items-center gap-1">
                          <AlertTriangle size={9} /> Red Flags
                        </p>
                        {red_flags.map((flag, i) => (
                          <div key={i} className={`p-2 rounded-lg border text-[10px] ${SEVERITY_STYLE[flag.severity]}`}>
                            <div className="flex items-center gap-1.5 mb-0.5">
                              <span className="font-bold uppercase text-[8px] tracking-wide px-1 py-0.5 rounded border border-current">{flag.severity}</span>
                              <span className="font-semibold">{flag.issue}</span>
                            </div>
                            <p className="text-[9px] opacity-80">{flag.recommendation}</p>
                          </div>
                        ))}
                      </div>
                    )}
                    {writing_quality && (
                      <div className="space-y-2">
                        <p className="text-[9px] font-bold uppercase tracking-widest text-slate-400 flex items-center gap-1">
                          <Award size={9} /> Writing Quality
                        </p>
                        {(writing_quality.weak_phrases || []).slice(0, 3).map((wp, i) => (
                          <div key={i} className="flex items-start gap-2 p-2 bg-amber-50 rounded-lg border border-amber-100">
                            <div className="flex-1">
                              <span className="line-through text-[10px] text-red-400">{wp.weak_phrase}</span>
                              <span className="text-[10px] text-slate-400 mx-1">→</span>
                              <span className="text-[10px] font-semibold text-emerald-700">{wp.stronger_alternative}</span>
                            </div>
                          </div>
                        ))}
                        {writing_quality.action_verbs?.recommended_power_verbs && (
                          <div>
                            <p className="text-[9px] text-slate-500 mb-1">Power verbs to use:</p>
                            <div className="flex flex-wrap gap-1">
                              {writing_quality.action_verbs.recommended_power_verbs.slice(0, 8).map((v, i) => (
                                <span key={i} className="px-1.5 py-0.5 bg-violet-50 text-violet-700 border border-violet-200 rounded text-[9px] font-medium">{v}</span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                    {overall_feedback && (
                      <div className="space-y-2">
                        <p className="text-[9px] font-bold uppercase tracking-widest text-slate-400 flex items-center gap-1">
                          <Lightbulb size={9} /> Quick Wins
                        </p>
                        {(overall_feedback.quick_wins || []).map((qw, i) => (
                          <p key={i} className="text-[10px] text-slate-700 flex items-start gap-1.5">
                            <span className="text-emerald-500 flex-shrink-0 mt-0.5">⚡</span> {qw}
                          </p>
                        ))}
                        {(overall_feedback.strengths || []).length > 0 && (
                          <div>
                            <p className="text-[9px] text-emerald-600 font-semibold mb-0.5">Strengths</p>
                            {overall_feedback.strengths!.slice(0, 3).map((s, i) => (
                              <p key={i} className="text-[10px] text-slate-600 flex items-start gap-1"><span className="text-emerald-400">✓</span> {s}</p>
                            ))}
                          </div>
                        )}
                        {(overall_feedback.weaknesses || []).length > 0 && (
                          <div>
                            <p className="text-[9px] text-red-500 font-semibold mb-0.5">Gaps to Address</p>
                            {overall_feedback.weaknesses!.slice(0, 3).map((w, i) => (
                              <p key={i} className="text-[10px] text-slate-600 flex items-start gap-1"><span className="text-red-400">✗</span> {w}</p>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      )}

      {/* Changes Made (from initial tailoring) */}
      {changes_made.length > 0 && (
        <div className="border-b border-slate-100">
          <button onClick={() => setChangesExpanded(!changesExpanded)} className="w-full flex items-center justify-between px-4 py-2.5 hover:bg-slate-50 transition-colors">
            <span className="text-[11px] font-semibold text-slate-700 font-sans">
              {changes_made.length} changes applied by AI
            </span>
            {changesExpanded ? <ChevronUp size={13} className="text-slate-400" /> : <ChevronDown size={13} className="text-slate-400" />}
          </button>
          <AnimatePresence>
            {changesExpanded && (
              <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.2 }} style={{ overflow: "hidden" }}>
                <div className="px-4 pb-3 space-y-1">
                  {changes_made.map((change, i) => (
                    <p key={i} className="text-[11px] text-slate-600 font-sans flex items-start gap-1.5">
                      <span className="text-emerald-400 mt-0.5 flex-shrink-0">✓</span> {change}
                    </p>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      )}

      {/* Actions */}
      <div className="px-4 py-3 flex items-center gap-2">
        <Button
          size="sm"
          className="flex-1 h-9 text-[12px] font-semibold bg-rose-600 hover:bg-rose-700 text-white gap-1.5 font-sans"
          onClick={() => onSendAction(`__APPROVE_CV__:${application_id}`)}
        >
          <CheckCircle size={13} />
          Approve & Generate PDF
        </Button>
        <Button
          size="sm"
          variant="outline"
          className="h-9 text-[11px] font-sans border-slate-200 text-slate-600 hover:text-slate-900 gap-1.5"
          onClick={() => setEditOpen(true)}
        >
          <Edit3 size={11} />
          Edit CV
        </Button>
        <Button
          size="sm"
          variant="ghost"
          className="h-9 text-[11px] font-sans text-slate-400 hover:text-rose-500 gap-1"
          onClick={() => onSendAction(`__REGENERATE_CV__:${job_id || application_id}`)}
        >
          <RefreshCw size={11} />
        </Button>
      </div>

      {/* ── Edit Dialog ──────────────────────────────────────────────────────── */}
      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent className="sm:max-w-[700px] max-h-[90vh] flex flex-col">
          <DialogHeader>
            <DialogTitle className="font-sans text-sm flex items-center gap-2">
              Edit Tailored CV — {job.title} at {job.company}
              {hasAiChanges && (
                <span className="flex items-center gap-1 px-2 py-0.5 bg-green-100 border border-green-200 rounded-full text-[9px] font-bold text-green-700">
                  <Sparkles size={8} /> {aiChanges.count} AI changes live
                </span>
              )}
            </DialogTitle>
          </DialogHeader>

          {/* Tabs */}
          <div className="flex gap-1 border-b border-slate-100 pb-2 flex-shrink-0 flex-wrap">
            {(["summary", "experience", "skills", "certifications", "cover"] as const).map(tab => {
              const hasTabChange = aiChanges.fields.has(tab)
                || (tab === "skills" && aiChanges.addedSkills.size > 0)
                || (tab === "certifications" && aiChanges.addedCerts.size > 0);
              return (
                <button
                  key={tab}
                  onClick={() => setActiveEditTab(tab)}
                  className={`px-3 py-1.5 rounded-lg text-[11px] font-medium font-sans transition-colors relative ${
                    activeEditTab === tab ? "bg-rose-600 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                  }`}
                >
                  {tab === "cover" ? "Cover Letter" : tab === "certifications" ? "Certs" : tab.charAt(0).toUpperCase() + tab.slice(1)}
                  {hasTabChange && (
                    <span className="absolute -top-1 -right-1 w-2 h-2 bg-green-500 rounded-full border border-white" />
                  )}
                </button>
              );
            })}
          </div>

          <div className="flex-1 overflow-y-auto py-2 space-y-3">
            {activeEditTab === "summary" && (
              <div>
                <label className="text-[11px] font-semibold text-slate-600 font-sans block mb-1.5 flex items-center gap-1.5">
                  Professional Summary
                  {aiChanges.fields.has("summary") && <AiBadge label="AI edited" />}
                </label>
                <Textarea
                  value={editedSummary}
                  onChange={e => setEditedSummary(e.target.value)}
                  className={`min-h-[160px] font-sans text-[13px] resize-none transition-all ${aiChanges.fields.has("summary") ? "border-green-300 bg-green-50/30 focus:border-green-400" : ""}`}
                  placeholder="Write a compelling summary targeting this role..."
                />
                <p className="text-[10px] text-slate-400 mt-1">Tip: Open with your title + years of experience, then 2-3 key strengths that match the job.</p>
              </div>
            )}

            {activeEditTab === "experience" && (
              <div className="space-y-4">
                {editedExperience.map((exp, expIdx) => (
                  <div key={expIdx} className="border border-slate-200 rounded-lg p-3">
                    <div className="mb-2">
                      <p className="text-[12px] font-semibold text-slate-800 font-sans">{exp.role}</p>
                      <p className="text-[10px] text-slate-500 font-sans">{exp.company} · {exp.duration}</p>
                    </div>
                    <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-wide mb-2">Achievement Bullets</p>
                    <div className="space-y-2">
                      {exp.achievements.map((bullet, bIdx) => {
                        const isAiAdded = aiChanges.addedBullets.has(bullet);
                        return (
                          <div key={bIdx} className={`flex gap-2 items-start rounded-lg transition-colors ${isAiAdded ? "bg-green-50 px-2 pt-1 border border-green-200" : ""}`}>
                            <span className={`text-[10px] mt-2 flex-shrink-0 font-bold ${isAiAdded ? "text-green-500" : "text-rose-400"}`}>
                              {isAiAdded ? "+" : "•"}
                            </span>
                            <Textarea
                              value={bullet}
                              onChange={e => updateBullet(expIdx, bIdx, e.target.value)}
                              className={`flex-1 min-h-[56px] font-sans text-[12px] resize-none ${isAiAdded ? "border-green-200 bg-green-50/50" : ""}`}
                              placeholder="Accomplished [X] as measured by [Y] by doing [Z]..."
                            />
                            <button onClick={() => removeBullet(expIdx, bIdx)} className="mt-2 p-1 text-slate-300 hover:text-red-400 transition-colors flex-shrink-0"><Trash2 size={12} /></button>
                          </div>
                        );
                      })}
                      <button onClick={() => addBullet(expIdx)} className="flex items-center gap-1 text-[11px] text-rose-500 hover:text-rose-700 font-sans font-medium mt-1">
                        <Plus size={11} /> Add bullet
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {activeEditTab === "skills" && (
              <div className="space-y-3">
                {Object.entries(editedSkillsRaw).map(([category, skills]) => (
                  <div key={category}>
                    <label className="text-[11px] font-semibold text-slate-600 font-sans block mb-1 capitalize flex items-center gap-1.5">
                      {category} Skills
                      {category === "technical" && aiChanges.addedSkills.size > 0 && (
                        <AiBadge label={`+${aiChanges.addedSkills.size}`} />
                      )}
                    </label>
                    <input
                      className={`w-full border rounded-lg px-3 py-2 text-[12px] font-sans outline-none focus:border-rose-300 transition-colors ${
                        category === "technical" && aiChanges.fields.has("skills")
                          ? "border-green-300 bg-green-50/30"
                          : "border-slate-200"
                      }`}
                      value={skills.join(", ")}
                      onChange={e => updateSkillCategory(category, e.target.value)}
                      placeholder="Comma-separated skills..."
                    />
                  </div>
                ))}
                <p className="text-[10px] text-slate-400">Tip: Put the most job-relevant skills first. Green skills were added by AI.</p>
              </div>
            )}

            {activeEditTab === "certifications" && (
              <div className="space-y-3">
                <div className="flex items-center justify-between mb-1">
                  <label className="text-[11px] font-semibold text-slate-600 font-sans flex items-center gap-1.5">
                    Certifications
                    {aiChanges.addedCerts.size > 0 && <AiBadge label={`+${aiChanges.addedCerts.size}`} />}
                  </label>
                  <button
                    onClick={addCert}
                    className="flex items-center gap-1 text-[11px] text-rose-500 hover:text-rose-700 font-sans font-medium"
                  >
                    <Plus size={11} /> Add Certificate
                  </button>
                </div>

                {editedCertifications.length === 0 && (
                  <div className="text-center py-8 text-[11px] text-slate-400 font-sans border border-dashed border-slate-200 rounded-lg">
                    No certifications yet. Click "Add Certificate" or ask AI to suggest relevant ones.
                  </div>
                )}

                {editedCertifications.map((cert, idx) => {
                  const isNew = aiChanges.addedCerts.has(cert.name);
                  return (
                    <div
                      key={idx}
                      className={`border rounded-xl p-3 space-y-2 transition-colors ${isNew ? "border-green-200 bg-green-50/40" : "border-slate-200"}`}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wide flex items-center gap-1">
                          {isNew ? <span className="text-green-500">★ New</span> : `Cert #${idx + 1}`}
                        </span>
                        <button onClick={() => removeCert(idx)} className="p-1 text-slate-300 hover:text-red-400 transition-colors">
                          <Trash2 size={12} />
                        </button>
                      </div>

                      {/* Name */}
                      <div>
                        <label className="text-[10px] text-slate-500 font-sans block mb-0.5">Certificate Name *</label>
                        <input
                          value={cert.name}
                          onChange={e => updateCert(idx, "name", e.target.value)}
                          className={`w-full border rounded-lg px-3 py-2 text-[12px] font-sans outline-none focus:border-rose-300 transition-colors ${isNew ? "border-green-200 bg-green-50/30" : "border-slate-200"}`}
                          placeholder="e.g. AWS Certified Solutions Architect"
                        />
                      </div>

                      <div className="grid grid-cols-2 gap-2">
                        {/* Issuer */}
                        <div>
                          <label className="text-[10px] text-slate-500 font-sans block mb-0.5">Issuing Organization</label>
                          <input
                            value={cert.issuer}
                            onChange={e => updateCert(idx, "issuer", e.target.value)}
                            className="w-full border border-slate-200 rounded-lg px-3 py-2 text-[12px] font-sans outline-none focus:border-rose-300 transition-colors"
                            placeholder="e.g. Amazon Web Services"
                          />
                        </div>

                        {/* Date */}
                        <div>
                          <label className="text-[10px] text-slate-500 font-sans block mb-0.5">Date Issued</label>
                          <input
                            value={cert.date}
                            onChange={e => updateCert(idx, "date", e.target.value)}
                            className="w-full border border-slate-200 rounded-lg px-3 py-2 text-[12px] font-sans outline-none focus:border-rose-300 transition-colors"
                            placeholder="e.g. Jan 2024"
                          />
                        </div>
                      </div>

                      <div className="grid grid-cols-2 gap-2">
                        {/* Expiry */}
                        <div>
                          <label className="text-[10px] text-slate-500 font-sans block mb-0.5">Expiry Date <span className="text-slate-300">(optional)</span></label>
                          <input
                            value={cert.expiry || ""}
                            onChange={e => updateCert(idx, "expiry", e.target.value)}
                            className="w-full border border-slate-200 rounded-lg px-3 py-2 text-[12px] font-sans outline-none focus:border-rose-300 transition-colors"
                            placeholder="e.g. Jan 2027 or No Expiry"
                          />
                        </div>

                        {/* Credential ID */}
                        <div>
                          <label className="text-[10px] text-slate-500 font-sans block mb-0.5">Credential ID <span className="text-slate-300">(optional)</span></label>
                          <input
                            value={cert.credential_id || ""}
                            onChange={e => updateCert(idx, "credential_id", e.target.value)}
                            className="w-full border border-slate-200 rounded-lg px-3 py-2 text-[12px] font-sans outline-none focus:border-rose-300 transition-colors"
                            placeholder="ID or verification URL"
                          />
                        </div>
                      </div>
                    </div>
                  );
                })}

                <p className="text-[10px] text-slate-400">Tip: Ask AI to suggest certifications relevant to this job role — it will add them automatically.</p>
              </div>
            )}

            {activeEditTab === "cover" && (
              <div>
                <label className="text-[11px] font-semibold text-slate-600 font-sans block mb-1.5 flex items-center gap-1.5">
                  Cover Letter
                  {aiChanges.fields.has("cover") && <AiBadge label="AI edited" />}
                </label>
                <Textarea
                  value={editedCoverLetter}
                  onChange={e => setEditedCoverLetter(e.target.value)}
                  className={`min-h-[220px] font-sans text-[12px] resize-none transition-all ${aiChanges.fields.has("cover") ? "border-green-300 bg-green-50/30" : ""}`}
                  placeholder="Hook → Value (2-3 achievements matching requirements) → CTA..."
                />
                <p className="text-[10px] text-slate-400 mt-1">Structure: 1) Why this company specifically. 2) Two specific achievements that prove fit. 3) Clear ask.</p>
              </div>
            )}
          </div>

          {/* AI Chat Input */}
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15, duration: 0.3 }}
            className="flex-shrink-0 border-t border-slate-100 pt-3 px-1"
          >
            <div className="flex items-center gap-1 mb-1.5">
              <Wand2 size={10} className="text-rose-500" />
              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Ask AI to edit this section — changes apply live to preview</span>
            </div>
            <div className="flex items-center gap-2 bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 focus-within:border-rose-300 focus-within:ring-2 focus-within:ring-rose-50 transition-all">
              <Sparkles size={13} className={`flex-shrink-0 ${aiLoading ? "text-rose-400 animate-spin" : "text-slate-400"}`} />
              <input
                ref={aiInputRef}
                value={aiInstruction}
                onChange={e => setAiInstruction(e.target.value)}
                onKeyDown={e => e.key === "Enter" && handleAiRewrite()}
                placeholder={
                  activeEditTab === "summary" ? "e.g. Make it more results-focused and aggressive..." :
                  activeEditTab === "experience" ? "e.g. Add more metrics and power verbs to all entries..." :
                  activeEditTab === "skills" ? "e.g. Prioritize cloud skills, add Kubernetes..." :
                  activeEditTab === "certifications" ? "e.g. Suggest relevant AWS or Azure certifications for this role..." :
                  "e.g. Make the opening hook more compelling..."
                }
                disabled={aiLoading}
                className="flex-1 bg-transparent text-xs text-slate-700 placeholder-slate-400 outline-none"
              />
              <button
                onClick={handleAiRewrite}
                disabled={!aiInstruction.trim() || aiLoading}
                className="w-6 h-6 rounded-lg bg-rose-600 hover:bg-rose-700 disabled:opacity-40 flex items-center justify-center transition-all flex-shrink-0"
              >
                <Send size={10} className="text-white" />
              </button>
            </div>
          </motion.div>

          <DialogFooter className="flex-shrink-0 border-t border-slate-100 pt-3">
            <Button size="sm" variant="ghost" className="font-sans text-sm text-slate-500" onClick={() => setEditOpen(false)}>
              <X size={13} className="mr-1" /> Cancel
            </Button>
            <Button size="sm" disabled={saving} className="bg-rose-600 hover:bg-rose-700 text-white font-sans text-sm gap-1.5" onClick={handleSaveEdits}>
              <Save size={13} />
              {saving ? "Saving..." : "Save Changes"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </motion.div>
  );
}
