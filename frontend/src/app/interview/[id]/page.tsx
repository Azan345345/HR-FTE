"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { RefreshCw, ArrowLeft, Download } from "lucide-react";
import { useAuthStore } from "@/stores/auth-store";
import Link from "next/link";
import { PrepOverview } from "@/components/interview/PrepOverview";

export default function InterviewDetailPage() {
    const params = useParams();
    const id = params.id as string;
    const { accessToken } = useAuthStore();
    const [prep, setPrep] = useState<any | null>(null);
    const [loading, setLoading] = useState(true);

    const apiBase = process.env.NEXT_PUBLIC_API_URL || "";

    const fetchPrep = async () => {
        setLoading(true);
        try {
            const res = await fetch(`${apiBase}/api/interview/${id}`, {
                headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
            });
            if (res.ok) {
                const data = await res.json();
                setPrep(data);
            }
        } catch (error) {
            console.error("Failed to fetch prep details:", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (id && accessToken) {
            fetchPrep();
        }
    }, [id, accessToken]);

    if (loading) {
        return (
            <div className="flex items-center justify-center p-12 text-muted-foreground h-full min-h-[50vh]">
                <RefreshCw className="h-6 w-6 animate-spin" />
            </div>
        );
    }

    if (!prep) {
        return (
            <div className="glass rounded-xl p-8 text-center text-muted-foreground animate-fadeIn max-w-md mx-auto mt-12">
                <p>Could not load interview preparation.</p>
                <Link href="/interview" className="text-indigo-400 hover:text-indigo-300 flex items-center justify-center gap-1.5 mt-4 text-sm transition-colors">
                    <ArrowLeft className="w-4 h-4" /> Back to Interviews
                </Link>
            </div>
        );
    }

    return (
        <div className="space-y-6 animate-fadeIn">
            {/* Nav */}
            <div className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground w-fit transition-colors">
                <Link href="/interview" className="flex items-center gap-1.5">
                    <ArrowLeft className="w-4 h-4" /> Back
                </Link>
            </div>

            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-2xl font-bold">{prep.job?.title || "Role"} Interview Prep</h1>
                    <p className="text-muted-foreground mt-1">For {prep.job?.company || "Company"}</p>
                </div>

                <div className="flex items-center gap-3">
                    {prep.study_material_path && (
                        <a
                            href={`${apiBase}/api/files/${prep.study_material_path}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center gap-2 px-4 py-2 bg-secondary hover:bg-white/10 rounded-lg text-sm font-medium transition-colors"
                        >
                            <Download className="w-4 h-4" /> Download PDF
                        </a>
                    )}
                    <Link
                        href={`/interview/${id}/mock`}
                        className="flex items-center gap-2 px-5 py-2 bg-gradient-to-r from-indigo-500 to-purple-500 hover:from-indigo-600 hover:to-purple-600 text-white rounded-lg text-sm font-medium shadow-lg shadow-indigo-500/20 transition-all"
                    >
                        Start Mock Interview
                    </Link>
                </div>
            </div>

            {/* Content Tabs Wrapper */}
            <div className="mt-8">
                <PrepOverview prep={prep} />
            </div>
        </div>
    );
}
