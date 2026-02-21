"use client";

import { useState } from "react";
import { X, Download, FileText, CheckCircle2, ChevronRight, ArrowLeft } from "lucide-react";
import { CVDetail } from "@/components/cv/cv-detail";
import { useTailorStore } from "@/stores/tailor-store";
import { useAuthStore } from "@/stores/auth-store";

export function TailoredPreview() {
    const { tailoredCV, setShowPreview } = useTailorStore();
    const { accessToken } = useAuthStore();
    const [isDownloading, setIsDownloading] = useState(false);

    const apiBase = process.env.NEXT_PUBLIC_API_URL || "";

    if (!tailoredCV) return null;

    const handleDownload = async () => {
        setIsDownloading(true);
        try {
            const res = await fetch(`${apiBase}/api/cv/tailored/${tailoredCV.id}/pdf`, {
                headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
            });

            if (!res.ok) throw new Error("Download failed");

            const blob = await res.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `Tailored_CV_${tailoredCV.company.replace(/\s+/g, "_")}.pdf`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } catch (err) {
            console.error(err);
            // alert("Failed to download PDF"); // Simple error handling for now
        } finally {
            setIsDownloading(false);
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex flex-col bg-background/95 backdrop-blur-sm animate-fadeIn">
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-border bg-background/80 backdrop-blur-md">
                <div className="flex items-center gap-4">
                    <button
                        onClick={() => setShowPreview(false)}
                        className="p-2 hover:bg-secondary rounded-full transition-colors"
                    >
                        <ArrowLeft className="h-5 w-5" />
                    </button>
                    <div>
                        <h2 className="font-bold flex items-center gap-2">
                            <span className="text-indigo-400">Tailored CV</span>
                            <ChevronRight className="h-4 w-4 text-muted-foreground" />
                            <span>{tailoredCV.jobTitle}</span>
                        </h2>
                        <p className="text-xs text-muted-foreground">Targeting {tailoredCV.company}</p>
                    </div>
                </div>

                <div className="flex items-center gap-3">
                    <div className="hidden sm:flex items-center gap-2 text-xs text-emerald-400 bg-emerald-500/10 px-3 py-1.5 rounded-full font-medium">
                        <CheckCircle2 className="h-3.5 w-3.5" />
                        Optimized for ATS
                    </div>
                    <button
                        onClick={handleDownload}
                        disabled={isDownloading}
                        className="flex items-center gap-2 px-4 py-2 bg-indigo-500 hover:bg-indigo-600 rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
                    >
                        {isDownloading ? (
                            <span className="animate-spin">⌛</span>
                        ) : (
                            <FileText className="h-4 w-4" />
                        )}
                        Download PDF
                    </button>
                </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-auto p-4 sm:p-8">
                <div className="max-w-4xl mx-auto">
                    {/* Reuse existing CV Detail component to show the tailored data */}
                    <CVDetail parsedData={tailoredCV.tailoredData as any} />
                </div>
            </div>
        </div>
    );
}
