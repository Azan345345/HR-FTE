"use client";

import { useEffect, useState } from "react";
import { RefreshCw, GraduationCap, Building2, ChevronRight, PlayCircle } from "lucide-react";
import { useAuthStore } from "@/stores/auth-store";
import Link from "next/link";

export default function InterviewPage() {
    const { accessToken } = useAuthStore();
    const [preps, setPreps] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    const apiBase = process.env.NEXT_PUBLIC_API_URL || "";

    const fetchPreps = async () => {
        setLoading(true);
        try {
            const res = await fetch(`${apiBase}/api/interview`, {
                headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
            });
            if (res.ok) {
                const data = await res.json();
                setPreps(data);
            }
        } catch (error) {
            console.error("Failed to fetch interview preps:", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (accessToken) {
            fetchPreps();
        }
    }, [accessToken]);

    return (
        <div className="space-y-6 animate-fadeIn">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold">Interview Preparations</h1>
                    <p className="text-muted-foreground mt-1">Review tailored questions and company research.</p>
                </div>
                <button
                    onClick={fetchPreps}
                    className="p-2 text-muted-foreground hover:text-foreground bg-white/5 rounded-lg transition-colors"
                >
                    <RefreshCw className="w-5 h-5" />
                </button>
            </div>

            {loading ? (
                <div className="flex items-center justify-center p-12 text-muted-foreground">
                    <RefreshCw className="h-6 w-6 animate-spin" />
                </div>
            ) : preps.length === 0 ? (
                <div className="glass rounded-xl p-8 text-center text-muted-foreground">
                    <GraduationCap className="h-10 w-10 mx-auto mb-3 opacity-40" />
                    <p>No interview preparations generated yet.</p>
                    <p className="text-sm mt-1">Apply for a job to unlock tailored prep materials!</p>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {preps.map((prep) => (
                        <div key={prep.id} className="glass rounded-xl p-5 hover:border-indigo-500/50 transition-all group">
                            <div className="flex items-start justify-between">
                                <div>
                                    <h3 className="font-semibold text-lg">{prep.job?.title || "Role"}</h3>
                                    <div className="flex items-center gap-2 mt-1 text-sm text-muted-foreground">
                                        <Building2 className="w-4 h-4" /> {prep.job?.company || "Company"}
                                    </div>
                                </div>
                                <span className={`text-xs px-2 py-1 rounded-full ${prep.status === 'completed' ? 'bg-emerald-500/10 text-emerald-500' : 'bg-amber-500/10 text-amber-500'}`}>
                                    {prep.status}
                                </span>
                            </div>

                            <div className="flex items-center gap-3 mt-5">
                                <Link
                                    href={`/interview/${prep.id}`}
                                    className="flex-1 flex justify-center items-center gap-2 px-4 py-2 bg-white/5 hover:bg-white/10 rounded-lg text-sm font-medium transition-colors"
                                >
                                    Study Material <ChevronRight className="w-4 h-4" />
                                </Link>
                                <Link
                                    href={`/interview/${prep.id}/mock`}
                                    className="flex-1 flex justify-center items-center gap-2 px-4 py-2 bg-indigo-500 hover:bg-indigo-600 text-white rounded-lg text-sm font-medium shadow-lg shadow-indigo-500/20 transition-all"
                                >
                                    <PlayCircle className="w-4 h-4" /> Mock Interview
                                </Link>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
