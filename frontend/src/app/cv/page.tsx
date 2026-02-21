"use client";

import { useState, useCallback, useRef } from "react";
import { FileText, Upload, Loader2, AlertCircle, ArrowLeft, Sparkles } from "lucide-react";
import { CVCard } from "@/components/cv/cv-card";
import { CVDetail } from "@/components/cv/cv-detail";
import { useCVStore, type CVItem } from "@/stores/cv-store";
import { useAuthStore } from "@/stores/auth-store";

export default function CVPage() {
    const {
        cvs, selectedCV, isUploading, isParsing, uploadProgress, error,
        addCV, removeCV, selectCV, updateCV,
        setUploading, setParsing, setUploadProgress, setError,
    } = useCVStore();
    const { accessToken } = useAuthStore();
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [isDragging, setIsDragging] = useState(false);

    const apiBase = process.env.NEXT_PUBLIC_API_URL || "";

    // ── Upload handler ──────────────────────────
    const handleUpload = useCallback(async (file: File) => {
        setError(null);
        setUploading(true);
        setUploadProgress(0);

        try {
            const formData = new FormData();
            formData.append("file", file);

            const res = await fetch(`${apiBase}/api/cv/upload`, {
                method: "POST",
                headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
                body: formData,
            });

            if (!res.ok) {
                const err = await res.json().catch(() => ({ detail: "Upload failed" }));
                throw new Error(err.detail);
            }

            const data = await res.json();
            addCV({
                id: data.id,
                file_name: data.file_name,
                file_type: data.file_type,
                is_primary: data.is_primary,
                has_parsed_data: false,
                created_at: data.created_at,
            });

            // Auto-trigger parse
            handleParse(data.id);
        } catch (err: any) {
            setError(err.message || "Upload failed");
        } finally {
            setUploading(false);
            setUploadProgress(100);
        }
    }, [accessToken, apiBase]);

    // ── Parse handler ───────────────────────────
    const handleParse = useCallback(async (cvId: string) => {
        setParsing(true);
        try {
            const res = await fetch(`${apiBase}/api/cv/${cvId}/parse`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
                },
            });

            if (!res.ok) throw new Error("Parse failed");

            const analysis = await res.json();
            updateCV(cvId, {
                has_parsed_data: true,
                parsed_data: analysis.parsed_data,
            });
        } catch (err: any) {
            setError(err.message || "Parse failed");
        } finally {
            setParsing(false);
        }
    }, [accessToken, apiBase]);

    // ── Delete handler ──────────────────────────
    const handleDelete = useCallback(async (cvId: string) => {
        try {
            await fetch(`${apiBase}/api/cv/${cvId}`, {
                method: "DELETE",
                headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
            });
            removeCV(cvId);
            if (selectedCV?.id === cvId) selectCV(null);
        } catch (err: any) {
            setError(err.message || "Delete failed");
        }
    }, [accessToken, apiBase, selectedCV]);

    // ── Set primary handler ─────────────────────
    const handleSetPrimary = useCallback(async (cvId: string) => {
        try {
            await fetch(`${apiBase}/api/cv/${cvId}/primary`, {
                method: "PUT",
                headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
            });
            // Update all CVs locally
            useCVStore.getState().cvs.forEach((cv) => {
                updateCV(cv.id, { is_primary: cv.id === cvId });
            });
        } catch (err: any) {
            setError(err.message || "Failed to set primary");
        }
    }, [accessToken, apiBase]);

    // ── Drag and drop ───────────────────────────
    const handleDragOver = (e: React.DragEvent) => { e.preventDefault(); setIsDragging(true); };
    const handleDragLeave = () => setIsDragging(false);
    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(false);
        const file = e.dataTransfer.files[0];
        if (file) handleUpload(file);
    };

    const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) handleUpload(file);
    };

    // ── If a CV is selected, show detail view ───
    if (selectedCV) {
        return (
            <div className="space-y-4 animate-fadeIn">
                <button
                    onClick={() => selectCV(null)}
                    className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
                >
                    <ArrowLeft className="h-4 w-4" /> Back to CV list
                </button>
                <div className="flex items-center justify-between">
                    <h1 className="text-2xl font-bold">{selectedCV.file_name}</h1>
                    {!selectedCV.has_parsed_data && (
                        <button
                            onClick={() => handleParse(selectedCV.id)}
                            disabled={isParsing}
                            className="flex items-center gap-2 px-4 py-2 bg-indigo-500 hover:bg-indigo-600 rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
                        >
                            {isParsing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                            {isParsing ? "Parsing..." : "Parse with AI"}
                        </button>
                    )}
                </div>
                {selectedCV.parsed_data ? (
                    <CVDetail parsedData={selectedCV.parsed_data as any} />
                ) : isParsing ? (
                    <div className="glass rounded-xl p-12 text-center">
                        <Loader2 className="h-10 w-10 mx-auto mb-4 text-indigo-400 animate-spin" />
                        <p className="font-medium">Analyzing your CV with AI...</p>
                        <p className="text-sm text-muted-foreground mt-1">Extracting skills, experience, and more</p>
                    </div>
                ) : (
                    <div className="glass rounded-xl p-8 text-center text-muted-foreground">
                        <Sparkles className="h-10 w-10 mx-auto mb-3 opacity-40" />
                        <p>Click "Parse with AI" to extract structured data from this CV</p>
                    </div>
                )}
            </div>
        );
    }

    // ── Main list view ──────────────────────────
    return (
        <div className="space-y-6 animate-fadeIn">
            <div>
                <h1 className="text-2xl font-bold">My CV</h1>
                <p className="text-muted-foreground mt-1">Upload and manage your resumes</p>
            </div>

            {/* Error */}
            {error && (
                <div className="flex items-center gap-3 p-4 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400">
                    <AlertCircle className="h-5 w-5 flex-shrink-0" />
                    <p className="text-sm">{error}</p>
                </div>
            )}

            {/* Upload Area */}
            <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`glass rounded-xl p-12 text-center border-2 border-dashed transition-all cursor-pointer
          ${isDragging
                        ? "border-indigo-500 bg-indigo-500/5"
                        : "border-border hover:border-indigo-500/50"
                    }
          ${isUploading ? "pointer-events-none opacity-60" : ""}
        `}
            >
                <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf,.docx"
                    onChange={handleFileSelect}
                    className="hidden"
                />
                {isUploading ? (
                    <>
                        <Loader2 className="h-12 w-12 mx-auto text-indigo-400 mb-4 animate-spin" />
                        <p className="font-medium">Uploading...</p>
                    </>
                ) : (
                    <>
                        <Upload className={`h-12 w-12 mx-auto mb-4 ${isDragging ? "text-indigo-400" : "text-muted-foreground"}`} />
                        <p className="font-medium">
                            {isDragging ? "Drop your CV here" : "Drop your CV here or click to browse"}
                        </p>
                        <p className="text-sm text-muted-foreground mt-1">Supports PDF and DOCX (max 10MB)</p>
                    </>
                )}
            </div>

            {/* CV List */}
            {cvs.length > 0 ? (
                <div className="space-y-3">
                    <h2 className="text-lg font-semibold">Your CVs ({cvs.length})</h2>
                    {cvs.map((cv) => (
                        <CVCard
                            key={cv.id}
                            id={cv.id}
                            fileName={cv.file_name}
                            fileType={cv.file_type}
                            isPrimary={cv.is_primary}
                            hasParsedData={cv.has_parsed_data}
                            createdAt={cv.created_at}
                            onSelect={() => selectCV(cv)}
                            onParse={() => handleParse(cv.id)}
                            onDelete={() => handleDelete(cv.id)}
                            onSetPrimary={() => handleSetPrimary(cv.id)}
                        />
                    ))}
                </div>
            ) : (
                <div className="glass rounded-xl p-8 text-center text-muted-foreground">
                    <FileText className="h-10 w-10 mx-auto mb-3 opacity-40" />
                    <p>No CVs uploaded yet</p>
                </div>
            )}
        </div>
    );
}
