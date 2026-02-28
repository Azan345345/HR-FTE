/**
 * WebSocket hook for real-time agent observability updates.
 * Connects to the backend WebSocket endpoint and dispatches events
 * to the agent store.
 */
import { useEffect, useRef, useCallback, useState } from "react";
import { useAgentStore, AgentName } from "@/stores/agent-store";

// Use Vite proxy in dev (relative URL → ws://localhost:5173/ws → proxied to backend)
const WS_URL =
    (import.meta as any).env?.VITE_WS_URL ||
    `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host}/ws`;

interface WSMessage {
    type: string;
    data: Record<string, unknown>;
}

const agentEmojiMap: Record<string, string> = {
    supervisor: "🟢",
    cv_parser: "📄",
    job_hunter: "🔍",
    cv_tailor: "✍️",
    hr_finder: "📧",
    email_sender: "📧",
    interview_prep: "🎤",
    doc_generator: "📝",
};

export function useWebSocket(token: string | null) {
    const wsRef = useRef<WebSocket | null>(null);
    const [isConnected, setIsConnected] = useState(false);
    const { setAgentStatus, setActiveAgent, addCompletedNode, addLog, updateLastLogStatus } = useAgentStore();

    const connect = useCallback(() => {
        if (!token || wsRef.current?.readyState === WebSocket.OPEN) return;

        const ws = new WebSocket(WS_URL);
        wsRef.current = ws;

        ws.onopen = () => {
            console.log("WebSocket connecting...");
            // Send JWT for authentication
            if (token) {
                ws.send(token);
                console.log("WebSocket auth token sent");
            }
        };

        ws.onmessage = (event) => {
            try {
                const msg: WSMessage = JSON.parse(event.data);
                handleMessage(msg);
            } catch {
                // ignore malformed messages
            }
        };

        ws.onclose = () => {
            setIsConnected(false);
            // Auto-reconnect after 3 seconds
            setTimeout(() => connect(), 3000);
        };

        ws.onerror = () => {
            ws.close();
        };
    }, [token]);

    const handleMessage = useCallback(
        (msg: WSMessage) => {
            const { type, data } = msg;
            const agentName = (data.agent_name as AgentName) || "supervisor";

            switch (type) {
                case "connected":
                    setIsConnected(true);
                    break;

                case "agent_started": {
                    const plan = (data.plan as string) || "";
                    setAgentStatus(agentName, {
                        status: "processing",
                        plan,
                        currentStep: 0,
                        currentAction: "Starting...",
                    });
                    setActiveAgent(agentName);
                    addLog({
                        emoji: agentEmojiMap[agentName] || "🤖",
                        agent: agentName,
                        title: "Agent Started",
                        desc: plan || "Initializing tasks...",
                        thought: (data.thought as string) || (plan.length > 60 ? plan : undefined),
                        status: "running",
                    });
                    break;
                }

                case "agent_progress": {
                    const action = (data.current_action as string) || "Processing";
                    const details = (data.details as string) || "";
                    setAgentStatus(agentName, {
                        currentStep: data.step as number,
                        totalSteps: data.total_steps as number,
                        currentAction: action,
                    });
                    addLog({
                        emoji: agentEmojiMap[agentName] || "🤖",
                        agent: agentName,
                        title: action,
                        desc: details || `Step ${data.step} of ${data.total_steps}`,
                        thought: details.length > 60 ? details : undefined,
                        status: "running",
                    });
                    break;
                }

                case "log_entry": {
                    const desc = (data.desc as string) || "";
                    addLog({
                        emoji: (data.emoji as string) || "📝",
                        agent: (data.agent as string) || "System",
                        title: (data.title as string) || "Log",
                        desc,
                        thought: (data.thought as string) || (desc.length > 80 ? desc : undefined),
                        status: (data.status as any) || "running",
                        duration: data.duration as string,
                        tokens: data.tokens as string,
                    });
                    break;
                }

                case "agent_completed": {
                    const summary = (data.result_summary as string) || "Task finished executing.";
                    setAgentStatus(agentName, { status: "completed" });
                    addCompletedNode(agentName);
                    updateLastLogStatus(agentName, "done");
                    addLog({
                        emoji: "✅",
                        agent: agentName,
                        title: "Completed Successfully",
                        desc: summary,
                        thought: (data.thought as string) || (summary.length > 60 ? summary : undefined),
                        status: "done",
                        duration: data.time_taken ? `${Number(data.time_taken).toFixed(1)}s` : undefined,
                        tokens: data.tokens_used ? `${data.tokens_used} tokens` : undefined,
                    });
                    break;
                }

                case "agent_error": {
                    const errMsg = (data.error_message as string) || "An unexpected error occurred.";
                    setAgentStatus(agentName, {
                        status: "error",
                        currentAction: errMsg,
                    });
                    updateLastLogStatus(agentName, "error");
                    addLog({
                        emoji: "❌",
                        agent: agentName,
                        title: "Execution Error",
                        desc: errMsg,
                        thought: errMsg.length > 60 ? errMsg : undefined,
                        status: "error",
                    });
                    break;
                }

                case "workflow_update":
                    // Update completed nodes list
                    const completed = (data.completed_nodes as string[]) || [];
                    completed.forEach((node) => addCompletedNode(node));
                    if (data.active_node) {
                        setActiveAgent(data.active_node as AgentName);
                    }
                    break;

                case "agent_update":
                    setAgentStatus(agentName, {
                        status: data.status as any,
                        currentAction: data.job_info as string,
                        plan: data.plan as string,
                    });
                    break;

                case "approval_requested":
                    setAgentStatus(agentName, {
                        status: "waiting",
                        currentAction: "Awaiting your review...",
                        drafts: {
                            cv: data.cv,
                            cover_letter: data.cover_letter as string,
                            email: data.email as string,
                            application_id: data.application_id as string,
                        }
                    });
                    setActiveAgent(agentName);
                    addLog({
                        emoji: "✋",
                        agent: agentName,
                        title: "Approval Requested",
                        desc: "Please review and approve the draft before sending.",
                        status: "waiting",
                    });
                    break;

                case "pong":
                    break;

                default:
                    break;
            }
        },
        [setAgentStatus, setActiveAgent, addCompletedNode]
    );

    useEffect(() => {
        connect();
        return () => {
            wsRef.current?.close();
        };
    }, [connect]);

    // Heartbeat — send ping every 30s
    useEffect(() => {
        const interval = setInterval(() => {
            if (wsRef.current?.readyState === WebSocket.OPEN) {
                wsRef.current.send("ping");
            }
        }, 30000);
        return () => clearInterval(interval);
    }, []);

    return { isConnected };
}
