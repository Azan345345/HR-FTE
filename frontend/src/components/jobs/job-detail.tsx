"use client";

import { useState } from "react";
import {
    Building2, MapPin, Briefcase, DollarSign, ExternalLink,
    Calendar, CheckCircle2, XCircle, ArrowLeft, TrendingUp, Sparkles, Loader2
} from "lucide-react";
import { useTailorStore } from "@/stores/tailor-store";
import { useAuthStore } from "@/stores/auth-store";
import { useCVStore } from "@/stores/cv-store";

interface JobDetailProps {
    job: {
        id: string; // Ensure ID is passed
        title: string;
        company: string;
        location?: string;
        job_type?: string;
        salary_range?: string;
        description?: string;
        requirements?: string[];
        nice_to_have?: string[];
        responsibilities?: string[];
        posted_date?: string;
        application_url?: string;
        source: string;
        match_score?: number;
        matching_skills?: string[];
        missing_skills?: string[];
    };
    onBack: () => void;
}

export function JobDetail({ job, onBack }: JobDetailProps) {
    const score = job.match_score ?? 0;
    const { setTailoring, setTailoredCV, setShowPreview, setError } = useTailorStore();
    const { cvs } = useCVStore();
    const { accessToken } = useAuthStore();
    const [isProcessing, setIsProcessing] = useState(false);

    const apiBase = process.env.NEXT_PUBLIC_API_URL || "";

    const handleTailorCV = async () => {
        // Find primary CV
        const primaryCV = cvs.find(c => c.is_primary);
        if (!primaryCV) {
            alert("Please upload and set a primary CV first.");
            return;
        }

        setIsProcessing(true);
        setTailoring(true);
        setError(null);

        try {
            const res = await fetch(`${apiBase}/api/cv/${primaryCV.id}/tailor`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
                },
                body: JSON.stringify({ job_id: job.id }),
            });

            if (!res.ok) {
                const err = await res.json().catch(() => ({ detail: "Tailoring failed" }));
                throw new Error(err.detail);
            }

            const data = await res.json();
            setTailoredCV({
                id: data.id,
                jobTitle: data.job_title,
                company: data.company,
                tailoredData: data.tailored_data,
            });
            setShowPreview(true);
        } catch (err: any) {
            setError(err.message || "Failed to tailor CV");
            alert(`Error: ${err.message}`);
        } finally {
            setIsProcessing(false);
            setTailoring(false);
        }
    };

    return (
        <div className="space-y-5 animate-fadeIn">
            {/* Back */}
            <button
                onClick={onBack}
                className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
                <ArrowLeft className="h-4 w-4" /> Back to jobs
            </button>

            {/* Header */}
            <div className="glass rounded-xl p-6">
                <div className="flex items-start justify-between gap-4">
                    <div>
                        <h1 className="text-xl font-bold">{job.title}</h1>
                        <div className="flex items-center gap-4 mt-2 text-muted-foreground">
                            <span className="flex items-center gap-1.5">
                                <Building2 className="h-4 w-4" /> {job.company}
                            </span>
                            {job.location && (
                                <span className="flex items-center gap-1.5">
                                    <MapPin className="h-4 w-4" /> {job.location}
                                </span>
                            )}
                            {job.job_type && (
                                <span className="flex items-center gap-1.5">
                                    <Briefcase className="h-4 w-4" /> {job.job_type}
                                </span>
                            )}
                        </div>
                        <div className="flex items-center gap-4 mt-2 text-muted-foreground text-sm">
                            {job.salary_range && (
                                <span className="flex items-center gap-1.5">
                                    <DollarSign className="h-3.5 w-3.5" /> {job.salary_range}
                                </span>
                            )}
                            {job.posted_date && (
                                <span className="flex items-center gap-1.5">
                                    <Calendar className="h-3.5 w-3.5" /> {job.posted_date}
                                </span>
                            )}
                            <span className="text-xs px-2 py-0.5 bg-secondary rounded">{job.source}</span>
                        </div>
                    </div>

                    {/* Score Card */}
                    <div className="text-center p-4 rounded-xl bg-secondary/50 flex-shrink-0">
                        <div className={`text-3xl font-bold ${score >= 75 ? "text-emerald-400" : score >= 50 ? "text-amber-400" : "text-red-400"}`}>
                            {score.toFixed(0)}%
                        </div>
                        <p className="text-xs text-muted-foreground mt-1">Match Score</p>
                    </div>
                </div>

                <div className="flex items-center gap-3 mt-6">
                    <button
                        onClick={handleTailorCV}
                        disabled={isProcessing}
                        className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-indigo-500 to-purple-500 hover:from-indigo-600 hover:to-purple-600 text-white rounded-lg text-sm font-medium transition-all shadow-lg shadow-indigo-500/20 disabled:opacity-70"
                    >
                        {isProcessing ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                            <Sparkles className="h-4 w-4" />
                        )}
                        {isProcessing ? "Tailoring CV with AI..." : "Tailor CV for this Job"}
                    </button>

                    {job.application_url && (
                        <a
                            href={job.application_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center gap-2 px-4 py-2 bg-secondary hover:bg-secondary/80 rounded-lg text-sm font-medium transition-colors"
                        >
                            <ExternalLink className="h-4 w-4" /> Apply Now
                        </a>
                    )}
                </div>
            </div>

            {/* Skills Match */}
            {(job.matching_skills?.length || job.missing_skills?.length) ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {job.matching_skills && job.matching_skills.length > 0 && (
                        <div className="glass rounded-xl p-5">
                            <div className="flex items-center gap-2 mb-3">
                                <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                                <h3 className="font-semibold text-sm">Matching Skills ({job.matching_skills.length})</h3>
                            </div>
                            <div className="flex flex-wrap gap-1.5">
                                {job.matching_skills.map((s, i) => (
                                    <span key={i} className="px-2 py-1 bg-emerald-500/10 text-emerald-400 text-xs rounded-md">{s}</span>
                                ))}
                            </div>
                        </div>
                    )}
                    {job.missing_skills && job.missing_skills.length > 0 && (
                        <div className="glass rounded-xl p-5">
                            <div className="flex items-center gap-2 mb-3">
                                <XCircle className="h-4 w-4 text-red-400" />
                                <h3 className="font-semibold text-sm">Missing Skills ({job.missing_skills.length})</h3>
                            </div>
                            <div className="flex flex-wrap gap-1.5">
                                {job.missing_skills.map((s, i) => (
                                    <span key={i} className="px-2 py-1 bg-red-500/10 text-red-400 text-xs rounded-md">{s}</span>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            ) : null}

            {/* Description */}
            {job.description && (
                <div className="glass rounded-xl p-5">
                    <h3 className="font-semibold mb-3">Description</h3>
                    <p className="text-sm text-muted-foreground leading-relaxed whitespace-pre-line">
                        {job.description}
                    </p>
                </div>
            )}

            {/* Requirements */}
            {job.requirements && job.requirements.length > 0 && (
                <div className="glass rounded-xl p-5">
                    <h3 className="font-semibold mb-3">Requirements</h3>
                    <ul className="space-y-1.5">
                        {job.requirements.map((r, i) => (
                            <li key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
                                <span className="text-indigo-400 mt-0.5">•</span> {r}
                            </li>
                        ))}
                    </ul>
                </div>
            )}

            {/* Responsibilities */}
            {job.responsibilities && job.responsibilities.length > 0 && (
                <div className="glass rounded-xl p-5">
                    <h3 className="font-semibold mb-3">Responsibilities</h3>
                    <ul className="space-y-1.5">
                        {job.responsibilities.map((r, i) => (
                            <li key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
                                <span className="text-blue-400 mt-0.5">•</span> {r}
                            </li>
                        ))}
                    </ul>
                </div>
            )}
        </div>
    );
}
