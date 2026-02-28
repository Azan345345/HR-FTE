import { create } from "zustand";

export interface LogEntry {
    id: string;
    time: string;
    emoji: string;
    agent: string;
    title: string;
    desc: string;
    thought?: string;
    status: "done" | "running" | "waiting" | "error";
    duration?: string;
    tokens?: string;
}
export type AgentName =
    | "supervisor"
    | "cv_parser"
    | "job_hunter"
    | "cv_tailor"
    | "hr_finder"
    | "email_sender"
    | "interview_prep"
    | "doc_generator";

export type AgentStatus = "idle" | "processing" | "completed" | "error" | "waiting";

interface AgentInfo {
    name: AgentName;
    status: AgentStatus;
    plan?: string;
    currentStep?: number;
    totalSteps?: number;
    currentAction?: string;
    drafts?: {
        cv?: any;
        cover_letter?: string;
        email?: string;
        application_id?: string;
    };
}

interface AgentStoreState {
    agents: Record<AgentName, AgentInfo>;
    activeAgent: AgentName | null;
    completedNodes: string[];
    logs: LogEntry[];
    setAgentStatus: (name: AgentName, updates: Partial<AgentInfo>) => void;
    setActiveAgent: (name: AgentName | null) => void;
    addCompletedNode: (node: string) => void;
    addLog: (log: Omit<LogEntry, "id" | "time">) => void;
    updateLastLogStatus: (agent: string, status: LogEntry["status"]) => void;
    setAgentDrafts: (name: AgentName, drafts: AgentInfo["drafts"]) => void;
    resetAll: () => void;
}

const defaultAgents: Record<AgentName, AgentInfo> = {
    supervisor: { name: "supervisor", status: "idle" },
    cv_parser: { name: "cv_parser", status: "idle" },
    job_hunter: { name: "job_hunter", status: "idle" },
    cv_tailor: { name: "cv_tailor", status: "idle" },
    hr_finder: { name: "hr_finder", status: "idle" },
    email_sender: { name: "email_sender", status: "idle" },
    interview_prep: { name: "interview_prep", status: "idle" },
    doc_generator: { name: "doc_generator", status: "idle" },
};

export const useAgentStore = create<AgentStoreState>((set) => ({
    agents: { ...defaultAgents },
    activeAgent: null,
    completedNodes: [],
    logs: [],

    setAgentStatus: (name, updates) =>
        set((state) => ({
            agents: {
                ...state.agents,
                [name]: { ...state.agents[name], ...updates },
            },
        })),

    setActiveAgent: (name) => set({ activeAgent: name }),

    addCompletedNode: (node) =>
        set((state) => ({
            completedNodes: [...state.completedNodes, node],
        })),

    addLog: (log) =>
        set((state) => ({
            logs: [
                ...state.logs,
                {
                    ...log,
                    id: crypto.randomUUID(),
                    time: new Date().toLocaleTimeString("en-US", { hour12: false }),
                },
            ],
        })),

    updateLastLogStatus: (agent, status) =>
        set((state) => {
            const index = [...state.logs].reverse().findIndex(l => l.agent === agent);
            if (index === -1) return state;
            const realIndex = state.logs.length - 1 - index;
            const newLogs = [...state.logs];
            newLogs[realIndex] = { ...newLogs[realIndex], status };
            return { logs: newLogs };
        }),

    setAgentDrafts: (name, drafts) =>
        set((state) => ({
            agents: {
                ...state.agents,
                [name]: { ...state.agents[name], drafts },
            },
        })),

    resetAll: () =>
        set({ agents: { ...defaultAgents }, activeAgent: null, completedNodes: [], logs: [] }),
}));
