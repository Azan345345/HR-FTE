"use client";

import { ApplicationList } from "@/components/applications/ApplicationList";

export default function ApplicationsPage() {
    return (
        <div className="space-y-6 animate-fadeIn">
            <div>
                <h1 className="text-2xl font-bold">Applications</h1>
                <p className="text-muted-foreground mt-1">Track and review your job applications</p>
            </div>

            <ApplicationList />
        </div>
    );
}
