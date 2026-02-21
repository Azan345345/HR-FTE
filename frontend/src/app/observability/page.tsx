"use client";

import { Activity } from "lucide-react";
import { ExecutionLog } from "@/components/observability/ExecutionLog";
import { ReactFlowVisualizer } from "@/components/observability/react-flow-visualizer";

export default function ObservabilityPage() {
    return (
        <div className="space-y-6 animate-fadeIn">
            <div className="flex items-center justify-between mb-8">
                <div>
                    <h1 className="text-2xl font-bold flex items-center gap-3">
                        <Activity className="w-6 h-6 text-indigo-400" />
                        System Observability
                    </h1>
                    <p className="text-muted-foreground mt-1">Monitor background agent executions and trace system logs.</p>
                </div>
            </div>

            <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                <div className="glass rounded-xl p-6">
                    <h2 className="text-lg font-semibold mb-4">Agent Network Topology</h2>
                    <ReactFlowVisualizer />
                </div>

                <div className="glass rounded-xl p-6">
                    <h2 className="text-lg font-semibold mb-4">Execution Trace Logs</h2>
                    <div className="h-[500px] overflow-y-auto pr-2">
                        <ExecutionLog limit={20} />
                    </div>
                </div>
            </div>
        </div>
    );
}
