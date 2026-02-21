"use client";

import { useEffect, useState } from "react";
import { ApplicationCard } from "./ApplicationCard";
import { ApprovalDialog } from "./ApprovalDialog";
import { useAuthStore } from "@/stores/auth-store";
import { Mail, RefreshCw } from "lucide-react";

export function ApplicationList() {
    const { accessToken } = useAuthStore();
    const [applications, setApplications] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedApp, setSelectedApp] = useState<any | null>(null);

    const apiBase = process.env.NEXT_PUBLIC_API_URL || "";

    const fetchApplications = async () => {
        setLoading(true);
        try {
            const res = await fetch(`${apiBase}/api/applications`, {
                headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
            });
            if (res.ok) {
                const data = await res.json();
                setApplications(data);
            }
        } catch (error) {
            console.error("Failed to fetch applications:", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (accessToken) {
            fetchApplications();
        }
    }, [accessToken]);

    if (loading) {
        return <div className="flex items-center justify-center p-12 text-muted-foreground"><RefreshCw className="h-6 w-6 animate-spin" /></div>;
    }

    if (applications.length === 0) {
        return (
            <div className="glass rounded-xl p-8 text-center text-muted-foreground animate-fadeIn">
                <Mail className="h-10 w-10 mx-auto mb-3 opacity-40" />
                <p>No applications yet. Find jobs and apply to track them here!</p>
            </div>
        );
    }

    return (
        <div className="space-y-4 animate-fadeIn">
            <div className="flex items-center justify-between mb-2">
                <h2 className="font-semibold">Your Applications</h2>
                <button onClick={fetchApplications} className="text-sm flex items-center gap-1.5 text-muted-foreground hover:text-foreground">
                    <RefreshCw className="h-4 w-4" /> Refresh
                </button>
            </div>

            <div className="grid grid-cols-1 gap-4">
                {applications.map((app) => (
                    <ApplicationCard
                        key={app.id}
                        application={app}
                        onReview={() => setSelectedApp(app)}
                    />
                ))}
            </div>

            {selectedApp && (
                <ApprovalDialog
                    application={selectedApp}
                    onClose={() => setSelectedApp(null)}
                    onApproved={() => {
                        setSelectedApp(null);
                        fetchApplications();
                    }}
                />
            )}
        </div>
    );
}
