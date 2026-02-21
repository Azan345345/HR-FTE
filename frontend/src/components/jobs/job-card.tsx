"use client";

import { Building2, MapPin, Briefcase, DollarSign, ExternalLink, TrendingUp } from "lucide-react";

interface JobCardProps {
    title: string;
    company: string;
    location?: string;
    jobType?: string;
    salaryRange?: string;
    source: string;
    matchScore?: number;
    matchingSkills?: string[];
    onSelect: () => void;
    applicationUrl?: string;
}

function getScoreColor(score: number): string {
    if (score >= 75) return "text-emerald-400 bg-emerald-500/10";
    if (score >= 50) return "text-amber-400 bg-amber-500/10";
    return "text-red-400 bg-red-500/10";
}

function getScoreBarColor(score: number): string {
    if (score >= 75) return "from-emerald-500 to-emerald-400";
    if (score >= 50) return "from-amber-500 to-amber-400";
    return "from-red-500 to-red-400";
}

export function JobCard({
    title, company, location, jobType, salaryRange, source,
    matchScore, matchingSkills, onSelect, applicationUrl,
}: JobCardProps) {
    const score = matchScore ?? 0;

    return (
        <div
            className="glass rounded-xl p-5 hover:border-indigo-500/50 transition-all duration-300 cursor-pointer group"
            onClick={onSelect}
        >
            <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                    {/* Title & Company */}
                    <h3 className="font-semibold text-sm truncate group-hover:text-indigo-400 transition-colors">
                        {title}
                    </h3>
                    <div className="flex items-center gap-2 mt-1">
                        <Building2 className="h-3.5 w-3.5 text-muted-foreground flex-shrink-0" />
                        <span className="text-sm text-muted-foreground truncate">{company}</span>
                    </div>

                    {/* Meta Row */}
                    <div className="flex flex-wrap items-center gap-3 mt-2">
                        {location && (
                            <span className="flex items-center gap-1 text-xs text-muted-foreground">
                                <MapPin className="h-3 w-3" /> {location}
                            </span>
                        )}
                        {jobType && (
                            <span className="flex items-center gap-1 text-xs text-muted-foreground">
                                <Briefcase className="h-3 w-3" /> {jobType}
                            </span>
                        )}
                        {salaryRange && (
                            <span className="flex items-center gap-1 text-xs text-muted-foreground">
                                <DollarSign className="h-3 w-3" /> {salaryRange}
                            </span>
                        )}
                    </div>

                    {/* Matching Skills */}
                    {matchingSkills && matchingSkills.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-2">
                            {matchingSkills.slice(0, 5).map((skill, i) => (
                                <span key={i} className="px-1.5 py-0.5 bg-emerald-500/10 text-emerald-400 text-xs rounded">
                                    {skill}
                                </span>
                            ))}
                            {matchingSkills.length > 5 && (
                                <span className="text-xs text-muted-foreground">+{matchingSkills.length - 5} more</span>
                            )}
                        </div>
                    )}
                </div>

                {/* Score */}
                <div className="flex flex-col items-center gap-1 flex-shrink-0">
                    <div className={`px-2.5 py-1.5 rounded-lg ${getScoreColor(score)} font-bold text-sm`}>
                        {score.toFixed(0)}%
                    </div>
                    <div className="w-12 h-1 bg-secondary rounded-full overflow-hidden">
                        <div
                            className={`h-full bg-gradient-to-r ${getScoreBarColor(score)} rounded-full transition-all`}
                            style={{ width: `${score}%` }}
                        />
                    </div>
                    <span className="text-[10px] text-muted-foreground">{source}</span>
                </div>
            </div>

            {/* Actions (on hover) */}
            {applicationUrl && (
                <div className="mt-3 pt-3 border-t border-border opacity-0 group-hover:opacity-100 transition-opacity">
                    <a
                        href={applicationUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        className="flex items-center gap-1.5 text-xs text-indigo-400 hover:text-indigo-300"
                    >
                        <ExternalLink className="h-3 w-3" /> Apply directly
                    </a>
                </div>
            )}
        </div>
    );
}
