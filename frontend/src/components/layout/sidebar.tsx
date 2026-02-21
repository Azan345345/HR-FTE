"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
    LayoutDashboard, FileText, Search, Mail,
    GraduationCap, MessageSquare, Settings, Activity, Cpu,
} from "lucide-react";

const navItems = [
    { label: "Dashboard", href: "/", icon: LayoutDashboard },
    { label: "My CV", href: "/cv", icon: FileText },
    { label: "Jobs", href: "/jobs", icon: Search },
    { label: "Applications", href: "/applications", icon: Mail },
    { label: "Interview Prep", href: "/interview", icon: GraduationCap },
    { label: "Chat", href: "/chat", icon: MessageSquare },
    { label: "Agent Status", href: "/observability", icon: Activity },
    { label: "Settings", href: "/settings", icon: Settings },
];

export function Sidebar() {
    const pathname = usePathname();

    return (
        <aside className="w-64 h-screen flex flex-col bg-card border-r border-border">
            {/* Logo */}
            <div className="p-5 border-b border-border">
                <Link href="/" className="flex items-center gap-3">
                    <div className="h-9 w-9 rounded-lg bg-gradient-to-br from-indigo-500 to-blue-500 flex items-center justify-center animate-pulse-glow">
                        <Cpu className="h-5 w-5 text-white" />
                    </div>
                    <div>
                        <h1 className="font-bold text-lg leading-tight">Digital FTE</h1>
                        <p className="text-xs text-muted-foreground">AI Job Assistant</p>
                    </div>
                </Link>
            </div>

            {/* Navigation */}
            <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
                {navItems.map((item) => {
                    const isActive = pathname === item.href;
                    return (
                        <Link
                            key={item.href}
                            href={item.href}
                            className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200
                ${isActive
                                    ? "bg-indigo-500/15 text-indigo-400 border border-indigo-500/30"
                                    : "text-muted-foreground hover:bg-secondary hover:text-foreground"
                                }`}
                        >
                            <item.icon className="h-4.5 w-4.5" />
                            {item.label}
                        </Link>
                    );
                })}
            </nav>

            {/* Footer */}
            <div className="p-4 border-t border-border">
                <div className="glass rounded-lg p-3">
                    <p className="text-xs font-medium text-muted-foreground">Quota Status</p>
                    <div className="flex items-center gap-2 mt-2">
                        <div className="flex-1 h-1.5 bg-secondary rounded-full overflow-hidden">
                            <div className="h-full w-1/5 bg-gradient-to-r from-indigo-500 to-blue-500 rounded-full" />
                        </div>
                        <span className="text-xs text-muted-foreground">20%</span>
                    </div>
                </div>
            </div>
        </aside>
    );
}
