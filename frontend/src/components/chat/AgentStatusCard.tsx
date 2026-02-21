"use client";

import { Activity, CheckCircle, Clock } from "lucide-react";

export function AgentStatusCard({
    agentName,
    status = "running",
    detail = "Initializing..."
}: {
    agentName: string;
    status?: "running" | "completed" | "error";
    detail?: string;
}) {
    const formatName = (name: string) => {
        return name.split("_").map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(" ");
    };

    return (
        <div className="flex flex-col gap-1 p-3 bg-secondary/30 rounded-lg border border-border/50 max-w-[280px]">
            <div className="flex items-center gap-2">
                {status === "running" ? (
                    <Activity className="w-4 h-4 text-indigo-400 animate-pulse" />
                ) : status === "completed" ? (
                    <CheckCircle className="w-4 h-4 text-emerald-400" />
                ) : (
                    <Clock className="w-4 h-4 text-amber-400" />
                )}
                <span className="font-medium text-xs text-foreground uppercase tracking-wider">{formatName(agentName)}</span>
            </div>
            <p className="text-xs text-muted-foreground ml-6">
                {detail}
            </p>
        </div>
    );
}
