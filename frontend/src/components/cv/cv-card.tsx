"use client";

import { FileText, Star, Trash2, Sparkles, Clock, CheckCircle2 } from "lucide-react";

interface CVCardProps {
    id: string;
    fileName: string;
    fileType: string;
    isPrimary: boolean;
    hasParsedData: boolean;
    createdAt?: string;
    onSelect: () => void;
    onParse: () => void;
    onDelete: () => void;
    onSetPrimary: () => void;
}

export function CVCard({
    id,
    fileName,
    fileType,
    isPrimary,
    hasParsedData,
    createdAt,
    onSelect,
    onParse,
    onDelete,
    onSetPrimary,
}: CVCardProps) {
    return (
        <div
            className="glass rounded-xl p-4 flex items-center gap-4 group hover:border-indigo-500/50 transition-all duration-300 cursor-pointer"
            onClick={onSelect}
        >
            {/* File icon */}
            <div className={`h-12 w-12 rounded-lg flex items-center justify-center ${fileType === "pdf" ? "bg-red-500/10" : "bg-blue-500/10"
                }`}>
                <FileText className={`h-6 w-6 ${fileType === "pdf" ? "text-red-400" : "text-blue-400"
                    }`} />
            </div>

            {/* Info */}
            <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                    <h3 className="font-medium text-sm truncate">{fileName}</h3>
                    {isPrimary && (
                        <span className="px-1.5 py-0.5 bg-amber-500/15 text-amber-400 text-xs rounded-md font-medium">
                            Primary
                        </span>
                    )}
                </div>
                <div className="flex items-center gap-3 mt-1">
                    <span className="text-xs text-muted-foreground uppercase">{fileType}</span>
                    {hasParsedData ? (
                        <span className="flex items-center gap-1 text-xs text-emerald-400">
                            <CheckCircle2 className="h-3 w-3" /> Parsed
                        </span>
                    ) : (
                        <span className="flex items-center gap-1 text-xs text-muted-foreground">
                            <Clock className="h-3 w-3" /> Not parsed
                        </span>
                    )}
                    {createdAt && (
                        <span className="text-xs text-muted-foreground">
                            {new Date(createdAt).toLocaleDateString()}
                        </span>
                    )}
                </div>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                {!hasParsedData && (
                    <button
                        onClick={(e) => { e.stopPropagation(); onParse(); }}
                        className="p-2 hover:bg-indigo-500/15 rounded-lg transition-colors"
                        title="Parse with AI"
                    >
                        <Sparkles className="h-4 w-4 text-indigo-400" />
                    </button>
                )}
                {!isPrimary && (
                    <button
                        onClick={(e) => { e.stopPropagation(); onSetPrimary(); }}
                        className="p-2 hover:bg-amber-500/15 rounded-lg transition-colors"
                        title="Set as primary"
                    >
                        <Star className="h-4 w-4 text-amber-400" />
                    </button>
                )}
                <button
                    onClick={(e) => { e.stopPropagation(); onDelete(); }}
                    className="p-2 hover:bg-red-500/15 rounded-lg transition-colors"
                    title="Delete"
                >
                    <Trash2 className="h-4 w-4 text-red-400" />
                </button>
            </div>
        </div>
    );
}
