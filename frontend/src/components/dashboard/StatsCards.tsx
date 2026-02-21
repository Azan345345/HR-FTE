"use client";

import { useEffect, useState } from "react";
import { useAuthStore } from "@/stores/auth-store";
import { FileText, Search, Mail, GraduationCap } from "lucide-react";

export function StatsCards() {
    const { accessToken } = useAuthStore();
    const apiBase = process.env.NEXT_PUBLIC_API_URL || "";

    const [stats, setStats] = useState({
        cvs_count: 0,
        jobs_count: 0,
        apps_count: 0,
        preps_count: 0
    });

    useEffect(() => {
        if (accessToken) {
            fetch(`${apiBase}/api/observability/stats`, {
                headers: { Authorization: `Bearer ${accessToken}` }
            })
                .then(res => res.json())
                .then(data => setStats(data))
                .catch(console.error);
        }
    }, [accessToken]);

    const cards = [
        { label: "CVs Uploaded", value: stats.cvs_count, icon: FileText, color: "text-indigo-400" },
        { label: "Jobs Found", value: stats.jobs_count, icon: Search, color: "text-blue-400" },
        { label: "Apps Tracked", value: stats.apps_count, icon: Mail, color: "text-emerald-400" },
        { label: "Interviews", value: stats.preps_count, icon: GraduationCap, color: "text-amber-400" },
    ];

    return (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 animate-fadeIn">
            {cards.map((stat) => (
                <div
                    key={stat.label}
                    className="glass rounded-xl p-5 hover:border-indigo-500/50 transition-all duration-300"
                >
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-sm text-muted-foreground">{stat.label}</p>
                            <p className="text-2xl font-bold mt-1">{stat.value}</p>
                        </div>
                        <stat.icon className={`h-8 w-8 ${stat.color} opacity-60`} />
                    </div>
                </div>
            ))}
        </div>
    );
}
