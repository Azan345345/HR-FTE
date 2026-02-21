"use client";

import { Search, Mail, FileText, GraduationCap, ArrowRight, BarChart3 } from "lucide-react";
import { StatsCards } from "@/components/dashboard/StatsCards";
import { ExecutionLog } from "@/components/observability/ExecutionLog";
import { QuotaWidget } from "@/components/observability/QuotaWidget";

const quickActions = [
    { title: "Upload CV", description: "Start by uploading your resume", href: "/cv", icon: FileText },
    { title: "Find Jobs", description: "Search matching positions", href: "/jobs", icon: Search },
    { title: "Track Applications", description: "Monitor your applications", href: "/applications", icon: Mail },
    { title: "Interview Prep", description: "Prepare for upcoming interviews", href: "/interview", icon: GraduationCap },
];

export default function DashboardPage() {
    return (
        <div className="space-y-8 animate-fadeIn">
            {/* Header */}
            <div>
                <h1 className="text-3xl font-bold">
                    Welcome to <span className="gradient-text">Digital FTE</span>
                </h1>
                <p className="text-muted-foreground mt-2">
                    Your AI-powered job application assistant is ready to work.
                </p>
            </div>

            {/* Dynamic Stats Module */}
            <StatsCards />

            {/* Quick Actions */}
            <div>
                <h2 className="text-xl font-semibold mb-4">Quick Actions</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {quickActions.map((action) => (
                        <a
                            key={action.title}
                            href={action.href}
                            className="glass rounded-xl p-5 flex items-center gap-4 group hover:border-indigo-500/50 transition-all duration-300"
                        >
                            <div className="h-12 w-12 rounded-lg bg-indigo-500/10 flex items-center justify-center group-hover:bg-indigo-500/20 transition-colors">
                                <action.icon className="h-6 w-6 text-indigo-400" />
                            </div>
                            <div className="flex-1">
                                <h3 className="font-semibold">{action.title}</h3>
                                <p className="text-sm text-muted-foreground">{action.description}</p>
                            </div>
                            <ArrowRight className="h-5 w-5 text-muted-foreground group-hover:text-indigo-400 transition-colors" />
                        </a>
                    ))}
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Activity Feed */}
                <div className="lg:col-span-2">
                    <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
                        <BarChart3 className="w-5 h-5 text-indigo-400" />
                        Recent Activity
                    </h2>
                    <div className="glass rounded-xl p-6">
                        <ExecutionLog limit={3} />
                    </div>
                </div>

                {/* Quota Hud */}
                <div className="lg:col-span-1">
                    <QuotaWidget />
                </div>
            </div>
        </div>
    );
}
