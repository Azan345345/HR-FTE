"use client";

import { useEffect, useState } from "react";
import { useAuthStore } from "@/stores/auth-store";
import { AlertTriangle, ServerCrash, Cpu } from "lucide-react";

interface QuotaUsage {
    used: number;
    limit: number;
    percentage: number;
    is_near_limit: boolean;
    is_exhausted: boolean;
}

export function QuotaWidget() {
    const { accessToken } = useAuthStore();
    const apiBase = process.env.NEXT_PUBLIC_API_URL || "";

    const [quotas, setQuotas] = useState<Record<string, QuotaUsage>>({});
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (accessToken) {
            fetch(`${apiBase}/api/quota/usage`, {
                headers: { Authorization: `Bearer ${accessToken}` }
            })
                .then(res => res.json())
                .then(data => {
                    setQuotas(data);
                })
                .catch(console.error)
                .finally(() => setLoading(false));
        }
    }, [accessToken, apiBase]);

    if (loading) return null;

    const items = [
        { key: "llm_requests", label: "LLM Generations" },
        { key: "job_searches", label: "Job Searches" },
        { key: "cv_parses", label: "AI CV Parses" },
    ];

    return (
        <div className="glass rounded-xl p-6">
            <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
                <Cpu className="w-5 h-5 text-indigo-400" />
                API Quotas
            </h2>
            <div className="space-y-5">
                {items.map(({ key, label }) => {
                    const usage = quotas[key];
                    if (!usage) return null;

                    return (
                        <div key={key} className="space-y-2">
                            <div className="flex justify-between items-center text-sm">
                                <span className="font-medium">{label}</span>
                                <span className="text-muted-foreground">{usage.used} / {usage.limit}</span>
                            </div>
                            <div className="h-2 w-full bg-secondary/50 rounded-full overflow-hidden">
                                <div
                                    className={`h-full rounded-full transition-all duration-500 ${usage.is_exhausted ? "bg-rose-500" :
                                            usage.is_near_limit ? "bg-amber-400" :
                                                "bg-indigo-500"
                                        }`}
                                    style={{ width: `${Math.min(usage.percentage, 100)}%` }}
                                />
                            </div>
                            {usage.is_near_limit && !usage.is_exhausted && (
                                <p className="text-xs text-amber-400 flex items-center gap-1">
                                    <AlertTriangle className="w-3 h-3" /> Approaching free tier limit
                                </p>
                            )}
                            {usage.is_exhausted && (
                                <p className="text-xs text-rose-400 flex items-center gap-1">
                                    <ServerCrash className="w-3 h-3" /> Quota exhausted for this month
                                </p>
                            )}
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
