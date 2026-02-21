"use client";

import { CheckCircle2, Clock, Mail, User, Building, Briefcase } from "lucide-react";

export function ApplicationCard({ application, onReview }: any) {
    const jobTitle = application.job?.title || "Unknown Role";
    const company = application.job?.company || "Unknown Company";
    const hrName = application.hr_contact?.hr_name || "Hiring Manager";
    const hrEmail = application.hr_contact?.hr_email || "Unknown Email";

    const isPending = application.status === "pending_approval";
    const isApproved = application.status === "approved" || application.status === "sent";

    return (
        <div className="glass rounded-xl p-5 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 transition-all hover:bg-white/5">
            <div className="flex-1">
                <div className="flex items-center gap-2 mb-1.5">
                    <h3 className="font-semibold text-lg">{jobTitle}</h3>
                    {isPending && (
                        <span className="text-xs px-2 py-0.5 bg-amber-500/10 text-amber-500 rounded-full flex items-center gap-1">
                            <Clock className="w-3 h-3" /> Action Required
                        </span>
                    )}
                    {isApproved && (
                        <span className="text-xs px-2 py-0.5 bg-emerald-500/10 text-emerald-500 rounded-full flex items-center gap-1">
                            <CheckCircle2 className="w-3 h-3" /> {application.status}
                        </span>
                    )}
                </div>

                <div className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
                    <span className="flex items-center gap-1.5"><Building className="w-4 h-4" /> {company}</span>
                    <span className="flex items-center gap-1.5"><User className="w-4 h-4" /> {hrName}</span>
                    <span className="flex items-center gap-1.5"><Mail className="w-4 h-4" /> {hrEmail}</span>
                </div>
            </div>

            {isPending && (
                <button
                    onClick={onReview}
                    className="flex-shrink-0 px-4 py-2 bg-gradient-to-r from-indigo-500 to-purple-500 hover:from-indigo-600 hover:to-purple-600 text-white text-sm font-medium rounded-lg shadow-lg shadow-indigo-500/20 transition-all"
                >
                    Review Email Draft
                </button>
            )}
        </div>
    );
}
