"use client";

import { useEffect, useState } from "react";
import { useAuthStore } from "@/stores/auth-store";
import { Activity, AlertCircle, CheckCircle, Clock } from "lucide-react";

export function ExecutionLog({ limit = 5 }: { limit?: number }) {
    const { accessToken } = useAuthStore();
    const apiBase = process.env.NEXT_PUBLIC_API_URL || "";
    const [logs, setLogs] = useState<any[]>([]);

    useEffect(() => {
        if (accessToken) {
            fetch(`${apiBase}/api/observability/logs?limit=${limit}`, {
                headers: { Authorization: `Bearer ${accessToken}` }
            })
                .then(res => res.json())
                .then(data => setLogs(data))
                .catch(console.error);
        }
    }, [accessToken, limit]);

    if (logs.length === 0) {
        return (
            <div className="p-6 text-center text-muted-foreground">
                <p>No recent executions recorded.</p>
            </div>
        );
    }

    return (
        <div className="space-y-4">
            {logs.map((log) => (
                <div key={log.id} className="p-4 rounded-xl bg-secondary/30 border border-border/50 flex flex-col sm:flex-row sm:items-center gap-4">
                    <div className="flex-shrink-0">
                        {log.status === "completed" ? (
                            <CheckCircle className="h-6 w-6 text-emerald-400" />
                        ) : log.status === "failed" ? (
                            <AlertCircle className="h-6 w-6 text-rose-400" />
                        ) : log.status === "running" ? (
                            <Activity className="h-6 w-6 text-indigo-400 animate-pulse" />
                        ) : (
                            <Clock className="h-6 w-6 text-amber-400" />
                        )}
                    </div>

                    <div className="flex-1">
                        <div className="flex items-center gap-2">
                            <span className="font-semibold">{log.agent_name.replace(/_/g, " ").toUpperCase()}</span>
                            <span className={`text-xs px-2 py-0.5 rounded-full ${log.status === "completed" ? "bg-emerald-500/10 text-emerald-500" :
                                    log.status === "failed" ? "bg-rose-500/10 text-rose-500" :
                                        "bg-amber-500/10 text-amber-500"
                                }`}>
                                {log.status}
                            </span>
                        </div>

                        <p className="text-sm text-muted-foreground mt-1 line-clamp-2">
                            {log.status === "failed" ? log.error_message : log.result_data || "Running processes..."}
                        </p>
                    </div>

                    <div className="text-xs text-muted-foreground flex-shrink-0">
                        {new Date(log.created_at).toLocaleString()}
                    </div>
                </div>
            ))}
        </div>
    );
}
