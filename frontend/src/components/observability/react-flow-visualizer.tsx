"use client";

import { useEffect, useMemo, useState } from "react";
import {
    ReactFlow,
    Background,
    Controls,
    Node,
    Edge,
    Position,
    MarkerType
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useAuthStore } from "@/stores/auth-store";

// Define the static topology of our LangGraph orchestration
const initialNodes: Node[] = [
    {
        id: "user", data: { label: "User Input" }, position: { x: 250, y: 0 }, type: "input",
        style: { background: "#4f46e5", color: "white", borderRadius: "10px", padding: "10px" }
    },
    {
        id: "supervisor", data: { label: "Supervisor Agent" }, position: { x: 250, y: 100 },
        style: { background: "#6366f1", color: "white", borderRadius: "8px", fontWeight: "bold" }
    },
    { id: "cv_parser", data: { label: "CV Parser" }, position: { x: 0, y: 200 } },
    { id: "job_hunter", data: { label: "Job Hunter" }, position: { x: 150, y: 200 } },
    { id: "cv_tailor", data: { label: "CV Tailor" }, position: { x: 350, y: 200 } },
    { id: "hr_finder", data: { label: "HR Finder" }, position: { x: 500, y: 200 } },
    { id: "email_sender", data: { label: "Email Sender" }, position: { x: 500, y: 300 } },
    { id: "interview_prep", data: { label: "Interview Prep" }, position: { x: 250, y: 300 } },
    { id: "doc_generator", data: { label: "Doc Generator" }, position: { x: 250, y: 400 }, type: "output" },
];

const initialEdges: Edge[] = [
    { id: "e-user-sup", source: "user", target: "supervisor", markerEnd: { type: MarkerType.ArrowClosed } },
    { id: "e-sup-cv", source: "supervisor", target: "cv_parser", animated: true },
    { id: "e-sup-job", source: "supervisor", target: "job_hunter", animated: true },
    { id: "e-sup-tailor", source: "supervisor", target: "cv_tailor", animated: true },
    { id: "e-sup-hr", source: "supervisor", target: "hr_finder", animated: true },
    { id: "e-sup-int", source: "supervisor", target: "interview_prep", animated: true },

    // Sequential fallback dependencies (implied by graph logic)
    { id: "e-hr-email", source: "hr_finder", target: "email_sender", animated: true },
    { id: "e-int-doc", source: "interview_prep", target: "doc_generator", animated: true },
];

export function ReactFlowVisualizer() {
    const { accessToken } = useAuthStore();
    const apiBase = process.env.NEXT_PUBLIC_API_URL || "";

    const [nodes, setNodes] = useState<Node[]>(initialNodes);
    const [edges, setEdges] = useState<Edge[]>(initialEdges);

    // Fetch latest execution to highlight active node
    useEffect(() => {
        if (!accessToken) return;

        const fetchLatestLog = async () => {
            try {
                const res = await fetch(`${apiBase}/api/observability/logs?limit=1`, {
                    headers: { Authorization: `Bearer ${accessToken}` }
                });
                const data = await res.json();

                if (data && data.length > 0) {
                    const latestAgent = data[0].agent_name;
                    const status = data[0].status;

                    // Update node styles based on active agent
                    setNodes(nds => nds.map(node => {
                        if (node.id === latestAgent) {
                            return {
                                ...node,
                                style: {
                                    ...node.style,
                                    background: status === "completed" ? "#10b981" : status === "failed" ? "#f43f5e" : "#f59e0b",
                                    color: "white",
                                    border: "2px solid white"
                                }
                            };
                        }
                        return {
                            ...node,
                            style: { ...node.style, opacity: 0.7 }
                        };
                    }));
                }
            } catch (err) {
                console.error("Failed to fetch node status:", err);
            }
        };

        // Poll every 5 seconds to show pseudo real-time transitions
        fetchLatestLog();
        const interval = setInterval(fetchLatestLog, 5000);
        return () => clearInterval(interval);
    }, [accessToken, apiBase]);

    return (
        <div className="w-full h-[500px] border border-border/50 rounded-xl overflow-hidden bg-secondary/20">
            <ReactFlow
                nodes={nodes}
                edges={edges}
                fitView
                attributionPosition="bottom-right"
                colorMode={"dark"}
            >
                <Background gap={12} size={1} />
                <Controls />
            </ReactFlow>
        </div>
    );
}
