"use client";

import { Building2, LineChart, Users } from "lucide-react";

export function CompanyResearch({ researchData, salaryData }: any) {
    return (
        <div className="space-y-6">
            <div className="glass rounded-xl p-6">
                <div className="flex items-center gap-2 mb-4">
                    <Building2 className="w-5 h-5 text-indigo-400" />
                    <h2 className="text-xl font-semibold">Company Overview</h2>
                </div>
                <p className="text-sm text-muted-foreground leading-relaxed whitespace-pre-line">
                    {researchData?.overview || "No specific overview provided."}
                </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="glass rounded-xl p-6">
                    <div className="flex items-center gap-2 mb-4">
                        <Users className="w-5 h-5 text-emerald-400" />
                        <h3 className="font-semibold">Culture Insights</h3>
                    </div>
                    <p className="text-sm text-muted-foreground leading-relaxed">
                        {researchData?.culture_insights || "No specific culture insights provided."}
                    </p>
                </div>

                <div className="glass rounded-xl p-6">
                    <div className="flex items-center gap-2 mb-4">
                        <LineChart className="w-5 h-5 text-amber-400" />
                        <h3 className="font-semibold">Salary Expectations</h3>
                    </div>
                    <div className="space-y-3">
                        <div>
                            <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Expected Range</span>
                            <p className="text-lg font-medium">{salaryData?.expected_range || "Unknown"}</p>
                        </div>
                        <div>
                            <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Negotiation Tips</span>
                            <p className="text-sm text-muted-foreground mt-1">{salaryData?.negotiation_tips || "Aim high but emphasize fit and total compensation."}</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
